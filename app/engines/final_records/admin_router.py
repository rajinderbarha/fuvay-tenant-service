"""Sprint 19 — Admin Final Records APIs.

Admin can view all final records across all tenants.

Endpoints:
  GET /v1/admin/final-records/bookings          — list all ServiceBookings
  GET /v1/admin/final-records/bookings/{id}
  GET /v1/admin/final-records/jobs              — list all ServiceJobs
  GET /v1/admin/final-records/jobs/{id}
  GET /v1/admin/final-records/appointments      — list all CoachingAppointments
  GET /v1/admin/final-records/appointments/{id}
  GET /v1/admin/final-records/leads             — list all RealEstateLeads
  GET /v1/admin/final-records/leads/{id}
  GET /v1/admin/final-records/audit-logs        — list FinalCreationAuditLogs
  GET /v1/admin/final-records/confirmations     — list CustomerBookingConfirmations
"""
from __future__ import annotations
import uuid
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.final_records.models import (
    ServiceBooking, ServiceJob, CoachingAppointment, RealEstateLead,
    CustomerBookingConfirmation, FinalCreationAuditLog,
)

router = APIRouter(
    prefix="/v1/admin/final-records",
    tags=["Admin Final Records"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _list(db, model, filters: list, order_col, limit: int, offset: int):
    q       = select(model)
    for f in filters:
        q = q.where(f)
    total_q = select(func.count()).where(*filters) if filters else select(func.count(model.id))
    q = q.order_by(order_col.desc()).limit(limit).offset(offset)
    rows    = (await db.execute(q)).scalars().all()
    total   = await db.scalar(total_q)
    return rows, total or 0


def _positive_amount(value) -> Decimal:
    """Return a usable positive money value without trusting loose JSON data."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
    return amount if amount > 0 else Decimal("0")


def _absolute_amount(value) -> Decimal:
    try:
        return abs(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def _canonical_job_price_summary(*, booking=None, quote=None, invoice=None) -> dict | None:
    """Build the authoritative amount shown in admin job details.

    A booking snapshot is the price known when the customer first requested the
    visit. It must not replace a later approved quote or final invoice.
    """
    if invoice is not None:
        service_total = _positive_amount(getattr(invoice, "total_amount", None))
        platform_fee = _positive_amount(getattr(invoice, "platform_fee_amount", None))
        customer_total = _positive_amount(getattr(invoice, "customer_payable_amount", None))
        if customer_total == 0:
            customer_total = service_total + platform_fee
        return {
            "customer_total": str(customer_total),
            "service_total": str(service_total),
            "platform_fee": str(platform_fee),
            "credit_applied": str(_positive_amount(getattr(invoice, "credit_applied_amount", None))),
            "currency": getattr(invoice, "currency", None) or "INR",
            "payment_mode": getattr(invoice, "payment_mode", None),
            "payment_status": getattr(invoice, "payment_status", None),
            "invoice_number": getattr(invoice, "invoice_number", None),
            "source": "final_invoice",
        }

    if quote is not None:
        service_total = _positive_amount(getattr(quote, "total_amount", None))
        customer_total = _positive_amount(getattr(quote, "customer_payable_amount", None))
        if customer_total == 0:
            customer_total = service_total
        return {
            "customer_total": str(customer_total),
            "service_total": str(service_total),
            "platform_fee": str(max(customer_total - service_total, Decimal("0"))),
            "currency": getattr(quote, "currency", None) or "INR",
            "quote_status": getattr(quote, "status", None),
            "version": getattr(quote, "version_number", None),
            "source": "current_quote",
        }

    snapshot = dict(getattr(booking, "price_snapshot", None) or {})
    if not snapshot:
        return None
    snapshot.setdefault("source", "booking_snapshot")
    return snapshot


def _job_charge_ledger_summary(rows: list) -> dict:
    """Separate legitimate completion charges from true duplicate rows."""
    from app.engines.execution.usage_credit_deduction import DEDUCTION_EVENT_TYPE
    from app.engines.vertical_monetization.customer_charge_recovery import RECOVERY_EVENT_TYPE

    commission_rows = [row for row in rows if row.event_type == DEDUCTION_EVENT_TYPE]
    platform_rows = [row for row in rows if row.event_type == RECOVERY_EVENT_TYPE]
    commission = commission_rows[0] if commission_rows else None
    platform = platform_rows[0] if platform_rows else None
    commission_amount = _absolute_amount(getattr(commission, "credit_delta", None))
    platform_amount = _absolute_amount(getattr(platform, "credit_delta", None))
    return {
        "commission_entry": commission,
        "platform_charge_entry": platform,
        "commission_amount": str(commission_amount),
        "platform_charge_amount": str(platform_amount),
        "total_provider_credit_deduction": str(commission_amount + platform_amount),
        "duplicate_count": max(0, len(commission_rows) - 1) + max(0, len(platform_rows) - 1),
    }


# ── Bookings ──────────────────────────────────────────────────────────────────

@router.get("/bookings", summary="List all service bookings (admin)", response_model=ApiResponse)
async def admin_list_bookings(
    r:         Request,
    status:    str | None       = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    limit:     int              = Query(50, ge=1, le=200),
    offset:    int              = Query(0, ge=0),
    user:      UserContext      = Depends(require_super_admin),
):
    db = await anext(get_db())
    try:
        filters = []
        if status:    filters.append(ServiceBooking.status == status)
        if tenant_id: filters.append(ServiceBooking.tenant_id == tenant_id)

        q = select(ServiceBooking)
        for f in filters: q = q.where(f)
        q = q.order_by(ServiceBooking.created_at.desc()).limit(limit).offset(offset)
        rows = (await db.execute(q)).scalars().all()

        cq = select(func.count(ServiceBooking.id))
        for f in filters: cq = cq.where(f)
        total = await db.scalar(cq)

        return ok({"items": [b.to_dict() for b in rows], "total": total or 0,
                   "limit": limit, "offset": offset}, _RID(r), "final_records")
    except Exception: raise


@router.get("/bookings/{booking_id}", summary="Get a service booking (admin)",
            response_model=ApiResponse)
async def admin_get_booking(booking_id: uuid.UUID, r: Request,
                             user: UserContext = Depends(require_super_admin)):
    db = await anext(get_db())
    result = await db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
    booking = result.scalars().first()
    if not booking:
        return ok({"error": "FINAL_BOOKING_NOT_FOUND"}, _RID(r), "final_records")
    job_result = await db.execute(select(ServiceJob).where(ServiceJob.booking_id == booking.id))
    job = job_result.scalars().first()
    data = booking.to_dict()
    data["job"] = job.to_dict() if job else None
    return ok(data, _RID(r), "final_records")


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.get("/jobs/summary", summary="Canonical operational summary for service_jobs (admin)",
            response_model=ApiResponse)
async def admin_jobs_summary(
    r:         Request,
    tenant_id: uuid.UUID | None = Query(None),
    status:    str | None       = Query(None),
    user:      UserContext      = Depends(require_super_admin),
):
    from app.engines.final_records.sla_summary import compute_summary
    db = await anext(get_db())
    result = await compute_summary(db, tenant_id=tenant_id, status=status)
    return ok(result, _RID(r), "final_records")


@router.get("/jobs", summary="List all service jobs (admin)", response_model=ApiResponse)
async def admin_list_jobs(
    r:         Request,
    status:    str | None       = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    limit:     int              = Query(50, ge=1, le=200),
    offset:    int              = Query(0, ge=0),
    user:      UserContext      = Depends(require_super_admin),
):
    from app.engines.final_records.sla_summary import attach_sla
    db = await anext(get_db())
    filters = []
    if status:    filters.append(ServiceJob.status == status)
    if tenant_id: filters.append(ServiceJob.tenant_id == tenant_id)

    q = select(ServiceJob)
    for f in filters: q = q.where(f)
    q = q.order_by(ServiceJob.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).scalars().all()

    cq = select(func.count(ServiceJob.id))
    for f in filters: cq = cq.where(f)
    total = await db.scalar(cq)

    sla_map = await attach_sla(db, rows)

    # Batch-fetch Completed Job Deduction ledger rows for this page of jobs
    # (one query, not per-row) -- real approved-terminology data, not a
    # fabricated financial column.
    from app.engines.tenant_engine.models import UsageCreditLedger
    job_ids = [j.id for j in rows]
    deduction_map: dict[str, float] = {}
    if job_ids:
        ded_rows = (await db.execute(
            select(UsageCreditLedger).where(
                UsageCreditLedger.job_id.in_(job_ids),
                UsageCreditLedger.event_type == "completed_job_deduction",
            )
        )).scalars().all()
        for dr in ded_rows:
            deduction_map[str(dr.job_id)] = abs(float(dr.credit_delta))

    items = []
    for j in rows:
        d = j.to_dict()
        d["sla"] = sla_map.get(str(j.id))
        d["collected_amount"] = (j.completion_data or {}).get("collected_amount")
        d["completed_job_deduction_credits"] = deduction_map.get(str(j.id))
        items.append(d)

    return ok({"items": items, "total": total or 0,
               "limit": limit, "offset": offset}, _RID(r), "final_records")


@router.get("/jobs/{job_id}", summary="Get a service job (admin)", response_model=ApiResponse)
async def admin_get_job(job_id: uuid.UUID, r: Request,
                         user: UserContext = Depends(require_super_admin)):
    from app.engines.final_records.sla_summary import attach_sla
    db = await anext(get_db())
    result = await db.execute(select(ServiceJob).where(ServiceJob.id == job_id))
    job = result.scalars().first()
    if not job:
        return ok({"error": "FINAL_JOB_NOT_FOUND"}, _RID(r), "final_records")

    sla_map = await attach_sla(db, [job])
    data = job.to_dict()
    data["sla"] = sla_map.get(str(job.id))

    # Enrich with booking's price/payment/provider snapshot — the job row
    # itself has no price/payment fields (see class docstrings), those
    # live on the booking created alongside it.
    booking_result = await db.execute(
        select(ServiceBooking).where(ServiceBooking.id == job.booking_id)
    )
    booking = booking_result.scalars().first()
    data["booking"] = booking.to_dict() if booking else None

    # The original booking snapshot describes the initial visit price only.
    # Once a quote/invoice exists, expose that later record as the canonical
    # price so completed-job details do not fall back to the old inspection fee.
    from app.engines.quote_checklist.models import ServiceJobQuote, ServiceJobQuoteItem
    from app.engines.invoice_payment.models import ServiceInvoice

    quote_result = await db.execute(
        select(ServiceJobQuote)
        .where(ServiceJobQuote.job_id == job.id)
        .order_by(ServiceJobQuote.is_current.desc(), ServiceJobQuote.version_number.desc())
        .limit(1)
    )
    current_quote = quote_result.scalars().first()

    quote_items = []
    if current_quote is not None:
        quote_items = (await db.execute(
            select(ServiceJobQuoteItem)
            .where(ServiceJobQuoteItem.quote_id == current_quote.id)
            .order_by(ServiceJobQuoteItem.created_at.asc())
        )).scalars().all()

    invoice_result = await db.execute(
        select(ServiceInvoice)
        .where(ServiceInvoice.job_id == job.id, ServiceInvoice.status != "cancelled")
        .order_by(ServiceInvoice.created_at.desc())
        .limit(1)
    )
    invoice = invoice_result.scalars().first()

    data["current_quote"] = current_quote.to_dict() if current_quote else None
    data["quote_items"] = [item.to_dict() for item in quote_items]
    data["invoice"] = invoice.to_dict() if invoice else None
    data["price_summary"] = _canonical_job_price_summary(
        booking=booking,
        quote=current_quote,
        invoice=invoice,
    )

    # A completed job can legitimately have one commission entry and one
    # platform-charge entry. Only repeated rows within either event are true
    # duplicates; treating the two different charge types as duplicates made
    # correct jobs display a false warning.
    from app.engines.tenant_engine.models import UsageCreditLedger
    from app.engines.execution.usage_credit_deduction import DEDUCTION_EVENT_TYPE
    from app.engines.vertical_monetization.customer_charge_recovery import RECOVERY_EVENT_TYPE
    ledger_result = await db.execute(
        select(UsageCreditLedger)
        .where(
            UsageCreditLedger.job_id == job.id,
            UsageCreditLedger.event_type.in_((DEDUCTION_EVENT_TYPE, RECOVERY_EVENT_TYPE)),
        )
        .order_by(UsageCreditLedger.created_at.desc())
    )
    ledger_rows = ledger_result.scalars().all()
    charge_ledger = _job_charge_ledger_summary(ledger_rows)
    commission_entry = charge_ledger.pop("commission_entry")
    platform_charge_entry = charge_ledger.pop("platform_charge_entry")
    data["usage_credit_deduction"] = commission_entry.to_dict() if commission_entry else None
    data["platform_charge_recovery"] = platform_charge_entry.to_dict() if platform_charge_entry else None
    data["usage_credit_deduction_duplicate_count"] = charge_ledger.pop("duplicate_count")
    data["charge_summary"] = charge_ledger

    from app.engines.admin_catalog.models import MasterIssueType, MasterService, JobTypeDefinition
    from app.engines.home_service_assignment.staff_model import ProviderTeamMember

    service_row = (await db.execute(
        select(MasterService.service_name, MasterService.job_type)
        .where(MasterService.id == job.offering_id)
    )).first()
    problem_name = None
    if job.selected_problem_id:
        problem_name = await db.scalar(
            select(MasterIssueType.name).where(MasterIssueType.id == job.selected_problem_id)
        )
    job_type_label = None
    if job.job_type_id:
        job_type_label = await db.scalar(
            select(JobTypeDefinition.label).where(JobTypeDefinition.id == job.job_type_id)
        )
    data["service_context"] = {
        "service_name": service_row[0] if service_row else None,
        "legacy_job_type": service_row[1] if service_row else None,
        "job_type": job_type_label,
        "problem_name": problem_name,
    }

    technician = None
    if job.assigned_staff_id and job.tenant_id:
        technician_row = await db.scalar(
            select(ProviderTeamMember).where(
                ProviderTeamMember.id == job.assigned_staff_id,
                ProviderTeamMember.tenant_id == job.tenant_id,
                ProviderTeamMember.deleted_at.is_(None),
            )
        )
        if technician_row:
            technician = {
                "id": str(technician_row.id),
                "full_name": technician_row.full_name,
                "designation": technician_row.designation,
                "phone": technician_row.phone,
                "email": technician_row.email,
            }
    data["technician"] = technician

    return ok(data, _RID(r), "final_records")


# ── Appointments ──────────────────────────────────────────────────────────────

@router.get("/appointments", summary="List all coaching appointments (admin)",
            response_model=ApiResponse)
async def admin_list_appointments(
    r:         Request,
    status:    str | None       = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    limit:     int              = Query(50, ge=1, le=200),
    offset:    int              = Query(0, ge=0),
    user:      UserContext      = Depends(require_super_admin),
):
    db = await anext(get_db())
    filters = []
    if status:    filters.append(CoachingAppointment.status == status)
    if tenant_id: filters.append(CoachingAppointment.tenant_id == tenant_id)

    q = select(CoachingAppointment)
    for f in filters: q = q.where(f)
    q = q.order_by(CoachingAppointment.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).scalars().all()

    cq = select(func.count(CoachingAppointment.id))
    for f in filters: cq = cq.where(f)
    total = await db.scalar(cq)

    return ok({"items": [a.to_dict() for a in rows], "total": total or 0,
               "limit": limit, "offset": offset}, _RID(r), "final_records")


@router.get("/appointments/{appointment_id}", summary="Get a coaching appointment (admin)",
            response_model=ApiResponse)
async def admin_get_appointment(appointment_id: uuid.UUID, r: Request,
                                 user: UserContext = Depends(require_super_admin)):
    db = await anext(get_db())
    result = await db.execute(
        select(CoachingAppointment).where(CoachingAppointment.id == appointment_id)
    )
    appt = result.scalars().first()
    if not appt:
        return ok({"error": "FINAL_APPOINTMENT_NOT_FOUND"}, _RID(r), "final_records")
    return ok(appt.to_dict(), _RID(r), "final_records")


# ── Real Estate Leads ─────────────────────────────────────────────────────────

@router.get("/leads", summary="List all real estate leads (admin)", response_model=ApiResponse)
async def admin_list_leads(
    r:         Request,
    status:    str | None       = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    city:      str | None       = Query(None),
    intent:    str | None       = Query(None),
    limit:     int              = Query(50, ge=1, le=200),
    offset:    int              = Query(0, ge=0),
    user:      UserContext      = Depends(require_super_admin),
):
    db = await anext(get_db())
    filters = []
    if status:    filters.append(RealEstateLead.status == status)
    if tenant_id: filters.append(RealEstateLead.tenant_id == tenant_id)
    if city:      filters.append(RealEstateLead.city == city)
    if intent:    filters.append(RealEstateLead.lead_intent == intent)

    q = select(RealEstateLead)
    for f in filters: q = q.where(f)
    q = q.order_by(RealEstateLead.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).scalars().all()

    cq = select(func.count(RealEstateLead.id))
    for f in filters: cq = cq.where(f)
    total = await db.scalar(cq)

    return ok({"items": [l.to_dict() for l in rows], "total": total or 0,
               "limit": limit, "offset": offset}, _RID(r), "final_records")


@router.get("/leads/{lead_id}", summary="Get a real estate lead (admin)",
            response_model=ApiResponse)
async def admin_get_lead(lead_id: uuid.UUID, r: Request,
                          user: UserContext = Depends(require_super_admin)):
    db = await anext(get_db())
    result = await db.execute(select(RealEstateLead).where(RealEstateLead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        return ok({"error": "FINAL_LEAD_NOT_FOUND"}, _RID(r), "final_records")
    return ok(lead.to_dict(), _RID(r), "final_records")


# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/audit-logs", summary="List final creation audit logs (admin)",
            response_model=ApiResponse)
async def admin_list_audit_logs(
    r:          Request,
    action:     str | None       = Query(None),
    draft_type: str | None       = Query(None),
    limit:      int              = Query(50, ge=1, le=200),
    offset:     int              = Query(0, ge=0),
    user:       UserContext      = Depends(require_super_admin),
):
    db = await anext(get_db())
    q = select(FinalCreationAuditLog)
    if action:     q = q.where(FinalCreationAuditLog.action == action)
    if draft_type: q = q.where(FinalCreationAuditLog.draft_type == draft_type)
    q = q.order_by(FinalCreationAuditLog.created_at.desc()).limit(limit).offset(offset)
    rows  = (await db.execute(q)).scalars().all()
    total = await db.scalar(select(func.count(FinalCreationAuditLog.id)))
    return ok({"items": [l.to_dict() for l in rows], "total": total or 0,
               "limit": limit, "offset": offset}, _RID(r), "final_records")


# ── Confirmations ─────────────────────────────────────────────────────────────

@router.get("/confirmations", summary="List customer booking confirmations (admin)",
            response_model=ApiResponse)
async def admin_list_confirmations(
    r:          Request,
    draft_type: str | None = Query(None),
    status:     str | None = Query(None),
    limit:      int        = Query(50, ge=1, le=200),
    offset:     int        = Query(0, ge=0),
    user:       UserContext = Depends(require_super_admin),
):
    db = await anext(get_db())
    q = select(CustomerBookingConfirmation)
    if draft_type: q = q.where(CustomerBookingConfirmation.draft_type == draft_type)
    if status:     q = q.where(CustomerBookingConfirmation.status == status)
    q = q.order_by(CustomerBookingConfirmation.created_at.desc()).limit(limit).offset(offset)
    rows  = (await db.execute(q)).scalars().all()
    total = await db.scalar(select(func.count(CustomerBookingConfirmation.id)))
    return ok({"items": [c.to_dict() for c in rows], "total": total or 0,
               "limit": limit, "offset": offset}, _RID(r), "final_records")
