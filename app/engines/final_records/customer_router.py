"""Sprint 19 — Customer My Activity APIs.

Endpoints:
  GET /v1/customer/my-activity              — aggregated view (bookings + appointments + leads)
  GET /v1/customer/my-activity/bookings     — list ServiceBookings for the current customer
  GET /v1/customer/my-activity/bookings/{id}
  GET /v1/customer/my-activity/jobs/{id}    — get ServiceJob by id
  GET /v1/customer/my-activity/appointments — list CoachingAppointments
  GET /v1/customer/my-activity/appointments/{id}
  GET /v1/customer/my-activity/leads        — list RealEstateLeads
  GET /v1/customer/my-activity/leads/{id}
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
from app.engines.final_records.constants import ERR_BOOKING_NOT_FOUND, ERR_ACCESS_DENIED

router = APIRouter(
    prefix="/v1/customer/my-activity",
    tags=["Customer My Activity"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")


# ── GET /my-activity (aggregated summary) ────────────────────────────────────

@router.get(
    "",
    summary="Customer activity summary — counts of all record types",
    response_model=ApiResponse,
)
async def get_activity_summary(
    r:    Request,
    user: UserContext     = Depends(get_current_user),
    db:   AsyncSession   = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)

    b_count = await db.scalar(select(func.count()).where(ServiceBooking.customer_id == customer_id))
    a_count = await db.scalar(select(func.count()).where(CoachingAppointment.customer_id == customer_id))
    l_count = await db.scalar(select(func.count()).where(RealEstateLead.customer_id == customer_id))

    return ok({
        "customer_id":         str(customer_id),
        "service_bookings":    b_count or 0,
        "appointments":        a_count or 0,
        "real_estate_leads":   l_count or 0,
        "total":               (b_count or 0) + (a_count or 0) + (l_count or 0),
    }, _RID(r), "final_records")


# ── GET /bookings ─────────────────────────────────────────────────────────────

@router.get("/bookings", summary="List my service bookings", response_model=ApiResponse)
async def list_my_bookings(
    r:      Request,
    status: str | None = Query(None),
    limit:  int        = Query(20, ge=1, le=100),
    offset: int        = Query(0, ge=0),
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    q = select(ServiceBooking).where(ServiceBooking.customer_id == customer_id)
    if status:
        q = q.where(ServiceBooking.status == status)
    q = q.order_by(ServiceBooking.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    rows   = result.scalars().all()

    total_q = select(func.count()).where(ServiceBooking.customer_id == customer_id)
    if status:
        total_q = total_q.where(ServiceBooking.status == status)
    total = await db.scalar(total_q)

    return ok({
        "items":  [b.to_dict() for b in rows],
        "total":  total,
        "limit":  limit,
        "offset": offset,
    }, _RID(r), "final_records")


# ── GET /bookings/{booking_id} ────────────────────────────────────────────────

@router.get("/bookings/{booking_id}", summary="Get a specific booking", response_model=ApiResponse)
async def get_my_booking(
    booking_id: uuid.UUID,
    r:          Request,
    user:       UserContext  = Depends(get_current_user),
    db:         AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    result = await db.execute(
        select(ServiceBooking).where(ServiceBooking.id == booking_id)
    )
    booking = result.scalars().first()
    if not booking:
        return ok({"error": ERR_BOOKING_NOT_FOUND}, _RID(r), "final_records")
    if booking.customer_id and booking.customer_id != customer_id:
        return ok({"error": ERR_ACCESS_DENIED}, _RID(r), "final_records")

    # Attach job if exists
    job_result = await db.execute(
        select(ServiceJob).where(ServiceJob.booking_id == booking.id)
    )
    job = job_result.scalars().first()

    data = booking.to_dict()
    data["job"] = job.to_dict() if job else None
    return ok(data, _RID(r), "final_records")


# ── GET /jobs/{job_id} ────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}", summary="Get a service job", response_model=ApiResponse)
async def get_my_job(
    job_id: uuid.UUID,
    r:      Request,
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    result = await db.execute(select(ServiceJob).where(ServiceJob.id == job_id))
    job = result.scalars().first()
    if not job:
        return ok({"error": "FINAL_JOB_NOT_FOUND"}, _RID(r), "final_records")
    if job.customer_id and job.customer_id != customer_id:
        return ok({"error": ERR_ACCESS_DENIED}, _RID(r), "final_records")
    return ok(job.to_dict(), _RID(r), "final_records")


# ── GET /appointments ─────────────────────────────────────────────────────────

@router.get("/appointments", summary="List my coaching appointments", response_model=ApiResponse)
async def list_my_appointments(
    r:      Request,
    status: str | None = Query(None),
    limit:  int        = Query(20, ge=1, le=100),
    offset: int        = Query(0, ge=0),
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    q = select(CoachingAppointment).where(CoachingAppointment.customer_id == customer_id)
    if status:
        q = q.where(CoachingAppointment.status == status)
    q = q.order_by(CoachingAppointment.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    rows   = result.scalars().all()

    total_q = select(func.count()).where(CoachingAppointment.customer_id == customer_id)
    if status:
        total_q = total_q.where(CoachingAppointment.status == status)
    total = await db.scalar(total_q)

    return ok({
        "items":  [a.to_dict() for a in rows],
        "total":  total,
        "limit":  limit,
        "offset": offset,
    }, _RID(r), "final_records")


# ── GET /appointments/{appointment_id} ────────────────────────────────────────

@router.get("/appointments/{appointment_id}", summary="Get a coaching appointment",
            response_model=ApiResponse)
async def get_my_appointment(
    appointment_id: uuid.UUID,
    r:              Request,
    user:           UserContext  = Depends(get_current_user),
    db:             AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    result = await db.execute(
        select(CoachingAppointment).where(CoachingAppointment.id == appointment_id)
    )
    appt = result.scalars().first()
    if not appt:
        return ok({"error": "FINAL_APPOINTMENT_NOT_FOUND"}, _RID(r), "final_records")
    if appt.customer_id and appt.customer_id != customer_id:
        return ok({"error": ERR_ACCESS_DENIED}, _RID(r), "final_records")
    return ok(appt.to_dict(), _RID(r), "final_records")


# ── GET /leads ────────────────────────────────────────────────────────────────

@router.get("/leads", summary="List my real estate leads", response_model=ApiResponse)
async def list_my_leads(
    r:      Request,
    status: str | None = Query(None),
    limit:  int        = Query(20, ge=1, le=100),
    offset: int        = Query(0, ge=0),
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    q = select(RealEstateLead).where(RealEstateLead.customer_id == customer_id)
    if status:
        q = q.where(RealEstateLead.status == status)
    q = q.order_by(RealEstateLead.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    rows   = result.scalars().all()

    total_q = select(func.count()).where(RealEstateLead.customer_id == customer_id)
    if status:
        total_q = total_q.where(RealEstateLead.status == status)
    total = await db.scalar(total_q)

    return ok({
        "items":  [l.to_dict() for l in rows],
        "total":  total,
        "limit":  limit,
        "offset": offset,
    }, _RID(r), "final_records")


# ── GET /leads/{lead_id} ──────────────────────────────────────────────────────

@router.get("/leads/{lead_id}", summary="Get a real estate lead", response_model=ApiResponse)
async def get_my_lead(
    lead_id: uuid.UUID,
    r:       Request,
    user:    UserContext  = Depends(get_current_user),
    db:      AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    result = await db.execute(select(RealEstateLead).where(RealEstateLead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        return ok({"error": "FINAL_LEAD_NOT_FOUND"}, _RID(r), "final_records")
    if lead.customer_id and lead.customer_id != customer_id:
        return ok({"error": ERR_ACCESS_DENIED}, _RID(r), "final_records")
    return ok(lead.to_dict(), _RID(r), "final_records")
