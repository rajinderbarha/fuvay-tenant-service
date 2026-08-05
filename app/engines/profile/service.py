"""Profile Engine — Service for Phase 0C.

Handles:
  - User profile get / update (any role)
  - Business profile get / update (tenant roles)
  - Audit logging for all profile changes
  - Re-verification guard for critical business field changes
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.dependencies.auth import UserContext
from app.engines.auth.models import User
from app.engines.profile.schemas import UpdateUserProfileRequest, UpdateBusinessProfileRequest, CRITICAL_BUSINESS_FIELDS
from app.exceptions import NotFoundException, ServiceOSException

logger = structlog.get_logger("profile.service")
utcnow = lambda: datetime.now(timezone.utc)

# Statuses that trigger re-verification when a critical field changes
_VERIFIED_STATUSES = {"verified", "approved", "active"}
# Fields the user must NOT be able to set
_FORBIDDEN_USER_FIELDS = {"role", "tenant_id", "customer_id", "hashed_password", "is_active",
                          "is_mfa_enabled", "force_password_change", "failed_login_attempts"}


class ProfileService:

    def __init__(self, db: AsyncSession, actor: UserContext) -> None:
        self.db = db
        self.actor = actor

    # ── User profile ──────────────────────────────────────────────────────────

    async def get_user_profile(self) -> dict:
        user = await self._load_user(uuid.UUID(self.actor.user_id))
        return self._serialize_user(user)

    async def update_user_profile(self, body: UpdateUserProfileRequest) -> dict:
        # SECURITY (2026-08-01, Personal Details phase closure): no
        # authenticated contact-change OTP flow exists ANYWHERE in this
        # codebase (confirmed via direct audit of app/engines/auth/router.py
        # -- only the pre-auth LOGIN phone-OTP endpoints exist). Before this
        # fix, `phone` was silently accepted and mutated here with only a
        # uniqueness check, no verification -- an authenticated customer
        # (or anyone with a valid access token) could call this endpoint
        # directly and take over a phone number's association with their
        # account without ever proving they control it. Rejected atomically
        # -- before any other field on the request is applied -- so a
        # request combining a legitimate `full_name` change with a `phone`
        # change never partially succeeds.
        if body.phone is not None:
            raise ServiceOSException(
                "PHONE_CHANGE_REQUIRES_VERIFICATION",
                "Mobile number changes require verification.",
                status_code=422,
            )

        user = await self._load_user(uuid.UUID(self.actor.user_id))

        changed: dict[str, tuple] = {}  # field → (old, new)

        if body.full_name is not None and body.full_name != user.full_name:
            changed["full_name"] = (user.full_name, body.full_name)
            user.full_name = body.full_name

        if body.display_name is not None:
            old = getattr(user, "display_name", None)
            if body.display_name != old:
                changed["display_name"] = (old, body.display_name)
            user.display_name = body.display_name  # type: ignore[attr-defined]

        if body.language is not None:
            old = getattr(user, "language", "en")
            if body.language != old:
                changed["language"] = (old, body.language)
            user.language = body.language  # type: ignore[attr-defined]

        if body.timezone is not None:
            old = getattr(user, "timezone", "UTC")
            if body.timezone != old:
                changed["timezone"] = (old, body.timezone)
            user.timezone = body.timezone  # type: ignore[attr-defined]

        if not changed:
            return self._serialize_user(user)

        await record_platform_audit(
            self.db,
            operation="profile.updated",
            engine_id="profile",
            entity_id=str(user.id),
            entity_type="user",
            actor_id=user.id,
            actor_role=self.actor.role,
            tenant_id=uuid.UUID(self.actor.tenant_id) if self.actor.tenant_id else None,
            after={"changed_fields": list(changed.keys()),
                   "new_values": {k: v[1] for k, v in changed.items() if k != "phone"},
                   "old_values": {k: v[0] for k, v in changed.items() if k != "phone"}},
        )
        logger.info("profile.updated", user_id=str(user.id), fields=list(changed.keys()))
        return self._serialize_user(user)

    # ── Business profile ──────────────────────────────────────────────────────

    async def get_business_profile(self) -> dict:
        tenant = await self._load_tenant()
        return self._serialize_tenant(tenant)

    async def update_business_profile(self, body: UpdateBusinessProfileRequest) -> dict:
        if not self.actor.tenant_id:
            raise ServiceOSException("PROFILE_UPDATE_FORBIDDEN", "No tenant context.")
        tenant = await self._load_tenant()

        current_snapshot = {
            "business_name": tenant.business_name,
            "owner_name": getattr(tenant, "owner_name", None),
            "business_phone": tenant.phone,
            "business_email": tenant.email,
            "address_line1": tenant.address_line1,
            "state": tenant.state,
            "district": tenant.district,
            "city": tenant.city,
            "pincode": tenant.zipcode,
            "gst_number": tenant.gst_number,
        }

        critical_changed = body.changed_critical_fields(current_snapshot)
        changed_keys: list[str] = []

        # Apply non-critical fields
        if body.business_name is not None:
            tenant.business_name = body.business_name
            changed_keys.append("business_name")
        if body.owner_name is not None:
            # owner_name may live in meta if not a direct column
            if hasattr(tenant, "owner_name"):
                tenant.owner_name = body.owner_name  # type: ignore[attr-defined]
            else:
                tenant.meta = {**(tenant.meta or {}), "owner_name": body.owner_name}
            changed_keys.append("owner_name")
        if body.business_phone is not None:
            tenant.phone = body.business_phone
            changed_keys.append("phone")
        if body.business_email is not None:
            tenant.email = body.business_email
            changed_keys.append("email")
        if body.address_line1 is not None:
            tenant.address_line1 = body.address_line1
            changed_keys.append("address_line1")
        if body.address_line2 is not None:
            tenant.address_line2 = body.address_line2
            changed_keys.append("address_line2")
        if body.city is not None:
            tenant.city = body.city
            changed_keys.append("city")
        if body.district is not None:
            tenant.district = body.district
            changed_keys.append("district")
        if body.state is not None:
            tenant.state = body.state
            changed_keys.append("state")
        if body.country is not None:
            tenant.country = body.country
            changed_keys.append("country")
        if body.pincode is not None:
            tenant.zipcode = body.pincode
            changed_keys.append("zipcode")
        if body.gst_number is not None:
            tenant.gst_number = body.gst_number
            changed_keys.append("gst_number")
        if body.legal_name is not None:
            tenant.legal_name = body.legal_name
            changed_keys.append("legal_name")
        if body.business_type is not None:
            tenant.business_type = body.business_type
            changed_keys.append("business_type")
        if body.year_established is not None:
            # Real bug fixed here: `Tenant` has no `year_established` column
            # (it lives on TenantBusinessProfile, a different table) --
            # every save/load of the business profile 500'd. Stored in
            # tenant.meta, the same pattern already used for
            # registration_number/website_url/description below.
            tenant.meta = {**(tenant.meta or {}), "year_established": body.year_established}
            changed_keys.append("year_established")
        if body.registration_number is not None:
            tenant.meta = {**(tenant.meta or {}), "registration_number": body.registration_number}
            changed_keys.append("registration_number")
        if body.website_url is not None:
            tenant.meta = {**(tenant.meta or {}), "website_url": body.website_url}
            changed_keys.append("website_url")
        if body.description is not None:
            tenant.meta = {**(tenant.meta or {}), "description": body.description}
            changed_keys.append("description")

        requires_reverification = False
        if critical_changed and tenant.verification_status in _VERIFIED_STATUSES:
            tenant.verification_status = "changes_pending_review"
            requires_reverification = True

        await record_platform_audit(
            self.db,
            operation="business_profile.updated",
            engine_id="profile",
            entity_id=str(tenant.id),
            entity_type="tenant",
            actor_id=uuid.UUID(self.actor.user_id),
            actor_role=self.actor.role,
            tenant_id=tenant.id,
            after={
                "changed_fields": changed_keys,
                "critical_fields_changed": critical_changed,
                "reverification_triggered": requires_reverification,
            },
        )

        if requires_reverification:
            await record_platform_audit(
                self.db,
                operation="business_profile.reverification_required",
                engine_id="profile",
                entity_id=str(tenant.id),
                entity_type="tenant",
                actor_id=uuid.UUID(self.actor.user_id),
                actor_role=self.actor.role,
                tenant_id=tenant.id,
                after={"critical_fields": critical_changed, "new_status": "changes_pending_review"},
            )

        result = self._serialize_tenant(tenant)
        result["reverification_triggered"] = requires_reverification
        if requires_reverification:
            result["reverification_message"] = (
                "Critical business details were changed. Your account has been flagged for re-verification review. "
                "You can continue using the platform during this period."
            )
        logger.info("business_profile.updated", tenant_id=str(tenant.id),
                    fields=changed_keys, reverification=requires_reverification)
        return result

    # ── Submit for review ────────────────────────────────────────────────────

    # Mirrors the tenant portal's computeCompletion() required-field list
    # (business name, phone, email, GST, address, city+state, logo,
    # description, storefront photo) — kept in sync manually since there is
    # no shared schema between frontend and backend for this checklist.
    REQUIRED_FOR_REVIEW = (
        ("business_name", "Business Name"),
        ("phone", "Business Phone"),
        ("email", "Business Email"),
        ("gst_number", "GST Number"),
        ("address_line1", "Business Address"),
        ("city", "City"),
        ("state", "State"),
        ("logo_url", "Business Logo"),
        ("description", "Business Description"),
        ("shop_photo_media_id", "Storefront Photo"),
    )

    async def submit_business_profile_for_review(self) -> dict:
        tenant = await self._load_tenant()
        meta = tenant.meta or {}

        missing = []
        for field, label in self.REQUIRED_FOR_REVIEW:
            if field == "description":
                value = meta.get("description")
            else:
                value = getattr(tenant, field, None)
            if not value:
                missing.append({"field": field, "label": label})

        if missing:
            raise ServiceOSException(
                "BUSINESS_PROFILE_INCOMPLETE",
                f"You must complete {len(missing)} required item(s) before submitting.",
                status_code=422,
                context={"missing": missing, "missing_count": len(missing)},
            )

        if tenant.verification_status in _VERIFIED_STATUSES:
            result = self._serialize_tenant(tenant)
            result["submitted"] = False
            result["message"] = "Your business profile is already verified."
            return result

        if tenant.verification_status == "pending":
            result = self._serialize_tenant(tenant)
            result["submitted"] = False
            result["message"] = "Your business profile is already under review."
            return result

        old_status = tenant.verification_status
        tenant.verification_status = "pending"

        await record_platform_audit(
            self.db,
            operation="verification_submitted",
            engine_id="profile",
            entity_id=str(tenant.id),
            entity_type="tenant",
            actor_id=uuid.UUID(self.actor.user_id),
            actor_role=self.actor.role,
            tenant_id=tenant.id,
            before={"verification_status": old_status},
            after={"verification_status": "pending"},
        )

        result = self._serialize_tenant(tenant)
        result["submitted"] = True
        result["message"] = "Your business profile has been submitted for admin review."
        logger.info("business_profile.submitted_for_review", tenant_id=str(tenant.id))
        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _load_user(self, user_id: uuid.UUID) -> User:
        r = await self.db.execute(select(User).where(User.id == user_id))
        user = r.scalar_one_or_none()
        if not user:
            raise NotFoundException("User", str(user_id))
        return user

    async def _load_tenant(self):
        from app.engines.tenant_engine.models import Tenant
        if not self.actor.tenant_id:
            raise ServiceOSException("BUSINESS_PROFILE_NOT_FOUND", "No tenant context.")
        r = await self.db.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(self.actor.tenant_id))
        )
        tenant = r.scalar_one_or_none()
        if not tenant:
            raise NotFoundException("Tenant", self.actor.tenant_id)
        return tenant

    @staticmethod
    def _serialize_user(user: User) -> dict:
        return {
            "id": str(user.id),
            "user_id": str(user.id),
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "display_name": getattr(user, "display_name", None),
            "language": getattr(user, "language", "en") or "en",
            "timezone": getattr(user, "timezone", "UTC") or "UTC",
            "role": user.role,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "is_mfa_enabled": user.is_mfa_enabled,
            "avatar_url": user.avatar_url,
            "profile_photo_media_id": str(user.profile_photo_media_id) if getattr(user, "profile_photo_media_id", None) else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat(),
        }

    @staticmethod
    def _serialize_tenant(tenant) -> dict:
        meta = tenant.meta or {}
        return {
            "id": str(tenant.id),
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.tenant_name,
            "business_name": tenant.business_name,
            "legal_name": tenant.legal_name,
            "owner_name": getattr(tenant, "owner_name", None) or meta.get("owner_name"),
            "phone": tenant.phone,
            "email": tenant.email,
            "gst_number": tenant.gst_number,
            "business_type": tenant.business_type,
            "year_established": meta.get("year_established"),
            "registration_number": meta.get("registration_number"),
            "address_line1": tenant.address_line1,
            "address_line2": tenant.address_line2,
            "city": tenant.city,
            "district": tenant.district,
            "state": tenant.state,
            "country": tenant.country,
            "zipcode": tenant.zipcode,
            "logo_url": tenant.logo_url,
            "business_logo_media_id": str(tenant.business_logo_media_id) if tenant.business_logo_media_id else None,
            "shop_photo_media_id": str(tenant.shop_photo_media_id) if tenant.shop_photo_media_id else None,
            "verification_status": tenant.verification_status,
            "status": tenant.status,
            "plan_type": tenant.plan_type,
            "website_url": meta.get("website_url"),
            "description": meta.get("description"),
            "slug": tenant.slug,
            "created_at": tenant.created_at.isoformat(),
        }
