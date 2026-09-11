"""FINAL-L5-05D — Canonical admin exceptional mutations against service_jobs:
status override, force-close, void.

Centralizes the transition policy so no router hand-rolls its own status
logic. Reuses the real, already-shipped canonical status set (execution
engine's JOB_TRANSITIONS) rather than inventing a parallel simplified state
machine, and adds exactly two new terminal statuses this domain genuinely
lacked: force_closed, voided (status is an unconstrained String(40) column,
so no migration is required).

Force-close policy (derived from HS9's usage_credit_deduction.py, not
guessed): deduct_for_completed_job() requires a resolved master_service_id/
offering_type_id/brand_id and is idempotent per job_id via a real
UsageCreditLedger row (event_type="completed_job_deduction"). A force-closed
job has not necessarily gone through the normal completion flow's evidence
capture, so this module implements POLICY A -- force-close never creates a
Completed Job Deduction. If completion evidence genuinely exists, use the
real completion endpoint instead of force-close.

Void policy: BLOCK_VOID_AFTER_DEDUCTION -- if a completed_job_deduction
ledger row already exists for this job_id, void is refused (a real ledger
reversal is a separate, explicit finance action out of this module's scope,
consistent with rule 15: never silently rewrite ledger history).
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.engines.execution.constants import JOB_TRANSITIONS
from app.engines.execution.models import ServiceJobExecutionEvent
from app.exceptions import ServiceOSException

# ── new terminal statuses this domain adds ─────────────────────────────────
JS_FORCE_CLOSED = "force_closed"
JS_VOIDED = "voided"

TERMINAL_STATUSES = {"completed", "cancelled", "failed", JS_FORCE_CLOSED, JS_VOIDED}

# Status override is a narrow, curated escape hatch (rule: do not permit
# arbitrary status mutation) -- not "any status to any status". The only
# override target exposed today is "cancelled", from any non-terminal
# status, for jobs stuck by e.g. a technician who went silent mid-flow.
ADMIN_OVERRIDE_TARGETS = {"cancelled"}
ADMIN_REOPENABLE_STATUSES = {"cancelled", "failed"}

EVENT_STATUS_OVERRIDDEN = "admin_status_overridden"
EVENT_FORCE_CLOSED = "admin_force_closed"
EVENT_VOIDED = "admin_voided"

AUDIT_OP_STATUS_OVERRIDDEN = "service_job.status_overridden"
AUDIT_OP_FORCE_CLOSED = "service_job.force_closed"
AUDIT_OP_VOIDED = "service_job.voided"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AdminJobActionsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _load_job(self, job_id: uuid.UUID):
        from app.engines.final_records.models import ServiceJob
        res = await self.db.execute(select(ServiceJob).where(ServiceJob.id == job_id))
        job = res.scalars().first()
        if not job:
            raise ServiceOSException(error_code="JOB_NOT_FOUND", detail="Service job not found.", status_code=404)
        return job

    def get_allowed_override_targets(self, current_status: str) -> list[str]:
        if current_status in ADMIN_REOPENABLE_STATUSES:
            return ["pending_assignment"]
        if current_status in TERMINAL_STATUSES:
            return []
        return sorted(ADMIN_OVERRIDE_TARGETS)

    async def _has_deduction(self, job_id: uuid.UUID) -> bool:
        from app.engines.tenant_engine.models import UsageCreditLedger
        row = (await self.db.execute(
            select(UsageCreditLedger).where(
                UsageCreditLedger.job_id == job_id,
                UsageCreditLedger.event_type == "completed_job_deduction",
            )
        )).scalars().first()
        return row is not None

    async def _log_event(self, job, event_type: str, old_status: str, new_status: str,
                          actor_user_id: uuid.UUID | None, actor_role: str | None,
                          notes: str, request_id: str | None, metadata: dict) -> None:
        self.db.add(ServiceJobExecutionEvent(
            booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
            staff_member_id=job.assigned_staff_id, actor_user_id=actor_user_id,
            actor_role=actor_role, event_type=event_type, old_status=old_status,
            new_status=new_status, notes=notes, event_metadata=metadata, request_id=request_id,
        ))

    # ── status override ─────────────────────────────────────────────────────
    async def override_status(
        self, job_id: uuid.UUID, target_status: str, expected_current_status: str,
        reason_code: str, reason: str, actor_user_id: uuid.UUID, actor_role: str,
        request_id: str | None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException(error_code="REASON_REQUIRED", detail="A detailed reason is required.", status_code=422)
        job = await self._load_job(job_id)
        current = job.status
        if current != expected_current_status:
            raise ServiceOSException(
                error_code="JOB_STATUS_CONFLICT",
                detail=f"Job status changed since you last viewed it (now '{current}').",
                status_code=409,
            )
        reopening = current in ADMIN_REOPENABLE_STATUSES and target_status == "pending_assignment"
        if current in TERMINAL_STATUSES and not reopening:
            raise ServiceOSException(error_code="JOB_ALREADY_TERMINAL", detail=f"Job is already in a terminal status ('{current}').", status_code=409)
        if target_status not in ADMIN_OVERRIDE_TARGETS and not reopening:
            raise ServiceOSException(error_code="INVALID_ADMIN_OVERRIDE_TRANSITION",
                                      detail=f"'{target_status}' is not an allowed admin override target from '{current}'.", status_code=422)

        job.status = target_status
        job.updated_at = _now()
        if reopening:
            job.assigned_staff_id = None
            job.assignment_status = "unassigned"
            job.failure_reason = None
            from app.engines.final_records.models import ServiceBooking
            booking = await self.db.get(ServiceBooking, job.booking_id)
            if booking:
                booking.status = "pending_assignment"
                booking.assignment_status = "unassigned"
                booking.failure_reason = None
                self.db.add(booking)
            from app.engines.home_service_assignment.models import ServiceJobAssignment
            current_assignment = (await self.db.execute(select(ServiceJobAssignment).where(
                ServiceJobAssignment.job_id == job.id,
                ServiceJobAssignment.is_current.is_(True),
            ))).scalars().first()
            if current_assignment:
                current_assignment.is_current = False
                current_assignment.assignment_status = "cancelled"
                current_assignment.cancelled_at = _now()
                current_assignment.notes = reason
                self.db.add(current_assignment)
        self.db.add(job)
        await self.db.flush()

        await self._log_event(job, EVENT_STATUS_OVERRIDDEN, current, target_status,
                               actor_user_id, actor_role, reason, request_id,
                               {"reason_code": reason_code})
        await record_platform_audit(
            self.db, operation=AUDIT_OP_STATUS_OVERRIDDEN, engine_id="execution",
            entity_id=str(job_id), entity_type="service_job", tenant_id=job.tenant_id,
            actor_id=actor_user_id, actor_role=actor_role, request_id=request_id,
            before={"status": current}, after={"status": target_status, "reason_code": reason_code, "reason": reason},
        )
        await self.db.commit()
        return {"job_id": str(job_id), "previous_status": current, "new_status": target_status,
                "reason_code": reason_code, "reason": reason}

    # ── force-close (POLICY A: never creates a deduction) ──────────────────
    async def force_close(
        self, job_id: uuid.UUID, expected_current_status: str, reason_code: str, reason: str,
        completion_note: str | None, actor_user_id: uuid.UUID, actor_role: str, request_id: str | None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException(error_code="REASON_REQUIRED", detail="A detailed reason is required.", status_code=422)
        job = await self._load_job(job_id)
        current = job.status
        if current != expected_current_status:
            raise ServiceOSException(error_code="JOB_STATUS_CONFLICT",
                                      detail=f"Job status changed since you last viewed it (now '{current}').", status_code=409)
        if current == JS_FORCE_CLOSED:
            raise ServiceOSException(error_code="JOB_ALREADY_CLOSED", detail="Job is already force-closed.", status_code=409)
        if current in TERMINAL_STATUSES:
            raise ServiceOSException(error_code="JOB_FORCE_CLOSE_NOT_ALLOWED",
                                      detail=f"Job is already terminal ('{current}') and cannot be force-closed.", status_code=409)

        job.status = JS_FORCE_CLOSED
        job.updated_at = _now()
        if completion_note:
            job.completion_data = {**(job.completion_data or {}), "force_close_note": completion_note}
        self.db.add(job)
        await self.db.flush()

        await self._log_event(job, EVENT_FORCE_CLOSED, current, JS_FORCE_CLOSED,
                               actor_user_id, actor_role, reason, request_id,
                               {"reason_code": reason_code, "deduction_created": False,
                                "policy": "POLICY_A_NO_AUTOMATIC_DEDUCTION"})
        await record_platform_audit(
            self.db, operation=AUDIT_OP_FORCE_CLOSED, engine_id="execution",
            entity_id=str(job_id), entity_type="service_job", tenant_id=job.tenant_id,
            actor_id=actor_user_id, actor_role=actor_role, request_id=request_id,
            before={"status": current}, after={"status": JS_FORCE_CLOSED, "reason_code": reason_code, "reason": reason},
        )
        await self.db.commit()
        return {"job_id": str(job_id), "previous_status": current, "new_status": JS_FORCE_CLOSED,
                "deduction_created": False,
                "deduction_policy": "Force-close never creates a Completed Job Deduction automatically. "
                                     "If real completion evidence exists, a finance review must apply it manually."}

    # ── void (BLOCK_VOID_AFTER_DEDUCTION) ───────────────────────────────────
    async def void(
        self, job_id: uuid.UUID, expected_current_status: str, reason_code: str, reason: str,
        actor_user_id: uuid.UUID, actor_role: str, request_id: str | None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException(error_code="REASON_REQUIRED", detail="A detailed reason is required.", status_code=422)
        job = await self._load_job(job_id)
        current = job.status
        if current != expected_current_status:
            raise ServiceOSException(error_code="JOB_STATUS_CONFLICT",
                                      detail=f"Job status changed since you last viewed it (now '{current}').", status_code=409)
        if current == JS_VOIDED:
            raise ServiceOSException(error_code="JOB_ALREADY_VOIDED", detail="Job is already voided.", status_code=409)
        if await self._has_deduction(job_id):
            raise ServiceOSException(
                error_code="JOB_DEDUCTION_REVERSAL_REQUIRED",
                detail="This job already has a Completed Job Deduction. Voiding is blocked to protect ledger "
                       "integrity -- a manual finance reversal must be recorded separately before this job can be voided.",
                status_code=409,
            )

        job.status = JS_VOIDED
        job.updated_at = _now()
        self.db.add(job)
        await self.db.flush()

        await self._log_event(job, EVENT_VOIDED, current, JS_VOIDED,
                               actor_user_id, actor_role, reason, request_id,
                               {"reason_code": reason_code})
        await record_platform_audit(
            self.db, operation=AUDIT_OP_VOIDED, engine_id="execution",
            entity_id=str(job_id), entity_type="service_job", tenant_id=job.tenant_id,
            actor_id=actor_user_id, actor_role=actor_role, request_id=request_id,
            before={"status": current}, after={"status": JS_VOIDED, "reason_code": reason_code, "reason": reason},
        )
        await self.db.commit()
        return {"job_id": str(job_id), "previous_status": current, "new_status": JS_VOIDED}
