"""Sprint 19 — Provider Record Visibility APIs.

Providers can see final records assigned to their tenant.

Endpoints:
  GET /v1/provider/my-records                — aggregated count summary
  GET /v1/provider/my-records/bookings       — list ServiceBookings for provider's tenant
  GET /v1/provider/my-records/bookings/{id}
  GET /v1/provider/my-records/jobs           — list ServiceJobs for provider's tenant
  GET /v1/provider/my-records/jobs/{id}
  GET /v1/provider/my-records/appointments   — list CoachingAppointments
  GET /v1/provider/my-records/appointments/{id}
  GET /v1/provider/my-records/leads          — list RealEstateLeads
  GET /v1/provider/my-records/leads/{id}
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
)

router = APIRouter(
    prefix="/v1/provider/my-records",
    tags=["Provider Records"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")


async def _get_tenant_id(user: UserContext) -> uuid.UUID | None:
    """Extract tenant_id from JWT. Providers have tenant_id in user context."""
    tid = getattr(user, "tenant_id", None)
    return uuid.UUID(str(tid)) if tid else None


# ── GET /my-records (summary) ─────────────────────────────────────────────────

@router.get("", summary="Provider records summary — counts", response_model=ApiResponse)
async def get_provider_records_summary(
    r:    Request,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(user)

    b_count = await db.scalar(select(func.count()).where(ServiceBooking.tenant_id == tenant_id))
    j_count = await db.scalar(select(func.count()).where(ServiceJob.tenant_id == tenant_id))
    a_count = await db.scalar(select(func.count()).where(CoachingAppointment.tenant_id == tenant_id))
    l_count = await db.scalar(select(func.count()).where(RealEstateLead.tenant_id == tenant_id))

    return ok({
        "tenant_id":         str(tenant_id) if tenant_id else None,
        "service_bookings":  b_count or 0,
        "service_jobs":      j_count or 0,
        "appointments":      a_count or 0,
        "real_estate_leads": l_count or 0,
    }, _RID(r), "final_records")


# ── GET /bookings ─────────────────────────────────────────────────────────────

@router.get("/bookings", summary="List bookings for my tenant", response_model=ApiResponse)
async def list_provider_bookings(
    r:      Request,
    status: str | None = Query(None),
    limit:  int        = Query(20, ge=1, le=100),
    offset: int        = Query(0, ge=0),
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(user)
    q = select(ServiceBooking).where(ServiceBooking.tenant_id == tenant_id)
    if status:
        q = q.where(ServiceBooking.status == status)
    q = q.order_by(ServiceBooking.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    rows   = result.scalars().all()

    total_q = select(func.count()).where(ServiceBooking.tenant_id == tenant_id)
    if status:
        total_q = total_q.where(ServiceBooking.status == status)
    total = await db.scalar(total_q)

    return ok({"items": [b.to_dict() for b in rows], "total": total,
               "limit": limit, "offset": offset}, _RID(r), "final_records")


# ── GET /bookings/{booking_id} ────────────────────────────────────────────────

@router.get("/bookings/{booking_id}", summary="Get a booking", response_model=ApiResponse)
async def get_provider_booking(
    booking_id: uuid.UUID,
    r:          Request,
    user:       UserContext  = Depends(get_current_user),
    db:         AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(user)
    result = await db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
    booking = result.scalars().first()
    if not booking or booking.tenant_id != tenant_id:
        return ok({"error": "FINAL_BOOKING_NOT_FOUND"}, _RID(r), "final_records")
    return ok(booking.to_dict(), _RID(r), "final_records")


# ── GET /jobs ─────────────────────────────────────────────────────────────────

@router.get("/jobs", summary="List jobs for my tenant", response_model=ApiResponse)
async def list_provider_jobs(
    r:      Request,
    status: str | None = Query(None),
    limit:  int        = Query(20, ge=1, le=100),
    offset: int        = Query(0, ge=0),
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(user)
    q = select(ServiceJob).where(ServiceJob.tenant_id == tenant_id)
    if status:
        q = q.where(ServiceJob.status == status)
    q = q.order_by(ServiceJob.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    rows   = result.scalars().all()

    total_q = select(func.count()).where(ServiceJob.tenant_id == tenant_id)
    if status:
        total_q = total_q.where(ServiceJob.status == status)
    total = await db.scalar(total_q)

    return ok({"items": [j.to_dict() for j in rows], "total": total,
               "limit": limit, "offset": offset}, _RID(r), "final_records")


# ── GET /jobs/{job_id} ────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}", summary="Get a service job", response_model=ApiResponse)
async def get_provider_job(
    job_id: uuid.UUID,
    r:      Request,
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(user)
    result = await db.execute(select(ServiceJob).where(ServiceJob.id == job_id))
    job = result.scalars().first()
    if not job or job.tenant_id != tenant_id:
        return ok({"error": "FINAL_JOB_NOT_FOUND"}, _RID(r), "final_records")
    return ok(job.to_dict(), _RID(r), "final_records")


# ── GET /appointments ─────────────────────────────────────────────────────────

@router.get("/appointments", summary="List appointments for my tenant", response_model=ApiResponse)
async def list_provider_appointments(
    r:      Request,
    status: str | None = Query(None),
    limit:  int        = Query(20, ge=1, le=100),
    offset: int        = Query(0, ge=0),
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(user)
    q = select(CoachingAppointment).where(CoachingAppointment.tenant_id == tenant_id)
    if status:
        q = q.where(CoachingAppointment.status == status)
    q = q.order_by(CoachingAppointment.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    rows   = result.scalars().all()

    total_q = select(func.count()).where(CoachingAppointment.tenant_id == tenant_id)
    if status:
        total_q = total_q.where(CoachingAppointment.status == status)
    total = await db.scalar(total_q)

    return ok({"items": [a.to_dict() for a in rows], "total": total,
               "limit": limit, "offset": offset}, _RID(r), "final_records")


# ── GET /appointments/{appointment_id} ────────────────────────────────────────

@router.get("/appointments/{appointment_id}", summary="Get an appointment",
            response_model=ApiResponse)
async def get_provider_appointment(
    appointment_id: uuid.UUID,
    r:              Request,
    user:           UserContext  = Depends(get_current_user),
    db:             AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(user)
    result = await db.execute(
        select(CoachingAppointment).where(CoachingAppointment.id == appointment_id)
    )
    appt = result.scalars().first()
    if not appt or appt.tenant_id != tenant_id:
        return ok({"error": "FINAL_APPOINTMENT_NOT_FOUND"}, _RID(r), "final_records")
    return ok(appt.to_dict(), _RID(r), "final_records")


# ── GET /leads ────────────────────────────────────────────────────────────────

@router.get("/leads", summary="List leads for my tenant", response_model=ApiResponse)
async def list_provider_leads(
    r:      Request,
    status: str | None = Query(None),
    limit:  int        = Query(20, ge=1, le=100),
    offset: int        = Query(0, ge=0),
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(user)
    q = select(RealEstateLead).where(RealEstateLead.tenant_id == tenant_id)
    if status:
        q = q.where(RealEstateLead.status == status)
    q = q.order_by(RealEstateLead.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    rows   = result.scalars().all()

    total_q = select(func.count()).where(RealEstateLead.tenant_id == tenant_id)
    if status:
        total_q = total_q.where(RealEstateLead.status == status)
    total = await db.scalar(total_q)

    return ok({"items": [l.to_dict() for l in rows], "total": total,
               "limit": limit, "offset": offset}, _RID(r), "final_records")


# ── GET /leads/{lead_id} ──────────────────────────────────────────────────────

@router.get("/leads/{lead_id}", summary="Get a lead", response_model=ApiResponse)
async def get_provider_lead(
    lead_id: uuid.UUID,
    r:       Request,
    user:    UserContext  = Depends(get_current_user),
    db:      AsyncSession = Depends(get_db),
):
    tenant_id = await _get_tenant_id(user)
    result = await db.execute(select(RealEstateLead).where(RealEstateLead.id == lead_id))
    lead = result.scalars().first()
    if not lead or lead.tenant_id != tenant_id:
        return ok({"error": "FINAL_LEAD_NOT_FOUND"}, _RID(r), "final_records")
    return ok(lead.to_dict(), _RID(r), "final_records")
