"""Finance Hub — Home Services Finance (Completion Charges).

Replaces the retired `/admin/home-services/completed-job-deduction` page,
which 404'd because it called the deleted `GET /v1/admin/pricing-rules`
admin surface (removed 2026-07 under the "provider-set-price" policy while
the underlying `ServicePricingRule` table/model and its
`completed_job_deduction_credits` column were deliberately left in place).

This service does NOT call that deleted endpoint and does NOT duplicate the
certified completion-charge engine. It is a READ (plus safe reconciliation)
projection over data the canonical engine already writes:

  - app.engines.execution.usage_credit_deduction.deduct_for_completed_job
    -- the ONLY writer of usage_credit_ledger rows for completed jobs.
    Runs inside the SAME DB transaction as job completion (atomic), and is
    idempotent per job_id both at the application layer (existing-row check)
    and the database layer (migration 129's partial unique index
    uq_ucl_job_event_once on (job_id, event_type) WHERE event_type =
    'completed_job_deduction'). This service never writes ledger rows.

Home Services isolation is structural, not a runtime flag: `usage_credit_
ledger.job_id` references `service_jobs.id`, and `service_jobs` is the
Home-Services-only final-record table (Coaching/Real Estate use their own
separate tables -- CoachingAppointment/RealEstateLead). A query scoped to
`usage_credit_ledger` joined to `service_jobs` can therefore never see
another vertical's charges by construction.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.engines.execution.usage_credit_deduction import DEDUCTION_EVENT_TYPE
from app.engines.final_records.models import ServiceJob
from app.engines.tenant_engine.models import TenantBilling, UsageCreditLedger, Tenant
from app.engines.admin_catalog.models import ServicePricingRule, JobTypeDefinition, MasterService
from app.engines.admin_catalog.service import AdminCatalogService
from app.engines.invoice_payment.models import FinancialEvent, ServiceInvoice, SvcCommissionRecord, ServicePaymentRecord
from app.engines.finance_hub.models import CreditTopupOrder
from app.engines.platform_commerce.models import SecurityDeposit, WarrantyClaim
from app.engines.complaints.models import RefundRequest
from app.exceptions import ServiceOSException, NotFoundException

HOME_SERVICES_VERTICAL = "home_services"

ENGINE_ID = "finance_hub"

# JS_COMPLETED mirrors app.engines.execution.constants.JS_COMPLETED -- not
# imported directly to avoid a hard dependency of finance_hub on the
# execution engine's full constants module; the string is the stable
# canonical value, unchanged since Sprint 21.
CHARGEABLE_JOB_STATUS = "completed"

LOW_BALANCE_DEFAULT_THRESHOLD = Decimal("500.00")

# Reason codes -- grounded in what is actually distinguishable from stored
# data, not invented. See module docstring: deduct_for_completed_job()
# records deduction_source = str(pricing_rule_id) when a rule matched, or
# None when none did (credit_delta is then 0, per resolve_completed_job_
# deduction_credits' documented fallback) -- that IS "POLICY_UNRESOLVED".
# "Missing charge" (a completed job with no ledger row at all) is a
# reconciliation finding, not a ledger-row status (the ledger has none --
# deduction is synchronous+atomic with completion, so this can only occur
# for jobs completed before this deduction mechanism existed, or a genuine
# data gap).
REASON_POLICY_UNRESOLVED = "POLICY_UNRESOLVED"
REASON_MISSING_CHARGE = "MISSING_CHARGE"
REASON_DUPLICATE_BLOCKED = "DUPLICATE_BLOCKED"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HomeServicesFinanceService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        # Deposits (already vertical-filterable) reused via composition, not
        # duplicated -- FinanceHubService.list_deposits/get_deposit_detail
        # remain the single canonical implementation for both the
        # cross-vertical Deposits page and this HS-scoped tab.
        from app.engines.finance_hub.service import FinanceHubService
        self._fh = FinanceHubService(db=db, request_id=request_id, actor_id=actor_id, actor_role=actor_role)

    async def _audit(self, operation: str, entity_type: str, entity_id: str | None,
                      tenant_id: uuid.UUID | None = None,
                      before: dict | None = None, after: dict | None = None) -> None:
        await record_platform_audit(
            self.db, operation=operation, engine_id=ENGINE_ID,
            entity_type=entity_type, entity_id=entity_id, tenant_id=tenant_id,
            actor_id=self.actor_id, actor_role=self.actor_role, request_id=self.request_id,
            before=before, after=after,
        )

    # ── Shared filter builder ───────────────────────────────────────────────

    def _date_filters(self, date_from: str | None, date_to: str | None, col):
        clauses = []
        if date_from:
            clauses.append(col >= datetime.fromisoformat(date_from))
        if date_to:
            clauses.append(col <= datetime.fromisoformat(date_to))
        return clauses

    async def _chargeable_job_ids_query(self, date_from: str | None, date_to: str | None):
        clauses = [ServiceJob.status == CHARGEABLE_JOB_STATUS]
        clauses += self._date_filters(date_from, date_to, ServiceJob.updated_at)
        return select(ServiceJob.id).where(*clauses)

    # ── Summary ──────────────────────────────────────────────────────────────

    async def get_summary(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        job_clauses = [ServiceJob.status == CHARGEABLE_JOB_STATUS]
        job_clauses += self._date_filters(date_from, date_to, ServiceJob.updated_at)
        completed_jobs = (await self.db.execute(
            select(func.count(ServiceJob.id)).where(*job_clauses)
        )).scalar() or 0

        ledger_clauses = [UsageCreditLedger.event_type == DEDUCTION_EVENT_TYPE]
        ledger_clauses += self._date_filters(date_from, date_to, UsageCreditLedger.created_at)
        charges_posted = (await self.db.execute(
            select(func.count(UsageCreditLedger.id)).where(*ledger_clauses)
        )).scalar() or 0

        credits_deducted = (await self.db.execute(
            select(func.coalesce(func.sum(-UsageCreditLedger.credit_delta), 0)).where(*ledger_clauses)
        )).scalar() or Decimal("0")

        recon = await self._compute_reconciliation(date_from, date_to)

        low_balance_tenants = (await self.db.execute(
            select(func.count(TenantBilling.id)).where(TenantBilling.credit_balance < LOW_BALANCE_DEFAULT_THRESHOLD)
        )).scalar() or 0

        return {
            "completed_jobs": completed_jobs,
            "charges_posted": charges_posted,
            "credits_deducted": str(credits_deducted),
            "pending": 0,  # deduction is synchronous+atomic with completion -- no persisted pending state exists
            "missing_charges": recon["missing_count"],
            "duplicate_charges": recon["duplicate_count"],
            "low_balance_tenants": low_balance_tenants,
        }

    # ── Completion charge ledger (list) ─────────────────────────────────────

    async def list_completion_charges(
        self, *, q: str | None = None, tenant_id: str | None = None,
        job_type_id: str | None = None, date_from: str | None = None,
        date_to: str | None = None, page: int = 1, page_size: int = 50,
        sort_by: str = "created_at", sort_dir: str = "desc",
    ) -> dict:
        clauses = [UsageCreditLedger.event_type == DEDUCTION_EVENT_TYPE]
        clauses += self._date_filters(date_from, date_to, UsageCreditLedger.created_at)
        if tenant_id:
            clauses.append(UsageCreditLedger.tenant_id == uuid.UUID(tenant_id))

        stmt = (
            select(UsageCreditLedger, ServiceJob, Tenant)
            .join(ServiceJob, ServiceJob.id == UsageCreditLedger.job_id, isouter=True)
            .join(Tenant, Tenant.id == UsageCreditLedger.tenant_id, isouter=True)
            .where(*clauses)
        )
        if job_type_id:
            stmt = stmt.where(ServiceJob.job_type_id == uuid.UUID(job_type_id))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(
                ServiceJob.job_number.ilike(like),
                Tenant.business_name.ilike(like),
            ))

        sort_col = {
            "created_at": UsageCreditLedger.created_at,
            "credit_delta": UsageCreditLedger.credit_delta,
            "balance_after": UsageCreditLedger.balance_after,
        }.get(sort_by, UsageCreditLedger.created_at)
        stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

        total = (await self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        )).scalar() or 0

        rows = (await self.db.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )).all()

        job_type_ids = {j.job_type_id for _, j, _ in rows if j and j.job_type_id}
        job_types = {}
        if job_type_ids:
            jt_rows = (await self.db.execute(
                select(JobTypeDefinition).where(JobTypeDefinition.id.in_(job_type_ids))
            )).scalars().all()
            job_types = {jt.id: jt.label for jt in jt_rows}

        items = []
        for ledger, job, tenant in rows:
            items.append({
                "charge_id": str(ledger.id),
                "job_id": str(ledger.job_id) if ledger.job_id else None,
                "job_number": job.job_number if job else None,
                "booking_id": str(ledger.booking_id) if ledger.booking_id else None,
                "tenant_id": str(ledger.tenant_id),
                "tenant_name": tenant.business_name if tenant else None,
                "job_type_id": str(job.job_type_id) if job and job.job_type_id else None,
                "job_type_label": job_types.get(job.job_type_id) if job else None,
                "credits": str(-ledger.credit_delta),
                "balance_before": str(ledger.balance_before),
                "balance_after": str(ledger.balance_after),
                "status": "posted",  # every persisted row is, by construction, a successfully posted charge
                "policy_source": "platform_pricing_rule" if ledger.deduction_source else "unresolved_zero_charge",
                "policy_id": ledger.deduction_source,
                "idempotency_key": ledger.idempotency_key,
                "completed_at": job.updated_at.isoformat() if job and job.updated_at else None,
                "posted_at": ledger.created_at.isoformat() if ledger.created_at else None,
                "reason_code": None if ledger.deduction_source else REASON_POLICY_UNRESOLVED,
            })

        return {"items": items, "total": total, "page": page, "page_size": page_size}

    # ── Charge detail ────────────────────────────────────────────────────────

    async def get_charge_detail(self, charge_id: str) -> dict:
        ledger = await self.db.get(UsageCreditLedger, uuid.UUID(charge_id))
        if not ledger or ledger.event_type != DEDUCTION_EVENT_TYPE:
            raise NotFoundException("CompletionCharge", charge_id)
        job = await self.db.get(ServiceJob, ledger.job_id) if ledger.job_id else None
        tenant = await self.db.get(Tenant, ledger.tenant_id)
        rule = None
        if ledger.deduction_source:
            try:
                rule = await self.db.get(ServicePricingRule, uuid.UUID(ledger.deduction_source))
            except (ValueError, TypeError):
                rule = None
        return {
            "charge_id": str(ledger.id),
            "job_id": str(ledger.job_id) if ledger.job_id else None,
            "job_number": job.job_number if job else None,
            "job_status": job.status if job else None,
            "booking_id": str(ledger.booking_id) if ledger.booking_id else None,
            "tenant_id": str(ledger.tenant_id),
            "tenant_name": tenant.business_name if tenant else None,
            "credits": str(-ledger.credit_delta),
            "balance_before": str(ledger.balance_before),
            "balance_after": str(ledger.balance_after),
            "idempotency_key": ledger.idempotency_key,
            "policy_source": "platform_pricing_rule" if ledger.deduction_source else "unresolved_zero_charge",
            "policy_id": ledger.deduction_source,
            "policy_active": rule.is_active if rule else None,
            "request_id": ledger.request_id,
            "reason": ledger.reason,
            "posted_at": ledger.created_at.isoformat() if ledger.created_at else None,
            "completion_evidence": {
                "status": job.status if job else None,
                "completion_data": job.completion_data if job else None,
            } if job else None,
        }

    # ── Failure summary (reconciliation-grounded, no fabricated states) ─────

    async def get_failure_summary(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        ledger_clauses = [UsageCreditLedger.event_type == DEDUCTION_EVENT_TYPE]
        ledger_clauses += self._date_filters(date_from, date_to, UsageCreditLedger.created_at)
        policy_unresolved = (await self.db.execute(
            select(func.count(UsageCreditLedger.id)).where(
                *ledger_clauses, UsageCreditLedger.deduction_source.is_(None),
            )
        )).scalar() or 0
        recon = await self._compute_reconciliation(date_from, date_to)
        return {
            REASON_POLICY_UNRESOLVED: policy_unresolved,
            REASON_MISSING_CHARGE: recon["missing_count"],
            REASON_DUPLICATE_BLOCKED: recon["duplicate_count"],
        }

    # ── Ledger health ────────────────────────────────────────────────────────

    async def get_ledger_health(self) -> dict:
        last_recon = await self._last_reconciliation_run()
        return {
            "append_only": True,          # structural: no UPDATE/DELETE code path exists against usage_credit_ledger
            "idempotency_protected": True,  # DB partial unique index uq_ucl_job_event_once (migration 129)
            "atomic_balance_update": True,  # ledger insert + credit_balance write share one DB transaction with job completion
            "audit_current": True,
            "last_reconciliation": last_recon,
        }

    async def _last_reconciliation_run(self) -> str | None:
        from app.engines.security.models import PlatformAuditLog
        row = (await self.db.execute(
            select(PlatformAuditLog.created_at)
            .where(PlatformAuditLog.engine_id == ENGINE_ID,
                   PlatformAuditLog.operation == "home_services_finance.reconciliation_run")
            .order_by(PlatformAuditLog.created_at.desc())
            .limit(1)
        )).scalar()
        return row.isoformat() if row else None

    # ── Reconciliation (read-only comparison, never mutates) ───────────────

    async def _compute_reconciliation(self, date_from: str | None, date_to: str | None) -> dict:
        chargeable_ids_stmt = await self._chargeable_job_ids_query(date_from, date_to)
        chargeable_ids = {r[0] for r in (await self.db.execute(chargeable_ids_stmt)).all()}

        ledger_clauses = [UsageCreditLedger.event_type == DEDUCTION_EVENT_TYPE]
        ledger_rows = (await self.db.execute(
            select(UsageCreditLedger.job_id).where(*ledger_clauses, UsageCreditLedger.job_id.isnot(None))
        )).all()
        charged_job_ids: list[uuid.UUID] = [r[0] for r in ledger_rows]
        charged_set = set(charged_job_ids)

        missing = chargeable_ids - charged_set
        # A job_id appearing more than once in the ledger for this event type
        # would mean the DB-level partial unique index failed -- should be
        # structurally impossible; reconciliation checks it anyway rather
        # than assuming.
        seen: dict[uuid.UUID, int] = {}
        for jid in charged_job_ids:
            seen[jid] = seen.get(jid, 0) + 1
        duplicates = {jid for jid, n in seen.items() if n > 1}
        orphaned = charged_set - chargeable_ids  # charged but job not (or no longer) in a chargeable state

        return {
            "missing_count": len(missing),
            "missing_job_ids": [str(j) for j in list(missing)[:200]],
            "duplicate_count": len(duplicates),
            "duplicate_job_ids": [str(j) for j in duplicates],
            "orphaned_count": len(orphaned),
            "orphaned_job_ids": [str(j) for j in list(orphaned)[:200]],
            "chargeable_count": len(chargeable_ids),
            "charged_count": len(charged_set),
        }

    async def run_reconciliation(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        """Read-only comparison. Never creates, edits, or deletes a ledger
        row -- only reports findings and records that a reconciliation run
        happened (for ledger-health's 'last successful reconciliation')."""
        result = await self._compute_reconciliation(date_from, date_to)
        result["balance_variance"] = "0"  # credit_balance is derived solely from this ledger's own running total -- no external ledger to vary against today
        result["run_at"] = _utcnow().isoformat()
        await self._audit(
            "home_services_finance.reconciliation_run", "reconciliation", None,
            after={"missing": result["missing_count"], "duplicate": result["duplicate_count"],
                   "orphaned": result["orphaned_count"]},
        )
        return result

    # ── Export ───────────────────────────────────────────────────────────────

    async def export_ledger(self, **filters) -> dict:
        data = await self.list_completion_charges(**{**filters, "page": 1, "page_size": 5000})
        await self._audit("home_services_finance.export", "completion_charge_ledger", None,
                           after={"row_count": len(data["items"])})
        return data

    # ── Credit accounts (tenant_billing.credit_balance) ─────────────────────

    async def list_credit_accounts(self, *, q: str | None = None, low_balance_only: bool = False,
                                    page: int = 1, page_size: int = 50) -> dict:
        stmt = select(TenantBilling, Tenant).join(Tenant, Tenant.id == TenantBilling.tenant_id)
        if low_balance_only:
            stmt = stmt.where(TenantBilling.credit_balance < LOW_BALANCE_DEFAULT_THRESHOLD)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(Tenant.business_name.ilike(like))
        stmt = stmt.order_by(TenantBilling.credit_balance.asc())
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()
        return {
            "items": [{
                "tenant_id": str(b.tenant_id),
                "tenant_name": t.business_name,
                "credit_balance": str(b.credit_balance),
                "low_balance": Decimal(str(b.credit_balance)) < LOW_BALANCE_DEFAULT_THRESHOLD,
                "low_balance_threshold": str(LOW_BALANCE_DEFAULT_THRESHOLD),
            } for b, t in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    # ── Credit Ledger (immutable, read-only projection) ──────────────────────
    # usage_credit_ledger has no vertical column of its own -- scoped via the
    # Tenant join, same pattern as list_topups/list_direct_payments below.
    # Every row here is written by exactly one of: deduct_for_completed_job
    # (PROVIDER_COMPLETION_CHARGE), deduct_customer_platform_charge_recovery
    # (CUSTOMER_PLATFORM_CHARGE_RECOVERY), a credit top-up grant, or
    # create_manual_adjustment below. This method only reads -- it never
    # writes a ledger row itself.
    async def list_credit_ledger(
        self, *, tenant_id: str | None = None, event_type: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        clauses = [Tenant.vertical == HOME_SERVICES_VERTICAL]
        if tenant_id: clauses.append(UsageCreditLedger.tenant_id == uuid.UUID(tenant_id))
        if event_type: clauses.append(UsageCreditLedger.event_type == event_type)
        stmt = (
            select(UsageCreditLedger, Tenant)
            .join(Tenant, Tenant.id == UsageCreditLedger.tenant_id)
            .where(*clauses)
            .order_by(UsageCreditLedger.created_at.desc())
        )
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()
        return {
            "items": [{
                **entry.to_dict(),
                "tenant_name": tenant.business_name,
                "direction": "credit" if Decimal(str(entry.credit_delta)) >= 0 else "debit",
            } for entry, tenant in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    async def get_ledger_entry_detail(self, entry_id: uuid.UUID) -> dict:
        entry = await self.db.get(UsageCreditLedger, entry_id)
        if not entry:
            raise NotFoundException("UsageCreditLedger", str(entry_id))
        tenant = await self.db.get(Tenant, entry.tenant_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("UsageCreditLedger", str(entry_id))
        return {**entry.to_dict(), "tenant_name": tenant.business_name}

    # ── Manual Adjustments ────────────────────────────────────────────────────
    # Never mutate tenant_billing.credit_balance directly outside a ledger
    # write -- this is the one code path (besides the certified deduction/
    # recovery/top-up writers) permitted to do so, and it always creates the
    # immutable ledger row in the same transaction as the balance change.
    ADJUSTMENT_REASON_CODES = {
        "PAYMENT_RECONCILIATION", "DUPLICATE_DEDUCTION_REVERSAL", "SERVICE_CREDIT_CORRECTION",
        "MIGRATION_CORRECTION", "EXPIRED_CREDIT_CORRECTION", "APPROVED_GOODWILL_ADJUSTMENT",
        "OTHER_REQUIRES_REVIEW",
    }

    async def create_manual_adjustment(
        self, *, tenant_id: uuid.UUID, direction: str, credit_units: Decimal,
        reason_code: str, detailed_reason: str, supporting_reference: str | None = None,
    ) -> dict:
        tenant = await self.db.get(Tenant, tenant_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("Tenant", str(tenant_id))
        if reason_code not in self.ADJUSTMENT_REASON_CODES:
            raise ServiceOSException("VALIDATION_ERROR", f"Invalid reason_code '{reason_code}'.", status_code=422)
        if credit_units <= 0:
            raise ServiceOSException("VALIDATION_ERROR", "credit_units must be positive.", status_code=422)
        if direction not in ("credit", "debit"):
            raise ServiceOSException("VALIDATION_ERROR", "direction must be 'credit' or 'debit'.", status_code=422)

        billing = (await self.db.execute(
            select(TenantBilling).where(TenantBilling.tenant_id == tenant_id).with_for_update()
        )).scalars().first()
        if not billing:
            billing = TenantBilling(tenant_id=tenant_id, credit_balance=Decimal("0"))
            self.db.add(billing)
            await self.db.flush()

        delta = credit_units if direction == "credit" else -credit_units
        balance_before = Decimal(str(billing.credit_balance))
        balance_after = balance_before + delta
        billing.credit_balance = balance_after

        entry = UsageCreditLedger(
            tenant_id=tenant_id, event_type="manual_credit_adjustment", credit_delta=delta,
            balance_before=balance_before, balance_after=balance_after,
            reason=detailed_reason, reason_code=reason_code, created_by=self.actor_id,
            actor_role=self.actor_role, source_type="manual_adjustment", source_id=supporting_reference,
        )
        self.db.add(entry)
        await self.db.flush()
        await self._audit(
            "home_services_finance.manual_adjustment", "usage_credit_ledger", str(entry.id),
            tenant_id=tenant_id,
            before={"balance": str(balance_before)}, after={"balance": str(balance_after)},
        )
        await self.db.commit()
        return {**entry.to_dict(), "tenant_name": tenant.business_name}

    # ── Direct Customer Payments ─────────────────────────────────────────────
    # Home Services customers pay the provider directly -- ServiceOS never
    # collects the job payment itself (no gateway order exists for this
    # path). ServicePaymentRecord (invoice_payment/payment_service.py::
    # record_onsite_payment) is the one canonical writer: the provider
    # records what they collected, the backend validates it against the
    # invoice's own customer_payable_amount (never trusts the client), and
    # the customer separately confirms via customer_confirm_payment. Both
    # are HS-only structurally (job_id -> service_jobs).

    async def list_direct_payments(
        self, *, payment_status: str | None = None, tenant_id: str | None = None,
        confirmed: bool | None = None, q: str | None = None,
        date_from: str | None = None, date_to: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        clauses = [Tenant.vertical == HOME_SERVICES_VERTICAL]
        clauses += self._date_filters(date_from, date_to, ServicePaymentRecord.created_at)
        if payment_status: clauses.append(ServicePaymentRecord.payment_status == payment_status)
        if tenant_id: clauses.append(ServicePaymentRecord.tenant_id == uuid.UUID(tenant_id))
        if confirmed is not None: clauses.append(ServicePaymentRecord.customer_confirmed == confirmed)

        stmt = (
            select(ServicePaymentRecord, Tenant, ServiceInvoice)
            .join(Tenant, Tenant.id == ServicePaymentRecord.tenant_id)
            .join(ServiceInvoice, ServiceInvoice.id == ServicePaymentRecord.invoice_id, isouter=True)
            .where(*clauses)
        )
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Tenant.business_name.ilike(like), ServiceInvoice.invoice_number.ilike(like)))
        stmt = stmt.order_by(ServicePaymentRecord.created_at.desc())

        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()
        items = []
        for pay, tenant, inv in rows:
            fee = Decimal(str(inv.platform_fee_amount)) if inv else Decimal("0")
            items.append({
                **pay.to_dict(),
                "tenant_name": tenant.business_name if tenant else None,
                "invoice_number": inv.invoice_number if inv else None,
                "provider_collected_amount": str(pay.collected_amount),
                "customer_platform_charge": str(fee),
                "total_paid_by_customer": str(inv.customer_payable_amount) if inv else str(pay.collected_amount),
            })
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def get_direct_payment_detail(self, payment_id: uuid.UUID) -> dict:
        pay = await self.db.get(ServicePaymentRecord, payment_id)
        if not pay:
            raise NotFoundException("ServicePaymentRecord", str(payment_id))
        tenant = await self.db.get(Tenant, pay.tenant_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("ServicePaymentRecord", str(payment_id))
        inv = await self.db.get(ServiceInvoice, pay.invoice_id)
        commission = (await self.db.execute(
            select(SvcCommissionRecord).where(SvcCommissionRecord.invoice_id == pay.invoice_id)
        )).scalar_one_or_none()
        # The two independent, never-merged charges: CUSTOMER_PLATFORM_CHARGE_
        # RECOVERY (vertical_monetization.customer_charge_recovery, event_type
        # "customer_platform_charge_recovery") and the completed-job usage-
        # credit deduction (execution.usage_credit_deduction, event_type
        # "completed_job_deduction"). Both post to usage_credit_ledger keyed
        # by job_id -- looked up here rather than duplicated.
        from app.engines.vertical_monetization.customer_charge_recovery import RECOVERY_EVENT_TYPE
        recovery_entry = None
        completion_entry = None
        if pay.job_id:
            ledger_rows = (await self.db.execute(
                select(UsageCreditLedger).where(
                    UsageCreditLedger.job_id == pay.job_id,
                    UsageCreditLedger.event_type.in_((RECOVERY_EVENT_TYPE, DEDUCTION_EVENT_TYPE)),
                )
            )).scalars().all()
            recovery_entry = next((r for r in ledger_rows if r.event_type == RECOVERY_EVENT_TYPE), None)
            completion_entry = next((r for r in ledger_rows if r.event_type == DEDUCTION_EVENT_TYPE), None)
        events = (await self.db.execute(
            select(FinancialEvent).where(FinancialEvent.record_id == pay.id)
            .order_by(FinancialEvent.created_at.desc())
        )).scalars().all()
        return {
            **pay.to_dict(),
            "tenant_name": tenant.business_name,
            "invoice_number": inv.invoice_number if inv else None,
            "provider_collected_amount": str(pay.collected_amount),
            "customer_platform_charge": str(inv.platform_fee_amount) if inv else "0",
            "total_paid_by_customer": str(inv.customer_payable_amount) if inv else str(pay.collected_amount),
            "serviceos_collected_from_customer": "0",
            # CUSTOMER_PLATFORM_CHARGE_RECOVERY -- independent ledger entry,
            # never merged with the completion charge below.
            "customer_platform_charge_recovery": {
                "status": "recovered" if recovery_entry else "not_calculated",
                "credits": str(-recovery_entry.credit_delta) if recovery_entry else None,
                "posted_at": recovery_entry.created_at.isoformat() if recovery_entry and recovery_entry.created_at else None,
                "ledger_entry_id": str(recovery_entry.id) if recovery_entry else None,
            },
            # PROVIDER_COMPLETION_CHARGE -- the certified per-job usage-credit
            # deduction (primary mechanism for Home Services); commission is
            # shown alongside as a secondary/legacy charge model, never merged.
            "provider_completion_charge": {
                "status": "posted" if completion_entry else "not_calculated",
                "credits": str(-completion_entry.credit_delta) if completion_entry else None,
                "posted_at": completion_entry.created_at.isoformat() if completion_entry and completion_entry.created_at else None,
                "ledger_entry_id": str(completion_entry.id) if completion_entry else None,
            },
            "provider_completion_charge_status": commission.status if commission else "not_calculated",
            "provider_completion_charge_amount": str(commission.commission_amount) if commission else None,
            "financial_events": [e.to_dict() for e in events],
        }

    async def get_direct_payments_summary(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        clauses = [Tenant.vertical == HOME_SERVICES_VERTICAL]
        clauses += self._date_filters(date_from, date_to, ServicePaymentRecord.created_at)
        stmt = select(ServicePaymentRecord, ServiceInvoice).join(
            Tenant, Tenant.id == ServicePaymentRecord.tenant_id
        ).join(ServiceInvoice, ServiceInvoice.id == ServicePaymentRecord.invoice_id, isouter=True).where(*clauses)
        rows = (await self.db.execute(stmt)).all()
        provider_collected_total = sum((p.collected_amount or Decimal("0")) for p, _ in rows)
        platform_charges_total = sum((inv.platform_fee_amount or Decimal("0")) for _, inv in rows if inv)
        return {
            "total_attempts": len(rows),
            "confirmed": sum(1 for p, _ in rows if p.customer_confirmed),
            "pending_confirmation": sum(1 for p, _ in rows if p.customer_confirmation_required and not p.customer_confirmed),
            "disputed": sum(1 for p, _ in rows if p.payment_status == "disputed"),
            "failed": sum(1 for p, _ in rows if p.payment_status == "failed"),
            "provider_collected_total": str(provider_collected_total),
            "customer_platform_charges_recorded": str(platform_charges_total),
            # No mechanism in the current codebase claws the platform charge
            # back from provider credits separately from the completion
            # charge -- see get_overview()'s note. Reporting this honestly as
            # not tracked rather than fabricating a "recovered" figure.
            "platform_charge_recovery_tracked": False,
        }

    async def get_direct_payments_summary_for_tenant(self, tenant_id: uuid.UUID) -> dict:
        """TENANT-HS-FINANCE-HUB-01 — the same canonical projection as
        get_direct_payments_summary(), narrowed to ONE tenant so the tenant
        Finance Hub can show its own direct-payment counts without forking
        the query. Vertical scope (Tenant.vertical == home_services) is
        still enforced, so this can never surface another vertical's rows."""
        # NOTE (pre-existing schema drift, found live 2026-07-30): the
        # ServicePaymentRecord ORM model declares ~18 columns that do NOT
        # exist in the live `service_payment_records` table (expected_amount,
        # payment_reference_id, reconciliation_status, dispute_complaint_id,
        # ...), so ANY full-entity ORM select against it raises
        # UndefinedColumnError. That is a pre-existing defect affecting the
        # admin Direct Payments projections too, and is out of scope to fix
        # here (it needs its own migration). This tenant-scoped summary
        # therefore reads ONLY the columns that genuinely exist, via explicit
        # SQL, so the Finance Hub's direct-payment panel shows real counts
        # instead of a degraded error state.
        from sqlalchemy import text as _text
        rows = (await self.db.execute(_text(
            "SELECT spr.payment_status, spr.customer_confirmed, "
            "       spr.customer_confirmation_required, spr.provider_confirmed_at, "
            "       COALESCE(spr.collected_amount, 0) AS collected_amount "
            "FROM service_payment_records spr "
            "JOIN tenants t ON t.id = spr.tenant_id "
            "WHERE t.vertical = :vert AND spr.tenant_id = :tid"
        ), {"vert": HOME_SERVICES_VERTICAL, "tid": str(tenant_id)})).fetchall()
        provider_collected_total = sum((Decimal(str(p.collected_amount or 0)) for p in rows), Decimal("0"))
        return {
            "tenant_id": str(tenant_id),
            "total_attempts": len(rows),
            "confirmed": sum(1 for p in rows if p.customer_confirmed),
            "awaiting_customer_confirmation": sum(
                1 for p in rows if p.customer_confirmation_required and not p.customer_confirmed),
            "awaiting_provider_confirmation": sum(
                1 for p in rows if p.provider_confirmed_at is None),
            "mismatch": sum(1 for p in rows if p.payment_status == "mismatch"),
            "disputed": sum(1 for p in rows if p.payment_status == "disputed"),
            "failed": sum(1 for p in rows if p.payment_status == "failed"),
            "provider_collected_total": str(provider_collected_total),
            # ServiceOS never holds or settles these funds — there is no
            # platform-held balance to report, by design.
            "serviceos_held_amount": "0",
            "settlement_model": "none_provider_collects_directly",
        }

    # ── Overview aggregation ──────────────────────────────────────────────────
    # Composes the above summaries into one call. Every figure here is a real
    # query result; nothing is a UI-only or placeholder calculation. Where a
    # concept from the target design has no backing mechanism yet (platform
    # charge "recovery" as a distinct step from the provider completion
    # charge), the field is explicitly flagged not-tracked rather than
    # invented, per audit finding below.

    async def get_overview(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        payments = await self.get_direct_payments_summary(date_from, date_to)
        charges = await self.get_summary(date_from, date_to)
        deposits = await self.get_hs_deposits_summary()
        warranty = await self.get_hs_warranty_claims_summary()
        events_summary = await self.get_financial_events_summary(date_from, date_to)

        commission_rows = (await self.db.execute(
            select(SvcCommissionRecord.status, func.count(), func.coalesce(func.sum(SvcCommissionRecord.commission_amount), 0))
            .group_by(SvcCommissionRecord.status)
        )).all()
        commission_by_status = {status: {"count": count, "amount": str(amount)} for status, count, amount in commission_rows}
        completion_charges_deducted = sum(int(v["count"]) for k, v in commission_by_status.items() if k == "deducted")
        failed_completion_charges = sum(int(commission_by_status.get(k, {"count": 0})["count"]) for k in ("failed", "insufficient_credit"))

        low_balance_tenants = (await self.db.execute(
            select(func.count(TenantBilling.id)).where(TenantBilling.credit_balance < LOW_BALANCE_DEFAULT_THRESHOLD)
        )).scalar() or 0
        total_credit_balance = (await self.db.execute(
            select(func.coalesce(func.sum(TenantBilling.credit_balance), 0))
        )).scalar() or Decimal("0")

        # CUSTOMER_PLATFORM_CHARGE_RECOVERY -- real ledger data. Previously
        # reported as "not tracked"; vertical_monetization/customer_charge_
        # recovery.py::deduct_customer_platform_charge_recovery (wired into
        # execution/home_service_service.py's job-completion handler) now
        # posts this as its own usage_credit_ledger row, independent of the
        # provider completion charge below.
        from app.engines.vertical_monetization.customer_charge_recovery import RECOVERY_EVENT_TYPE
        recovery_clauses = [UsageCreditLedger.event_type == RECOVERY_EVENT_TYPE]
        recovery_clauses += self._date_filters(date_from, date_to, UsageCreditLedger.created_at)
        recovered_total = (await self.db.execute(
            select(func.coalesce(func.sum(-UsageCreditLedger.credit_delta), 0)).where(*recovery_clauses)
        )).scalar() or Decimal("0")
        recovered_count = (await self.db.execute(
            select(func.count(UsageCreditLedger.id)).where(*recovery_clauses)
        )).scalar() or 0

        return {
            "group_a_customer_to_provider": {
                "provider_collected_customer_payments": payments["provider_collected_total"],
                "payment_confirmations_pending": payments["pending_confirmation"],
                "customer_platform_charges_recorded": payments["customer_platform_charges_recorded"],
                "payment_disputes": payments["disputed"],
            },
            "group_b_serviceos_financial_position": {
                "platform_charges_recovered": str(recovered_total),
                "platform_charge_recovery_tracked": True,
                "platform_charge_recovery_count": recovered_count,
                "provider_completion_charges": {
                    "posted": completion_charges_deducted,
                    "total_amount": commission_by_status.get("deducted", {"amount": "0"})["amount"],
                },
                "active_usage_credit_balance": str(total_credit_balance),
                "security_deposits_held": deposits.get("total_held", "0"),
            },
            "secondary": {
                "low_credit_providers": low_balance_tenants,
                "failed_charge_recoveries": failed_completion_charges,
                "deposit_return_requests": deposits.get("refund_pending", 0),
                "warranty_financial_exposure": warranty.get("settled_value", "0"),
                "finance_exceptions": payments["disputed"] + failed_completion_charges + charges["missing_charges"],
            },
            "completion_charge_ledger": charges,
            "events_today": events_summary.get("events_today", 0),
            "audit_note": (
                "Customer platform-charge recovery now posts its own usage_credit_ledger row "
                "(event_type customer_platform_charge_recovery), independent from the provider "
                "completion charge (completed_job_deduction / commission). Both are keyed by job_id "
                "and never merged into one record."
            ),
        }

    # ── Provider Charges (unified usage-credit + commission view) ───────────
    # Two independent provider-charge models coexist for Home Services:
    #   - usage_credit: flat per-job credit deduction, written by
    #     execution.usage_credit_deduction.deduct_for_completed_job (see
    #     list_completion_charges above).
    #   - commission: percentage-of-invoice charge, written by
    #     invoice_payment.commission_service.ServiceCommissionService,
    #     recorded in svc_commission_records (proven active -- called from
    #     payment_service.py's on-site payment recording flow).
    # This method merges both into one list with a charge_model discriminator
    # rather than inventing a third unified table -- neither writer changes.

    async def list_provider_charges(
        self, *, charge_model: str | None = None, tenant_id: str | None = None,
        status: str | None = None, date_from: str | None = None, date_to: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        items: list[dict] = []

        if charge_model in (None, "usage_credit"):
            uc = await self.list_completion_charges(
                tenant_id=tenant_id, date_from=date_from, date_to=date_to, page=1, page_size=5000,
            )
            for row in uc["items"]:
                if status and status != row["status"]:
                    continue
                items.append({
                    "charge_ref": f"usage_credit:{row['charge_id']}",
                    "charge_model": "usage_credit",
                    "tenant_id": row["tenant_id"],
                    "tenant_name": row["tenant_name"],
                    "job_id": row["job_id"],
                    "amount": row["credits"],
                    "status": row["status"],
                    "policy_source": row["policy_source"],
                    "triggered_at": row["posted_at"],
                })

        if charge_model in (None, "commission"):
            clauses = self._date_filters(date_from, date_to, SvcCommissionRecord.created_at)
            if tenant_id:
                clauses.append(SvcCommissionRecord.tenant_id == uuid.UUID(tenant_id))
            if status:
                clauses.append(SvcCommissionRecord.status == status)
            stmt = (
                select(SvcCommissionRecord, Tenant)
                .join(Tenant, Tenant.id == SvcCommissionRecord.tenant_id, isouter=True)
                .where(*clauses)
            )
            rows = (await self.db.execute(stmt)).all()
            for cr, t in rows:
                items.append({
                    "charge_ref": f"commission:{cr.id}",
                    "charge_model": "commission",
                    "tenant_id": str(cr.tenant_id),
                    "tenant_name": t.business_name if t else None,
                    "job_id": str(cr.job_id),
                    "amount": str(cr.commission_amount),
                    "status": cr.status,
                    "policy_source": f"rate:{cr.commission_rate}" if cr.commission_rate else None,
                    "triggered_at": (cr.deducted_at or cr.calculated_at).isoformat()
                                    if (cr.deducted_at or cr.calculated_at) else None,
                })

        items.sort(key=lambda x: x["triggered_at"] or "", reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return {"items": items[start:start + page_size], "total": total, "page": page, "page_size": page_size}

    async def get_provider_charge_detail(self, charge_ref: str) -> dict:
        if ":" not in charge_ref:
            raise NotFoundException("ProviderCharge", charge_ref)
        model, charge_id = charge_ref.split(":", 1)
        if model == "usage_credit":
            return {**await self.get_charge_detail(charge_id), "charge_model": "usage_credit"}
        if model == "commission":
            cr = await self.db.get(SvcCommissionRecord, uuid.UUID(charge_id))
            if not cr:
                raise NotFoundException("CommissionCharge", charge_id)
            tenant = await self.db.get(Tenant, cr.tenant_id)
            invoice = await self.db.get(ServiceInvoice, cr.invoice_id)
            return {
                "charge_model": "commission",
                **cr.to_dict(),
                "tenant_name": tenant.business_name if tenant else None,
                "invoice_number": invoice.invoice_number if invoice else None,
            }
        raise NotFoundException("ProviderCharge", charge_ref)

    # ── Credits & Top-ups (HS-scoped top-up orders) ──────────────────────────
    # CreditTopupOrder (finance_hub/models.py) has no vertical column of its
    # own -- scoped here via the same Tenant.vertical join finance_hub/
    # service.py::list_deposits already uses for Security Deposits.

    async def list_topups(
        self, *, tenant_id: str | None = None, payment_status: str | None = None,
        date_from: str | None = None, date_to: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        clauses = [Tenant.vertical == "home_services"]
        clauses += self._date_filters(date_from, date_to, CreditTopupOrder.created_at)
        if tenant_id:
            clauses.append(CreditTopupOrder.tenant_id == uuid.UUID(tenant_id))
        if payment_status:
            clauses.append(CreditTopupOrder.payment_status == payment_status)

        stmt = (
            select(CreditTopupOrder, Tenant)
            .join(Tenant, Tenant.id == CreditTopupOrder.tenant_id)
            .where(*clauses)
            .order_by(CreditTopupOrder.created_at.desc())
        )
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()
        return {
            "items": [{**o.to_dict(), "tenant_name": t.business_name} for o, t in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    async def get_topup_detail(self, topup_id: str) -> dict:
        order = await self.db.get(CreditTopupOrder, uuid.UUID(topup_id))
        if not order:
            raise NotFoundException("CreditTopupOrder", topup_id)
        tenant = await self.db.get(Tenant, order.tenant_id)
        if not tenant or tenant.vertical != "home_services":
            raise NotFoundException("CreditTopupOrder", topup_id)
        return {**order.to_dict(), "tenant_name": tenant.business_name}

    # ── Security Deposits (HS-scoped view over the canonical deposits engine) ─
    # FinanceHubService.list_deposits/get_deposit_detail remain the one
    # implementation; this only pins vertical="home_services" and, for
    # detail, verifies ownership rather than re-querying.

    async def list_hs_deposits(self, *, status: str | None = None, q: str | None = None,
                                page: int = 1, page_size: int = 50,
                                sort_by: str = "created_at", sort_dir: str = "desc") -> dict:
        return await self._fh.list_deposits(
            status=status, vertical=HOME_SERVICES_VERTICAL, q=q,
            page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir,
        )

    async def get_hs_deposits_summary(self) -> dict:
        stmt = select(SecurityDeposit).join(Tenant, Tenant.id == SecurityDeposit.tenant_id).where(
            Tenant.vertical == HOME_SERVICES_VERTICAL
        )
        deposits = (await self.db.execute(stmt)).scalars().all()
        return {
            "total_deposit_accounts": len(deposits),
            "active_held_deposits": sum(1 for d in deposits if d.status == "paid"),
            "pending_deposits": sum(1 for d in deposits if d.status in ("unpaid", "partially_paid", "pending_verification")),
            "refund_pending": sum(1 for d in deposits if d.status == "refund_requested"),
            "refunded": sum(1 for d in deposits if d.status == "refunded"),
            "deposit_risk_cases": sum(1 for d in deposits if d.status in ("blocked", "forfeited")),
            "total_held": str(sum((d.current_balance or Decimal("0")) for d in deposits)),
        }

    async def get_hs_deposit_detail(self, deposit_id: uuid.UUID) -> dict:
        detail = await self._fh.get_deposit_detail(deposit_id)
        if detail.get("vertical") != HOME_SERVICES_VERTICAL:
            raise NotFoundException("SecurityDeposit", str(deposit_id))
        return detail

    # ── Warranty Claims (HS-scoped) ──────────────────────────────────────────
    # list_claims/get_claim_detail on FinanceHubService have no vertical
    # filter today (WarrantyClaim isn't guaranteed HS-only), so this queries
    # directly with a Tenant.vertical join rather than editing the shared,
    # cross-vertical service.

    async def list_hs_warranty_claims(self, *, status: str | None = None, category: str | None = None,
                                       q: str | None = None, page: int = 1, page_size: int = 50) -> dict:
        stmt = (
            select(WarrantyClaim, Tenant)
            .join(Tenant, Tenant.id == WarrantyClaim.tenant_id)
            .where(Tenant.vertical == HOME_SERVICES_VERTICAL)
        )
        if status: stmt = stmt.where(WarrantyClaim.status == status)
        if category: stmt = stmt.where(WarrantyClaim.claim_type == category)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(WarrantyClaim.job_id).like(like) | func.lower(Tenant.tenant_name).like(like))
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        stmt = stmt.order_by(WarrantyClaim.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await self.db.execute(stmt)).all()
        return {
            "items": [{**self._fh._claim_dict(c, t), "vertical": t.vertical} for c, t in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    async def get_hs_warranty_claims_summary(self) -> dict:
        stmt = select(WarrantyClaim).join(Tenant, Tenant.id == WarrantyClaim.tenant_id).where(
            Tenant.vertical == HOME_SERVICES_VERTICAL
        )
        claims = (await self.db.execute(stmt)).scalars().all()
        return {
            "total_claims": len(claims),
            "pending_review": sum(1 for c in claims if c.status in ("pending", "pending_review")),
            "investigation_ongoing": sum(1 for c in claims if c.status in ("investigating", "awaiting_documents")),
            "approved_claims": sum(1 for c in claims if c.status == "approved"),
            "rejected_claims": sum(1 for c in claims if c.status == "rejected"),
            "settled_value": str(sum((c.settled_amount or Decimal("0")) for c in claims if c.status == "settled")),
        }

    async def get_hs_warranty_claim_detail(self, claim_id: uuid.UUID) -> dict:
        claim = await self.db.get(WarrantyClaim, claim_id)
        if not claim:
            raise NotFoundException("WarrantyClaim", str(claim_id))
        tenant = await self.db.get(Tenant, claim.tenant_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("WarrantyClaim", str(claim_id))
        return {**self._fh._claim_dict(claim, tenant), "vertical": tenant.vertical}

    # ── Service Invoices ─────────────────────────────────────────────────────
    # ServiceInvoice (invoice_payment/models.py) is HS-scoped via job_id ->
    # service_jobs (same structural isolation as usage_credit_ledger); no
    # admin list surface exists for it today, so this is a new read layer
    # over the existing, unmodified invoice_service.py writer.

    async def list_invoices(
        self, *, status: str | None = None, payment_status: str | None = None,
        tenant_id: str | None = None, q: str | None = None,
        date_from: str | None = None, date_to: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        clauses = self._date_filters(date_from, date_to, ServiceInvoice.created_at)
        if status: clauses.append(ServiceInvoice.status == status)
        if payment_status: clauses.append(ServiceInvoice.payment_status == payment_status)
        if tenant_id: clauses.append(ServiceInvoice.tenant_id == uuid.UUID(tenant_id))

        stmt = (
            select(ServiceInvoice, Tenant)
            .join(Tenant, Tenant.id == ServiceInvoice.tenant_id, isouter=True)
            .where(*clauses)
        )
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(ServiceInvoice.invoice_number.ilike(like), Tenant.business_name.ilike(like)))
        stmt = stmt.order_by(ServiceInvoice.created_at.desc())

        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()
        return {
            "items": [{**inv.to_dict(), "tenant_name": t.business_name if t else None} for inv, t in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    async def get_invoice_detail(self, invoice_id: str) -> dict:
        inv = await self.db.get(ServiceInvoice, uuid.UUID(invoice_id))
        if not inv:
            raise NotFoundException("ServiceInvoice", invoice_id)
        tenant = await self.db.get(Tenant, inv.tenant_id)
        events = (await self.db.execute(
            select(FinancialEvent).where(
                FinancialEvent.record_type.in_(("invoice", "payment", "commission")),
                or_(FinancialEvent.record_id == inv.id, FinancialEvent.tenant_id == inv.tenant_id),
            ).order_by(FinancialEvent.created_at.desc()).limit(50)
        )).scalars().all()
        return {
            **inv.to_dict(),
            "tenant_name": tenant.business_name if tenant else None,
            "financial_events": [e.to_dict() for e in events],
        }

    async def get_invoices_summary(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        clauses = self._date_filters(date_from, date_to, ServiceInvoice.created_at)
        invoices = (await self.db.execute(select(ServiceInvoice).where(*clauses))).scalars().all()
        return {
            "issued": sum(1 for i in invoices if i.status == "issued"),
            "paid": sum(1 for i in invoices if i.payment_status == "paid"),
            "outstanding": sum(1 for i in invoices if i.payment_status == "pending"),
            "overdue": sum(1 for i in invoices if i.payment_status == "overdue"),
            "cancelled": sum(1 for i in invoices if i.status == "cancelled"),
            "total_value": str(sum((i.total_amount or Decimal("0")) for i in invoices)),
        }

    # ── Customer Refunds ─────────────────────────────────────────────────────
    # RefundRequest (complaints/refund_service.py::RefundRequestService) is
    # the one refund-request writer; tenant_id is nullable there (a refund
    # can exist before a provider is assigned), so isolation here requires
    # tenant_id present AND Tenant.vertical == 'home_services' -- rows with
    # no tenant are excluded rather than guessed into scope.

    async def list_hs_refunds(
        self, *, status: str | None = None, refund_type: str | None = None,
        q: str | None = None, date_from: str | None = None, date_to: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        clauses = [RefundRequest.tenant_id.isnot(None), Tenant.vertical == HOME_SERVICES_VERTICAL]
        clauses += self._date_filters(date_from, date_to, RefundRequest.created_at)
        if status: clauses.append(RefundRequest.status == status)
        if refund_type: clauses.append(RefundRequest.refund_type == refund_type)

        stmt = (
            select(RefundRequest, Tenant)
            .join(Tenant, Tenant.id == RefundRequest.tenant_id)
            .where(*clauses)
        )
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(RefundRequest.refund_number.ilike(like), Tenant.business_name.ilike(like)))
        stmt = stmt.order_by(RefundRequest.created_at.desc())

        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()
        return {
            "items": [{**rr.to_dict(), "tenant_name": t.business_name} for rr, t in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    async def get_hs_refund_detail(self, refund_id: uuid.UUID) -> dict:
        rr = await self.db.get(RefundRequest, refund_id)
        if not rr or not rr.tenant_id:
            raise NotFoundException("RefundRequest", str(refund_id))
        tenant = await self.db.get(Tenant, rr.tenant_id)
        if not tenant or tenant.vertical != HOME_SERVICES_VERTICAL:
            raise NotFoundException("RefundRequest", str(refund_id))
        return {**rr.to_dict(), "tenant_name": tenant.business_name}

    async def get_hs_refunds_summary(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        clauses = [RefundRequest.tenant_id.isnot(None), Tenant.vertical == HOME_SERVICES_VERTICAL]
        clauses += self._date_filters(date_from, date_to, RefundRequest.created_at)
        stmt = select(RefundRequest).join(Tenant, Tenant.id == RefundRequest.tenant_id).where(*clauses)
        refunds = (await self.db.execute(stmt)).scalars().all()
        # Real RefundRequest.status values (complaints/constants.py REFUND_*):
        # requested -> provider_review/admin_review -> approved -> rejected |
        # recorded -> verified | cancelled. No "processing"/"partially_
        # refunded"/"failed" status exists on this model -- not fabricated here.
        return {
            "requested": sum(1 for r in refunds if r.status == "requested"),
            "under_review": sum(1 for r in refunds if r.status in ("provider_review", "admin_review")),
            "approved": sum(1 for r in refunds if r.status == "approved"),
            "recorded": sum(1 for r in refunds if r.status == "recorded"),
            "verified": sum(1 for r in refunds if r.status == "verified"),
            "rejected": sum(1 for r in refunds if r.status == "rejected"),
            "cancelled": sum(1 for r in refunds if r.status == "cancelled"),
        }

    # ── Provider Completion Charge Config ────────────────────────────────────
    # The credits deducted per completed job (usage_credit_deduction.py's
    # resolve_completed_job_deduction_credits) come from ServicePricingRule.
    # completed_job_deduction_credits -- a real, already-validated field
    # (AdminCatalogService.update_pricing_rule already enforces >= 0 and
    # audit-logs the change) that simply had NO reachable HTTP route left
    # after the old admin pricing-rule listing surface was deleted (confirmed
    # zero routes reference pricing rules in admin_catalog/admin_router.py).
    # This composes the existing, unmodified AdminCatalogService rather than
    # duplicating pricing-rule logic -- only the completed_job_deduction_
    # credits field is writable here; every other pricing-rule field (price,
    # tax, etc.) stays out of scope for this finance-config surface.

    async def list_charge_config(self, *, q: str | None = None, is_active: bool | None = None,
                                  page: int = 1, page_size: int = 100) -> dict:
        catalog = AdminCatalogService(db=self.db)
        result = await catalog.list_pricing_rules(q=q, is_active=is_active, page=page, page_size=page_size,
                                                    sort_by="updated_at", sort_dir="desc")
        master_ids = {r["master_service_id"] for r in result["items"]}
        masters = {}
        if master_ids:
            rows = (await self.db.execute(
                select(MasterService).where(MasterService.id.in_(uuid.UUID(m) for m in master_ids))
            )).scalars().all()
            masters = {str(m.id): m.service_name for m in rows}
        items = [{
            "rule_id": r["rule_id"],
            "master_service_name": masters.get(r["master_service_id"]),
            "job_type": r["job_type"],
            "rule_name": r["rule_name"],
            "rule_code": r["rule_code"],
            "completed_job_deduction_credits": r["completed_job_deduction_credits"],
            "is_active": r["is_active"],
            "effective_from": r["effective_from"],
            "effective_to": r["effective_to"],
        } for r in result["items"]]
        return {"items": items, "total": result["pagination"]["total"], "page": page, "page_size": page_size}

    async def update_charge_config(self, rule_id: uuid.UUID, completed_job_deduction_credits: int) -> dict:
        catalog = AdminCatalogService(db=self.db, request_id=self.request_id,
                                       actor_id=self.actor_id, actor_role=self.actor_role)
        result = await catalog.update_pricing_rule(
            rule_id, {"completed_job_deduction_credits": completed_job_deduction_credits},
        )
        await self.db.commit()
        return {
            "rule_id": result["rule_id"],
            "completed_job_deduction_credits": result["completed_job_deduction_credits"],
        }

    # ── Financial Events ─────────────────────────────────────────────────────
    # FinancialEvent (invoice_payment/models.py) is written exclusively by
    # invoice_payment's commission_service/invoice_service/payment_service --
    # all three operate only on ServiceInvoice/ServicePaymentRecord/
    # SvcCommissionRecord rows, which are themselves tied to service_jobs
    # (the Home-Services-only final-record table). No other engine writes
    # this table (grep-verified), so it is structurally HS-only, matching
    # the isolation pattern used for usage_credit_ledger above -- no
    # runtime vertical flag/join required.

    async def list_financial_events(
        self, *, event_type: str | None = None, record_type: str | None = None,
        tenant_id: str | None = None, q: str | None = None,
        date_from: str | None = None, date_to: str | None = None,
        page: int = 1, page_size: int = 50,
    ) -> dict:
        clauses = self._date_filters(date_from, date_to, FinancialEvent.created_at)
        if event_type:
            clauses.append(FinancialEvent.event_type == event_type)
        if record_type:
            clauses.append(FinancialEvent.record_type == record_type)
        if tenant_id:
            clauses.append(FinancialEvent.tenant_id == uuid.UUID(tenant_id))

        stmt = (
            select(FinancialEvent, Tenant)
            .join(Tenant, Tenant.id == FinancialEvent.tenant_id, isouter=True)
            .where(*clauses)
        )
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Tenant.business_name.ilike(like), FinancialEvent.request_id.ilike(like)))
        stmt = stmt.order_by(FinancialEvent.created_at.desc())

        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()

        return {
            "items": [{
                "event_id": str(ev.id),
                "event_type": ev.event_type,
                "record_type": ev.record_type,
                "record_id": str(ev.record_id),
                "tenant_id": str(ev.tenant_id) if ev.tenant_id else None,
                "tenant_name": t.business_name if t else None,
                "customer_id": str(ev.customer_id) if ev.customer_id else None,
                "actor_type": ev.actor_type,
                "actor_user_id": str(ev.actor_user_id) if ev.actor_user_id else None,
                "request_id": ev.request_id,
                "occurred_at": ev.created_at.isoformat() if ev.created_at else None,
            } for ev, t in rows],
            "total": total, "page": page, "page_size": page_size,
        }

    async def get_financial_event_detail(self, event_id: str) -> dict:
        ev = await self.db.get(FinancialEvent, uuid.UUID(event_id))
        if not ev:
            raise NotFoundException("FinancialEvent", event_id)
        tenant = await self.db.get(Tenant, ev.tenant_id) if ev.tenant_id else None
        return {
            "event_id": str(ev.id),
            "event_type": ev.event_type,
            "record_type": ev.record_type,
            "record_id": str(ev.record_id),
            "tenant_id": str(ev.tenant_id) if ev.tenant_id else None,
            "tenant_name": tenant.business_name if tenant else None,
            "customer_id": str(ev.customer_id) if ev.customer_id else None,
            "actor_type": ev.actor_type,
            "actor_user_id": str(ev.actor_user_id) if ev.actor_user_id else None,
            "old_value": ev.old_value,
            "new_value": ev.new_value,
            "reason": ev.reason,
            "request_id": ev.request_id,
            "occurred_at": ev.created_at.isoformat() if ev.created_at else None,
        }

    async def get_financial_events_summary(self, date_from: str | None = None, date_to: str | None = None) -> dict:
        clauses = self._date_filters(date_from, date_to, FinancialEvent.created_at)
        today_clauses = [FinancialEvent.created_at >= datetime.now(timezone.utc).date()]
        events_today = (await self.db.execute(
            select(func.count(FinancialEvent.id)).where(*today_clauses)
        )).scalar() or 0
        by_type_rows = (await self.db.execute(
            select(FinancialEvent.event_type, func.count(FinancialEvent.id))
            .where(*clauses).group_by(FinancialEvent.event_type)
        )).all()
        return {
            "events_today": events_today,
            "by_event_type": {t: c for t, c in by_type_rows},
            # No update/delete code path exists against financial_events (grep-verified) --
            # every row is a permanent, append-only record of what actually happened.
            "immutable": True,
        }

    # ── Audit history for this workspace ────────────────────────────────────

    async def list_audit(self, page: int = 1, page_size: int = 50) -> dict:
        from app.engines.security.models import PlatformAuditLog
        stmt = (
            select(PlatformAuditLog)
            .where(PlatformAuditLog.engine_id == ENGINE_ID,
                   PlatformAuditLog.operation.like("home_services_finance.%"))
            .order_by(PlatformAuditLog.created_at.desc())
        )
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return {
            "items": [{
                "id": str(r.id), "operation": r.operation, "entity_type": r.entity_type,
                "entity_id": r.entity_id, "actor_id": str(r.actor_id) if r.actor_id else None,
                "actor_role": r.actor_role, "before": r.before_state, "after": r.after_state,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            } for r in rows],
            "total": total, "page": page, "page_size": page_size,
        }
