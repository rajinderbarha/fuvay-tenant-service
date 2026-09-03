"""Sprint 25 — Service Rework Service."""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.engines.complaints.constants import (
    REWORK_REQUESTED, REWORK_APPROVED, REWORK_ASSIGNED, REWORK_SCHEDULED,
    REWORK_IN_PROGRESS, REWORK_COMPLETED, REWORK_REJECTED, REWORK_CANCELLED,
    STATUS_REWORK_APPROVED, STATUS_RESOLVED,
    ALLOWED_TRANSITIONS,
    EVT_REWORK_CREATED,
    ACTOR_PROVIDER, ACTOR_SYSTEM,
    ERR_REWORK_NOT_FOUND, ERR_REWORK_ACCESS_DENIED, ERR_REWORK_NOT_ALLOWED,
)
from app.exceptions import ServiceOSException
from app.engines.complaints.models import ServiceReworkRequest, CustomerComplaint, ComplaintEvent
from app.engines.complaints.complaint_service import ComplaintService


class ServiceReworkService:

    def __init__(self):
        self._complaint_svc = ComplaintService()

    async def create_rework_request_from_complaint(
        self,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_type: str,
        rework_reason: str,
        customer_visible_notes: str | None = None,
        request_id: str = "—",
    ) -> ServiceReworkRequest:
        complaint = await self._complaint_svc.get_complaint(db, complaint_id)
        rework = ServiceReworkRequest(
            complaint_id           = complaint_id,
            tenant_id              = complaint.tenant_id,
            customer_id            = complaint.customer_id,
            booking_id             = complaint.booking_id,
            job_id                 = complaint.job_id,
            original_job_id        = complaint.job_id,
            status                 = REWORK_APPROVED,
            rework_reason          = rework_reason,
            customer_visible_notes = customer_visible_notes,
        )
        db.add(rework)
        await db.flush()
        await self._log_event(db, complaint_id, complaint.tenant_id, actor_type, actor_user_id,
                              EVT_REWORK_CREATED, None, None, {"rework_id": str(rework.id)}, request_id)
        await db.commit()
        return rework

    # Rework had NO transition validation at all: every method below simply
    # assigned its target status. That let a rework skip approval entirely
    # (provider "start" straight from `requested`), let admin approval move a
    # rework that was already in progress BACKWARDS to `approved`, and let a
    # rework be completed without ever being approved or scheduled -- so the
    # completion could resolve the underlying complaint on the strength of
    # work no one authorised. RefundRequestService already guards its own
    # transitions this way (REFUND_INVALID_STATE); this mirrors it.
    _ALLOWED_REWORK_TRANSITIONS: dict[str, set[str]] = {
        REWORK_REQUESTED:   {REWORK_APPROVED, REWORK_REJECTED, REWORK_CANCELLED},
        REWORK_APPROVED:    {REWORK_ASSIGNED, REWORK_SCHEDULED, REWORK_IN_PROGRESS, REWORK_CANCELLED},
        REWORK_ASSIGNED:    {REWORK_SCHEDULED, REWORK_IN_PROGRESS, REWORK_CANCELLED},
        REWORK_SCHEDULED:   {REWORK_ASSIGNED, REWORK_IN_PROGRESS, REWORK_CANCELLED},
        REWORK_IN_PROGRESS: {REWORK_COMPLETED, REWORK_CANCELLED},
        REWORK_COMPLETED:   set(),
        REWORK_REJECTED:    set(),
        REWORK_CANCELLED:   set(),
    }

    @classmethod
    def _assert_rework_transition(cls, rework, target: str) -> None:
        current = rework.status
        if current == target:
            return
        if target not in cls._ALLOWED_REWORK_TRANSITIONS.get(current, set()):
            raise ServiceOSException(
                "REWORK_INVALID_STATE",
                "A rework in state '%s' cannot move to '%s'." % (current, target),
                status_code=409,
            )

    async def assign_rework(
        self,
        db: AsyncSession,
        rework_id: uuid.UUID,
        staff_member_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        request_id: str = "—",
    ) -> ServiceReworkRequest:
        rework = await self._get_rework(db, rework_id)
        self._assert_rework_transition(rework, REWORK_ASSIGNED)
        rework.assigned_staff_member_id = staff_member_id
        rework.status = REWORK_ASSIGNED
        await db.commit()
        return rework

    async def schedule_rework(
        self,
        db: AsyncSession,
        rework_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        scheduled_date: str | None = None,
        scheduled_time_window: str | None = None,
        request_id: str = "—",
        tenant_id: uuid.UUID | None = None,
    ) -> ServiceReworkRequest:
        rework = await self._get_rework(db, rework_id, tenant_id=tenant_id)
        self._assert_rework_transition(rework, REWORK_SCHEDULED)
        from datetime import date
        if scheduled_date:
            rework.scheduled_date = date.fromisoformat(scheduled_date)
        rework.scheduled_time_window = scheduled_time_window
        rework.status = REWORK_SCHEDULED
        await db.commit()
        return rework

    async def mark_rework_in_progress(
        self, db: AsyncSession, rework_id: uuid.UUID, actor_user_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
    ) -> ServiceReworkRequest:
        rework = await self._get_rework(db, rework_id, tenant_id=tenant_id)
        self._assert_rework_transition(rework, REWORK_IN_PROGRESS)
        rework.status = REWORK_IN_PROGRESS
        await db.commit()
        return rework

    async def mark_rework_completed(
        self,
        db: AsyncSession,
        rework_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        notes: str | None = None,
        request_id: str = "—",
        tenant_id: uuid.UUID | None = None,
    ) -> ServiceReworkRequest:
        rework = await self._get_rework(db, rework_id, tenant_id=tenant_id)
        self._assert_rework_transition(rework, REWORK_COMPLETED)
        rework.status       = REWORK_COMPLETED
        rework.completed_at = datetime.now(timezone.utc)
        if notes:
            rework.customer_visible_notes = notes

        complaint = await self._complaint_svc.get_complaint(db, rework.complaint_id)
        allowed = ALLOWED_TRANSITIONS.get(complaint.status, set())
        if STATUS_RESOLVED in allowed:
            complaint.status    = STATUS_RESOLVED
            complaint.resolved_at = datetime.now(timezone.utc)

        await db.commit()
        return rework

    async def list_rework_requests(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[ServiceReworkRequest]:
        q = select(ServiceReworkRequest)
        if tenant_id:
            q = q.where(ServiceReworkRequest.tenant_id == tenant_id)
        if status:
            q = q.where(ServiceReworkRequest.status == status)
        q = q.order_by(ServiceReworkRequest.created_at.desc()).limit(100)
        r = await db.execute(q)
        return r.scalars().all()

    async def get_rework(self, db: AsyncSession, rework_id: uuid.UUID,
                          tenant_id: uuid.UUID | None = None) -> ServiceReworkRequest:
        return await self._get_rework(db, rework_id, tenant_id=tenant_id)

    async def _get_rework(self, db: AsyncSession, rework_id: uuid.UUID,
                           tenant_id: uuid.UUID | None = None) -> ServiceReworkRequest:
        # Slice 2F-9: previously loaded by rework_id alone -- ANY authenticated
        # user of any tenant could schedule/start/complete/read another
        # tenant's rework request just by supplying its ID. When a tenant_id
        # is provided (the provider-facing callers now always supply the
        # caller's own principal tenant_id), the loaded row's tenant_id must
        # match, or the request fails closed with the same not-found error a
        # genuinely missing row would produce (no existence leakage).
        r = await db.execute(select(ServiceReworkRequest).where(ServiceReworkRequest.id == rework_id))
        rw = r.scalars().first()
        if not rw:
            raise ValueError(ERR_REWORK_NOT_FOUND)
        if tenant_id is not None and str(rw.tenant_id) != str(tenant_id):
            raise ValueError(ERR_REWORK_NOT_FOUND)
        return rw

    async def _log_event(
        self,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        tenant_id,
        actor_type: str,
        actor_user_id,
        event_type: str,
        old_status,
        new_status,
        new_value: dict | None,
        request_id: str,
    ) -> None:
        ev = ComplaintEvent(
            complaint_id  = complaint_id,
            tenant_id     = tenant_id,
            actor_type    = actor_type,
            actor_user_id = actor_user_id,
            event_type    = event_type,
            old_status    = old_status,
            new_status    = new_status,
            new_value     = new_value,
            request_id    = request_id,
        )
        db.add(ev)
        await db.flush()
