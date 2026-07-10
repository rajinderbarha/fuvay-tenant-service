"""Dispatch Engine — DispatchService. Auto-assign scoring, broadcast, escalation."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.dispatch.constants import (
    DispatchMode, DispatchStatus, DEFAULT_SCORE_WEIGHTS,
    BROADCAST_ACCEPT_TTL_MINUTES, AUTO_ASSIGN_ACCEPT_SLA_MINUTES,
    MAX_ESCALATION_ATTEMPTS, REDIS_BROADCAST, REDIS_DISPATCH_LOCK,
)
from app.engines.dispatch.models import DispatchRecord, DispatchEscalationLog
from app.engines.field_ops.constants import JS
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("dispatch.service")
utcnow = lambda: datetime.now(timezone.utc)


_JOB_FORWARD_CHAIN = [JS.DRAFT, JS.CONFIRMED, JS.DISPATCHED, JS.ACCEPTED]


class DispatchService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id; self.actor_id = actor_id; self.actor_role = actor_role

    async def _get_job(self, job_id: str):
        from app.engines.field_ops.models import Job
        try:
            job_uuid = uuid.UUID(job_id)
        except (ValueError, AttributeError):
            return None
        r = await self.db.execute(select(Job).where(Job.id == job_uuid))
        return r.scalar_one_or_none()

    async def _advance_job(self, job, target_status: str, reason: str) -> None:
        """Dispatch drives the Job's early lifecycle (draft→confirmed→dispatched→accepted).
        Only steps forward along this known linear segment — never touches a job
        that's already past it (en_route, work_started, etc.) so it can't clobber
        real field-ops progress."""
        from app.engines.field_ops.models import JobStatusHistory
        if job.status not in _JOB_FORWARD_CHAIN or target_status not in _JOB_FORWARD_CHAIN:
            return
        cur_idx = _JOB_FORWARD_CHAIN.index(job.status)
        tgt_idx = _JOB_FORWARD_CHAIN.index(target_status)
        for i in range(cur_idx, tgt_idx):
            from_s, to_s = _JOB_FORWARD_CHAIN[i], _JOB_FORWARD_CHAIN[i + 1]
            self.db.add(JobStatusHistory(
                job_id=job.id, tenant_id=job.tenant_id, from_status=from_s, to_status=to_s,
                changed_by=self.actor_id, changed_by_role=self.actor_role, reason=reason,
            ))
            job.status = to_s

    async def _get_score_weights(self, tenant_id: uuid.UUID) -> dict:
        try:
            from app.engines.settings_engine.service import SettingsService
            svc = SettingsService(self.db)
            result = await svc.resolve("dispatch_score_weights", tenant_id=tenant_id)
            if result.get("value"):
                return result["value"]
        except Exception:
            pass
        return DEFAULT_SCORE_WEIGHTS

    def _score_candidate(self, staff_id: str, distance_km: float, perf_score: float,
                          active_jobs: int, specialisation_match: bool, weights: dict) -> float:
        dist_score = max(0.0, 100.0 - (distance_km * 5))
        job_load   = max(0.0, 100.0 - (active_jobs * 20))
        spec_score = 100.0 if specialisation_match else 60.0
        return (dist_score * weights.get("distance", 0.4) +
                perf_score * weights.get("performance", 0.35) +
                job_load   * weights.get("active_job_count", 0.15) +
                spec_score * weights.get("specialisation", 0.10))

    def _rec_dict(self, r: DispatchRecord) -> dict:
        return {"dispatch_id": str(r.id), "job_id": r.job_id, "tenant_id": str(r.tenant_id),
                "dispatch_mode": r.dispatch_mode, "status": r.status,
                "assigned_staff_id": str(r.assigned_staff_id) if r.assigned_staff_id else None,
                "candidates_scored": r.candidates_scored, "rejection_count": r.rejection_count,
                "escalation_count": r.escalation_count,
                "accepted_at": r.accepted_at.isoformat() if r.accepted_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None}

    async def dispatch_job(self, job_id: str, tenant_id: uuid.UUID,
                            mode: str, staff_id: uuid.UUID | None,
                            job_lat: float | None, job_lng: float | None,
                            service_type_id: str) -> dict:
        # Idempotency
        ex = await self.db.execute(select(DispatchRecord).where(DispatchRecord.job_id == job_id))
        existing = ex.scalar_one_or_none()
        if existing:
            return {**self._rec_dict(existing), "idempotent": True}

        weights = await self._get_score_weights(tenant_id)
        candidates = []
        assigned_staff = None

        if mode == DispatchMode.MANUAL:
            if not staff_id:
                raise ServiceOSException("VALIDATION_ERROR", "staff_id required for manual dispatch.")
            assigned_staff = staff_id
            candidates = [{"staff_id": str(staff_id), "score": 100.0, "selected": True}]

        elif mode == DispatchMode.AUTO_ASSIGN:
            from app.engines.geo.models import StaffLocation
            from app.engines.data_science.models import StaffPerformanceScore
            loc_r = await self.db.execute(select(StaffLocation).where(
                StaffLocation.tenant_id == tenant_id,
                StaffLocation.status == "available"))
            available = loc_r.scalars().all()

            for loc in available:
                dist_km = 5.0  # fallback distance
                if job_lat and job_lng:
                    import math
                    d_lat = math.radians(job_lat - loc.latitude)
                    d_lng = math.radians(job_lng - loc.longitude)
                    a = math.sin(d_lat/2)**2 + math.cos(math.radians(job_lat)) * math.cos(math.radians(loc.latitude)) * math.sin(d_lng/2)**2
                    dist_km = 6371.0 * 2 * math.asin(math.sqrt(a))

                perf_r = await self.db.execute(select(StaffPerformanceScore).where(
                    StaffPerformanceScore.staff_id == loc.staff_id,
                    StaffPerformanceScore.tenant_id == tenant_id))
                perf = perf_r.scalar_one_or_none()
                perf_score = perf.composite_score if perf else 50.0

                score = self._score_candidate(str(loc.staff_id), dist_km, perf_score,
                                               loc.active_job_count, True, weights)
                candidates.append({"staff_id": str(loc.staff_id), "score": round(score, 2),
                                    "distance_km": round(dist_km, 2), "perf_score": perf_score,
                                    "active_jobs": loc.active_job_count, "selected": False})

            candidates.sort(key=lambda x: x["score"], reverse=True)
            if candidates:
                candidates[0]["selected"] = True
                assigned_staff = uuid.UUID(candidates[0]["staff_id"])

        rec = DispatchRecord(
            job_id=job_id, tenant_id=tenant_id, dispatch_mode=mode,
            status=DispatchStatus.ASSIGNED if assigned_staff else DispatchStatus.PENDING,
            assigned_staff_id=assigned_staff, candidates_scored=candidates,
            score_weights=weights, dispatched_by=self.actor_id,
            expires_at=utcnow() + timedelta(minutes=AUTO_ASSIGN_ACCEPT_SLA_MINUTES)
                if mode == DispatchMode.AUTO_ASSIGN else None,
        )
        self.db.add(rec); await self.db.flush()

        # Sync the Job row itself — without this, Job.assigned_staff_id stays
        # NULL forever and no staff member could ever see/act on their own jobs.
        job_obj = await self._get_job(job_id)
        if job_obj:
            if assigned_staff:
                job_obj.assigned_staff_id = assigned_staff
            await self._advance_job(job_obj, JS.DISPATCHED, f"Dispatched via {mode}")

        # Auto-create job chat conversation when staff is assigned
        if assigned_staff and job_obj:
            try:
                if job_obj.customer_id:
                    from app.engines.chat.service import ChatService
                    participants = [
                        {"user_id": str(job_obj.customer_id), "role": "customer", "name": "Customer"},
                        {"user_id": str(assigned_staff), "role": "staff", "name": "Staff"},
                    ]
                    await ChatService(self.db, actor_id=self.actor_id).get_or_create_conversation(
                        tenant_id, "job", job_id, participants=participants,
                        meta={"job_number": job_obj.job_number, "title": job_obj.title})
            except Exception as e:
                logger.warning("dispatch.chat_create_failed", error=str(e))

        logger.info("dispatch.dispatched", job_id=job_id, mode=mode,
                    staff=str(assigned_staff) if assigned_staff else None)
        return {**self._rec_dict(rec), "idempotent": False}

    async def get_dispatch_record(self, job_id: str) -> dict:
        r = await self.db.execute(select(DispatchRecord).where(DispatchRecord.job_id == job_id))
        rec = r.scalar_one_or_none()
        if not rec: raise NotFoundException("DispatchRecord", job_id)
        return self._rec_dict(rec)

    async def list_dispatch_records(self, tenant_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        q = select(DispatchRecord).where(DispatchRecord.tenant_id == tenant_id)            .order_by(DispatchRecord.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(DispatchRecord.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"dispatch_records": [self._rec_dict(x) for x in items], "has_next": has_next, "next_cursor": nc}

    async def accept_job(self, job_id: str, staff_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(DispatchRecord).where(DispatchRecord.job_id == job_id))
        rec = r.scalar_one_or_none()
        if not rec: raise NotFoundException("DispatchRecord", job_id)
        if rec.status == DispatchStatus.ACCEPTED:
            raise ServiceOSException("CONFLICT", "Job already accepted.")
        if rec.expires_at and rec.expires_at < utcnow():
            raise ServiceOSException("CONFLICT", "Acceptance window expired.")
        rec.status = DispatchStatus.ACCEPTED
        rec.assigned_staff_id = staff_id
        rec.accepted_at = utcnow()

        job_obj = await self._get_job(job_id)
        if job_obj:
            job_obj.assigned_staff_id = staff_id
            await self._advance_job(job_obj, JS.ACCEPTED, "Staff accepted dispatch")

        return self._rec_dict(rec)

    async def reject_job(self, job_id: str, staff_id: uuid.UUID, reason: str | None) -> dict:
        r = await self.db.execute(select(DispatchRecord).where(DispatchRecord.job_id == job_id))
        rec = r.scalar_one_or_none()
        if not rec: raise NotFoundException("DispatchRecord", job_id)
        self.db.add(DispatchEscalationLog(
            job_id=job_id, tenant_id=rec.tenant_id, staff_id=staff_id,
            attempt_no=rec.rejection_count + 1, outcome="rejected", reason=reason))
        rec.rejection_count += 1
        rec.escalation_count += 1
        if rec.escalation_count >= MAX_ESCALATION_ATTEMPTS:
            rec.status = DispatchStatus.ESCALATED
        return self._rec_dict(rec)

    async def reassign_job(self, job_id: str, new_staff_id: uuid.UUID, reason: str) -> dict:
        r = await self.db.execute(select(DispatchRecord).where(DispatchRecord.job_id == job_id))
        rec = r.scalar_one_or_none()
        if not rec: raise NotFoundException("DispatchRecord", job_id)
        old_staff = rec.assigned_staff_id
        rec.assigned_staff_id = new_staff_id
        rec.status = DispatchStatus.ASSIGNED

        job_obj = await self._get_job(job_id)
        if job_obj:
            job_obj.assigned_staff_id = new_staff_id

        self.db.add(DispatchEscalationLog(
            job_id=job_id, tenant_id=rec.tenant_id, staff_id=new_staff_id,
            attempt_no=rec.escalation_count + 1, outcome="reassigned", reason=reason))
        return {**self._rec_dict(rec), "previous_staff_id": str(old_staff) if old_staff else None}

    async def get_dispatch_queue(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(DispatchRecord).where(
            DispatchRecord.tenant_id == tenant_id,
            DispatchRecord.status.in_(["pending","assigned"])).order_by(DispatchRecord.created_at))
        items = r.scalars().all()
        return {"tenant_id": str(tenant_id), "queue_size": len(items),
                "items": [self._rec_dict(x) for x in items]}

    async def get_scoring_breakdown(self, job_id: str) -> dict:
        r = await self.db.execute(select(DispatchRecord).where(DispatchRecord.job_id == job_id))
        rec = r.scalar_one_or_none()
        if not rec: raise NotFoundException("DispatchRecord", job_id)
        return {"job_id": job_id, "dispatch_mode": rec.dispatch_mode,
                "score_weights": rec.score_weights, "candidates": rec.candidates_scored,
                "selected_staff_id": str(rec.assigned_staff_id) if rec.assigned_staff_id else None}
