"""Sprint 21 — Real Estate Lead Execution Service."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.execution.constants import (
    LEAD_TRANSITIONS,
    RE_EV_ACCEPTED, RE_EV_REJECTED, RE_EV_CONTACTED,
    RE_EV_NOTE_ADDED, RE_EV_FOLLOW_UP, RE_EV_SITE_PLANNED,
    RE_EV_SITE_COMPLETED, RE_EV_QUALIFIED, RE_EV_UNQUALIFIED,
    RE_EV_CONVERTED, RE_EV_CLOSED_LOST,
    LS_ACCEPTED, LS_REJECTED, LS_CONTACTED,
    LS_FOLLOW_UP, LS_SITE_VISIT, LS_SITE_VISITED,
    LS_QUALIFIED, LS_UNQUALIFIED, LS_CONVERTED, LS_CLOSED_LOST,
    ERR_RECORD_NOT_FOUND, ERR_INVALID_TRANSITION,
    ERR_REASON_REQUIRED, ERR_STAFF_NOT_ASSIGNED,
)
from app.engines.execution.models import (
    RealEstateLeadExecutionEvent,
    RealEstateLeadNote,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RealEstateLeadExecutionService:

    async def _get_lead(self, db: AsyncSession, lead_id: uuid.UUID, tenant_id: uuid.UUID | None = None):
        from app.engines.final_records.models import RealEstateLead
        q = select(RealEstateLead).where(RealEstateLead.id == lead_id)
        if tenant_id:
            q = q.where(RealEstateLead.tenant_id == tenant_id)
        res = await db.execute(q)
        lead = res.scalars().first()
        if not lead:
            raise ValueError(ERR_RECORD_NOT_FOUND)
        return lead

    def _assert_transition(self, current: str, target: str) -> None:
        allowed = LEAD_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(ERR_INVALID_TRANSITION)

    def _assert_agent_owns_lead(self, lead, agent_id: uuid.UUID) -> None:
        if str(lead.agent_id) != str(agent_id):
            raise ValueError(ERR_STAFF_NOT_ASSIGNED)

    async def _set_status(
        self,
        db: AsyncSession,
        lead,
        new_status: str,
        event_type: str,
        user_id: uuid.UUID | None,
        actor_role: str,
        notes: str | None = None,
        request_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        old = lead.status
        self._assert_transition(old, new_status)
        lead.status = new_status
        lead.updated_at = _now()
        db.add(lead)
        ev = RealEstateLeadExecutionEvent(
            lead_id=lead.id,
            tenant_id=lead.tenant_id,
            assigned_agent_id=lead.agent_id,
            actor_user_id=user_id,
            actor_role=actor_role,
            event_type=event_type,
            old_status=old,
            new_status=new_status,
            notes=notes,
            event_metadata=metadata,
            request_id=request_id,
        )
        db.add(ev)

    # ── lifecycle transitions ─────────────────────────────────────────────────

    async def accept_lead(self, db, lead_id, tenant_id, agent_id, user_id, request_id=None):
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        await self._set_status(db, lead, LS_ACCEPTED, RE_EV_ACCEPTED, user_id, "agent", request_id=request_id)
        await db.flush()
        return lead.to_dict()

    async def reject_lead(self, db, lead_id, tenant_id, agent_id, user_id, reason: str, request_id=None):
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        await self._set_status(db, lead, LS_REJECTED, RE_EV_REJECTED, user_id, "agent", notes=reason, request_id=request_id)
        lead.failure_reason = reason
        db.add(lead)
        await db.flush()
        return lead.to_dict()

    async def mark_contacted(self, db, lead_id, tenant_id, agent_id, user_id, notes=None, request_id=None):
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        await self._set_status(db, lead, LS_CONTACTED, RE_EV_CONTACTED, user_id, "agent", notes=notes, request_id=request_id)
        await db.flush()
        return lead.to_dict()

    async def schedule_follow_up(self, db, lead_id, tenant_id, agent_id, user_id, notes=None, request_id=None):
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        await self._set_status(db, lead, LS_FOLLOW_UP, RE_EV_FOLLOW_UP, user_id, "agent", notes=notes, request_id=request_id)
        await db.flush()
        return lead.to_dict()

    async def plan_site_visit(self, db, lead_id, tenant_id, agent_id, user_id, notes=None, request_id=None):
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        await self._set_status(db, lead, LS_SITE_VISIT, RE_EV_SITE_PLANNED, user_id, "agent", notes=notes, request_id=request_id)
        await db.flush()
        return lead.to_dict()

    async def complete_site_visit(self, db, lead_id, tenant_id, agent_id, user_id, notes=None, request_id=None):
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        await self._set_status(db, lead, LS_SITE_VISITED, RE_EV_SITE_COMPLETED, user_id, "agent", notes=notes, request_id=request_id)
        await db.flush()
        return lead.to_dict()

    async def qualify_lead(self, db, lead_id, tenant_id, agent_id, user_id, notes=None, request_id=None):
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        await self._set_status(db, lead, LS_QUALIFIED, RE_EV_QUALIFIED, user_id, "agent", notes=notes, request_id=request_id)
        await db.flush()
        return lead.to_dict()

    async def disqualify_lead(self, db, lead_id, tenant_id, agent_id, user_id, reason: str, request_id=None):
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        await self._set_status(db, lead, LS_UNQUALIFIED, RE_EV_UNQUALIFIED, user_id, "agent", notes=reason, request_id=request_id)
        await db.flush()
        return lead.to_dict()

    async def convert_lead(self, db, lead_id, tenant_id, agent_id, user_id, notes=None, request_id=None):
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        await self._set_status(db, lead, LS_CONVERTED, RE_EV_CONVERTED, user_id, "agent", notes=notes, request_id=request_id)
        await db.flush()
        return lead.to_dict()

    async def close_lost(self, db, lead_id, tenant_id, agent_id, user_id, reason: str, request_id=None):
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        await self._set_status(db, lead, LS_CLOSED_LOST, RE_EV_CLOSED_LOST, user_id, "agent", notes=reason, request_id=request_id)
        lead.failure_reason = reason
        db.add(lead)
        await db.flush()
        return lead.to_dict()

    # ── notes ─────────────────────────────────────────────────────────────────

    async def add_note(self, db, lead_id, tenant_id, agent_id, user_id, note_text: str, is_customer_visible: bool = False, request_id=None):
        lead = await self._get_lead(db, lead_id, tenant_id)
        self._assert_agent_owns_lead(lead, agent_id)
        note = RealEstateLeadNote(
            lead_id=lead.id, tenant_id=lead.tenant_id,
            assigned_agent_id=agent_id, note_type="consultation",
            note_text=note_text, is_customer_visible=is_customer_visible,
            created_by_user_id=user_id,
        )
        db.add(note)
        ev = RealEstateLeadExecutionEvent(
            lead_id=lead.id, tenant_id=lead.tenant_id,
            assigned_agent_id=lead.agent_id, actor_user_id=user_id,
            actor_role="agent", event_type=RE_EV_NOTE_ADDED,
            old_status=lead.status, new_status=lead.status,
            request_id=request_id,
        )
        db.add(ev)
        await db.flush()
        return note.to_dict()

    # ── timeline / notes read ─────────────────────────────────────────────────

    async def get_timeline(self, db: AsyncSession, lead_id: uuid.UUID, tenant_id: uuid.UUID | None = None) -> list[dict]:
        q = select(RealEstateLeadExecutionEvent).where(RealEstateLeadExecutionEvent.lead_id == lead_id)
        if tenant_id:
            q = q.where(RealEstateLeadExecutionEvent.tenant_id == tenant_id)
        res = await db.execute(q.order_by(RealEstateLeadExecutionEvent.created_at.asc()))
        return [e.to_dict() for e in res.scalars().all()]

    async def get_notes(self, db: AsyncSession, lead_id: uuid.UUID, tenant_id: uuid.UUID | None = None, customer_only: bool = False) -> list[dict]:
        q = select(RealEstateLeadNote).where(RealEstateLeadNote.lead_id == lead_id)
        if tenant_id:
            q = q.where(RealEstateLeadNote.tenant_id == tenant_id)
        if customer_only:
            q = q.where(RealEstateLeadNote.is_customer_visible == True)
        res = await db.execute(q.order_by(RealEstateLeadNote.created_at.asc()))
        return [n.to_dict() for n in res.scalars().all()]
