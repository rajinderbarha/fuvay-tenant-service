"""Public Registration Engine — Service (5-step no-payment tenant signup).

Owner Account -> Verify Contact -> Business Identity -> Select Vertical ->
Review & Consent -> Create Workspace.

Steps 1-4 mutate a single PendingTenantRegistration row (autosave-friendly,
resumable, idempotent). Step 5 is the ONLY place real User / Tenant /
TenantBusinessProfile / TenantVerticalEnrollment / ConsentRecord rows are
created, inside one atomic transaction.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.auth.models import User, OTPRecord, AuthAuditLog
from app.engines.auth.utils import (
    hash_password, verify_password, validate_password_strength,
    generate_otp, verify_otp, hash_recipient,
    create_access_token, create_refresh_token,
)
from app.engines.auth.models import UserSession, RefreshToken, RefreshTokenFamily
from app.engines.auth.constants import OTP_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
from app.engines.tenant_engine.models import Tenant, TenantBusinessProfile, TenantAuditLog
from app.engines.vertical_catalog.models import Vertical, TenantVerticalEnrollment, VerticalAuditLog
from app.engines.compliance.models import ConsentRecord, DPDPPolicyVersion
from app.engines.public_registration.models import PendingTenantRegistration
from app.exceptions import ServiceOSException
from app.config import get_settings
from app.twilio_client import send_sms
from app.email_client import send_email

logger = structlog.get_logger("public_registration.service")
utcnow = lambda: datetime.now(timezone.utc)

MOBILE_OTP_PURPOSE = "tenant_registration_mobile"
EMAIL_OTP_PURPOSE = "tenant_registration_email"
MAX_OTP_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]$")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_mobile(mobile: str) -> str:
    m = mobile.strip().replace(" ", "")
    if not m.startswith("+"):
        m = "+" + m.lstrip("0")
    return m


class RegistrationService:
    def __init__(self, db: AsyncSession, ip_address: str | None = None, user_agent: str | None = None):
        self.db = db
        self.ip_address = ip_address
        self.user_agent = user_agent

    # ── Helpers ──────────────────────────────────────────────────────────────
    async def _get_pending(self, registration_id: uuid.UUID) -> PendingTenantRegistration:
        r = await self.db.execute(
            select(PendingTenantRegistration).where(PendingTenantRegistration.id == registration_id)
        )
        pending = r.scalar_one_or_none()
        if not pending:
            raise ServiceOSException("REGISTRATION_NOT_FOUND", "Registration session not found or expired.",
                                      status_code=404)
        if pending.status != "in_progress":
            raise ServiceOSException("REGISTRATION_ALREADY_COMPLETED",
                                      "This registration has already been completed.", status_code=409)
        return pending

    async def _audit(self, action_type: str, outcome: str, target_id=None, metadata: dict | None = None):
        self.db.add(AuthAuditLog(
            actor_id=None, actor_role=None, tenant_id=None, action_type=action_type,
            target_id=target_id, target_type="pending_tenant_registration", outcome=outcome,
            ip_address=self.ip_address, user_agent=self.user_agent, action_meta=metadata or {},
        ))

    # ── Step 1 — Owner Account ──────────────────────────────────────────────
    async def start_or_resume(
        self, full_name: str, email: str, mobile: str, password: str, password_confirm: str,
        authorized_declaration: bool, tos_privacy_accepted: bool, marketing_consent: bool,
        registration_id: uuid.UUID | None = None,
    ) -> dict:
        email_n = _normalize_email(email)
        mobile_n = _normalize_mobile(mobile)

        if password != password_confirm:
            raise ServiceOSException("PASSWORD_MISMATCH", "Passwords do not match.", status_code=422)
        errors = validate_password_strength(password, full_name, email_n)
        if errors:
            raise ServiceOSException("VALIDATION_ERROR", "; ".join(errors), status_code=422)

        # Idempotent resume via registration_id
        if registration_id:
            pending = await self._get_pending(registration_id)
            pending.full_name = full_name
            pending.email = email_n
            pending.mobile = mobile_n
            pending.hashed_password = hash_password(password)
            # Step 1 only establishes credentials and sends verification
            # codes. Consent is captured atomically at completion (step 5).
            pending.authorized_declaration = False
            pending.tos_privacy_accepted = False
            pending.marketing_consent = False
            await self.db.flush()
            dev_codes = await self._send_otps(pending)
            await self._audit("registration.owner_account_updated", "success", target_id=pending.id)
            return self._issue_flow_response(pending, dev_codes=dev_codes)

        # Duplicate check against real users — never leak which field matched
        existing_user = (await self.db.execute(
            select(User).where((User.email == email_n) | (User.phone == mobile_n))
        )).scalars().first()
        if existing_user:
            return {
                "existing_account": True,
                "message": "An account already exists for these details. Sign in, or use account recovery.",
            }

        # Resume an existing incomplete registration for this identity
        existing_pending = (await self.db.execute(
            select(PendingTenantRegistration).where(
                PendingTenantRegistration.status == "in_progress",
                (PendingTenantRegistration.email == email_n) | (PendingTenantRegistration.mobile == mobile_n),
            )
        )).scalars().first()
        if existing_pending:
            existing_pending.full_name = full_name
            existing_pending.hashed_password = hash_password(password)
            existing_pending.authorized_declaration = False
            existing_pending.tos_privacy_accepted = False
            existing_pending.marketing_consent = False
            await self.db.flush()
            dev_codes = await self._send_otps(existing_pending)
            await self._audit("registration.resumed", "success", target_id=existing_pending.id)
            return self._issue_flow_response(existing_pending, resumed=True, dev_codes=dev_codes)

        pending = PendingTenantRegistration(
            full_name=full_name.strip(), email=email_n, mobile=mobile_n,
            hashed_password=hash_password(password),
            authorized_declaration=False,
            tos_privacy_accepted=False,
            marketing_consent=False,
            status="in_progress",
        )
        self.db.add(pending)
        await self.db.flush()
        dev_codes = await self._send_otps(pending)
        await self._audit("registration.started", "success", target_id=pending.id)
        logger.info("registration.step1_owner_account", registration_id=str(pending.id))
        return self._issue_flow_response(pending, dev_codes=dev_codes)

    async def _send_otps(self, pending: PendingTenantRegistration, channels: tuple[str, ...] = ("mobile", "email")) -> dict[str, str]:
        """Sends (or, outside production, simulates) OTPs for the given channels.
        Returns dev codes actually generated this call — never returned to the
        caller unless settings.DEBUG is on; production always leaves this empty
        regardless of DEBUG, so a misconfigured env var can't leak codes."""
        s = get_settings()
        dev_codes: dict[str, str] = {}
        wanted = {
            "mobile": (MOBILE_OTP_PURPOSE, pending.mobile),
            "email": (EMAIL_OTP_PURPOSE, pending.email),
        }
        for purpose, recipient in (wanted[c] for c in channels):
            recent = (await self.db.execute(
                select(OTPRecord).where(
                    OTPRecord.purpose == purpose,
                    OTPRecord.recipient_hash == hash_recipient(recipient),
                    OTPRecord.is_used == False,  # noqa: E712
                ).order_by(OTPRecord.created_at.desc()).limit(1)
            )).scalar_one_or_none()
            if recent and recent.created_at and (utcnow() - recent.created_at).total_seconds() < RESEND_COOLDOWN_SECONDS:
                continue
            otp_plain, otp_hashed = generate_otp()
            self.db.add(OTPRecord(
                purpose=purpose, recipient_hash=hash_recipient(recipient),
                hashed_otp=otp_hashed, expires_at=utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES),
            ))
            if s.DEBUG:
                # Dev/staging: never attempt real delivery (Twilio trial/sandbox
                # numbers routinely report success without the SMS ever
                # arriving) — always surface the code directly instead.
                dev_codes[purpose] = otp_plain
                logger.info("registration.otp_sent_dev", purpose=purpose, dev_otp=otp_plain)
            elif purpose == MOBILE_OTP_PURPOSE:
                await send_sms(recipient, f"Your ServiceOS verification code is {otp_plain}. Valid for {OTP_EXPIRE_MINUTES} minutes.")
            else:
                await send_email(recipient, "Verify your ServiceOS email",
                    f"Your ServiceOS verification code is {otp_plain}. Valid for {OTP_EXPIRE_MINUTES} minutes.")
        return dev_codes

    def _issue_flow_response(self, pending: PendingTenantRegistration, resumed: bool = False,
                              dev_codes: dict[str, str] | None = None) -> dict:
        data = {
            "existing_account": False,
            "registration_id": str(pending.id),
            "resumed": resumed,
            "mobile_verified": pending.mobile_verified,
            "email_verified": pending.email_verified,
            "message": "OTP sent to your mobile and email. Verify both to continue.",
        }
        if dev_codes:
            dev_otps: dict[str, str] = {}
            if dev_codes.get(MOBILE_OTP_PURPOSE):
                data["dev_otp_mobile"] = dev_codes[MOBILE_OTP_PURPOSE]
                dev_otps["mobile"] = dev_codes[MOBILE_OTP_PURPOSE]
            if dev_codes.get(EMAIL_OTP_PURPOSE):
                data["dev_otp_email"] = dev_codes[EMAIL_OTP_PURPOSE]
                dev_otps["email"] = dev_codes[EMAIL_OTP_PURPOSE]
            # Canonical response consumed by the web wizard. The flat keys
            # remain for compatibility with older API clients.
            data["dev_otps"] = dev_otps
        return data

    # ── Step 2 — Verify Contact ──────────────────────────────────────────────
    async def verify_contact(self, registration_id: uuid.UUID, channel: str, otp: str) -> dict:
        pending = await self._get_pending(registration_id)
        purpose = MOBILE_OTP_PURPOSE if channel == "mobile" else EMAIL_OTP_PURPOSE
        recipient = pending.mobile if channel == "mobile" else pending.email

        r = await self.db.execute(
            select(OTPRecord).where(
                OTPRecord.purpose == purpose,
                OTPRecord.recipient_hash == hash_recipient(recipient),
                OTPRecord.is_used == False,  # noqa: E712
            ).order_by(OTPRecord.created_at.desc()).limit(1)
        )
        record = r.scalar_one_or_none()
        generic_error = "The code you entered is invalid or has expired."

        if not record:
            await self._audit(f"registration.{channel}_verify_failed", "failure", target_id=pending.id)
            raise ServiceOSException("INVALID_OTP", generic_error, status_code=400)
        if record.attempts >= MAX_OTP_ATTEMPTS or record.expires_at < utcnow():
            record.is_used = True
            await self._audit(f"registration.{channel}_verify_failed", "failure", target_id=pending.id,
                               metadata={"reason": "max_attempts_or_expired"})
            raise ServiceOSException("INVALID_OTP", generic_error, status_code=400)

        record.attempts += 1
        if not verify_otp(otp, record.hashed_otp):
            await self._audit(f"registration.{channel}_verify_failed", "failure", target_id=pending.id)
            raise ServiceOSException("INVALID_OTP", generic_error, status_code=400)

        record.is_used = True
        record.used_at = utcnow()
        if channel == "mobile":
            pending.mobile_verified = True
        else:
            pending.email_verified = True
        await self._audit(f"registration.{channel}_verified", "success", target_id=pending.id)
        logger.info("registration.step2_verified", channel=channel, registration_id=str(pending.id))
        return {
            "registration_id": str(pending.id),
            "mobile_verified": pending.mobile_verified,
            "email_verified": pending.email_verified,
            "can_proceed": pending.mobile_verified and pending.email_verified,
        }

    async def resend_otp(self, registration_id: uuid.UUID, channel: str) -> dict:
        pending = await self._get_pending(registration_id)
        dev_codes = await self._send_otps(pending, channels=(channel,))
        await self._audit(f"registration.{channel}_otp_resent", "success", target_id=pending.id)
        result = {"registration_id": str(pending.id), "channel": channel, "resent": True}
        purpose = MOBILE_OTP_PURPOSE if channel == "mobile" else EMAIL_OTP_PURPOSE
        if dev_codes.get(purpose):
            result["dev_otp"] = dev_codes[purpose]
        return result

    # ── Step 3 — Business Identity ───────────────────────────────────────────
    async def save_business_identity(self, registration_id: uuid.UUID, **fields) -> dict:
        pending = await self._get_pending(registration_id)
        self._require_verified(pending)

        gstin = fields.get("gstin")
        if gstin and not GSTIN_RE.match(gstin.strip().upper()):
            raise ServiceOSException("VALIDATION_ERROR", "GSTIN format is invalid.", status_code=422)

        for key in ("legal_name", "business_name", "gstin", "pan", "cin", "business_type",
                    "year_established", "employee_count", "website_url", "description"):
            if key in fields and fields[key] is not None:
                setattr(pending, key, fields[key])
        if fields.get("registered_address") is not None:
            # Registered address is the legal address only — NOT service coverage.
            pending.registered_address = fields["registered_address"]
        await self.db.flush()
        await self._audit("registration.business_identity_saved", "success", target_id=pending.id)
        return {"registration_id": str(pending.id), "saved": True}

    def _require_verified(self, pending: PendingTenantRegistration) -> None:
        if not (pending.mobile_verified and pending.email_verified):
            raise ServiceOSException("CONTACT_NOT_VERIFIED",
                                      "Verify your mobile and email before continuing.", status_code=403)

    # ── Step 4 — Select Vertical ─────────────────────────────────────────────
    async def list_registrable_verticals(self) -> list[dict]:
        rows = (await self.db.execute(
            select(Vertical).where(
                Vertical.is_enabled == True,  # noqa: E712
                Vertical.registration_allowed == True,  # noqa: E712
                Vertical.lifecycle_status.in_(["active", "production"]),
            ).order_by(Vertical.sort_order)
        )).scalars().all()
        return [
            {"key": v.key, "slug": v.slug, "label": v.label, "description": v.description,
             "icon": v.icon, "color": v.color}
            for v in rows
        ]

    async def select_vertical(self, registration_id: uuid.UUID, vertical_key: str) -> dict:
        pending = await self._get_pending(registration_id)
        self._require_verified(pending)
        v = (await self.db.execute(
            select(Vertical).where(Vertical.key == vertical_key)
        )).scalar_one_or_none()
        if not v or not v.is_enabled or not v.registration_allowed:
            raise ServiceOSException("VERTICAL_NOT_REGISTRABLE",
                                      "This business category is not currently open for signup.", status_code=422)
        pending.selected_vertical_key = vertical_key
        await self.db.flush()
        await self._audit("registration.vertical_selected", "success", target_id=pending.id,
                           metadata={"vertical_key": vertical_key})
        return {"registration_id": str(pending.id), "selected_vertical_key": vertical_key}

    # ── Step 5 — Review & Consent -> Create Workspace ────────────────────────
    async def complete(
        self, registration_id: uuid.UUID, idempotency_key: str,
        authorized_declaration: bool, tos_privacy_accepted: bool, marketing_consent: bool,
    ) -> dict:
        # Idempotent replay: same key on an already-completed registration returns the same result.
        existing_by_key = (await self.db.execute(
            select(PendingTenantRegistration).where(
                PendingTenantRegistration.idempotency_key == idempotency_key,
                PendingTenantRegistration.status == "completed",
            )
        )).scalar_one_or_none()
        if existing_by_key and existing_by_key.id == registration_id:
            return await self._workspace_response(existing_by_key)

        pending = await self._get_pending(registration_id)
        self._require_verified(pending)
        if not pending.selected_vertical_key:
            raise ServiceOSException("VERTICAL_NOT_SELECTED", "Select a business category before continuing.",
                                      status_code=422)
        if not (authorized_declaration and tos_privacy_accepted):
            raise ServiceOSException("CONSENT_REQUIRED",
                                      "You must confirm the authorization declaration and Terms/Privacy Policy.",
                                      status_code=422)
        if not (pending.legal_name or pending.business_name):
            raise ServiceOSException("BUSINESS_IDENTITY_INCOMPLETE",
                                      "Business name is required before completing signup.", status_code=422)

        # Re-check duplicate right before commit (race between step 1 and step 5)
        dup = (await self.db.execute(
            select(User).where((User.email == pending.email) | (User.phone == pending.mobile))
        )).scalars().first()
        if dup:
            raise ServiceOSException("REGISTRATION_DUPLICATE",
                                      "An account with these details already exists. Please sign in.",
                                      status_code=409)

        vertical = (await self.db.execute(
            select(Vertical).where(Vertical.key == pending.selected_vertical_key)
        )).scalar_one_or_none()
        if not vertical or not vertical.is_enabled or not vertical.registration_allowed:
            raise ServiceOSException("VERTICAL_NOT_REGISTRABLE",
                                      "This business category is no longer open for signup.", status_code=422)

        policy = (await self.db.execute(
            select(DPDPPolicyVersion).where(DPDPPolicyVersion.is_active == True)  # noqa: E712
            .order_by(DPDPPolicyVersion.effective_date.desc())
        )).scalars().first()
        policy_version = policy.policy_version if policy else "unversioned"

        try:
            business_name = pending.business_name or pending.legal_name
            tenant = Tenant(
                tenant_name=business_name,
                business_name=business_name,
                legal_name=pending.legal_name or business_name,
                vertical=vertical.key,
                # Not activated — activation requires setup -> submission ->
                # admin review -> approval -> activation-requirements -> active.
                status="onboarding_pending",
                verification_status="not_started",
                email=pending.email,
                phone=pending.mobile,
                gst_number=pending.gstin,
                business_type=pending.business_type,
                country="India",
                address_line1=(pending.registered_address or {}).get("address_line1")
                              or (pending.registered_address or {}).get("line1"),
                address_line2=(pending.registered_address or {}).get("address_line2")
                              or (pending.registered_address or {}).get("line2"),
                city=(pending.registered_address or {}).get("city"),
                district=(pending.registered_address or {}).get("district"),
                state=(pending.registered_address or {}).get("state"),
                zipcode=(pending.registered_address or {}).get("zipcode")
                        or (pending.registered_address or {}).get("pincode"),
                meta={
                    "owner_name": pending.full_name,
                    "year_established": pending.year_established,
                    "website_url": pending.website_url,
                    "description": pending.description,
                    "registration_number": pending.cin,
                },
            )
            self.db.add(tenant)
            await self.db.flush()

            owner = User(
                tenant_id=tenant.id, email=pending.email, phone=pending.mobile,
                full_name=pending.full_name, role="tenant_owner",
                hashed_password=pending.hashed_password,
                is_active=True, is_verified=True,
                force_password_change=False,
            )
            self.db.add(owner)
            await self.db.flush()
            tenant.owner_user_id = owner.id

            self.db.add(TenantBusinessProfile(
                tenant_id=tenant.id, trade_name=pending.business_name,
                gstin=pending.gstin, cin=pending.cin, pan=pending.pan,
                registered_address=pending.registered_address or {},
                year_established=pending.year_established,
                employee_count=pending.employee_count,
                website_url=pending.website_url, description=pending.description,
            ))

            # draft_setup transition rule: created here at signup completion,
            # BEFORE any setup-wizard content exists. It advances to `draft`
            # once the tenant engages the vertical setup wizard (first save),
            # and only becomes `submitted` when the tenant explicitly submits
            # that wizard for admin review. draft_setup therefore means
            # "vertical chosen, setup not yet started" — distinct from
            # `draft`, which means "setup in progress but not submitted".
            enrollment = TenantVerticalEnrollment(
                tenant_id=tenant.id, vertical_id=vertical.id, status="draft_setup",
            )
            self.db.add(enrollment)
            await self.db.flush()

            # Enrollment tracks setup state; tenant service enablement and
            # provider matching enforce the independent entitlement tables.
            # Grant the chosen vertical and its active service groups in this
            # same transaction so a fresh workspace can complete Services &
            # Pricing. Admin can still disable either entitlement later.
            from app.engines.entitlement.service import entitlement_service
            await entitlement_service.grant_registration_defaults(
                self.db,
                tenant_id=tenant.id,
                module_key=vertical.key,
                actor_id=owner.id,
                actor_role="tenant_owner",
                request_id=idempotency_key,
                commit=False,
            )

            granted_at = utcnow()
            self.db.add(ConsentRecord(
                user_id=owner.id, tenant_id=tenant.id, consent_type="authorization_declaration",
                action="granted", policy_version=policy_version, granted_at=granted_at,
                ip_address=self.ip_address, user_agent=self.user_agent, source="tenant_signup",
            ))
            self.db.add(ConsentRecord(
                user_id=owner.id, tenant_id=tenant.id, consent_type="tos_privacy",
                action="granted", policy_version=policy_version, granted_at=granted_at,
                ip_address=self.ip_address, user_agent=self.user_agent, source="tenant_signup",
            ))
            if marketing_consent:
                # Marketing consent is always its own separate record — never
                # bundled with the required ToS/Privacy or declaration rows.
                self.db.add(ConsentRecord(
                    user_id=owner.id, tenant_id=tenant.id, consent_type="marketing",
                    action="granted", policy_version=policy_version, granted_at=granted_at,
                    ip_address=self.ip_address, user_agent=self.user_agent, source="tenant_signup",
                ))

            self.db.add(TenantAuditLog(
                tenant_id=tenant.id, actor_id=owner.id, actor_role="tenant_owner",
                action_type="tenant.registered", entity_type="tenant", entity_id=str(tenant.id),
                ip_address=self.ip_address,
            ))
            self.db.add(VerticalAuditLog(
                vertical_id=vertical.id, tenant_id=tenant.id, actor_id=owner.id,
                action_type="tenant_vertical.enrolled",
                after_state={"status": "draft_setup"},
            ))
            self.db.add(AuthAuditLog(
                actor_id=owner.id, actor_role="tenant_owner", tenant_id=tenant.id,
                action_type="tenant.registered", target_id=tenant.id, target_type="tenant",
                outcome="success", ip_address=self.ip_address, user_agent=self.user_agent,
            ))

            pending.status = "completed"
            pending.idempotency_key = idempotency_key
            pending.completed_at = utcnow()
            pending.created_tenant_id = tenant.id
            pending.created_user_id = owner.id
            pending.authorized_declaration = True
            pending.tos_privacy_accepted = True
            pending.marketing_consent = marketing_consent

            # Auto-login
            session = UserSession(
                user_id=owner.id, tenant_id=tenant.id, device_id="signup", device_name="Signup",
                device_type="web", ip_address=self.ip_address, user_agent=self.user_agent,
                is_approved=True,
            )
            self.db.add(session)
            await self.db.flush()

            access_token, jti = create_access_token(
                user_id=str(owner.id), email=owner.email, role=owner.role,
                tenant_id=str(tenant.id), tenant_name=tenant.tenant_name, plan_type=tenant.plan_type,
                session_id=str(session.id), device_id=session.device_id,
                is_mfa_enabled=False, onboarding_complete=False, enabled_engines=[],
            )
            family = RefreshTokenFamily(user_id=owner.id, session_id=session.id)
            self.db.add(family)
            await self.db.flush()
            raw_refresh, refresh_jti, hashed_refresh = create_refresh_token()
            self.db.add(RefreshToken(
                family_id=family.id, user_id=owner.id, jti=refresh_jti, hashed_token=hashed_refresh,
                expires_at=utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            ))

            await self.db.commit()
        except ServiceOSException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error("registration.step5_failed", error=str(e))
            raise ServiceOSException("REGISTRATION_FAILED",
                                      "Failed to create your workspace. Please try again.", status_code=500)

        logger.info("registration.completed", tenant_id=str(tenant.id), user_id=str(owner.id))
        return {
            "tenant_id": str(tenant.id),
            "user_id": str(owner.id),
            "enrollment_status": "draft_setup",
            "tenant_status": tenant.status,
            "vertical_key": vertical.key,
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "message": "Workspace created. Continue to the vertical setup wizard.",
        }

    async def _workspace_response(self, pending: PendingTenantRegistration) -> dict:
        owner = await self.db.get(User, pending.created_user_id)
        tenant = await self.db.get(Tenant, pending.created_tenant_id)
        if not owner or not tenant:
            raise ServiceOSException(
                "REGISTRATION_RESULT_NOT_FOUND",
                "The completed workspace could not be restored. Please sign in.",
                status_code=409,
            )

        # A completion response may be lost after the transaction commits.
        # Replaying the same idempotency key must therefore issue a fresh,
        # usable session rather than returning a token-less partial result.
        session = UserSession(
            user_id=owner.id, tenant_id=tenant.id, device_id="signup-replay",
            device_name="Signup replay", device_type="web",
            ip_address=self.ip_address, user_agent=self.user_agent,
            is_approved=True,
        )
        self.db.add(session)
        await self.db.flush()
        access_token, _ = create_access_token(
            user_id=str(owner.id), email=owner.email, role=owner.role,
            tenant_id=str(tenant.id), tenant_name=tenant.tenant_name,
            plan_type=tenant.plan_type, session_id=str(session.id),
            device_id=session.device_id, is_mfa_enabled=False,
            onboarding_complete=False, enabled_engines=[],
        )
        family = RefreshTokenFamily(user_id=owner.id, session_id=session.id)
        self.db.add(family)
        await self.db.flush()
        raw_refresh, refresh_jti, hashed_refresh = create_refresh_token()
        self.db.add(RefreshToken(
            family_id=family.id, user_id=owner.id, jti=refresh_jti,
            hashed_token=hashed_refresh,
            expires_at=utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        ))
        await self.db.commit()
        return {
            "tenant_id": str(pending.created_tenant_id),
            "user_id": str(pending.created_user_id),
            "enrollment_status": "draft_setup",
            "tenant_status": tenant.status,
            "vertical_key": pending.selected_vertical_key,
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "message": "This registration was already completed.",
            "replayed": True,
        }

    # ── Status-aware routing support ─────────────────────────────────────────
    async def get_status(self, registration_id: uuid.UUID | None, user: User | None) -> dict:
        if user and user.tenant_id:
            tenant = (await self.db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
            enrollment = (await self.db.execute(
                select(TenantVerticalEnrollment).where(TenantVerticalEnrollment.tenant_id == user.tenant_id)
            )).scalars().first()
            return {
                "stage": self._compute_stage(tenant, enrollment),
                "tenant_status": tenant.status if tenant else None,
                "verification_status": tenant.verification_status if tenant else None,
                "enrollment_status": enrollment.status if enrollment else None,
            }
        if registration_id:
            pending = (await self.db.execute(
                select(PendingTenantRegistration).where(PendingTenantRegistration.id == registration_id)
            )).scalar_one_or_none()
            if not pending:
                return {"stage": "not_found"}
            if pending.status == "completed":
                return {"stage": "completed", "tenant_id": str(pending.created_tenant_id)}
            return {"stage": self._resume_step(pending), "registration_id": str(pending.id)}
        return {"stage": "unknown"}

    def _resume_step(self, pending: PendingTenantRegistration) -> str:
        if not (pending.mobile_verified and pending.email_verified):
            return "verify_contact"
        if not (pending.legal_name or pending.business_name):
            return "business_identity"
        if not pending.selected_vertical_key:
            return "select_vertical"
        return "review_consent"

    def _compute_stage(self, tenant: Tenant | None, enrollment: TenantVerticalEnrollment | None) -> str:
        if not tenant:
            return "unknown"
        if tenant.status == "suspended":
            return "suspended"
        if not enrollment:
            return "setup_incomplete"
        return {
            "draft_setup": "setup_incomplete",
            "draft": "setup_incomplete",
            "submitted": "submitted",
            "under_review": "submitted",
            "changes_requested": "changes_requested",
            "approved": "approved_pending_activation",
            "active": "active",
            "rejected": "rejected",
            "suspended": "suspended",
        }.get(enrollment.status, "setup_incomplete")
