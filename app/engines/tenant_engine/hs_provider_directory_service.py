"""Home Services Provider Directory — /admin/home-services/providers.

Audit finding: no Home Services-scoped provider directory existed before
this file (grep-verified: no router/service/frontend page referenced
"home_services_providers" or similar). The screenshot's "1 provider but
empty table" bug describes a real anti-pattern (summary and table built
from independently-reconstructed filters) that this file is structured to
make structurally impossible, not a defect being reproduced from existing
code: `_base_query()` is the ONE predicate builder; `list_providers()` and
`get_summary()` both apply it before diverging into pagination vs.
aggregation, so they can never disagree about which rows are in scope.

Multi-vertical membership: `Tenant.vertical` is a single string column
today (confirmed via grep across tenant_engine/models.py) -- there is no
`TenantBusinessVertical` join table yet, so a tenant can only ever belong
to exactly one vertical in the current schema. `TenantBilling.vertical_key`
(migration 181) already anticipates a future multi-vertical model ("without
ever letting two verticals silently share one balance row" -- its own
comment) but nothing has built the tenant-membership side of that yet.
This service filters on `Tenant.vertical == "home_services"`, which is
correct for the current schema and forward-compatible: the day a
TenantBusinessVertical table exists, only `_base_query()` needs to change.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.tenant_engine.models import Tenant, TenantBilling
from app.engines.platform_commerce.models import SecurityDeposit
from app.engines.final_records.models import ServiceJob
from app.exceptions import NotFoundException

HOME_SERVICES_VERTICAL = "home_services"
LOW_BALANCE_THRESHOLD = Decimal("500.00")

# Setup-incomplete tenant.status values (registration not yet through
# onboarding) -- from tenant_engine/constants.py::TENANT_STATES.
SETUP_INCOMPLETE_STATUSES = {"onboarding_pending", "under_review", "awaiting_documents", "pending_activation"}


class HomeServicesProviderDirectoryService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role

    # ── The one shared predicate: summary, list and export all start here ──
    def _base_query(self, *, q: str | None = None, status: str | None = None,
                     status_in: list[str] | None = None,
                     verification_status: str | None = None):
        stmt = select(Tenant).where(Tenant.vertical == HOME_SERVICES_VERTICAL)
        if status:
            stmt = stmt.where(Tenant.status == status)
        if status_in:
            stmt = stmt.where(Tenant.status.in_(status_in))
        if verification_status:
            stmt = stmt.where(Tenant.verification_status == verification_status)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(
                Tenant.business_name.ilike(like), Tenant.tenant_name.ilike(like),
                Tenant.email.ilike(like), Tenant.phone.ilike(like),
                Tenant.tenant_code.ilike(like),
            ))
        return stmt

    async def get_summary(self, *, q: str | None = None) -> dict:
        # Aggregate in PostgreSQL.  Loading every Tenant row and counting in
        # Python made this dashboard endpoint O(n) in application memory and
        # unusable for a large provider population.
        base = self._base_query(q=q).subquery()
        counts = (await self.db.execute(select(
            func.count().label("total_providers"),
            func.count().filter(base.c.verification_status.in_(("not_started", "pending"))).label("pending_verification"),
            func.count().filter(base.c.status == "active").label("active"),
            func.count().filter(base.c.status.in_(SETUP_INCOMPLETE_STATUSES)).label("setup_incomplete"),
            func.count().filter(base.c.verification_status == "changes_requested").label("changes_requested"),
            func.count().filter(base.c.status == "suspended").label("suspended"),
            func.count().filter(or_(base.c.status == "rejected", base.c.verification_status == "rejected")).label("rejected"),
            func.count().filter(or_(base.c.verification_status == "changes_requested", base.c.status == "suspended")).label("needs_attention"),
        ).select_from(base))).one()
        return {
            key: int(getattr(counts, key) or 0)
            for key in (
                "total_providers", "pending_verification", "active",
                "setup_incomplete", "changes_requested", "suspended",
                "rejected", "needs_attention",
            )
        }

    async def list_providers(self, *, q: str | None = None, status: str | None = None,
                              status_in: list[str] | None = None,
                              verification_status: str | None = None,
                              page: int = 1, page_size: int = 20,
                              sort_by: str = "created_at", sort_dir: str = "desc") -> dict:
        base = self._base_query(q=q, status=status, status_in=status_in, verification_status=verification_status)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0

        sort_col = {"created_at": Tenant.created_at, "health_score": Tenant.health_score,
                    "business_name": Tenant.business_name}.get(sort_by, Tenant.created_at)
        stmt = base.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        tenants = (await self.db.execute(stmt)).scalars().all()

        tenant_ids = [t.id for t in tenants]
        billing_by_tenant, deposit_by_tenant = {}, {}
        if tenant_ids:
            billing_rows = (await self.db.execute(
                select(TenantBilling).where(TenantBilling.tenant_id.in_(tenant_ids))
            )).scalars().all()
            billing_by_tenant = {b.tenant_id: b for b in billing_rows}
            deposit_rows = (await self.db.execute(
                select(SecurityDeposit).where(SecurityDeposit.tenant_id.in_(tenant_ids))
            )).scalars().all()
            deposit_by_tenant = {d.tenant_id: d for d in deposit_rows}

        items = [self._provider_row(t, billing_by_tenant.get(t.id), deposit_by_tenant.get(t.id)) for t in tenants]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def _provider_row(self, t: Tenant, billing: TenantBilling | None, deposit: SecurityDeposit | None) -> dict:
        credit_balance = Decimal(str(billing.credit_balance)) if billing else Decimal("0")
        return {
            "provider_id": str(t.id),
            "tenant_code": t.tenant_code,
            "business_name": t.business_name or t.tenant_name,
            "logo_url": t.logo_url,
            "registration_status": t.status,
            "verification_status": t.verification_status,
            "health_score": float(t.health_score),
            "health_band": t.health_band,
            "rating_average": float(t.rating_average),
            "credit_balance": str(credit_balance),
            "credit_status": "low" if credit_balance < LOW_BALANCE_THRESHOLD else "healthy",
            "deposit_status": deposit.status if deposit else "not_required",
            "email": t.email,
            "phone": t.phone,
            "city": t.city,
            "state": t.state,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "suspended_at": t.suspended_at.isoformat() if t.suspended_at else None,
            "suspension_reason": t.suspension_reason,
        }

    async def get_provider_detail(self, provider_id: uuid.UUID) -> dict:
        tenant = await self.db.get(Tenant, provider_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("HomeServicesProvider", str(provider_id))
        billing = (await self.db.execute(
            select(TenantBilling).where(TenantBilling.tenant_id == provider_id)
        )).scalar_one_or_none()
        deposit = (await self.db.execute(
            select(SecurityDeposit).where(SecurityDeposit.tenant_id == provider_id)
        )).scalar_one_or_none()

        owner = None
        if tenant.owner_user_id:
            from app.engines.auth.models import User
            owner = await self.db.get(User, tenant.owner_user_id)

        row = self._provider_row(tenant, billing, deposit)
        return {
            **row,
            "owner_user_id": str(tenant.owner_user_id) if tenant.owner_user_id else None,
            "owner_name": owner.full_name if owner else None,
            "owner_email": owner.email if owner else None,
            # Tenant.vertical is a single string column today (no
            # TenantBusinessVertical join table exists yet), so a tenant can
            # only ever match one vertical -- this is always 0 for now, not
            # fabricated as if multi-vertical membership already existed.
            "additional_vertical_assignments": 0,
            "address": {
                "line1": tenant.address_line1, "line2": tenant.address_line2,
                "city": tenant.city, "state": tenant.state, "zipcode": tenant.zipcode,
            },
            "gst_number": tenant.gst_number,
            "is_discoverable": tenant.is_discoverable,
            "suspended_at": tenant.suspended_at.isoformat() if tenant.suspended_at else None,
            "suspension_reason": tenant.suspension_reason,
            # Finance readiness -- contextual only; full finance operations
            # (adjustments, deposit returns) remain in Home Services Finance,
            # never duplicated here.
            "finance_readiness": {
                "security_deposit_status": deposit.status if deposit else "not_required",
                "available_credits": str(billing.credit_balance) if billing else "0",
                "low_balance": (Decimal(str(billing.credit_balance)) if billing else Decimal("0")) < LOW_BALANCE_THRESHOLD,
            },
            # Readiness checks grounded in what's actually queryable today.
            # Staff eligibility, exact job-type configuration, and coverage
            # readiness need engines this service doesn't yet reach into --
            # left absent (not fabricated as "ready") rather than guessed.
            "readiness": {
                "business_verification_complete": tenant.verification_status == "approved",
                "security_deposit_active": bool(deposit and deposit.status == "paid"),
                "credit_account_healthy": bool(billing) and Decimal(str(billing.credit_balance if billing else 0)) >= LOW_BALANCE_THRESHOLD,
                "admin_hold_active": tenant.status == "suspended",
            },
        }

    # ── Provider 360 Finance tab ──────────────────────────────────────────────
    # Composes the canonical HomeServicesFinanceService (finance_hub) filtered
    # to this one provider -- reuses list_provider_charges/list_topups exactly
    # as the Home Services Finance workspace does, not a second finance model.
    #
    # ADDED (2026-08-04): the provider's own payment-acceptance / invoicing
    # setup (TenantFinanceReadiness -- accepts_cash/upi/card/bank_transfer,
    # invoice_prefix, issue_customer_receipt) is captured during Home
    # Services onboarding but was never surfaced here, even though real
    # data exists for it (confirmed live for Guramrit). This is exactly the
    # "what did the tenant choose during setup" finance-side info that was
    # missing from this tab.
    async def get_provider_finance(self, provider_id: uuid.UUID) -> dict:
        tenant = await self.db.get(Tenant, provider_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("HomeServicesProvider", str(provider_id))

        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        from app.engines.tenant_engine.models import TenantFinanceReadiness
        fin = HomeServicesFinanceService(db=self.db)

        billing = (await self.db.execute(
            select(TenantBilling).where(TenantBilling.tenant_id == provider_id)
        )).scalar_one_or_none()
        deposit = (await self.db.execute(
            select(SecurityDeposit).where(SecurityDeposit.tenant_id == provider_id)
        )).scalar_one_or_none()
        readiness = (await self.db.execute(
            select(TenantFinanceReadiness).where(TenantFinanceReadiness.tenant_id == provider_id)
        )).scalar_one_or_none()

        charges = await fin.list_provider_charges(tenant_id=str(provider_id), page=1, page_size=20)
        topups = await fin.list_topups(tenant_id=str(provider_id), page=1, page_size=20)

        return {
            "usage_credits": {
                "balance": str(billing.credit_balance) if billing else "0",
                "low_balance": (Decimal(str(billing.credit_balance)) if billing else Decimal("0")) < LOW_BALANCE_THRESHOLD,
            },
            "security_deposit": {
                "status": deposit.status if deposit else "not_required",
                "required_amount": str(deposit.required_amount) if deposit else "0",
                "current_balance": str(deposit.current_balance) if deposit else "0",
            } if deposit else {"status": "not_required", "required_amount": "0", "current_balance": "0"},
            "provider_charges": charges["items"],
            "topup_history": topups["items"],
            # Customer pays the provider directly -- ServiceOS never collects
            # the job payment. This tab shows provider-side charges only;
            # customer payment records live in Direct Customer Payments
            # (Home Services Finance), not duplicated here.
            "customer_payment_note": "Customer pays provider directly. ServiceOS does not collect or hold this payment.",
            "payment_setup": {
                "accepts_cash": readiness.accepts_cash,
                "accepts_upi": readiness.accepts_upi,
                "accepts_card_at_service_location": readiness.accepts_card_at_service_location,
                "accepts_bank_transfer": readiness.accepts_bank_transfer,
                "payment_confirmation_required": readiness.payment_confirmation_required,
                "invoice_business_name": readiness.invoice_business_name,
                "invoice_prefix": readiness.invoice_prefix,
                "issue_customer_receipt": readiness.issue_customer_receipt,
            } if readiness else None,
        }

    # ── Provider 360 Quality & Complaints tab ────────────────────────────────
    # CustomerComplaint.tenant_id already scopes to this one provider; since
    # Tenant.vertical is single-valued today, any complaint tied to this
    # tenant_id is a Home Services complaint by construction -- no separate
    # vertical_id join needed for correctness (that column exists for a
    # future multi-vertical tenant model, per its own migration comment).
    async def get_provider_quality(self, provider_id: uuid.UUID, *, page: int = 1, page_size: int = 20) -> dict:
        tenant = await self.db.get(Tenant, provider_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("HomeServicesProvider", str(provider_id))

        from app.engines.complaints.models import CustomerComplaint
        clauses = [CustomerComplaint.tenant_id == provider_id]
        total = (await self.db.execute(
            select(func.count()).select_from(select(CustomerComplaint).where(*clauses).subquery())
        )).scalar() or 0
        rows = (await self.db.execute(
            select(CustomerComplaint).where(*clauses)
            .order_by(CustomerComplaint.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        open_count = sum(1 for c in rows if c.status not in ("resolved", "closed", "rejected"))

        return {
            "rating_average": float(tenant.rating_average),
            "health_score": float(tenant.health_score),
            "health_band": tenant.health_band,
            "open_complaints_count": open_count,
            "total_complaints": total,
            "complaints": [{
                "complaint_id": str(c.id),
                "complaint_number": c.complaint_number,
                "status": c.status,
                "severity": c.severity,
                "sla_status": c.sla_status,
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            } for c in rows],
            "page": page, "page_size": page_size,
        }

    # ── Provider 360 Team & Capacity tab ─────────────────────────────────────
    # BUG FIX (2026-08-04): this used to read StaffBusinessVertical
    # (vertical_directory engine, migration 179), the "canonical explicit
    # staff-to-vertical assignment" table -- except nothing in the codebase
    # ever inserts a row into it (grep-verified: zero db.add(StaffBusinessVertical(...))
    # call sites anywhere). Every provider's Team & Capacity tab has always
    # returned 0 staff, for every tenant, regardless of how many real staff
    # they have -- confirmed live: tenant 244beeec ("Guramrit") has a real,
    # active technician ("dhiman", users.tenant_id match) that this tab
    # reported as empty. Repointed to query `users` directly, scoped by
    # tenant_id, matching the same reliable source /v1/admin/staff already
    # uses successfully. Per-staff "capability"/fine-grained availability
    # concepts don't exist at the User level -- reported as unavailable
    # (0 / not fabricated) rather than guessed; "available" here means
    # active and not currently assigned to an in-progress ServiceJob (the
    # real Home Services job table, not the dead field_ops `jobs` table).
    async def get_provider_team(self, provider_id: uuid.UUID) -> dict:
        tenant = await self.db.get(Tenant, provider_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("HomeServicesProvider", str(provider_id))

        from app.engines.auth.models import User

        staff = (await self.db.execute(
            select(User).where(
                User.tenant_id == provider_id,
                User.role.notin_(("customer", "super_admin", "tenant_owner")),
                User.deleted_at.is_(None),
            )
        )).scalars().all()

        active_jobs_by_staff: dict[uuid.UUID, int] = {}
        if staff:
            staff_ids = [u.id for u in staff]
            job_rows = (await self.db.execute(
                select(ServiceJob.assigned_staff_id, func.count())
                .where(ServiceJob.assigned_staff_id.in_(staff_ids),
                       ServiceJob.status.notin_(("completed", "cancelled")))
                .group_by(ServiceJob.assigned_staff_id)
            )).all()
            active_jobs_by_staff = {sid: count for sid, count in job_rows}

        def is_available(u) -> bool:
            return u.is_active and active_jobs_by_staff.get(u.id, 0) == 0

        return {
            "total_staff": len(staff),
            "verified_staff": sum(1 for u in staff if u.is_verified),
            "available_staff": sum(1 for u in staff if is_available(u)),
            # Per-job-type capability isn't tracked at the User level today --
            # reported as 0 (not applicable), never guessed.
            "capability_incomplete_staff": 0,
            "suspended_staff": sum(1 for u in staff if not u.is_active),
            "staff": [{
                "staff_id": str(u.id),
                "name": u.full_name,
                "designation": u.role,
                "verification_status": "verified" if u.is_verified else "not_started",
                "assignment_status": "active" if u.is_active else "suspended",
                "availability_status": "available" if is_available(u) else "on_job" if active_jobs_by_staff.get(u.id, 0) else "unavailable",
                "job_type_capabilities": [],
                "is_active": u.is_active,
            } for u in staff],
        }

    # ── Provider 360 Operations tab ──────────────────────────────────────────
    # ServiceJob is the canonical Home-Services-only execution record
    # (structurally isolated -- see home_services_finance_service.py's own
    # docstring on this same fact). Filters by tenant_id only, no separate
    # vertical flag needed.
    async def get_provider_operations(self, provider_id: uuid.UUID, *, page: int = 1, page_size: int = 20) -> dict:
        tenant = await self.db.get(Tenant, provider_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("HomeServicesProvider", str(provider_id))

        clauses = [ServiceJob.tenant_id == provider_id]
        total = (await self.db.execute(
            select(func.count()).select_from(select(ServiceJob).where(*clauses).subquery())
        )).scalar() or 0
        rows = (await self.db.execute(
            select(ServiceJob).where(*clauses)
            .order_by(ServiceJob.updated_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()

        by_status: dict[str, int] = {}
        for j in rows:
            by_status[j.status] = by_status.get(j.status, 0) + 1

        return {
            "total_jobs": total,
            "active_jobs": sum(1 for j in rows if j.status not in ("completed", "cancelled")),
            "by_status": by_status,
            "jobs": [{
                "job_id": str(j.id),
                "job_number": j.job_number,
                "status": j.status,
                "assignment_status": j.assignment_status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            } for j in rows],
            "page": page, "page_size": page_size,
        }

    # ── Provider 360 Documents & Activity tab ────────────────────────────────
    # PlatformAuditLog is the canonical platform-wide audit trail; filtered
    # to this tenant_id, this is Home-Services-scoped by construction (the
    # tenant itself is HS-only).
    #
    # BUG FIX (2026-08-04): this unconditionally reported
    # "documents_available": False and never queried TenantDocument, even
    # though a real document repository (tenant_documents, used by
    # mobile_documents_service.py) exists and had real rows for at least
    # one live tenant (Guramrit: 4 documents) -- confirmed via direct query.
    # Wired to the real table instead of hardcoding absence.
    async def get_provider_activity(self, provider_id: uuid.UUID, *, page: int = 1, page_size: int = 30) -> dict:
        tenant = await self.db.get(Tenant, provider_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("HomeServicesProvider", str(provider_id))

        from app.engines.security.models import PlatformAuditLog
        from app.engines.tenant_engine.models import TenantDocument

        clauses = [PlatformAuditLog.tenant_id == provider_id]
        total = (await self.db.execute(
            select(func.count()).select_from(select(PlatformAuditLog).where(*clauses).subquery())
        )).scalar() or 0
        rows = (await self.db.execute(
            select(PlatformAuditLog).where(*clauses)
            .order_by(PlatformAuditLog.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()

        doc_rows = (await self.db.execute(
            select(TenantDocument)
            .where(TenantDocument.tenant_id == provider_id, TenantDocument.is_current.is_(True))
            .order_by(TenantDocument.doc_type)
        )).scalars().all()

        return {
            "total": total,
            "events": [{
                "id": str(a.id),
                "operation": a.operation,
                "engine_id": a.engine_id,
                "actor_role": a.actor_role,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            } for a in rows],
            "page": page, "page_size": page_size,
            "documents_available": len(doc_rows) > 0,
            "documents": [{
                "id": str(d.id),
                "doc_type": d.doc_type,
                "label": d.label,
                "document_number": d.document_number,
                "status": d.status,
                "issue_date": d.issue_date.isoformat() if d.issue_date else None,
                "expiry_date": d.expiry_date.isoformat() if d.expiry_date else None,
                "file_url": d.file_url,
                "media_asset_id": str(d.media_asset_id) if d.media_asset_id else None,
                "verified_at": d.verified_at.isoformat() if d.verified_at else None,
            } for d in doc_rows],
        }

    # ── Provider 360 Services & Coverage tab ─────────────────────────────────
    # TenantService (admin_catalog engine) is the canonical per-tenant service
    # activation record -- includes the tenant's own setup_status/published_at
    # and price-configured flags. Read-only here; admin never sets tenant_base_
    # price/tenant_min_price/etc. from this page (those stay tenant-owned).
    #
    # BUG FIX (2026-08-04): the "Coverage" section always said "isn't wired
    # into this tab yet" even though real serviceable-area rows exist
    # (tenant_service_areas, confirmed live for Guramrit: 1 zipcode,
    # BASSIPATHANA 140412, ACTIVE) -- the query was simply never written.
    # Wired to the real table.
    async def get_provider_services(self, provider_id: uuid.UUID) -> dict:
        tenant = await self.db.get(Tenant, provider_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("HomeServicesProvider", str(provider_id))

        from app.engines.admin_catalog.models import TenantService, MasterService
        from app.engines.serviceability.models import TenantServiceArea

        rows = (await self.db.execute(
            select(TenantService, MasterService)
            .join(MasterService, MasterService.id == TenantService.master_service_id, isouter=True)
            .where(TenantService.tenant_id == provider_id, TenantService.deleted_at.is_(None))
            .order_by(TenantService.created_at.desc())
        )).all()

        coverage_rows = (await self.db.execute(
            select(TenantServiceArea)
            .where(TenantServiceArea.tenant_id == provider_id, TenantServiceArea.is_active.is_(True))
            .order_by(TenantServiceArea.city, TenantServiceArea.zipcode)
        )).scalars().all()

        def price_configured(ts: TenantService) -> bool:
            return any([ts.tenant_base_price is not None, ts.tenant_min_price is not None,
                        ts.tenant_max_price is not None, ts.tenant_visit_fee is not None])

        return {
            "total_services": len(rows),
            "published_services": sum(1 for ts, _ in rows if ts.published_at is not None),
            "active_services": sum(1 for ts, _ in rows if ts.is_enabled and ts.is_active),
            "price_configured_count": sum(1 for ts, _ in rows if price_configured(ts)),
            "missing_price_config_count": sum(1 for ts, _ in rows if not price_configured(ts)),
            "pricing_ownership": "tenant_owned",
            "services": [{
                "tenant_service_id": str(ts.id),
                "master_service_name": ms.service_name if ms else None,
                "job_type": ts.job_type,
                "is_enabled": ts.is_enabled,
                "is_active": ts.is_active,
                "setup_status": ts.setup_status,
                "published": ts.published_at is not None,
                "requires_brand": ts.requires_brand,
                "requires_type": ts.requires_type,
                "type_coverage_mode": ts.type_coverage_mode,
                "brand_coverage_mode": ts.brand_coverage_mode,
                "price_configured": price_configured(ts),
            } for ts, ms in rows],
            "total_coverage_areas": len(coverage_rows),
            "coverage_areas": [{
                "id": str(a.id),
                "coverage_type": a.coverage_type,
                "city": a.city,
                "zipcode": a.zipcode,
                "status": a.status,
            } for a in coverage_rows],
        }
