"""Sprint 21 — Coaching appointment execution routers (staff + provider + customer + admin)."""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.dependencies.auth import get_current_user, require_super_admin
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.execution.coaching_service import CoachingAppointmentExecutionService

_svc = CoachingAppointmentExecutionService()

# ── Staff / Coach router ──────────────────────────────────────────────────────
staff_router = APIRouter(prefix="/v1/staff/coaching-appointments", tags=["Sprint21-Staff-Coaching"])


class ReasonBody(BaseModel):
    reason: str


class NoteBody(BaseModel):
    note_text: str
    is_customer_visible: bool = False


class OptionalNoteBody(BaseModel):
    notes: Optional[str] = None


@staff_router.post("/{appointment_id}/accept")
async def staff_accept(appointment_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.accept_appointment(db, appointment_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-coaching-accept")


@staff_router.post("/{appointment_id}/reject")
async def staff_reject(appointment_id: uuid.UUID, body: ReasonBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.reject_appointment(db, appointment_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), reason=body.reason, request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-coaching-reject")


@staff_router.post("/{appointment_id}/start")
async def staff_start(appointment_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.start_appointment(db, appointment_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-coaching-start")


@staff_router.post("/{appointment_id}/complete")
async def staff_complete(appointment_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.complete_appointment(db, appointment_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-coaching-complete")


@staff_router.post("/{appointment_id}/no-show")
async def staff_no_show(appointment_id: uuid.UUID, body: OptionalNoteBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.mark_no_show(db, appointment_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), notes=body.notes, request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-coaching-no-show")


@staff_router.post("/{appointment_id}/request-reschedule")
async def staff_reschedule(appointment_id: uuid.UUID, body: OptionalNoteBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.request_reschedule(db, appointment_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), notes=body.notes, request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-coaching-reschedule")


@staff_router.post("/{appointment_id}/notes")
async def staff_add_note(appointment_id: uuid.UUID, body: NoteBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.add_note(db, appointment_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id)), uuid.UUID(str(user.user_id)), note_text=body.note_text, is_customer_visible=body.is_customer_visible, request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-coaching-note")


@staff_router.get("/{appointment_id}/timeline")
async def staff_timeline(appointment_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_timeline(db, appointment_id, uuid.UUID(str(user.tenant_id)))
    return ok(result, rid, "staff-coaching-timeline")


# ── Provider router ───────────────────────────────────────────────────────────
provider_router = APIRouter(prefix="/v1/provider/coaching-appointments", tags=["Sprint21-Provider-Coaching"])


@provider_router.post("/{appointment_id}/cancel")
async def provider_cancel(appointment_id: uuid.UUID, body: ReasonBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.cancel_appointment(db, appointment_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(user.user_id)), reason=body.reason, actor_role="provider", request_id=rid)
    await db.commit()
    return ok(result, rid, "provider-coaching-cancel")


@provider_router.get("/{appointment_id}/timeline")
async def provider_timeline(appointment_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_timeline(db, appointment_id, uuid.UUID(str(user.tenant_id)))
    return ok(result, rid, "provider-coaching-timeline")


# ── Customer tracking router ──────────────────────────────────────────────────
customer_router = APIRouter(prefix="/v1/customer/coaching-appointments", tags=["Sprint21-Customer-Coaching"])


@customer_router.get("/{appointment_id}/tracking")
async def customer_tracking(appointment_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    from sqlalchemy import select
    from app.engines.final_records.models import CoachingAppointment
    res = await db.execute(select(CoachingAppointment).where(
        CoachingAppointment.id == appointment_id,
        CoachingAppointment.customer_id == uuid.UUID(str(user.user_id))
    ))
    appt = res.scalars().first()
    if not appt:
        from app.engines.execution.constants import ERR_RECORD_NOT_FOUND
        raise ValueError(ERR_RECORD_NOT_FOUND)
    notes = await _svc.get_notes(db, appointment_id, appt.tenant_id, customer_only=True)
    return ok({"appointment": appt.to_dict(), "notes": notes}, rid, "customer-coaching-tracking")


# ── Admin router ──────────────────────────────────────────────────────────────
admin_router = APIRouter(prefix="/v1/admin/coaching-appointments", tags=["Sprint21-Admin-Coaching"])


@admin_router.get("/{appointment_id}/execution-timeline")
async def admin_timeline(appointment_id: uuid.UUID, r: Request, user=Depends(require_super_admin), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    from sqlalchemy import select
    from app.engines.final_records.models import CoachingAppointment
    res = await db.execute(select(CoachingAppointment).where(CoachingAppointment.id == appointment_id))
    appt = res.scalars().first()
    if not appt:
        from app.engines.execution.constants import ERR_RECORD_NOT_FOUND
        raise ValueError(ERR_RECORD_NOT_FOUND)
    result = await _svc.get_timeline(db, appointment_id, appt.tenant_id)
    return ok(result, rid, "admin-coaching-timeline")
