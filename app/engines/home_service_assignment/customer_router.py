"""Sprint 20 — Customer Booking Tracking APIs (assignment-aware)."""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok

router = APIRouter(
    prefix="/v1/customer/bookings",
    tags=["Customer Booking Tracking"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")

# Customer-safe assignment status display messages
_ASSIGNMENT_DISPLAY = {
    "unassigned": "Provider is assigning a technician.",
    "assigned":   "Technician assigned.",
    "accepted":   "Technician accepted your booking.",
    "rejected":   "Provider is assigning another technician.",
    "cancelled":  "Provider is assigning a technician.",
    "reassigned": "Provider updated the technician assignment.",
}


# HS7 — customer-safe fields lifted from a provider snapshot; never leaks
# internal_score, matching_score_snapshot, admin price range, etc.
def _customer_safe_provider(snapshot: dict | None) -> dict | None:
    if not snapshot:
        return None
    return {
        "provider_name":  snapshot.get("provider_name"),
        "rating":         snapshot.get("rating"),
        "public_badges":  snapshot.get("public_badges", []),
    }


@router.get("", response_model=ApiResponse,
            summary="List my Home Services bookings")
async def list_bookings(
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    from app.engines.final_records.models import ServiceBooking

    customer_id = uuid.UUID(user.user_id)
    res = await db.execute(
        select(ServiceBooking)
        .where(ServiceBooking.customer_id == customer_id)
        .order_by(ServiceBooking.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    bookings = res.scalars().all()
    items = [
        {
            "booking_id":           str(b.id),
            "booking_number":       b.booking_number,
            "status":               b.status,
            "issue_summary":        b.issue_summary,
            "city":                 b.city,
            "preferred_date":       b.preferred_date.isoformat() if b.preferred_date else None,
            "selected_provider":    _customer_safe_provider(b.provider_snapshot),
            "selected_price_option": (b.price_snapshot or {}).get("selected_price_option"),
            "selected_price_amount": (b.price_snapshot or {}).get("selected_price_amount"),
        }
        for b in bookings
    ]
    return ok({"items": items, "page": page, "page_size": page_size}, _RID(r), "assignment")


@router.get("/{booking_id}", response_model=ApiResponse,
            summary="Get customer booking with assignment status")
async def get_booking(
    booking_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    from app.engines.final_records.models import ServiceBooking, ServiceJob
    customer_id = uuid.UUID(user.user_id)

    res = await db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
    booking = res.scalars().first()
    if not booking or str(booking.customer_id) != str(customer_id):
        return ok({"success": False, "error": {"code": "BOOKING_NOT_FOUND",
                   "message": "Booking not found."}}, _RID(r), "assignment")

    res2 = await db.execute(select(ServiceJob).where(ServiceJob.booking_id == booking.id))
    job = res2.scalars().first()

    assignment_status = booking.assignment_status or "unassigned"
    display_message = _ASSIGNMENT_DISPLAY.get(assignment_status, "")

    price_snapshot = booking.price_snapshot or {}
    data = {
        "booking_id":             str(booking.id),
        "booking_number":         booking.booking_number,
        "status":                 booking.status,
        "assignment_status":      assignment_status,
        "assignment_message":     display_message,
        "preferred_date":         booking.preferred_date.isoformat() if booking.preferred_date else None,
        "preferred_time_window":  booking.preferred_time_window,
        "city":                   booking.city,
        "address":                booking.address_snapshot,
        "issue_summary":          booking.issue_summary,
        "selected_provider":      _customer_safe_provider(booking.provider_snapshot),
        "selected_price_option":  price_snapshot.get("selected_price_option"),
        "selected_price_amount":  price_snapshot.get("selected_price_amount"),
        "payment_mode":           price_snapshot.get("payment_mode", "customer_pays_provider_directly"),
    }
    if job:
        # MODULE-L5-16: expose job_id so the app can reach the job's work quotes
        # (customer quote approval) — it was loaded here but never returned.
        data["job_id"]                = str(job.id)
        data["job_status"]            = job.status
        data["scheduled_date"]        = job.scheduled_date.isoformat() if job.scheduled_date else None
        data["scheduled_time_window"] = job.scheduled_time_window

        # No weather advisory here, by product decision: the weather API is called
        # only when a provider or staff member picks weather as a reschedule reason.
        # This endpoint is polled while a customer watches a booking, so an advisory
        # here would have been the bulk of all weather calls -- and when conditions
        # really are bad, the provider moving the slot is what the customer is told
        # about, through the reschedule notification that already exists.

    return ok(data, _RID(r), "assignment")


@router.get("/{booking_id}/tracking", response_model=ApiResponse,
            summary="Get customer-safe booking tracking timeline")
async def get_booking_tracking(
    booking_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    from app.engines.final_records.models import ServiceBooking, ServiceJob
    from app.engines.home_service_assignment.models import ServiceJobAssignmentEvent
    customer_id = uuid.UUID(user.user_id)

    res = await db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
    booking = res.scalars().first()
    if not booking or str(booking.customer_id) != str(customer_id):
        return ok({"success": False, "error": {"code": "BOOKING_NOT_FOUND",
                   "message": "Booking not found."}}, _RID(r), "assignment")

    res2 = await db.execute(select(ServiceJob).where(ServiceJob.booking_id == booking.id))
    job = res2.scalars().first()

    # Build customer-safe timeline from assignment events
    dated_events: list[dict] = []

    if job:
        res3 = await db.execute(
            select(ServiceJobAssignmentEvent)
            .where(ServiceJobAssignmentEvent.job_id == job.id)
            .order_by(ServiceJobAssignmentEvent.created_at)
        )
        for ev in res3.scalars().all():
            label = _safe_event_label(ev.event_type)
            if label:
                dated_events.append({
                    "event":      label,
                    "event_type": ev.event_type,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                    "_sort_key":  ev.created_at,
                })

        # TRACK-TECHNICIAN: the execution engine's on_the_way/reached_site
        # transitions are real, server-enforced ServiceJob.status changes,
        # but they're logged to a SEPARATE table (ServiceJobExecutionEvent,
        # not ServiceJobAssignmentEvent) — the timeline above silently
        # dropped them because _safe_event_label had no entries for them.
        # Merge them in for real rather than inventing status copy.
        from app.engines.execution.models import ServiceJobExecutionEvent
        res4 = await db.execute(
            select(ServiceJobExecutionEvent)
            .where(ServiceJobExecutionEvent.job_id == job.id)
            .order_by(ServiceJobExecutionEvent.created_at)
        )
        for ev in res4.scalars().all():
            label = _safe_execution_event_label(ev.event_type)
            if label:
                dated_events.append({
                    "event":      label,
                    "event_type": ev.event_type,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                    "_sort_key":  ev.created_at,
                })

    dated_events.sort(key=lambda e: e["_sort_key"] or _dt_min())
    for e in dated_events:
        e.pop("_sort_key", None)

    timeline = [{"event": "Booking confirmed", "status": "confirmed"}, *dated_events]

    assignment_status = booking.assignment_status or "unassigned"
    return ok({
        "booking_number":     booking.booking_number,
        "status":             booking.status,
        "assignment_status":  assignment_status,
        "assignment_message": _ASSIGNMENT_DISPLAY.get(assignment_status, ""),
        "timeline":           timeline,
    }, _RID(r), "assignment")


@router.get("/{booking_id}/tracking-location", response_model=ApiResponse,
            summary="Real-time technician location for an active visit, when available")
async def get_booking_tracking_location(
    booking_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Returns {available: false, reason: ...} whenever the job isn't in an
    active-tracking status or no location has been submitted yet — never a
    stale/fabricated position. Coordinates/timestamp/technician identity are
    all backend-authoritative (see HomeServiceJobAssignmentService.
    get_customer_tracking_location); this route only handles ownership
    enumeration-safety and error-code mapping."""
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    try:
        result = await HomeServiceJobAssignmentService(db).get_customer_tracking_location(
            booking_id=booking_id, customer_id=uuid.UUID(user.user_id),
        )
    except ValueError as exc:
        _cancel_reschedule_error(exc)
    return ok(result, _RID(r), "assignment")


def _safe_event_label(event_type: str) -> str | None:
    """Map internal event types to customer-safe display labels."""
    _map = {
        "job_received":           "Provider received your booking.",
        "assignment_created":     "Technician assigned.",
        "assignment_reassigned":  "Technician updated.",
        "assignment_cancelled":   "Provider is finding a technician.",
        "technician_accepted":    "Technician accepted your booking.",
        "technician_rejected":    "Provider is finding another technician.",
        "job_scheduled":          "Visit scheduled.",
    }
    return _map.get(event_type)


def _safe_execution_event_label(event_type: str) -> str | None:
    """Customer-safe labels for the execution engine's real, server-enforced
    job-progress transitions (separate table from assignment events)."""
    _map = {
        "technician_on_the_way":   "Technician is on the way.",
        "technician_reached_site": "Technician has arrived.",
    }
    return _map.get(event_type)


def _dt_min():
    import datetime as _dt
    return _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)


# ── HS9B — customer rating/review, wraps the real Review Engine ──────────────

@router.post("/{booking_id}/rating", response_model=ApiResponse)
async def submit_booking_rating(
    booking_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    # MODULE-L5-13: the booking rating used to write to the LEGACY review engine
    # (`reviews` table), which the provider/admin review dashboards and the rating
    # aggregation (tenant_rating_summaries / staff_rating_summaries — the source of
    # trust_quality's average_rating) never read. Customer ratings therefore never
    # reached the provider, the aggregates, or health scoring. This now submits
    # through the real customer_reviews engine, which records the review AND
    # recomputes the tenant/staff summaries the dashboards and health read.
    from app.exceptions import ServiceOSException
    from app.engines.final_records.models import ServiceBooking
    from app.engines.customer_reviews.review_service import ReviewService

    customer_id = uuid.UUID(user.user_id)
    body = await r.json() if r.headers.get("content-length", "0") != "0" else {}

    res = await db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
    booking = res.scalars().first()
    if not booking or str(booking.customer_id) != str(customer_id):
        raise ServiceOSException("BOOKING_NOT_FOUND", "Booking not found.", status_code=404)

    rating = body.get("rating")
    if rating is None or not (1 <= int(rating) <= 5):
        raise ServiceOSException("RATING_REQUIRED", "Rating must be between 1 and 5.", status_code=422)

    # The engine's eligibility check owns the "completed"/"already reviewed" rules;
    # map its domain ValueErrors back to the codes/messages the app expects.
    # WORK-IN-PROGRESS-COMPLETION-RATING phase -- `review_tags` was already
    # a real, accepted parameter on `ReviewService.submit_review` (JSONB
    # column, no backend enum constraint) but this router never forwarded
    # it, so a customer's selected tags (e.g. "Professional", "On time")
    # were silently dropped. `tags` must be a list of strings if present.
    tags = body.get("tags")
    if tags is not None and not isinstance(tags, list):
        raise ServiceOSException("VALIDATION_ERROR", "tags must be a list of strings.", status_code=422)

    try:
        review = await ReviewService().submit_review(
            db, customer_id=customer_id, tenant_id=booking.tenant_id,
            record_type="service_booking", record_id=booking_id,
            overall_rating=int(rating), review_text=body.get("comment"),
            review_tags=tags, request_id=_RID(r),
        )
    except ValueError as exc:
        code = str(exc)
        if code == "REVIEW_ALREADY_EXISTS":
            raise ServiceOSException("REVIEW_ALREADY_SUBMITTED",
                                     "A review has already been submitted for this booking.",
                                     status_code=409)
        if code == "REVIEW_NOT_ELIGIBLE":
            raise ServiceOSException("BOOKING_NOT_COMPLETED",
                                     "You can review this service after it is completed.",
                                     status_code=422)
        status = 404 if code == "RECORD_NOT_FOUND" else 422
        raise ServiceOSException(code, code.replace("_", " ").title(), status_code=status)
    # WORK-IN-PROGRESS-COMPLETION-RATING phase -- this previously returned
    # `review.to_dict()` verbatim, leaking customer_id/tenant_id/
    # staff_member_id and every sub-rating column straight to the customer
    # app. Allow-listed to the same shape `get_booking_rating` already
    # returns, now with `tags` included.
    return ok({
        "review": {
            "rating":  review.overall_rating,
            "comment": review.review_text,
            "tags":    review.review_tags,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        },
    }, _RID(r), "assignment")


@router.get("/{booking_id}/rating", response_model=ApiResponse)
async def get_booking_rating(
    booking_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    # MODULE-L5-13: read the review back from the same customer_reviews engine the
    # rating now writes to (was reading the orphaned legacy `reviews` table).
    from app.engines.customer_reviews.models import CustomerReview

    customer_id = uuid.UUID(user.user_id)
    review = (await db.execute(
        select(CustomerReview).where(
            CustomerReview.customer_id == customer_id,
            CustomerReview.booking_id == booking_id,
        )
    )).scalars().first()
    if not review:
        return ok({"review": None}, _RID(r), "assignment")

    return ok({
        "review": {
            "rating": review.overall_rating,
            "comment": review.review_text,
            "tags": review.review_tags,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        },
    }, _RID(r), "assignment")


# MODULE-L5-29: a customer had no way to cancel or reschedule a CONFIRMED
# booking at all — only a pre-confirmation draft could be cancelled. Once a
# booking existed, the only escape hatch was an admin force-void. These wire
# the real, already-existing cancellable-status guard in the assignment engine.

def _cancel_reschedule_error(exc: ValueError):
    from app.exceptions import ServiceOSException
    code = str(exc)
    status_map = {
        "JOB_ASSIGNMENT_BOOKING_NOT_FOUND": 404,
        "JOB_ASSIGNMENT_JOB_NOT_FOUND": 404,
        "JOB_ASSIGNMENT_ACCESS_DENIED": 403,
        "JOB_ASSIGNMENT_REASON_REQUIRED": 422,
        "JOB_ASSIGNMENT_INVALID_REASON": 422,
        "JOB_ASSIGNMENT_PAST_DATE": 422,
        "JOB_ASSIGNMENT_CANCEL_NOT_ALLOWED": 409,
        "JOB_ASSIGNMENT_RESCHEDULE_NOT_ALLOWED": 409,
        "JOB_ASSIGNMENT_RESCHEDULE_LIMIT_REACHED": 409,
        "JOB_ASSIGNMENT_STALE_VERSION": 409,
        "JOB_ASSIGNMENT_SLOT_UNAVAILABLE": 409,
    }
    raise ServiceOSException(code, code.replace("_", " ").title(),
                             status_code=status_map.get(code, 422))


@router.get("/{booking_id}/cancel-reschedule-eligibility", response_model=ApiResponse,
            summary="Check whether this booking can be cancelled/rescheduled")
async def get_cancel_reschedule_eligibility(
    booking_id: uuid.UUID,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    try:
        result = await HomeServiceJobAssignmentService(db).get_customer_eligibility(
            booking_id=booking_id, customer_id=uuid.UUID(user.user_id),
        )
    except ValueError as exc:
        _cancel_reschedule_error(exc)
    return ok(result, _RID(r), "assignment")


@router.get("/{booking_id}/reschedule-availability", response_model=ApiResponse,
            summary="Real day-level availability for the reschedule date picker")
async def get_reschedule_availability(
    booking_id: uuid.UUID,
    r:    Request      = ...,
    horizon_days: int = 14,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    try:
        result = await HomeServiceJobAssignmentService(db).get_reschedule_available_dates(
            booking_id=booking_id, customer_id=uuid.UUID(user.user_id),
            horizon_days=horizon_days,
        )
    except ValueError as exc:
        _cancel_reschedule_error(exc)
    return ok(result, _RID(r), "assignment")


@router.post("/{booking_id}/cancel", response_model=ApiResponse)
async def cancel_booking(
    booking_id: uuid.UUID,
    body: dict,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    try:
        result = await HomeServiceJobAssignmentService(db).customer_cancel_booking(
            booking_id=booking_id, customer_id=uuid.UUID(user.user_id),
            reason=body.get("reason", ""), detail=body.get("detail"),
            expected_version=body.get("expected_version"), request_id=_RID(r),
        )
    except ValueError as exc:
        _cancel_reschedule_error(exc)
    return ok(result, _RID(r), "assignment")


@router.post("/{booking_id}/reschedule", response_model=ApiResponse)
async def reschedule_booking(
    booking_id: uuid.UUID,
    body: dict,
    r:    Request      = ...,
    user: UserContext  = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    import datetime as _dt
    from app.exceptions import ServiceOSException
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    raw_date = body.get("scheduled_date")
    if not raw_date:
        raise ServiceOSException("VALIDATION_ERROR", "scheduled_date is required.", status_code=422)
    try:
        scheduled_date = _dt.date.fromisoformat(raw_date)
    except ValueError:
        raise ServiceOSException("VALIDATION_ERROR", "scheduled_date must be YYYY-MM-DD.", status_code=422)

    try:
        result = await HomeServiceJobAssignmentService(db).customer_reschedule_booking(
            booking_id=booking_id, customer_id=uuid.UUID(user.user_id),
            scheduled_date=scheduled_date,
            scheduled_time_window=body.get("scheduled_time_window"),
            reason=body.get("reason", ""),
            expected_version=body.get("expected_version"), request_id=_RID(r),
        )
    except ValueError as exc:
        _cancel_reschedule_error(exc)
    return ok(result, _RID(r), "assignment")
