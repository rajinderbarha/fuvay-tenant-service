"""Sprint 21 — Coaching Appointment Execution Service."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.execution.constants import (
    APPT_TRANSITIONS,
    CA_EV_ACCEPTED, CA_EV_REJECTED, CA_EV_STARTED,
    CA_EV_NOTE_ADDED, CA_EV_COMPLETED, CA_EV_NO_SHOW,
    CA_EV_RESCHEDULE, CA_EV_CANCELLED,
    AS_ACCEPTED, AS_REJECTED, AS_STARTED,
    AS_COMPLETED, AS_NO_SHOW, AS_RESCHEDULE_REQUESTED, AS_CANCELLED,
    ERR_RECORD_NOT_FOUND, ERR_INVALID_TRANSITION,
    ERR_REASON_REQUIRED, ERR_STAFF_NOT_ASSIGNED,
)
from app.engines.execution.models import (
    CoachingAppointmentExecutionEvent,
    CoachingAppointmentNote,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CoachingAppointmentExecutionService:

    async def _get_appt(self, db: AsyncSession, appointment_id: uuid.UUID, tenant_id: uuid.UUID):
        from app.engines.final_records.models import CoachingAppointment
        res = await db.execute(
            select(CoachingAppointment).where(
                CoachingAppointment.id == appointment_id,
                CoachingAppointment.tenant_id == tenant_id,
            )
        )
        appt = res.scalars().first()
        if not appt:
            raise ValueError(ERR_RECORD_NOT_FOUND)
        return appt

    def _assert_transition(self, current: str, target: str) -> None:
        allowed = APPT_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(ERR_INVALID_TRANSITION)

    def _assert_staff_owns_appt(self, appt, staff_member_id: uuid.UUID) -> None:
        if str(appt.staff_member_id) != str(staff_member_id):
            raise ValueError(ERR_STAFF_NOT_ASSIGNED)

    async def _set_status(
        self,
        db: AsyncSession,
        appt,
        new_status: str,
        event_type: str,
        user_id: uuid.UUID | None,
        actor_role: str,
        notes: str | None = None,
        request_id: str | None = None,
    ) -> None:
        old = appt.status
        self._assert_transition(old, new_status)
        appt.status = new_status
        appt.updated_at = _now()
        db.add(appt)
        ev = CoachingAppointmentExecutionEvent(
            appointment_id=appt.id,
            tenant_id=appt.tenant_id,
            staff_member_id=appt.staff_member_id,
            actor_user_id=user_id,
            actor_role=actor_role,
            event_type=event_type,
            old_status=old,
            new_status=new_status,
            notes=notes,
            request_id=request_id,
        )
        db.add(ev)

    # ── lifecycle transitions ─────────────────────────────────────────────────

    async def accept_appointment(self, db, appointment_id, tenant_id, staff_member_id, user_id, request_id=None):
        appt = await self._get_appt(db, appointment_id, tenant_id)
        self._assert_staff_owns_appt(appt, staff_member_id)
        await self._set_status(db, appt, AS_ACCEPTED, CA_EV_ACCEPTED, user_id, "staff", request_id=request_id)
        await db.flush()
        return appt.to_dict()

    async def reject_appointment(self, db, appointment_id, tenant_id, staff_member_id, user_id, reason: str, request_id=None):
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        appt = await self._get_appt(db, appointment_id, tenant_id)
        self._assert_staff_owns_appt(appt, staff_member_id)
        await self._set_status(db, appt, AS_REJECTED, CA_EV_REJECTED, user_id, "staff", notes=reason, request_id=request_id)
        appt.failure_reason = reason
        db.add(appt)
        await db.flush()
        return appt.to_dict()

    async def start_appointment(self, db, appointment_id, tenant_id, staff_member_id, user_id, request_id=None):
        appt = await self._get_appt(db, appointment_id, tenant_id)
        self._assert_staff_owns_appt(appt, staff_member_id)
        await self._set_status(db, appt, AS_STARTED, CA_EV_STARTED, user_id, "staff", request_id=request_id)
        await db.flush()
        return appt.to_dict()

    async def complete_appointment(self, db, appointment_id, tenant_id, staff_member_id, user_id, request_id=None):
        appt = await self._get_appt(db, appointment_id, tenant_id)
        self._assert_staff_owns_appt(appt, staff_member_id)
        await self._set_status(db, appt, AS_COMPLETED, CA_EV_COMPLETED, user_id, "staff", request_id=request_id)
        await db.flush()
        return appt.to_dict()

    async def mark_no_show(self, db, appointment_id, tenant_id, staff_member_id, user_id, notes=None, request_id=None):
        appt = await self._get_appt(db, appointment_id, tenant_id)
        self._assert_staff_owns_appt(appt, staff_member_id)
        await self._set_status(db, appt, AS_NO_SHOW, CA_EV_NO_SHOW, user_id, "staff", notes=notes, request_id=request_id)
        await db.flush()
        return appt.to_dict()

    async def request_reschedule(self, db, appointment_id, tenant_id, staff_member_id, user_id, notes=None, request_id=None):
        appt = await self._get_appt(db, appointment_id, tenant_id)
        self._assert_staff_owns_appt(appt, staff_member_id)
        await self._set_status(db, appt, AS_RESCHEDULE_REQUESTED, CA_EV_RESCHEDULE, user_id, "staff", notes=notes, request_id=request_id)
        await db.flush()
        return appt.to_dict()

    async def cancel_appointment(self, db, appointment_id, tenant_id, user_id, reason: str, actor_role: str = "provider", request_id=None):
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        appt = await self._get_appt(db, appointment_id, tenant_id)
        await self._set_status(db, appt, AS_CANCELLED, CA_EV_CANCELLED, user_id, actor_role, notes=reason, request_id=request_id)
        appt.failure_reason = reason
        db.add(appt)
        await db.flush()
        return appt.to_dict()

    # ── notes ─────────────────────────────────────────────────────────────────

    async def add_note(self, db, appointment_id, tenant_id, staff_member_id, user_id, note_text: str, is_customer_visible: bool = False, request_id=None):
        appt = await self._get_appt(db, appointment_id, tenant_id)
        self._assert_staff_owns_appt(appt, staff_member_id)
        note = CoachingAppointmentNote(
            appointment_id=appt.id, tenant_id=appt.tenant_id,
            staff_member_id=staff_member_id, note_type="consultation",
            note_text=note_text, is_customer_visible=is_customer_visible,
            created_by_user_id=user_id,
        )
        db.add(note)
        ev = CoachingAppointmentExecutionEvent(
            appointment_id=appt.id, tenant_id=appt.tenant_id,
            staff_member_id=staff_member_id, actor_user_id=user_id,
            actor_role="staff", event_type=CA_EV_NOTE_ADDED,
            old_status=appt.status, new_status=appt.status,
            request_id=request_id,
        )
        db.add(ev)
        await db.flush()
        return note.to_dict()

    # ── timeline / notes read ─────────────────────────────────────────────────

    async def get_timeline(self, db: AsyncSession, appointment_id: uuid.UUID, tenant_id: uuid.UUID) -> list[dict]:
        res = await db.execute(
            select(CoachingAppointmentExecutionEvent)
            .where(
                CoachingAppointmentExecutionEvent.appointment_id == appointment_id,
                CoachingAppointmentExecutionEvent.tenant_id == tenant_id,
            )
            .order_by(CoachingAppointmentExecutionEvent.created_at.asc())
        )
        return [e.to_dict() for e in res.scalars().all()]

    async def get_notes(self, db: AsyncSession, appointment_id: uuid.UUID, tenant_id: uuid.UUID, customer_only: bool = False) -> list[dict]:
        q = select(CoachingAppointmentNote).where(
            CoachingAppointmentNote.appointment_id == appointment_id,
            CoachingAppointmentNote.tenant_id == tenant_id,
        )
        if customer_only:
            q = q.where(CoachingAppointmentNote.is_customer_visible == True)
        res = await db.execute(q.order_by(CoachingAppointmentNote.created_at.asc()))
        return [n.to_dict() for n in res.scalars().all()]
