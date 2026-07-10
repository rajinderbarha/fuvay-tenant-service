"""Appointment Engine — Router (15 endpoints). Zero inline imports."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.appointment.service import AppointmentService
from app.schemas.base import ApiResponse, Links, Link, ok

logger = structlog.get_logger("appointment.router")
router = APIRouter(prefix="/v1/appointments", tags=["Appointment Engine"])
ENGINE_ID = "appointment"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> AppointmentService:
    return AppointmentService(db=db, request_id=getattr(r.state,"request_id","—"),
                               actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                               actor_role=u.role)
def _rid(r): return getattr(r.state,"request_id","—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Appointment Engine", "version": "9.0.0",
            "endpoint_count": 15, "status": "active",
            "capabilities": ["slot_generation","hold_10min_ttl","double_booking_prevention",
                             "no_show_detection","reschedule_flow","calendar_blocks",
                             "working_hours","automated_reminders","immutable_history"]}

@router.post("/hold",
             summary="Hold a slot — 10-min TTL. Redis SETNX + DB unique constraint.",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def hold_slot(r: Request,
                     u: UserContext = Depends(get_current_user),
                     s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.hold_slot(
        staff_id=uuid.UUID(body["staff_id"]),
        tenant_id=uuid.UUID(body["tenant_id"]),
        customer_id=uuid.UUID(body["customer_id"]),
        service_type_id=body["service_type_id"],
        scheduled_at=body["scheduled_at"],
        duration_minutes=body.get("duration_minutes", 60),
        booking_id=uuid.UUID(body["booking_id"]) if body.get("booking_id") else None,
        customer_notes=body.get("customer_notes"),
    )
    return ok(data, _rid(r), ENGINE_ID,
              links=Links(actions=[
                  Link(href=f"/v1/appointments/{data['appointment_id']}/confirm",
                       method="POST", rel="confirm_hold",
                       description=f"Confirm within {data.get('hold_ttl_seconds',600)//60} minutes")]))

@router.post("/{appointment_id}/confirm",
             summary="Confirm hold — permanently books the slot",
             response_model=ApiResponse[dict])
async def confirm_hold(appointment_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.confirm_hold(appointment_id), _rid(r), ENGINE_ID)

@router.get("/{appointment_id}", summary="Get appointment with HATEOAS transitions",
            response_model=ApiResponse[dict])
async def get_appointment(appointment_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(get_current_user),
                           s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_appointment(appointment_id), _rid(r), ENGINE_ID)

@router.get("/staff/{staff_id}", summary="List appointments by staff member",
            response_model=ApiResponse[dict])
async def list_by_staff(staff_id: uuid.UUID, r: Request,
                         tenant_id: uuid.UUID = Query(...),
                         appt_status: str | None = Query(None, alias="status"),
                         limit: int = Query(50,ge=1,le=200),
                         cursor: str | None = Query(None),
                         u: UserContext = Depends(get_current_user),
                         s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_by_staff(staff_id, tenant_id, appt_status, limit, cursor), _rid(r), ENGINE_ID)

@router.get("/customers/{customer_id}", summary="List appointments by customer",
            response_model=ApiResponse[dict])
async def list_by_customer(customer_id: uuid.UUID, r: Request,
                            tenant_id: uuid.UUID | None = Query(None),
                            limit: int = Query(50,ge=1,le=200),
                            cursor: str | None = Query(None),
                            u: UserContext = Depends(get_current_user),
                            s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_by_customer(customer_id, tenant_id, limit, cursor), _rid(r), ENGINE_ID)

@router.post("/{appointment_id}/cancel", response_model=ApiResponse[dict])
async def cancel_appointment(appointment_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(get_current_user),
                              s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.cancel_appointment(appointment_id, body.get("reason","Cancelled")),
              _rid(r), ENGINE_ID)

@router.post("/{appointment_id}/reschedule",
             summary="Reschedule — marks current as rescheduled, creates new hold",
             response_model=ApiResponse[dict])
async def reschedule(appointment_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.reschedule_appointment(appointment_id, body["new_scheduled_at"]),
              _rid(r), ENGINE_ID)

@router.post("/{appointment_id}/no-show",
             summary="Mark no-show — updates customer health signal + forfeits reservation",
             response_model=ApiResponse[dict])
async def mark_no_show(appointment_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                        s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.mark_no_show(appointment_id), _rid(r), ENGINE_ID)

@router.get("/{appointment_id}/history",
            summary="Immutable appointment status history", response_model=ApiResponse[dict])
async def get_history(appointment_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(get_current_user),
                       s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_history(appointment_id), _rid(r), ENGINE_ID)

@router.get("/staff/{staff_id}/slots",
            summary="Available slots for a staff member on a date",
            response_model=ApiResponse[dict])
async def available_slots(staff_id: uuid.UUID, r: Request,
                           date: str = Query(...),
                           tenant_id: uuid.UUID = Query(...),
                           u: UserContext = Depends(get_current_user),
                           s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_available_slots(staff_id, tenant_id, date), _rid(r), ENGINE_ID)

@router.post("/staff/{staff_id}/calendar/block",
             summary="Block calendar time — prevents slots from being offered",
             status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def block_calendar(staff_id: uuid.UUID, r: Request,
                          tenant_id: uuid.UUID = Query(...),
                          u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                          s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.block_calendar_time(staff_id, tenant_id, body["block_date"],
              body.get("start_time","00:00"), body.get("end_time","23:59"),
              body.get("block_type","leave"), body.get("reason"),
              body.get("is_full_day", False)), _rid(r), ENGINE_ID)

@router.delete("/calendar/blocks/{block_id}",
               summary="Unblock calendar time", response_model=ApiResponse[dict])
async def unblock_calendar(block_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                            s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.unblock_calendar_time(block_id), _rid(r), ENGINE_ID)

@router.put("/staff/{staff_id}/working-hours",
            summary="Set staff working hours and slot configuration",
            response_model=ApiResponse[dict])
async def set_working_hours(staff_id: uuid.UUID, r: Request,
                             tenant_id: uuid.UUID = Query(...),
                             u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                             s: AppointmentService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.set_working_hours(staff_id, tenant_id, body["day_of_week"],
              body["start_time"], body["end_time"],
              body.get("slot_duration",60), body.get("buffer_minutes",15)), _rid(r), ENGINE_ID)
