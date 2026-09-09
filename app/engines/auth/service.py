"""
Auth Engine — AuthService (Complete Level 5 Implementation)
All business logic. Routers call methods only — zero business logic in routers.
Every method:
  - Validates inputs
  - Applies rate limiting where appropriate
  - Publishes domain events
  - Writes audit log
  - Returns typed data
"""
from __future__ import annotations
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.permissions import ROLE_PERMISSIONS, permission_checker
from app.core.security import (
    enforce_otp_delivery_budget,
    enforce_otp_send_limits,
    enforce_otp_verify_limits,
)
from app.engines.auth.constants import (
    ACCESS_TOKEN_EXPIRE_MINUTES, BACKUP_CODE_COUNT,
    MAX_FAILED_LOGIN_ATTEMPTS, LOCKOUT_MINUTES, HARD_LOCKOUT_ATTEMPTS,
    OTP_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, PASSWORD_HISTORY_COUNT,
    REDIS_BLACKLIST_PREFIX, REDIS_IMPERSONATION_PREFIX, REDIS_MFA_CHALLENGE_PREFIX,
    AUDIENCE, LOGIN_EVENT_PUBLIC_MAP, LOGIN_EVENT_UNKNOWN_LABEL, LOGIN_EVENT_UNKNOWN_OUTCOME,
)
from app.engines.auth.models import (
    User, UserSession, RefreshToken, RefreshTokenFamily,
    MFASecret, MFABackupCode, StaffPermission,
    ApiKey, OTPRecord, AuthAuditLog, LoginEvent,
)
from app.engines.tenant_engine.models import Tenant
from app.engines.auth.utils import (
    hash_password, verify_password, validate_password_strength,
    create_access_token, create_refresh_token, create_mfa_challenge_token,
    create_impersonation_token, decode_token, hash_token,
    generate_otp, verify_otp, hash_recipient,
    generate_totp_secret, get_totp_uri, verify_totp,
    generate_backup_codes, verify_backup_code,
    generate_api_key, parse_device_info,
)
from app.exceptions import ServiceOSException, NotFoundException, PermissionDeniedException
from app.redis_client import get_redis, RedisKeys

logger = structlog.get_logger("auth.service")

_PERMISSION_KEYS: frozenset[str] | None = None


def _valid_permission_keys() -> frozenset[str]:
    """Every permission string the platform actually defines.

    Phase 2A Slice 2F-29 (M01): built from the existing registry only -- the
    `P` constants plus every permission granted by `ROLE_PERMISSIONS`. No
    permission is created here. Used to reject unknown StaffPermission keys
    before they are persisted as live overrides.
    """
    global _PERMISSION_KEYS
    if _PERMISSION_KEYS is None:
        from app.core.permissions import P as _P
        keys = {v for k, v in vars(_P).items()
                if not k.startswith("_") and isinstance(v, str)}
        for granted in ROLE_PERMISSIONS.values():
            keys.update(g for g in granted if isinstance(g, str))
        _PERMISSION_KEYS = frozenset(keys)
    return _PERMISSION_KEYS
utcnow = lambda: datetime.now(timezone.utc)

# Auth events sensitive enough to also mirror into the cross-engine
# PlatformAuditLog. Routine auth traffic (login attempts, MFA challenges,
# token refresh) stays in AuthAuditLog only — mirroring it would drown out
# the platform-wide security view with high-volume, low-risk noise.
PLATFORM_AUDIT_ACTIONS = {
    "staff.invited", "staff.permissions_updated", "staff.deactivated",
    "impersonation.started", "impersonation.ended",
    "api_key.created", "api_key.revoked", "api_key.updated",
    "account.locked_permanent", "token.theft_detected",
}


class AuthService:
    def __init__(self, db: AsyncSession, request_id: str = "—", ip_address: str | None = None):
        self.db = db
        self.redis = get_redis()
        self.settings = get_settings()
        self.request_id = request_id
        self.ip_address = ip_address

    # ── Internal Helpers ──────────────────────────────────────────────────────
    async def _get_user_by_email(self, email: str) -> User | None:
        # `scalar_one_or_none()` RAISES on more than one row, and this ran before any
        # password check -- so a single duplicated email turned every login for that
        # address into a 500 with nothing to explain it. It happened: a tenant owner
        # signed up again on the customer side and locked themselves out of a live
        # business account entirely.
        #
        # Migration 243 adds the unique index that should make this impossible. This
        # stays deliberately tolerant anyway: an auth path is the worst place to
        # discover a data problem by crashing, and the same defence has been on the
        # phone lookup below for exactly this reason. Newest row wins, matching it.
        r = await self.db.execute(
            select(User)
            .where(func.lower(User.email) == email.lower().strip())
            .order_by(User.created_at.desc())
            .limit(1)
        )
        return r.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        r = await self.db.execute(select(User).where(User.id == user_id))
        return r.scalar_one_or_none()

    async def _get_user_by_phone(self, phone: str) -> User | None:
        # Phone now HAS a unique index (migration 243), but this tolerance stays for the
        # same reason as the email lookup above: crashing an auth path is a worse failure
        # than picking the newest of two rows.
        r = await self.db.execute(
            select(User).where(User.phone == phone).order_by(User.created_at.desc()).limit(1)
        )
        return r.scalar_one_or_none()

    async def resolve_post_login_destination(self, user: User) -> dict[str, str]:
        """Project one backend-authoritative destination after authentication.

        Tenant status protects the account as a whole; the vertical
        enrollment then selects setup, review, activation, or operations.
        Frontends map these stable keys to their own routes.
        """
        if user.role == "customer":
            return {"next_destination": "access_rejected", "reason_code": "CUSTOMER_ROLE_NOT_PERMITTED"}
        if user.role == "technician":
            return {"next_destination": "technician_app", "reason_code": "TECHNICIAN_ROLE_NO_PORTAL_ACCESS"}
        if user.role in ("super_admin", "admin_operations", "admin_finance", "admin_support", "admin_readonly"):
            return {"next_destination": "admin_dashboard", "reason_code": "ADMIN_ROLE"}
        if not user.tenant_id:
            return {"next_destination": "resume_signup", "reason_code": "NO_TENANT_MEMBERSHIP"}

        tenant_result = await self.db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            return {"next_destination": "resume_signup", "reason_code": "TENANT_NOT_FOUND"}
        if tenant.status in ("suspended", "terminated"):
            return {"next_destination": "restricted_account", "reason_code": "TENANT_SUSPENDED"}

        from app.engines.vertical_catalog.models import TenantVerticalEnrollment
        enrollment_result = await self.db.execute(
            select(TenantVerticalEnrollment)
            .where(TenantVerticalEnrollment.tenant_id == user.tenant_id)
            .order_by(TenantVerticalEnrollment.created_at.desc())
        )
        enrollments = enrollment_result.scalars().all()
        if not enrollments:
            return {"next_destination": "vertical_setup_wizard", "reason_code": "VERTICAL_SETUP_NOT_STARTED"}

        status = enrollments[0].status
        if status in ("draft", "draft_setup"):
            return {"next_destination": "vertical_setup_wizard", "reason_code": "VERTICAL_SETUP_NOT_STARTED"}
        if status == "changes_requested":
            # The status page explains the admin's note and offers the
            # explicit "Continue corrections" action. Dropping a provider
            # straight into the wizard hides the reason they were sent back.
            return {"next_destination": "application_status", "reason_code": "CHANGES_REQUESTED"}
        if status in ("submitted", "under_review", "rejected"):
            return {"next_destination": "application_status", "reason_code": "VERTICAL_UNDER_REVIEW"}
        if status in ("approved", "approved_pending_activation", "activation_requirements_pending", "activating"):
            return {"next_destination": "activation_center", "reason_code": "VERTICAL_APPROVED_PENDING_ACTIVATION"}
        if status == "active":
            return {"next_destination": "tenant_dashboard", "reason_code": "VERTICAL_ACTIVE"}
        return {"next_destination": "restricted_account", "reason_code": "VERTICAL_STATUS_UNSUPPORTED"}

    async def get_mobile_access_context(self, user_id: uuid.UUID) -> dict:
        """Backend-authoritative access projection shared by native apps.

        Tenant and vertical state come from their canonical tables. Staff
        identity follows the same compatibility rule as assignment/execution:
        use ProviderTeamMember when present, otherwise use the active auth user
        id because existing jobs may legitimately be assigned to users.id.
        """
        user = await self._get_user_by_id(user_id)
        if user is None:
            raise NotFoundException("User", str(user_id))

        tenant_status = None
        enabled_verticals: list[str] = []
        if user.tenant_id:
            tenant_result = await self.db.execute(
                select(Tenant).where(Tenant.id == user.tenant_id)
            )
            tenant = tenant_result.scalar_one_or_none()
            if tenant is not None:
                tenant_status = tenant.status

            from app.engines.vertical_catalog.models import (
                TenantVerticalEnrollment,
                Vertical,
            )
            enrollment_result = await self.db.execute(
                select(Vertical.key)
                .join(
                    TenantVerticalEnrollment,
                    TenantVerticalEnrollment.vertical_id == Vertical.id,
                )
                .where(
                    TenantVerticalEnrollment.tenant_id == user.tenant_id,
                    TenantVerticalEnrollment.status == "active",
                    Vertical.is_enabled.is_(True),
                )
                .order_by(Vertical.key)
            )
            enabled_verticals = list(enrollment_result.scalars().all())

        technician_id = None
        technician_status = None
        if user.role in ("technician", "staff") and user.tenant_id:
            from app.engines.home_service_assignment.staff_model import ProviderTeamMember

            member_result = await self.db.execute(
                select(ProviderTeamMember).where(
                    ProviderTeamMember.user_id == user.id,
                    ProviderTeamMember.tenant_id == user.tenant_id,
                )
            )
            member = member_result.scalar_one_or_none()
            if member is not None:
                technician_id = str(member.id)
                technician_status = member.status
            else:
                # Current production/demo assignments use users.id when the
                # optional roster row has not been created. Returning null here
                # would lock that valid technician out of the native app.
                technician_id = str(user.id)
                technician_status = "active" if getattr(user, "is_active", True) else "suspended"

        return {
            "user_id": str(user.id),
            "canonical_role": user.role,
            "audience": AUDIENCE.get(user.role, "serviceos:customer"),
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "tenant_status": tenant_status,
            "technician_id": technician_id,
            "technician_status": technician_status,
            "enabled_verticals": enabled_verticals,
            "capabilities": ROLE_PERMISSIONS.get(user.role, []),
        }

    async def _is_blacklisted(self, jti: str) -> bool:
        try:
            return await self.redis.exists(f"{REDIS_BLACKLIST_PREFIX}{jti}") > 0
        except Exception:
            return False

    async def _blacklist(self, jti: str, ttl: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60) -> None:
        try:
            await self.redis.setex(f"{REDIS_BLACKLIST_PREFIX}{jti}", ttl, "1")
        except Exception:
            pass

    async def _audit(
        self,
        action_type: str,
        outcome: str,
        actor_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        tenant_id: uuid.UUID | None = None,
        target_id: uuid.UUID | None = None,
        target_type: str | None = None,
        failure_reason: str | None = None,
        session_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> None:
        log = AuthAuditLog(
            actor_id=actor_id,
            actor_role=actor_role,
            tenant_id=tenant_id,
            action_type=action_type,
            target_id=target_id,
            target_type=target_type,
            outcome=outcome,
            failure_reason=failure_reason,
            ip_address=self.ip_address,
            device_id=None,
            session_id=session_id,
            action_meta=metadata or {},
        )
        self.db.add(log)

        if action_type in PLATFORM_AUDIT_ACTIONS:
            from app.core.audit import record_platform_audit
            await record_platform_audit(
                self.db, operation=action_type, engine_id="auth", tenant_id=tenant_id,
                entity_type=target_type, entity_id=str(target_id) if target_id else None,
                actor_id=actor_id, actor_role=actor_role, actor_ip=self.ip_address,
                request_id=self.request_id, after=metadata,
            )

    async def _get_failed_attempts(self, email: str) -> int:
        from app.engines.auth.constants import REDIS_FAILED_ATTEMPTS_PREFIX
        v = await self.redis.get(f"{REDIS_FAILED_ATTEMPTS_PREFIX}{email.lower()}")
        return int(v) if v else 0

    async def _increment_failed(self, email: str) -> int:
        from app.engines.auth.constants import REDIS_FAILED_ATTEMPTS_PREFIX
        key = f"{REDIS_FAILED_ATTEMPTS_PREFIX}{email.lower()}"
        c = await self.redis.incr(key)
        await self.redis.expire(key, LOCKOUT_MINUTES * 60)
        return c

    async def _clear_failed(self, email: str) -> None:
        from app.engines.auth.constants import REDIS_FAILED_ATTEMPTS_PREFIX
        await self.redis.delete(f"{REDIS_FAILED_ATTEMPTS_PREFIX}{email.lower()}")

    async def _security_policy_value(self, key: str, default: Any) -> Any:
        """Resolve a runtime Security workspace policy with a safe fallback."""
        try:
            from app.engines.security.models import SecurityPolicy
            result = await self.db.execute(select(SecurityPolicy.policy_value_json).where(
                SecurityPolicy.policy_key == key))
            value = result.scalar_one_or_none()
            return default if value is None else value
        except Exception:
            return default

    async def _session_expires_at(self) -> datetime:
        minutes = int(await self._security_policy_value("session_max_lifetime_minutes", 1440))
        return utcnow() + timedelta(minutes=max(15, min(minutes, 43200)))

    async def _ensure_required_admin_mfa(self, user: User) -> None:
        if user.role == "super_admin":
            policy_key = "mfa_required_super_admin"
        elif user.role.startswith("admin_"):
            policy_key = "mfa_required_platform_admin"
        else:
            return
        if bool(await self._security_policy_value(policy_key, False)) and not user.is_mfa_enabled:
            raise ServiceOSException(
                "MFA_ENROLLMENT_REQUIRED",
                "Multi-factor authentication is required for this administrator account.",
                resolution="Ask a Super Admin to complete MFA enrollment before enabling this policy.",
            )

    async def _enforce_concurrent_session_limit(self, user_id: uuid.UUID) -> None:
        """Revoke the oldest sessions after every successful authentication."""
        maximum = int(await self._security_policy_value("max_concurrent_sessions", 10))
        maximum = max(1, min(maximum, 100))
        result = await self.db.execute(select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        ).order_by(UserSession.last_active_at.desc(), UserSession.id.desc()).offset(maximum))
        for stale in result.scalars().all():
            stale.revoked_at = utcnow()
            stale.revoke_reason = "Concurrent session limit enforced"
            try:
                await self.redis.setex(
                    f"serviceos:session:revoked:{stale.id}",
                    ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
            except Exception:
                pass

    async def _publish_event(self, event_type: str, entity_id: str, payload: dict,
                              tenant_id: str | None = None, actor_id: str | None = None) -> None:
        try:
            from app.core.events import get_event_bus, DomainEvent
            bus = get_event_bus()
            await bus.publish_raw(
                event_type=event_type, engine_id="auth",
                tenant_id=tenant_id or "platform",
                entity_type="user", entity_id=entity_id,
                payload=payload, actor_id=actor_id,
            )
        except Exception as e:
            logger.warning("auth.event_publish_failed", error=str(e), event_type=event_type)

    async def _get_staff_permissions(self, user_id: uuid.UUID) -> dict[str, bool]:
        r = await self.db.execute(
            select(StaffPermission).where(StaffPermission.user_id == user_id)
        )
        overrides = r.scalars().all()
        return {p.permission_key: p.is_granted for p in overrides}

    async def _build_token_pair(
        self,
        user: User,
        session: UserSession,
        enabled_engines: list[str],
        tenant_name: str | None = None,
        plan_type: str | None = None,
        extra_claims: dict | None = None,
    ) -> dict[str, Any]:
        """Creates access + refresh token pair. Stores refresh in DB."""
        # Load staff permission overrides for the JWT
        staff_perms = {}
        if user.role == "staff":
            staff_perms = await self._get_staff_permissions(user.id)

        access_token, jti = create_access_token(
            user_id=str(user.id),
            email=user.email,
            role=user.role,
            tenant_id=str(user.tenant_id) if user.tenant_id else None,
            tenant_name=tenant_name,
            plan_type=plan_type,
            session_id=str(session.id),
            device_id=session.device_id,
            is_mfa_enabled=user.is_mfa_enabled,
            onboarding_complete=user.onboarding_complete,
            enabled_engines=enabled_engines,
            extra_claims={
                "force_password_change": user.force_password_change,
                "full_name": user.full_name,
                "is_verified": user.is_verified,
                "permission_overrides": staff_perms,
                "access_scope": getattr(user, "access_scope", None),
                **(extra_claims or {}),
            },
        )

        # Refresh token family
        family = RefreshTokenFamily(user_id=user.id, session_id=session.id)
        self.db.add(family)
        await self.db.flush()

        raw_refresh, refresh_jti, hashed_refresh = create_refresh_token()
        rt = RefreshToken(
            family_id=family.id,
            user_id=user.id,
            jti=refresh_jti,
            hashed_token=hashed_refresh,
            expires_at=utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(rt)

        return {
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "jti": jti,
            "family_id": str(family.id),
        }

    def _user_to_profile(self, user: User, permissions: list[str] | None = None) -> dict:
        return {
            "user_id": str(user.id),
            "id": str(user.id),
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "display_name": getattr(user, "display_name", None),
            "language": getattr(user, "language", "en") or "en",
            "timezone": getattr(user, "timezone", "UTC") or "UTC",
            "role": user.role,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "is_verified": user.is_verified,
            "is_mfa_enabled": user.is_mfa_enabled,
            "is_active": user.is_active,
            "onboarding_complete": user.onboarding_complete,
            "force_password_change": user.force_password_change,
            "password_reset_required": getattr(user, "password_reset_required", False),
            "temporary_password_active": getattr(user, "temporary_password_active", False),
            "password_changed_at": user.password_changed_at.isoformat() if user.password_changed_at else None,
            "avatar_url": user.avatar_url,
            "profile_photo_media_id": str(user.profile_photo_media_id) if getattr(user, "profile_photo_media_id", None) else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat(),
            "permissions": permissions or ROLE_PERMISSIONS.get(user.role, []),
        }

    async def _tenant_to_ctx(self, tenant_id: uuid.UUID | None) -> dict | None:
        if not tenant_id:
            return None
        r = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = r.scalar_one_or_none()
        if not tenant:
            return None
        return {
            "id": str(tenant.id),
            "name": tenant.tenant_name,
            "vertical": tenant.vertical,
            "city": tenant.city,
            "plan_type": tenant.plan_type,
            "health_score": float(tenant.health_score),
        }

    # ── Registration ──────────────────────────────────────────────────────────
    async def register_customer(
        self,
        full_name: str,
        phone: str,
        email: str | None,
        tenant_id: uuid.UUID | None,
        source_id: str | None = None,
    ) -> dict:
        # Check if phone already registered
        existing = await self._get_user_by_phone(phone)
        if existing:
            raise ServiceOSException(
                "ALREADY_EXISTS",
                "An account with this phone number already exists.",
                resolution="Log in at POST /v1/auth/login/phone",
            )
        user = User(
            email=email or f"customer_{uuid.uuid4().hex[:8]}@serviceos.internal",
            phone=phone,
            full_name=full_name,
            role="customer",
            tenant_id=tenant_id,
            is_active=True,
            is_verified=False,
        )
        self.db.add(user)
        await self.db.flush()

        otp_result = await self.send_phone_otp(
            phone,
            "phone_login",
            source_id=source_id or f"customer-register:{user.id}",
        )
        await self._audit("user.registered", "success", actor_id=user.id,
                          tenant_id=tenant_id, target_id=user.id, target_type="user")
        await self._publish_event("auth.user_registered", str(user.id),
                                   {"email": user.email, "phone": phone})
        logger.info("auth.customer_registered", user_id=str(user.id))
        return {
            "user_id": str(user.id),
            "message": "OTP sent to your phone. Verify to activate your account.",
            **({"otp_hint": otp_result["otp_hint"]} if otp_result.get("otp_hint") else {}),
        }

    # ── Login ─────────────────────────────────────────────────────────────────
    async def login(
        self,
        email: str,
        password: str,
        device_id: str,
        device_name: str | None,
        user_agent: str | None,
        enabled_engines: list[str] | None = None,
        tenant_name: str | None = None,
        plan_type: str | None = None,
    ) -> dict:
        identifier = email.strip()
        user = (await self._get_user_by_phone(identifier)) if "@" not in identifier else (
            await self._get_user_by_email(identifier)
        )

        if not user:
            await self._audit("login.failed", "failure", failure_reason="user_not_found")
            raise ServiceOSException(
                "UNAUTHORIZED",
                "Invalid email or password.",
                resolution="Check your credentials and try again.",
            )

        # Lockout check
        if user.locked_until and isinstance(user.locked_until, datetime) and user.locked_until > utcnow():
            mins = max(1, int((user.locked_until - utcnow()).total_seconds() / 60))
            raise ServiceOSException(
                "ACCOUNT_LOCKED",
                f"Account is locked due to too many failed attempts. Try again in {mins} minute(s).",
                resolution=f"Wait {mins} minutes or contact support to unlock your account.",
                context={"locked_until": user.locked_until.isoformat()},
            )

        if not user.is_active:
            raise ServiceOSException(
                "UNAUTHORIZED",
                "This account has been deactivated.",
                resolution="Contact your administrator.",
            )

        # Runtime thresholds are owned by Admin -> Security Policies.
        warning_threshold = int(await self._security_policy_value(
            "failed_login_threshold", MAX_FAILED_LOGIN_ATTEMPTS))
        hard_threshold = int(await self._security_policy_value(
            "auto_lock_threshold", HARD_LOCKOUT_ATTEMPTS))

        # Verify password
        if not verify_password(password, user.hashed_password or ""):
            count = await self._increment_failed(email)
            if count >= hard_threshold:
                user.locked_until = utcnow() + timedelta(days=365)
                await self._audit("account.locked_permanent", "warning", actor_id=user.id)
                await self._publish_event("auth.account_locked", str(user.id),
                                           {"reason": "too_many_attempts", "count": count})
            elif count >= warning_threshold:
                user.locked_until = utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                await self._audit("account.locked_temp", "warning", actor_id=user.id)
            user.last_failed_login_at = utcnow()
            await self._audit("login.failed", "failure", actor_id=user.id,
                              failure_reason="wrong_password",
                              metadata={"attempt": count})
            await self._log_login_event(
                "login_failed", user_id=user.id,
                email_attempted=email, tenant_id=user.tenant_id,
                failure_reason="wrong_password", device_id=device_id, user_agent=user_agent,
            )
            raise ServiceOSException(
                "UNAUTHORIZED",
                f"Invalid email or password. {max(0, warning_threshold - count)} attempt(s) remaining before lockout.",
                resolution="Check your password and try again.",
            )

        # Clear lockout on success
        await self._clear_failed(email)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = utcnow()

        # MFA policy is enforced on every administrator login path.
        await self._ensure_required_admin_mfa(user)
        if user.is_mfa_enabled:
            challenge = create_mfa_challenge_token(str(user.id), user.email)
            await self._audit("login.mfa_required", "pending", actor_id=user.id,
                              tenant_id=user.tenant_id)
            # Login Activity phase: previously only password success/failure
            # and logout ever wrote a `login_events` row -- an MFA challenge
            # (a real, customer-relevant "additional verification required"
            # moment) was invisible in a customer's own login history.
            await self._log_login_event(
                "mfa_challenge_required", user_id=user.id,
                email_attempted=email, tenant_id=user.tenant_id,
                device_id=device_id, user_agent=user_agent,
            )
            return {"mfa_required": True, "mfa_challenge_token": challenge}

        # Create session
        dname, dtype = parse_device_info(user_agent)
        session = UserSession(
            user_id=user.id,
            tenant_id=user.tenant_id,
            device_id=device_id,
            device_name=device_name or dname,
            device_type=dtype,
            ip_address=self.ip_address,
            user_agent=user_agent,
            is_approved=True,
            expires_at=await self._session_expires_at(),
        )
        self.db.add(session)
        await self.db.flush()
        await self._enforce_concurrent_session_limit(user.id)

        tokens = await self._build_token_pair(user, session, enabled_engines or [], tenant_name, plan_type)
        await self._audit("login.success", "success", actor_id=user.id,
                          tenant_id=user.tenant_id, session_id=session.id)
        await self._log_login_event(
            "login_success", user_id=user.id,
            email_attempted=email, tenant_id=user.tenant_id,
            device_id=device_id, user_agent=user_agent,
        )
        await self._publish_event("auth.login_success", str(user.id),
                                   {"role": user.role, "device": device_name or dname},
                                   tenant_id=str(user.tenant_id) if user.tenant_id else None)
        logger.info("auth.login_success", user_id=str(user.id), role=user.role)

        requires_change = user.force_password_change or user.password_reset_required or user.temporary_password_active
        destination = await self.resolve_post_login_destination(user)
        return {
            "mfa_required": False,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"] if not requires_change else None,
            "force_password_change": user.force_password_change,
            "requires_password_change": requires_change,
            "password_change_reason": (
                "temporary_password" if user.temporary_password_active
                else "force_change" if user.force_password_change
                else "admin_reset" if user.password_reset_required
                else None
            ),
            "redirect_to": "/change-password-required" if requires_change else None,
            "user": self._user_to_profile(user),
            "tenant": await self._tenant_to_ctx(user.tenant_id),
            **destination,
        }

    # ── Phone OTP Login ───────────────────────────────────────────────────────
    async def send_phone_otp(
        self, phone: str, purpose: str, *, source_id: str | None = None
    ) -> dict:
        """
        Send OTP to phone.
        When Twilio Verify is configured: delegates to Verify API (no local OTP stored).
        Otherwise: generates OTP locally, stores hashed in DB, no SMS sent (dev mode).
        """
        await enforce_otp_send_limits(
            phone, ip_address=self.ip_address, source_id=source_id
        )
        from app.twilio_client import verify_send, is_verify_configured
        if is_verify_configured():
            sent = await verify_send(phone)
            logger.info("auth.otp_sent", purpose=purpose, phone=phone[:4] + "****",
                        method="twilio_verify", sent=sent)
            if not sent:
                raise ServiceOSException(
                    "SERVICE_UNAVAILABLE",
                    "We couldn't send the verification code. Please try again.",
                    status_code=503,
                )
            return {"message": "OTP sent to your phone via Twilio Verify.", "use_verify": True}

        # Fallback: self-managed OTP stored in DB
        recipient_hash = hash_recipient(phone)
        otp_plain, otp_hashed = generate_otp()
        otp_record = OTPRecord(
            purpose=purpose,
            recipient_hash=recipient_hash,
            hashed_otp=otp_hashed,
            expires_at=utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES),
        )
        self.db.add(otp_record)
        logger.info("auth.otp_sent", purpose=purpose, phone=phone[:4] + "****", method="db_fallback")
        return {
            "message": "OTP sent.",
            **({"otp_hint": otp_plain} if (
                self.settings.DEBUG
                or (
                    self.settings.APP_ENV != "production"
                    and getattr(self.settings, "MESSAGING_DEV_OTP_ENABLED", False)
                )
            ) else {}),
        }

    # ── Email OTP Login ───────────────────────────────────────────────────────
    EMAIL_OTP_PURPOSE = "email_login"

    async def send_email_otp(
        self, email: str, purpose: str = EMAIL_OTP_PURPOSE, *, source_id: str | None = None
    ) -> dict:
        """Email a sign-in code.

        `/otp/send` has advertised "phone or email" and accepted an `email` field since
        it was written, but the router passed `phone=body.phone or ""` and dropped the
        email on the floor -- so asking for an email code stored a record against an
        empty recipient and told the caller it had been sent. This is the real path.

        Enumeration-safe: the response is identical whether or not the address has an
        account, exactly like password reset. A sign-in form that reveals which emails
        are registered is an account list for anyone who asks.

        The code is only stored when there is a user to sign in, so an unknown address
        cannot fill the table with records nobody will ever use.
        """
        from app.email_client import is_email_configured, send_login_code_email

        normalized = email.lower().strip()
        await enforce_otp_send_limits(
            normalized,
            ip_address=self.ip_address,
            source_id=source_id,
            costed_delivery=False,
        )
        generic = {"message": "If an account exists, a sign-in code has been sent."}

        if not is_email_configured():
            # Refuse rather than pretend. A code the customer will never receive is
            # worse than no option at all, because they wait for it.
            raise ServiceOSException(
                "SERVICE_UNAVAILABLE",
                "Email sign-in codes are not available right now.",
                resolution="Sign in with your password or a phone code instead.",
            )

        user = await self._get_user_by_email(normalized)
        if not user or not user.is_active:
            logger.info("auth.email_otp_skipped", reason="no_active_user")
            return generic

        otp_plain, otp_hashed = generate_otp()
        self.db.add(OTPRecord(
            purpose=purpose,
            recipient_hash=hash_recipient(normalized),
            hashed_otp=otp_hashed,
            expires_at=utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES),
        ))
        await self.db.flush()

        sent = await send_login_code_email(normalized, otp_plain, OTP_EXPIRE_MINUTES)
        logger.info("auth.email_otp_sent", delivered=sent)
        if not sent:
            # Delivery failed after the record was written. Say so: the alternative is
            # a customer waiting on an email that is not coming.
            raise ServiceOSException(
                "SERVICE_UNAVAILABLE",
                "We couldn't send the code to that email. Please try again.",
                resolution="Sign in with your password or a phone code instead.",
            )
        # `otp_hint` mirrors the phone path's dev-only convenience and is gated on the
        # same DEBUG flag, so a production build never returns the code in the response.
        return {**generic, **({"otp_hint": otp_plain} if get_settings().DEBUG else {})}

    async def verify_email_otp_login(
        self, email: str, otp: str, device_id: str, device_name: str | None,
        user_agent: str | None, enabled_engines: list[str] | None = None,
        tenant_name: str | None = None, plan_type: str | None = None,
    ) -> dict:
        """Exchange an emailed code for a session.

        Mirrors `verify_phone_otp_login`, including its attempt limit and its
        enumeration-safe failures: an unknown address and a wrong code for a real one
        fail identically.
        """
        normalized = email.lower().strip()
        await enforce_otp_verify_limits(
            normalized, ip_address=self.ip_address, source_id=device_id
        )
        recipient_hash = hash_recipient(normalized)
        r = await self.db.execute(
            select(OTPRecord).where(
                and_(OTPRecord.purpose == self.EMAIL_OTP_PURPOSE,
                     OTPRecord.recipient_hash == recipient_hash,
                     OTPRecord.is_used == False,  # noqa: E712
                     OTPRecord.expires_at > utcnow())
            ).order_by(OTPRecord.created_at.desc()).limit(1)
        )
        otp_record = r.scalar_one_or_none()
        if not otp_record:
            raise ServiceOSException("UNAUTHORIZED", "Invalid or expired code.",
                                     resolution="Request a new code.")
        otp_record.attempts += 1
        if otp_record.attempts > 3:
            # Burned deliberately: three guesses at a 6-digit code is the whole
            # protection, and leaving it live would make brute force a matter of time.
            otp_record.is_used = True
            raise ServiceOSException("UNAUTHORIZED",
                                     "Too many incorrect attempts. Request a new code.")
        if not verify_otp(otp, otp_record.hashed_otp):
            raise ServiceOSException("UNAUTHORIZED", "Invalid or expired code.",
                                     resolution=f"{3 - otp_record.attempts} attempts remaining.")
        otp_record.is_used = True

        user = await self._get_user_by_email(normalized)
        if not user:
            # Only reachable if the account was removed between send and verify.
            raise ServiceOSException("UNAUTHORIZED", "Invalid or expired code.")
        if not user.is_active:
            raise ServiceOSException("UNAUTHORIZED", "Account is deactivated.")

        await self._ensure_required_admin_mfa(user)
        if user.is_mfa_enabled:
            challenge = create_mfa_challenge_token(str(user.id), user.email)
            await self._audit("login.mfa_required", "pending", actor_id=user.id,
                              tenant_id=user.tenant_id)
            await self._log_login_event(
                "mfa_challenge_required", user_id=user.id,
                email_attempted=normalized, tenant_id=user.tenant_id,
                device_id=device_id, user_agent=user_agent,
            )
            return {"mfa_required": True, "mfa_challenge_token": challenge}

        user.last_login_at = utcnow()
        # Holding the code proves the address, which is exactly what verification means.
        if not user.is_verified:
            user.is_verified = True

        dname, dtype = parse_device_info(user_agent)
        session = UserSession(
            user_id=user.id, tenant_id=user.tenant_id,
            device_id=device_id, device_name=device_name or dname,
            device_type=dtype, ip_address=self.ip_address,
            user_agent=user_agent, is_approved=True,
            expires_at=await self._session_expires_at(),
        )
        self.db.add(session)
        await self.db.flush()
        await self._enforce_concurrent_session_limit(user.id)

        tokens = await self._build_token_pair(user, session, enabled_engines or [], tenant_name, plan_type)
        await self._audit("login.email_otp_success", "success", actor_id=user.id,
                          tenant_id=user.tenant_id, session_id=session.id)
        await self._log_login_event(
            "login_success", user_id=user.id, tenant_id=user.tenant_id,
            device_id=device_id, user_agent=user_agent,
        )
        requires_change = user.force_password_change or user.password_reset_required or user.temporary_password_active
        return {
            "access_token": tokens["access_token"],
            # Keep the email-OTP path aligned with password-only login: accounts
            # under a mandatory password-change policy must not receive a
            # reusable refresh token before completing that change.
            "refresh_token": tokens["refresh_token"] if not requires_change else None,
            "user": self._user_to_profile(user),
            "tenant": await self._tenant_to_ctx(user.tenant_id),
            "force_password_change": user.force_password_change,
            "requires_password_change": requires_change,
            "password_change_reason": (
                "temporary_password" if user.temporary_password_active
                else "force_change" if user.force_password_change
                else "admin_reset" if user.password_reset_required
                else None
            ),
            "redirect_to": "/change-password-required" if requires_change else None,
            **(await self.resolve_post_login_destination(user)),
        }

    async def verify_phone_otp_login(
        self, phone: str, otp: str, device_id: str, device_name: str | None,
        user_agent: str | None, enabled_engines: list[str] | None = None,
        tenant_name: str | None = None, plan_type: str | None = None,
    ) -> dict:
        await enforce_otp_verify_limits(
            phone, ip_address=self.ip_address, source_id=device_id
        )
        from app.twilio_client import verify_check, is_verify_configured
        if is_verify_configured():
            approved = await verify_check(phone, otp)
            if not approved:
                raise ServiceOSException("UNAUTHORIZED", "Incorrect or expired OTP.",
                                         resolution="Request a new OTP.")
        else:
            # Fallback: check OTPRecord in DB
            recipient_hash = hash_recipient(phone)
            r = await self.db.execute(
                select(OTPRecord).where(
                    and_(OTPRecord.purpose == "phone_login",
                         OTPRecord.recipient_hash == recipient_hash,
                         OTPRecord.is_used == False,
                         OTPRecord.expires_at > utcnow())
                ).order_by(OTPRecord.created_at.desc()).limit(1)
            )
            otp_record = r.scalar_one_or_none()
            if not otp_record:
                raise ServiceOSException("UNAUTHORIZED", "OTP not found or expired.",
                                         resolution="Request a new OTP.")
            otp_record.attempts += 1
            if otp_record.attempts > 3:
                otp_record.is_used = True
                raise ServiceOSException("UNAUTHORIZED", "Too many incorrect OTP attempts. Request a new OTP.")
            if not verify_otp(otp, otp_record.hashed_otp):
                raise ServiceOSException("UNAUTHORIZED", "Incorrect OTP.",
                                         resolution=f"{3 - otp_record.attempts} attempts remaining.")
            otp_record.is_used = True

        user = await self._get_user_by_phone(phone)
        if not user:
            raise ServiceOSException("NOT_FOUND", "No account found with this phone number.")
        if not user.is_active:
            raise ServiceOSException("UNAUTHORIZED", "Account is deactivated.")

        await self._ensure_required_admin_mfa(user)
        if user.is_mfa_enabled:
            challenge = create_mfa_challenge_token(str(user.id), user.email)
            await self._audit("login.mfa_required", "pending", actor_id=user.id,
                              tenant_id=user.tenant_id)
            await self._log_login_event(
                "mfa_challenge_required", user_id=user.id,
                email_attempted=None, tenant_id=user.tenant_id,
                device_id=device_id, user_agent=user_agent,
            )
            return {"mfa_required": True, "mfa_challenge_token": challenge}

        user.last_login_at = utcnow()
        if not user.is_verified:
            user.is_verified = True

        dname, dtype = parse_device_info(user_agent)
        session = UserSession(
            user_id=user.id, tenant_id=user.tenant_id,
            device_id=device_id, device_name=device_name or dname,
            device_type=dtype, ip_address=self.ip_address,
            user_agent=user_agent, is_approved=True,
            expires_at=await self._session_expires_at(),
        )
        self.db.add(session)
        await self.db.flush()
        await self._enforce_concurrent_session_limit(user.id)

        tokens = await self._build_token_pair(user, session, enabled_engines or [], tenant_name, plan_type)
        await self._audit("login.phone_otp_success", "success", actor_id=user.id,
                          tenant_id=user.tenant_id, session_id=session.id)
        await self._log_login_event(
            "login_success", user_id=user.id, tenant_id=user.tenant_id,
            device_id=device_id, user_agent=user_agent,
        )
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "user": self._user_to_profile(user),
            "tenant": await self._tenant_to_ctx(user.tenant_id),
        }

    # ── MFA ───────────────────────────────────────────────────────────────────
    async def verify_mfa(
        self, mfa_challenge_token: str, code: str,
        device_id: str, device_name: str | None, user_agent: str | None,
        remember_device: bool = False,
        enabled_engines: list[str] | None = None,
        tenant_name: str | None = None, plan_type: str | None = None,
    ) -> dict:
        try:
            payload = decode_token(mfa_challenge_token)
            if payload.get("purpose") != "mfa_challenge":
                raise ValueError("wrong_purpose")
        except Exception:
            raise ServiceOSException("INVALID_TOKEN", "Invalid or expired MFA challenge token.",
                                     resolution="Log in again to get a new challenge token.")

        user = await self._get_user_by_id(uuid.UUID(payload["sub"]))
        if not user:
            raise ServiceOSException("NOT_FOUND", "User not found.")

        r = await self.db.execute(
            select(MFASecret).where(MFASecret.user_id == user.id, MFASecret.is_confirmed == True)
        )
        mfa_secret = r.scalar_one_or_none()
        if not mfa_secret:
            raise ServiceOSException("INTERNAL_ERROR", "MFA not configured correctly.")

        verified = False
        if len(code) == 6 and code.isdigit():
            verified = verify_totp(mfa_secret.encrypted_secret, code)
        else:
            # Try backup code
            r2 = await self.db.execute(
                select(MFABackupCode).where(
                    MFABackupCode.user_id == user.id, MFABackupCode.is_used == False
                )
            )
            for bc in r2.scalars().all():
                if verify_backup_code(code, bc.hashed_code):
                    bc.is_used = True
                    bc.used_at = utcnow()
                    verified = True
                    break

        if not verified:
            await self._audit("mfa.verify_failed", "failure", actor_id=user.id)
            raise ServiceOSException("UNAUTHORIZED", "Invalid MFA code.",
                                     resolution="Check your authenticator app for the current 6-digit code.")

        user.last_login_at = utcnow()
        dname, dtype = parse_device_info(user_agent)
        session = UserSession(
            user_id=user.id, tenant_id=user.tenant_id,
            device_id=device_id, device_name=device_name or dname,
            device_type=dtype, ip_address=self.ip_address,
            user_agent=user_agent,
            is_trusted=remember_device and device_id != "web",
            is_approved=True,
            expires_at=await self._session_expires_at(),
        )
        self.db.add(session)
        await self.db.flush()
        await self._enforce_concurrent_session_limit(user.id)

        tokens = await self._build_token_pair(user, session, enabled_engines or [], tenant_name, plan_type)
        await self._audit("mfa.verify_success", "success", actor_id=user.id, session_id=session.id)
        await self._log_login_event(
            "login_success", user_id=user.id, tenant_id=user.tenant_id,
            device_id=device_id, user_agent=user_agent,
        )
        requires_change = user.force_password_change or user.password_reset_required or user.temporary_password_active
        return {
            **(await self.resolve_post_login_destination(user)),
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"] if not requires_change else None,
            "user": self._user_to_profile(user),
            "tenant": await self._tenant_to_ctx(user.tenant_id),
            "force_password_change": user.force_password_change,
            "requires_password_change": requires_change,
            "password_change_reason": (
                "temporary_password" if user.temporary_password_active
                else "force_change" if user.force_password_change
                else "admin_reset" if user.password_reset_required
                else None
            ),
            "redirect_to": "/change-password-required" if requires_change else None,
        }

    async def setup_mfa(self, user_id: uuid.UUID) -> dict:
        user = await self._get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User", str(user_id))

        secret = generate_totp_secret()
        qr_uri = get_totp_uri(secret, user.email)
        plain_codes, hashed_codes = generate_backup_codes()

        r = await self.db.execute(select(MFASecret).where(MFASecret.user_id == user_id))
        mfa = r.scalar_one_or_none()
        if mfa:
            mfa.encrypted_secret = secret
            mfa.is_confirmed = False
            mfa.confirmed_at = None
        else:
            self.db.add(MFASecret(user_id=user_id, encrypted_secret=secret, is_confirmed=False))

        # Invalidate existing backup codes
        await self.db.execute(
            update(MFABackupCode).where(MFABackupCode.user_id == user_id).values(is_used=True)
        )
        for hc in hashed_codes:
            self.db.add(MFABackupCode(user_id=user_id, hashed_code=hc))

        await self._audit("mfa.setup_initiated", "success", actor_id=user_id)
        return {"secret": secret, "qr_uri": qr_uri, "backup_codes": plain_codes,
                "backup_codes_remaining": BACKUP_CODE_COUNT}

    async def confirm_mfa(self, user_id: uuid.UUID, code: str) -> dict:
        r = await self.db.execute(select(MFASecret).where(MFASecret.user_id == user_id))
        mfa = r.scalar_one_or_none()
        if not mfa:
            raise ServiceOSException("NOT_FOUND", "MFA setup not initiated. Call POST /v1/auth/mfa/setup first.")
        if not verify_totp(mfa.encrypted_secret, code):
            raise ServiceOSException("UNAUTHORIZED", "Invalid code.",
                                     resolution="Check your authenticator app for the current code.")
        mfa.is_confirmed = True
        mfa.confirmed_at = utcnow()
        user = await self._get_user_by_id(user_id)
        if user:
            user.is_mfa_enabled = True
        await self._audit("mfa.enabled", "success", actor_id=user_id,
                          tenant_id=user.tenant_id if user else None)
        await self._publish_event("auth.mfa_enabled", str(user_id), {})
        return {"mfa_enabled": True, "message": "MFA is now active on your account."}

    async def disable_mfa(self, user_id: uuid.UUID, password: str, code: str) -> dict:
        user = await self._get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User", str(user_id))
        if not verify_password(password, user.hashed_password or ""):
            raise ServiceOSException("UNAUTHORIZED", "Incorrect password.")
        r = await self.db.execute(
            select(MFASecret).where(MFASecret.user_id == user_id, MFASecret.is_confirmed == True)
        )
        mfa = r.scalar_one_or_none()
        if not mfa or not verify_totp(mfa.encrypted_secret, code):
            raise ServiceOSException("UNAUTHORIZED", "Invalid MFA code.",
                                     resolution="You must provide a valid TOTP code to disable MFA.")
        if user.mfa_required:
            raise ServiceOSException(
                "MFA_POLICY_REQUIRED",
                "MFA cannot be disabled for this account — it is required by policy.",
                resolution="Contact your administrator to change this account's MFA policy.",
                status_code=422,
            )
        user.is_mfa_enabled = False
        mfa.is_confirmed = False
        await self._audit("mfa.disabled", "success", actor_id=user_id, tenant_id=user.tenant_id)
        return {"mfa_enabled": False, "message": "MFA has been disabled."}

    async def regenerate_backup_codes(self, user_id: uuid.UUID, code: str) -> dict:
        """Regenerate backup codes — requires current TOTP code to prevent abuse."""
        r = await self.db.execute(
            select(MFASecret).where(MFASecret.user_id == user_id, MFASecret.is_confirmed == True)
        )
        mfa = r.scalar_one_or_none()
        if not mfa or not verify_totp(mfa.encrypted_secret, code):
            raise ServiceOSException("UNAUTHORIZED", "Invalid MFA code.")
        await self.db.execute(
            update(MFABackupCode).where(MFABackupCode.user_id == user_id).values(is_used=True)
        )
        plain, hashed = generate_backup_codes()
        for hc in hashed:
            self.db.add(MFABackupCode(user_id=user_id, hashed_code=hc))
        await self._audit("mfa.backup_codes_regenerated", "success", actor_id=user_id)
        return {"backup_codes": plain,
                "message": "New backup codes generated. Previous codes are now invalid."}

    # ── Token Management ──────────────────────────────────────────────────────
    async def refresh_token(self, raw_token: str) -> dict:
        hashed = hash_token(raw_token)
        r = await self.db.execute(
            select(RefreshToken).where(RefreshToken.hashed_token == hashed)
        )
        rt = r.scalar_one_or_none()

        if not rt:
            raise ServiceOSException("INVALID_TOKEN", "Refresh token not found.",
                                     resolution="Log in again.")

        if rt.is_used:
            # THEFT DETECTED — invalidate entire family
            family_r = await self.db.execute(
                select(RefreshTokenFamily).where(RefreshTokenFamily.id == rt.family_id)
            )
            family = family_r.scalar_one_or_none()
            if family and not family.is_invalidated:
                family.invalidate("theft_detected")
                await self.db.execute(
                    update(RefreshToken)
                    .where(RefreshToken.family_id == rt.family_id)
                    .values(revoked_at=utcnow())
                )
                # Also revoke the session
                await self.db.execute(
                    update(UserSession)
                    .where(UserSession.id == family.session_id)
                    .values(revoked_at=utcnow())
                )
            await self._audit("token.theft_detected", "warning", actor_id=rt.user_id,
                              metadata={"family_id": str(rt.family_id)})
            await self._publish_event("auth.token_theft_detected", str(rt.user_id),
                                       {"family_id": str(rt.family_id)})
            logger.warning("auth.refresh_token_theft", user_id=str(rt.user_id))
            raise ServiceOSException(
                "TOKEN_BLACKLISTED",
                "Security alert: token reuse detected. All sessions have been invalidated for your protection.",
                resolution="Log in again. If you did not do this, your account may be compromised.",
            )

        if rt.expires_at < utcnow() or rt.revoked_at:
            raise ServiceOSException("TOKEN_EXPIRED", "Refresh token has expired.",
                                     resolution="Log in again to get a new token.")

        # Mark as used (one-time)
        rt.is_used = True
        rt.used_at = utcnow()

        user = await self._get_user_by_id(rt.user_id)
        if not user or not user.is_active:
            raise ServiceOSException("UNAUTHORIZED", "Account is not accessible.")

        # Get session
        family_r = await self.db.execute(
            select(RefreshTokenFamily).where(RefreshTokenFamily.id == rt.family_id)
        )
        family = family_r.scalar_one_or_none()
        if not family or family.is_invalidated:
            raise ServiceOSException("UNAUTHORIZED", "Session has been invalidated.")

        session_r = await self.db.execute(
            select(UserSession).where(UserSession.id == family.session_id)
        )
        session = session_r.scalar_one_or_none()
        if not session or session.revoked_at:
            raise ServiceOSException("UNAUTHORIZED", "Session has been revoked.")
        if session.expires_at and session.expires_at <= utcnow():
            session.revoked_at = utcnow()
            session.revocation_reason = "maximum_lifetime_exceeded"
            raise ServiceOSException("UNAUTHORIZED", "Session has expired. Log in again.")
        idle_minutes = int(await self._security_policy_value("idle_timeout_minutes", 30))
        if session.last_active_at and session.last_active_at <= utcnow() - timedelta(minutes=idle_minutes):
            session.revoked_at = utcnow()
            session.revocation_reason = "idle_timeout_exceeded"
            raise ServiceOSException("UNAUTHORIZED", "Session expired after inactivity. Log in again.")

        session.last_active_at = utcnow()

        # Issue new refresh token in same family
        raw_new, new_jti, hashed_new = create_refresh_token()
        self.db.add(RefreshToken(
            family_id=rt.family_id,
            user_id=user.id,
            jti=new_jti,
            hashed_token=hashed_new,
            expires_at=utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        ))

        # New access token
        staff_perms = await self._get_staff_permissions(user.id) if user.role == "staff" else {}
        access_token, jti = create_access_token(
            user_id=str(user.id), email=user.email, role=user.role,
            tenant_id=str(user.tenant_id) if user.tenant_id else None,
            tenant_name=None, plan_type=None,
            session_id=str(session.id), device_id=session.device_id,
            is_mfa_enabled=user.is_mfa_enabled,
            onboarding_complete=user.onboarding_complete,
            enabled_engines=[],
            extra_claims={"force_password_change": user.force_password_change,
                          "full_name": user.full_name, "is_verified": user.is_verified,
                          "permission_overrides": staff_perms,
                          "access_scope": getattr(user, "access_scope", None)},
        )
        return {"access_token": access_token, "refresh_token": raw_new}

    async def logout(self, jti: str, session_id: str, user_id: str) -> None:
        await self._blacklist(jti)
        try:
            r = await self.db.execute(
                select(UserSession).where(UserSession.id == uuid.UUID(session_id))
            )
            session = r.scalar_one_or_none()
            if session:
                session.revoked_at = utcnow()
        except Exception:
            pass
        await self._audit("session.logout", "success",
                          actor_id=uuid.UUID(user_id) if user_id else None)
        await self._log_login_event(
            "logout",
            user_id=uuid.UUID(user_id) if user_id else None,
            device_id=None,
        )
        await self._publish_event("auth.logout", user_id, {"session_id": session_id})

    async def logout_all(
        self, user_id: str, current_jti: str, exclude_session_id: uuid.UUID | None = None,
    ) -> int:
        """Revoke every active session for `user_id`.

        BUG FIX (Manage Sessions phase): `exclude_session_id` previously
        didn't exist -- the ONLY lever callers had was `current_jti`
        (blacklist-or-not), but the actual SESSION revocation query had no
        exclusion filter at all, so it wiped every session unconditionally
        regardless of what jti was passed. `/v1/auth/sessions/revoke-all-
        other`'s own docstring promised "except the current one" while its
        implementation revoked literally everything, including the caller's
        own session -- confirmed via direct read, not assumed. Full global
        logout (`/v1/auth/logout-all`) still passes no exclusion (revokes
        everything, matching that endpoint's own contract); the
        revoke-all-other endpoint now passes the real current session id.
        """
        uid = uuid.UUID(user_id)
        conditions = [UserSession.user_id == uid, UserSession.revoked_at == None]
        if exclude_session_id is not None:
            conditions.append(UserSession.id != exclude_session_id)
        r = await self.db.execute(select(UserSession).where(and_(*conditions)))
        sessions = r.scalars().all()
        count = 0
        for session in sessions:
            session.revoked_at = utcnow()
            count += 1
        if exclude_session_id is None:
            # Full logout: also blacklist the current access token's jti so
            # it stops passing auth checks immediately, not just at its
            # natural TTL expiry.
            await self._blacklist(current_jti)
        await self._audit("session.logout_all", "success", actor_id=uid,
                          metadata={"sessions_revoked": count, "excluded_current": exclude_session_id is not None})
        await self._publish_event("auth.logout_all", user_id, {"sessions_revoked": count})
        return count

    async def introspect_token(self, token: str) -> dict:
        """Validate a token and return its claims (for internal service-to-service use)."""
        try:
            payload = decode_token(token)
            jti = payload.get("jti", "")
            if await self._is_blacklisted(jti):
                return {"active": False}
            return {
                "active": True,
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "role": payload.get("role"),
                "tenant_id": payload.get("tenant_id"),
                "jti": jti,
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc).isoformat(),
                "is_impersonation": payload.get("is_impersonation", False),
            }
        except Exception:
            return {"active": False}

    # ── Sessions ──────────────────────────────────────────────────────────────
    @staticmethod
    def _channel_for(device_type: str) -> str:
        """Derived from the real stored `device_type` (see `parse_device_info`)
        -- never fabricated. `device_type` values map cleanly to a coarse
        channel; anything else is honestly reported as "Web"."""
        return {"mobile": "Mobile", "tablet": "Mobile", "desktop": "Web"}.get(device_type, "Web")

    async def list_sessions(self, user_id: uuid.UUID, current_session_id: uuid.UUID | None) -> list[dict]:
        """`current_session_id` (Manage Sessions phase) is the authoritative
        session id carried in the access token's own claims -- NOT a
        device_id comparison. Multiple sessions can legitimately share a
        device_id (reinstall, cleared storage), so device_id equality was
        never a reliable "this is the request that's asking" signal; the
        token's own `session_id` claim is.

        Customer-facing fields are an explicit allowlist -- `ip_address`
        (full IP) is intentionally NOT included; no geo-lookup capability
        exists in this codebase, so no approximate-location field is
        fabricated either."""
        r = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at == None,
            ).order_by(UserSession.last_active_at.desc())
        )
        sessions = r.scalars().all()
        return [
            {
                "session_id": str(s.id),
                "device_name": s.device_name,
                "device_type": s.device_type,
                "channel": self._channel_for(s.device_type),
                "last_active_at": s.last_active_at.isoformat(),
                "created_at": s.created_at.isoformat(),
                "is_current": current_session_id is not None and s.id == current_session_id,
                "is_trusted": s.is_trusted,
            }
            for s in sessions
        ]

    async def get_mobile_security_summary(
        self, user_id: uuid.UUID, current_session_id: uuid.UUID | None,
        current_device_id: str | None = None,
    ) -> dict:
        """Technician mobile app Phase V -- composed entirely over real,
        existing data (User row + list_sessions' own live session query),
        never a fabricated status. Found deleted from source entirely
        during the "make it 100% working" pass despite a real, passing
        pytest suite existing for it; rebuilt to the exact shape that
        suite already proves against real data.

        Staff-app full-audit finding: the previously "rebuilt" shape above
        only covered `verified_contacts.masked_*`/`mfa.enabled+required`/
        `current_device.session_id+trusted`/`active_session_count`/
        `security_status.level+reasons` -- but SecurityScreen.tsx (and
        TrustedDeviceScreen.tsx) also read `password.*`, `mfa.method`/
        `enabled_at`/`recovery_codes_remaining`/`required_by_policy`,
        `current_device.device_name`/`last_active_at`,
        `verified_contacts.mobile_verified`/`email_verified`,
        `security_status.label`, and `recent_activity` -- none of which
        this endpoint ever returned, so those sections silently rendered
        undefined/blank. Every added field below is sourced from real,
        already-existing data (User row, the session dict already computed
        by list_sessions(), MFASecret/MFABackupCode rows, the same
        LOGIN_EVENT query get_my_login_activity uses) -- nothing fabricated."""
        from sqlalchemy import func as _func
        user = await self.db.get(User, user_id)
        if not user:
            raise ServiceOSException("NOT_FOUND", "User not found.", status_code=404)

        def _mask_phone(phone: str | None) -> str | None:
            if not phone or len(phone) < 5:
                return None
            return "•" * 5 + " " + phone[-5:]

        def _mask_email(email: str | None) -> str | None:
            if not email or "@" not in email:
                return None
            local, _, domain = email.partition("@")
            first = local[0] if local else "*"
            return f"{first}***@{domain}"

        sessions = await self.list_sessions(user_id, current_session_id)
        current = next((s for s in sessions if s["is_current"]), None)
        active_session_count = len(sessions)

        if user.is_mfa_enabled:
            level, reasons = "protected", []
            label = "Your account is protected"
        elif user.recovery_email or user.recovery_phone:
            level, reasons = "protection_recommended", ["mfa_not_enabled"]
            label = "Turn on two-step verification for extra protection"
        else:
            level, reasons = "action_required", ["mfa_not_enabled", "no_recovery_contact"]
            label = "Your account needs attention"

        mfa_enabled_at = None
        recovery_codes_remaining = None
        if user.is_mfa_enabled:
            secret = (await self.db.execute(
                select(MFASecret).where(MFASecret.user_id == user_id)
            )).scalar_one_or_none()
            mfa_enabled_at = secret.confirmed_at.isoformat() if secret and secret.confirmed_at else None
            recovery_codes_remaining = await self.db.scalar(
                select(_func.count()).select_from(MFABackupCode).where(
                    MFABackupCode.user_id == user_id, MFABackupCode.is_used == False,
                )
            )

        # Same event query/mapping as get_my_login_activity, just capped
        # short for an inline "recent activity" preview rather than the
        # full paginated feed.
        r = await self.db.execute(
            select(LoginEvent).where(LoginEvent.user_id == user_id)
            .order_by(LoginEvent.created_at.desc(), LoginEvent.id.desc()).limit(5)
        )
        recent_activity = []
        for e in r.scalars().all():
            evt_label, outcome = LOGIN_EVENT_PUBLIC_MAP.get(
                e.event_type, (LOGIN_EVENT_UNKNOWN_LABEL, LOGIN_EVENT_UNKNOWN_OUTCOME)
            )
            device_name, device_type = parse_device_info(e.user_agent)
            recent_activity.append({
                "event_id": str(e.id), "label": evt_label, "outcome": outcome,
                "channel": self._channel_for(device_type), "device_name": device_name,
                "is_current_device": bool(current_device_id) and e.device_id == current_device_id,
                "occurred_at": e.created_at.isoformat(),
            })

        return {
            "verified_contacts": {
                "masked_mobile": _mask_phone(user.phone),
                "mobile_verified": user.is_verified,
                "masked_email": _mask_email(user.email),
                "email_verified": user.is_verified,
            },
            "password": {
                "configured": bool(user.hashed_password),
                "changed_at": user.password_changed_at.isoformat() if user.password_changed_at else None,
                "change_allowed": True,
            },
            "mfa": {
                "enabled": user.is_mfa_enabled,
                "method": "totp" if user.is_mfa_enabled else None,
                "enabled_at": mfa_enabled_at,
                "recovery_codes_remaining": recovery_codes_remaining,
                "required_by_policy": user.mfa_required,
            },
            "current_device": {
                "session_id": current["session_id"] if current else None,
                "trusted": current["is_trusted"] if current else None,
                "device_name": current["device_name"] if current else None,
                "last_active_at": current["last_active_at"] if current else None,
            },
            "active_session_count": active_session_count,
            "security_status": {"level": level, "label": label, "reasons": reasons},
            "recent_activity": recent_activity,
        }

    async def revoke_session(
        self, session_id: uuid.UUID, requesting_user_id: uuid.UUID,
        current_session_id: uuid.UUID | None = None,
    ) -> None:
        r = await self.db.execute(select(UserSession).where(UserSession.id == session_id))
        session = r.scalar_one_or_none()
        # Enumeration-safe (Account Security phase): a session that doesn't
        # exist and one that belongs to another customer previously raised
        # different error shapes (404 NOT_FOUND vs 403 PERMISSION_DENIED),
        # letting a caller distinguish "no such session" from "exists but
        # not mine" by probing session IDs. Both now raise the identical
        # generic 404 SESSION_NOT_FOUND.
        if not session or session.user_id != requesting_user_id:
            raise ServiceOSException("SESSION_NOT_FOUND", f"Session '{session_id}' not found.",
                                     status_code=404)
        if current_session_id is not None and session_id == current_session_id:
            raise ServiceOSException(
                "CANNOT_REVOKE_CURRENT_SESSION",
                "You cannot revoke the session you're currently using here.",
                resolution="Log out to end this session instead.",
                status_code=422,
            )
        if session.revoked_at is not None:
            return  # idempotent -- already revoked
        session.revoked_at = utcnow()
        session.is_trusted = False

        try:
            await self.redis.setex(
                f"serviceos:session:revoked:{session_id}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
        except Exception:
            pass

        # Web and legacy sessions do not necessarily have an associated push
        # device.  Revoking the authentication session must still succeed;
        # only revoke a push registration when a concrete device is linked.
        session_device_id = getattr(session, "device_id", None)
        if session_device_id:
            from app.engines.platform_notifications.push_device_models import StaffPushDevice
            await self.db.execute(
                update(StaffPushDevice)
                .where(StaffPushDevice.user_id == requesting_user_id,
                       StaffPushDevice.device_id == session_device_id,
                       StaffPushDevice.revoked_at.is_(None))
                .values(revoked_at=utcnow())
            )

        await self._audit("session.revoked", "success", actor_id=requesting_user_id,
                          target_id=session_id, target_type="session")
        await self.db.commit()

    async def remove_session_trust(
        self, session_id: uuid.UUID, requesting_user_id: uuid.UUID,
    ) -> dict:
        """Clears UserSession.is_trusted WITHOUT revoking the session -- a
        real gap found by the staff-app API audit: the mobile Trusted
        Device screen (and its confirmation copy: "you may be asked to
        verify with a code more often, afterward" -- explicitly promising
        the device STAYS signed in) called POST .../devices/{id}/remove-
        trust, but no such endpoint existed. The only place `is_trusted`
        was ever cleared was as a side effect of full revoke_session()
        above, which would have silently logged the device out instead --
        the opposite of what the screen promises. This is the narrow,
        real operation the UI actually describes."""
        r = await self.db.execute(select(UserSession).where(UserSession.id == session_id))
        session = r.scalar_one_or_none()
        # Enumeration-safe, matching revoke_session's convention above.
        if not session or session.user_id != requesting_user_id:
            raise ServiceOSException("SESSION_NOT_FOUND", f"Session '{session_id}' not found.",
                                     status_code=404)
        if session.revoked_at is not None:
            raise ServiceOSException("SESSION_NOT_FOUND", f"Session '{session_id}' not found.",
                                     status_code=404)
        session.is_trusted = False
        await self._audit("session.trust_removed", "success", actor_id=requesting_user_id,
                          target_id=session_id, target_type="session")
        await self.db.commit()
        return {"session_id": str(session_id), "is_trusted": False}

    async def get_sessions_projection(
        self, user_id: uuid.UUID, current_session_id: uuid.UUID | None,
        current_device_id: str | None,
    ) -> dict:
        """Richer 'Manage Sessions' projection for GET /v1/auth/sessions.
        Resolves "current" via the token's own session_id claim when present;
        falls back to device_id match only when no session_id claim is
        available on the request context (device_id can legitimately repeat
        across reinstalls, so it's a fallback, never the primary signal)."""
        r = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at == None,
            ).order_by(UserSession.last_active_at.desc())
        )
        rows = r.scalars().all()

        resolved_current_id = None
        if current_session_id is not None and any(s.id == current_session_id for s in rows):
            resolved_current_id = current_session_id
        elif current_device_id:
            match = next((s for s in rows if s.device_id == current_device_id), None)
            if match:
                resolved_current_id = match.id

        sessions = []
        trusted_count = 0
        for s in rows:
            if s.is_trusted:
                trusted_count += 1
            is_current = s.id == resolved_current_id
            device_display_name = s.device_name or f"Unknown {s.device_type or 'device'}"
            sessions.append({
                "session_id": str(s.id),
                "device_display_name": device_display_name,
                "device_type": s.device_type,
                "channel": self._channel_for(s.device_type),
                "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
                "created_at": s.created_at.isoformat(),
                "is_current": is_current,
                "is_trusted": s.is_trusted,
                "allowed_actions": (["view", "remove_trust"] if is_current else ["view", "revoke"]),
                # No geo-lookup capability exists in this codebase --
                # never fabricate an approximate location.
                "approximate_location": None,
            })

        return {
            "sessions": sessions,
            "total": len(sessions),
            "current_session_id": str(resolved_current_id) if resolved_current_id else None,
            "trusted_device_count": trusted_count,
        }

    async def approve_device(
        self, session_id: uuid.UUID, approving_user_id: uuid.UUID, approving_role: str
    ) -> dict:
        """Tenant owner approves a new staff device."""
        if approving_role not in ("super_admin", "tenant_owner"):
            raise PermissionDeniedException("tenant_owner", approving_role)
        r = await self.db.execute(select(UserSession).where(UserSession.id == session_id))
        session = r.scalar_one_or_none()
        if not session:
            raise NotFoundException("Session", str(session_id))
        session.is_approved = True
        await self._audit("device.approved", "success",
                          actor_id=approving_user_id, target_id=session_id, target_type="session",
                          metadata={"device_name": session.device_name})
        await self._publish_event("auth.device_approved", str(session.user_id),
                                   {"device_name": session.device_name, "session_id": str(session.id)})
        return {"session_id": str(session.id), "device_name": session.device_name,
                "is_approved": True}

    # ── Password ──────────────────────────────────────────────────────────────
    async def change_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str,
        current_session_id: uuid.UUID | None = None,
    ) -> int:
        user = await self._get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User", str(user_id))
        if not verify_password(current_password, user.hashed_password or ""):
            raise ServiceOSException("UNAUTHORIZED", "Current password is incorrect.")
        errors = validate_password_strength(new_password, user.full_name, user.email)
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors))
        new_hash = hash_password(new_password)
        history = user.password_history or []
        for old_hash in history:
            if verify_password(new_password, old_hash):
                raise ServiceOSException(
                    "VALIDATION_ERROR",
                    f"Cannot reuse any of your last {PASSWORD_HISTORY_COUNT} passwords.",
                )
        user.hashed_password = new_hash
        user.password_history = ([new_hash] + history)[:PASSWORD_HISTORY_COUNT]
        user.password_changed_at = utcnow()
        user.force_password_change = False
        user.password_reset_required = False
        user.temporary_password_active = False

        # SECURITY (Account Security phase): a password change is exactly
        # the moment a compromised session should be cut off elsewhere --
        # previously this silently left every other session alive. The
        # session that just authenticated this request is preserved (the
        # customer does not need to re-login for the device they're on).
        revoke_conditions = [UserSession.user_id == user_id, UserSession.revoked_at == None]
        if current_session_id is not None:
            revoke_conditions.append(UserSession.id != current_session_id)
        result = await self.db.execute(
            update(UserSession).where(and_(*revoke_conditions)).values(revoked_at=utcnow())
        )
        sessions_revoked = result.rowcount or 0

        await self._audit("auth.password_changed", "success", actor_id=user_id,
                          tenant_id=user.tenant_id,
                          metadata={"reason": "user_initiated", "other_sessions_revoked": sessions_revoked})
        await self._publish_event("auth.password_changed", str(user_id), {},
                                   tenant_id=str(user.tenant_id) if user.tenant_id else None)
        return sessions_revoked

    async def request_password_reset(self, email: str | None, phone: str | None) -> dict:
        recipient = (email or phone or "").strip().lower()
        if not recipient:
            raise ServiceOSException(
                "VALIDATION_ERROR", "Either email or phone is required.", status_code=422
            )
        await enforce_otp_send_limits(
            recipient,
            ip_address=self.ip_address,
            source_id=f"password-reset:{self.ip_address or 'unknown'}",
            # Unknown recipients are throttled, but cannot consume the paid
            # SMS circuit breaker when no message will be delivered.
            costed_delivery=False,
        )
        user = None
        if email:
            user = await self._get_user_by_email(email)
        elif phone:
            user = await self._get_user_by_phone(phone)

        # Always return success (don't reveal if account exists)
        if not user:
            return {"message": "If an account exists, a reset link/OTP has been sent."}

        if phone:
            await enforce_otp_delivery_budget(ip_address=self.ip_address)

        purpose = "password_reset"
        otp_plain: str | None = None
        if phone:
            from app.twilio_client import is_verify_configured, send_sms, verify_send
            if is_verify_configured():
                delivered = await verify_send(phone)
            else:
                otp_plain, otp_hashed = generate_otp()
                self.db.add(OTPRecord(
                    purpose=purpose,
                    recipient_hash=hash_recipient(recipient),
                    hashed_otp=otp_hashed,
                    expires_at=utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES),
                ))
                delivered = True if self.settings.DEBUG else await send_sms(
                    phone,
                    f"Your Fuvay password reset code is {otp_plain}. "
                    f"Valid for {OTP_EXPIRE_MINUTES} minutes.",
                )
        else:
            from app.email_client import is_email_configured, send_login_code_email
            otp_plain, otp_hashed = generate_otp()
            self.db.add(OTPRecord(
                purpose=purpose,
                recipient_hash=hash_recipient(recipient),
                hashed_otp=otp_hashed,
                expires_at=utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES),
            ))
            delivered = True if self.settings.DEBUG else (
                await send_login_code_email(email or "", otp_plain, OTP_EXPIRE_MINUTES)
                if is_email_configured() else False
            )
        if not delivered:
            logger.warning("auth.password_reset_delivery_failed", channel="phone" if phone else "email")
            raise ServiceOSException(
                "SERVICE_UNAVAILABLE",
                "We couldn't send the reset code. Please try again.",
                status_code=503,
            )
        await self._audit("password.reset_requested", "success",
                          actor_id=user.id, tenant_id=user.tenant_id)
        return {
            "message": "If an account exists, a reset OTP has been sent.",
            **({"otp_hint": otp_plain} if self.settings.DEBUG and otp_plain else {}),
        }

    async def confirm_password_reset(
        self, email: str | None, phone: str | None, reset_token: str, new_password: str
    ) -> dict:
        """`reset_token` is the OTP issued by `request_password_reset`. Mirrors
        `verify_phone_otp_login`'s OTPRecord lookup/attempt-limiting pattern --
        OTPRecord has no reversible user reference (only a one-way
        `recipient_hash`), so the same identifier used to request the OTP is
        required again here to locate both the OTP and the account."""
        recipient = (email or phone or "").strip().lower()
        if not recipient:
            raise ServiceOSException("VALIDATION_ERROR", "Either email or phone is required.")
        await enforce_otp_verify_limits(
            recipient,
            ip_address=self.ip_address,
            source_id=f"password-reset:{self.ip_address or 'unknown'}",
        )
        otp_record = None
        verify_approved = False
        if phone:
            from app.twilio_client import is_verify_configured, verify_check
            if is_verify_configured():
                verify_approved = await verify_check(phone, reset_token)
                if not verify_approved:
                    raise ServiceOSException(
                        "PASSWORD_RESET_CODE_INVALID", "Invalid or expired reset code.",
                        status_code=400, resolution="Request a new reset code.",
                    )
        if not verify_approved:
            recipient_hash = hash_recipient(recipient)
            r = await self.db.execute(
                select(OTPRecord).where(
                    and_(OTPRecord.purpose == "password_reset",
                         OTPRecord.recipient_hash == recipient_hash,
                         OTPRecord.is_used == False,
                         OTPRecord.expires_at > utcnow())
                ).order_by(OTPRecord.created_at.desc()).limit(1)
            )
            otp_record = r.scalar_one_or_none()
            # Enumeration-safe: an unknown recipient and an expired/wrong OTP
            # for a real recipient both fail identically.
            if not otp_record:
                raise ServiceOSException("PASSWORD_RESET_CODE_INVALID", "Invalid or expired reset code.",
                                         status_code=400, resolution="Request a new reset code.")
            otp_record.attempts += 1
            if otp_record.attempts > 3:
                otp_record.is_used = True
                raise ServiceOSException("PASSWORD_RESET_CODE_INVALID", "Too many incorrect attempts. Request a new reset code.",
                                         status_code=400)
            if not verify_otp(reset_token, otp_record.hashed_otp):
                raise ServiceOSException("PASSWORD_RESET_CODE_INVALID", "Invalid or expired reset code.",
                                         status_code=400,
                                         resolution=f"{3 - otp_record.attempts} attempts remaining.")
            otp_record.is_used = True

        user = await self._get_user_by_email(email) if email else await self._get_user_by_phone(phone)
        if not user or not user.is_active:
            raise ServiceOSException("PASSWORD_RESET_CODE_INVALID", "Invalid or expired reset code.", status_code=400)

        errors = validate_password_strength(new_password, user.full_name, user.email)
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors))
        history = user.password_history or []
        for old_hash in history:
            if verify_password(new_password, old_hash):
                raise ServiceOSException(
                    "VALIDATION_ERROR",
                    f"Cannot reuse any of your last {PASSWORD_HISTORY_COUNT} passwords.",
                )
        new_hash = hash_password(new_password)
        user.hashed_password = new_hash
        user.password_history = ([new_hash] + history)[:PASSWORD_HISTORY_COUNT]
        user.password_changed_at = utcnow()
        user.force_password_change = False
        user.password_reset_required = False
        user.temporary_password_active = False

        # A compromised-password scenario is exactly what recovery exists
        # for -- every existing session (and its refresh-token family) is
        # revoked, matching change_password's own other-sessions revocation
        # but here covering the current session too, since there is no
        # "current session" during an unauthenticated recovery flow.
        await self.db.execute(
            update(UserSession).where(
                UserSession.user_id == user.id, UserSession.revoked_at == None
            ).values(revoked_at=utcnow())
        )

        await self._audit("auth.password_reset_confirmed", "success", actor_id=user.id,
                          tenant_id=user.tenant_id)
        await self._publish_event("auth.password_changed", str(user.id), {"reason": "reset"},
                                   tenant_id=str(user.tenant_id) if user.tenant_id else None)
        return {"message": "Password reset successfully. Please log in with your new password."}

    # ── Required password change (force-change flow) ──────────────────────────
    async def change_password_required(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> dict:
        """Like change_password, but accepts temp/admin-set passwords and clears all security flags."""
        from app.engines.auth.models import PasswordResetToken
        user = await self._get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User", str(user_id))

        if not verify_password(current_password, user.hashed_password or ""):
            await self._audit("auth.password_reset_failed", "failure",
                              actor_id=user_id, tenant_id=user.tenant_id,
                              metadata={"reason": "wrong_current_password"})
            raise ServiceOSException(
                "CURRENT_PASSWORD_INVALID",
                "Current password is incorrect.",
                resolution="Enter the password that was last set for your account.",
            )

        errors = validate_password_strength(new_password, user.full_name, user.email)
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", errors[0])

        new_hash = hash_password(new_password)
        history = user.password_history or []
        for old_hash in history:
            if verify_password(new_password, old_hash):
                raise ServiceOSException(
                    "PASSWORD_SAME_AS_OLD",
                    f"Cannot reuse any of your last {PASSWORD_HISTORY_COUNT} passwords.",
                )

        user.hashed_password = new_hash
        user.password_history = ([new_hash] + history)[:PASSWORD_HISTORY_COUNT]
        user.password_changed_at = utcnow()
        user.force_password_change = False
        user.password_reset_required = False
        user.temporary_password_active = False

        # Revoke any admin-issued reset tokens for this user
        r = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.status == "active",
            )
        )
        for token in r.scalars().all():
            token.status = "used"
            token.used_at = utcnow()
            token.used_ip = self.ip_address

        await self._audit("auth.required_password_changed", "success",
                          actor_id=user_id, tenant_id=user.tenant_id,
                          metadata={"flags_cleared": ["force_password_change",
                                                      "password_reset_required",
                                                      "temporary_password_active"]})
        await self._publish_event("auth.required_password_changed", str(user_id), {},
                                   tenant_id=str(user.tenant_id) if user.tenant_id else None)
        logger.info("auth.required_password_changed", user_id=str(user_id))
        return {"password_changed": True, "redirect_to": "/login",
                "message": "Password changed successfully. Please log in again."}

    # ── Admin security actions ─────────────────────────────────────────────────
    async def _revoke_all_user_sessions(self, user_id: uuid.UUID) -> int:
        """Revoke all active sessions for a user. Adds session IDs to Redis for immediate enforcement."""
        r = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at == None,
            )
        )
        sessions = r.scalars().all()
        count = 0
        ttl = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        for s in sessions:
            s.revoked_at = utcnow()
            # Add to Redis so currently-issued JWTs are immediately blocked
            try:
                await self.redis.setex(
                    f"serviceos:session:revoked:{s.id}", ttl, "1"
                )
            except Exception:
                pass
            count += 1
        return count

    def _can_admin_manage_user(self, admin: "UserContext", target: User) -> None:
        """Raise if admin cannot manage the target user."""
        from app.dependencies.auth import UserContext as UC
        if admin.role == "super_admin":
            return  # Super admin can manage all
        if admin.role == "tenant_owner":
            if str(target.tenant_id) != admin.tenant_id:
                raise ServiceOSException(
                    "PERMISSION_DENIED", "You can only manage users within your own tenant."
                )
            if target.role == "super_admin":
                raise ServiceOSException(
                    "PERMISSION_DENIED", "Tenant owners cannot manage platform administrators."
                )
        else:
            raise ServiceOSException("PERMISSION_DENIED", "Insufficient permissions for this action.")

    async def admin_force_password_change(
        self,
        admin: "UserContext",
        target_user_id: uuid.UUID,
        reason: str,
        revoke_sessions: bool,
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        target.force_password_change = True
        target.password_reset_required = True
        target.last_password_reset_at = utcnow()
        target.last_password_reset_by_admin_id = uuid.UUID(admin.user_id)

        sessions_revoked = 0
        if revoke_sessions:
            sessions_revoked = await self._revoke_all_user_sessions(target_user_id)

        await self._audit(
            "auth.password_change_required_set", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id,
            target_id=target_user_id, target_type="user",
            metadata={"reason": reason, "sessions_revoked": sessions_revoked},
        )
        logger.info("auth.admin_forced_password_change",
                    admin_id=admin.user_id, target_user=str(target_user_id))
        return {
            "user_id": str(target_user_id),
            "force_password_change": True,
            "sessions_revoked": sessions_revoked,
        }

    async def admin_send_password_reset(
        self,
        admin: "UserContext",
        target_user_id: uuid.UUID,
        reason: str,
        revoke_sessions: bool,
    ) -> dict:
        from app.engines.auth.models import PasswordResetToken
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        # Generate a cryptographically secure reset token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Revoke any existing active reset tokens for this user
        r = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == target_user_id,
                PasswordResetToken.status == "active",
            )
        )
        for old in r.scalars().all():
            old.status = "revoked"

        reset_token = PasswordResetToken(
            user_id=target_user_id,
            token_hash=token_hash,
            purpose="admin_reset",
            status="active",
            expires_at=utcnow() + timedelta(hours=24),
            created_by_user_id=uuid.UUID(admin.user_id),
            created_ip=self.ip_address,
        )
        self.db.add(reset_token)

        sessions_revoked = 0
        if revoke_sessions:
            sessions_revoked = await self._revoke_all_user_sessions(target_user_id)

        # Attempt to send via email/notification; fail safely if not configured
        email_sent = False
        notification_sent = False
        try:
            from app.email_client import send_password_reset_email, is_email_configured
            if is_email_configured():
                await send_password_reset_email(
                    to=target.email,
                    full_name=target.full_name,
                    reset_token=raw_token,
                    expires_hours=24,
                )
                email_sent = True
        except Exception as e:
            logger.warning("auth.password_reset_email_failed", error=str(e))

        await self._audit(
            "auth.password_reset_link_sent", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id,
            target_id=target_user_id, target_type="user",
            metadata={"reason": reason, "email_sent": email_sent,
                      "sessions_revoked": sessions_revoked},
        )
        logger.info("auth.admin_sent_password_reset",
                    admin_id=admin.user_id, target_user=str(target_user_id))

        result: dict = {
            "user_id": str(target_user_id),
            "reset_token_created": True,
            "expires_at": reset_token.expires_at.isoformat(),
            "email_sent": email_sent,
            "sessions_revoked": sessions_revoked,
        }
        # In dev/staging: surface the token for manual testing (never in prod)
        from app.config import get_settings as _gs
        if _gs().APP_ENV in ("development", "testing"):
            result["reset_token_dev_only"] = raw_token
        return result

    async def admin_generate_temporary_password(
        self,
        admin: "UserContext",
        target_user_id: uuid.UUID,
        reason: str,
        revoke_sessions: bool,
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        # Generate a strong temporary password: 12 chars, meets all policy requirements
        import string as _string
        alphabet = _string.ascii_letters + _string.digits + "!@#$%^&*"
        while True:
            temp_pw = "".join(secrets.choice(alphabet) for _ in range(14))
            # Ensure it meets policy
            if (any(c.isupper() for c in temp_pw) and any(c.islower() for c in temp_pw)
                    and any(c.isdigit() for c in temp_pw)
                    and any(c in "!@#$%^&*" for c in temp_pw)):
                break

        target.hashed_password = hash_password(temp_pw)
        target.password_history = ([hash_password(temp_pw)] + (target.password_history or []))[:PASSWORD_HISTORY_COUNT]
        target.force_password_change = True
        target.password_reset_required = True
        target.temporary_password_active = True
        target.last_password_reset_at = utcnow()
        target.last_password_reset_by_admin_id = uuid.UUID(admin.user_id)

        sessions_revoked = 0
        if revoke_sessions:
            sessions_revoked = await self._revoke_all_user_sessions(target_user_id)

        # Audit WITHOUT logging the password itself
        await self._audit(
            "auth.temporary_password_generated", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id,
            target_id=target_user_id, target_type="user",
            metadata={"reason": reason, "sessions_revoked": sessions_revoked},
        )
        logger.info("auth.temporary_password_generated",
                    admin_id=admin.user_id, target_user=str(target_user_id))

        return {
            "user_id": str(target_user_id),
            "temporary_password": temp_pw,   # Shown once only — never stored plain
            "force_password_change": True,
            "sessions_revoked": sessions_revoked,
            "warning": "Copy this temporary password now. It will not be shown again.",
        }

    async def get_user_security_status(
        self, admin: "UserContext", target_user_id: uuid.UUID
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)
        return {
            "user_id": str(target.id),
            "email": target.email,
            "full_name": target.full_name,
            "role": target.role,
            "is_active": target.is_active,
            "force_password_change": target.force_password_change,
            "password_reset_required": target.password_reset_required,
            "temporary_password_active": target.temporary_password_active,
            "password_changed_at": target.password_changed_at.isoformat() if target.password_changed_at else None,
            "last_password_reset_at": target.last_password_reset_at.isoformat() if target.last_password_reset_at else None,
            "last_password_reset_by_admin_id": str(target.last_password_reset_by_admin_id) if target.last_password_reset_by_admin_id else None,
            "locked_until": target.locked_until.isoformat() if target.locked_until and target.locked_until > utcnow() else None,
            "last_login_at": target.last_login_at.isoformat() if target.last_login_at else None,
        }

    # ── Profile ───────────────────────────────────────────────────────────────
    async def get_profile(self, user_id: uuid.UUID) -> dict:
        user = await self._get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User", str(user_id))
        perms = ROLE_PERMISSIONS.get(user.role, [])
        if user.role == "staff":
            overrides = await self._get_staff_permissions(user.id)
            # Merge overrides
            extra_granted = [k for k, v in overrides.items() if v]
            perms = list(set(perms + extra_granted))
        return self._user_to_profile(user, perms)

    async def update_profile(
        self, user_id: uuid.UUID, full_name: str | None, phone: str | None, avatar_url: str | None
    ) -> dict:
        user = await self._get_user_by_id(user_id)
        if not user:
            raise NotFoundException("User", str(user_id))
        if full_name:
            user.full_name = full_name
        if phone:
            # Check uniqueness
            existing = await self._get_user_by_phone(phone)
            if existing and existing.id != user_id:
                raise ServiceOSException("ALREADY_EXISTS", "This phone number is already in use.")
            user.phone = phone
        if avatar_url is not None:
            user.avatar_url = avatar_url
        await self._audit("profile.updated", "success", actor_id=user_id, tenant_id=user.tenant_id)
        return self._user_to_profile(user)

    # ── Staff Management ──────────────────────────────────────────────────────
    async def invite_staff(
        self, tenant_id: uuid.UUID, inviter_id: uuid.UUID,
        email: str, full_name: str, phone: str | None, permissions: list[str]
    ) -> dict:
        # Phase 2A Slice 2F-29 (M01): validate permission keys against the real
        # registry BEFORE any persistence, so an invalid key cannot leave a
        # half-created user behind. No permission is added; the key must
        # already exist in the registry.
        unknown_perms = sorted(p for p in (permissions or [])
                               if p not in _valid_permission_keys())
        if unknown_perms:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                f"Unknown permission key(s): {', '.join(unknown_perms)}",
                resolution="Use a permission key from the platform permission registry.",
                context={"unknown_permissions": unknown_perms},
            )

        # Check if user already exists
        existing = await self._get_user_by_email(email)
        if existing and existing.tenant_id == tenant_id:
            raise ServiceOSException("ALREADY_EXISTS", f"A user with email {email} already exists in this tenant.")

        # Enforce the tenant's plan staff limit before creating the invite.
        try:
            from app.engines.tenant_engine.service import TenantService
            await TenantService(self.db).check_limit(tenant_id, "staff_count")
        except ServiceOSException:
            raise
        except Exception as e:
            logger.warning("auth.staff_limit_check_failed", error=str(e))

        # Create user with temp password
        temp_password = secrets.token_urlsafe(12)
        invite_token = secrets.token_urlsafe(32)

        user = User(
            email=email.lower(),
            phone=phone,
            full_name=full_name,
            role="staff",
            tenant_id=tenant_id,
            hashed_password=hash_password(temp_password),
            is_active=True,
            is_verified=False,
            force_password_change=True,
            meta={"invite_token": invite_token, "invite_expires": (utcnow() + timedelta(days=7)).isoformat()},
        )
        self.db.add(user)
        await self.db.flush()

        try:
            from app.core.usage_quota import adjust_usage
            await adjust_usage(self.db, tenant_id, "current_staff_count", 1)
        except Exception as e:
            logger.warning("auth.staff_usage_increment_failed", error=str(e))

        # Set custom permissions
        # Phase 2A Slice 2F-29 (M01): same registry validation as
        # update_permissions -- an invitation must not be able to mint a
        # StaffPermission override for a permission key the platform does not
        # define. Validated against the existing registry only; nothing added.
        for perm in permissions:
            self.db.add(StaffPermission(
                user_id=user.id, tenant_id=tenant_id,
                permission_key=perm, is_granted=True, granted_by=inviter_id,
            ))

        await self._audit("staff.invited", "success", actor_id=inviter_id,
                          tenant_id=tenant_id, target_id=user.id, target_type="user",
                          metadata={"email": email, "permissions": permissions})
        await self._publish_event("auth.staff_invited", str(user.id),
                                   {"email": email, "inviter_id": str(inviter_id)},
                                   tenant_id=str(tenant_id))
        # In production: send invite email via Notification engine
        invite_expires = (utcnow() + timedelta(days=7)).isoformat()
        return {
            "invite_id": str(user.id),
            "email": email,
            "expires_at": invite_expires,
            "message": f"Invite sent to {email}. Valid for 7 days.",
            "invite_token": invite_token,  # Remove in production
        }

    async def accept_invite(self, invite_token: str, password: str) -> dict:
        """Staff accepts invite, sets their own password."""
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import JSONB
        r = await self.db.execute(
            select(User).where(
                User.role == "staff",
                User.is_verified == False,
            )
        )
        users = r.scalars().all()
        user = None
        for u in users:
            if u.meta and u.meta.get("invite_token") == invite_token:
                user = u
                break

        if not user:
            raise ServiceOSException("NOT_FOUND", "Invalid or expired invite token.",
                                     resolution="Ask your administrator to resend the invitation.")

        invite_expires_str = user.meta.get("invite_expires", "")
        if invite_expires_str:
            try:
                expires = datetime.fromisoformat(invite_expires_str)
                if expires < utcnow():
                    raise ServiceOSException("INVALID_TOKEN", "Invite has expired.",
                                             resolution="Ask your administrator to resend the invitation.")
            except ServiceOSException:
                raise
            except Exception:
                pass

        errors = validate_password_strength(password, user.full_name, user.email)
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors))

        user.hashed_password = hash_password(password)
        user.is_verified = True
        user.force_password_change = False
        user.meta = {k: v for k, v in user.meta.items() if k not in ("invite_token", "invite_expires")}

        await self._audit("staff.invite_accepted", "success", actor_id=user.id,
                          tenant_id=user.tenant_id)
        return {"message": "Account activated. You can now log in.", "email": user.email}

    async def resend_invite(self, user_id: uuid.UUID, inviter_id: uuid.UUID) -> dict:
        user = await self._get_user_by_id(user_id)
        if not user or user.is_verified:
            raise ServiceOSException("NOT_FOUND", "Pending invite not found.")
        new_token = secrets.token_urlsafe(32)
        user.meta = {**user.meta, "invite_token": new_token,
                     "invite_expires": (utcnow() + timedelta(days=7)).isoformat()}
        await self._audit("staff.invite_resent", "success", actor_id=inviter_id,
                          target_id=user_id, target_type="user")
        return {"message": f"Invite resent to {user.email}.", "invite_token": new_token}

    async def update_permissions(
        self, target_user_id: uuid.UUID, tenant_id: uuid.UUID,
        granting_user_id: uuid.UUID, permissions: dict[str, bool]
    ) -> dict:
        # Phase 2A Slice 2F-29 (M01): a foreign-tenant target must not be
        # distinguishable from a nonexistent one. The previous
        # PERMISSION_DENIED("User does not belong to your tenant") confirmed
        # that the id existed in ANOTHER tenant -- an account-existence oracle
        # reachable by any principal holding auth:permissions:manage. Now
        # identical to the pre-existing deactivate_staff behaviour: NotFound.
        user = await self._get_user_by_id(target_user_id)
        if not user or user.tenant_id != tenant_id:
            raise NotFoundException("User", str(target_user_id))

        # Phase 2A Slice 2F-29 (M01): validate every permission key against the
        # real registry BEFORE writing. Previously any arbitrary string became a
        # StaffPermission row, and PermissionChecker.has consults those rows as
        # overrides -- so an unknown/typo key silently created a live grant (or
        # a deny that could never be satisfied). No permission is added here;
        # the key must already exist in the registry.
        unknown = sorted(k for k in permissions if k not in _valid_permission_keys())
        if unknown:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                f"Unknown permission key(s): {', '.join(unknown)}",
                resolution="Use a permission key from the platform permission registry.",
                context={"unknown_permissions": unknown},
            )

        # Phase 2A Slice 2F: a "reduction" is any permission that ends up
        # is_granted=False as a result of this call -- either an existing
        # True flipping to False, or a brand-new explicit deny row. Slice 2E
        # found permission changes embedded in the JWT can remain stale in
        # an already-issued token; Slice 2F closes that for the security-
        # sensitive direction (reductions) by revoking sessions immediately,
        # rather than only for role changes as the pre-existing
        # deactivate_staff method already did.
        reduced_keys: list[str] = []
        for perm_key, is_granted in permissions.items():
            r = await self.db.execute(
                select(StaffPermission).where(
                    StaffPermission.user_id == target_user_id,
                    StaffPermission.permission_key == perm_key,
                )
            )
            existing = r.scalar_one_or_none()
            if existing:
                if existing.is_granted and not is_granted:
                    reduced_keys.append(perm_key)
                existing.is_granted = is_granted
            else:
                self.db.add(StaffPermission(
                    user_id=target_user_id, tenant_id=tenant_id,
                    permission_key=perm_key, is_granted=is_granted,
                    granted_by=granting_user_id,
                ))
                if not is_granted:
                    reduced_keys.append(perm_key)

        sessions_revoked = 0
        if reduced_keys:
            active_sessions = await self.db.execute(
                select(UserSession.id).where(
                    UserSession.user_id == target_user_id, UserSession.revoked_at == None
                )
            )
            session_ids = [row[0] for row in active_sessions]
            if session_ids:
                await self.db.execute(
                    update(UserSession).where(
                        UserSession.user_id == target_user_id, UserSession.revoked_at == None
                    ).values(revoked_at=utcnow(), revocation_reason="permission_reduction")
                )
                sessions_revoked = len(session_ids)
                # Populate the Redis revocation flag get_current_user actually
                # checks (serviceos:session:revoked:{session_id}) -- setting
                # only user_sessions.revoked_at (as deactivate_staff already
                # did, pre-existing) does NOT stop an already-issued JWT from
                # continuing to authenticate, since get_current_user checks
                # Redis, not this DB column, at request time. This closes the
                # exact gap documented in Slice 2D's session-revocation
                # findings for the permission-reduction case.
                for sid in session_ids:
                    try:
                        await self.redis.setex(
                            f"serviceos:session:revoked:{sid}",
                            ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                            "1",
                        )
                    except Exception as e:
                        logger.warning("auth.session_revocation_redis_failed",
                                       session_id=str(sid), error=str(e))

        await self._audit("staff.permissions_updated", "success",
                          actor_id=granting_user_id, tenant_id=tenant_id,
                          target_id=target_user_id, target_type="user",
                          metadata={"permissions": permissions,
                                    "reduced_permission_keys": reduced_keys,
                                    "sessions_revoked": sessions_revoked})
        # Invalidate permission cache
        try:
            await self.redis.delete(f"serviceos:permissions:{target_user_id}")
        except Exception:
            pass
        message = "Permissions updated."
        if reduced_keys:
            message += f" {sessions_revoked} active session(s) revoked immediately due to permission reduction; reauthentication required."
        else:
            message += " Takes effect on next token refresh."
        return {"user_id": str(target_user_id),
                "permissions_updated": len(permissions),
                "reduced_permission_keys": reduced_keys,
                "sessions_revoked": sessions_revoked,
                "message": message}

    async def deactivate_staff(self, user_id: uuid.UUID, tenant_id: uuid.UUID,
                                requesting_user_id: uuid.UUID) -> dict:
        user = await self._get_user_by_id(user_id)
        if not user or user.tenant_id != tenant_id:
            raise NotFoundException("User", str(user_id))
        was_active = user.is_active
        user.is_active = False
        if was_active:
            try:
                from app.core.usage_quota import adjust_usage
                await adjust_usage(self.db, tenant_id, "current_staff_count", -1)
            except Exception as e:
                logger.warning("auth.staff_usage_decrement_failed", error=str(e))
        # Revoke all sessions
        active_sessions = await self.db.execute(
            select(UserSession.id).where(
                UserSession.user_id == user_id, UserSession.revoked_at == None
            )
        )
        session_ids = [row[0] for row in active_sessions]
        sessions_revoked = 0
        if session_ids:
            await self.db.execute(
                update(UserSession).where(
                    UserSession.user_id == user_id, UserSession.revoked_at == None
                ).values(revoked_at=utcnow(), revocation_reason="staff_deactivated")
            )
            sessions_revoked = len(session_ids)
            # Phase 2A Slice 2F-1: this method previously only set
            # user_sessions.revoked_at, which get_current_user does NOT check
            # at request time -- it checks the Redis flag
            # (serviceos:session:revoked:{session_id}) instead, so an
            # already-issued JWT kept authenticating after deactivation. Same
            # gap and same fix as update_permissions in Slice 2F.
            for sid in session_ids:
                try:
                    await self.redis.setex(
                        f"serviceos:session:revoked:{sid}",
                        ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                        "1",
                    )
                except Exception as e:
                    logger.warning("auth.session_revocation_redis_failed",
                                   session_id=str(sid), error=str(e))
        await self._audit("staff.deactivated", "success",
                          actor_id=requesting_user_id, tenant_id=tenant_id,
                          target_id=user_id, target_type="user",
                          metadata={"sessions_revoked": sessions_revoked})
        return {"user_id": str(user_id), "is_active": False,
                "sessions_revoked": sessions_revoked,
                "message": "Staff member deactivated and all sessions revoked."}

    # ── Staff Roster (tenant-portal Staff page) ─────────────────────────────────
    def _staff_dict(self, user: User, jobs_today: int = 0, active_job: str | None = None) -> dict:
        meta = user.meta or {}
        return {
            "id": str(user.id), "full_name": user.full_name, "phone": user.phone,
            "specialisations": meta.get("specialisations", []),
            "status": "active" if user.is_active else "deactivated",
            "rating": meta.get("rating"),
            "jobs_today": jobs_today, "active_job": active_job,
            "performance_score": meta.get("performance_score"),
            "working_hours": meta.get("working_hours"),
        }

    async def list_staff_by_tenant(self, tenant_id: uuid.UUID) -> dict:
        from app.engines.field_ops.models import Job
        from app.engines.field_ops.constants import TERMINAL_STATUSES, JS

        r = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id, User.role == "staff",
                                User.deleted_at.is_(None)).order_by(User.full_name)
        )
        staff = r.scalars().all()
        if not staff:
            return {"staff": [], "total": 0}

        staff_ids = [u.id for u in staff]
        today = utcnow().date()
        jr = await self.db.execute(
            select(Job.assigned_staff_id, Job.status, Job.job_number, Job.created_at)
            .where(Job.assigned_staff_id.in_(staff_ids))
        )
        jobs_today: dict[uuid.UUID, int] = {}
        active_job: dict[uuid.UUID, str] = {}
        excluded = set(TERMINAL_STATUSES) | {JS.DRAFT}
        for staff_id, status_, job_number, created_at in jr.all():
            if created_at and created_at.date() == today:
                jobs_today[staff_id] = jobs_today.get(staff_id, 0) + 1
            if status_ not in excluded and staff_id not in active_job:
                active_job[staff_id] = job_number

        return {
            "staff": [self._staff_dict(u, jobs_today.get(u.id, 0), active_job.get(u.id))
                      for u in staff],
            "total": len(staff),
        }

    async def get_staff(self, user_id: uuid.UUID) -> dict:
        user = await self._get_user_by_id(user_id)
        if not user or user.role != "staff":
            raise NotFoundException("Staff", str(user_id))
        return self._staff_dict(user)

    async def update_staff_schedule(self, user_id: uuid.UUID, working_hours: dict) -> dict:
        user = await self._get_user_by_id(user_id)
        if not user or user.role != "staff":
            raise NotFoundException("Staff", str(user_id))
        user.meta = {**(user.meta or {}), "working_hours": working_hours}
        return self._staff_dict(user)

    # ── Impersonation ─────────────────────────────────────────────────────────
    async def impersonate(
        self, impersonator_id: uuid.UUID, target_user_id: uuid.UUID,
        reason: str, enabled_engines: list[str] | None = None,
        tenant_name: str | None = None,
    ) -> dict:
        impersonator = await self._get_user_by_id(impersonator_id)
        if not impersonator or impersonator.role != "super_admin":
            raise PermissionDeniedException("super_admin",
                                            impersonator.role if impersonator else "unknown")

        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        if not target.is_active:
            raise ServiceOSException("CONFLICT", "Cannot impersonate a deactivated user.")

        session_id = str(uuid.uuid4())
        from datetime import timezone
        expires_at = utcnow() + timedelta(minutes=60)

        token, jti = create_impersonation_token(
            impersonator_id=str(impersonator_id),
            impersonation_session_id=session_id,
            target_user_id=str(target.id),
            target_email=target.email,
            target_role=target.role,
            tenant_id=str(target.tenant_id) if target.tenant_id else None,
            tenant_name=tenant_name,
            plan_type=None,
            enabled_engines=enabled_engines or [],
        )

        # Track in Redis (for listing active impersonations)
        await self.redis.setex(
            f"{REDIS_IMPERSONATION_PREFIX}{session_id}",
            3600,
            f"{impersonator_id}:{target_user_id}:{reason[:100]}",
        )

        await self._audit("impersonation.started", "success",
                          actor_id=impersonator_id, actor_role="super_admin",
                          target_id=target_user_id, target_type="user",
                          metadata={"reason": reason, "session_id": session_id})
        await self._publish_event("auth.impersonation_started", str(target_user_id),
                                   {"impersonator_id": str(impersonator_id), "reason": reason})
        logger.warning("auth.impersonation_started",
                       impersonator=str(impersonator_id), target=str(target_user_id))

        return {
            "impersonation_session_id": session_id,
            "access_token": token,
            "target_user": self._user_to_profile(target),
            "expires_at": expires_at.isoformat(),
            "warning": "All actions during impersonation are fully logged.",
        }

    async def end_impersonation(self, session_id: str, admin_id: uuid.UUID) -> dict:
        key = f"{REDIS_IMPERSONATION_PREFIX}{session_id}"
        val = await self.redis.get(key)
        if not val:
            raise NotFoundException("ImpersonationSession", session_id)
        await self.redis.delete(key)
        await self._audit("impersonation.ended", "success", actor_id=admin_id,
                          metadata={"session_id": session_id})
        return {"session_id": session_id, "ended": True}

    async def list_active_impersonations(self) -> list[dict]:
        keys = await self.redis.keys(f"{REDIS_IMPERSONATION_PREFIX}*")
        result = []
        for key in keys:
            val = await self.redis.get(key)
            session_id = key.replace(REDIS_IMPERSONATION_PREFIX, "")
            if val:
                parts = val.split(":", 2)
                result.append({
                    "session_id": session_id,
                    "impersonator_id": parts[0] if len(parts) > 0 else None,
                    "target_user_id": parts[1] if len(parts) > 1 else None,
                    "reason": parts[2] if len(parts) > 2 else None,
                })
        return result

    # ── API Keys ──────────────────────────────────────────────────────────────
    async def create_api_key(
        self, tenant_id: uuid.UUID, created_by: uuid.UUID,
        name: str, scopes: list[str], is_test_mode: bool, expires_days: int | None
    ) -> dict:
        full_key, key_prefix, hashed = generate_api_key(is_test_mode)
        key = ApiKey(
            tenant_id=tenant_id,
            created_by=created_by,
            name=name,
            key_prefix=key_prefix,
            hashed_key=hashed,
            scopes=scopes,
            is_test_mode=is_test_mode,
            expires_at=(utcnow() + timedelta(days=expires_days)) if expires_days else None,
        )
        self.db.add(key)
        await self.db.flush()
        await self._audit("api_key.created", "success", actor_id=created_by, tenant_id=tenant_id,
                          target_id=key.id, target_type="api_key",
                          metadata={"name": name, "scopes": scopes})
        return {
            "key_id": str(key.id), "name": name,
            "full_key": full_key, "key_prefix": key_prefix,
            "scopes": scopes, "is_test_mode": is_test_mode,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "warning": "Store this key securely. It will not be shown again.",
        }

    async def list_api_keys(self, tenant_id: uuid.UUID) -> list[dict]:
        r = await self.db.execute(
            select(ApiKey).where(ApiKey.tenant_id == tenant_id, ApiKey.revoked_at == None)
            .order_by(ApiKey.created_at.desc())
        )
        keys = r.scalars().all()
        return [
            {
                "key_id": str(k.id), "name": k.name, "key_prefix": k.key_prefix,
                "scopes": k.scopes, "is_test_mode": k.is_test_mode,
                "calls_today": k.calls_today, "calls_total": k.calls_total,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "created_at": k.created_at.isoformat(),
            }
            for k in keys
        ]

    async def revoke_api_key(self, key_id: uuid.UUID, tenant_id: uuid.UUID,
                              revoker_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id,
                                 ApiKey.revoked_at == None)
        )
        key = r.scalar_one_or_none()
        if not key:
            raise NotFoundException("ApiKey", str(key_id))
        key.revoked_at = utcnow()
        key.is_active = False
        await self._audit("api_key.revoked", "success", actor_id=revoker_id, tenant_id=tenant_id,
                          target_id=key_id, target_type="api_key")
        return {"key_id": str(key_id), "revoked": True}

    async def update_api_key(
        self, key_id: uuid.UUID, tenant_id: uuid.UUID, updater_id: uuid.UUID,
        name: str | None, scopes: list[str] | None
    ) -> dict:
        r = await self.db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id,
                                 ApiKey.revoked_at == None)
        )
        key = r.scalar_one_or_none()
        if not key:
            raise NotFoundException("ApiKey", str(key_id))
        if name:
            key.name = name
        if scopes is not None:
            key.scopes = scopes
        await self._audit("api_key.updated", "success", actor_id=updater_id, tenant_id=tenant_id,
                          target_id=key_id, target_type="api_key")
        return {"key_id": str(key_id), "name": key.name, "scopes": key.scopes}

    # ── Audit Log ─────────────────────────────────────────────────────────────
    async def get_audit_log(
        self, user_id: uuid.UUID | None, tenant_id: uuid.UUID | None,
        role: str, limit: int = 50, cursor: str | None = None
    ) -> dict:
        from app.schemas.base import decode_cursor, encode_cursor

        query = select(AuthAuditLog).order_by(AuthAuditLog.created_at.desc())

        if role == "super_admin":
            if tenant_id:
                query = query.where(AuthAuditLog.tenant_id == tenant_id)
        else:
            query = query.where(AuthAuditLog.actor_id == user_id)

        if cursor:
            try:
                c = decode_cursor(cursor)
                query = query.where(AuthAuditLog.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception:
                pass

        query = query.limit(limit + 1)
        r = await self.db.execute(query)
        logs = r.scalars().all()

        has_next = len(logs) > limit
        logs = logs[:limit]
        next_cursor = None
        if has_next and logs:
            next_cursor = encode_cursor({"created_at": logs[-1].created_at.isoformat()})

        return {
            "logs": [
                {
                    "log_id": str(l.id),
                    "actor_id": str(l.actor_id) if l.actor_id else None,
                    "actor_role": l.actor_role,
                    "action_type": l.action_type,
                    "outcome": l.outcome,
                    "target_id": str(l.target_id) if l.target_id else None,
                    "target_type": l.target_type,
                    "ip_address": l.ip_address,
                    "failure_reason": l.failure_reason,
                    "created_at": l.created_at.isoformat(),
                }
                for l in logs
            ],
            "has_next": has_next,
            "next_cursor": next_cursor,
        }

    # ── Phase 0E: Login event logging ────────────────────────────────────────
    async def _log_login_event(
        self,
        event_type: str,
        user_id: uuid.UUID | None = None,
        email_attempted: str | None = None,
        tenant_id: uuid.UUID | None = None,
        failure_reason: str | None = None,
        device_id: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Write one row to login_events. Never raises — fire-and-forget."""
        try:
            ev = LoginEvent(
                user_id=user_id,
                email_attempted=email_attempted,
                tenant_id=tenant_id,
                event_type=event_type,
                failure_reason=failure_reason,
                ip_address=self.ip_address,
                user_agent=user_agent,
                device_id=device_id,
                request_id=self.request_id,
            )
            self.db.add(ev)
        except Exception as exc:
            logger.warning("login_event.write_failed", error=str(exc))

    # ── Phase 0E: Lock / Unlock ───────────────────────────────────────────────
    async def lock_user(
        self,
        admin: "UserContext",
        target_user_id: uuid.UUID,
        reason: str,
        locked_until: "datetime | None",
        revoke_sessions: bool,
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        target.account_status = "locked"
        target.lock_reason = reason
        target.locked_by_user_id = uuid.UUID(admin.user_id)
        if locked_until:
            target.locked_until = locked_until
        else:
            # Permanent lock: set to far future
            target.locked_until = utcnow() + timedelta(days=3650)

        sessions_revoked = 0
        if revoke_sessions:
            sessions_revoked = await self._revoke_all_user_sessions(target_user_id)

        await self._audit(
            "account.locked", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason, "sessions_revoked": sessions_revoked,
                      "locked_until": locked_until.isoformat() if locked_until else "permanent"},
        )
        logger.info("account.locked", admin_id=admin.user_id, target=str(target_user_id))
        return {
            "user_id": str(target_user_id),
            "account_status": "locked",
            "locked_until": target.locked_until.isoformat() if target.locked_until else None,
            "sessions_revoked": sessions_revoked,
            "message": "Account locked.",
        }

    async def unlock_user(
        self,
        admin: "UserContext",
        target_user_id: uuid.UUID,
        reason: str,
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        target.account_status = "active"
        target.locked_until = None
        target.lock_reason = None
        target.locked_by_user_id = None

        await self._audit(
            "account.unlocked", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason},
        )
        logger.info("account.unlocked", admin_id=admin.user_id, target=str(target_user_id))
        return {
            "user_id": str(target_user_id),
            "account_status": "active",
            "message": "Account unlocked. User can log in again.",
        }

    # ── Phase 0E: Deactivate / Reactivate ────────────────────────────────────
    async def deactivate_user(
        self,
        admin: "UserContext",
        target_user_id: uuid.UUID,
        reason: str,
        revoke_sessions: bool,
    ) -> dict:
        if str(admin.user_id) == str(target_user_id):
            raise ServiceOSException("PERMISSION_DENIED", "You cannot deactivate your own account.")
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        target.is_active = False
        target.account_status = "disabled"
        target.deactivated_at = utcnow()
        target.deactivated_by_user_id = uuid.UUID(admin.user_id)
        target.deactivation_reason = reason

        sessions_revoked = 0
        if revoke_sessions:
            sessions_revoked = await self._revoke_all_user_sessions(target_user_id)

        await self._audit(
            "account.deactivated", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason, "sessions_revoked": sessions_revoked},
        )
        logger.info("account.deactivated", admin_id=admin.user_id, target=str(target_user_id))
        return {
            "user_id": str(target_user_id),
            "is_active": False,
            "account_status": "disabled",
            "sessions_revoked": sessions_revoked,
            "message": "User deactivated.",
        }

    async def reactivate_user(
        self,
        admin: "UserContext",
        target_user_id: uuid.UUID,
        reason: str,
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        target.is_active = True
        target.account_status = "active"
        target.deactivated_at = None
        target.deactivated_by_user_id = None
        target.deactivation_reason = None

        await self._audit(
            "account.reactivated", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason},
        )
        logger.info("account.reactivated", admin_id=admin.user_id, target=str(target_user_id))
        return {
            "user_id": str(target_user_id),
            "is_active": True,
            "account_status": "active",
            "message": "User reactivated. They can log in again.",
        }

    # ── P0 Platform Users: Suspend / Unsuspend ────────────────────────────────
    async def suspend_user(
        self, admin: "UserContext", target_user_id: uuid.UUID,
        reason: str, revoke_sessions: bool = True,
    ) -> dict:
        if str(admin.user_id) == str(target_user_id):
            raise ServiceOSException("PERMISSION_DENIED", "You cannot suspend your own account.")
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        target.is_active = False
        target.account_status = "suspended"

        sessions_revoked = 0
        if revoke_sessions:
            sessions_revoked = await self._revoke_all_user_sessions(target_user_id)

        await self._audit(
            "platform_user.suspended", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason, "sessions_revoked": sessions_revoked},
        )
        return {
            "user_id": str(target_user_id), "is_active": False, "account_status": "suspended",
            "sessions_revoked": sessions_revoked, "message": "User suspended.",
        }

    async def unsuspend_user(
        self, admin: "UserContext", target_user_id: uuid.UUID, reason: str,
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        target.is_active = True
        target.account_status = "active"

        await self._audit(
            "platform_user.reactivated", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason},
        )
        return {
            "user_id": str(target_user_id), "is_active": True, "account_status": "active",
            "message": "Suspension lifted. User can log in again.",
        }

    # ── P0 Platform Users: MFA enforcement ────────────────────────────────────
    async def require_mfa_for_user(
        self, admin: "UserContext", target_user_id: uuid.UUID, reason: str,
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        target.mfa_required = True
        await self._audit(
            "platform_user.mfa_required", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason},
        )
        return {"user_id": str(target_user_id), "mfa_required": True,
                "message": "MFA is now required for this user."}

    async def reset_mfa_for_user(
        self, admin: "UserContext", target_user_id: uuid.UUID, reason: str,
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        from app.engines.auth.models import MFASecret, MFABackupCode
        await self.db.execute(
            delete(MFASecret).where(MFASecret.user_id == target_user_id))
        await self.db.execute(
            delete(MFABackupCode).where(MFABackupCode.user_id == target_user_id))
        target.is_mfa_enabled = False

        await self._audit(
            "platform_user.mfa_reset", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason},
        )
        return {"user_id": str(target_user_id), "is_mfa_enabled": False,
                "message": "MFA has been reset. User must set up MFA again."}

    # ── P0 Platform Users: Single session revoke ──────────────────────────────
    async def admin_revoke_session(
        self, admin: "UserContext", target_user_id: uuid.UUID,
        session_id: uuid.UUID, reason: str,
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        session = await self.db.scalar(
            select(UserSession).where(
                UserSession.id == session_id, UserSession.user_id == target_user_id))
        if not session:
            raise NotFoundException("Session", str(session_id))
        session.revoked_at = utcnow()
        session.revoked_by_user_id = uuid.UUID(admin.user_id)
        session.revocation_reason = reason

        try:
            await self.redis.setex(
                f"serviceos:session:revoked:{session_id}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
        except Exception:
            pass

        await self._audit(
            "platform_user.session_revoked", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason, "session_id": str(session_id)},
        )
        return {"session_id": str(session_id), "revoked": True, "message": "Session revoked."}

    # ── P0 Platform Users: Role & Access Scope ────────────────────────────────
    # FINAL-L5-05N: these must be exactly the 5 real, enforced role strings
    # from app.core.permissions.ROLE_PERMISSIONS -- not invented labels. The
    # previous 8-value set (platform_admin/compliance_officer/support_admin/
    # operations_admin/finance_admin/security_admin/read_only_admin) matched
    # no real authorization role except "super_admin"; a user "invited" with
    # any of those labels was silently granted full super_admin access
    # (see the User(role="super_admin", ...) bug fixed in invite_platform_user
    # below) while the UI displayed a plausible-looking limited role.
    VALID_PLATFORM_ROLES = {
        "super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly",
    }
    # Same 5 values as a list, for User.role.in_(...) queries scoping the
    # Platform Users surface to real platform-level admin accounts (not
    # just literal super_admin, now that distinct roles are real).
    PLATFORM_ADMIN_ROLES = list(VALID_PLATFORM_ROLES)
    VALID_ACCESS_SCOPES = {
        "global", "operations", "finance", "compliance", "support",
        "tenant_scoped", "customer_support_limited",
    }

    async def change_platform_role(
        self, admin: "UserContext", target_user_id: uuid.UUID,
        platform_role: str, reason: str,
    ) -> dict:
        """FINAL-L5-05N: updates the real, enforced `role` column (the one
        app.core.permissions.PermissionChecker actually consults) in
        addition to `platform_role` (kept in sync as a display label, no
        longer a dead write since it always mirrors the real role). Prior
        behavior only wrote platform_role -- this endpoint had zero effect
        on the target's actual backend authorization."""
        if platform_role not in self.VALID_PLATFORM_ROLES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"platform_role must be one of: {sorted(self.VALID_PLATFORM_ROLES)}")
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        old_role = target.role
        old_platform_role = target.platform_role
        target.role = platform_role
        target.platform_role = platform_role
        await self._audit(
            "platform_user.role_changed", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason, "old_role": old_role, "new_role": platform_role,
                      "old_platform_role": old_platform_role},
        )
        return {"user_id": str(target_user_id), "platform_role": platform_role,
                "message": "Platform role updated."}

    async def change_access_scope(
        self, admin: "UserContext", target_user_id: uuid.UUID,
        access_scope: str, reason: str,
    ) -> dict:
        if access_scope not in self.VALID_ACCESS_SCOPES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"access_scope must be one of: {sorted(self.VALID_ACCESS_SCOPES)}")
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        old_scope = target.access_scope
        target.access_scope = access_scope
        await self._audit(
            "platform_user.access_scope_changed", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason, "old_scope": old_scope, "new_scope": access_scope},
        )
        return {"user_id": str(target_user_id), "access_scope": access_scope,
                "message": "Access scope updated."}

    # ── P0 Platform Users: List / Summary / Detail ────────────────────────────

    @staticmethod
    def _user_group(u: "User") -> str:
        return {
            "super_admin": "platform",
            "admin_operations": "platform",
            "admin_finance": "platform",
            "admin_security": "platform",
            "admin_readonly": "platform",
            "tenant_owner": "tenant",
            "staff": "staff", "customer": "customer",
        }.get(u.role, "other")

    @staticmethod
    def _user_status(u: "User") -> str:
        if u.account_status == "locked" or (u.locked_until and u.locked_until > utcnow()):
            return "locked"
        if u.account_status == "suspended":
            return "suspended"
        if not u.is_active:
            return "deactivated"
        if u.meta and u.meta.get("invite_token"):
            return "invited"
        if u.password_reset_required:
            return "password_reset_required"
        return "active"

    @staticmethod
    def _mfa_status(u: "User") -> str:
        if u.is_mfa_enabled:
            return "on"
        if u.mfa_required:
            return "required"
        return "off"

    def _platform_user_dict(self, u: "User") -> dict:
        return {
            "id": str(u.id),
            "full_name": u.full_name,
            "email": u.email,
            "phone": u.phone,
            "user_group": self._user_group(u),
            "role": u.role,
            "platform_role": u.platform_role,
            "access_scope": u.access_scope,
            "tenant_id": str(u.tenant_id) if u.tenant_id else None,
            "status": self._user_status(u),
            "mfa_status": self._mfa_status(u),
            "is_active": u.is_active,
            "password_reset_required": u.password_reset_required,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "failed_login_attempts": u.failed_login_attempts,
        }

    async def list_platform_users(
        self, user_group: str = "platform", q: str | None = None,
        role: str | None = None, platform_role: str | None = None,
        status: str | None = None, mfa_status: str | None = None,
        access_scope: str | None = None, inactive_days_min: int | None = None,
        page: int = 1, limit: int = 50,
    ) -> dict:
        stmt = select(User).where(User.deleted_at.is_(None))
        if user_group != "all":
            group_roles = {
                "platform": self.PLATFORM_ADMIN_ROLES, "tenant": ["tenant_owner"],
                "staff": ["staff"], "customer": ["customer"],
            }.get(user_group, [])
            if group_roles:
                stmt = stmt.where(User.role.in_(group_roles))
        if role:
            stmt = stmt.where(User.role == role)
        if platform_role:
            stmt = stmt.where(User.platform_role == platform_role)
        if access_scope:
            stmt = stmt.where(User.access_scope == access_scope)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                func.lower(User.full_name).like(like) |
                func.lower(User.email).like(like) |
                func.lower(func.coalesce(User.phone, "")).like(like)
            )
        if inactive_days_min:
            cutoff = utcnow() - timedelta(days=inactive_days_min)
            stmt = stmt.where(
                (User.last_login_at.is_(None) & (User.created_at < cutoff)) |
                (User.last_login_at < cutoff)
            )
        if status:
            now = utcnow()
            invited = User.meta.has_key("invite_token")  # type: ignore[attr-defined]
            status_filters = {
                "locked": or_(User.account_status == "locked", User.locked_until > now),
                "suspended": User.account_status == "suspended",
                "deactivated": User.is_active.is_(False),
                "invited": invited,
                "password_reset_required": User.password_reset_required.is_(True),
                "active": and_(
                    User.account_status.notin_(("locked", "suspended")),
                    or_(User.locked_until.is_(None), User.locked_until <= now),
                    User.is_active.is_(True),
                    User.password_reset_required.is_(False),
                    ~invited,
                ),
            }
            if status in status_filters:
                stmt = stmt.where(status_filters[status])
        if mfa_status:
            if mfa_status == "on":
                stmt = stmt.where(User.is_mfa_enabled.is_(True))
            elif mfa_status == "required":
                stmt = stmt.where(User.is_mfa_enabled.is_(False), User.mfa_required.is_(True))
            elif mfa_status == "off":
                stmt = stmt.where(User.is_mfa_enabled.is_(False), User.mfa_required.is_(False))

        total_count = await self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        start = (page - 1) * limit
        rows = (await self.db.execute(
            stmt.order_by(User.created_at.desc()).offset(start).limit(limit)
        )).scalars().all()
        # status/mfa_status are derived — filter in Python after computing
        dicts = [self._platform_user_dict(u) for u in rows]
        if status:
            dicts = [d for d in dicts if d["status"] == status]
        if mfa_status:
            dicts = [d for d in dicts if d["mfa_status"] == mfa_status]

        total = total_count
        page_rows = dicts
        return {
            "users": page_rows,
            "meta": {"total": total, "page": page, "limit": limit,
                     "total_pages": max(1, (total + limit - 1) // limit)},
        }

    async def get_platform_users_summary(self) -> dict:
        rows = (await self.db.execute(
            select(User).where(User.deleted_at.is_(None), User.role.in_(self.PLATFORM_ADMIN_ROLES))
        )).scalars().all()
        total = len(rows)
        active = sum(1 for u in rows if self._user_status(u) == "active")
        mfa_on = sum(1 for u in rows if u.is_mfa_enabled)
        mfa_missing = total - mfa_on
        admins = sum(1 for u in rows if u.role in ("super_admin", "admin_security"))
        pending_invites = sum(1 for u in rows if u.meta and u.meta.get("invite_token"))
        locked = sum(1 for u in rows if self._user_status(u) == "locked")
        suspicious = sum(1 for u in rows if u.failed_login_attempts >= 3)
        cutoff = utcnow() - timedelta(days=30)
        inactive_30 = sum(1 for u in rows if
                           (u.last_login_at and u.last_login_at < cutoff) or
                           (not u.last_login_at and u.created_at and u.created_at < cutoff))
        return {
            "total_platform_users": total,
            "active_users": active,
            "inactive_users": total - active,
            "mfa_enabled": mfa_on,
            "mfa_missing": mfa_missing,
            "administrators": admins,
            "pending_invites": pending_invites,
            "locked_accounts": locked,
            "suspicious_logins": suspicious,
            "inactive_30_days": inactive_30,
        }

    async def get_platform_user_detail(self, admin: "UserContext", target_user_id: uuid.UUID) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)
        d = self._platform_user_dict(target)
        d["mfa_required"] = target.mfa_required
        d["locked_until"] = target.locked_until.isoformat() if target.locked_until else None
        d["lock_reason"] = target.lock_reason
        d["deactivation_reason"] = target.deactivation_reason
        d["last_password_reset_at"] = (
            target.last_password_reset_at.isoformat() if target.last_password_reset_at else None)
        d["temporary_password_active"] = target.temporary_password_active
        d["invited_by_user_id"] = str(target.invited_by_user_id) if target.invited_by_user_id else None
        return d

    # ── P0 Platform Users: Invite lifecycle ───────────────────────────────────

    async def invite_platform_user(
        self, admin: "UserContext", email: str, full_name: str, phone: str | None,
        platform_role: str, access_scope: str, require_mfa: bool = True,
        invite_expiry_days: int = 7,
    ) -> dict:
        if platform_role not in self.VALID_PLATFORM_ROLES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"platform_role must be one of: {sorted(self.VALID_PLATFORM_ROLES)}")
        if access_scope not in self.VALID_ACCESS_SCOPES:
            raise ServiceOSException("VALIDATION_ERROR",
                f"access_scope must be one of: {sorted(self.VALID_ACCESS_SCOPES)}")
        if platform_role == "super_admin" and admin.role != "super_admin":
            raise ServiceOSException("PERMISSION_DENIED", "Only a Super Admin can invite another Super Admin.")

        existing = await self._get_user_by_email(email)
        if existing:
            raise ServiceOSException("ALREADY_EXISTS", f"A user with email {email} already exists.")

        temp_password = secrets.token_urlsafe(12)
        invite_token = secrets.token_urlsafe(32)
        expires_at = utcnow() + timedelta(days=invite_expiry_days)

        user = User(
            # FINAL-L5-05N: role (the real, enforced authorization column --
            # see app.core.permissions.ROLE_PERMISSIONS) must match the
            # intended platform_role, not be hardcoded to "super_admin" for
            # every invite regardless of the role selected in the UI.
            email=email.lower(), phone=phone, full_name=full_name,
            role=platform_role, platform_role=platform_role, access_scope=access_scope,
            hashed_password=hash_password(temp_password),
            is_active=True, is_verified=False, force_password_change=True,
            mfa_required=require_mfa,
            invited_by_user_id=uuid.UUID(admin.user_id),
            meta={"invite_token": invite_token, "invite_expires": expires_at.isoformat()},
        )
        self.db.add(user)
        await self.db.flush()

        await self._audit(
            "platform_user.invited", "success", actor_id=uuid.UUID(admin.user_id),
            actor_role=admin.role, target_id=user.id, target_type="user",
            metadata={"email": email, "platform_role": platform_role, "access_scope": access_scope},
        )
        return {
            "invite_id": str(user.id), "email": email, "expires_at": expires_at.isoformat(),
            "message": f"Invite sent to {email}. Valid for {invite_expiry_days} days.",
            "invite_token": invite_token,
        }

    async def list_platform_invites(self) -> dict:
        rows = (await self.db.execute(
            select(User).where(
                User.role.in_(self.PLATFORM_ADMIN_ROLES), User.deleted_at.is_(None),
            ).order_by(User.created_at.desc())
        )).scalars().all()
        invites = []
        for u in rows:
            token = (u.meta or {}).get("invite_token")
            if not token:
                continue
            expires_str = (u.meta or {}).get("invite_expires")
            expired = False
            if expires_str:
                try:
                    expired = datetime.fromisoformat(expires_str) < utcnow()
                except Exception:
                    pass
            invites.append({
                "invite_id": str(u.id), "email": u.email, "name": u.full_name,
                "platform_role": u.platform_role, "access_scope": u.access_scope,
                "status": "expired" if expired else "pending",
                "expires_at": expires_str, "invited_by_user_id": str(u.invited_by_user_id) if u.invited_by_user_id else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            })
        return {"invites": invites, "total": len(invites)}

    async def revoke_platform_invite(
        self, admin: "UserContext", invite_user_id: uuid.UUID, reason: str,
    ) -> dict:
        target = await self._get_user_by_id(invite_user_id)
        if not target or not (target.meta or {}).get("invite_token"):
            raise NotFoundException("Invite", str(invite_user_id))
        target.is_active = False
        target.account_status = "disabled"
        target.meta = {k: v for k, v in (target.meta or {}).items()
                       if k not in ("invite_token", "invite_expires")}
        await self._audit(
            "platform_user.invite_revoked", "success", actor_id=uuid.UUID(admin.user_id),
            actor_role=admin.role, target_id=invite_user_id, target_type="user",
            metadata={"reason": reason},
        )
        return {"invite_id": str(invite_user_id), "status": "revoked", "message": "Invite revoked."}

    # ── P0 Platform Users: Risk signals (computed, not persisted) ─────────────

    async def get_platform_user_risk_signals(self, admin: "UserContext", target_user_id: uuid.UUID) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        signals = []
        if not target.is_mfa_enabled:
            signals.append({"risk_type": "mfa_missing", "risk_level": "medium",
                             "description": "Multi-factor authentication is not enabled."})
        if target.failed_login_attempts >= 3:
            signals.append({"risk_type": "too_many_failed_logins", "risk_level": "high",
                             "description": f"{target.failed_login_attempts} recent failed login attempts."})
        if self._user_status(target) == "locked":
            signals.append({"risk_type": "locked_account", "risk_level": "high",
                             "description": target.lock_reason or "Account is locked."})
        if target.password_reset_required:
            signals.append({"risk_type": "password_reset_required", "risk_level": "low",
                             "description": "User must reset their password."})
        cutoff = utcnow() - timedelta(days=30)
        if (target.last_login_at and target.last_login_at < cutoff) or \
           (not target.last_login_at and target.created_at and target.created_at < cutoff):
            signals.append({"risk_type": "inactive_30_days", "risk_level": "medium",
                             "description": "No login activity in the last 30 days."})
        if target.role in ("super_admin", "admin_security"):
            signals.append({"risk_type": "role_privilege_high", "risk_level": "low",
                             "description": f"User holds a high-privilege role ({target.role})."})

        levels = [s["risk_level"] for s in signals]
        if "high" in levels and len(levels) >= 2:
            score = "critical"
        elif "high" in levels:
            score = "high"
        elif "medium" in levels:
            score = "medium"
        else:
            score = "low"

        return {"user_id": str(target_user_id), "risk_score": score, "signals": signals}

    # ── P0 Platform Users: Audit trail ────────────────────────────────────────

    async def get_platform_user_audit_logs(
        self, admin: "UserContext", target_user_id: uuid.UUID, page: int = 1, limit: int = 50,
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        stmt = select(AuthAuditLog).where(
            AuthAuditLog.target_id == target_user_id, AuthAuditLog.target_type == "user",
        ).order_by(AuthAuditLog.created_at.desc())
        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
        return {
            "logs": [self._audit_dict(r) for r in rows],
            "meta": {"total": total or 0, "page": page, "limit": limit},
        }

    async def list_platform_audit_logs(
        self, action_type: str | None = None, page: int = 1, limit: int = 50,
    ) -> dict:
        stmt = select(AuthAuditLog).where(
            AuthAuditLog.action_type.like("platform_user.%")
        ).order_by(AuthAuditLog.created_at.desc())
        if action_type:
            stmt = stmt.where(AuthAuditLog.action_type == action_type)
        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
        return {
            "logs": [self._audit_dict(r) for r in rows],
            "meta": {"total": total or 0, "page": page, "limit": limit},
        }

    @staticmethod
    def _audit_dict(r: "AuthAuditLog") -> dict:
        ip = r.ip_address or ""
        ip_hint = ip.rsplit(".", 1)[0] + ".xxx" if "." in ip else (ip[:6] + "…" if ip else None)
        return {
            "id": str(r.id),
            "actor_id": str(r.actor_id) if r.actor_id else None,
            "actor_role": r.actor_role,
            "action_type": r.action_type,
            "target_id": str(r.target_id) if r.target_id else None,
            "outcome": r.outcome,
            "reason": (r.action_meta or {}).get("reason"),
            "old_value": {k: v for k, v in (r.action_meta or {}).items() if k.startswith("old_")},
            "new_value": {k: v for k, v in (r.action_meta or {}).items() if k.startswith("new_")},
            "ip_hint": ip_hint,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    # ── P0 Platform Users: Bulk actions ───────────────────────────────────────

    async def bulk_platform_action(
        self, admin: "UserContext", action: str, user_ids: list[uuid.UUID], reason: str,
    ) -> dict:
        results = []
        for uid in user_ids:
            try:
                if action == "require_mfa":
                    await self.require_mfa_for_user(admin, uid, reason)
                elif action == "force_password_reset":
                    await self.admin_force_password_change(admin, uid, reason, True)
                elif action == "suspend":
                    await self.suspend_user(admin, uid, reason, True)
                elif action == "deactivate":
                    await self.deactivate_user(admin, uid, reason, True)
                elif action == "revoke_sessions":
                    await self.admin_revoke_all_sessions(admin, uid, reason)
                else:
                    raise ServiceOSException("VALIDATION_ERROR", f"Unknown bulk action '{action}'.")
                results.append({"user_id": str(uid), "success": True})
            except Exception as e:
                results.append({"user_id": str(uid), "success": False, "error": str(e)})
        succeeded = sum(1 for r in results if r["success"])
        return {"action": action, "total": len(user_ids), "succeeded": succeeded,
                "failed": len(user_ids) - succeeded, "results": results}

    # ── Phase 0E: Admin session management ───────────────────────────────────
    async def admin_list_sessions(
        self, admin: "UserContext", target_user_id: uuid.UUID
    ) -> list[dict]:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        r = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == target_user_id,
                UserSession.revoked_at == None,
            ).order_by(UserSession.last_active_at.desc())
        )
        sessions = r.scalars().all()
        await self._audit(
            "security.user_sessions_viewed", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            target_id=target_user_id, target_type="user",
        )
        return [
            {
                "session_id": str(s.id),
                "device_name": s.device_name,
                "device_type": s.device_type,
                "ip_address": s.ip_address,
                "last_active_at": s.last_active_at.isoformat(),
                "is_trusted": s.is_trusted,
                "is_approved": s.is_approved,
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ]

    async def admin_revoke_all_sessions(
        self, admin: "UserContext", target_user_id: uuid.UUID, reason: str
    ) -> dict:
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        # Update revoked_by and reason on each session
        r = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == target_user_id,
                UserSession.revoked_at == None,
            )
        )
        sessions = r.scalars().all()
        ttl = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        for s in sessions:
            s.revoked_at = utcnow()
            s.revoked_by_user_id = uuid.UUID(admin.user_id)
            s.revocation_reason = reason
            try:
                await self.redis.setex(f"serviceos:session:revoked:{s.id}", ttl, "1")
            except Exception:
                pass

        await self._audit(
            "session.revoked_all", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            tenant_id=target.tenant_id, target_id=target_user_id, target_type="user",
            metadata={"reason": reason, "sessions_revoked": len(sessions)},
        )
        logger.info("session.revoked_all", admin_id=admin.user_id, target=str(target_user_id))
        return {
            "user_id": str(target_user_id),
            "sessions_revoked": len(sessions),
            "message": f"{len(sessions)} session(s) revoked.",
        }

    # ── Phase 0E: Login history ───────────────────────────────────────────────
    async def get_login_history(
        self,
        requester_id: uuid.UUID,
        requester_role: str,
        target_user_id: uuid.UUID,
        limit: int = 50,
    ) -> dict:
        # Authorization: super_admin or self
        if requester_role != "super_admin" and requester_id != target_user_id:
            # Tenant owner can see own staff
            target = await self._get_user_by_id(target_user_id)
            if not target:
                raise NotFoundException("User", str(target_user_id))
            # Verify requester is owner of the same tenant
            requester = await self._get_user_by_id(requester_id)
            if (not requester or requester_role != "tenant_owner"
                    or requester.tenant_id != target.tenant_id
                    or target.role not in ("staff", "technician")):
                raise ServiceOSException(
                    "PERMISSION_DENIED",
                    "You can only view your own login history or your tenant staff's history.",
                )

        r = await self.db.execute(
            select(LoginEvent)
            .where(LoginEvent.user_id == target_user_id)
            .order_by(LoginEvent.created_at.desc())
            .limit(limit)
        )
        events = r.scalars().all()
        await self._audit(
            "security.login_history_viewed", "success",
            actor_id=requester_id, target_id=target_user_id, target_type="user",
        )
        return {
            "user_id": str(target_user_id),
            "events": [
                {
                    "event_id": str(e.id),
                    "event_type": e.event_type,
                    "failure_reason": e.failure_reason,
                    "ip_address": e.ip_address,
                    "device_id": e.device_id,
                    "created_at": e.created_at.isoformat(),
                }
                for e in events
            ],
            "total": len(events),
        }

    async def get_my_login_activity(
        self, user_id: uuid.UUID, current_device_id: str | None,
        outcome_filter: str = "all", limit: int = 20, cursor: str | None = None,
    ) -> dict:
        """Customer-safe login history (Login Activity phase) -- deliberately
        a SEPARATE method from `get_login_history` (which stays the raw
        admin/tenant-owner view). Reuses the same canonical `LoginEvent`
        table -- no parallel mobile-only history table, no synthetic
        events derived from sessions.

        Every internal `event_type` is mapped through the centralized
        `LOGIN_EVENT_PUBLIC_MAP`; an unmapped value renders as the neutral
        fallback rather than leaking the raw backend string. `ip_address`
        and `failure_reason` are never included in the response -- only a
        public label/outcome. `channel`/`device_name` are derived from the
        stored `user_agent` via the same `parse_device_info` helper used
        for sessions (LoginEvent has no stored device_type column).
        `is_current_device` uses the same device_id-comparison heuristic
        already disclosed as imperfect for sessions -- LoginEvent has no
        session_id column to compare against instead."""
        conditions = [LoginEvent.user_id == user_id]
        if outcome_filter == "successful":
            success_types = [k for k, v in LOGIN_EVENT_PUBLIC_MAP.items() if v[1] == "successful"]
            conditions.append(LoginEvent.event_type.in_(success_types))
        elif outcome_filter == "needs_attention":
            attention_types = [k for k, v in LOGIN_EVENT_PUBLIC_MAP.items()
                                if v[1] in ("verification_required", "blocked")]
            conditions.append(LoginEvent.event_type.in_(attention_types))

        if cursor:
            try:
                cursor_ts_raw, cursor_id_raw = cursor.split("|", 1)
                cursor_ts = datetime.fromisoformat(cursor_ts_raw)
                cursor_id = uuid.UUID(cursor_id_raw)
                conditions.append(
                    or_(
                        LoginEvent.created_at < cursor_ts,
                        and_(LoginEvent.created_at == cursor_ts, LoginEvent.id < cursor_id),
                    )
                )
            except (ValueError, TypeError):
                pass  # Malformed cursor -- ignore rather than 500.

        page_size = min(max(limit, 1), 100)
        r = await self.db.execute(
            select(LoginEvent).where(and_(*conditions))
            .order_by(LoginEvent.created_at.desc(), LoginEvent.id.desc())
            .limit(page_size + 1)
        )
        rows = r.scalars().all()
        has_more = len(rows) > page_size
        rows = rows[:page_size]

        items = []
        for e in rows:
            label, outcome = LOGIN_EVENT_PUBLIC_MAP.get(
                e.event_type, (LOGIN_EVENT_UNKNOWN_LABEL, LOGIN_EVENT_UNKNOWN_OUTCOME)
            )
            device_name, device_type = parse_device_info(e.user_agent)
            items.append({
                "event_id": str(e.id),
                "label": label,
                "outcome": outcome,
                "channel": self._channel_for(device_type),
                "device_name": device_name,
                "is_current_device": bool(current_device_id) and e.device_id == current_device_id,
                "occurred_at": e.created_at.isoformat(),
            })

        next_cursor = None
        if has_more and rows:
            last = rows[-1]
            next_cursor = f"{last.created_at.isoformat()}|{last.id}"

        return {"events": items, "next_cursor": next_cursor}

    # ── Phase 0E: Enhanced security status ───────────────────────────────────
    async def get_full_security_status(
        self, admin: "UserContext", target_user_id: uuid.UUID
    ) -> dict:
        """Extended security status including account_status, lock info, session count."""
        target = await self._get_user_by_id(target_user_id)
        if not target:
            raise NotFoundException("User", str(target_user_id))
        self._can_admin_manage_user(admin, target)

        # Count active sessions
        session_r = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == target_user_id,
                UserSession.revoked_at == None,
            )
        )
        active_sessions = len(session_r.scalars().all())

        await self._audit(
            "security.user_security_viewed", "success",
            actor_id=uuid.UUID(admin.user_id), actor_role=admin.role,
            target_id=target_user_id, target_type="user",
        )
        return {
            "user_id": str(target.id),
            "email": target.email,
            "full_name": target.full_name,
            "role": target.role,
            "is_active": target.is_active,
            "account_status": getattr(target, "account_status", "active"),
            "lock_reason": getattr(target, "lock_reason", None),
            "locked_until": (
                target.locked_until.isoformat()
                if target.locked_until and target.locked_until > utcnow()
                else None
            ),
            "deactivated_at": (
                target.deactivated_at.isoformat()
                if getattr(target, "deactivated_at", None)
                else None
            ),
            "deactivation_reason": getattr(target, "deactivation_reason", None),
            "force_password_change": target.force_password_change,
            "password_reset_required": target.password_reset_required,
            "temporary_password_active": target.temporary_password_active,
            "password_changed_at": (
                target.password_changed_at.isoformat() if target.password_changed_at else None
            ),
            "last_password_reset_at": (
                target.last_password_reset_at.isoformat()
                if target.last_password_reset_at else None
            ),
            "last_login_at": target.last_login_at.isoformat() if target.last_login_at else None,
            "failed_login_attempts": getattr(target, "failed_login_attempts", 0),
            "active_sessions": active_sessions,
            "mfa_enabled": target.is_mfa_enabled,
        }
