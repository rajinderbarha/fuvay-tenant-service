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
from app.engines.final_records.bookings_jobs_stage_mapping import map_job_status
from app.engines.home_service_assignment.staff_model import ProviderTeamMember
from app.exceptions import ServiceOSException

router = APIRouter(
    prefix="/v1/customer/my-activity",
    tags=["Customer My Activity"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")


# ACTIVE-BOOKING-DETAILS phase — customer-safe projection of a ServiceJob.
# The previous code returned `job.to_dict()` verbatim, which leaked
# `assigned_staff_id` (a raw internal `users.id`), `tenant_id`, `category_id`,
# `offering_id`, every workflow/job-type id, and `completion_data` straight to
# the customer app. This allow-lists exactly the fields a customer may see and
# resolves the technician's PUBLIC display identity via `ProviderTeamMember`
# (never the raw staff/user id), scoped to the job's own tenant so a staff row
# from another tenant can never be joined in by id collision.
async def _customer_safe_job(db: AsyncSession, job: ServiceJob) -> dict:
    technician = None
    if job.assigned_staff_id and job.tenant_id:
        staff = await db.scalar(
            select(ProviderTeamMember).where(
                ProviderTeamMember.user_id == job.assigned_staff_id,
                ProviderTeamMember.tenant_id == job.tenant_id,
            )
        )
        if staff:
            technician = {
                "display_name": staff.full_name,
                "designation":  staff.designation,
                "photo_url":    staff.profile_photo_url,
            }

    stage_info = map_job_status(job.status, job.assignment_status)

    # WORK-IN-PROGRESS-COMPLETION-RATING phase -- `job.completion_data` is
    # the SAME atomic record `complete_job()` writes (work_summary,
    # collected_amount, timestamps, photo/signature ids, staff id,
    # technician_note). Only the three customer-facing fields are exposed;
    # photo/signature ids, `completed_by_staff_id` and `technician_note`
    # are internal/operational and never leave this allow-list.
    completion = None
    if job.status == "completed" and job.completion_data:
        completion = {
            "work_summary":     job.completion_data.get("work_summary"),
            "collected_amount": job.completion_data.get("collected_amount"),
            "completed_at":     job.completion_data.get("completed_at"),
        }

    return {
        # ARRIVAL-INSPECTION-QUOTE-APPROVAL phase: the job's own id is not
        # sensitive (unlike assigned_staff_id/tenant_id/category_id, it
        # names no internal party) and is required by the customer app to
        # correlate this job with its own quote via
        # GET /v1/customer/quotes/jobs/{job_id}.
        "id":                    str(job.id),
        "status":                job.status,
        "assignment_status":     job.assignment_status,
        "stage":                 stage_info["stage"],
        "stage_label":           stage_info["stage_label"],
        "is_terminal":           stage_info["is_terminal"],
        "scheduled_date":        job.scheduled_date.isoformat() if job.scheduled_date else None,
        "scheduled_time_window": job.scheduled_time_window,
        "technician":            technician,
        "updated_at":            job.updated_at.isoformat() if job.updated_at else None,
        "completion":            completion,
    }


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


#: A booking never leaves these two states. Everything else -- including
#: `accepted`/`assigned`/`on_the_way` -- is still ACTIVE for grouping: an
#: in-progress job is not a finished one. Mirrors the customer app's own
#: `TERMINAL_BOOKING_STATUSES` so both sides group identically.
_TERMINAL_BOOKING_STATUSES = ("completed", "cancelled")


# ── GET /bookings ─────────────────────────────────────────────────────────────

@router.get("/bookings", summary="List my service bookings", response_model=ApiResponse)
async def list_my_bookings(
    r:      Request,
    bucket: str | None = Query(None, description="active | completed | all"),
    status: str | None = Query(None),
    limit:  int        = Query(20, ge=1, le=100),
    offset: int        = Query(0, ge=0),
    user:   UserContext  = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    """My Bookings.

    Real bug fixed here -- this endpoint broke the customer's My Bookings
    screen outright:

      * The response had no `counts`, but the app's contract requires it
        (it drives the tab counts and is declared non-optional). The
        client's schema parse therefore FAILED on every load, which the UI
        surfaced as "We couldn't load your bookings. Try again." -- the
        list was unreachable even though the data was fine.
      * The app filters by `bucket` (active/completed/all); this endpoint
        only ever accepted `status` and ignored `bucket` entirely, so the
        tabs did nothing.
      * Ordering was `created_at DESC` alone, which is not deterministic
        for rows sharing a timestamp -- an item could repeat or vanish
        across pages. `id DESC` breaks the tie.

    `counts` is deliberately computed for ALL THREE buckets regardless of
    which one was requested: the tabs must show real totals, and a count
    derived from a paginated fetch of one bucket would be wrong.
    """
    customer_id = uuid.UUID(user.user_id)
    mine = ServiceBooking.customer_id == customer_id

    def _bucket_filter(q, which: str | None):
        if which == "active":
            return q.where(ServiceBooking.status.notin_(_TERMINAL_BOOKING_STATUSES))
        if which == "completed":
            return q.where(ServiceBooking.status == "completed")
        return q  # "all" / unset

    q = select(ServiceBooking).where(mine)
    q = _bucket_filter(q, bucket)
    # `status` remains supported for any caller that filters on one exact
    # raw status; it narrows further rather than replacing the bucket.
    if status:
        q = q.where(ServiceBooking.status == status)
    q = q.order_by(ServiceBooking.created_at.desc(), ServiceBooking.id.desc())
    rows = (await db.execute(q.limit(limit).offset(offset))).scalars().all()

    total_q = _bucket_filter(select(func.count()).where(mine), bucket)
    if status:
        total_q = total_q.where(ServiceBooking.status == status)
    total = await db.scalar(total_q)

    all_count = await db.scalar(select(func.count()).where(mine))
    completed_count = await db.scalar(
        select(func.count()).where(mine, ServiceBooking.status == "completed")
    )
    active_count = await db.scalar(
        select(func.count()).where(mine, ServiceBooking.status.notin_(_TERMINAL_BOOKING_STATUSES))
    )

    return ok({
        "items":  [b.to_dict() for b in rows],
        "total":  total or 0,
        "counts": {
            "active":    active_count or 0,
            "completed": completed_count or 0,
            "all":       all_count or 0,
        },
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
    # Booking Details Pending Assignment audit: a missing booking and one
    # owned by a different customer previously returned two distinguishable
    # HTTP-200 `{"error": ...}` payloads instead of a real 404 -- both a
    # wrong status code (the frontend's `getMyBooking` already expects a
    # real 404 per contracts/customerBookings.ts) and a cross-customer
    # enumeration leak (the two error strings differed). Both cases now
    # raise the identical enumeration-safe NOT_FOUND.
    if not booking or (booking.customer_id and booking.customer_id != customer_id):
        raise ServiceOSException("BOOKING_NOT_FOUND", "Booking not found", status_code=404)

    # Attach job if exists
    job_result = await db.execute(
        select(ServiceJob).where(ServiceJob.booking_id == booking.id)
    )
    job = job_result.scalars().first()

    data = booking.to_dict()
    data["job"] = await _customer_safe_job(db, job) if job else None
    data.update(await _catalog_labels(db, booking))
    return ok(data, _RID(r), "final_records")


async def _catalog_labels(db: AsyncSession, booking: ServiceBooking) -> dict:
    """Human-readable names for the catalog ids stored on a booking.

    Real bug fixed here: the customer app's booking-detail contract has
    always declared `offering_name` / `category_name` / `job_type_label` as
    "enriched server-side by get_my_booking", and the app renders the
    service name from exactly those fields -- but nothing ever added them,
    so every booking's detail page showed a blank service name. Tests for
    this enrichment already existed (test_level5_booking_confirmation_
    receipt.py); only the implementation was missing.

    Resolved by primary key at read time rather than snapshotted: these are
    display labels only, and the booking's real commitments are already
    frozen in price_snapshot/answer_snapshot.

    A key is OMITTED rather than set to None when its catalog row is gone,
    which is what the contract's `.optional()` fields mean and what the
    enrichment tests assert -- a present-but-null name would make the client
    render an empty label instead of falling back to the next best one.
    """
    from app.engines.admin_catalog.models import MasterService, ServiceCategory, JobTypeDefinition

    out: dict = {}

    offering = await db.get(MasterService, booking.offering_id) if booking.offering_id else None
    if offering is not None:
        out["offering_name"] = offering.service_name

    category = await db.get(ServiceCategory, booking.category_id) if booking.category_id else None
    if category is not None:
        out["category_name"] = category.name

    job_type = await db.get(JobTypeDefinition, booking.job_type_id) if booking.job_type_id else None
    if job_type is not None:
        out["job_type_label"] = job_type.label

    return out


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
