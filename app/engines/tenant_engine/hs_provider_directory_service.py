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
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select, func, or_, exists, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.tenant_engine.models import Tenant, TenantBilling
from app.engines.vertical_catalog.models import TenantVerticalEnrollment, Vertical
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

    async def _canonical_health_map(self, tenant_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
        """Fresh, banded Trust & Quality score used by allocation and admin.

        Directory cards previously displayed ``tenants.health_score`` (whose
        historical default was 100) while matching used a different source.
        Returning the same neutral/unassessed state here removes that split.
        """
        if not tenant_ids:
            return {}
        from app.engines.home_service_booking.matching_engine import (
            HEALTH_SCORE_STALE_AFTER_DAYS, MISSING_HEALTH_SCORE_DEFAULT,
        )
        rows = (await self.db.execute(text("""
            SELECT DISTINCT ON (hs.target_id)
                   hs.target_id, hs.score, hs.band_key, hs.calculated_at
              FROM health_scores hs
              JOIN health_formulas hf ON hf.id = hs.formula_id
             WHERE hs.target_type = 'tenant' AND hf.status = 'active'
               AND hs.target_id = ANY(CAST(:ids AS uuid[]))
               AND hs.band_key IS NOT NULL
               AND hs.calculated_at >= now() - (:days * interval '1 day')
             ORDER BY hs.target_id, hs.calculated_at DESC
        """), {"ids": [str(value) for value in tenant_ids], "days": HEALTH_SCORE_STALE_AFTER_DAYS})).mappings().all()
        mapped = {
            row["target_id"]: {
                "score": float(row["score"]), "band": row["band_key"],
                "source": "canonical",
            }
            for row in rows
        }
        for tenant_id in tenant_ids:
            mapped.setdefault(tenant_id, {
                "score": MISSING_HEALTH_SCORE_DEFAULT,
                "band": None,
                "source": "unassessed_default",
            })
        return mapped

    # ── The one shared predicate: summary, list and export all start here ──
    def _base_query(self, *, q: str | None = None, status: str | None = None,
                     status_in: list[str] | None = None,
                     verification_status: str | None = None,
                     city: str | None = None, state: str | None = None,
                     health_band: str | None = None):
        stmt = select(Tenant).where(Tenant.vertical == HOME_SERVICES_VERTICAL)
        if status:
            stmt = stmt.where(Tenant.status == status)
        if status_in:
            stmt = stmt.where(Tenant.status.in_(status_in))
        if verification_status:
            stmt = stmt.where(Tenant.verification_status == verification_status)
        if city:
            stmt = stmt.where(Tenant.city.ilike(f"%{city.strip()}%"))
        if state:
            stmt = stmt.where(Tenant.state.ilike(f"%{state.strip()}%"))
        if health_band:
            from app.engines.trust_quality.models import HealthFormula, HealthScore
            stmt = stmt.where(exists(
                select(1).select_from(HealthScore)
                .join(HealthFormula, HealthFormula.id == HealthScore.formula_id)
                .where(
                    HealthScore.target_type == "tenant",
                    HealthScore.target_id == Tenant.id,
                    HealthScore.band_key == health_band,
                    HealthScore.calculated_at >= datetime.now(timezone.utc) - timedelta(days=7),
                    HealthFormula.status == "active",
                )
            ))
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
            func.count().filter(base.c.verification_status.in_(("pending", "under_review")), exists(
                select(1).select_from(TenantVerticalEnrollment).join(Vertical, Vertical.id == TenantVerticalEnrollment.vertical_id)
                .where(TenantVerticalEnrollment.tenant_id == base.c.id, Vertical.key == 'home_services',
                       TenantVerticalEnrollment.submitted_at.is_not(None), TenantVerticalEnrollment.status == 'submitted')
            )).label("pending_verification"),
            func.count().filter(base.c.status == "active").label("active"),
            func.count().filter(base.c.status.in_(SETUP_INCOMPLETE_STATUSES)).label("setup_incomplete"),
            func.count().filter(base.c.verification_status == "changes_requested").label("changes_requested"),
            func.count().filter(base.c.status == "suspended").label("suspended"),
            func.count().filter(base.c.status == "archived").label("archived"),
            func.count().filter(or_(base.c.status == "rejected", base.c.verification_status == "rejected")).label("rejected"),
            func.count().filter(or_(base.c.verification_status == "changes_requested", base.c.status == "suspended")).label("needs_attention"),
        ).select_from(base))).one()
        return {
            key: int(getattr(counts, key, 0) or 0)
            for key in (
                "total_providers", "pending_verification", "active",
                "setup_incomplete", "changes_requested", "suspended", "archived",
                "rejected", "needs_attention",
            )
        }

    async def list_providers(self, *, q: str | None = None, status: str | None = None,
                              status_in: list[str] | None = None,
                              verification_status: str | None = None,
                              city: str | None = None, state: str | None = None,
                              health_band: str | None = None,
                              page: int = 1, page_size: int = 20,
                              sort_by: str = "created_at", sort_dir: str = "desc") -> dict:
        base = self._base_query(
            q=q, status=status, status_in=status_in,
            verification_status=verification_status, city=city, state=state,
            health_band=health_band,
        )
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0

        if sort_by == "health_score":
            from app.engines.trust_quality.models import HealthFormula, HealthScore
            canonical_health = (
                select(HealthScore.score)
                .join(HealthFormula, HealthFormula.id == HealthScore.formula_id)
                .where(
                    HealthScore.target_type == "tenant",
                    HealthScore.target_id == Tenant.id,
                    HealthScore.band_key.is_not(None),
                    HealthScore.calculated_at >= datetime.now(timezone.utc) - timedelta(days=7),
                    HealthFormula.status == "active",
                )
                .order_by(HealthScore.calculated_at.desc()).limit(1)
                .correlate(Tenant).scalar_subquery()
            )
            sort_col = func.coalesce(canonical_health, 65.0)
        else:
            sort_col = {"created_at": Tenant.created_at,
                    "business_name": Tenant.business_name, "rating_average": Tenant.rating_average,
                    "city": Tenant.city, "verification_status": Tenant.verification_status}.get(sort_by, Tenant.created_at)
        direction = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
        # The id tie-breaker makes adjacent pages deterministic when many rows
        # share a timestamp/status -- essential when the directory is changing.
        stmt = base.order_by(direction, Tenant.id.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        tenants = (await self.db.execute(stmt)).scalars().all()

        tenant_ids = [t.id for t in tenants]
        billing_by_tenant = {}
        if tenant_ids:
            billing_rows = (await self.db.execute(
                select(TenantBilling).where(TenantBilling.tenant_id.in_(tenant_ids))
            )).scalars().all()
            billing_by_tenant = {b.tenant_id: b for b in billing_rows}

        health_by_tenant = await self._canonical_health_map(tenant_ids)

        items = [self._provider_row(t, billing_by_tenant.get(t.id), health_by_tenant.get(t.id)) for t in tenants]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def _provider_row(self, t: Tenant, billing: TenantBilling | None, health: dict | None = None) -> dict:
        credit_balance = Decimal(str(billing.credit_balance)) if billing else Decimal("0")
        health = health or {"score": 65.0, "band": None, "source": "unassessed_default"}
        return {
            "provider_id": str(t.id),
            "tenant_code": t.tenant_code,
            "business_name": t.business_name or t.tenant_name,
            "logo_url": t.logo_url,
            "registration_status": t.status,
            "verification_status": t.verification_status,
            "health_score": float(health["score"]),
            "health_band": health["band"],
            "health_score_source": health["source"],
            "rating_average": float(t.rating_average),
            "credit_balance": str(credit_balance),
            "credit_status": "low" if credit_balance < LOW_BALANCE_THRESHOLD else "healthy",
            # The deposit went in migration 317/318 and its local was removed
            # with it, but this reference was left behind -- so building ANY
            # provider row raised NameError and the whole Providers console
            # 500'd. Credit is what stands in the deposit's place.
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
        owner = None
        if tenant.owner_user_id:
            from app.engines.auth.models import User
            owner = await self.db.get(User, tenant.owner_user_id)

        health = (await self._canonical_health_map([provider_id]))[provider_id]
        row = self._provider_row(tenant, billing, health)
        from app.engines.vertical_catalog.home_services_setup_service import get_setup_overview
        from app.engines.provider_portal.router import _evaluate_provider_bookability
        from app.engines.tenant_engine.models import TenantBusinessProfile
        setup = await get_setup_overview(self.db, provider_id)
        bookability = await _evaluate_provider_bookability(self.db, provider_id)
        profile = (await self.db.execute(select(TenantBusinessProfile).where(TenantBusinessProfile.tenant_id == provider_id))).scalar_one_or_none()
        from app.engines.vertical_catalog.seat_enforcement import get_seat_usage
        seats = await get_seat_usage(self.db, provider_id)
        enrollment_status = setup["vertical"]["status"]
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
            "business_type": tenant.business_type,
            "gst_number": (profile.gstin if profile else None) or tenant.gst_number,
            "profile_completion_percentage": setup["progress"]["percentage"],
            "setup_progress": setup["progress"],
            "setup_sections": setup["sections"],
            "enrollment_status": enrollment_status,
            "is_bookable": enrollment_status == "active" and bookability["is_bookable"],
            "bookability_blockers": bookability["bookability_blockers"],
            "is_discoverable": tenant.is_discoverable,
            "suspended_at": tenant.suspended_at.isoformat() if tenant.suspended_at else None,
            "suspension_reason": tenant.suspension_reason,
            # Finance readiness -- contextual only; full finance operations
            # (adjustments, top-ups) remain in Home Services Finance,
            # never duplicated here.
            "finance_readiness": {
                "entitled_seats": seats["entitled_seats"],
                "available_credits": str(billing.credit_balance) if billing else "0",
                "low_balance": (Decimal(str(billing.credit_balance)) if billing else Decimal("0")) < LOW_BALANCE_THRESHOLD,
            },
            # Setup and operational readiness share the tenant's read services.
            "readiness": {
                "business_verification_complete": tenant.verification_status in ("approved", "verified"),
                "seats_purchased": seats["entitled_seats"] > 0,
                "credit_account_healthy": bool(billing) and Decimal(str(billing.credit_balance if billing else 0)) >= LOW_BALANCE_THRESHOLD,
                "admin_hold_active": tenant.status == "suspended",
                "setup_complete": setup["progress"]["percentage"] == 100,
                "enrollment_active": enrollment_status == "active",
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
        readiness = (await self.db.execute(
            select(TenantFinanceReadiness).where(TenantFinanceReadiness.tenant_id == provider_id)
        )).scalar_one_or_none()

        from app.engines.vertical_catalog.seat_enforcement import get_seat_usage
        seat_usage = await get_seat_usage(self.db, provider_id)

        charges = await fin.list_provider_charges(tenant_id=str(provider_id), page=1, page_size=20)
        topups = await fin.list_topups(tenant_id=str(provider_id), page=1, page_size=20)
        plan_orders = (await self.db.execute(text("SELECT id,amount,currency,seats_granted,credited_amount,status,created_at FROM activation_payment_orders WHERE tenant_id=:tid AND topup_plan_id IS NOT NULL ORDER BY created_at DESC LIMIT 20"), {"tid":str(provider_id)})).mappings().all()

        return {
            "usage_credits": {
                "balance": str(billing.credit_balance) if billing else "0",
                "low_balance": (Decimal(str(billing.credit_balance)) if billing else Decimal("0")) < LOW_BALANCE_THRESHOLD,
            },
            "technician_seats": {
                "entitled": seat_usage["entitled_seats"],
                "used": seat_usage["used_seats"],
                "available": max(0, seat_usage["entitled_seats"] - seat_usage["used_seats"]),
            },
            "provider_charges": charges["items"],
            "topup_history": topups["items"],
            "plan_purchase_history": [dict(order) for order in plan_orders],
            # Customer pays the provider directly -- Fuvay never collects
            # the job payment. This tab shows provider-side charges only;
            # customer payment records live in Direct Customer Payments
            # (Home Services Finance), not duplicated here.
            "customer_payment_note": "Customer pays provider directly. Fuvay does not collect or hold this payment.",
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
        open_count = (await self.db.execute(
            select(func.count(CustomerComplaint.id)).where(
                *clauses,
                CustomerComplaint.status.notin_(("resolved", "closed", "rejected")),
            )
        )).scalar() or 0
        job_counts = (await self.db.execute(select(
            func.count(ServiceJob.id).label("total"),
            func.count(ServiceJob.id).filter(ServiceJob.status == "completed").label("completed"),
            func.count(ServiceJob.id).filter(ServiceJob.status == "cancelled").label("cancelled"),
            func.count(func.distinct(ServiceJob.customer_id)).filter(ServiceJob.customer_id.isnot(None)).label("customers"),
        ).where(ServiceJob.tenant_id == provider_id))).one()
        repeat_customers = (await self.db.execute(select(func.count()).select_from(
            select(ServiceJob.customer_id)
            .where(ServiceJob.tenant_id == provider_id, ServiceJob.customer_id.isnot(None))
            .group_by(ServiceJob.customer_id).having(func.count(ServiceJob.id) > 1).subquery()
        ))).scalar() or 0
        total_jobs = int(job_counts.total or 0)
        completed_jobs = int(job_counts.completed or 0)
        cancelled_jobs = int(job_counts.cancelled or 0)

        health = (await self._canonical_health_map([provider_id]))[provider_id]
        return {
            "rating_average": float(tenant.rating_average),
            "health_score": float(health["score"]),
            "health_band": health["band"],
            "health_score_source": health["source"],
            "open_complaints_count": open_count,
            "total_complaints": total,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "cancelled_jobs": cancelled_jobs,
            "completion_rate": round((completed_jobs / total_jobs) * 100, 1) if total_jobs else 0.0,
            "cancellation_rate": round((cancelled_jobs / total_jobs) * 100, 1) if total_jobs else 0.0,
            "unique_customers": int(job_counts.customers or 0),
            "repeat_customers": int(repeat_customers),
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
    async def get_provider_team(self, provider_id: uuid.UUID, *, page: int = 1, page_size: int = 20) -> dict:
        tenant = await self.db.get(Tenant, provider_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("HomeServicesProvider", str(provider_id))

        from app.engines.tenant_engine.provider_team_projection import provider_team_projection
        return await provider_team_projection(self.db, provider_id, page, page_size)

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

        status_rows = (await self.db.execute(
            select(ServiceJob.status, func.count(ServiceJob.id))
            .where(*clauses).group_by(ServiceJob.status)
        )).all()
        by_status = {str(status): int(count) for status, count in status_rows}
        active_jobs = sum(count for status, count in by_status.items()
                          if status not in ("completed", "cancelled"))

        return {
            "total_jobs": total,
            "active_jobs": active_jobs,
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
                "version": d.version,
                "uploaded_at": d.created_at.isoformat() if d.created_at else None,
                "rejection_reason": d.rejection_reason,
                "staff_member_id": str(d.staff_member_id) if d.staff_member_id else None,
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

        from app.engines.admin_catalog.tenant_service import TenantCatalogService
        from app.engines.vertical_catalog.service_setup_readiness import service_setup_readiness
        catalog = TenantCatalogService(self.db, actor_tenant_id=provider_id)
        configured = {}
        for ts, _ in rows:
            if ts.is_enabled and ts.is_active:
                validation = await catalog.validate_for_publish(ts.id)
                configured[ts.id] = service_setup_readiness([(str(ts.id), validation)])["complete"]
        def price_configured(ts: TenantService) -> bool:
            return configured.get(ts.id, False)

        hours = (await self.db.execute(text("SELECT day_of_week,start_time,end_time,break_start_time,break_end_time,max_jobs_per_day,timezone FROM provider_availability_rules WHERE tenant_id=:tid AND scope_type='provider' AND scope_id IS NULL AND is_active=true ORDER BY day_of_week,start_time"), {"tid": str(provider_id)})).mappings().all()
        exceptions = (await self.db.execute(text("SELECT date,reason,full_day_closed FROM tenant_availability_exceptions WHERE tenant_id=:tid AND status='active' AND date>=CURRENT_DATE ORDER BY date"), {"tid": str(provider_id)})).mappings().all()

        return {
            "total_services": len(rows),
            "published_services": sum(1 for ts, _ in rows if ts.published_at is not None),
            "active_services": sum(1 for ts, _ in rows if ts.is_enabled and ts.is_active),
            "price_configured_count": sum(1 for ts, _ in rows if price_configured(ts)),
            "missing_price_config_count": sum(1 for ts, _ in rows if ts.is_enabled and ts.is_active and not price_configured(ts)),
            "business_hours": [dict(r) for r in hours],
            "schedule_exceptions": [dict(r) for r in exceptions],
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
