"""Booking Engine — Router (21 endpoints). Zero inline imports. Zero business logic."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.booking.service import BookingService
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, Links, Link, ok

logger = structlog.get_logger("booking.router")
router = APIRouter(prefix="/v1/bookings", tags=["Booking Engine"])
ENGINE_ID = "booking"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> BookingService:
    return BookingService(
        db=db, request_id=getattr(r.state, "request_id", "—"),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role,
        actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None,
    )
def _rid(r): return getattr(r.state, "request_id", "—")


@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Booking Engine", "version": "10.0.0",
            "endpoint_count": 21, "status": "active",
            "capabilities": ["idempotent_creation","price_snapshot_lock","5_check_preflight",
                             "atomic_cancellation","reschedule_flow","booking_to_job_conversion",
                             "immutable_timeline","hateoas_transitions","cursor_pagination",
                             "serviceability_preflight","server_side_tenant_matching",
                             "pending_confirmation_flow"]}


# ── Step 4: Booking preflight ─────────────────────────────────────────────────
@router.post("/preflight",
             summary="Step 4: Booking preflight — serviceability + pricing + SLA check",
             tags=["Booking Preflight"],
             response_model=ApiResponse[dict])
async def booking_preflight(r: Request,
                             u: UserContext = Depends(require_permission(P.BOOKING_CREATE)),
                             s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    """
    Run pre-booking checks: service available at address, best tenant match,
    pricing estimate, SLA. Frontend must call this before POST /v1/bookings.
    Returns can_book + matched_tenant_id + estimated_price + sla_minutes.
    """
    body = await r.json()
    if not body.get("service_id"):
        raise ServiceOSException("VALIDATION_ERROR", "service_id is required.", status_code=422)
    if not body.get("job_type"):
        raise ServiceOSException("VALIDATION_ERROR", "job_type is required.", status_code=422)

    customer_id = uuid.UUID(u.user_id) if u.role == "customer" else None
    data = await s.run_booking_preflight(
        address_id=body.get("address_id"),
        city=body.get("city"),
        state=body.get("state"),
        zipcode=body.get("zipcode"),
        service_id=body["service_id"],
        job_type=body["job_type"],
        scheduled_at=body.get("scheduled_at"),
        customer_id=customer_id,
    )
    return ok(data, _rid(r), ENGINE_ID)


# ── Step 4: Create booking ────────────────────────────────────────────────────
@router.post("",
             summary="Step 4: Create booking — server-side serviceability match, status=pending_confirmation",
             status_code=status.HTTP_201_CREATED,
             tags=["Booking Engine"],
             response_model=ApiResponse[dict])
async def create_booking(r: Request,
                          u: UserContext = Depends(require_permission(P.BOOKING_CREATE)),
                          s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    """
    Creates a booking with server-side serviceability re-match.
    Frontend MUST NOT send tenant_id — the backend selects the best tenant.
    Status starts as pending_confirmation.
    """
    body = await r.json()
    if body.get("tenant_id"):
        raise ServiceOSException("FRONTEND_TENANT_ID_NOT_ALLOWED",
            "tenant_id cannot be specified by the client. "
            "The system auto-selects the best provider via serviceability matching.",
            status_code=400)

    customer_id = uuid.UUID(u.user_id) if u.role == "customer" else (
        uuid.UUID(body["customer_id"]) if body.get("customer_id") else None
    )
    if not customer_id:
        raise ServiceOSException("VALIDATION_ERROR", "customer_id is required.", status_code=422)

    data = await s.create_booking(
        customer_id=customer_id,
        address_id=uuid.UUID(body["address_id"]) if body.get("address_id") else None,
        service_id=uuid.UUID(body["service_id"]) if body.get("service_id") else None,
        job_type=body.get("job_type"),
        scheduled_at=body.get("scheduled_at"),
        customer_notes=body.get("notes") or body.get("customer_notes"),
        tags=body.get("tags", []),
        address=body.get("address", {}),
        preferred_date=body.get("preferred_date"),
        preferred_slot=body.get("preferred_slot"),
    )
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(actions=[
                  Link(href=f"/v1/bookings/{data['booking_id']}", method="GET", rel="self"),
                  Link(href=f"/v1/bookings/{data['booking_id']}/cancel", method="POST", rel="cancel"),
              ]))


# ── Step 4: Get booking ────────────────────────────────────────────────────────
@router.get("/{booking_id}",
            summary="Step 4: Get booking — tenant_owner sees own tenant, customer sees own",
            response_model=ApiResponse[dict])
async def get_booking(booking_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_permission(P.BOOKING_READ)),
                       s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    data = await s.get_booking(booking_id)
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(
                  self_link=f"/v1/bookings/{booking_id}",
                  actions=[Link(href=f"/v1/bookings/{booking_id}/timeline",
                                method="GET", rel="timeline"),
                           Link(href=f"/v1/bookings/{booking_id}/cancel",
                                method="POST", rel="cancel")]))


# ── Step 4: List bookings — unified, role-scoped ──────────────────────────────
@router.get("",
            summary="Step 4: List bookings — customer sees own, tenant_owner sees tenant, super_admin sees all",
            response_model=ApiResponse[dict])
async def list_bookings(r: Request,
                         booking_status: str | None = Query(None, alias="status"),
                         limit: int = Query(50, ge=1, le=200),
                         cursor: str | None = Query(None),
                         tenant_id: uuid.UUID | None = Query(None),
                         customer_id: uuid.UUID | None = Query(None),
                         u: UserContext = Depends(require_permission(P.BOOKING_READ)),
                         s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(
        await s.list_bookings(
            status=booking_status, limit=limit, cursor=cursor,
            tenant_id=tenant_id, customer_id=customer_id),
        _rid(r), ENGINE_ID)


# ── Step 4: Cancel booking ─────────────────────────────────────────────────────
@router.post("/{booking_id}/cancel",
             summary="Step 4: Cancel booking — customer cancels own, tenant_owner cancels tenant's",
             response_model=ApiResponse[dict])
async def cancel_booking(booking_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_permission(P.BOOKING_CANCEL)),
                          s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.cancel_booking(booking_id, body.get("reason", "Customer request")),
              _rid(r), ENGINE_ID)


# ── Legacy / unchanged endpoints ──────────────────────────────────────────────

@router.get("/customers/{customer_id}", summary="List bookings by customer",
            response_model=ApiResponse[dict])
async def list_by_customer(customer_id: uuid.UUID, r: Request,
                            tenant_id: uuid.UUID | None = Query(None),
                            limit: int = Query(50, ge=1, le=200),
                            cursor: str | None = Query(None),
                            u: UserContext = Depends(get_current_user),
                            s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_by_customer(customer_id, tenant_id, limit, cursor), _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id_param}", summary="List bookings by tenant (legacy)",
            response_model=ApiResponse[dict])
async def list_by_tenant(tenant_id_param: uuid.UUID, r: Request,
                          booking_status: str | None = Query(None, alias="status"),
                          limit: int = Query(50, ge=1, le=200),
                          cursor: str | None = Query(None),
                          u: UserContext = Depends(get_current_user),
                          s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_by_tenant(tenant_id_param, booking_status, limit, cursor),
              _rid(r), ENGINE_ID)


@router.post("/{booking_id}/confirm",
             summary="Step 5: Confirm pending_confirmation booking — tenant_owner only",
             response_model=ApiResponse[dict])
async def confirm_booking(booking_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_permission(P.BOOKING_MANAGE)),
                           s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.confirm_booking(booking_id, body.get("scheduled_at"))
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(actions=[
                  Link(href=f"/v1/bookings/{booking_id}/convert-to-job",
                       method="POST", rel="convert_to_job"),
                  Link(href=f"/v1/bookings/{booking_id}/reject",
                       method="POST", rel="reject"),
              ]))


@router.post("/{booking_id}/reject",
             summary="Step 5: Reject pending_confirmation booking — tenant_owner only, reason required",
             response_model=ApiResponse[dict])
async def reject_booking(booking_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_permission(P.BOOKING_MANAGE)),
                          s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    if not body.get("reason"):
        from app.exceptions import ServiceOSException
        raise ServiceOSException("BOOKING_REJECTION_REASON_REQUIRED",
            "reason is required in the request body.", status_code=422)
    data = await s.reject_booking(booking_id, body["reason"])
    return ok(data, _rid(r), ENGINE_ID)


@router.post("/{booking_id}/convert-to-job",
             summary="Step 5: Convert confirmed booking to Field Ops job — tenant_owner only",
             response_model=ApiResponse[dict])
async def convert_to_job(booking_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_permission(P.BOOKING_MANAGE)),
                          s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    assigned_staff_id = (uuid.UUID(body["assigned_staff_id"])
                         if body.get("assigned_staff_id") else None)
    data = await s.convert_to_job(
        booking_id,
        assignment_mode=body.get("assignment_mode", "manual"),
        assigned_staff_id=assigned_staff_id,
        notes=body.get("notes"),
    )
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(actions=[Link(href=f"/v1/jobs/{data.get('job_id')}",
                                        method="GET", rel="job")]))


@router.post("/{booking_id}/reschedule/request",
             summary="Request reschedule — notifies tenant for approval",
             response_model=ApiResponse[dict])
async def request_reschedule(booking_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(require_permission(P.BOOKING_RESCHEDULE)),
                              s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    # MODULE-L5-02 bug #26: raw body["requested_date"]/["requested_slot"] access
    # raised KeyError -> 500 when a field was missing. Validate to a clean 422.
    missing = [f for f in ("requested_date", "requested_slot") if not body.get(f)]
    if missing:
        raise ServiceOSException("RESCHEDULE_FIELDS_REQUIRED",
            f"Missing required field(s): {', '.join(missing)}.", status_code=422,
            context={"missing": missing})
    return ok(await s.request_reschedule(booking_id, body["requested_date"],
              body["requested_slot"], body.get("reason")), _rid(r), ENGINE_ID)


@router.post("/reschedule/{reschedule_id}/accept",
             summary="Tenant accepts reschedule request",
             response_model=ApiResponse[dict])
async def accept_reschedule(reschedule_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                             s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.accept_reschedule(reschedule_id), _rid(r), ENGINE_ID)


@router.post("/reschedule/{reschedule_id}/reject",
             summary="Tenant rejects reschedule request",
             response_model=ApiResponse[dict])
async def reject_reschedule(reschedule_id: uuid.UUID, r: Request,
                             u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                             s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.reject_reschedule(reschedule_id, body.get("reason", "Slot unavailable")),
              _rid(r), ENGINE_ID)


@router.get("/{booking_id}/timeline",
            summary="Full immutable booking status history",
            response_model=ApiResponse[dict])
async def get_timeline(booking_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_timeline(booking_id), _rid(r), ENGINE_ID)


@router.post("/{booking_id}/notes", status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def add_note(booking_id: uuid.UUID, r: Request,
                    u: UserContext = Depends(get_current_user),
                    s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.add_note(booking_id, body["content"], body.get("is_internal", True)),
              _rid(r), ENGINE_ID)


@router.get("/{booking_id}/notes", response_model=ApiResponse[dict])
async def list_notes(booking_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_notes(booking_id), _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id_param}/slots/check",
            summary="Check slot availability for a date and time slot",
            response_model=ApiResponse[dict])
async def check_slots(tenant_id_param: uuid.UUID, r: Request,
                       date: str = Query(...), slot: str = Query(...),
                       u: UserContext = Depends(get_current_user),
                       s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.check_slot_availability(tenant_id_param, date, slot), _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id_param}/cancellation-policy",
            summary="Get tenant cancellation policy and reschedule limits",
            response_model=ApiResponse[dict])
async def cancellation_policy(tenant_id_param: uuid.UUID, r: Request,
                               u: UserContext = Depends(get_current_user),
                               s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_cancellation_policy(tenant_id_param), _rid(r), ENGINE_ID)


@router.post("/{booking_id}/void",
             summary="Void booking (admin only — not a cancellation)",
             response_model=ApiResponse[dict])
async def void_booking(booking_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.void_booking(booking_id, body.get("reason", "Voided by admin")),
              _rid(r), ENGINE_ID)


@router.get("/tenants/{tenant_id_param}/search",
            summary="Search bookings by booking number", response_model=ApiResponse[dict])
async def search(tenant_id_param: uuid.UUID, r: Request,
                  q_str: str = Query(..., alias="q"),
                  limit: int = Query(20, ge=1, le=50),
                  u: UserContext = Depends(get_current_user),
                  s: BookingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.search_bookings(tenant_id_param, q_str, limit), _rid(r), ENGINE_ID)
