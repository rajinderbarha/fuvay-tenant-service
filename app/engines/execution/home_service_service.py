"""Sprint 21 — Home Service Job Execution Service."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update, text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.execution.constants import (
    JOB_TRANSITIONS,
    EV_JOB_ACCEPTED, EV_JOB_REJECTED, EV_JOB_SCHEDULED, EV_CUSTOMER_CONTACTED,
    EV_ON_THE_WAY, EV_REACHED_SITE,
    EV_INSPECTION_STARTED, EV_INSPECTION_COMPLETED,
    EV_SERVICE_STARTED, EV_DIAGNOSIS_ADDED,
    EV_BEFORE_PHOTO, EV_AFTER_PHOTO, EV_WORK_NOTE_ADDED,
    EV_QUOTE_REQUIRED, EV_PARTS_REQUIRED,
    EV_WORK_DONE, EV_CUSTOMER_NOT_AVAIL, EV_JOB_CANCELLED,
    JS_ACCEPTED, JS_CANCELLED, JS_SCHEDULED,
    JS_ON_THE_WAY, JS_REACHED_SITE,
    JS_INSPECTION_STARTED, JS_INSPECTION_DONE,
    JS_SERVICE_STARTED, JS_WORK_DONE,
    JS_QUOTE_REQUIRED, JS_CUSTOMER_NOT_AVAIL,
    ERR_RECORD_NOT_FOUND, ERR_ACCESS_DENIED,
    ERR_INVALID_TRANSITION, ERR_REASON_REQUIRED,
    ERR_STAFF_NOT_ASSIGNED, ERR_PROVIDER_SCOPE_INVALID,
    # HS8B
    PARTS_STATUS_REQUESTED, PARTS_STATUS_BUSINESS_APPROVED,
    PARTS_STATUS_BUSINESS_REJECTED, PARTS_STATUS_CUSTOMER_APPROVAL_PENDING,
    PARTS_STATUS_CUSTOMER_APPROVED, PARTS_STATUS_CUSTOMER_REJECTED,
    PARTS_STATUS_INSTALLED, PARTS_REQUEST_ALLOWED_JOB_STATUSES,
    ERR_PART_NAME_REQUIRED, ERR_QUANTITY_INVALID, ERR_ESTIMATED_COST_INVALID,
    ERR_PARTS_REASON_REQUIRED, ERR_PARTS_NOT_ALLOWED_STATUS,
    ERR_PARTS_REQUEST_NOT_FOUND, ERR_PARTS_ALREADY_DECIDED,
    ERR_PARTS_NOT_APPROVED, ERR_PARTS_REJECTED_CANNOT_INSTALL,
    ERR_PARTS_CUSTOMER_DECISION_NOT_ALLOWED,
    JS_COMPLETED, COMPLETABLE_JOB_STATUSES, PAYMENT_MODE_HOME_SERVICES,
    ERR_WORK_SUMMARY_REQUIRED, ERR_COLLECTED_AMOUNT_REQUIRED,
    ERR_COLLECTED_AMOUNT_INVALID, ERR_PAYMENT_MODE_INVALID,
    ERR_JOB_NOT_COMPLETABLE, ERR_UNRESOLVED_PARTS_REQUESTS,
    ERR_ESTIMATE_REQUIRED, ERR_ESTIMATE_APPROVAL_REQUIRED,
    ERR_ESTIMATE_REVISION_REQUIRED, ERR_ESTIMATE_REJECTED,
    MSG_ESTIMATE_REQUIRED, MSG_ESTIMATE_APPROVAL_REQUIRED,
    MSG_ESTIMATE_REVISION_REQUIRED, MSG_ESTIMATE_REJECTED,
    ERR_JOB_TYPE_CONTEXT_UNRESOLVED, MSG_JOB_TYPE_CONTEXT_UNRESOLVED,
)
from app.engines.execution.models import (
    ServiceJobExecutionEvent,
    ServiceJobExecutionNote,
    ServiceJobMediaUpload,
)
from app.exceptions import ServiceOSException


def _now() -> datetime:
    return datetime.now(timezone.utc)


class HomeServiceJobExecutionService:

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _get_job(self, db: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID):
        from app.engines.final_records.models import ServiceJob
        res = await db.execute(
            select(ServiceJob).where(
                ServiceJob.id == job_id,
                ServiceJob.tenant_id == tenant_id,
            )
        )
        job = res.scalars().first()
        if not job:
            raise ServiceOSException(ERR_RECORD_NOT_FOUND, "Job not found.", status_code=404)
        return job

    def _assert_transition(self, current: str, target: str) -> None:
        # HS8 fix: this previously raised a bare ValueError, which no
        # execution router handler caught — every invalid status jump (and
        # every valid one, transitively, since this gate runs on every
        # transition) surfaced as a raw 500 INTERNAL_ERROR instead of the
        # required 422 INVALID_JOB_STATUS_TRANSITION. Live-verified: calling
        # /on-the-way again after a job reached work_done (terminal, no
        # allowed transitions) now returns a clean 422.
        allowed = JOB_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ServiceOSException(
                ERR_INVALID_TRANSITION,
                f"This job cannot move from {current} to {target} directly.",
                status_code=422,
            )

    def _assert_staff_owns_job(self, job, staff_member_id: uuid.UUID) -> None:
        if str(job.assigned_staff_id) != str(staff_member_id):
            raise ServiceOSException(
                ERR_STAFF_NOT_ASSIGNED,
                "This job is not assigned to you.",
                status_code=403,
            )

    async def _log_event(
        self,
        db: AsyncSession,
        job,
        event_type: str,
        old_status: str | None,
        new_status: str | None,
        actor_user_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        notes: str | None = None,
        staff_member_id: uuid.UUID | None = None,
        request_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        event = ServiceJobExecutionEvent(
            booking_id=job.booking_id,
            job_id=job.id,
            tenant_id=job.tenant_id,
            staff_member_id=staff_member_id or job.assigned_staff_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            event_type=event_type,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
            event_metadata=metadata,
            request_id=request_id,
        )
        db.add(event)

    async def _resolve_job_type_workflow(self, db: AsyncSession, job):
        """HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (spec section 16):
        resolve via the job's own STORED booking-time snapshot --
        ServiceJob.service_job_workflow_id -- an exact, immutable version
        row, rather than re-deriving "whichever ServiceJobWorkflow row is
        current right now" (Phase 2A.1's resolver). That mattered because
        job_type_blueprint_service.set_workflow() is now append-only
        (migration 171): an admin publishing a new version supersedes the
        old row but does not delete it, so a job created against version 3
        must keep resolving version 3 forever, even after version 4 exists.

        Falls back to a live (offering_id, job_type_id) "is_current" lookup
        ONLY for legacy jobs created before migration 171 added the snapshot
        column (service_job_workflow_id is NULL) -- those still fail closed
        on None per Phase 2A.1's existing behavior, and this fallback does
        not change their resolution for the CURRENT version at all.

        Returns the ServiceJobWorkflow row, or None if unresolved/invalid --
        callers MUST fail closed on None, never guess.
        """
        from app.engines.admin_catalog.models import MasterServiceJobType, ServiceJobWorkflow
        snapshot_id = getattr(job, "service_job_workflow_id", None)
        if snapshot_id is not None:
            return await db.get(ServiceJobWorkflow, snapshot_id)

        offering_id = getattr(job, "offering_id", None)
        job_type_id = getattr(job, "job_type_id", None)
        if offering_id is None or job_type_id is None:
            return None
        link = (await db.execute(
            select(MasterServiceJobType).where(
                MasterServiceJobType.master_service_id == offering_id,
                MasterServiceJobType.job_type_id == job_type_id,
                MasterServiceJobType.is_active.is_(True),
            )
        )).scalars().first()
        if link is None:
            return None  # job type does not belong to this service, or is inactive
        workflow = (await db.execute(
            select(ServiceJobWorkflow).where(
                ServiceJobWorkflow.master_service_id == offering_id,
                ServiceJobWorkflow.job_type_id == job_type_id,
                ServiceJobWorkflow.is_current.is_(True),
            )
        )).scalars().first()
        return workflow  # None if no published blueprint workflow exists yet

    async def _assert_quote_approval_satisfied(self, db: AsyncSession, job) -> None:
        """Central work-start guard (spec section 5, corrected by 2A.1).
        Called from the ONLY place ServiceJob.status is ever mutated in this
        engine (_set_status), so every existing and future caller that tries
        to reach JS_SERVICE_STARTED is covered -- there is no separate
        router/staff-app/tenant-app path that can bypass this."""
        workflow = await self._resolve_job_type_workflow(db, job)
        if workflow is None:
            raise ServiceOSException(
                ERR_JOB_TYPE_CONTEXT_UNRESOLVED, MSG_JOB_TYPE_CONTEXT_UNRESOLVED, status_code=409,
            )
        # A workflow whose price is created only after inspection/custom
        # diagnosis necessarily requires the customer's approval before
        # work. Treat the structural pricing behavior as authoritative too,
        # so a stale/misconfigured boolean cannot bypass the money gate.
        requires_quote_approval = bool(workflow.quote_approval_required) or (
            getattr(workflow, "pricing_behavior", None)
            in {"inspection_required", "custom_quote"}
        )
        if not requires_quote_approval:
            return
        from app.engines.quote_checklist.models import ServiceJobQuote
        from app.engines.quote_checklist.constants import (
            QS_SENT_TO_CUSTOMER, QS_CUSTOMER_APPROVED,
            QS_CUSTOMER_REJECTED, QS_REVISION_REQUESTED,
        )
        quote = (await db.execute(
            select(ServiceJobQuote).where(
                ServiceJobQuote.job_id == job.id,
                ServiceJobQuote.is_current.is_(True),
            )
        )).scalars().first()
        if quote is None:
            raise ServiceOSException(ERR_ESTIMATE_REQUIRED, MSG_ESTIMATE_REQUIRED, status_code=409)
        # Ownership is inherent: quote was looked up by this job's own id, so
        # it cannot belong to another job/tenant/customer. Only its STATUS
        # (and is_current, already filtered above) determines the outcome.
        if quote.status == QS_CUSTOMER_APPROVED:
            return
        if quote.status == QS_CUSTOMER_REJECTED:
            raise ServiceOSException(ERR_ESTIMATE_REJECTED, MSG_ESTIMATE_REJECTED, status_code=409)
        if quote.status == QS_REVISION_REQUESTED:
            raise ServiceOSException(ERR_ESTIMATE_REVISION_REQUIRED, MSG_ESTIMATE_REVISION_REQUIRED, status_code=409)
        if quote.status == QS_SENT_TO_CUSTOMER:
            raise ServiceOSException(ERR_ESTIMATE_APPROVAL_REQUIRED, MSG_ESTIMATE_APPROVAL_REQUIRED, status_code=409)
        # draft / submitted_to_provider / provider_approved / provider_rejected
        # / revised / expired / cancelled -- none of these is a customer
        # decision in flight; the customer has nothing to approve yet.
        raise ServiceOSException(ERR_ESTIMATE_REQUIRED, MSG_ESTIMATE_REQUIRED, status_code=409)

    async def get_work_start_status(self, db: AsyncSession, job) -> dict:
        """HOME-SERVICES-RUNTIME-SAFETY Phase 2A.1 (spec section 12): a
        read-only projection of the SAME guard logic _assert_quote_approval_
        satisfied enforces, for staff/tenant/customer API responses. Backend
        remains authoritative -- this exists so clients display the correct
        state WITHOUT re-implementing the resolution/decision logic
        themselves; it is not a second source of truth, it just narrates the
        one the guard already computes."""
        from app.engines.admin_catalog.models import JobTypeDefinition
        result = {
            "job_type_id": str(job.job_type_id) if getattr(job, "job_type_id", None) else None,
            "job_type_key": None,
            "job_type_label": None,
            "quote_approval_required": None,
            "quote_state": None,
            "can_start_work": False,
            "start_work_block_code": None,
        }
        if job.job_type_id:
            jt = await db.get(JobTypeDefinition, job.job_type_id)
            if jt:
                result["job_type_key"] = jt.key
                result["job_type_label"] = jt.label

        workflow = await self._resolve_job_type_workflow(db, job)
        if workflow is None:
            result["start_work_block_code"] = ERR_JOB_TYPE_CONTEXT_UNRESOLVED
            return result
        requires_quote_approval = bool(workflow.quote_approval_required) or (
            getattr(workflow, "pricing_behavior", None)
            in {"inspection_required", "custom_quote"}
        )
        result["quote_approval_required"] = requires_quote_approval

        try:
            await self._assert_quote_approval_satisfied(db, job)
            result["can_start_work"] = True
        except ServiceOSException as exc:
            result["start_work_block_code"] = exc.error_code

        if requires_quote_approval:
            from app.engines.quote_checklist.models import ServiceJobQuote
            quote = (await db.execute(
                select(ServiceJobQuote).where(
                    ServiceJobQuote.job_id == job.id,
                    ServiceJobQuote.is_current.is_(True),
                )
            )).scalars().first()
            result["quote_state"] = quote.status if quote else None
        return result

    async def _set_status(
        self,
        db: AsyncSession,
        job,
        new_status: str,
        event_type: str,
        actor_user_id: uuid.UUID | None,
        actor_role: str,
        notes: str | None = None,
        request_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        old = job.status
        self._assert_transition(old, new_status)
        if new_status == JS_SERVICE_STARTED:
            await self._assert_quote_approval_satisfied(db, job)
            # Customer platform fee gate (vertical_monetization).
            #
            # Real production gap fixed here: the monetization engine defined
            # this gate but nothing ever called it, so work could start on a
            # job whose customer platform fee was still unpaid -- the platform
            # then had no leverage to collect it. Sits beside the existing
            # quote-approval gate because both answer the same question:
            # "is this job actually authorised to begin?".
            #
            # This one is deliberately NOT swallowed: unlike charge CREATION
            # (best-effort), an unpaid required fee must genuinely block work.
            # The helper is a no-op when no policy/charge applies.
            from app.engines.vertical_monetization.charge_service import (
                assert_customer_platform_fee_paid_if_required,
            )
            await assert_customer_platform_fee_paid_if_required(db, job)
            await self._assert_checklist_satisfied(db, job)
        job.status = new_status
        job.updated_at = _now()
        db.add(job)
        await self._log_event(
            db, job, event_type, old, new_status,
            actor_user_id=actor_user_id, actor_role=actor_role,
            notes=notes, request_id=request_id, metadata=metadata,
        )
        await self.sync_booking_status(db, job.booking_id, new_status)

    # ── accept / reject ───────────────────────────────────────────────────────

    async def accept_job(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        staff_member_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None = None,
    ) -> dict:
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._set_status(
            db, job, JS_ACCEPTED, EV_JOB_ACCEPTED,
            actor_user_id=user_id, actor_role="staff",
            request_id=request_id,
        )
        await db.flush()
        return job.to_dict()

    async def reject_job(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        staff_member_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str,
        request_id: str | None = None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException(ERR_REASON_REQUIRED, "Reason is required.", status_code=422)
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._set_status(
            db, job, JS_CANCELLED, EV_JOB_REJECTED,
            actor_user_id=user_id, actor_role="staff",
            notes=reason, request_id=request_id,
        )
        job.failure_reason = reason
        db.add(job)
        await db.flush()
        return job.to_dict()

    # ── scheduling ────────────────────────────────────────────────────────────

    async def mark_scheduled(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        scheduled_date: str | None = None,
        scheduled_time_window: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        job = await self._get_job(db, job_id, tenant_id)
        if scheduled_date:
            from datetime import date as dateobj
            job.scheduled_date = dateobj.fromisoformat(scheduled_date)
        if scheduled_time_window:
            job.scheduled_time_window = scheduled_time_window
        await self._set_status(
            db, job, JS_SCHEDULED, EV_JOB_SCHEDULED,
            actor_user_id=user_id, actor_role="staff",
            request_id=request_id,
            metadata={"scheduled_date": scheduled_date, "window": scheduled_time_window},
        )
        await db.flush()
        return job.to_dict()

    # ── field progression ─────────────────────────────────────────────────────

    async def mark_on_the_way(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._set_status(db, job, JS_ON_THE_WAY, EV_ON_THE_WAY, user_id, "staff", request_id=request_id)
        await db.flush()
        return job.to_dict()

    async def log_customer_contacted(
        self, db, job_id, tenant_id, staff_member_id, user_id,
        notes: str | None = None, requirements: str | None = None, request_id=None,
    ):
        """Records the FIRST task on an auto-accepted job: the provider spoke to
        the customer, understood the request and captured requirements.

        Deliberately does NOT change job status -- the job is legitimately
        `accepted` before and after, so the existing JOB_TRANSITIONS graph is
        untouched. It writes the event that `_next_required_action` looks for,
        which is what moves the technician's next step on from
        "Call Customer & Confirm Requirements" to "Start Traveling".

        Idempotent: calling it twice does not stack duplicate events, so a
        double-tap in the field cannot corrupt the timeline.
        """
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)

        existing = (await db.execute(_sa_text(
            "SELECT 1 FROM service_job_execution_events "
            "WHERE job_id=:jid AND event_type=:et LIMIT 1"
        ), {"jid": str(job.id), "et": EV_CUSTOMER_CONTACTED})).fetchone()
        if existing is None:
            db.add(ServiceJobExecutionEvent(
                booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
                staff_member_id=staff_member_id, actor_user_id=user_id, actor_role="staff",
                event_type=EV_CUSTOMER_CONTACTED,
                old_status=job.status, new_status=job.status,
                notes=notes or "Provider contacted the customer to confirm requirements.",
                event_metadata={"requirements": requirements} if requirements else {},
                request_id=request_id,
            ))
            await db.flush()
        return {**job.to_dict(), "customer_contacted": True}

    async def mark_reached_site(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._set_status(db, job, JS_REACHED_SITE, EV_REACHED_SITE, user_id, "staff", request_id=request_id)
        await db.flush()
        return job.to_dict()

    async def start_inspection(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._set_status(db, job, JS_INSPECTION_STARTED, EV_INSPECTION_STARTED, user_id, "staff", request_id=request_id)
        await db.flush()
        return job.to_dict()

    async def complete_inspection(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        from app.engines.checklist_catalog.gate import assert_gate_satisfied
        from app.engines.checklist_catalog.constants import GATE_BEFORE_INSPECTION_COMPLETE
        await assert_gate_satisfied(db, job, GATE_BEFORE_INSPECTION_COMPLETE)
        await self._set_status(db, job, JS_INSPECTION_DONE, EV_INSPECTION_COMPLETED, user_id, "staff", request_id=request_id)
        await db.flush()
        return job.to_dict()

    async def start_service(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        # Estimate-approval gate is the pre-existing, independent authority
        # for work start (_set_status -> _assert_quote_approval_satisfied).
        # A required pre-work checklist gate complements it and never
        # substitutes for it -- both must pass.
        from app.engines.checklist_catalog.gate import assert_gate_satisfied
        from app.engines.checklist_catalog.constants import GATE_BEFORE_WORK_START
        await assert_gate_satisfied(db, job, GATE_BEFORE_WORK_START)
        await self._set_status(db, job, JS_SERVICE_STARTED, EV_SERVICE_STARTED, user_id, "staff", request_id=request_id)
        await db.flush()
        return job.to_dict()

    async def mark_work_done(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._set_status(db, job, JS_WORK_DONE, EV_WORK_DONE, user_id, "staff", request_id=request_id)
        await db.flush()
        return job.to_dict()

    async def mark_customer_not_available(self, db, job_id, tenant_id, staff_member_id, user_id, notes=None, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._set_status(db, job, JS_CUSTOMER_NOT_AVAIL, EV_CUSTOMER_NOT_AVAIL, user_id, "staff", notes=notes, request_id=request_id)
        await db.flush()
        return job.to_dict()

    async def mark_quote_required(self, db, job_id, tenant_id, staff_member_id, user_id, notes=None, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._set_status(db, job, JS_QUOTE_REQUIRED, EV_QUOTE_REQUIRED, user_id, "staff", notes=notes, request_id=request_id)
        await db.flush()
        return job.to_dict()

    async def mark_parts_required(self, db, job_id, tenant_id, staff_member_id, user_id, notes=None, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        # parts_required → quote_required (same terminal status for this sprint)
        await self._set_status(db, job, JS_QUOTE_REQUIRED, EV_PARTS_REQUIRED, user_id, "staff", notes=notes, request_id=request_id)
        await db.flush()
        return job.to_dict()

    async def _assert_checklist_satisfied(self, db: AsyncSession, job) -> None:
        """Workflow checklist gate.

        Real bug fixed here: `ServiceJobWorkflow.checklist_required` is a real,
        admin-configurable column, but nothing enforced it -- a technician
        could start work on a job type that explicitly requires a pre-work
        checklist without any checklist row ever existing, defeating the whole
        safety/compliance purpose of the setting.

        Fails closed ONLY when a workflow genuinely resolves AND explicitly
        requires a checklist. A legacy job with no resolvable workflow is
        unaffected, so this can never strand existing in-flight jobs.

        Satisfied by EITHER checklist generation:

        * a canonical `job_checklist_instances` row (checklist_catalog) that is
          COMPLETED or WAIVED -- what the technician app actually fills in, and
        * a legacy `quote_checklist.ServiceJobChecklist` row, for jobs from
          before the canonical engine existed.

        Accepting only the legacy row was a real dead end: the technician's own
        checklist surface writes canonical instances, so on a job type with
        checklist_required=True they could complete every point of the real
        checklist and start-service still answered 409 -- with nothing in any UI
        able to satisfy it. The gate blocked the work it was meant to certify.
        """
        workflow = await self._resolve_job_type_workflow(db, job)
        if workflow is None or not workflow.checklist_required:
            return

        from app.engines.checklist_catalog import constants as cc
        from app.engines.checklist_catalog.models import JobChecklistInstance
        canonical = (await db.execute(
            select(JobChecklistInstance.state).where(JobChecklistInstance.job_id == job.id)
        )).scalars().all()
        if any(state in (cc.INSTANCE_COMPLETED, cc.INSTANCE_WAIVED) for state in canonical):
            return

        from app.engines.quote_checklist.models import ServiceJobChecklist
        exists = (await db.execute(
            select(ServiceJobChecklist.id).where(ServiceJobChecklist.job_id == job.id).limit(1)
        )).scalars().first()
        if not exists:
            # Distinguish "no checklist has been authored/attached at all" from
            # "the one on this job is still open", so the technician is told
            # which of the two it is instead of a dead-end message.
            detail = (
                "The checklist on this job must be completed before work can start."
                if canonical else
                "A pre-work checklist is required for this job type before work can start."
            )
            raise ServiceOSException(
                "CHECKLIST_REQUIRED_BEFORE_WORK_START",
                detail,
                status_code=409,
            )

    async def cancel_job(self, db, job_id, tenant_id, user_id, reason: str, actor_role: str = "provider", request_id=None):
        if not reason or not reason.strip():
            raise ServiceOSException(ERR_REASON_REQUIRED, "Reason is required.", status_code=422)
        job = await self._get_job(db, job_id, tenant_id)

        # Workflow cancellation gate.
        #
        # Real bug fixed here: `ServiceJobWorkflow.allows_cancellation` is a
        # real, admin-configurable column that the catalog UI exposes, but
        # cancel_job never read it -- so a job type explicitly configured as
        # non-cancellable could still be cancelled by any provider/staff user.
        #
        # Fails closed ONLY when a workflow genuinely resolves AND explicitly
        # disallows cancellation. A legacy job with no resolvable workflow
        # (service_job_workflow_id NULL) stays cancellable, so this can never
        # strand an old job with no way to close it out.
        workflow = await self._resolve_job_type_workflow(db, job)
        if workflow is not None and not workflow.allows_cancellation:
            raise ServiceOSException(
                "JOB_CANCELLATION_NOT_ALLOWED",
                "This job type cannot be cancelled once it has been created.",
                status_code=422,
            )

        await self._set_status(db, job, JS_CANCELLED, EV_JOB_CANCELLED, user_id, actor_role, notes=reason, request_id=request_id)
        job.failure_reason = reason
        db.add(job)
        await db.flush()
        return job.to_dict()

    # ── notes / media ─────────────────────────────────────────────────────────

    async def add_diagnosis_note(self, db, job_id, tenant_id, staff_member_id, user_id, note_text: str, is_customer_visible: bool = False, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        note = ServiceJobExecutionNote(
            booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
            staff_member_id=staff_member_id, note_type="diagnosis",
            note_text=note_text, is_customer_visible=is_customer_visible,
            created_by_user_id=user_id,
        )
        db.add(note)
        await self._log_event(db, job, EV_DIAGNOSIS_ADDED, job.status, job.status, actor_user_id=user_id, actor_role="staff", request_id=request_id)
        await db.flush()
        return note.to_dict()

    async def add_work_note(self, db, job_id, tenant_id, staff_member_id, user_id, note_text: str, is_customer_visible: bool = False, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        note = ServiceJobExecutionNote(
            booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
            staff_member_id=staff_member_id, note_type="work_note",
            note_text=note_text, is_customer_visible=is_customer_visible,
            created_by_user_id=user_id,
        )
        db.add(note)
        await self._log_event(db, job, EV_WORK_NOTE_ADDED, job.status, job.status, actor_user_id=user_id, actor_role="staff", request_id=request_id)
        await db.flush()
        return note.to_dict()

    async def upload_job_media(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        staff_member_id: uuid.UUID,
        user_id: uuid.UUID,
        media_type: str,
        file_url: str,
        file_name: str | None = None,
        caption: str | None = None,
        is_customer_visible: bool = False,
        request_id: str | None = None,
    ) -> dict:
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        upload = ServiceJobMediaUpload(
            booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
            staff_member_id=staff_member_id, media_type=media_type,
            file_url=file_url, file_name=file_name, caption=caption,
            is_customer_visible=is_customer_visible,
            uploaded_by_user_id=user_id,
        )
        db.add(upload)
        ev_type = EV_BEFORE_PHOTO if media_type == "before_photo" else (EV_AFTER_PHOTO if media_type == "after_photo" else EV_WORK_NOTE_ADDED)
        await self._log_event(db, job, ev_type, job.status, job.status, actor_user_id=user_id, actor_role="staff", request_id=request_id)
        await db.flush()
        return upload.to_dict()

    # ── HS8B — real parts request workflow ───────────────────────────────────

    async def create_parts_request(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        staff_member_id: uuid.UUID,
        user_id: uuid.UUID,
        part_name: str,
        quantity: int,
        estimated_cost,
        reason: str,
        photo_ids: list | None = None,
        technician_note: str | None = None,
        customer_approval_required: bool = False,
        request_id: str | None = None,
    ) -> dict:
        from app.engines.execution.models import PartsRequest

        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)

        if not part_name or not part_name.strip():
            raise ServiceOSException(ERR_PART_NAME_REQUIRED, "Part name is required.", status_code=422)
        if quantity is None or quantity <= 0:
            raise ServiceOSException(ERR_QUANTITY_INVALID, "Quantity must be a positive number.", status_code=422)
        if estimated_cost is None or float(estimated_cost) < 0:
            raise ServiceOSException(ERR_ESTIMATED_COST_INVALID, "Estimated cost must be 0 or greater.", status_code=422)
        if not reason or not reason.strip():
            raise ServiceOSException(ERR_PARTS_REASON_REQUIRED, "Reason is required.", status_code=422)
        if job.status not in PARTS_REQUEST_ALLOWED_JOB_STATUSES:
            raise ServiceOSException(
                ERR_PARTS_NOT_ALLOWED_STATUS,
                "Parts can only be requested after inspection has started.",
                status_code=422,
            )

        pr = PartsRequest(
            job_id=job.id, tenant_id=tenant_id, technician_id=staff_member_id,
            part_name=part_name.strip(), quantity=quantity, estimated_cost=estimated_cost,
            reason=reason.strip(), photo_ids=photo_ids or [], technician_note=technician_note,
            customer_approval_required=customer_approval_required,
            business_approval_required=True,
            status=PARTS_STATUS_REQUESTED,
            request_id=request_id,
        )
        db.add(pr)
        # Reflect that parts are pending on the job itself (reuses the
        # existing quote_required terminal status — see HS8's
        # mark_parts_required for the same mapping).
        if job.status != JS_QUOTE_REQUIRED:
            await self._set_status(db, job, JS_QUOTE_REQUIRED, EV_PARTS_REQUIRED, user_id, "staff", request_id=request_id)
        await db.flush()
        return pr.to_dict()

    async def list_parts_requests(self, db: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID) -> list[dict]:
        from app.engines.execution.models import PartsRequest
        res = await db.execute(
            select(PartsRequest)
            .where(PartsRequest.job_id == job_id, PartsRequest.tenant_id == tenant_id)
            .order_by(PartsRequest.created_at.desc())
        )
        return [p.to_dict() for p in res.scalars().all()]

    async def _get_parts_request(self, db: AsyncSession, parts_request_id: uuid.UUID, tenant_id: uuid.UUID):
        from app.engines.execution.models import PartsRequest
        res = await db.execute(
            select(PartsRequest).where(
                PartsRequest.id == parts_request_id, PartsRequest.tenant_id == tenant_id,
            )
        )
        pr = res.scalars().first()
        if not pr:
            raise ServiceOSException(ERR_PARTS_REQUEST_NOT_FOUND, "Parts request not found.", status_code=404)
        return pr

    async def approve_parts_request(
        self, db: AsyncSession, parts_request_id: uuid.UUID, tenant_id: uuid.UUID,
        approver_user_id: uuid.UUID, request_id: str | None = None,
    ) -> dict:
        pr = await self._get_parts_request(db, parts_request_id, tenant_id)
        if pr.status != PARTS_STATUS_REQUESTED:
            raise ServiceOSException(
                ERR_PARTS_ALREADY_DECIDED,
                f"This parts request has already been {pr.status}.",
                status_code=422,
            )
        pr.status = (
            PARTS_STATUS_CUSTOMER_APPROVAL_PENDING if pr.customer_approval_required
            else PARTS_STATUS_BUSINESS_APPROVED
        )
        pr.approved_by = approver_user_id
        pr.approved_at = _now()
        db.add(pr)
        await db.flush()
        return pr.to_dict()

    async def reject_parts_request(
        self, db: AsyncSession, parts_request_id: uuid.UUID, tenant_id: uuid.UUID,
        rejector_user_id: uuid.UUID, reason: str | None = None, request_id: str | None = None,
    ) -> dict:
        pr = await self._get_parts_request(db, parts_request_id, tenant_id)
        if pr.status != PARTS_STATUS_REQUESTED:
            raise ServiceOSException(
                ERR_PARTS_ALREADY_DECIDED,
                f"This parts request has already been {pr.status}.",
                status_code=422,
            )
        pr.status = PARTS_STATUS_BUSINESS_REJECTED
        pr.rejected_by = rejector_user_id
        pr.rejected_at = _now()
        pr.rejection_reason = reason
        db.add(pr)
        await db.flush()
        return pr.to_dict()

    async def install_parts_request(
        self, db: AsyncSession, parts_request_id: uuid.UUID, tenant_id: uuid.UUID,
        request_id: str | None = None,
    ) -> dict:
        pr = await self._get_parts_request(db, parts_request_id, tenant_id)
        if pr.status in (PARTS_STATUS_BUSINESS_REJECTED, PARTS_STATUS_CUSTOMER_REJECTED):
            raise ServiceOSException(
                ERR_PARTS_REJECTED_CANNOT_INSTALL,
                "A rejected parts request cannot be installed.",
                status_code=422,
            )
        if pr.status not in (PARTS_STATUS_BUSINESS_APPROVED, PARTS_STATUS_CUSTOMER_APPROVED):
            raise ServiceOSException(
                ERR_PARTS_NOT_APPROVED,
                "Only an approved parts request can be marked installed.",
                status_code=422,
            )
        pr.status = PARTS_STATUS_INSTALLED
        db.add(pr)
        await db.flush()
        return pr.to_dict()

    # ── PARTS-APPROVAL phase — customer read/decide ──────────────────────────
    # Audit finding: `customer_approval_required` is a real, per-request
    # policy flag (set by staff at request time), and `approve_parts_request`
    # already computes a real `PARTS_STATUS_CUSTOMER_APPROVAL_PENDING` status
    # when it's set -- but no method anywhere transitioned a request OUT of
    # that status (a customer literally could not decide, and no customer
    # read endpoint existed at all). This is the smallest correct customer
    # extension (Outcome C): mirrors the already-proven quote_checklist
    # customer-decision pattern (ownership via job.customer_id, only a
    # PENDING request is actionable, decided requests fail safely on retry)
    # rather than inventing a second decision engine.
    #
    # A request is customer-visible only once the business has acted on it
    # (approved into either CUSTOMER_APPROVAL_PENDING or BUSINESS_APPROVED)
    # or reached a customer-facing terminal state -- a bare `requested` or
    # `business_rejected` request is internal technician/business back-and-
    # forth the customer has no proven need to see.
    _CUSTOMER_VISIBLE_PARTS_STATUSES = frozenset({
        PARTS_STATUS_CUSTOMER_APPROVAL_PENDING, PARTS_STATUS_CUSTOMER_APPROVED,
        PARTS_STATUS_CUSTOMER_REJECTED, PARTS_STATUS_BUSINESS_APPROVED, PARTS_STATUS_INSTALLED,
    })

    @staticmethod
    def _customer_safe_parts_request(pr) -> dict:
        decided_at = pr.approved_at or pr.rejected_at
        return {
            "parts_request_id":           str(pr.id),
            "status":                     pr.status,
            "part_name":                  pr.part_name,
            "quantity":                   pr.quantity,
            "unit_amount":                str(pr.estimated_cost),
            "line_total":                 str(Decimal(str(pr.estimated_cost)) * pr.quantity),
            "reason":                     pr.reason,
            "customer_approval_required": pr.customer_approval_required,
            "submitted_at":               pr.created_at.isoformat() if pr.created_at else None,
            "decided_at":                 decided_at.isoformat() if decided_at else None,
            "rejection_reason":           pr.rejection_reason if pr.status == PARTS_STATUS_CUSTOMER_REJECTED else None,
        }

    async def customer_list_parts_requests(self, db: AsyncSession, job_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
        from app.engines.execution.models import PartsRequest
        from app.engines.final_records.models import ServiceJob
        job = await db.get(ServiceJob, job_id)
        if not job or not job.customer_id or str(job.customer_id) != str(customer_id):
            raise ServiceOSException(ERR_PARTS_REQUEST_NOT_FOUND, "Parts request not found.", status_code=404)

        res = await db.execute(
            select(PartsRequest).where(PartsRequest.job_id == job_id).order_by(PartsRequest.created_at.desc())
        )
        visible = [p for p in res.scalars().all() if p.status in self._CUSTOMER_VISIBLE_PARTS_STATUSES]
        items = [self._customer_safe_parts_request(p) for p in visible]
        additional_total = sum((Decimal(i["line_total"]) for i in items), Decimal("0"))

        # Backend-authoritative "previous estimate" -- the job's own current
        # quote, the same customer-safe total the Quote Review card already
        # shows. Absent when no quote exists yet (a genuinely valid state --
        # a part can be requested before any estimate is sent).
        from app.engines.quote_checklist.models import ServiceJobQuote
        quote = (await db.execute(
            select(ServiceJobQuote).where(ServiceJobQuote.job_id == job_id, ServiceJobQuote.is_current.is_(True))
        )).scalars().first()
        previous_total = Decimal(str(quote.customer_payable_amount)) if quote else Decimal("0")
        currency = quote.currency if quote else "INR"

        return {
            "currency":                str(currency),
            "previous_estimated_total": str(previous_total),
            "additional_total":         str(additional_total),
            "new_estimated_total":      str(previous_total + additional_total),
            "items":                    items,
        }

    async def customer_decide_parts_request(
        self, db: AsyncSession, parts_request_id: uuid.UUID, customer_id: uuid.UUID,
        decision: str, reason: str | None, request_id: str | None = None,
    ) -> dict:
        from app.engines.execution.models import PartsRequest
        from app.engines.final_records.models import ServiceJob
        res = await db.execute(select(PartsRequest).where(PartsRequest.id == parts_request_id))
        pr = res.scalars().first()
        if not pr:
            raise ServiceOSException(ERR_PARTS_REQUEST_NOT_FOUND, "Parts request not found.", status_code=404)
        job = await db.get(ServiceJob, pr.job_id)
        # Enumeration-safe: a foreign customer's request and a genuinely
        # missing one return the identical NOT_FOUND, mirroring the same
        # pattern established for bookings/quotes.
        if not job or not job.customer_id or str(job.customer_id) != str(customer_id):
            raise ServiceOSException(ERR_PARTS_REQUEST_NOT_FOUND, "Parts request not found.", status_code=404)
        if not pr.customer_approval_required:
            raise ServiceOSException(
                ERR_PARTS_CUSTOMER_DECISION_NOT_ALLOWED,
                "This parts request does not require your approval.", status_code=403,
            )
        # Only a request currently awaiting the customer's decision is
        # actionable -- a repeat call after either decision, or a call
        # before business approval, fails safely rather than double-
        # transitioning or silently no-op'ing.
        if pr.status != PARTS_STATUS_CUSTOMER_APPROVAL_PENDING:
            raise ServiceOSException(
                ERR_PARTS_ALREADY_DECIDED,
                f"This parts request is not awaiting your decision (status: {pr.status}).", status_code=409,
            )
        now = _now()
        if decision == "approve":
            pr.status = PARTS_STATUS_CUSTOMER_APPROVED
            pr.approved_by = customer_id
            pr.approved_at = now
            event_type = "customer_part_approved"
        elif decision == "decline":
            if not reason or not reason.strip():
                raise ServiceOSException(ERR_PARTS_REASON_REQUIRED, "A reason is required to decline.", status_code=422)
            pr.status = PARTS_STATUS_CUSTOMER_REJECTED
            pr.rejected_by = customer_id
            pr.rejected_at = now
            pr.rejection_reason = reason.strip()
            event_type = "customer_part_declined"
        else:
            raise ServiceOSException("PARTS_INVALID_DECISION", "decision must be 'approve' or 'decline'.", status_code=422)
        db.add(pr)
        # Reuses the existing job-event log (no new audit table) -- job.status
        # itself is untouched by this decision (see phase report: no
        # canonical transition ties parts resolution to work resuming).
        await self._log_event(
            db, job, event_type, job.status, job.status,
            actor_user_id=customer_id, actor_role="customer",
            notes=f"parts_request_id={pr.id}", request_id=request_id,
        )
        await db.flush()
        return self._customer_safe_parts_request(pr)

    # ── HS8B — single validated completion action ────────────────────────────

    async def complete_job(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        staff_member_id: uuid.UUID,
        user_id: uuid.UUID,
        work_summary: str,
        collected_amount,
        payment_mode: str = PAYMENT_MODE_HOME_SERVICES,
        before_photo_ids: list | None = None,
        after_photo_ids: list | None = None,
        completion_photo_ids: list | None = None,
        customer_signature_id: str | None = None,
        technician_note: str | None = None,
        require_completion_photo: bool = False,
        require_resolved_parts: bool = True,
        request_id: str | None = None,
    ) -> dict:
        """HS8B — the single validated completion action every other HS8
        endpoint (`/work-done`, `/notes`, `/media`) was missing. Prepares
        `service_jobs.completion_data` for HS9's usage-credit deduction —
        does NOT deduct credits itself (out of scope, per the ticket)."""
        from app.engines.execution.models import PartsRequest

        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)

        if job.status not in COMPLETABLE_JOB_STATUSES:
            raise ServiceOSException(
                ERR_JOB_NOT_COMPLETABLE,
                f"Job cannot be completed from its current status ({job.status}).",
                status_code=422,
            )
        if not work_summary or not work_summary.strip():
            raise ServiceOSException(
                ERR_WORK_SUMMARY_REQUIRED,
                "Work summary is required before completing this job.",
                status_code=422,
            )
        if collected_amount is None:
            raise ServiceOSException(
                ERR_COLLECTED_AMOUNT_REQUIRED,
                "Collected amount is required for direct provider payment records.",
                status_code=422,
            )
        if float(collected_amount) < 0:
            raise ServiceOSException(
                ERR_COLLECTED_AMOUNT_INVALID,
                "Collected amount must be 0 or greater.",
                status_code=422,
            )
        if payment_mode != PAYMENT_MODE_HOME_SERVICES:
            raise ServiceOSException(
                ERR_PAYMENT_MODE_INVALID,
                "Payment mode must be customer_pays_provider_directly for Home Services.",
                status_code=422,
            )
        if require_completion_photo and not completion_photo_ids:
            raise ServiceOSException(
                "COMPLETION_PHOTO_REQUIRED",
                "A completion photo is required to complete this job.",
                status_code=422,
            )
        if require_resolved_parts:
            res = await db.execute(
                select(PartsRequest).where(
                    PartsRequest.job_id == job_id,
                    PartsRequest.tenant_id == tenant_id,
                    PartsRequest.status == PARTS_STATUS_REQUESTED,
                )
            )
            if res.scalars().first():
                raise ServiceOSException(
                    ERR_UNRESOLVED_PARTS_REQUESTS,
                    "This job has parts requests awaiting approval. Resolve them before completing.",
                    status_code=422,
                )

        from app.engines.checklist_catalog.gate import assert_gate_satisfied
        from app.engines.checklist_catalog.constants import GATE_BEFORE_JOB_COMPLETION
        await assert_gate_satisfied(db, job, GATE_BEFORE_JOB_COMPLETION)

        job.completion_data = {
            "work_summary": work_summary.strip(),
            "collected_amount": float(collected_amount),
            "payment_mode": payment_mode,
            "before_photo_ids": before_photo_ids or [],
            "after_photo_ids": after_photo_ids or [],
            "completion_photo_ids": completion_photo_ids or [],
            "customer_signature_id": customer_signature_id,
            "technician_note": technician_note,
            "completed_by_staff_id": str(staff_member_id),
            "completed_at": _now().isoformat(),
        }
        await self._set_status(db, job, JS_COMPLETED, EV_WORK_DONE, user_id, "staff", request_id=request_id)
        db.add(job)
        await db.flush()

        # HS9 — Completed Job Deduction. Prepared here (not a separate
        # HS9 sprint's own endpoint) since it must happen atomically with
        # the same completion that creates job.completion_data — a job
        # marked completed with no corresponding deduction attempt would
        # be a silent finance gap. Idempotent per job_id (see
        # usage_credit_deduction.deduct_for_completed_job).
        from app.engines.execution.usage_credit_deduction import deduct_for_completed_job
        from app.engines.final_records.models import ServiceBooking
        from app.engines.home_service_booking.models import HomeServiceBookingDraft

        booking = await db.get(ServiceBooking, job.booking_id)
        offering_type_id = brand_id_for_deduction = None
        if booking:
            draft = await db.get(HomeServiceBookingDraft, booking.draft_id)
            if draft:
                offering_type_id = draft.offering_type_id
                brand_id_for_deduction = draft.brand_id
        deduction = await deduct_for_completed_job(
            db, tenant_id=tenant_id, job_id=job.id, booking_id=job.booking_id,
            master_service_id=job.offering_id, offering_type_id=offering_type_id,
            brand_id=brand_id_for_deduction, category_id=job.category_id,
            job_type_id=job.job_type_id,
            job_price=Decimal(str(collected_amount)), request_id=request_id,
        )
        await db.flush()

        result = job.to_dict()
        result["usage_credit_deduction"] = deduction
        return result

    # ── timeline / status read ────────────────────────────────────────────────

    async def get_job_timeline(self, db: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID) -> list[dict]:
        res = await db.execute(
            select(ServiceJobExecutionEvent)
            .where(
                ServiceJobExecutionEvent.job_id == job_id,
                ServiceJobExecutionEvent.tenant_id == tenant_id,
            )
            .order_by(ServiceJobExecutionEvent.created_at.asc())
        )
        return [e.to_dict() for e in res.scalars().all()]

    async def get_job_notes(self, db: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID, customer_only: bool = False) -> list[dict]:
        q = select(ServiceJobExecutionNote).where(
            ServiceJobExecutionNote.job_id == job_id,
            ServiceJobExecutionNote.tenant_id == tenant_id,
        )
        if customer_only:
            q = q.where(ServiceJobExecutionNote.is_customer_visible == True)
        res = await db.execute(q.order_by(ServiceJobExecutionNote.created_at.asc()))
        return [n.to_dict() for n in res.scalars().all()]

    async def get_job_media(self, db: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID, customer_only: bool = False) -> list[dict]:
        q = select(ServiceJobMediaUpload).where(
            ServiceJobMediaUpload.job_id == job_id,
            ServiceJobMediaUpload.tenant_id == tenant_id,
        )
        if customer_only:
            q = q.where(ServiceJobMediaUpload.is_customer_visible == True)
        res = await db.execute(q.order_by(ServiceJobMediaUpload.created_at.asc()))
        return [m.to_dict() for m in res.scalars().all()]

    # ── booking sync ──────────────────────────────────────────────────────────

    async def sync_booking_status(self, db: AsyncSession, booking_id: uuid.UUID, new_job_status: str) -> None:
        from app.engines.final_records.models import ServiceBooking
        res = await db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
        booking = res.scalars().first()
        if booking:
            booking.status = new_job_status
            booking.updated_at = _now()
            db.add(booking)
