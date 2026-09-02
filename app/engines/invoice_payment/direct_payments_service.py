"""TENANT-HS-DIRECT-PAYMENTS-01 — Home Services Direct Payments.

A job-linked payment CONFIRMATION and RECONCILIATION workflow. The customer
pays the provider business DIRECTLY (cash / UPI / card on the provider's own
terminal / bank transfer). ServiceOS:

  * does NOT collect, hold, settle or transfer this money,
  * creates NO provider payout and NO settlement record,
  * posts NOTHING to the usage-credit wallet or the security-deposit ledger
    from this flow,
  * never treats the amount as platform revenue.

It records two independent facts -- the provider's DECLARATION and the
customer's CONFIRMATION -- plus a derived reconciliation status, and links a
disagreement to the canonical Complaints & Resolution Center.

Canonical systems reused (nothing parallel is built here):
  * ServicePaymentRecord / ServiceInvoice / FinancialEvent
    (app.engines.invoice_payment.models) -- the one payment-record table.
  * ServiceJob / ServiceBooking (app.engines.final_records.models) and the
    booking's immutable price_snapshot.
  * ServiceJobQuote (app.engines.quote_checklist.models) -- the approved
    Repair estimate, with its is_current/version_number lineage.
  * ServiceJobWorkflow.requires_direct_payment_record
    (app.engines.admin_catalog.models) -- the Job-Type gate for whether this
    stage exists at all.
  * CustomerComplaint via ComplaintService (app.engines.complaints) -- the
    only dispute system.
  * NotificationService.fire_event (app.engines.platform_notifications) --
    the only notification path.
  * CustomerOperationalAccessPolicy.customer_alias -- the only customer
    identity exposed to the tenant here.
  * MediaAsset (app.engines.media, media_context "payment_proof") -- evidence
    storage; no public URL is ever produced by this module.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.invoice_payment.direct_payments_constants import (
    AMOUNT_TOLERANCE, CA_CLARIFICATION, CA_CONFIRM, CUSTOMER_ACTIONS,
    CUSTOMER_NONRESPONSE_ESCALATION_DAYS, DIRECT_PAYMENT_METHODS, EVIDENCE_TYPES,
    ERR_DP_ACCESS_DENIED, ERR_DP_ALREADY_CONFIRMED, ERR_DP_ALREADY_DECLARED,
    ERR_DP_DISPUTE_EXISTS, ERR_DP_EXPECTED_UNRESOLVED, ERR_DP_INVALID_ACTION,
    ERR_DP_INVALID_AMOUNT, ERR_DP_INVALID_EVIDENCE_TYPE, ERR_DP_INVALID_METHOD,
    ERR_DP_JOB_NOT_FOUND, ERR_DP_LOCKED_AFTER_CONFIRM, ERR_DP_LOCKED_BY_DISPUTE,
    ERR_DP_NO_APPROVED_ESTIMATE, ERR_DP_NOT_FOUND, ERR_DP_REASON_REQUIRED,
    ERR_DP_REMINDER_RATE_LIMITED, ERR_DP_STALE_VERSION, ERR_DP_WORK_NOT_DONE,
    EVT_DP_CONFIRMATION_REQUESTED, EVT_DP_CONFIRMED_BY_CUSTOMER,
    EVT_DP_MISMATCH_REPORTED,
    FEV_DP_CONFIRMED, FEV_DP_CORRECTED, FEV_DP_DECLARED, FEV_DP_DISPUTE_OPENED,
    FEV_DP_MISMATCH, FEV_DP_REMINDER_SENT,
    METHOD_LABELS, MISMATCH_ACTIONS, POLICY_BULLETS,
    REMINDER_MAX_PER_RECORD, REMINDER_MIN_INTERVAL_HOURS,
    RS_AWAITING_CUSTOMER, RS_AWAITING_PROVIDER, RS_CONFIRMED, RS_DISPUTED,
    RS_MISMATCHED, RS_NOT_REQUIRED, STATUS_LABELS, WORK_DONE_JOB_STATUSES,
    WORKFLOW_STEPS,
)
from app.engines.quote_checklist.constants import QS_CUSTOMER_APPROVED
from app.engines.invoice_payment.models import (
    FinancialEvent, ServiceInvoice, ServicePaymentRecord,
)
from app.exceptions import ServiceOSException

_TOL = Decimal(AMOUNT_TOLERANCE)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _d(v) -> Decimal:
    return Decimal(str(v or 0))


def _iso(v):
    return v.isoformat() if v else None


def _parse_dt(v):
    """Accept an ISO date or datetime string (including a trailing 'Z', which
    datetime.fromisoformat rejects on older Pythons and which asyncpg cannot
    bind to a timestamptz column as a bare string) and return a real
    timezone-aware datetime. Returns None on anything unparseable rather than
    silently widening the filter to 'everything'."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            dt = datetime.fromisoformat(s[:10])
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _err(code: str, detail: str, status_code: int = 422, **kw) -> ServiceOSException:
    return ServiceOSException(error_code=code, detail=detail, status_code=status_code, **kw)


class DirectPaymentsService:
    """All methods are tenant-scoped by construction -- tenant_id comes from
    the caller's JWT (UserContext.tenant_id), never from a request body."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, request_id: str = "—") -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.request_id = request_id

    # ── Loaders ─────────────────────────────────────────────────────────────

    async def _job(self, job_id: uuid.UUID):
        from app.engines.final_records.models import ServiceJob
        row = (await self.db.execute(
            select(ServiceJob).where(
                ServiceJob.id == job_id, ServiceJob.tenant_id == self.tenant_id,
            )
        )).scalars().first()
        return row

    async def _booking(self, booking_id):
        if not booking_id:
            return None
        from app.engines.final_records.models import ServiceBooking
        return (await self.db.execute(
            select(ServiceBooking).where(ServiceBooking.id == booking_id)
        )).scalars().first()

    async def _invoice_for_job(self, job_id):
        return (await self.db.execute(
            select(ServiceInvoice)
            .where(ServiceInvoice.job_id == job_id,
                   ServiceInvoice.tenant_id == self.tenant_id)
            .order_by(ServiceInvoice.created_at.desc())
        )).scalars().first()

    async def _current_quote(self, job_id):
        """The CURRENT quote for the job. Superseded revisions can never define
        a payment amount (section 13) -- is_current is the canonical marker."""
        from app.engines.quote_checklist.models import ServiceJobQuote
        return (await self.db.execute(
            select(ServiceJobQuote)
            .where(ServiceJobQuote.job_id == job_id,
                   ServiceJobQuote.tenant_id == self.tenant_id,
                   ServiceJobQuote.is_current.is_(True))
            .order_by(ServiceJobQuote.version_number.desc())
        )).scalars().first()

    async def _workflow(self, job):
        from app.engines.admin_catalog.models import ServiceJobWorkflow
        wid = getattr(job, "service_job_workflow_id", None)
        if not wid:
            return None
        return (await self.db.execute(
            select(ServiceJobWorkflow).where(ServiceJobWorkflow.id == wid)
        )).scalars().first()

    async def _service_name(self, offering_id):
        if not offering_id:
            return None
        from app.engines.admin_catalog.models import MasterService
        row = (await self.db.execute(
            select(MasterService.service_name).where(MasterService.id == offering_id)
        )).first()
        return row[0] if row else None

    async def _technician_name(self, staff_id):
        if not staff_id:
            return None
        try:
            from app.engines.home_service_assignment.staff_model import ProviderTeamMember
            row = (await self.db.execute(
                select(ProviderTeamMember).where(ProviderTeamMember.id == staff_id)
            )).scalars().first()
            if row is not None:
                return getattr(row, "full_name", None) or getattr(row, "name", None)
        except Exception:
            pass
        return None

    def _alias(self, customer_id):
        if not customer_id:
            return None
        from app.engines.tenant_engine.customer_operational_access_policy import customer_alias
        return customer_alias(self.tenant_id, customer_id)

    # ── Canonical expected-amount resolution (section 8) ─────────────────────

    async def resolve_expected_amount(self, job, booking=None, invoice=None) -> dict:
        """Resolve the expected final payable SERVER-SIDE. A browser-supplied
        expected amount is never authoritative anywhere in this module.

        Precedence:
          1. The issued invoice's immutable customer_payable_amount snapshot.
             It includes the approved service value, visit-fee adjustment and
             snapshotted customer platform charge.
          2. A CURRENT APPROVED quote when an invoice has not yet been
             materialized (legacy/read-only projection fallback).
          3. The booking's immutable price_snapshot (fixed price + approved
             options), visit-fee adjusted.
        Anything else -> unresolved, reported honestly, never guessed.
        """
        booking = booking if booking is not None else await self._booking(job.booking_id)
        invoice = invoice if invoice is not None else await self._invoice_for_job(job.id)
        quote = await self._current_quote(job.id)
        wf = await self._workflow(job)
        pricing_behavior = getattr(wf, "pricing_behavior", None) if wf else None

        snap = (booking.price_snapshot or {}) if booking is not None else {}
        visit_fee = _d(snap.get("visit_fee"))
        currency = snap.get("currency") or (invoice.currency if invoice is not None else "INR")

        approved_estimate = None
        if quote is not None:
            approved_estimate = {
                "quote_id":        str(quote.id),
                "quote_number":    quote.quote_number,
                "version_number":  quote.version_number,
                "status":          quote.status,
                "is_current":      quote.is_current,
                "total_amount":    str(quote.total_amount),
                "customer_payable_amount": str(quote.customer_payable_amount),
                "approved_at":     _iso(quote.approved_at),
                "is_approved":     quote.status == QS_CUSTOMER_APPROVED,
            }

        # Repair / post-assessment pricing MUST have an approved current
        # estimate before any amount can be declared. A revision-requested,
        # rejected or draft quote leaves this unresolved on purpose.
        repair_like = bool(
            (pricing_behavior and "assess" in str(pricing_behavior).lower())
            or (quote is not None)
        )

        expected: Decimal | None = None
        source = None
        unresolved_reason = None
        visit_fee_adjustment = Decimal("0")

        if invoice is not None and _d(invoice.customer_payable_amount) > 0:
            expected = _d(invoice.customer_payable_amount)
            source = "invoice_snapshot"
        elif quote is not None and quote.status == QS_CUSTOMER_APPROVED:
            work_amount = _d(quote.customer_payable_amount) or _d(quote.total_amount)
            # Customer continued after inspection: the visit fee already
            # charged on the published snapshot is credited against the work.
            if visit_fee > 0 and work_amount > visit_fee:
                visit_fee_adjustment = -visit_fee
            expected = work_amount + visit_fee_adjustment
            source = "approved_estimate"
        elif repair_like and quote is not None and quote.status != QS_CUSTOMER_APPROVED:
            unresolved_reason = ERR_DP_NO_APPROVED_ESTIMATE
        else:
            candidates = [
                snap.get("selected_price_amount"), snap.get("standard_price"),
                snap.get("base_price"), snap.get("display_price_amount"),
            ]
            for c in candidates:
                if c is not None and _d(c) > 0:
                    expected = _d(c)
                    source = "booking_price_snapshot"
                    break
            if expected is None and visit_fee > 0:
                # Customer declined after inspection: work amount is not
                # payable; the visit fee remains payable per the snapshot.
                expected = visit_fee
                source = "visit_fee_only"
            if expected is None:
                unresolved_reason = ERR_DP_EXPECTED_UNRESOLVED

        return {
            "expected_amount":      str(expected) if expected is not None else None,
            "expected_amount_source": source,
            "unresolved_reason":    unresolved_reason,
            "currency":             currency,
            "pricing_behavior":     pricing_behavior,
            "approved_estimate":    approved_estimate,
            "visit_fee":            str(visit_fee),
            "visit_fee_adjustment": str(visit_fee_adjustment),
            "requires_direct_payment_record": bool(
                getattr(wf, "requires_direct_payment_record", False)) if wf else False,
        }

    # ── Derived reconciliation status (section 11) ───────────────────────────

    def derive_status(self, pay: ServicePaymentRecord) -> str:
        if pay.dispute_complaint_id:
            return RS_DISPUTED
        if pay.payment_status == "disputed":
            return RS_DISPUTED
        if pay.customer_confirmation_action in MISMATCH_ACTIONS:
            return RS_MISMATCHED
        if pay.customer_confirmed:
            declared = _d(pay.collected_amount)
            reported = pay.customer_reported_amount
            if reported is not None and abs(declared - _d(reported)) > _TOL:
                return RS_MISMATCHED
            return RS_CONFIRMED
        if pay.provider_confirmed_at:
            # A declared amount that differs from the server-resolved expected
            # amount is ALREADY a mismatch under review (section 9) -- it must
            # never present as a clean "awaiting customer" just because the
            # customer has not replied yet.
            if (pay.expected_amount is not None
                    and abs(_d(pay.collected_amount) - _d(pay.expected_amount)) > _TOL):
                return RS_MISMATCHED
            return RS_AWAITING_CUSTOMER
        return RS_AWAITING_PROVIDER

    # ── Projections ─────────────────────────────────────────────────────────

    async def _row(self, pay: ServicePaymentRecord, *, job=None, booking=None,
                   invoice=None, service_name=None) -> dict:
        job = job if job is not None else await self._job(pay.job_id)
        status = self.derive_status(pay)
        return {
            "id":               str(pay.id),
            "kind":             "record",
            "job_id":           str(pay.job_id),
            "job_ref":          getattr(job, "job_number", None) or str(pay.job_id)[:8],
            "booking_id":       str(pay.booking_id) if pay.booking_id else None,
            "time_window":      getattr(job, "scheduled_time_window", None),
            "customer_alias":   self._alias(pay.customer_id),
            "service":          service_name if service_name is not None
                                else await self._service_name(getattr(job, "offering_id", None)),
            "declared_amount":  str(pay.collected_amount),
            "expected_amount":  str(pay.expected_amount) if pay.expected_amount is not None else None,
            "currency":         pay.currency,
            "method":           pay.payment_mode,
            "method_label":     METHOD_LABELS.get(pay.payment_mode, pay.payment_mode),
            "provider_confirmation": {
                "state": "confirmed" if pay.provider_confirmed_at else "pending",
                "at":    _iso(pay.provider_confirmed_at),
            },
            "customer_confirmation": {
                "state": ("confirmed" if pay.customer_confirmed else
                          "mismatched" if pay.customer_confirmation_action in MISMATCH_ACTIONS
                          else "pending"),
                "at":    _iso(pay.customer_confirmed_at),
                "action": pay.customer_confirmation_action,
            },
            "status":           status,
            "status_label":     STATUS_LABELS.get(status, status),
            "dispute_complaint_id": str(pay.dispute_complaint_id) if pay.dispute_complaint_id else None,
            "declaration_version": pay.declaration_version,
            "reminder_count":   pay.reminder_count,
            "last_reminder_at": _iso(pay.last_reminder_at),
            "updated_at":       _iso(pay.updated_at),
        }

    async def _service_facet(self) -> list[dict]:
        """Services this tenant has published, as filter options.

        Built from the SAME column the filter matches on
        (`ServiceJob.offering_id` -> `tenant_services.master_service_id`), so a
        value offered here can never come back empty.
        """
        rows = (await self.db.execute(text("""
            SELECT DISTINCT ms.id::text AS id, ms.service_name AS name
              FROM tenant_services ts
              JOIN master_services ms ON ms.id = ts.master_service_id
             WHERE ts.tenant_id = :tid AND ts.is_active = true AND ts.deleted_at IS NULL
             ORDER BY ms.service_name
        """), {"tid": str(self.tenant_id)})).fetchall()
        return [{"value": r.id, "label": r.name} for r in rows]

    async def _technician_facet(self) -> list[dict]:
        """Team members who can hold a job, as filter options."""
        rows = (await self.db.execute(text("""
            SELECT id::text AS id,
                   COALESCE(NULLIF(TRIM(full_name), ''), designation, 'Technician') AS name
              FROM provider_team_members
             WHERE tenant_id = :tid AND status = 'active'
             ORDER BY 2
        """), {"tid": str(self.tenant_id)})).fetchall()
        return [{"value": r.id, "label": r.name} for r in rows]

    async def _awaiting_provider_row(self, job, service_name=None) -> dict:
        """A job whose work is done and which requires a declaration that does
        not exist yet. Represented with a synthetic `job:{id}` reference -- no
        placeholder ServicePaymentRecord row is ever written to fake one."""
        exp = await self.resolve_expected_amount(job)
        return {
            "id":               f"job:{job.id}",
            "kind":             "awaiting_provider",
            "job_id":           str(job.id),
            "job_ref":          job.job_number,
            "booking_id":       str(job.booking_id) if job.booking_id else None,
            "time_window":      job.scheduled_time_window,
            "customer_alias":   self._alias(job.customer_id),
            "service":          service_name if service_name is not None
                                else await self._service_name(job.offering_id),
            "declared_amount":  None,
            "expected_amount":  exp["expected_amount"],
            "currency":         exp["currency"],
            "method":           None,
            "method_label":     None,
            "provider_confirmation": {"state": "pending", "at": None},
            "customer_confirmation": {"state": "pending", "at": None, "action": None},
            "status":           RS_AWAITING_PROVIDER,
            "status_label":     STATUS_LABELS[RS_AWAITING_PROVIDER],
            "dispute_complaint_id": None,
            "declaration_version": 0,
            "reminder_count":   0,
            "last_reminder_at": None,
            "updated_at":       _iso(job.updated_at),
        }

    # ── Queue (section 7 / 19) ──────────────────────────────────────────────

    async def list_queue(
        self, *, status: str | None = None, method: str | None = None,
        service_id: str | None = None, job_type_id: str | None = None,
        technician_id: str | None = None, date_from: str | None = None,
        date_to: str | None = None, search: str | None = None,
        page: int = 1, limit: int = 25,
    ) -> dict:
        from app.engines.final_records.models import ServiceBooking, ServiceJob

        # ── Real declaration records ────────────────────────────────────────
        pq = (select(ServicePaymentRecord, ServiceJob)
              .join(ServiceJob, ServiceJob.id == ServicePaymentRecord.job_id, isouter=True)
              .where(ServicePaymentRecord.tenant_id == self.tenant_id))
        if method:
            pq = pq.where(ServicePaymentRecord.payment_mode == method)
        df, dt_ = _parse_dt(date_from), _parse_dt(date_to)
        if df is not None:
            pq = pq.where(ServicePaymentRecord.created_at >= df)
        if dt_ is not None:
            pq = pq.where(ServicePaymentRecord.created_at <= dt_)
        if technician_id:
            pq = pq.where(ServiceJob.assigned_staff_id == uuid.UUID(technician_id))
        if service_id:
            pq = pq.where(ServiceJob.offering_id == uuid.UUID(service_id))
        if job_type_id:
            pq = pq.where(ServiceJob.job_type_id == uuid.UUID(job_type_id))
        pq = pq.order_by(ServicePaymentRecord.updated_at.desc())
        pay_rows = (await self.db.execute(pq)).all()

        # ── Jobs awaiting a provider declaration ────────────────────────────
        # "Has this job been declared?" is a fact about the JOB, not about the
        # caller's current filter. This set was built from the FILTERED
        # `pay_rows`, so any filter that excluded a payment record made its job
        # fall through to the awaiting-declaration branch below — e.g. filtering
        # by a method the payment did not use, or a date range it falls outside,
        # made an already-paid job reappear as "awaiting provider declaration"
        # and invited a duplicate declaration for money already recorded.
        # Resolve it from every payment record this tenant has, unfiltered.
        declared_job_ids = set((await self.db.execute(
            select(ServicePaymentRecord.job_id)
            .where(ServicePaymentRecord.tenant_id == self.tenant_id)
        )).scalars().all())
        jq = (select(ServiceJob)
              .where(ServiceJob.tenant_id == self.tenant_id,
                     ServiceJob.status.in_(WORK_DONE_JOB_STATUSES)))
        if technician_id:
            jq = jq.where(ServiceJob.assigned_staff_id == uuid.UUID(technician_id))
        if service_id:
            jq = jq.where(ServiceJob.offering_id == uuid.UUID(service_id))
        if job_type_id:
            jq = jq.where(ServiceJob.job_type_id == uuid.UUID(job_type_id))
        jobs = [j for j in (await self.db.execute(jq)).scalars().all()
                if j.id not in declared_job_ids]

        rows: list[dict] = []
        for pay, job in pay_rows:
            rows.append(await self._row(pay, job=job))
        for job in jobs:
            rows.append(await self._awaiting_provider_row(job))

        # ── Search (alias / job ref / service) ──────────────────────────────
        if search:
            s = search.strip().lower()
            rows = [r for r in rows if s in " ".join(
                str(x or "") for x in (r["job_ref"], r["customer_alias"], r["service"])
            ).lower()]

        # ── Summary (section 6) — computed over the whole filtered set, not
        # the current page, and never fabricated when a query fails.
        summary = self._summary(rows)

        tab_counts = {
            "needs_action": sum(1 for r in rows if r["status"] in
                                (RS_AWAITING_PROVIDER, RS_MISMATCHED, RS_DISPUTED)),
            "all":       len(rows),
            "awaiting_provider": sum(1 for r in rows if r["status"] == RS_AWAITING_PROVIDER),
            "awaiting_customer": sum(1 for r in rows if r["status"] == RS_AWAITING_CUSTOMER),
            "confirmed": sum(1 for r in rows if r["status"] == RS_CONFIRMED),
            "mismatch":  sum(1 for r in rows if r["status"] == RS_MISMATCHED),
            "disputed":  sum(1 for r in rows if r["status"] == RS_DISPUTED),
        }

        if status and status != "all":
            if status == "needs_action":
                rows = [r for r in rows if r["status"] in
                        (RS_AWAITING_PROVIDER, RS_MISMATCHED, RS_DISPUTED)]
            else:
                rows = [r for r in rows if r["status"] == status]

        rows.sort(key=lambda r: r["updated_at"] or "", reverse=True)
        total = len(rows)
        start = max(0, (page - 1) * limit)
        page_rows = rows[start:start + limit]

        return {
            "summary":   summary,
            "records":   page_rows,
            "tab_counts": tab_counts,
            "filters": {
                "statuses": [{"value": k, "label": v} for k, v in STATUS_LABELS.items()],
                "methods":  [{"value": k, "label": v} for k, v in sorted(METHOD_LABELS.items())],
                # `service_id` and `technician_id` were accepted and correctly
                # applied by this query (see the where-clauses above) but no
                # facet listed the available values, so no UI could offer them
                # and the two most useful cuts of a finance queue — "which
                # service" and "which technician" — were unreachable.
                "services":    await self._service_facet(),
                "technicians": await self._technician_facet(),
            },
            "pagination": {"page": page, "limit": limit, "total": total,
                           "pages": max(1, -(-total // limit))},
            "available_actions": ["declare", "remind_customer", "open_dispute", "export"],
            "banner": {"type": "info", "text":
                       "ServiceOS does not collect this money. "
                       "Customers pay your business directly."},
            "generated_at": _utcnow().isoformat(),
        }

    def _summary(self, rows: list[dict]) -> dict:
        def agg(pred):
            sel = [r for r in rows if pred(r)]
            total = sum(_d(r["declared_amount"] if r["declared_amount"] is not None
                           else r["expected_amount"]) for r in sel)
            return {"count": len(sel), "amount": str(total)}

        confirmed_rows = [r for r in rows if r["status"] == RS_CONFIRMED]
        confirmed_value = sum(_d(r["declared_amount"]) for r in confirmed_rows)
        return {
            "awaiting_provider": agg(lambda r: r["status"] == RS_AWAITING_PROVIDER),
            "awaiting_customer": agg(lambda r: r["status"] == RS_AWAITING_CUSTOMER),
            "confirmed":         agg(lambda r: r["status"] == RS_CONFIRMED),
            "mismatched":        agg(lambda r: r["status"] == RS_MISMATCHED),
            "disputed":          agg(lambda r: r["status"] == RS_DISPUTED),
            # NEVER "platform revenue" / "settlement" / "payout value".
            "confirmed_direct_payment_value": {
                "label":   "Confirmed direct-payment value",
                "subtext": "Total confirmed amount",
                "amount":  str(confirmed_value),
                "currency": (rows[0]["currency"] if rows else "INR"),
            },
        }

    # ── Detail (section 19) ─────────────────────────────────────────────────

    async def _get_record(self, payment_id: uuid.UUID) -> ServicePaymentRecord:
        pay = (await self.db.execute(
            select(ServicePaymentRecord).where(
                ServicePaymentRecord.id == payment_id,
                ServicePaymentRecord.tenant_id == self.tenant_id,
            )
        )).scalars().first()
        if pay is None:
            raise _err(ERR_DP_NOT_FOUND, "Direct payment record not found.", 404)
        return pay

    async def get_detail(self, payment_id: uuid.UUID) -> dict:
        pay = await self._get_record(payment_id)
        job = await self._job(pay.job_id)
        booking = await self._booking(pay.booking_id)
        invoice = await self._invoice_for_job(pay.job_id)
        exp = await self.resolve_expected_amount(job, booking, invoice) if job else {}
        status = self.derive_status(pay)

        events = (await self.db.execute(
            select(FinancialEvent)
            .where(FinancialEvent.record_id == pay.id,
                   FinancialEvent.tenant_id == self.tenant_id)
            .order_by(FinancialEvent.created_at.desc())
        )).scalars().all()

        dispute = None
        if pay.dispute_complaint_id:
            try:
                from app.engines.complaints.models import CustomerComplaint
                c = await self.db.get(CustomerComplaint, pay.dispute_complaint_id)
                if c is not None:
                    dispute = {
                        "complaint_id":   str(c.id),
                        "complaint_number": getattr(c, "complaint_number", None),
                        "status":         c.status,
                        "complaint_type": c.complaint_type,
                        "created_at":     _iso(c.created_at),
                        "resolution_center": "Complaints & Resolution Center",
                    }
            except Exception:
                dispute = {"complaint_id": str(pay.dispute_complaint_id),
                           "status": "unknown", "detail_unavailable": True}

        evidence = None
        if pay.evidence_media_id:
            evidence = {
                "media_id":  str(pay.evidence_media_id),
                "type":      pay.evidence_type,
                "label":     "Receipt uploaded",
                # Access-checked media route -- never a public URL.
                "view_path": f"/v1/media/{pay.evidence_media_id}/view",
                "uploaded_by_user_id": str(pay.collected_by_user_id) if pay.collected_by_user_id else None,
                "uploaded_at": _iso(pay.provider_confirmed_at),
            }
        elif pay.proof_media_url:
            evidence = {"media_id": None, "type": pay.evidence_type,
                        "label": "Receipt uploaded", "view_path": None,
                        "legacy_reference": True}

        can_edit = (not pay.customer_confirmed) and not pay.dispute_complaint_id
        next_reminder_at = None
        if pay.last_reminder_at:
            next_reminder_at = _iso(pay.last_reminder_at +
                                    timedelta(hours=REMINDER_MIN_INTERVAL_HOURS))

        escalation_due = None
        if status == RS_AWAITING_CUSTOMER and pay.provider_confirmed_at:
            escalation_due = _iso(pay.provider_confirmed_at +
                                  timedelta(days=CUSTOMER_NONRESPONSE_ESCALATION_DAYS))

        return {
            "record": await self._row(pay, job=job),
            "job_context": {
                "job_id":        str(pay.job_id),
                "job_ref":       getattr(job, "job_number", None),
                "service":       await self._service_name(getattr(job, "offering_id", None)),
                "technician":    await self._technician_name(getattr(job, "assigned_staff_id", None)),
                "job_status":    getattr(job, "status", None),
                "completed_at":  _iso(getattr(job, "updated_at", None))
                                 if getattr(job, "status", None) in ("completed", "work_done") else None,
                "scheduled_date": (job.scheduled_date.isoformat()
                                   if job is not None and job.scheduled_date else None),
                "time_window":   getattr(job, "scheduled_time_window", None),
                "customer_alias": self._alias(pay.customer_id),
                # Exact service address is deliberately NOT returned -- it is
                # unnecessary for payment confirmation (section 21).
                "locality":      None,
            },
            "expected_amount":      exp.get("expected_amount"),
            "expected_amount_source": exp.get("expected_amount_source"),
            "expected_unresolved_reason": exp.get("unresolved_reason"),
            "approved_estimate":    exp.get("approved_estimate"),
            "visit_fee_adjustment": {
                "visit_fee":  exp.get("visit_fee"),
                "adjustment": exp.get("visit_fee_adjustment"),
                "applied":    _d(exp.get("visit_fee_adjustment")) != 0,
            },
            "final_payable_label": "Final payable (customer-to-provider)",
            "provider_declaration": {
                "state":          "confirmed" if pay.provider_confirmed_at else "pending",
                "amount":         str(pay.collected_amount),
                "currency":       pay.currency,
                "method":         pay.payment_mode,
                "method_label":   METHOD_LABELS.get(pay.payment_mode, pay.payment_mode),
                "reference_id":   pay.payment_reference_id,
                "note":           pay.declaration_note,
                "received_at":    _iso(pay.received_at),
                "confirmed_at":   _iso(pay.provider_confirmed_at),
                "version":        pay.declaration_version,
                "difference_reason": pay.amount_difference_reason,
                "correction_reason": pay.correction_reason,
                "declared_by_user_id": str(pay.collected_by_user_id) if pay.collected_by_user_id else None,
            },
            "customer_confirmation": {
                "state":       ("confirmed" if pay.customer_confirmed else
                                "mismatched" if pay.customer_confirmation_action in MISMATCH_ACTIONS
                                else "pending"),
                "action":      pay.customer_confirmation_action,
                "confirmed_at": _iso(pay.customer_confirmed_at),
                "reported_amount": (str(pay.customer_reported_amount)
                                    if pay.customer_reported_amount is not None else None),
                "reported_method": pay.customer_reported_method,
                "note":        pay.customer_confirmation_note,
                "reminder_count": pay.reminder_count,
                "last_reminder_at": _iso(pay.last_reminder_at),
                "reminder_channel": "in_app",
                "next_reminder_allowed_at": next_reminder_at,
                "escalation_due_at": escalation_due,
                "reassurance": "We will notify you to confirm the amount paid.",
            },
            "workflow": self._workflow_steps(pay, job, status),
            "evidence": evidence,
            "dispute":  dispute,
            "activity": [self._activity_entry(e) for e in events],
            "policy":   POLICY_BULLETS,
            "available_actions": {
                "remind_customer": status in (RS_AWAITING_CUSTOMER, RS_MISMATCHED),
                "edit_declaration": can_edit,
                "edit_declaration_hint": "Available before customer confirmation",
                "open_dispute": status in (RS_AWAITING_CUSTOMER, RS_MISMATCHED, RS_CONFIRMED)
                                and not pay.dispute_complaint_id,
                "open_job": True,
                "upload_evidence": can_edit,
            },
            # Explicit, machine-checkable proof for the UI and for tests.
            "settlement_guarantees": {
                "payout_created": False,
                "settlement_created": False,
                "wallet_credit_posted": False,
                "platform_revenue_recognised": False,
                "serviceos_collected_amount": "0",
            },
            "version": pay.declaration_version,
            "generated_at": _utcnow().isoformat(),
        }

    def _workflow_steps(self, pay, job, status: str) -> dict:
        job_status = getattr(job, "status", None)
        done = {
            "work_done":         job_status in WORK_DONE_JOB_STATUSES or bool(pay.provider_confirmed_at),
            "provider_declares": bool(pay.provider_confirmed_at),
            "customer_confirms": bool(pay.customer_confirmed),
            "reconciled":        status == RS_CONFIRMED,
            "job_completed":     job_status == "completed",
        }
        current = None
        for key, _label in WORKFLOW_STEPS:
            if not done[key]:
                current = key
                break
        return {
            "current_step": current,
            "steps": [
                {"key": k, "label": lbl, "complete": done[k], "current": k == current}
                for k, lbl in WORKFLOW_STEPS
            ],
        }

    def _activity_entry(self, e: FinancialEvent) -> dict:
        labels = {
            FEV_DP_DECLARED:       "Provider recorded payment",
            FEV_DP_CORRECTED:      "Declaration corrected",
            FEV_DP_REMINDER_SENT:  "Confirmation reminder sent",
            FEV_DP_CONFIRMED:      "Customer confirmed payment",
            FEV_DP_MISMATCH:       "Customer reported a different payment",
            FEV_DP_DISPUTE_OPENED: "Payment dispute opened",
        }
        return {
            "at":      _iso(e.created_at),
            "type":    e.event_type,
            "label":   labels.get(e.event_type, e.event_type.replace("_", " ").capitalize()),
            "actor":   e.actor_type,
            "detail":  e.new_value,
            "reason":  e.reason,
        }

    # ── Audit / financial event helper ──────────────────────────────────────

    async def _log(self, pay: ServicePaymentRecord, event_type: str, actor_type: str,
                   actor_user_id, new_value: dict | None = None,
                   old_value: dict | None = None, reason: str | None = None) -> None:
        self.db.add(FinancialEvent(
            id=uuid.uuid4(),
            record_type="payment",
            record_id=pay.id,
            tenant_id=pay.tenant_id,
            customer_id=pay.customer_id,
            actor_type=actor_type,
            actor_user_id=uuid.UUID(str(actor_user_id)) if actor_user_id else None,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            request_id=self.request_id,
        ))

    # ── Provider declaration (section 9) ────────────────────────────────────

    async def declaration_preflight(self, job_id: uuid.UUID) -> dict:
        job = await self._job(job_id)
        if job is None:
            raise _err(ERR_DP_JOB_NOT_FOUND, "Job not found for this tenant.", 404)
        exp = await self.resolve_expected_amount(job)
        existing = (await self.db.execute(
            select(ServicePaymentRecord).where(
                ServicePaymentRecord.job_id == job_id,
                ServicePaymentRecord.tenant_id == self.tenant_id,
            )
        )).scalars().first()
        return {
            "job_id":  str(job_id),
            "job_ref": job.job_number,
            "work_done": job.status in WORK_DONE_JOB_STATUSES,
            "expected_amount": exp["expected_amount"],
            "expected_amount_source": exp["expected_amount_source"],
            "approved_estimate": exp["approved_estimate"],
            "visit_fee": exp["visit_fee"],
            "visit_fee_adjustment": exp["visit_fee_adjustment"],
            "unresolved_reason": exp["unresolved_reason"],
            "existing_declaration": (await self._row(existing, job=job)) if existing else None,
            "methods": [{"value": k, "label": METHOD_LABELS[k]} for k in sorted(DIRECT_PAYMENT_METHODS)],
            "sensitive_data_warning": (
                "Never upload card numbers, CVV, UPI PIN, OTP, net-banking "
                "passwords or any full bank credentials."),
        }

    async def declare(
        self, *, job_id: uuid.UUID, amount, method: str, actor_user_id: str,
        received_at: datetime | None = None, reference_id: str | None = None,
        note: str | None = None, evidence_media_id: str | None = None,
        evidence_type: str | None = None, difference_reason: str | None = None,
    ) -> dict:
        if method not in DIRECT_PAYMENT_METHODS:
            raise _err(ERR_DP_INVALID_METHOD,
                       "Not a supported direct payment method. ServiceOS-collected "
                       "gateway payments are not direct payments.")
        if evidence_type and evidence_type not in EVIDENCE_TYPES:
            raise _err(ERR_DP_INVALID_EVIDENCE_TYPE, "Unknown evidence type.")
        amt = _d(amount)
        if amt <= 0:
            raise _err(ERR_DP_INVALID_AMOUNT, "Declared amount must be greater than zero.")

        job = await self._job(job_id)
        if job is None:
            raise _err(ERR_DP_JOB_NOT_FOUND, "Job not found for this tenant.", 404)
        if job.status not in WORK_DONE_JOB_STATUSES:
            raise _err(ERR_DP_WORK_NOT_DONE,
                       "Work must be completed before a direct payment can be declared.")

        # Idempotency / no duplicate obligation: one declaration per job.
        existing = (await self.db.execute(
            select(ServicePaymentRecord).where(
                ServicePaymentRecord.job_id == job_id,
                ServicePaymentRecord.tenant_id == self.tenant_id,
            )
        )).scalars().first()
        if existing is not None:
            raise _err(ERR_DP_ALREADY_DECLARED,
                       "A direct payment declaration already exists for this job. "
                       "Correct the existing declaration instead.", 409)

        booking = await self._booking(job.booking_id)
        # A payment may never point at a job UUID masquerading as invoice_id.
        # Materialize the canonical invoice here as a compatibility safety net
        # for work_done records created before proof submission did so.
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        invoice = await ServiceInvoiceService().ensure_issued_for_job(
            self.db, str(job.id), str(self.tenant_id), actor_user_id,
            request_id=self.request_id, notify_customer=True,
        )
        exp = await self.resolve_expected_amount(job, booking, invoice)
        if exp["unresolved_reason"] == ERR_DP_NO_APPROVED_ESTIMATE:
            raise _err(ERR_DP_NO_APPROVED_ESTIMATE,
                       "No approved estimate for this Repair job. The provider cannot "
                       "declare an amount against an unapproved or superseded estimate.")
        if exp["expected_amount"] is None:
            raise _err(ERR_DP_EXPECTED_UNRESOLVED,
                       "The expected payable amount could not be resolved from any "
                       "canonical source. Nothing is guessed here.")

        expected = _d(exp["expected_amount"])
        mismatch = abs(amt - expected) > _TOL
        if mismatch and not (difference_reason or "").strip():
            raise _err(ERR_DP_REASON_REQUIRED,
                       f"Declared amount differs from the expected {expected}. "
                       "A reason is required; the record will be marked for review.")

        now = _utcnow()
        pay = ServicePaymentRecord(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            booking_id=job.booking_id,
            job_id=job.id,
            tenant_id=self.tenant_id,
            customer_id=job.customer_id,
            payment_mode=method,
            # "collected" here means "the provider states the customer paid
            # them directly" -- it is NOT money received by ServiceOS.
            payment_status="collected",
            collected_amount=amt,
            currency=exp["currency"] or "INR",
            collected_by_user_id=uuid.UUID(str(actor_user_id)),
            collected_by_staff_member_id=job.assigned_staff_id,
            customer_confirmation_required=True,
            customer_confirmed=False,
            provider_confirmed_at=now,
            expected_amount=expected,
            payment_reference_id=reference_id,
            declaration_note=note,
            declaration_version=1,
            amount_difference_reason=difference_reason if mismatch else None,
            received_at=received_at or now,
            reconciliation_status=RS_MISMATCHED if mismatch else RS_AWAITING_CUSTOMER,
            evidence_media_id=uuid.UUID(evidence_media_id) if evidence_media_id else None,
            evidence_type=evidence_type,
        )
        self.db.add(pay)
        await self.db.flush()
        invoice.payment_mode = method
        await ServiceInvoiceService().update_payment_status(
            self.db, invoice.id, "collected", paid_at=now,
        )
        await self._log(pay, FEV_DP_DECLARED, "staff", actor_user_id, new_value={
            "declared_amount": str(amt), "expected_amount": str(expected),
            "method": method, "reference_id": reference_id,
            "mismatch": mismatch, "visit_fee_adjustment": exp["visit_fee_adjustment"],
            "expected_amount_source": exp["expected_amount_source"],
            "no_payout_created": True, "no_settlement_created": True,
        }, reason=difference_reason)
        await self.db.commit()
        await self.db.refresh(pay)
        await self._notify_customer_confirmation_request(pay, job)
        return await self.get_detail(pay.id)

    async def correct_declaration(
        self, *, payment_id: uuid.UUID, actor_user_id: str, expected_version: int | None,
        amount=None, method: str | None = None, reference_id: str | None = None,
        note: str | None = None, received_at: datetime | None = None,
        evidence_media_id: str | None = None, evidence_type: str | None = None,
        correction_reason: str | None = None, difference_reason: str | None = None,
    ) -> dict:
        pay = await self._get_record(payment_id)
        if pay.dispute_complaint_id:
            raise _err(ERR_DP_LOCKED_BY_DISPUTE,
                       "Ordinary edits are locked while a payment dispute is open. "
                       "Corrections happen through dispute resolution.", 409)
        if pay.customer_confirmed:
            raise _err(ERR_DP_LOCKED_AFTER_CONFIRM,
                       "The customer has already confirmed. This record cannot be "
                       "edited in place -- a reversal/correction workflow with "
                       "customer notification is required.", 409)
        if expected_version is not None and expected_version != pay.declaration_version:
            raise _err(ERR_DP_STALE_VERSION,
                       "This declaration changed since you loaded it. Reload and retry.", 409)
        if not (correction_reason or "").strip():
            raise _err(ERR_DP_REASON_REQUIRED, "A correction reason is required.")
        if method is not None and method not in DIRECT_PAYMENT_METHODS:
            raise _err(ERR_DP_INVALID_METHOD, "Not a supported direct payment method.")
        if evidence_type and evidence_type not in EVIDENCE_TYPES:
            raise _err(ERR_DP_INVALID_EVIDENCE_TYPE, "Unknown evidence type.")

        prior = {
            "declared_amount": str(pay.collected_amount),
            "method":          pay.payment_mode,
            "reference_id":    pay.payment_reference_id,
            "note":            pay.declaration_note,
            "received_at":     _iso(pay.received_at),
            "version":         pay.declaration_version,
        }

        if amount is not None:
            amt = _d(amount)
            if amt <= 0:
                raise _err(ERR_DP_INVALID_AMOUNT, "Declared amount must be greater than zero.")
            expected = _d(pay.expected_amount)
            if expected > 0 and abs(amt - expected) > _TOL and not (difference_reason or "").strip():
                raise _err(ERR_DP_REASON_REQUIRED,
                           f"Corrected amount differs from the expected {expected}. "
                           "A reason is required.")
            pay.collected_amount = amt
            pay.amount_difference_reason = (
                difference_reason if (expected > 0 and abs(amt - expected) > _TOL) else None)
        if method is not None:
            pay.payment_mode = method
        if reference_id is not None:
            pay.payment_reference_id = reference_id
        if note is not None:
            pay.declaration_note = note
        if received_at is not None:
            pay.received_at = received_at
        if evidence_media_id is not None:
            pay.evidence_media_id = uuid.UUID(evidence_media_id)
        if evidence_type is not None:
            pay.evidence_type = evidence_type

        pay.declaration_version += 1
        pay.correction_reason = correction_reason
        # A correction resets the customer's outstanding decision.
        pay.customer_confirmation_action = None
        pay.customer_reported_amount = None
        pay.customer_reported_method = None
        pay.reconciliation_status = self.derive_status(pay)
        pay.updated_at = _utcnow()
        await self._log(pay, FEV_DP_CORRECTED, "staff", actor_user_id,
                        old_value=prior,
                        new_value={"declared_amount": str(pay.collected_amount),
                                   "method": pay.payment_mode,
                                   "reference_id": pay.payment_reference_id,
                                   "version": pay.declaration_version},
                        reason=correction_reason)
        await self.db.commit()
        await self.db.refresh(pay)
        return await self.get_detail(pay.id)

    # ── Reminder (section 18) ───────────────────────────────────────────────

    async def remind_customer(self, *, payment_id: uuid.UUID, actor_user_id: str) -> dict:
        pay = await self._get_record(payment_id)
        if pay.customer_confirmed:
            raise _err(ERR_DP_ALREADY_CONFIRMED,
                       "The customer has already confirmed this payment.", 409)
        now = _utcnow()
        if pay.reminder_count >= REMINDER_MAX_PER_RECORD:
            raise _err(ERR_DP_REMINDER_RATE_LIMITED,
                       f"The maximum of {REMINDER_MAX_PER_RECORD} reminders for this "
                       "record has been reached. Open a payment dispute instead.", 429)
        if pay.last_reminder_at:
            nxt = pay.last_reminder_at + timedelta(hours=REMINDER_MIN_INTERVAL_HOURS)
            if now < nxt:
                raise _err(ERR_DP_REMINDER_RATE_LIMITED,
                           f"A reminder was already sent. Next reminder allowed at "
                           f"{nxt.isoformat()}.", 429,
                           context={"next_reminder_allowed_at": nxt.isoformat(),
                                    "reminders_sent": pay.reminder_count})

        job = await self._job(pay.job_id)
        fired = await self._notify_customer_confirmation_request(pay, job)
        pay.reminder_count += 1
        pay.last_reminder_at = now
        pay.updated_at = now
        await self._log(pay, FEV_DP_REMINDER_SENT, "staff", actor_user_id,
                        new_value={"channel": "in_app", "reminder_count": pay.reminder_count,
                                   "notification_dispatched": fired})
        await self.db.commit()
        return {
            "payment_id": str(pay.id),
            "reminders_sent": pay.reminder_count,
            "sent_at": now.isoformat(),
            "channel": "in_app",
            "notification_dispatched": fired,
            "next_reminder_allowed_at":
                (now + timedelta(hours=REMINDER_MIN_INTERVAL_HOURS)).isoformat(),
            "available_action": ("open_dispute" if pay.reminder_count >= REMINDER_MAX_PER_RECORD
                                 else "remind_customer"),
        }

    async def _notify_customer_confirmation_request(self, pay, job) -> bool:
        """Real notification through the canonical path. Contains NO raw
        contact detail -- only job number, business name and the amount."""
        try:
            from app.engines.platform_notifications.notification_service import NotificationService
            from app.engines.tenant_engine.models import Tenant
            tenant = await self.db.get(Tenant, self.tenant_id)
            ev = await NotificationService().fire_event(
                self.db, EVT_DP_CONFIRMATION_REQUESTED,
                payload={
                    "job_number":       getattr(job, "job_number", None) or "",
                    "booking_id":       str(pay.booking_id) if pay.booking_id else "",
                    "payment_id":       str(pay.id),
                    "provider_business": getattr(tenant, "business_name", "your provider"),
                    "declared_amount":  str(pay.collected_amount),
                    "currency":         pay.currency,
                    "method":           METHOD_LABELS.get(pay.payment_mode, pay.payment_mode),
                },
                tenant_id=self.tenant_id, customer_id=pay.customer_id,
                source_record_type="service_payment_records", source_record_id=pay.id,
                recipients=[{"user_id": pay.customer_id, "recipient_type": "customer"}],
            )
            return ev is not None
        except Exception:
            return False

    # ── Dispute (section 16) ────────────────────────────────────────────────

    async def open_dispute(self, *, payment_id: uuid.UUID, actor_user_id: str,
                           description: str, actor_type: str = "staff") -> dict:
        pay = await self._get_record(payment_id)
        if pay.dispute_complaint_id:
            raise _err(ERR_DP_DISPUTE_EXISTS,
                       "A payment dispute is already open for this record.", 409)
        job = await self._job(pay.job_id)

        # Canonical dispute system -- Complaints & Resolution Center. No
        # parallel dispute table, and NO payout/settlement record.
        complaint_id = None
        creation_error = None
        try:
            from app.engines.complaints.complaint_service import ComplaintService
            from app.engines.complaints.constants import RECORD_SERVICE_JOB
            c = await ComplaintService().create_complaint(
                self.db,
                customer_id=pay.customer_id,
                category_id=getattr(job, "category_id", None),
                record_type=RECORD_SERVICE_JOB,
                record_id=pay.job_id,
                complaint_type="payment_issue",
                description=description,
                tenant_id=self.tenant_id,
                offering_id=getattr(job, "offering_id", None),
                title=f"Direct payment dispute — {getattr(job, 'job_number', '')}",
                request_id=self.request_id,
            )
            complaint_id = c.id
        except Exception as exc:
            creation_error = str(exc)

        if complaint_id is None:
            raise _err("DIRECT_PAYMENT_DISPUTE_NOT_CREATED",
                       "The canonical Complaints & Resolution Center rejected this "
                       f"dispute: {creation_error}. No local dispute record was "
                       "created -- ServiceOS does not keep a parallel dispute system.",
                       422)

        pay.dispute_complaint_id = complaint_id
        pay.payment_status = "disputed"
        pay.reconciliation_status = RS_DISPUTED
        pay.updated_at = _utcnow()
        await self._log(pay, FEV_DP_DISPUTE_OPENED, actor_type, actor_user_id,
                        new_value={"complaint_id": str(complaint_id),
                                   "resolution_center": "Complaints & Resolution Center",
                                   "payout_created": False, "settlement_created": False},
                        reason=description)
        await self.db.commit()
        return await self.get_detail(pay.id)

    # ── Customer side (section 10) ──────────────────────────────────────────

    async def customer_confirm(self, *, payment_id: uuid.UUID, customer_id: str) -> dict:
        pay = (await self.db.execute(
            select(ServicePaymentRecord).where(ServicePaymentRecord.id == payment_id)
        )).scalars().first()
        if pay is None:
            raise _err(ERR_DP_NOT_FOUND, "Direct payment record not found.", 404)
        if str(pay.customer_id) != str(customer_id):
            raise _err(ERR_DP_ACCESS_DENIED, "This payment record is not yours.", 403)
        if pay.customer_confirmed:
            # Idempotent: a duplicate confirmation is a no-op, not a second fact.
            return {"payment_id": str(pay.id), "status": self.derive_status(pay),
                    "customer_confirmed": True, "idempotent": True,
                    "confirmed_at": _iso(pay.customer_confirmed_at)}
        now = _utcnow()
        pay.customer_confirmed = True
        pay.customer_confirmed_at = now
        pay.customer_confirmation_action = CA_CONFIRM
        pay.customer_reported_amount = pay.collected_amount
        pay.customer_reported_method = pay.payment_mode
        pay.reconciliation_status = RS_CONFIRMED
        pay.updated_at = now
        self.tenant_id = pay.tenant_id
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        await ServiceInvoiceService().update_payment_status(
            self.db, pay.invoice_id, "verified", paid_at=now,
        )
        await self._log(pay, FEV_DP_CONFIRMED, "customer", customer_id, new_value={
            "confirmed_amount": str(pay.collected_amount),
            "method": pay.payment_mode,
            "payout_created": False, "settlement_created": False,
            "wallet_credit_posted": False,
        })
        await self.db.commit()
        await self._notify_provider(pay, EVT_DP_CONFIRMED_BY_CUSTOMER)
        return {"payment_id": str(pay.id), "status": RS_CONFIRMED,
                "customer_confirmed": True, "idempotent": False,
                "confirmed_at": now.isoformat(),
                "serviceos_collected_amount": "0"}

    async def customer_report_mismatch(
        self, *, payment_id: uuid.UUID, customer_id: str, action: str,
        reported_amount=None, reported_method: str | None = None,
        note: str | None = None,
    ) -> dict:
        if action not in CUSTOMER_ACTIONS or action == CA_CONFIRM:
            raise _err(ERR_DP_INVALID_ACTION, "Unsupported customer action.")
        pay = (await self.db.execute(
            select(ServicePaymentRecord).where(ServicePaymentRecord.id == payment_id)
        )).scalars().first()
        if pay is None:
            raise _err(ERR_DP_NOT_FOUND, "Direct payment record not found.", 404)
        if str(pay.customer_id) != str(customer_id):
            raise _err(ERR_DP_ACCESS_DENIED, "This payment record is not yours.", 403)
        now = _utcnow()
        pay.customer_confirmed = False
        pay.customer_confirmation_action = action
        pay.customer_confirmation_note = note
        if reported_amount is not None:
            pay.customer_reported_amount = _d(reported_amount)
        if reported_method is not None:
            pay.customer_reported_method = reported_method
        if action == CA_CLARIFICATION:
            pay.reconciliation_status = RS_AWAITING_CUSTOMER
        else:
            pay.reconciliation_status = RS_MISMATCHED
        pay.updated_at = now
        self.tenant_id = pay.tenant_id
        await self._log(pay, FEV_DP_MISMATCH, "customer", customer_id, new_value={
            "action": action,
            "declared_amount": str(pay.collected_amount),
            "reported_amount": (str(pay.customer_reported_amount)
                                if pay.customer_reported_amount is not None else None),
            "reported_method": pay.customer_reported_method,
        }, reason=note)
        await self.db.commit()
        await self._notify_provider(pay, EVT_DP_MISMATCH_REPORTED)
        return {"payment_id": str(pay.id), "status": pay.reconciliation_status,
                "action": action, "reported_at": now.isoformat()}

    async def _notify_provider(self, pay, event_key: str) -> bool:
        try:
            from app.engines.platform_notifications.notification_service import NotificationService
            from app.engines.tenant_engine.models import Tenant
            from app.engines.final_records.models import ServiceJob
            tenant = await self.db.get(Tenant, pay.tenant_id)
            owner_id = getattr(tenant, "owner_user_id", None) if tenant else None
            if not owner_id:
                return False
            job = (await self.db.execute(
                select(ServiceJob).where(ServiceJob.id == pay.job_id))).scalars().first()
            ev = await NotificationService().fire_event(
                self.db, event_key,
                payload={
                    "job_number": getattr(job, "job_number", None) or "",
                    "payment_id": str(pay.id),
                    "declared_amount": str(pay.collected_amount),
                    "reported_amount": (str(pay.customer_reported_amount)
                                        if pay.customer_reported_amount is not None else ""),
                    "currency": pay.currency,
                },
                tenant_id=pay.tenant_id, customer_id=pay.customer_id,
                source_record_type="service_payment_records", source_record_id=pay.id,
                recipients=[{"user_id": owner_id, "recipient_type": "provider"}],
            )
            return ev is not None
        except Exception:
            return False

    async def customer_pending_list(self, customer_id: str) -> dict:
        """What the customer app needs to confirm a direct payment. Contains
        the provider BUSINESS name but no tenant phone/contact detail."""
        from app.engines.final_records.models import ServiceJob
        from app.engines.tenant_engine.models import Tenant
        rows = (await self.db.execute(
            select(ServicePaymentRecord, ServiceJob, Tenant)
            .join(ServiceJob, ServiceJob.id == ServicePaymentRecord.job_id, isouter=True)
            .join(Tenant, Tenant.id == ServicePaymentRecord.tenant_id, isouter=True)
            .where(ServicePaymentRecord.customer_id == uuid.UUID(str(customer_id)))
            .order_by(ServicePaymentRecord.updated_at.desc())
        )).all()
        items = []
        for pay, job, tenant in rows:
            items.append({
                "payment_id":      str(pay.id),
                "job_id":          str(pay.job_id),
                "booking_id":      str(pay.booking_id) if pay.booking_id else None,
                "job_ref":         getattr(job, "job_number", None),
                "provider_business": getattr(tenant, "business_name", None),
                "service_amount":  str(pay.collected_amount),
                "currency":        pay.currency,
                "method":          METHOD_LABELS.get(pay.payment_mode, pay.payment_mode),
                "payment_date":    _iso(pay.received_at or pay.provider_confirmed_at),
                "evidence_available": bool(pay.evidence_media_id),
                "status":          self.derive_status(pay),
                "customer_confirmed": pay.customer_confirmed,
                "customer_action": pay.customer_confirmation_action,
                "notice": "You paid this amount directly to the provider. "
                          "ServiceOS did not collect it.",
            })
        return {"items": items, "total": len(items)}

    # ── Export (section 22) ─────────────────────────────────────────────────

    async def export_rows(self, **filters) -> dict:
        q = await self.list_queue(page=1, limit=10000, **filters)
        fields = ["record_reference", "job_reference", "customer_alias", "service",
                  "expected_amount", "declared_amount", "method",
                  "provider_confirmation", "customer_confirmation",
                  "reconciliation_status", "dispute_reference",
                  "declared_at", "updated_at"]
        rows = []
        for r in q["records"]:
            rows.append({
                "record_reference":  r["id"],
                "job_reference":     r["job_ref"],
                "customer_alias":    r["customer_alias"],
                "service":           r["service"],
                "expected_amount":   r["expected_amount"],
                "declared_amount":   r["declared_amount"],
                "method":            r["method_label"],
                "provider_confirmation": r["provider_confirmation"]["state"],
                "customer_confirmation": r["customer_confirmation"]["state"],
                "reconciliation_status": r["status_label"],
                "dispute_reference": r["dispute_complaint_id"],
                "declared_at":       r["provider_confirmation"]["at"],
                "updated_at":        r["updated_at"],
            })
        return {
            "fields": fields, "rows": rows, "total": len(rows),
            "generated_at": _utcnow().isoformat(),
            "privacy_note": ("Tenant-scoped. No raw contact detail, no full address, "
                             "no evidence URL, no bank credentials, no other-vertical "
                             "or other-tenant records."),
        }
