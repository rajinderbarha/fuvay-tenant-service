"""Phase M -- work-session (start/pause/resume) service. Supplementary
elapsed-time evidence only; never a second workflow-status authority
(ServiceJob.status via HomeServiceJobExecutionService remains sole source
of truth for gating). One row per job."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.engines.execution.models import WorkSession

STATE_ACTIVE = "active"
STATE_PAUSED = "paused"
STATE_FINISHED = "finished"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WorkSessionService:
    async def get(self, db: AsyncSession, job_id: uuid.UUID) -> WorkSession | None:
        res = await db.execute(select(WorkSession).where(WorkSession.job_id == job_id))
        return res.scalars().first()

    async def start_or_resume(self, db: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID, staff_member_id: uuid.UUID) -> WorkSession:
        session = await self.get(db, job_id)
        now = _now()
        if session is None:
            session = WorkSession(
                job_id=job_id, tenant_id=tenant_id, staff_member_id=staff_member_id,
                state=STATE_ACTIVE, started_at=now, segment_started_at=now, accumulated_seconds=0,
            )
            db.add(session)
            await db.flush()
            return session
        if session.state == STATE_FINISHED:
            raise ServiceOSException("WORK_SESSION_ALREADY_FINISHED", "This job's work session is already finished.", status_code=409)
        if session.state == STATE_ACTIVE:
            # Duplicate start/resume request -- idempotent no-op, not a second session.
            return session
        session.state = STATE_ACTIVE
        session.segment_started_at = now
        session.paused_at = None
        session.pause_reason = None
        db.add(session)
        await db.flush()
        return session

    async def pause(self, db: AsyncSession, job_id: uuid.UUID, reason: str | None) -> WorkSession:
        session = await self.get(db, job_id)
        if session is None or session.state != STATE_ACTIVE:
            raise ServiceOSException("WORK_SESSION_NOT_ACTIVE", "There is no active work session to pause.", status_code=409)
        now = _now()
        elapsed = int((now - session.segment_started_at).total_seconds()) if session.segment_started_at else 0
        session.accumulated_seconds += max(elapsed, 0)
        session.state = STATE_PAUSED
        session.paused_at = now
        session.pause_reason = reason
        session.segment_started_at = None
        db.add(session)
        await db.flush()
        return session

    async def finish(self, db: AsyncSession, job_id: uuid.UUID) -> WorkSession:
        session = await self.get(db, job_id)
        if session is None:
            raise ServiceOSException("WORK_SESSION_NOT_FOUND", "No work session exists for this job.", status_code=409)
        if session.state == STATE_FINISHED:
            return session
        now = _now()
        if session.state == STATE_ACTIVE and session.segment_started_at:
            elapsed = int((now - session.segment_started_at).total_seconds())
            session.accumulated_seconds += max(elapsed, 0)
        session.state = STATE_FINISHED
        session.finished_at = now
        session.segment_started_at = None
        db.add(session)
        await db.flush()
        return session

    def elapsed_seconds(self, session: WorkSession | None) -> int:
        if session is None:
            return 0
        if session.state == STATE_ACTIVE and session.segment_started_at:
            return session.accumulated_seconds + max(int((_now() - session.segment_started_at).total_seconds()), 0)
        return session.accumulated_seconds
