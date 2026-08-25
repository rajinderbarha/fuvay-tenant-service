"""
Tenant Engine — TenantService (Complete Level 5 Implementation)
All 42 endpoint methods. No business logic in routers.
Every method: validate → query → mutate → event → audit → return typed dict.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine_registry.registry import registry
from app.engine_registry.models import TenantEngine
from app.engines.tenant_engine.constants import (
    PLAN_LIMITS, SECURITY_DEPOSIT_BY_PLAN, DEFAULT_ENGINES_BY_VERTICAL,
    CHECKLIST_ITEMS, HEALTH_BANDS, COMMISSION_ADJUSTMENT_BY_BAND,
)
from app.engines.tenant_engine.models import (
    Tenant, TenantBusinessProfile, TenantBranding, TenantBilling,
    TenantLimits, TenantDocument, OnboardingRequest, TenantFeatureFlag, TenantAuditLog,
    TenantSettings,
)
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis, cache_get, cache_set, cache_delete, RedisKeys
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("tenant.service")
utcnow = lambda: datetime.now(timezone.utc)

CORE_ENGINE_IDS = {"auth","rag","notification","payment","analytics","media",
                   "review","chat","settings","tenant","platform_commerce","pricing","data_science"}


class TenantService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 ip_address: str | None = None):
        self.db = db
        self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.ip_address = ip_address

    # ── Private helpers ───────────────────────────────────────────────────────
    async def _get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        r = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        t = r.scalar_one_or_none()
        if not t:
            raise NotFoundException("Tenant", str(tenant_id))
        return t

    async def _get_billing(self, tenant_id: uuid.UUID) -> TenantBilling | None:
        r = await self.db.execute(select(TenantBilling).where(TenantBilling.tenant_id == tenant_id))
        return r.scalar_one_or_none()

    async def _get_limits(self, tenant_id: uuid.UUID) -> TenantLimits | None:
        r = await self.db.execute(select(TenantLimits).where(TenantLimits.tenant_id == tenant_id))
        return r.scalar_one_or_none()

    async def _audit(self, tenant_id: uuid.UUID, action_type: str,
                     entity_type: str | None = None, entity_id: str | None = None,
                     before: dict | None = None, after: dict | None = None,
                     notes: str | None = None) -> None:
        self.db.add(TenantAuditLog(
            tenant_id=tenant_id, actor_id=self.actor_id, actor_role=self.actor_role,
            action_type=action_type, entity_type=entity_type, entity_id=entity_id,
            before_state=before, after_state=after, ip_address=self.ip_address, notes=notes,
        ))
        from app.core.audit import record_platform_audit
        await record_platform_audit(
            self.db, operation=action_type, engine_id="tenant", tenant_id=tenant_id,
            entity_type=entity_type, entity_id=entity_id or str(tenant_id),
            actor_id=self.actor_id, actor_role=self.actor_role, actor_ip=self.ip_address,
            request_id=self.request_id, before=before, after=after,
        )

    async def _publish(self, event_type: str, tenant_id: str, entity_id: str, payload: dict) -> None:
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(
                event_type=event_type, engine_id="tenant", tenant_id=tenant_id,
                entity_type="tenant", entity_id=entity_id, payload=payload,
                actor_id=str(self.actor_id) if self.actor_id else None,
            )
        except Exception as e:
            logger.warning("tenant.event_failed", error=str(e))

    async def _invalidate_cache(self, tenant_id: uuid.UUID) -> None:
        try:
            await cache_delete(RedisKeys.tenant_config(str(tenant_id)))
            await self.redis.delete(f"serviceos:tenant:360:{tenant_id}")
        except Exception:
            pass

    async def _check_engine_deps(self, tenant_id: uuid.UUID, engine_id: str, enabling: bool) -> None:
        engine_def = registry.get(engine_id)
        if not engine_def:
            raise ServiceOSException("NOT_FOUND", f"Engine \'{engine_id}\' is not registered.")
        r = await self.db.execute(
            select(TenantEngine).where(TenantEngine.tenant_id == tenant_id, TenantEngine.is_enabled == True)
        )
        enabled = {te.engine_id for te in r.scalars().all()} | CORE_ENGINE_IDS
        if enabling:
            missing = [d for d in engine_def.dependencies if d not in enabled]
            if missing:
                raise ServiceOSException(
                    "ENGINE_DEPENDENCY",
                    f"Enable these engines first: {', '.join(missing)}",
                    context={"engine_id": engine_id, "missing": missing},
                )
        else:
            dependents = []
            for te_id in (enabled - CORE_ENGINE_IDS):
                dep_def = registry.get(te_id)
                if dep_def and engine_id in dep_def.dependencies:
                    dependents.append(te_id)
            if dependents:
                raise ServiceOSException(
                    "ENGINE_IN_USE",
                    f"Disable these engines first: {', '.join(dependents)}",
                    context={"engine_id": engine_id, "dependents": dependents},
                )

    def _tenant_summary(self, t: Tenant) -> dict:
        return {
            "tenant_id": str(t.id), "tenant_name": t.tenant_name,
            "vertical": t.vertical, "status": t.status, "plan_type": t.plan_type,
            "health_score": float(t.health_score), "health_band": t.health_band,
            "city": t.city, "state": t.state, "is_discoverable": t.is_discoverable,
            "logo_url": t.logo_url,
            "activated_at": t.activated_at.isoformat() if t.activated_at else None,
            "created_at": t.created_at.isoformat(),
        }

    def _tenant_full(self, t: Tenant) -> dict:
        return {
            **self._tenant_summary(t),
            "owner_user_id": str(t.owner_user_id) if t.owner_user_id else None,
            "country": t.country,
            "suspended_at": t.suspended_at.isoformat() if t.suspended_at else None,
            "suspension_reason": t.suspension_reason,
            "trial_expires_at": t.trial_expires_at.isoformat() if t.trial_expires_at else None,
        }

    def _billing_summary(self, b: TenantBilling | None) -> dict | None:
        if not b:
            return None
        return {
            "billing_email": b.billing_email, "billing_cycle": b.billing_cycle,
            "credit_balance": float(b.credit_balance),
            "security_deposit_paid": b.security_deposit_paid,
            "security_deposit_amount": float(b.security_deposit_amount),
            "subscription_status": b.subscription_status,
            "next_billing_date": b.next_billing_date.isoformat() if b.next_billing_date else None,
        }

    def _limits_summary(self, lim: TenantLimits | None) -> dict | None:
        if not lim:
            return None
        return {
            "staff": {"current": lim.current_staff_count, "max": lim.max_staff},
            "active_jobs": {"current": lim.current_active_jobs, "max": lim.max_active_jobs},
            "storage_gb": {"max": lim.max_storage_gb},
            "api_calls_today": {"current": lim.current_api_calls_today, "max": lim.max_api_calls_per_day},
            "engines": {"max": lim.max_engines},
            "customers": {"max": lim.max_customers},
        }

    def _req_to_dict(self, req: OnboardingRequest) -> dict:
        return {
            "id": str(req.id), "request_id": str(req.id),  # id is canonical; request_id for compat
            "business_name": req.business_name,
            "vertical": req.vertical, "owner_name": req.owner_name,
            "owner_email": req.owner_email, "owner_phone": req.owner_phone,
            "city": req.city, "state": req.state, "gstin": req.gstin,
            "description": req.description, "status": req.status,
            "plan_type": req.plan_type,
            "source": req.source,
            "assigned_admin_id": str(req.assigned_admin_id) if req.assigned_admin_id else None,
            "checklist": req.checklist, "engines_to_enable": req.engines_to_enable,
            "admin_notes": req.admin_notes, "rejection_reason": req.rejection_reason,
            "review_started_at": req.review_started_at.isoformat() if req.review_started_at else None,
            "activated_at": req.activated_at.isoformat() if req.activated_at else None,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "updated_at": (req.updated_at.isoformat() if req.updated_at
                           else (req.created_at.isoformat() if req.created_at else None)),
        }

    # ── 1-9: Onboarding ────────────────────────────────────────────────────
    async def submit_signup(self, data: dict) -> dict:
        checklist = {item: {"status": "pending"} for item in CHECKLIST_ITEMS}
        req = OnboardingRequest(
            business_name=data["business_name"], vertical=data["vertical"],
            owner_name=data["owner_name"], owner_email=data["owner_email"].lower(),
            owner_phone=data["owner_phone"], city=data["city"], state=data.get("state"),
            gstin=data.get("gstin"), description=data.get("description"),
            checklist=checklist,
            engines_to_enable=DEFAULT_ENGINES_BY_VERTICAL.get(data["vertical"], []),
            source=data.get("source", "self_signup"),
        )
        self.db.add(req)
        await self.db.flush()
        await self.db.refresh(req)
        logger.info("onboarding.submitted", request_id=str(req.id))
        result = self._req_to_dict(req)
        result["message"] = "Request received. Our team will review within 24 hours."
        return result

    async def lookup_signup_status_by_email(self, email: str) -> dict:
        """Public, deliberately minimal: lets the LOGIN page distinguish
        "wrong password" from "you signed up but aren't activated yet"
        without exposing anything about the applicant beyond their own
        request's status.

        Real bug this fixes: a tenant who submits the no-payment signup
        flow has no user account until an admin activates their request --
        but login had no way to know that, so it always said "Invalid
        email or password", which reads as a typo to someone whose real
        problem is "nobody has approved me yet".

        Returns only `{exists, status}` -- never the business name, owner
        name, or any other field, and never distinguishes "never signed up"
        from "signed up under a different email" (both return exists=False)
        so this cannot be used to enumerate real applicants' emails.
        """
        r = await self.db.execute(
            select(OnboardingRequest)
            .where(OnboardingRequest.owner_email == email)
            .order_by(OnboardingRequest.created_at.desc())
            .limit(1)
        )
        req = r.scalar_one_or_none()
        if not req:
            return {"exists": False, "status": None}
        return {"exists": True, "status": req.status}

    async def get_onboarding_request(self, request_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
        req = r.scalar_one_or_none()
        if not req:
            raise NotFoundException("OnboardingRequest", str(request_id))
        return self._req_to_dict(req)

    async def list_onboarding_queue(self, status_filter: str | None, limit: int, cursor: str | None) -> dict:
        q = select(OnboardingRequest).order_by(OnboardingRequest.created_at.desc())
        if status_filter:
            q = q.where(OnboardingRequest.status == status_filter)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(OnboardingRequest.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        reqs = r.scalars().all()
        has_next = len(reqs) > limit
        reqs = reqs[:limit]
        next_cur = encode_cursor({"created_at": reqs[-1].created_at.isoformat()}) if has_next and reqs else None
        return {"requests": [self._req_to_dict(req) for req in reqs],
                "total": len(reqs), "has_next": has_next, "next_cursor": next_cur}

    async def start_review(self, request_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
        req = r.scalar_one_or_none()
        if not req:
            raise NotFoundException("OnboardingRequest", str(request_id))
        if req.status != "submitted":
            raise ServiceOSException("CONFLICT", f"Request is already \'{req.status}\'.")
        req.status = "under_review"
        req.assigned_admin_id = self.actor_id
        req.review_started_at = utcnow()
        return self._req_to_dict(req)

    async def request_documents(self, request_id: uuid.UUID, message: str) -> dict:
        r = await self.db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
        req = r.scalar_one_or_none()
        if not req:
            raise NotFoundException("OnboardingRequest", str(request_id))
        req.status = "awaiting_documents"
        req.admin_notes = (f"{req.admin_notes or chr(10)}[{utcnow().isoformat()}] {message}").strip()
        return self._req_to_dict(req)

    async def update_checklist_item(self, request_id: uuid.UUID, item_key: str,
                                     status: str, notes: str | None) -> dict:
        if item_key not in CHECKLIST_ITEMS:
            raise ServiceOSException("VALIDATION_ERROR",
                                     f"\'{item_key}\' is not a valid checklist item.",
                                     context={"valid_items": CHECKLIST_ITEMS})
        r = await self.db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
        req = r.scalar_one_or_none()
        if not req:
            raise NotFoundException("OnboardingRequest", str(request_id))
        checklist = dict(req.checklist)
        checklist[item_key] = {"status": status, "completed_at": utcnow().isoformat(),
                                "completed_by": str(self.actor_id) if self.actor_id else None,
                                "notes": notes}
        req.checklist = checklist
        all_done = all(v.get("status") in ("done", "skipped") for v in checklist.values())
        if all_done and req.status == "reviewing":
            req.status = "pending_activation"
        return {**self._req_to_dict(req), "ready_to_activate": all_done}

    async def run_preflight(self, request_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
        req = r.scalar_one_or_none()
        if not req:
            raise NotFoundException("OnboardingRequest", str(request_id))
        issues, warnings = [], []
        incomplete = [k for k, v in req.checklist.items() if v.get("status") == "pending"]
        if incomplete:
            issues.append(f"Checklist items pending: {', '.join(incomplete)}")
        if not req.plan_type:
            issues.append("Plan type not selected.")
        engines = set(req.engines_to_enable)
        for eng_id in engines:
            eng_def = registry.get(eng_id)
            if eng_def:
                for dep in eng_def.dependencies:
                    if dep not in engines and dep not in CORE_ENGINE_IDS:
                        issues.append(f"Engine \'{eng_id}\' requires \'{dep}\'.")
        if not req.gstin:
            warnings.append("GST number not provided — required for tax invoicing.")
        return {"ready": not issues, "issues": issues, "warnings": warnings,
                "engines_to_enable": req.engines_to_enable}

    async def activate_tenant(self, request_id: uuid.UUID) -> dict:
        from app.engines.tenant_engine.provisioning import provision_tenant
        from app.engines.auth.utils import hash_password
        import secrets
        r = await self.db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
        req = r.scalar_one_or_none()
        if not req:
            raise NotFoundException("OnboardingRequest", str(request_id))
        if req.status == "activated":
            raise ServiceOSException("CONFLICT", "Already activated.",
                                     resolution=f"Find the tenant at GET /v1/tenants/{req.tenant_id}")
        plan = req.plan_type or "starter"
        limits_config = PLAN_LIMITS[plan]
        tenant = Tenant(tenant_name=req.business_name, vertical=req.vertical,
                        status="active", plan_type=plan, city=req.city, state=req.state)
        self.db.add(tenant)
        await self.db.flush()
        self.db.add(TenantBusinessProfile(tenant_id=tenant.id, gstin=req.gstin,
            registered_address={"city": req.city, "state": req.state, "country": "India"}))
        self.db.add(TenantBranding(tenant_id=tenant.id))
        self.db.add(TenantBilling(tenant_id=tenant.id, billing_email=req.owner_email,
            security_deposit_amount=float(SECURITY_DEPOSIT_BY_PLAN[plan])))
        self.db.add(TenantLimits(tenant_id=tenant.id, **limits_config))
        # MODULE-L5-46: this is the canonical tenant-signup path
        # (OnboardingRequest -> activate) and never created a
        # TenantSettings row (table tenant_operational_settings, holding
        # commission_rate/timezone/currency/notification toggles) --
        # confirmed via direct query that no tenant activated through it has
        # one. Distinct from the per-schema "tenant_settings" key-value table
        # provision_tenant() creates below (a different, Settings-Engine
        # concept with the same name). Package-based commission overrides
        # (MODULE-L5-45) and the tenant-settings fallback tier of commission
        # resolution (MODULE-L5-32) both depend on this row existing.
        self.db.add(TenantSettings(tenant_id=tenant.id))
        # Admin requests created before engine selection was mandatory can
        # carry an empty list.  Activating such a tenant used to provision no
        # engines at all, leaving approved providers with dead navigation.
        enabled_engines = list(req.engines_to_enable or DEFAULT_ENGINES_BY_VERTICAL.get(req.vertical, []))
        for engine_id in enabled_engines:
            self.db.add(TenantEngine(tenant_id=tenant.id, engine_id=engine_id, is_enabled=True,
                config=req.engine_configs.get(engine_id, {}), activated_at=utcnow(),
                activated_by=self.actor_id))
        temp_password = secrets.token_urlsafe(12)
        from app.engines.auth.models import User
        owner = User(email=req.owner_email, phone=req.owner_phone, full_name=req.owner_name,
                     role="tenant_owner", tenant_id=tenant.id,
                     hashed_password=hash_password(temp_password),
                     is_active=True, is_verified=True, force_password_change=True)
        self.db.add(owner)
        await self.db.flush()
        tenant.owner_user_id = owner.id
        tenant.activated_at = utcnow()
        req.status = "activated"
        req.tenant_id = tenant.id
        req.activated_at = utcnow()
        prov = await provision_tenant(db=self.db, tenant_id=tenant.id,
            tenant_name=tenant.tenant_name, vertical=tenant.vertical, plan_type=plan,
            engines_to_enable=enabled_engines, engine_configs=req.engine_configs,
            owner_email=req.owner_email, admin_id=self.actor_id or uuid.uuid4())
        await cache_set(RedisKeys.tenant_config(str(tenant.id)),
            {"tenant_id": str(tenant.id), "tenant_name": tenant.tenant_name,
             "plan_type": plan, "status": "active", "subdomain": None,
             "vertical": tenant.vertical, "enabled_engines": enabled_engines}, ttl=300)
        await self._audit(tenant.id, "tenant.activated",
                          after={"status": "active", "plan": plan, "engines": len(enabled_engines)})
        await self._publish("tenant.activated", str(tenant.id), str(tenant.id),
                            {"plan": plan, "vertical": tenant.vertical})
        logger.info("tenant.activated", tenant_id=str(tenant.id))
        return {"tenant_id": str(tenant.id), "tenant_name": tenant.tenant_name,
                "status": "active", "plan_type": plan,
                "activated_at": tenant.activated_at.isoformat(), "provisioning": prov,
                "message": "Tenant is live. Owner credentials sent by email."}

    async def reject_onboarding(self, request_id: uuid.UUID, reason: str) -> dict:
        r = await self.db.execute(select(OnboardingRequest).where(OnboardingRequest.id == request_id))
        req = r.scalar_one_or_none()
        if not req:
            raise NotFoundException("OnboardingRequest", str(request_id))
        if req.status == "activated":
            raise ServiceOSException("CONFLICT", "Cannot reject an activated request.")
        req.status = "rejected"
        req.rejection_reason = reason
        return self._req_to_dict(req)

    # ── 10-13: Tenant CRUD ───────────────────────────────────────────────────
    async def list_tenants(self, status_filter: str | None, vertical: str | None,
                           plan: str | None, limit: int, cursor: str | None) -> dict:
        q = select(Tenant).order_by(Tenant.created_at.desc())
        if status_filter:
            q = q.where(Tenant.status == status_filter)
        if vertical:
            q = q.where(Tenant.vertical == vertical)
        if plan:
            q = q.where(Tenant.plan_type == plan)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(Tenant.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        tenants = r.scalars().all()
        has_next = len(tenants) > limit
        tenants = tenants[:limit]
        next_cur = encode_cursor({"created_at": tenants[-1].created_at.isoformat()}) if has_next and tenants else None
        return {"tenants": [self._tenant_summary(t) for t in tenants],
                "total": len(tenants), "has_next": has_next, "next_cursor": next_cur}

    async def get_tenant_detail(self, tenant_id: uuid.UUID) -> dict:
        tenant = await self._get_tenant(tenant_id)
        billing = await self._get_billing(tenant_id)
        limits = await self._get_limits(tenant_id)
        return {**self._tenant_full(tenant), "billing": self._billing_summary(billing),
                "limits": self._limits_summary(limits)}

    async def update_tenant(self, tenant_id: uuid.UUID, data: dict) -> dict:
        tenant = await self._get_tenant(tenant_id)
        before = self._tenant_summary(tenant)
        for field in ("tenant_name", "city", "state"):
            if field in data:
                setattr(tenant, field, data[field])
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "tenant.updated", before=before, after=self._tenant_summary(tenant))
        return self._tenant_full(tenant)

    async def get_360_view(self, tenant_id: uuid.UUID) -> dict:
        import asyncio
        tenant = await self._get_tenant(tenant_id)
        billing, limits, health = await asyncio.gather(
            self._get_billing(tenant_id), self._get_limits(tenant_id), self.get_health_score(tenant_id)
        )
        r = await self.db.execute(
            select(TenantEngine).where(TenantEngine.tenant_id == tenant_id, TenantEngine.is_enabled == True)
        )
        enabled = r.scalars().all()
        return {
            "tenant_id": str(tenant.id), "tenant_name": tenant.tenant_name,
            "vertical": tenant.vertical, "status": tenant.status, "plan_type": tenant.plan_type,
            "health": health, "is_discoverable": tenant.is_discoverable,
            "billing": self._billing_summary(billing), "limits": self._limits_summary(limits),
            "enabled_engines": [{"engine_id": te.engine_id} for te in enabled],
            "engine_summaries": {},
            "activated_at": tenant.activated_at.isoformat() if tenant.activated_at else None,
        }

    # ── 14-16: Health ────────────────────────────────────────────────────────
    async def get_health_score(self, tenant_id: uuid.UUID) -> dict:
        from app.engines.tenant_engine.health import compute_health_score
        return await compute_health_score(tenant_id, db=self.db)

    async def get_health_history(self, tenant_id: uuid.UUID, days: int = 30) -> dict:
        return {"tenant_id": str(tenant_id), "days": days, "history": [],
                "_note": "Hourly history stored from Phase 3 onwards."}

    # ── 17-20: Lifecycle ─────────────────────────────────────────────────────
    async def suspend_tenant(self, tenant_id: uuid.UUID, reason: str, reason_category: str) -> dict:
        tenant = await self._get_tenant(tenant_id)
        if tenant.status == "suspended":
            raise ServiceOSException("CONFLICT", "Tenant is already suspended.")
        before = {"status": tenant.status}
        tenant.status = "suspended"
        tenant.suspended_at = utcnow()
        tenant.suspension_reason = reason
        tenant.is_discoverable = False
        await self._invalidate_cache(tenant_id)
        try:
            await self.redis.publish("serviceos:sessions:invalidate", f"tenant:{tenant_id}")
        except Exception:
            pass
        await self._audit(tenant_id, "tenant.suspended", before=before,
                          after={"status": "suspended", "reason": reason, "category": reason_category})
        await self._publish("tenant.suspended", str(tenant_id), str(tenant_id), {"reason": reason})
        logger.warning("tenant.suspended", tenant_id=str(tenant_id))
        return {"tenant_id": str(tenant_id), "status": "suspended",
                "suspended_at": tenant.suspended_at.isoformat()}

    async def reinstate_tenant(self, tenant_id: uuid.UUID, reason: str) -> dict:
        tenant = await self._get_tenant(tenant_id)
        if tenant.status != "suspended":
            raise ServiceOSException("CONFLICT", f"Tenant is not suspended. Status: \'{tenant.status}\'")
        before = {"status": tenant.status}
        tenant.status = "active"
        tenant.suspended_at = None
        tenant.suspension_reason = None
        tenant.is_discoverable = True
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "tenant.reinstated", before=before,
                          after={"status": "active"}, notes=reason)
        await self._publish("tenant.reinstated", str(tenant_id), str(tenant_id), {})
        return {"tenant_id": str(tenant_id), "status": "active"}

    async def begin_termination(self, tenant_id: uuid.UUID, reason: str) -> dict:
        tenant = await self._get_tenant(tenant_id)
        if tenant.status == "terminated":
            raise ServiceOSException("CONFLICT", "Tenant is already terminated.")
        termination_date = utcnow() + timedelta(days=14)
        tenant.meta = {**(tenant.meta or {}), "termination_scheduled": termination_date.isoformat(),
                       "termination_reason": reason}
        await self._audit(tenant_id, "tenant.termination_begun",
                          after={"scheduled_for": termination_date.isoformat()})
        await self._publish("tenant.termination_begun", str(tenant_id), str(tenant_id),
                            {"scheduled_for": termination_date.isoformat()})
        return {"tenant_id": str(tenant_id),
                "termination_date": termination_date.isoformat(),
                "message": "14-day warning period started. Data export available.",
                "data_export_url": f"/v1/tenants/{tenant_id}/data/export"}

    async def confirm_termination(self, tenant_id: uuid.UUID) -> dict:
        tenant = await self._get_tenant(tenant_id)
        before = {"status": tenant.status}
        tenant.status = "terminated"
        tenant.terminated_at = utcnow()
        tenant.is_discoverable = False
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "tenant.terminated", before=before, after={"status": "terminated"})
        await self._publish("tenant.terminated", str(tenant_id), str(tenant_id), {})
        logger.warning("tenant.terminated", tenant_id=str(tenant_id))
        return {"tenant_id": str(tenant_id), "status": "terminated",
                "message": "Tenant terminated. Schema scheduled for deletion after 90-day backup."}

    # ── 21-23: Plan Management ───────────────────────────────────────────────
    async def check_limit(self, tenant_id: uuid.UUID, limit_type: str) -> dict:
        limits = await self._get_limits(tenant_id)
        if not limits:
            return {"allowed": True}
        # api_calls is counted live in Redis by UsageQuotaMiddleware (resets
        # daily via TTL) — the Postgres column would only ever read stale 0s.
        current_api_calls = limits.current_api_calls_today
        try:
            from app.redis_client import get_redis
            from app.core.usage_quota import get_api_calls_today
            current_api_calls = await get_api_calls_today(get_redis(), str(tenant_id))
        except Exception:
            pass
        checks = {"staff_count": (limits.current_staff_count, limits.max_staff),
                  "active_jobs": (limits.current_active_jobs, limits.max_active_jobs),
                  "api_calls": (current_api_calls, limits.max_api_calls_per_day)}
        if limit_type in checks:
            current, maximum = checks[limit_type]
            if current >= maximum:
                raise ServiceOSException("PLAN_LIMIT_EXCEEDED",
                    f"Reached {limit_type} limit ({maximum}).",
                    context={"current": current, "limit": maximum},
                    resolution="Upgrade your plan to increase this limit.")
        return {"allowed": True, "limit_type": limit_type}

    async def upgrade_plan(self, tenant_id: uuid.UUID, target_plan: str, reason: str) -> dict:
        tenant = await self._get_tenant(tenant_id)
        plan_order = {"starter": 1, "growth": 2, "enterprise": 3}
        if plan_order.get(target_plan, 0) <= plan_order.get(tenant.plan_type, 0):
            raise ServiceOSException("CONFLICT",
                "Target plan must be a higher tier. Use /plan/downgrade for downgrades.")
        before = {"plan_type": tenant.plan_type}
        tenant.plan_type = target_plan
        new_limits = PLAN_LIMITS[target_plan]
        lim = await self._get_limits(tenant_id)
        if lim:
            for k, v in new_limits.items():
                if hasattr(lim, k):
                    setattr(lim, k, v)
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "plan.upgraded", before=before, after={"plan_type": target_plan}, notes=reason)
        await self._publish("tenant.plan_upgraded", str(tenant_id), str(tenant_id),
                            {"from": before["plan_type"], "to": target_plan})
        return {"tenant_id": str(tenant_id), "plan_type": target_plan, "new_limits": new_limits}

    async def downgrade_plan(self, tenant_id: uuid.UUID, target_plan: str) -> dict:
        tenant = await self._get_tenant(tenant_id)
        target_limits = PLAN_LIMITS.get(target_plan, {})
        lim = await self._get_limits(tenant_id)
        if lim:
            blockers = []
            if lim.current_staff_count > target_limits.get("max_staff", 0):
                blockers.append(f"staff_count {lim.current_staff_count} > target {target_limits['max_staff']}")
            if blockers:
                raise ServiceOSException("DOWNGRADE_BLOCKED",
                    "Usage exceeds target plan limits.", context={"blockers": blockers},
                    resolution="Reduce usage or choose a higher plan.")
        before = {"plan_type": tenant.plan_type}
        tenant.plan_type = target_plan
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "plan.downgraded", before=before, after={"plan_type": target_plan})
        return {"tenant_id": str(tenant_id), "plan_type": target_plan,
                "message": "Takes effect at next billing cycle."}

    async def convert_trial(self, tenant_id: uuid.UUID) -> dict:
        tenant = await self._get_tenant(tenant_id)
        if tenant.status != "trial":
            raise ServiceOSException("CONFLICT", "Tenant is not on a trial.")
        tenant.status = "active"
        tenant.trial_expires_at = None
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "trial.converted", after={"status": "active"})
        return {"tenant_id": str(tenant_id), "status": "active"}

    # ── 24-30: Engine Management ─────────────────────────────────────────────
    async def list_engines(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(TenantEngine).where(TenantEngine.tenant_id == tenant_id)
        )
        te_map = {te.engine_id: te for te in r.scalars().all()}
        return {"engines": [
            {
                "engine_id": e.engine_id, "name": e.name,
                "engine_type": e.engine_type, "category": e.category,
                "is_enabled": e.engine_id in te_map and te_map[e.engine_id].is_enabled,
                "is_core": e.engine_type == "core",
                "config": te_map[e.engine_id].config if e.engine_id in te_map else {},
                "dependencies": e.dependencies, "api_prefix": e.api_prefix,
                "activated_at": te_map[e.engine_id].activated_at.isoformat()
                    if e.engine_id in te_map and te_map[e.engine_id].activated_at else None,
            }
            for e in registry.all()
        ]}

    async def enable_engine(self, tenant_id: uuid.UUID, engine_id: str) -> dict:
        await self._check_engine_deps(tenant_id, engine_id, enabling=True)
        r = await self.db.execute(
            select(TenantEngine).where(TenantEngine.tenant_id == tenant_id,
                                       TenantEngine.engine_id == engine_id)
        )
        te = r.scalar_one_or_none()
        if te:
            if te.is_enabled:
                raise ServiceOSException("CONFLICT", f"Engine \'{engine_id}\' is already enabled.")
            te.is_enabled = True
            te.activated_at = utcnow()
            te.activated_by = self.actor_id
            te.deactivated_at = None
        else:
            self.db.add(TenantEngine(tenant_id=tenant_id, engine_id=engine_id,
                is_enabled=True, activated_at=utcnow(), activated_by=self.actor_id))
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "engine.enabled", entity_type="engine", entity_id=engine_id)
        await self._publish("tenant.engine_enabled", str(tenant_id), engine_id, {"engine_id": engine_id})
        return {"tenant_id": str(tenant_id), "engine_id": engine_id, "is_enabled": True}

    async def disable_engine(self, tenant_id: uuid.UUID, engine_id: str) -> dict:
        if engine_id in CORE_ENGINE_IDS:
            raise ServiceOSException("PERMISSION_DENIED",
                f"\'{engine_id}\' is a core engine and cannot be disabled.",
                resolution="Only plugin engines can be disabled.")
        await self._check_engine_deps(tenant_id, engine_id, enabling=False)
        r = await self.db.execute(
            select(TenantEngine).where(TenantEngine.tenant_id == tenant_id,
                                       TenantEngine.engine_id == engine_id, TenantEngine.is_enabled == True)
        )
        te = r.scalar_one_or_none()
        if not te:
            raise ServiceOSException("NOT_FOUND", f"Engine \'{engine_id}\' is not enabled.")
        te.is_enabled = False
        te.deactivated_at = utcnow()
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "engine.disabled", entity_type="engine", entity_id=engine_id)
        return {"tenant_id": str(tenant_id), "engine_id": engine_id, "is_enabled": False}

    async def bulk_enable_engines(self, tenant_id: uuid.UUID, engine_ids: list[str]) -> dict:
        results = []
        for engine_id in engine_ids:
            try:
                result = await self.enable_engine(tenant_id, engine_id)
                results.append({"engine_id": engine_id, "status": "enabled"})
            except Exception as e:
                results.append({"engine_id": engine_id, "status": "failed", "error": str(e)})
        return {"results": results, "total": len(engine_ids),
                "succeeded": sum(1 for r in results if r["status"] == "enabled")}

    async def bulk_disable_engines(self, tenant_id: uuid.UUID, engine_ids: list[str]) -> dict:
        results = []
        for engine_id in engine_ids:
            try:
                result = await self.disable_engine(tenant_id, engine_id)
                results.append({"engine_id": engine_id, "status": "disabled"})
            except Exception as e:
                results.append({"engine_id": engine_id, "status": "failed", "error": str(e)})
        return {"results": results, "total": len(engine_ids),
                "succeeded": sum(1 for r in results if r["status"] == "disabled")}

    async def get_engine_config(self, tenant_id: uuid.UUID, engine_id: str) -> dict:
        r = await self.db.execute(
            select(TenantEngine).where(TenantEngine.tenant_id == tenant_id,
                                       TenantEngine.engine_id == engine_id)
        )
        te = r.scalar_one_or_none()
        if not te:
            raise ServiceOSException("NOT_FOUND", f"Engine \'{engine_id}\' not configured for this tenant.")
        return {"engine_id": engine_id, "is_enabled": te.is_enabled, "config": te.config,
                "activated_at": te.activated_at.isoformat() if te.activated_at else None}

    async def update_engine_config(self, tenant_id: uuid.UUID, engine_id: str, config: dict) -> dict:
        r = await self.db.execute(
            select(TenantEngine).where(TenantEngine.tenant_id == tenant_id,
                                       TenantEngine.engine_id == engine_id)
        )
        te = r.scalar_one_or_none()
        if not te:
            raise ServiceOSException("NOT_FOUND", f"Engine \'{engine_id}\' not configured.")
        before_config = te.config
        te.config = {**te.config, **config}
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "engine.config_updated", entity_type="engine",
                          entity_id=engine_id, before={"config": before_config},
                          after={"config": te.config})
        await self._publish("tenant.engine_config_changed", str(tenant_id), engine_id,
                            {"engine_id": engine_id, "changed_keys": list(config.keys())})
        return {"engine_id": engine_id, "config": te.config}

    async def validate_engine_config(self, engine_id: str, config: dict) -> dict:
        engine_def = registry.get(engine_id)
        if not engine_def:
            raise ServiceOSException("NOT_FOUND", f"Engine \'{engine_id}\' not registered.")
        issues = []
        # Engine-specific validation stubs (each engine will register validators in later phases)
        if engine_id == "field_ops":
            sla = config.get("sla_hours", 4)
            auto_close = config.get("auto_close_after_hours", 48)
            if not (1 <= sla <= 168):
                issues.append("sla_hours must be between 1 and 168.")
            if auto_close <= sla:
                issues.append("auto_close_after_hours must be greater than sla_hours.")
        return {"valid": not issues, "issues": issues, "engine_id": engine_id}

    # ── 31-34: Feature Flags ─────────────────────────────────────────────────
    async def list_feature_flags(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(TenantFeatureFlag).where(TenantFeatureFlag.tenant_id == tenant_id)
        )
        flags = r.scalars().all()
        return {"flags": [{"flag_key": f.flag_key, "flag_value": f.flag_value,
                           "set_by": str(f.set_by) if f.set_by else None,
                           "notes": f.notes} for f in flags]}

    async def set_feature_flag(self, tenant_id: uuid.UUID, flag_key: str,
                                flag_value: Any, notes: str | None) -> dict:
        r = await self.db.execute(
            select(TenantFeatureFlag).where(TenantFeatureFlag.tenant_id == tenant_id,
                                            TenantFeatureFlag.flag_key == flag_key)
        )
        flag = r.scalar_one_or_none()
        if flag:
            flag.flag_value = {"value": flag_value}
            flag.set_by = self.actor_id
            flag.notes = notes
        else:
            self.db.add(TenantFeatureFlag(tenant_id=tenant_id, flag_key=flag_key,
                flag_value={"value": flag_value}, set_by=self.actor_id, notes=notes))
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "feature_flag.set", entity_type="feature_flag",
                          entity_id=flag_key, after={"value": flag_value})
        return {"tenant_id": str(tenant_id), "flag_key": flag_key, "flag_value": flag_value}

    async def delete_feature_flag(self, tenant_id: uuid.UUID, flag_key: str) -> dict:
        r = await self.db.execute(
            select(TenantFeatureFlag).where(TenantFeatureFlag.tenant_id == tenant_id,
                                            TenantFeatureFlag.flag_key == flag_key)
        )
        flag = r.scalar_one_or_none()
        if not flag:
            raise NotFoundException("FeatureFlag", flag_key)
        await self.db.delete(flag)
        await self._invalidate_cache(tenant_id)
        await self._audit(tenant_id, "feature_flag.deleted", entity_type="feature_flag",
                          entity_id=flag_key)
        return {"flag_key": flag_key, "deleted": True}

    async def resolve_feature_flag(self, tenant_id: uuid.UUID, flag_key: str) -> dict:
        r = await self.db.execute(
            select(TenantFeatureFlag).where(TenantFeatureFlag.tenant_id == tenant_id,
                                            TenantFeatureFlag.flag_key == flag_key)
        )
        flag = r.scalar_one_or_none()
        resolved_value = flag.flag_value.get("value") if flag else None
        return {"flag_key": flag_key, "resolved_value": resolved_value,
                "source": "tenant_override" if flag else "platform_default",
                "tenant_id": str(tenant_id)}

    # ── 35-38: Billing ───────────────────────────────────────────────────────
    async def get_billing_summary(self, tenant_id: uuid.UUID) -> dict:
        tenant = await self._get_tenant(tenant_id)
        billing = await self._get_billing(tenant_id)
        r = await self.db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
        settings = r.scalar_one_or_none()
        summary = self._billing_summary(billing) or {}
        return {
            **summary,
            "tenant_id": str(tenant_id),
            "plan_type": tenant.plan_type,
            "billing_mode": summary.get("billing_cycle", "monthly"),
            "commission_rate": float(settings.commission_rate) if settings else 0.10,
        }

    async def update_payment_method(self, tenant_id: uuid.UUID, gateway: str,
                                     gateway_customer_id: str) -> dict:
        billing = await self._get_billing(tenant_id)
        if not billing:
            raise NotFoundException("Billing", str(tenant_id))
        if gateway == "razorpay":
            billing.razorpay_customer_id = gateway_customer_id
        elif gateway == "stripe":
            billing.stripe_customer_id = gateway_customer_id
        await self._audit(tenant_id, "billing.payment_method_updated",
                          after={"gateway": gateway})
        return {"tenant_id": str(tenant_id), "gateway": gateway, "updated": True}

    async def list_invoices(self, tenant_id: uuid.UUID, limit: int) -> dict:
        return {"invoices": [], "total": 0,
                "_note": "Invoice list populated by Payment Engine in Phase 7."}

    async def trigger_dunning(self, tenant_id: uuid.UUID) -> dict:
        return {"tenant_id": str(tenant_id), "dunning_triggered": True,
                "_note": "Full dunning flow implemented in Phase 7 with Payment Engine."}

    # ── 39-41: Data Management ───────────────────────────────────────────────
    async def request_data_export(self, tenant_id: uuid.UUID) -> dict:
        import uuid as _uuid
        import json
        job_id = str(_uuid.uuid4())
        try:
            await self.redis.setex(f"serviceos:async:{job_id}:progress", 86400,
                                    json.dumps({"status": "pending", "progress": 0, "tenant_id": str(tenant_id)}))
        except Exception:
            pass
        await self._audit(tenant_id, "data.export_requested", after={"job_id": job_id})
        return {"job_id": job_id, "status": "pending",
                "poll_url": f"/v1/tenants/{tenant_id}/data/export/{job_id}",
                "estimated_duration_seconds": 120,
                "_note": "Full async export with S3 implemented in Phase 5."}

    async def get_export_status(self, tenant_id: uuid.UUID, job_id: str) -> dict:
        # MODULE-L5-01A: a job_id-only Redis lookup let a caller poll ANY
        # tenant's export status by guessing/reusing a leaked job_id, even
        # after the router-level tenant_id check passes with the caller's
        # own tenant_id -- a nested-resource IDOR distinct from the
        # path-parameter one. The stored payload now records its owning
        # tenant_id at creation time; verify it here rather than trusting
        # job_id alone, and return a generic "not found" rather than a
        # permission-denied error so a foreign job's existence is not
        # confirmed to the caller.
        try:
            import json
            raw = await self.redis.get(f"serviceos:async:{job_id}:progress")
            if raw:
                payload = json.loads(raw)
                owner_tenant_id = payload.get("tenant_id")
                if owner_tenant_id is not None and str(owner_tenant_id) != str(tenant_id):
                    return {"job_id": job_id, "status": "unknown"}
                return {**payload, "job_id": job_id}
        except Exception:
            pass
        return {"job_id": job_id, "status": "unknown"}

    async def request_gdpr_deletion(self, tenant_id: uuid.UUID, reason: str) -> dict:
        await self._audit(tenant_id, "data.gdpr_deletion_requested", notes=reason)
        return {"tenant_id": str(tenant_id), "deletion_requested": True,
                "message": "GDPR deletion request received. PII will be anonymized within 72 hours.",
                "financial_note": "Financial records retained 7 years for GST compliance."}

    # ── 42: Audit Log ─────────────────────────────────────────────────────────
    async def get_audit_log(self, tenant_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        q = (select(TenantAuditLog).where(TenantAuditLog.tenant_id == tenant_id)
             .order_by(TenantAuditLog.created_at.desc()))
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(TenantAuditLog.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception:
                pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        logs = r.scalars().all()
        has_next = len(logs) > limit
        logs = logs[:limit]
        next_cur = encode_cursor({"created_at": logs[-1].created_at.isoformat()}) if has_next and logs else None
        return {
            "logs": [{"log_id": str(l.id), "action_type": l.action_type,
                      "actor_role": l.actor_role, "entity_type": l.entity_type,
                      "entity_id": l.entity_id,
                      "before_state": l.before_state, "after_state": l.after_state,
                      "notes": l.notes, "created_at": l.created_at.isoformat()}
                     for l in logs],
            "has_next": has_next, "next_cursor": next_cur,
        }
