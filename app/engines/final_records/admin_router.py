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

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
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


# ── Bookings ──────────────────────────────────────────────────────────────────

@router.get("/bookings", summary="List all service bookings (admin)", response_model=ApiResponse)
async def admin_list_bookings(
    r:         Request,
    status:    str | None       = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    limit:     int              = Query(50, ge=1, le=200),
    offset:    int              = Query(0, ge=0),
    user:      UserContext      = Depends(get_current_user),
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
                             user: UserContext = Depends(get_current_user)):
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
    user:      UserContext      = Depends(get_current_user),
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
    user:      UserContext      = Depends(get_current_user),
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
                         user: UserContext = Depends(get_current_user)):
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

    # Enrich with the Completed Job Deduction ledger entry for this job,
    # if one exists — links this admin detail view directly to the exact
    # Usage Credit Ledger row without a separate round trip.
    from app.engines.tenant_engine.models import UsageCreditLedger
    ledger_result = await db.execute(
        select(UsageCreditLedger)
        .where(UsageCreditLedger.job_id == job.id)
        .order_by(UsageCreditLedger.created_at.desc())
    )
    ledger_rows = ledger_result.scalars().all()
    data["usage_credit_deduction"] = ledger_rows[0].to_dict() if ledger_rows else None
    data["usage_credit_deduction_duplicate_count"] = max(0, len(ledger_rows) - 1)

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
    user:      UserContext      = Depends(get_current_user),
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
                                 user: UserContext = Depends(get_current_user)):
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
    user:      UserContext      = Depends(get_current_user),
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
                          user: UserContext = Depends(get_current_user)):
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
    user:       UserContext      = Depends(get_current_user),
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
    user:       UserContext = Depends(get_current_user),
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
