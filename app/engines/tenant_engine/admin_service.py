"""Sprint 4 — AdminTenantService.

Handles all admin-driven tenant operations:
  • Atomic tenant onboarding (creates tenant + owner user + wallet + settings + deposit in one transaction)
  • Tenant CRUD with Sprint 4 fields (category, verification, address, contact)
  • Tenant 360 sub-resources: users, staff, service areas, catalog proxy, pricing, packages, media
  • Security deposit mark-paid, credit top-up/adjustment

Pattern: __init__(db, request_id, actor_id, actor_role)
All writes flush within the same session; the router's db middleware commits on success.
"""
from __future__ import annotations

import json
import re
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.auth.models import User
from app.engines.platform_commerce.models import (
    SecurityDeposit, TenantWallet, WalletTransaction,
)
from app.engines.serviceability.models import TenantServiceArea
from app.engines.tenant_engine.models import (
    Tenant, TenantAuditLog, TenantBilling, TenantBranding,
    TenantLimits, TenantSettings,
)
from app.exceptions import ServiceOSException, NotFoundException

logger = structlog.get_logger("admin_tenant.service")
utcnow = lambda: datetime.now(timezone.utc)


# Phase 2A Slice 2 (non-canonical entry restriction): this set previously
# included "tenant_manager", "tenant_staff_admin", "tenant_finance",
# "tenant_support" -- none of which exist in app.core.permissions
# .ROLE_PERMISSIONS (the actual enforced 10-role RBAC set). A user created
# with one of those role strings got a User.role value the permission
# checker doesn't recognize, so PermissionChecker.has() would silently deny
# every permission check for them forever -- a real, previously-unconfirmed
# bug (distinct from the already-known roles_permissions/service.py
# aspirational-role UI, which is honest about is_implemented=false; this one
# was live-written to the User.role column with no such warning). Restricted
# to the two real, enforced roles this endpoint can legitimately grant.
VALID_TENANT_ROLES = {"tenant_owner", "staff"}
VALID_VERIFICATION_STATUSES = {"not_started", "pending", "approved", "rejected", "changes_requested"}
VALID_TENANT_STATUSES = {
    "pending_verification", "active", "suspended", "rejected", "archived",
    "onboarding_pending",  # backward compat
}
ALLOWED_MEDIA_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "application/pdf",
}
MAX_LOGO_SIZE = 5 * 1024 * 1024    # 5 MB
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 MB


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:80]


def _tenant_code(name: str) -> str:
    letters = re.sub(r"[^a-z0-9]", "", name.lower())[:6].upper()
    suffix = uuid.uuid4().hex[:4].upper()
    return f"TNT-{letters}-{suffix}"


class AdminTenantService:
    def __init__(
        self,
        db: AsyncSession,
        request_id: str = "—",
        actor_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        ip_address: str | None = None,
    ):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.ip_address = ip_address

    # ─── Private helpers ──────────────────────────────────────────────────────

    async def _get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        r = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        t = r.scalar_one_or_none()
        if not t:
            raise NotFoundException("Tenant", str(tenant_id))
        return t

    async def _audit(self, tenant_id: uuid.UUID, action: str,
                     entity_type: str | None = None, entity_id: str | None = None,
                     before: dict | None = None, after: dict | None = None,
                     notes: str | None = None) -> None:
        self.db.add(TenantAuditLog(
            tenant_id=tenant_id, actor_id=self.actor_id, actor_role=self.actor_role,
            action_type=action, entity_type=entity_type, entity_id=entity_id,
            before_state=before, after_state=after, ip_address=self.ip_address, notes=notes,
        ))
        # Also write to the platform-wide audit trail so admin tenant actions
        # (suspend/approve/add-credits/change-plan/etc.) appear in the
        # Platform Command Center's Recent Activity feed — previously only
        # written to the tenant-scoped TenantAuditLog, invisible platform-wide.
        from app.core.audit import record_platform_audit
        await record_platform_audit(
            self.db, operation=action, engine_id="tenant", tenant_id=tenant_id,
            entity_type=entity_type, entity_id=entity_id or str(tenant_id),
            actor_id=self.actor_id, actor_role=self.actor_role, actor_ip=self.ip_address,
            request_id=self.request_id, before=before, after=after,
        )

    def _tenant_dict(self, t: Tenant) -> dict:
        return {
            "tenant_id": str(t.id),
            "tenant_name": t.tenant_name,
            "business_name": t.business_name or t.tenant_name,
            "legal_name": t.legal_name,
            "slug": t.slug,
            "tenant_code": t.tenant_code,
            "vertical": t.vertical,
            "category_id": str(t.category_id) if t.category_id else None,
            "status": t.status,
            "verification_status": t.verification_status,
            "plan_type": t.plan_type,
            "owner_user_id": str(t.owner_user_id) if t.owner_user_id else None,
            "email": t.email,
            "phone": t.phone,
            "gst_number": t.gst_number,
            "business_type": t.business_type,
            "address_line1": t.address_line1,
            "address_line2": t.address_line2,
            "district": t.district,
            "city": t.city,
            "state": t.state,
            "city_tier": t.city_tier,
            "zone_id": str(t.zone_id) if t.zone_id else None,
            "zipcode": t.zipcode,
            "country": t.country,
            "logo_url": t.logo_url,
            "health_score": float(t.health_score),
            "health_band": t.health_band,
            "rating_average": float(t.rating_average),
            "is_discoverable": t.is_discoverable,
            "activated_at": t.activated_at.isoformat() if t.activated_at else None,
            "suspended_at": t.suspended_at.isoformat() if t.suspended_at else None,
            "archived_at": t.archived_at.isoformat() if t.archived_at else None,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }

    # ═══════════════════════════════════════════════════════════════
    # PHASE 2 — ATOMIC TENANT ONBOARDING
    # ═══════════════════════════════════════════════════════════════

    async def onboard_tenant(self, data: dict) -> dict:
        """Atomically create tenant + owner user + wallet + settings + security deposit."""
        biz = data.get("business", {})
        owner = data.get("owner", {})
        commercial = data.get("commercial", {})
        settings = data.get("settings", {})

        # ── Validation ────────────────────────────────────────────────────────
        if not biz.get("business_name", "").strip():
            raise ServiceOSException("TENANT_CATEGORY_REQUIRED",
                                     "business_name is required.")
        if not biz.get("city") or not biz.get("state"):
            raise ServiceOSException("TENANT_CATEGORY_REQUIRED",
                                     "city and state are required.")
        if not owner.get("name") or not owner.get("email") or not owner.get("phone"):
            raise ServiceOSException("TENANT_OWNER_REQUIRED",
                                     "Owner name, email and phone are required.")

        # ── Uniqueness checks ─────────────────────────────────────────────────
        owner_email = owner["email"].lower().strip()
        existing_user = await self.db.execute(
            select(User).where(User.email == owner_email)
        )
        if existing_user.scalar_one_or_none():
            raise ServiceOSException("TENANT_USER_ALREADY_EXISTS",
                                     f"A user with email {owner_email} already exists.")

        business_name = biz["business_name"].strip()
        slug_base = _slugify(business_name)
        slug = slug_base
        # ensure slug uniqueness
        existing_slug = await self.db.execute(
            select(Tenant).where(Tenant.slug == slug)
        )
        if existing_slug.scalar_one_or_none():
            slug = f"{slug_base}-{uuid.uuid4().hex[:6]}"

        # ── 1. Create Tenant ─────────────────────────────────────────────────
        tenant = Tenant(
            tenant_name=business_name,
            business_name=business_name,
            legal_name=biz.get("legal_name"),
            slug=slug,
            tenant_code=_tenant_code(business_name),
            vertical=biz.get("vertical", "home_services"),
            category_id=uuid.UUID(biz["category_id"]) if biz.get("category_id") else None,
            status="pending_verification",
            verification_status="not_started",
            plan_type="starter",
            email=biz.get("email") or owner_email,
            phone=biz.get("phone") or owner.get("phone"),
            gst_number=biz.get("gst_number"),
            business_type=biz.get("business_type"),
            address_line1=biz.get("address_line1"),
            address_line2=biz.get("address_line2"),
            district=biz.get("district"),
            city=biz["city"],
            state=biz["state"],
            zipcode=biz.get("zipcode"),
            country=biz.get("country", "India"),
        )
        self.db.add(tenant)
        await self.db.flush()  # get tenant.id

        # ── 2. Create owner user ──────────────────────────────────────────────
        from app.engines.auth.utils import hash_password
        raw_password = owner.get("password") or secrets.token_urlsafe(12)
        hashed = hash_password(raw_password)

        owner_user = User(
            email=owner_email,
            phone=owner.get("phone"),
            full_name=owner["name"].strip(),
            role="tenant_owner",
            tenant_id=tenant.id,
            hashed_password=hashed,
            is_active=True,
            is_verified=False,
            force_password_change=not bool(owner.get("password")),
        )
        self.db.add(owner_user)
        await self.db.flush()

        # link owner back to tenant
        tenant.owner_user_id = owner_user.id

        # ── 3. Tenant settings ────────────────────────────────────────────────
        commission_rate = float(commercial.get("commission_rate", 10)) / 100
        ts = TenantSettings(
            tenant_id=tenant.id,
            timezone=settings.get("timezone", "Asia/Kolkata"),
            currency=settings.get("currency", "INR"),
            language=settings.get("language", "en"),
            commission_rate=commission_rate,
        )
        self.db.add(ts)

        # ── 4. Tenant billing record ───────────────────────────────────────────
        security_deposit_required = commercial.get("security_deposit_required", True)
        billing = TenantBilling(
            tenant_id=tenant.id,
            billing_email=owner_email,
            security_deposit_paid=False,
            security_deposit_amount=5000.0,  # default; updated by package
        )
        self.db.add(billing)

        # ── 5. Tenant wallet ──────────────────────────────────────────────────
        wallet = TenantWallet(
            tenant_id=tenant.id,
            credit_balance=Decimal("0.00"),
        )
        self.db.add(wallet)
        await self.db.flush()

        # ── 6. Security deposit record ────────────────────────────────────────
        if security_deposit_required:
            deposit = SecurityDeposit(
                tenant_id=tenant.id,
                required_amount=Decimal("5000.00"),
                total_paid=Decimal("0.00"),
                status="unpaid",
            )
            self.db.add(deposit)

        # ── 7. Branding stub ──────────────────────────────────────────────────
        self.db.add(TenantBranding(tenant_id=tenant.id))

        # ── 8. Limits ─────────────────────────────────────────────────────────
        self.db.add(TenantLimits(tenant_id=tenant.id))

        # ── 9. Audit log ──────────────────────────────────────────────────────
        await self._audit(
            tenant.id, "admin_onboard_tenant",
            entity_type="tenant", entity_id=str(tenant.id),
            after={"business_name": business_name, "owner_email": owner_email},
            notes=f"Onboarded by admin {self.actor_id}",
        )

        await self.db.flush()
        logger.info("admin.onboard_tenant.success", tenant_id=str(tenant.id))

        return {
            "tenant_id": str(tenant.id),
            "tenant_name": business_name,
            "owner_user_id": str(owner_user.id),
            "slug": slug,
            "tenant_code": tenant.tenant_code,
            "category_id": str(tenant.category_id) if tenant.category_id else None,
            "security_deposit_status": "unpaid" if security_deposit_required else "not_required",
            "credit_wallet_balance": 0,
            "status": "pending_verification",
            "verification_status": "not_started",
            "owner_temp_password": raw_password if not owner.get("password") else None,
            "message": "Tenant onboarded successfully",
        }

    # ═══════════════════════════════════════════════════════════════
    # PHASE 3 — ADMIN TENANT CRUD
    # ═══════════════════════════════════════════════════════════════

    async def list_tenants(self, filters: dict) -> dict:
        """Server-side paginated tenant list with full filter + sort support."""
        from sqlalchemy import or_, func, asc, desc as sa_desc, case, text
        from app.exceptions import ServiceOSException

        # ── Pagination ───────────────────────────────────────────────────────
        MAX_PAGE_SIZE = 100
        page = max(1, int(filters.get("page", 1)))
        page_size = int(filters.get("page_size", 25))
        if page_size > MAX_PAGE_SIZE:
            raise ServiceOSException("PAGE_SIZE_TOO_LARGE",
                                     f"page_size cannot exceed {MAX_PAGE_SIZE}.")
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))

        # ── Build base WHERE ─────────────────────────────────────────────────
        conditions = []
        if filters.get("status"):
            conditions.append(Tenant.status == filters["status"])
        if filters.get("verification_status"):
            conditions.append(Tenant.verification_status == filters["verification_status"])
        if filters.get("category_id"):
            conditions.append(Tenant.category_id == uuid.UUID(str(filters["category_id"])))
        if filters.get("state"):
            conditions.append(Tenant.state.ilike(f"%{filters['state']}%"))
        if filters.get("district"):
            conditions.append(Tenant.district.ilike(f"%{filters['district']}%"))
        if filters.get("city"):
            conditions.append(Tenant.city.ilike(f"%{filters['city']}%"))
        if filters.get("city_tier"):
            conditions.append(Tenant.city_tier == filters["city_tier"])
        if filters.get("zipcode"):
            conditions.append(Tenant.zipcode == filters["zipcode"])
        if filters.get("plan_type"):
            conditions.append(Tenant.plan_type == filters["plan_type"])
        if filters.get("is_discoverable") is not None:
            conditions.append(Tenant.is_discoverable == bool(filters["is_discoverable"]))
        if filters.get("search"):
            s = f"%{filters['search']}%"
            conditions.append(or_(
                Tenant.tenant_name.ilike(s),
                Tenant.business_name.ilike(s),
                Tenant.email.ilike(s),
                Tenant.phone.ilike(s),
                Tenant.tenant_code.ilike(s),
                Tenant.slug.ilike(s),
            ))
        if filters.get("created_from"):
            conditions.append(Tenant.created_at >= filters["created_from"])
        if filters.get("created_to"):
            conditions.append(Tenant.created_at <= filters["created_to"])

        # ── Sorting ──────────────────────────────────────────────────────────
        ALLOWED_SORT_FIELDS = {
            "created_at", "updated_at", "tenant_name", "business_name",
            "status", "verification_status", "city", "state", "district",
            "city_tier", "plan_type", "health_score", "rating_average",
        }
        sort_by = filters.get("sort_by", "created_at")
        sort_dir = filters.get("sort_direction", "desc")
        if sort_by not in ALLOWED_SORT_FIELDS:
            raise ServiceOSException("SORT_FIELD_NOT_ALLOWED",
                                     f"Sort field '{sort_by}' is not allowed.")

        sort_col = getattr(Tenant, sort_by, Tenant.created_at)
        order_expr = asc(sort_col) if sort_dir == "asc" else sa_desc(sort_col)

        # ── COUNT query (uses same WHERE, no ORDER BY / LIMIT) ───────────────
        count_q = select(func.count(Tenant.id))
        if conditions:
            count_q = count_q.where(*conditions)
        count_r = await self.db.execute(count_q)
        total_items = count_r.scalar_one() or 0

        # ── Data query ───────────────────────────────────────────────────────
        data_q = select(Tenant)
        if conditions:
            data_q = data_q.where(*conditions)
        data_q = data_q.order_by(order_expr).offset((page - 1) * page_size).limit(page_size)
        r = await self.db.execute(data_q)
        tenants = r.scalars().all()

        total_pages = max(1, (total_items + page_size - 1) // page_size)

        # ── Enrich with wallet + jobs + complaints ───────────────────────────
        enrichment: dict[str, dict] = {}
        if tenants:
            tid_list = [str(t.id) for t in tenants]
            placeholders = ", ".join(f"'{x}'" for x in tid_list)
            enrich_sql = text(f"""
                SELECT
                    t.id::text                                                          AS tenant_id,
                    COALESCE(tb.credit_balance, 0)                                     AS usage_credit_balance,
                    COALESCE(tb.security_deposit_paid, FALSE)                          AS security_deposit_paid,
                    COALESCE(tb.security_deposit_amount, 0)                            AS security_deposit_amount,
                    COALESCE(tb.billing_cycle, 'monthly')                              AS billing_cycle,
                    COALESCE((SELECT COUNT(*) FROM jobs j
                               WHERE j.tenant_id = t.id
                                 AND j.status NOT IN ('completed','cancelled','rejected')), 0) AS active_jobs,
                    COALESCE((SELECT COUNT(*) FROM jobs j
                               WHERE j.tenant_id = t.id
                                 AND j.status = 'completed'), 0)                        AS completed_jobs,
                    COALESCE((SELECT COUNT(*) FROM customer_complaints cc
                               WHERE cc.tenant_id = t.id
                                 AND cc.status NOT IN ('resolved','closed','rejected')), 0) AS open_complaints,
                    COALESCE(tl.current_staff_count, 0)                                AS staff_count,
                    (SELECT u.full_name FROM users u WHERE u.id = t.owner_user_id)     AS owner_name
                FROM tenants t
                LEFT JOIN tenant_billing tb ON tb.tenant_id = t.id
                LEFT JOIN tenant_limits   tl ON tl.tenant_id = t.id
                WHERE t.id::text IN ({placeholders})
            """)
            enrich_r = await self.db.execute(enrich_sql)
            for row in enrich_r.fetchall():
                enrichment[row.tenant_id] = {
                    "usage_credit_balance":    float(row.usage_credit_balance or 0),
                    "security_deposit_paid":   bool(row.security_deposit_paid),
                    "security_deposit_amount": float(row.security_deposit_amount or 0),
                    "billing_cycle":           row.billing_cycle or "monthly",
                    "active_jobs":             int(row.active_jobs or 0),
                    "completed_jobs":          int(row.completed_jobs or 0),
                    "open_complaints":         int(row.open_complaints or 0),
                    "staff_count":             int(row.staff_count or 0),
                    "owner_name":              row.owner_name,
                }

        def _enrich(t: Tenant) -> dict:
            d = self._tenant_dict(t)
            ex = enrichment.get(str(t.id), {})
            d.update({
                "owner_name":              ex.get("owner_name"),
                "usage_credit_balance":    ex.get("usage_credit_balance", 0.0),
                "security_deposit_paid":   ex.get("security_deposit_paid", False),
                "security_deposit_amount": ex.get("security_deposit_amount", 0.0),
                "billing_cycle":           ex.get("billing_cycle", "monthly"),
                "active_jobs":             ex.get("active_jobs", 0),
                "completed_jobs":          ex.get("completed_jobs", 0),
                "open_complaints":         ex.get("open_complaints", 0),
                "staff_count":             ex.get("staff_count", 0),
            })
            return d

        return {
            "items": [_enrich(t) for t in tenants],
            "pagination": {
                "page": page, "page_size": page_size,
                "total_items": total_items, "total_pages": total_pages,
                "has_next": page < total_pages, "has_previous": page > 1,
            },
            "sort": {"sort_by": sort_by, "sort_direction": sort_dir},
            "filters_applied": {
                k: v for k, v in filters.items()
                if k not in {"page", "page_size", "sort_by", "sort_direction"} and v
            },
        }

    async def get_tenant(self, tenant_id: uuid.UUID) -> dict:
        t = await self._get_tenant(tenant_id)
        result = self._tenant_dict(t)
        # include settings
        r = await self.db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
        ts = r.scalar_one_or_none()
        if ts:
            result["settings"] = {
                "timezone": ts.timezone, "currency": ts.currency, "language": ts.language,
                "commission_rate": float(ts.commission_rate),
                "auto_accept_bookings": ts.auto_accept_bookings,
            }
        # include billing
        rb = await self.db.execute(select(TenantBilling).where(TenantBilling.tenant_id == tenant_id))
        billing = rb.scalar_one_or_none()
        if billing:
            result["billing"] = {
                "credit_balance": float(billing.credit_balance),
                "security_deposit_paid": billing.security_deposit_paid,
                "security_deposit_amount": float(billing.security_deposit_amount),
            }
        return result

    async def update_tenant(self, tenant_id: uuid.UUID, data: dict) -> dict:
        t = await self._get_tenant(tenant_id)
        before = self._tenant_dict(t)
        updatable = [
            "business_name", "legal_name", "email", "phone", "gst_number", "business_type",
            "address_line1", "address_line2", "district", "city", "state", "zipcode", "country",
            "logo_url", "is_discoverable",
        ]
        for field in updatable:
            if field in data:
                if field == "business_name":
                    t.tenant_name = data[field]
                    t.business_name = data[field]
                else:
                    setattr(t, field, data[field])
        await self._audit(tenant_id, "admin_update_tenant", before=before, after=self._tenant_dict(t))
        return self._tenant_dict(t)

    async def activate_tenant(self, tenant_id: uuid.UUID) -> dict:
        t = await self._get_tenant(tenant_id)
        if t.status == "active":
            return self._tenant_dict(t)
        t.status = "active"
        t.activated_at = utcnow()
        await self._audit(tenant_id, "admin_activate_tenant")
        return self._tenant_dict(t)

    async def suspend_tenant(self, tenant_id: uuid.UUID, reason: str) -> dict:
        t = await self._get_tenant(tenant_id)
        t.status = "suspended"
        t.suspended_at = utcnow()
        t.suspension_reason = reason
        await self._audit(tenant_id, "admin_suspend_tenant", notes=reason)
        return self._tenant_dict(t)

    async def add_admin_note(self, tenant_id: uuid.UUID, note: str) -> dict:
        """Internal admin note on a tenant — stored as an audit entry (no
        separate notes table exists; reuses the same append-only trail
        surfaced in the Audit tab and the Platform Command Center feed)."""
        if not note or not note.strip():
            raise ServiceOSException("NOTE_REQUIRED", "Note text is required.", status_code=422)
        await self._get_tenant(tenant_id)  # 404s if not found
        await self._audit(tenant_id, "admin_note_added", notes=note.strip())
        return {"tenant_id": str(tenant_id), "note_added": True}

    # ── Pending profile change requests ──────────────────────────────────────
    #
    # A verified tenant can no longer edit its identity fields live: ProfileService stages
    # the proposed values in meta['pending_changes'] and moves the tenant to
    # 'changes_pending_review'. These three methods are what resolves that -- the live
    # profile keeps the details ServiceOS actually verified until one of them runs.
    #
    # The staged values are held on the tenant rather than in a change_requests table
    # because there is exactly one open request per tenant at a time (a second edit
    # replaces the first), and a table would have to enforce that anyway.

    async def list_pending_change_requests(self) -> dict:
        rows = (await self.db.execute(text("""
            SELECT id, business_name, verification_status,
                   meta -> 'pending_changes' AS pending
            FROM tenants
            WHERE verification_status = 'changes_pending_review'
              AND meta ? 'pending_changes'
              AND terminated_at IS NULL AND archived_at IS NULL
            ORDER BY (meta -> 'pending_changes' ->> 'submitted_at')
        """))).fetchall()
        items = []
        for r in rows:
            pending = r.pending if isinstance(r.pending, dict) else json.loads(r.pending or "{}")
            items.append({
                "tenant_id": str(r.id),
                # The name still in force, so an admin comparing old against new is not
                # shown the requested name in both columns.
                "current_business_name": r.business_name,
                "requested_fields": pending.get("fields") or {},
                "submitted_at": pending.get("submitted_at"),
                "submitted_by_user_id": pending.get("submitted_by_user_id"),
                "documents_to_revalidate": pending.get("documents_to_revalidate") or [],
            })
        return {"change_requests": items, "count": len(items)}

    async def approve_change_request(self, tenant_id: uuid.UUID) -> dict:
        t = await self._get_tenant(tenant_id)
        pending = (t.meta or {}).get("pending_changes")
        if not pending or t.verification_status != "changes_pending_review":
            raise ServiceOSException(
                "NO_PENDING_CHANGE_REQUEST",
                "This tenant has no change request awaiting review.", status_code=409)

        fields = pending.get("fields") or {}
        # The staged keys are the request schema's names; these are the columns they map
        # to. Anything unmapped is ignored rather than set blindly -- a staged key that no
        # longer corresponds to a column must not silently vanish into an attribute.
        COLUMN = {
            "business_name": "business_name", "owner_name": "owner_name",
            "business_phone": "phone", "business_email": "email",
            "address_line1": "address_line1", "city": "city", "district": "district",
            "state": "state", "pincode": "zipcode", "gst_number": "gst_number",
        }
        applied: dict[str, object] = {}
        for key, value in fields.items():
            col = COLUMN.get(key)
            if col and hasattr(t, col):
                setattr(t, col, value)
                applied[key] = value

        # Identity moved, so the paperwork proving it no longer matches. Marked for
        # re-upload rather than deleted: the old document stays as the record of what was
        # verified at the time, which is what an audit of this approval would need.
        doc_types = pending.get("documents_to_revalidate") or []
        revalidated = 0
        if doc_types:
            res = await self.db.execute(text("""
                UPDATE tenant_documents
                SET status = 'needs_reupload', updated_at = now()
                WHERE tenant_id = :tid AND is_current = true
                  AND doc_type = ANY(:types) AND status <> 'needs_reupload'
            """), {"tid": str(tenant_id), "types": list(doc_types)})
            revalidated = res.rowcount or 0

        # Back to approved only when nothing is left to re-verify; otherwise the tenant is
        # trading on details whose proof is outstanding, and saying "approved" would hide
        # that.
        t.verification_status = "approved" if revalidated == 0 else "changes_requested"
        t.meta = {k: v for k, v in (t.meta or {}).items() if k != "pending_changes"}
        await self._audit(tenant_id, "admin_change_request_approved",
                          notes=json.dumps({"applied": applied,
                                            "documents_marked_for_reupload": revalidated}))
        await self.db.commit()
        return {
            "tenant_id": str(tenant_id), "approved": True, "applied_fields": applied,
            "documents_marked_for_reupload": revalidated,
            "verification_status": t.verification_status,
        }

    async def reject_change_request(self, tenant_id: uuid.UUID, reason: str) -> dict:
        t = await self._get_tenant(tenant_id)
        pending = (t.meta or {}).get("pending_changes")
        if not pending or t.verification_status != "changes_pending_review":
            raise ServiceOSException(
                "NO_PENDING_CHANGE_REQUEST",
                "This tenant has no change request awaiting review.", status_code=409)
        if not reason.strip():
            raise ServiceOSException(
                "REJECTION_REASON_REQUIRED",
                "A reason is required so the provider knows what to correct.", status_code=422)

        # Nothing to roll back: the live profile was never changed. Only the request and
        # the review state are cleared, and the tenant returns to approved because its
        # verified details are exactly as they were.
        rejected = {k: v for k, v in (t.meta or {}).items() if k != "pending_changes"}
        rejected["last_rejected_change"] = {
            "fields": pending.get("fields") or {},
            "reason": reason.strip(),
            "rejected_at": utcnow().isoformat(),
        }
        t.meta = rejected
        t.verification_status = "approved"
        await self._audit(tenant_id, "admin_change_request_rejected", notes=reason.strip())
        await self.db.commit()
        return {"tenant_id": str(tenant_id), "approved": False, "reason": reason.strip()}

    async def verify_tenant(self, tenant_id: uuid.UUID) -> dict:
        t = await self._get_tenant(tenant_id)
        if t.verification_status not in ("not_started", "pending", "changes_requested"):
            raise ServiceOSException("TENANT_VERIFICATION_INVALID_STATUS",
                                     f"Cannot verify tenant in '{t.verification_status}' status.")
        now = utcnow()
        t.verification_status = "approved"
        t.status = "active"
        t.activated_at = t.activated_at or now
        await self._audit(tenant_id, "admin_verify_tenant")

        # P1 — Activate tenant's package assignment after approval
        # Package starts only after admin approval; credits added here.
        try:
            from app.engines.package_commerce.service import PackageCommerceService
            pkg_svc = PackageCommerceService(
                db=self.db,
                request_id=getattr(self, "request_id", "—"),
                actor_id=self.actor_id,
                actor_role=self.actor_role,
            )
            await pkg_svc.activate_tenant_package_assignment(tenant_id)
        except Exception as exc:
            # Package activation failure must NOT block tenant approval
            logger.warning("verify_tenant.package_activation_failed",
                           tenant_id=str(tenant_id), error=str(exc))

        return self._tenant_dict(t)

    async def reject_verification(self, tenant_id: uuid.UUID, reason: str) -> dict:
        t = await self._get_tenant(tenant_id)
        t.verification_status = "rejected"
        t.status = "rejected"
        t.suspension_reason = reason
        await self._audit(tenant_id, "admin_reject_verification", notes=reason)

        # P1 — Mark package assignment as rejected
        try:
            from app.engines.package_commerce.service import PackageCommerceService
            pkg_svc = PackageCommerceService(
                db=self.db,
                request_id=getattr(self, "request_id", "—"),
                actor_id=self.actor_id,
                actor_role=self.actor_role,
            )
            await pkg_svc.reject_tenant_package_assignment(tenant_id, reason=reason)
        except Exception as exc:
            logger.warning("reject_verification.package_rejection_failed",
                           tenant_id=str(tenant_id), error=str(exc))

        # BUG FIX: rejection reason was saved (suspension_reason/audit) but
        # never told to the provider -- they had no way to know what to fix.
        try:
            from app.engines.tenant_engine.notifications import notify_tenant_verification
            await notify_tenant_verification(
                self.db, tenant_id,
                notification_type="tenant.verification_rejected",
                title="Verification rejected",
                body=f"Your business verification was rejected: {reason}. Please correct this and resubmit.",
                severity="danger",
            )
        except Exception as exc:
            logger.warning("reject_verification.notify_failed", tenant_id=str(tenant_id), error=str(exc))

        return self._tenant_dict(t)

    async def archive_tenant(self, tenant_id: uuid.UUID) -> dict:
        t = await self._get_tenant(tenant_id)
        t.status = "archived"
        t.archived_at = utcnow()
        await self._audit(tenant_id, "admin_archive_tenant")
        return self._tenant_dict(t)

    # ═══════════════════════════════════════════════════════════════
    # PHASE 5 — OVERVIEW
    # ═══════════════════════════════════════════════════════════════

    async def get_overview(self, tenant_id: uuid.UUID) -> dict:
        t = await self._get_tenant(tenant_id)

        # owner info
        owner_info: dict = {}
        if t.owner_user_id:
            ro = await self.db.execute(select(User).where(User.id == t.owner_user_id))
            owner = ro.scalar_one_or_none()
            if owner:
                owner_info = {"name": owner.full_name, "email": owner.email, "phone": owner.phone}

        # settings
        rs = await self.db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
        settings = rs.scalar_one_or_none()

        # billing
        rb = await self.db.execute(select(TenantBilling).where(TenantBilling.tenant_id == tenant_id))
        billing = rb.scalar_one_or_none()

        # wallet
        rw = await self.db.execute(select(TenantWallet).where(TenantWallet.tenant_id == tenant_id))
        wallet = rw.scalar_one_or_none()

        # deposit
        rd = await self.db.execute(select(SecurityDeposit).where(SecurityDeposit.tenant_id == tenant_id))
        deposit = rd.scalar_one_or_none()

        # service areas count
        from sqlalchemy import func
        rsa = await self.db.execute(
            select(func.count()).select_from(TenantServiceArea)
            .where(TenantServiceArea.tenant_id == tenant_id, TenantServiceArea.is_active == True)
        )
        service_areas_count = rsa.scalar() or 0

        # staff count
        rstaff = await self.db.execute(
            select(func.count()).select_from(User)
            .where(User.tenant_id == tenant_id, User.role.in_(("staff", "technician")), User.is_active == True)
        )
        staff_count = rstaff.scalar() or 0

        # users count
        rusers = await self.db.execute(
            select(func.count()).select_from(User)
            .where(User.tenant_id == tenant_id, User.is_active == True)
        )
        users_count = rusers.scalar() or 0

        return {
            "tenant": self._tenant_dict(t),
            "owner": owner_info,
            "commercial": {
                "commission_rate": float(settings.commission_rate) if settings else 0.10,
                "credit_wallet_balance": float(wallet.credit_balance) if wallet else 0,
                "security_deposit_status": deposit.status if deposit else "not_required",
                "security_deposit_required": float(deposit.required_amount) if deposit else 0,
                "security_deposit_paid": float(deposit.total_paid) if deposit else 0,
                "plan_type": t.plan_type,
            },
            "operational": {
                "staff_count": staff_count,
                "users_count": users_count,
                "service_areas_count": service_areas_count,
            },
            "settings": {
                "timezone": settings.timezone if settings else "Asia/Kolkata",
                "currency": settings.currency if settings else "INR",
                "language": settings.language if settings else "en",
            },
        }

    # ═══════════════════════════════════════════════════════════════
    # PHASE 6 — USERS
    # ═══════════════════════════════════════════════════════════════

    async def list_users(self, tenant_id: uuid.UUID, search: str | None = None) -> dict:
        await self._get_tenant(tenant_id)
        q = select(User).where(User.tenant_id == tenant_id)
        if search:
            from sqlalchemy import or_
            s = f"%{search}%"
            q = q.where(or_(User.full_name.ilike(s), User.email.ilike(s)))
        q = q.order_by(User.created_at.desc())
        r = await self.db.execute(q)
        users = r.scalars().all()
        return {"users": [self._user_dict(u) for u in users], "total": len(users)}

    async def create_user(self, tenant_id: uuid.UUID, data: dict) -> dict:
        await self._get_tenant(tenant_id)
        email = data.get("email", "").lower().strip()
        role = data.get("role", "tenant_manager")
        if role not in VALID_TENANT_ROLES:
            raise ServiceOSException("TENANT_USER_ROLE_INVALID", f"Role '{role}' is not valid.")
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ServiceOSException("TENANT_USER_ALREADY_EXISTS",
                                     f"User with email {email} already exists.")
        from app.engines.auth.utils import hash_password
        raw_password = secrets.token_urlsafe(12)
        user = User(
            email=email, phone=data.get("phone"),
            full_name=data.get("name", "").strip(),
            role=role, tenant_id=tenant_id,
            hashed_password=hash_password(raw_password),
            is_active=True, is_verified=False, force_password_change=True,
        )
        self.db.add(user)
        await self.db.flush()
        await self._audit(tenant_id, "admin_create_user", entity_type="user", entity_id=str(user.id))
        result = self._user_dict(user)
        result["temp_password"] = raw_password
        return result

    async def update_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID, data: dict) -> dict:
        user = await self._load_tenant_user(tenant_id, user_id)
        if "name" in data:
            user.full_name = data["name"]
        if "phone" in data:
            user.phone = data["phone"]
        if "role" in data:
            if data["role"] not in VALID_TENANT_ROLES:
                raise ServiceOSException("TENANT_USER_ROLE_INVALID", f"Role '{data['role']}' is not valid.")
            user.role = data["role"]
        await self._audit(tenant_id, "admin_update_user", entity_type="user", entity_id=str(user_id))
        return self._user_dict(user)

    async def activate_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        user = await self._load_tenant_user(tenant_id, user_id)
        user.is_active = True
        await self._audit(tenant_id, "admin_activate_user", entity_type="user", entity_id=str(user_id))
        return self._user_dict(user)

    async def suspend_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        user = await self._load_tenant_user(tenant_id, user_id)
        user.is_active = False
        await self._audit(tenant_id, "admin_suspend_user", entity_type="user", entity_id=str(user_id))
        return self._user_dict(user)

    async def reset_user_password(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        user = await self._load_tenant_user(tenant_id, user_id)
        from app.engines.auth.utils import hash_password
        raw_password = secrets.token_urlsafe(12)
        user.hashed_password = hash_password(raw_password)
        user.force_password_change = True
        await self._audit(tenant_id, "admin_reset_password", entity_type="user", entity_id=str(user_id))
        return {"user_id": str(user_id), "temp_password": raw_password, "message": "Password reset."}

    async def _load_tenant_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User:
        r = await self.db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        u = r.scalar_one_or_none()
        if not u:
            raise NotFoundException("User", str(user_id))
        return u

    def _user_dict(self, u: User) -> dict:
        return {
            "user_id": str(u.id), "name": u.full_name, "email": u.email, "phone": u.phone,
            "role": u.role, "is_active": u.is_active, "is_verified": u.is_verified,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat(),
        }

    # ═══════════════════════════════════════════════════════════════
    # PHASE 7 — STAFF
    # ═══════════════════════════════════════════════════════════════

    async def list_staff(self, tenant_id: uuid.UUID) -> dict:
        await self._get_tenant(tenant_id)
        r = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id, User.role.in_(("staff", "technician")))
            .order_by(User.created_at.desc())
        )
        staff = r.scalars().all()
        return {"staff": [self._user_dict(u) for u in staff], "total": len(staff)}

    async def create_staff(self, tenant_id: uuid.UUID, data: dict) -> dict:
        await self._get_tenant(tenant_id)
        email = data.get("email", "").lower().strip()
        if email:
            existing = await self.db.execute(select(User).where(User.email == email))
            if existing.scalar_one_or_none():
                raise ServiceOSException("TENANT_STAFF_ALREADY_EXISTS",
                                         f"Staff with email {email} already exists.")
        from app.engines.auth.utils import hash_password
        raw_password = secrets.token_urlsafe(12)
        user = User(
            email=email or f"staff.{uuid.uuid4().hex[:6]}@tenant.local",
            phone=data.get("phone"),
            full_name=data.get("name", "").strip(),
            role="staff", tenant_id=tenant_id,
            hashed_password=hash_password(raw_password),
            is_active=True, is_verified=False, force_password_change=True,
        )
        self.db.add(user)
        await self.db.flush()
        await self._audit(tenant_id, "admin_create_staff", entity_type="staff", entity_id=str(user.id))
        result = self._user_dict(user)
        result["temp_password"] = raw_password
        return result

    async def update_staff(self, tenant_id: uuid.UUID, staff_id: uuid.UUID, data: dict) -> dict:
        staff = await self._load_tenant_staff(tenant_id, staff_id)
        if "name" in data:
            staff.full_name = data["name"]
        if "phone" in data:
            staff.phone = data["phone"]
        if "avatar_url" in data:
            staff.avatar_url = data["avatar_url"]
        await self._audit(tenant_id, "admin_update_staff", entity_type="staff", entity_id=str(staff_id))
        return self._user_dict(staff)

    async def activate_staff(self, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> dict:
        staff = await self._load_tenant_staff(tenant_id, staff_id)
        staff.is_active = True
        await self._audit(tenant_id, "admin_activate_staff", entity_type="staff", entity_id=str(staff_id))
        return self._user_dict(staff)

    async def deactivate_staff(self, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> dict:
        staff = await self._load_tenant_staff(tenant_id, staff_id)
        staff.is_active = False
        # Phase 2A Slice 2F-4, Workstream 8/9: this method previously only
        # flipped is_active, unlike the frontend-canonical
        # AuthService.deactivate_staff (app/engines/auth/service.py, fixed
        # in Slice 2F-1) which also revokes DB + Redis sessions -- a
        # directly-connected weaker alternate route for the same
        # capability on the same User table (this router's path is
        # /v1/tenant/staff/{id}/deactivate, the auth router's is
        # /v1/auth/staff/{id}/deactivate; both are live and reachable).
        # Closing it here with the identical proven pattern.
        from app.engines.auth.models import UserSession
        from app.engines.auth.constants import ACCESS_TOKEN_EXPIRE_MINUTES
        from app.redis_client import get_redis
        active_sessions = await self.db.execute(
            select(UserSession.id).where(UserSession.user_id == staff_id, UserSession.revoked_at.is_(None))
        )
        session_ids = [row[0] for row in active_sessions]
        sessions_revoked = 0
        if session_ids:
            await self.db.execute(
                update(UserSession).where(
                    UserSession.user_id == staff_id, UserSession.revoked_at.is_(None)
                ).values(revoked_at=utcnow(), revocation_reason="staff_deactivated")
            )
            sessions_revoked = len(session_ids)
            redis = get_redis()
            for sid in session_ids:
                try:
                    await redis.setex(f"serviceos:session:revoked:{sid}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
                except Exception:
                    pass
        await self._audit(tenant_id, "admin_deactivate_staff", entity_type="staff", entity_id=str(staff_id),
                          after={"is_active": False, "sessions_revoked": sessions_revoked})
        result = self._user_dict(staff)
        result["sessions_revoked"] = sessions_revoked
        return result

    async def reset_staff_password(self, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> dict:
        staff = await self._load_tenant_staff(tenant_id, staff_id)
        from app.engines.auth.utils import hash_password
        raw_password = secrets.token_urlsafe(12)
        staff.hashed_password = hash_password(raw_password)
        staff.force_password_change = True
        await self._audit(tenant_id, "admin_reset_staff_password",
                          entity_type="staff", entity_id=str(staff_id))
        return {"staff_id": str(staff_id), "temp_password": raw_password, "message": "Password reset."}

    async def update_staff_photo(self, tenant_id: uuid.UUID, staff_id: uuid.UUID, photo_url: str) -> dict:
        staff = await self._load_tenant_staff(tenant_id, staff_id)
        staff.avatar_url = photo_url
        await self._audit(tenant_id, "admin_update_staff_photo",
                          entity_type="staff", entity_id=str(staff_id))
        return self._user_dict(staff)

    async def _load_tenant_staff(self, tenant_id: uuid.UUID, staff_id: uuid.UUID) -> User:
        r = await self.db.execute(
            select(User).where(User.id == staff_id, User.tenant_id == tenant_id, User.role.in_(("staff", "technician")))
        )
        s = r.scalar_one_or_none()
        if not s:
            raise NotFoundException("Staff", str(staff_id))
        return s

    # FINAL-L5-05T: Service Areas were removed from this service entirely.
    # `app.engines.serviceability.service.ServiceabilityService` is the
    # certified canonical owner (see
    # docs/final-l5-05/FINAL_L5_05T_ADR_SERVICE_AREA_CANONICAL_OWNER.md).
    # This class previously duplicated list/create/update/delete
    # service-area methods behind routes that were either fully shadowed
    # (identical method+path, unreachable because serviceability.router is
    # registered first in app/main.py) or a second, undiscovered live
    # mutation path on a different HTTP verb (PATCH vs. the canonical PUT).
    # Removed rather than retained as dead code (mission rule: "do not
    # leave unreachable mutation code presented as active").

    # FINAL-L5-05U: get_security_deposit/mark_deposit_paid removed from this
    # service entirely -- confirmed orphaned (their routes were already
    # removed in an earlier "Phase 4 finance certification" sprint per the
    # comment above the wallet routes in this file's admin_router.py sibling;
    # these two methods had zero remaining callers anywhere). The canonical
    # Security Deposit admin console is app.engines.finance_hub (see
    # docs/final-l5-05/FINAL_L5_05U_ADR_SECURITY_DEPOSIT_CANONICAL_PERMISSION.md).

    async def get_credit_wallet(self, tenant_id: uuid.UUID) -> dict:
        await self._get_tenant(tenant_id)
        r = await self.db.execute(
            select(TenantWallet).where(TenantWallet.tenant_id == tenant_id)
        )
        wallet = r.scalar_one_or_none()
        if not wallet:
            raise ServiceOSException("CREDIT_WALLET_NOT_FOUND", "No wallet found.")
        return {
            "wallet_id": str(wallet.id), "tenant_id": str(tenant_id),
            "credit_balance": float(wallet.credit_balance),
            "lifetime_purchased": float(wallet.lifetime_purchased),
            "lifetime_consumed": float(wallet.lifetime_consumed),
        }

    async def get_credit_ledger(self, tenant_id: uuid.UUID, limit: int = 50) -> dict:
        await self._get_tenant(tenant_id)
        r = await self.db.execute(
            select(WalletTransaction).where(WalletTransaction.tenant_id == tenant_id)
            .order_by(WalletTransaction.created_at.desc())
            .limit(limit)
        )
        txns = r.scalars().all()
        return {
            "transactions": [{
                "txn_id": str(t.id),
                "txn_type": t.txn_type,
                "amount": float(t.amount),
                "balance_before": float(t.balance_before),
                "balance_after": float(t.balance_after),
                "description": t.description,
                "created_at": t.created_at.isoformat(),
            } for t in txns]
        }

    async def credit_topup(self, tenant_id: uuid.UUID, amount: float, notes: str) -> dict:
        await self._get_tenant(tenant_id)
        r = await self.db.execute(
            select(TenantWallet).where(TenantWallet.tenant_id == tenant_id)
        )
        wallet = r.scalar_one_or_none()
        if not wallet:
            raise ServiceOSException("CREDIT_WALLET_NOT_FOUND", "No wallet found.")
        bal_before = wallet.credit_balance
        wallet.credit_balance += Decimal(str(amount))
        wallet.lifetime_purchased += Decimal(str(amount))
        wallet.last_transaction_at = utcnow()
        txn = WalletTransaction(
            tenant_id=tenant_id, txn_type="admin_topup",
            amount=Decimal(str(amount)),
            balance_before=bal_before, balance_after=wallet.credit_balance,
            description=notes or "Admin top-up", actor_id=self.actor_id,
        )
        self.db.add(txn)
        await self._audit(tenant_id, "admin_credit_topup", after={"amount": amount, "notes": notes})
        return {"new_balance": float(wallet.credit_balance), "amount_added": amount}

    async def credit_adjust(self, tenant_id: uuid.UUID, amount: float, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("CREDIT_ADJUSTMENT_REASON_REQUIRED", "Reason is required.")
        r = await self.db.execute(
            select(TenantWallet).where(TenantWallet.tenant_id == tenant_id)
        )
        wallet = r.scalar_one_or_none()
        if not wallet:
            raise ServiceOSException("CREDIT_WALLET_NOT_FOUND", "No wallet found.")
        bal_before = wallet.credit_balance
        wallet.credit_balance += Decimal(str(amount))
        txn = WalletTransaction(
            tenant_id=tenant_id, txn_type="admin_adjustment",
            amount=Decimal(str(amount)),
            balance_before=bal_before, balance_after=wallet.credit_balance,
            description=reason, actor_id=self.actor_id,
        )
        self.db.add(txn)
        await self._audit(tenant_id, "admin_credit_adjustment",
                          after={"amount": amount, "reason": reason})
        return {"new_balance": float(wallet.credit_balance), "adjustment": amount}

    # ═══════════════════════════════════════════════════════════════
    # PHASE 13 — READ-ONLY DATA TABS (bookings, jobs, reviews, audit)
    # ═══════════════════════════════════════════════════════════════

    async def get_audit_logs(self, tenant_id: uuid.UUID, limit: int = 50) -> dict:
        await self._get_tenant(tenant_id)
        r = await self.db.execute(
            select(TenantAuditLog).where(TenantAuditLog.tenant_id == tenant_id)
            .order_by(TenantAuditLog.created_at.desc())
            .limit(limit)
        )
        logs = r.scalars().all()
        return {
            "logs": [{
                "log_id": str(lg.id),
                "actor_id": str(lg.actor_id) if lg.actor_id else None,
                "actor_role": lg.actor_role,
                "action_type": lg.action_type,
                "entity_type": lg.entity_type,
                "entity_id": lg.entity_id,
                "notes": lg.notes,
                "created_at": lg.created_at.isoformat(),
            } for lg in logs]
        }

    # ═══════════════════════════════════════════════════════════════
    # SETTINGS PATCH
    # ═══════════════════════════════════════════════════════════════

    async def get_settings(self, tenant_id: uuid.UUID) -> dict:
        await self._get_tenant(tenant_id)
        r = await self.db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
        ts = r.scalar_one_or_none()
        if not ts:
            return {"timezone": "Asia/Kolkata", "currency": "INR", "language": "en"}
        return {
            "timezone": ts.timezone, "currency": ts.currency, "language": ts.language,
            "commission_rate": float(ts.commission_rate),
            "auto_accept_bookings": ts.auto_accept_bookings,
            "notify_new_booking": ts.notify_new_booking,
            "notify_low_credit": ts.notify_low_credit,
            "low_credit_threshold": float(ts.low_credit_threshold),
        }

    async def update_settings(self, tenant_id: uuid.UUID, data: dict) -> dict:
        await self._get_tenant(tenant_id)
        r = await self.db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant_id))
        ts = r.scalar_one_or_none()
        if not ts:
            ts = TenantSettings(tenant_id=tenant_id)
            self.db.add(ts)
        for field in ("timezone", "currency", "language", "auto_accept_bookings",
                      "notify_new_booking", "notify_low_credit", "low_credit_threshold"):
            if field in data:
                setattr(ts, field, data[field])
        if "commission_rate" in data:
            ts.commission_rate = float(data["commission_rate"]) / 100
        await self._audit(tenant_id, "admin_update_settings", after=data)
        return await self.get_settings(tenant_id)

    # ═══════════════════════════════════════════════════════════════
    # ENTERPRISE — INSIGHTS + ACTIONS
    # ═══════════════════════════════════════════════════════════════

    async def get_insights(self) -> dict:
        """Aggregated insight data for the right sidebar panels and bottom cards."""
        from sqlalchemy import text as sqlt
        base_where = "WHERE t.terminated_at IS NULL AND t.archived_at IS NULL"

        v_sql = sqlt(f"""
            SELECT
                SUM(CASE WHEN t.verification_status = 'not_started' THEN 1 ELSE 0 END)         AS not_started,
                SUM(CASE WHEN t.verification_status IN ('pending','under_review','in_progress') THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN t.verification_status IN ('approved','verified','completed')      THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN t.verification_status = 'changes_requested'                      THEN 1 ELSE 0 END) AS changes_requested,
                SUM(CASE WHEN t.verification_status IN ('rejected','expired')                  THEN 1 ELSE 0 END) AS rejected,
                COUNT(*) AS total
            FROM tenants t {base_where}
        """)
        p_sql = sqlt(f"""
            SELECT t.plan_type, COUNT(*) AS cnt
            FROM tenants t {base_where}
            GROUP BY t.plan_type ORDER BY cnt DESC
        """)
        loc_sql = sqlt(f"""
            SELECT t.city, t.state, COUNT(*) AS cnt
            FROM tenants t {base_where} AND t.city IS NOT NULL
            GROUP BY t.city, t.state ORDER BY cnt DESC LIMIT 8
        """)
        fin_sql = sqlt(f"""
            SELECT
                COALESCE(SUM(tb.credit_balance), 0)          AS total_credits,
                COALESCE(SUM(tb.security_deposit_amount), 0) AS total_deposits,
                COUNT(CASE WHEN tb.credit_balance < 500 AND tb.credit_balance IS NOT NULL THEN 1 END) AS low_credit_tenants
            FROM tenants t
            LEFT JOIN tenant_billing tb ON tb.tenant_id = t.id
            {base_where}
        """)
        health_sql = sqlt(f"""
            SELECT
                AVG(t.health_score)                                      AS avg_score,
                SUM(CASE WHEN t.health_score < 50 THEN 1 ELSE 0 END)    AS high_risk,
                SUM(CASE WHEN t.health_score BETWEEN 50 AND 75 THEN 1 ELSE 0 END) AS medium_risk,
                SUM(CASE WHEN t.health_score > 75 THEN 1 ELSE 0 END)    AS low_risk
            FROM tenants t {base_where}
        """)
        activity_sql = sqlt("""
            SELECT tal.action_type, tal.notes, tal.created_at,
                   t.tenant_name, t.business_name
            FROM tenant_audit_logs tal
            JOIN tenants t ON t.id = tal.tenant_id
            ORDER BY tal.created_at DESC LIMIT 10
        """)

        vr, pr, lr, fr, hr, ar = await self.db.execute(v_sql), None, None, None, None, None
        vrow = vr.fetchone()
        pr = (await self.db.execute(p_sql)).fetchall()
        lr = (await self.db.execute(loc_sql)).fetchall()
        fr_row = (await self.db.execute(fin_sql)).fetchone()
        hr_row = (await self.db.execute(health_sql)).fetchone()
        ar = (await self.db.execute(activity_sql)).fetchall()

        total_v = int(vrow.total or 1)
        return {
            "verification_overview": {
                "not_started":       int(vrow.not_started or 0),
                "in_progress":       int(vrow.in_progress or 0),
                "completed":         int(vrow.completed or 0),
                "changes_requested": int(vrow.changes_requested or 0),
                "rejected":          int(vrow.rejected or 0),
                "total":             total_v,
            },
            "plan_distribution": [
                {"plan": r.plan_type or "unknown", "count": int(r.cnt)} for r in pr
            ],
            "top_locations": [
                {"city": r.city, "state": r.state, "count": int(r.cnt)} for r in lr
            ],
            "financial_summary": {
                "total_usage_credits": float(fr_row.total_credits or 0),
                "total_security_deposits": float(fr_row.total_deposits or 0),
                "low_credit_tenants": int(fr_row.low_credit_tenants or 0),
            },
            "health_summary": {
                "average_health_score": round(float(hr_row.avg_score or 0), 1),
                "high_risk":   int(hr_row.high_risk or 0),
                "medium_risk": int(hr_row.medium_risk or 0),
                "low_risk":    int(hr_row.low_risk or 0),
            },
            "recent_activity": [
                {
                    "action":      r.action_type.replace("_", " ").title(),
                    "tenant_name": r.business_name or r.tenant_name or "Unknown",
                    "notes":       r.notes,
                    "created_at":  r.created_at.isoformat() if r.created_at else None,
                } for r in ar
            ],
        }

    async def add_usage_credits(self, tenant_id: uuid.UUID, amount: float, reason: str) -> dict:
        """Add usage credits to tenant billing. Not real money — usage credit only."""
        if amount <= 0:
            raise ServiceOSException("INVALID_AMOUNT", "Amount must be positive.")
        if not reason or not reason.strip():
            raise ServiceOSException("REASON_REQUIRED", "Reason is required for adding usage credits.")
        t = await self._get_tenant(tenant_id)
        r = await self.db.execute(
            select(TenantBilling).where(TenantBilling.tenant_id == tenant_id)
        )
        billing = r.scalar_one_or_none()
        if not billing:
            billing = TenantBilling(tenant_id=tenant_id, credit_balance=0.0)
            self.db.add(billing)
            await self.db.flush()
        old_balance = float(billing.credit_balance)
        billing.credit_balance = Decimal(str(old_balance + amount))
        await self._audit(
            tenant_id, "admin_add_usage_credits",
            before={"credit_balance": old_balance},
            after={"credit_balance": float(billing.credit_balance)},
            notes=reason,
        )
        return {
            "tenant_id": str(tenant_id),
            "old_balance": old_balance,
            "amount_added": amount,
            "new_balance": float(billing.credit_balance),
            "reason": reason,
        }

    async def change_plan(self, tenant_id: uuid.UUID, new_plan: str, reason: str) -> dict:
        """Change tenant plan. Requires reason and creates audit log."""
        VALID_PLANS = {"free", "starter", "growth", "professional", "enterprise"}
        if new_plan not in VALID_PLANS:
            raise ServiceOSException("INVALID_PLAN", f"Plan '{new_plan}' is not valid.")
        if not reason or not reason.strip():
            raise ServiceOSException("REASON_REQUIRED", "Reason is required for changing plan.")
        t = await self._get_tenant(tenant_id)
        old_plan = t.plan_type
        t.plan_type = new_plan
        await self._audit(
            tenant_id, "admin_change_plan",
            before={"plan_type": old_plan},
            after={"plan_type": new_plan},
            notes=reason,
        )
        return {"tenant_id": str(tenant_id), "old_plan": old_plan, "new_plan": new_plan, "reason": reason}

    async def reactivate_tenant(self, tenant_id: uuid.UUID, reason: str = "") -> dict:
        """Reactivate a suspended or rejected tenant."""
        t = await self._get_tenant(tenant_id)
        old_status = t.status
        t.status = "active"
        t.suspended_at = None
        t.suspension_reason = None
        await self._audit(
            tenant_id, "admin_reactivate_tenant",
            before={"status": old_status},
            after={"status": "active"},
            notes=reason or "Reactivated by admin",
        )
        return self._tenant_dict(t)

    async def request_changes(self, tenant_id: uuid.UUID, reason: str) -> dict:
        """Mark verification as changes_requested with a reason."""
        if not reason or not reason.strip():
            raise ServiceOSException("REASON_REQUIRED", "Reason is required for requesting changes.")
        t = await self._get_tenant(tenant_id)
        old_v = t.verification_status
        t.verification_status = "changes_requested"
        await self._audit(
            tenant_id, "admin_request_changes",
            before={"verification_status": old_v},
            after={"verification_status": "changes_requested"},
            notes=reason,
        )
        # BUG FIX: same as reject_verification -- the reason was recorded
        # but the provider was never told, so "changes_requested" silently
        # stalled with no one aware they needed to act.
        try:
            from app.engines.tenant_engine.notifications import notify_tenant_verification
            await notify_tenant_verification(
                self.db, tenant_id,
                notification_type="tenant.verification_changes_requested",
                title="Changes requested on your verification",
                body=f"Please make the following changes and resubmit: {reason}",
                severity="warning",
            )
        except Exception as exc:
            logger.warning("request_changes.notify_failed", tenant_id=str(tenant_id), error=str(exc))
        return {"tenant_id": str(tenant_id), "verification_status": "changes_requested", "reason": reason}

    async def send_notification(self, tenant_id: uuid.UUID, message: str, subject: str = "") -> dict:
        """Send an in-platform notification to the tenant owner. Audit logged."""
        if not message or not message.strip():
            raise ServiceOSException("MESSAGE_REQUIRED", "Notification message is required.")
        t = await self._get_tenant(tenant_id)
        await self._audit(
            tenant_id, "admin_notification_sent",
            notes=f"Subject: {subject}. Message: {message[:200]}",
        )
        return {"tenant_id": str(tenant_id), "status": "sent", "subject": subject, "message": message}

    async def export_tenants_csv(self, filters: dict) -> str:
        """Export tenants as CSV respecting all active filters."""
        from sqlalchemy import or_
        import csv, io

        conditions = []
        if filters.get("status"):
            conditions.append(Tenant.status == filters["status"])
        if filters.get("verification_status"):
            conditions.append(Tenant.verification_status == filters["verification_status"])
        if filters.get("plan_type"):
            conditions.append(Tenant.plan_type == filters["plan_type"])
        if filters.get("state"):
            conditions.append(Tenant.state.ilike(f"%{filters['state']}%"))
        if filters.get("city"):
            conditions.append(Tenant.city.ilike(f"%{filters['city']}%"))
        if filters.get("search"):
            s = f"%{filters['search']}%"
            conditions.append(or_(
                Tenant.tenant_name.ilike(s), Tenant.email.ilike(s),
                Tenant.phone.ilike(s), Tenant.tenant_code.ilike(s),
            ))

        q = select(Tenant).order_by(Tenant.created_at.desc()).limit(2000)
        if conditions:
            q = q.where(*conditions)
        r = await self.db.execute(q)
        tenants = r.scalars().all()

        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["tenant_id","tenant_name","business_name","email","phone",
                    "status","verification_status","plan_type","vertical",
                    "city","state","health_score","health_band","created_at"])
        for t in tenants:
            w.writerow([
                str(t.id), t.tenant_name, t.business_name or "", t.email or "", t.phone or "",
                t.status, t.verification_status, t.plan_type, t.vertical,
                t.city or "", t.state or "", float(t.health_score), t.health_band,
                t.created_at.isoformat(),
            ])
        return out.getvalue()

    async def export_tenant_report_csv(self, tenant_id: uuid.UUID) -> str:
        """Single-tenant snapshot report for the Tenant 360 'Export Tenant Report' action."""
        import csv, io

        t = await self.db.get(Tenant, tenant_id)
        if not t:
            raise NotFoundException(f"Tenant {tenant_id} not found")

        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["field", "value"])
        rows = [
            ("tenant_id", str(t.id)),
            ("tenant_name", t.tenant_name),
            ("business_name", t.business_name or ""),
            ("email", t.email or ""),
            ("phone", t.phone or ""),
            ("status", t.status),
            ("verification_status", t.verification_status),
            ("plan_type", t.plan_type),
            ("vertical", t.vertical),
            ("city", t.city or ""),
            ("state", t.state or ""),
            ("health_score", float(t.health_score)),
            ("health_band", t.health_band),
            ("is_discoverable", t.is_discoverable),
            ("created_at", t.created_at.isoformat()),
            ("activated_at", t.activated_at.isoformat() if t.activated_at else ""),
        ]
        for field, value in rows:
            w.writerow([field, value])
        return out.getvalue()
