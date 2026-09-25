"""Sprint 21 — Home Service Job Execution Service."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update, text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.execution.constants import (
    JOB_TRANSITIONS,
    EV_JOB_ACCEPTED, EV_JOB_REJECTED, EV_JOB_SCHEDULED, EV_CUSTOMER_CONTACTED,
    EV_CUSTOMER_CALL_DIALED,
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
    ERR_CANCELLATION_NOT_ALLOWED,
    # HS8B
    PARTS_STATUS_REQUESTED, PARTS_STATUS_BUSINESS_APPROVED,
    PARTS_STATUS_BUSINESS_REJECTED, PARTS_STATUS_CUSTOMER_APPROVAL_PENDING,
    PARTS_STATUS_CUSTOMER_APPROVED, PARTS_STATUS_CUSTOMER_REJECTED,
    PARTS_STATUS_INSTALLED, PARTS_REQUEST_ALLOWED_JOB_STATUSES,
    ERR_PARTS_INVENTORY_ITEM_REQUIRED, ERR_PARTS_INVENTORY_ITEM_UNAVAILABLE,
    ERR_PARTS_INSUFFICIENT_STOCK, ERR_QUANTITY_INVALID,
    ERR_PARTS_PENDING_BLOCK_WORK_DONE, PARTS_PENDING_STATUSES, PARTS_APPROVED_STATUSES,
    PARTS_STATUS_CANCELLED, EV_PARTS_REQUEST_CANCELLED,
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


def _local_today():
    """Today where the work happens; scheduled_date is a local calendar date."""
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


async def customer_already_contacted(db: AsyncSession, job_id) -> bool:
    """Whether the provider has logged the required first customer call.

    Presence of a real `customer_contacted` execution event -- never inferred
    from status or elapsed time, so the "call the customer first" step can only
    be satisfied by actually doing it.

    Lives here, beside `log_customer_contacted` which writes the event, so
    every technician projection answers the question the same way. They
    disagreed before: the Home screen asked and the mobile Job Detail screen
    did not, so Home offered "Call Customer & Confirm Requirements" while the
    screen that button opens offered "Start Traveling" for the same job.
    """
    row = (await db.execute(_sa_text(
        "SELECT 1 FROM service_job_execution_events "
        "WHERE job_id=:jid AND event_type=:et LIMIT 1"
    ), {"jid": str(job_id), "et": EV_CUSTOMER_CONTACTED})).fetchone()
    return row is not None



async def customer_call_times(db: AsyncSession, job_id, limit: int = 10) -> tuple[int, list[str]]:
    """How many times the technician tapped Call on this job, and the most
    recent tap times (newest first, ISO 8601)."""
    rows = (await db.execute(_sa_text(
        "SELECT created_at, count(*) OVER () AS total FROM service_job_execution_events "
        "WHERE job_id=:jid AND event_type=:et ORDER BY created_at DESC LIMIT :lim"
    ), {"jid": str(job_id), "et": EV_CUSTOMER_CALL_DIALED, "lim": limit})).fetchall()
    total = int(rows[0].total) if rows else 0
    return total, [row.created_at.isoformat() for row in rows]


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
        #
        # Delegates to transition_guard so the platform graph lives in exactly
        # one place. The workflow layer needs the job row and a session, so it
        # is applied by `_assert_transition_for_job` below; this synchronous
        # form remains for the callers that only have two status strings.
        from app.engines.execution.transition_guard import is_status_move_allowed
        if not is_status_move_allowed(current, target):
            raise ServiceOSException(
                ERR_INVALID_TRANSITION,
                f"This job cannot move from {current} to {target} directly.",
                status_code=422,
            )

    async def _assert_transition_for_job(self, db, job, target: str,
                                         actor_role: str | None = None) -> None:
        """Full gate: platform graph AND the job's own workflow.

        Used where the job row is already loaded. The workflow layer can only
        narrow what the platform graph permits, and stays silent for any job
        whose workflow defines no transitions — so nothing changes for jobs
        created before a journey was authored.
        """
        from app.engines.execution.transition_guard import assert_transition_allowed
        await assert_transition_allowed(db, job, target, actor_role)

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

    async def quote_gates_work(self, db: AsyncSession, job) -> bool:
        """Whether this job's price IS the estimate (inspection/custom quote).

        True for a job whose work may only start after the customer approves
        an estimate. False for a fixed-price job, where an estimate can only
        be an optional extra on top of the booked price: declining it must
        not close the job, and approving it must add to -- not replace -- the
        booked price. Fails closed (True) when the workflow cannot be
        resolved, which keeps the previous behaviour for legacy jobs.
        """
        workflow = await self._resolve_job_type_workflow(db, job)
        if workflow is None:
            return True
        if bool(workflow.quote_approval_required) or (
            getattr(workflow, "pricing_behavior", None)
            in {"inspection_required", "custom_quote"}
        ):
            return True
        from app.engines.final_records.models import ServiceBooking
        booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
        if isinstance(booking, ServiceBooking):
            snapshot = booking.price_snapshot or {}
            return bool(snapshot.get("requires_inspection_estimate")) or (
                snapshot.get("pricing_mode") in {"inspection", "inspection_required", "custom_quote"}
                or snapshot.get("pricing_model") in {"inspection", "inspection_required", "custom_quote"}
            )
        return False

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
        # The booking-time price contract is also immutable authority.  If
        # pricing resolved to inspection/estimate, a stale admin workflow
        # boolean must never let work begin before customer approval.
        if not requires_quote_approval:
            from app.engines.final_records.models import ServiceBooking
            booking = await db.get(ServiceBooking, job.booking_id)
            if isinstance(booking, ServiceBooking):
                snapshot = booking.price_snapshot or {}
                requires_quote_approval = bool(snapshot.get("requires_inspection_estimate")) or (
                    snapshot.get("pricing_mode") in {"inspection", "inspection_required", "custom_quote"}
                    or snapshot.get("pricing_model") in {"inspection", "inspection_required", "custom_quote"}
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
            "inspection_required": None,
            "quote_approval_required": None,
            "quote_state": None,
            "can_start_work": False,
            "start_work_block_code": None,
            "start_work_block_message": None,
        }
        if job.job_type_id:
            jt = await db.get(JobTypeDefinition, job.job_type_id)
            if jt:
                result["job_type_key"] = jt.key
                result["job_type_label"] = jt.label

        workflow = await self._resolve_job_type_workflow(db, job)
        if workflow is None:
            result["start_work_block_code"] = ERR_JOB_TYPE_CONTEXT_UNRESOLVED
            result["start_work_block_message"] = MSG_JOB_TYPE_CONTEXT_UNRESOLVED
            return result
        # A workflow whose price is only knowable after diagnosis inspects by
        # definition, so the structural pricing behavior counts too -- the same
        # reasoning `requires_quote_approval` below already applies. Without
        # this, a blueprint with the boolean unset but `inspection_required`
        # pricing skipped straight to `start-service`, which the work-start
        # gate then refuses for want of an approved quote.
        result["inspection_required"] = bool(workflow.inspection_required) or (
            getattr(workflow, "pricing_behavior", None) == "inspection_required"
        )
        requires_quote_approval = bool(workflow.quote_approval_required) or (
            getattr(workflow, "pricing_behavior", None)
            in {"inspection_required", "custom_quote"}
        )
        if not requires_quote_approval:
            from app.engines.final_records.models import ServiceBooking
            booking = await db.get(ServiceBooking, job.booking_id)
            if isinstance(booking, ServiceBooking):
                snapshot = booking.price_snapshot or {}
                requires_quote_approval = bool(snapshot.get("requires_inspection_estimate")) or (
                    snapshot.get("pricing_mode") in {"inspection", "inspection_required", "custom_quote"}
                    or snapshot.get("pricing_model") in {"inspection", "inspection_required", "custom_quote"}
                )
        result["quote_approval_required"] = requires_quote_approval

        try:
            await self._assert_quote_approval_satisfied(db, job)
            result["can_start_work"] = True
        except ServiceOSException as exc:
            result["start_work_block_code"] = exc.error_code
            result["start_work_block_message"] = exc.detail

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
        # Serialize concurrent transitions on THIS job before validating one.
        #
        # `_get_job` reads without a lock, so the guard below was a plain
        # read-modify-write: two requests arriving together -- a double tap, or
        # the mobile app retrying a request that actually succeeded after its
        # socket timed out -- both read the same `old`, both passed the
        # transition check, and both wrote. That produced duplicate execution
        # events and ran every side effect twice, including the ones that
        # charge a fee.
        #
        # Taking the row lock here makes the check and the write atomic: the
        # lock is held for the rest of the transaction, so the loser blocks
        # until the winner commits, then sees the new status and is rejected
        # with a 409 instead of silently double-applying. This mirrors the
        # optimistic check `admin_job_actions` already performs.
        from app.engines.final_records.models import ServiceJob as _ServiceJob

        locked_status = await db.scalar(
            select(_ServiceJob.status).where(_ServiceJob.id == job.id).with_for_update()
        )
        if locked_status is None:
            raise ServiceOSException(ERR_RECORD_NOT_FOUND, "Job not found.", status_code=404)
        if locked_status != old:
            raise ServiceOSException(
                "JOB_STATUS_CONFLICT",
                f"Job status changed since it was read (now '{locked_status}'). "
                "Reload the job and try again.",
                status_code=409,
            )
        # Re-applying the status the job already holds is a no-op, not a
        # transition: a retry of a request that succeeded must not log a second
        # event or fire the side effects again.
        if old == new_status:
            return
        # Every job status change in the home-services pipeline funnels through
        # here, so this is where the job's own workflow gets its say. It can only
        # narrow the platform graph, and stays silent unless the job's workflow
        # actually describes both the current and target statuses.
        await self._assert_transition_for_job(db, job, new_status, actor_role)
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
        transition_time = _now()
        job.status = new_status
        job.updated_at = transition_time
        db.add(job)
        from app.engines.execution.stage_timer_service import build_stage_timer_snapshot
        stage_timer = await build_stage_timer_snapshot(
            db, job, new_status, entered_at=transition_time,
        )
        event_metadata = dict(metadata or {})
        if stage_timer is not None:
            event_metadata["stage_timer"] = stage_timer
        await self._log_event(
            db, job, event_type, old, new_status,
            actor_user_id=actor_user_id, actor_role=actor_role,
            notes=notes, request_id=request_id, metadata=event_metadata or None,
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
        from app.engines.messaging_gateway.booking_updates import send_stage_update
        await send_stage_update(db, job, JS_SCHEDULED)
        return job.to_dict()

    # ── field progression ─────────────────────────────────────────────────────

    async def mark_on_the_way(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        # The app shows "Call customer & confirm requirements" as the first
        # task, but nothing enforced it: travel could start (and the customer
        # be told a technician was coming) before anyone had spoken to them.
        if not await customer_already_contacted(db, job.id):
            raise ServiceOSException(
                "CUSTOMER_CONTACT_REQUIRED",
                "Call the customer and confirm the requirements before starting travel.",
                status_code=409,
            )
        # Travel belongs to the visit day. Marking "on the way" days early
        # sent the customer an on-the-way message for a visit still to come.
        if job.scheduled_date and job.scheduled_date > _local_today():
            raise ServiceOSException(
                "TRAVEL_BEFORE_VISIT_DAY",
                f"This visit is scheduled for {job.scheduled_date.isoformat()}. "
                "Travel can be started on the day of the visit.",
                status_code=409,
            )
        # Do not let a technician create a misleading "on the way" state
        # hours before the promised visit.  The provider's configured travel
        # buffer is the earliest legitimate departure time; the same value is
        # snapshotted by the stage timer and enforced by travel_timeout.
        from app.engines.weather.slots import slot_start
        starts_at = slot_start(job.scheduled_date, job.scheduled_time_window)
        if starts_at is not None:
            configured = (await db.execute(_sa_text(
                "SELECT buffer_minutes_between_jobs "
                "FROM tenant_booking_window_settings WHERE tenant_id=:tenant_id"
            ), {"tenant_id": str(job.tenant_id)})).scalar()
            try:
                travel_minutes = min(1440, max(5, int(configured or 30)))
            except (TypeError, ValueError):
                travel_minutes = 30
            earliest_departure = starts_at - timedelta(minutes=travel_minutes)
            now_local = datetime.now(starts_at.tzinfo)
            if now_local < earliest_departure:
                raise ServiceOSException(
                    "TRAVEL_TOO_EARLY",
                    "Travel can be started near the booked slot, not before "
                    f"{earliest_departure.strftime('%d %b %Y, %I:%M %p')}.",
                    status_code=409,
                    context={"earliest_departure_at": earliest_departure.isoformat()},
                )
        await self._set_status(db, job, JS_ON_THE_WAY, EV_ON_THE_WAY, user_id, "staff", request_id=request_id)
        # Repair/enrol the scheduled-arrival SLA at the moment travel starts.
        # This protects legacy jobs that predate assignment-time SLA stamping.
        if job.sla_due_at is None and job.sla_enforcement_started_at is None:
            from app.engines.execution.sla_breach_service import stamp_due_at
            await stamp_due_at(db, job.id)
        await db.flush()
        from app.engines.messaging_gateway.booking_updates import send_on_the_way
        await send_on_the_way(db, job)
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

    async def record_customer_call(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        """The technician tapped Call customer: record the tap and hand back the
        number to dial.

        The number is released only here, so the phone dialer cannot open
        without the tap being recorded. It is the number the customer gave for
        this booking (the Instagram chat collects it), read at call time and
        never copied into the event.

        Dialing does not prove the customer answered, so this does not satisfy
        the contact-first task. `customer-contacted` still does that.
        """
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        from app.engines.masked_calling import constants as calling
        from app.engines.masked_calling.service import _customer_number, contact_window_open

        if not contact_window_open(job):
            message = (
                "Customer contact access ended when this job's warranty expired."
                if str(job.status) == "completed"
                else "This job is closed, so the customer cannot be called from it."
            )
            raise ServiceOSException(
                calling.ERR_JOB_NOT_CALLABLE,
                message,
                status_code=409,
            )
        phone = await _customer_number(
            db, {"booking_id": job.booking_id, "customer_id": job.customer_id},
        )
        if not phone:
            raise ServiceOSException(
                calling.ERR_NO_CUSTOMER_NUMBER,
                "There is no contact number for this customer.",
                status_code=422,
            )
        db.add(ServiceJobExecutionEvent(
            booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
            staff_member_id=staff_member_id, actor_user_id=user_id, actor_role="staff",
            event_type=EV_CUSTOMER_CALL_DIALED,
            old_status=job.status, new_status=job.status,
            notes="Technician tapped Call customer.",
            event_metadata={"via": "phone_dialer"},
            request_id=request_id,
        ))
        await db.flush()
        call_count, recent = await customer_call_times(db, job.id)
        return {
            "job_id": str(job.id),
            "customer_phone": phone,
            "called_at": recent[0],
            "call_count": call_count,
            "recent_call_times": recent,
        }

    async def mark_reached_site(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        # Instagram addresses in Punjab are frequently approximate.  For
        # those bookings a technician GPS fix is evidence, but the customer's
        # in-chat decision/doorstep code is the authority that advances the
        # job.  Do not stop SLA or claim arrival at this point.
        from app.engines.final_records.models import ServiceBooking
        booking = await db.get(ServiceBooking, job.booking_id)
        if booking and booking.source_channel == "instagram":
            from app.engines.vertical_monetization.runtime_operations import (
                get_home_services_operations_policy,
            )
            policy = await get_home_services_operations_policy(db)
            if policy.arrival_customer_confirmation_enabled:
                from app.engines.execution.arrival_confirmation_service import (
                    request_arrival_confirmation,
                )
                return await request_arrival_confirmation(
                    db, job=job, staff_member_id=staff_member_id,
                    requested_by_user_id=user_id,
                )
        from app.engines.execution.arrival_verification import verify_arrival
        arrival = await verify_arrival(db, job=job, staff_member_id=staff_member_id)
        await self._set_status(db, job, JS_REACHED_SITE, EV_REACHED_SITE, user_id, "staff", request_id=request_id)
        # This SLA measures missed arrival, so a recorded arrival ends it.
        # Inspection/work-start have their own gates and must not turn a timely
        # arrival into another no-show deduction.
        from app.engines.execution.sla_breach_service import stop_sla
        await stop_sla(db, job.id)
        job.sla_due_at = None
        job.sla_next_penalty_at = None
        job.sla_stopped_at = _now()
        await db.flush()
        from app.engines.messaging_gateway.booking_updates import send_arrived
        await send_arrived(db, job)
        return {**job.to_dict(), "arrival_verification": arrival}

    async def start_inspection(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        workflow = await self._resolve_job_type_workflow(db, job)
        # Same rule the job-detail projection uses (get_work_start_status):
        # an inspection-priced blueprint inspects even if its boolean is
        # unset. The two disagreed, so the app offered an inspection the
        # server then refused.
        inspection_required = workflow is None or bool(workflow.inspection_required) or (
            getattr(workflow, "pricing_behavior", None) == "inspection_required"
        )
        if not inspection_required:
            message = (
                "This job has no inspection step. Create and send the estimate instead."
                if await self.quote_gates_work(db, job) else
                "This fixed-price service does not require an inspection. Start the work instead."
            )
            raise ServiceOSException("INSPECTION_NOT_REQUIRED", message, status_code=409)
        if not job.arrival_verified_at:
            raise ServiceOSException(
                "ARRIVAL_VERIFICATION_REQUIRED",
                "Verified arrival at the customer address is required before inspection.",
                status_code=409,
            )
        await self._set_status(db, job, JS_INSPECTION_STARTED, EV_INSPECTION_STARTED, user_id, "staff", request_id=request_id)
        from app.engines.execution.sla_breach_service import stop_sla
        await stop_sla(db, job.id)
        job.sla_due_at = None
        job.sla_next_penalty_at = None
        job.sla_stopped_at = _now()
        await db.flush()
        from app.engines.messaging_gateway.booking_updates import send_stage_update
        await send_stage_update(db, job, JS_INSPECTION_STARTED)
        return job.to_dict()

    async def complete_inspection(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        from app.engines.checklist_catalog.gate import assert_gate_satisfied
        from app.engines.checklist_catalog.constants import GATE_BEFORE_INSPECTION_COMPLETE
        await assert_gate_satisfied(db, job, GATE_BEFORE_INSPECTION_COMPLETE)
        await self._set_status(db, job, JS_INSPECTION_DONE, EV_INSPECTION_COMPLETED, user_id, "staff", request_id=request_id)
        await db.flush()
        from app.engines.messaging_gateway.booking_updates import send_stage_update
        await send_stage_update(db, job, JS_INSPECTION_DONE)
        return job.to_dict()

    async def start_service(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        if not job.arrival_verified_at:
            raise ServiceOSException(
                "ARRIVAL_VERIFICATION_REQUIRED",
                "Verified arrival at the customer address is required before work starts.",
                status_code=409,
            )
        # Estimate-approval gate is the pre-existing, independent authority
        # for work start (_set_status -> _assert_quote_approval_satisfied).
        # A required pre-work checklist gate complements it and never
        # substitutes for it -- both must pass.
        from app.engines.checklist_catalog.gate import assert_gate_satisfied
        from app.engines.checklist_catalog.constants import GATE_BEFORE_WORK_START
        await assert_gate_satisfied(db, job, GATE_BEFORE_WORK_START)
        await self._set_status(db, job, JS_SERVICE_STARTED, EV_SERVICE_STARTED, user_id, "staff", request_id=request_id)
        # Fixed-price workflows legitimately skip inspection; verified work
        # start is therefore also an SLA stop point.
        from app.engines.execution.sla_breach_service import stop_sla
        await stop_sla(db, job.id)
        job.sla_due_at = None
        job.sla_next_penalty_at = None
        job.sla_stopped_at = _now()
        await db.flush()
        # Offer this moment to the monetization policy. It charges only if
        # `work_started` is the configured event; otherwise nothing is written
        # and the job stays chargeable at its real moment.
        from app.engines.execution.usage_credit_deduction import attempt_charge_at_event
        await attempt_charge_at_event(
            db, job=job, chargeable_event="work_started", request_id=request_id)
        from app.engines.messaging_gateway.booking_updates import send_stage_update
        await send_stage_update(db, job, JS_SERVICE_STARTED)
        return job.to_dict()

    async def mark_work_done(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._assert_no_pending_parts(db, job)
        await self._set_status(db, job, JS_WORK_DONE, EV_WORK_DONE, user_id, "staff", request_id=request_id)
        await self._install_approved_parts(db, job)
        await db.flush()
        from app.engines.execution.usage_credit_deduction import attempt_charge_at_event
        await attempt_charge_at_event(
            db, job=job, chargeable_event="work_done", request_id=request_id)
        from app.engines.messaging_gateway.booking_updates import send_stage_update
        await send_stage_update(db, job, JS_WORK_DONE)
        return job.to_dict()

    async def mark_customer_not_available(self, db, job_id, tenant_id, staff_member_id, user_id, notes=None, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._set_status(db, job, JS_CUSTOMER_NOT_AVAIL, EV_CUSTOMER_NOT_AVAIL, user_id, "staff", notes=notes, request_id=request_id)
        await db.flush()
        from app.engines.messaging_gateway.booking_updates import send_stage_update
        await send_stage_update(db, job, JS_CUSTOMER_NOT_AVAIL)
        return job.to_dict()

    async def mark_quote_required(self, db, job_id, tenant_id, staff_member_id, user_id, notes=None, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        await self._set_status(db, job, JS_QUOTE_REQUIRED, EV_QUOTE_REQUIRED, user_id, "staff", notes=notes, request_id=request_id)
        await db.flush()
        from app.engines.messaging_gateway.booking_updates import send_stage_update
        await send_stage_update(db, job, JS_QUOTE_REQUIRED)
        return job.to_dict()

    async def mark_parts_required(self, db, job_id, tenant_id, staff_member_id, user_id, notes=None, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        # parts_required → quote_required (same terminal status for this sprint)
        await self._set_status(db, job, JS_QUOTE_REQUIRED, EV_PARTS_REQUIRED, user_id, "staff", notes=notes, request_id=request_id)
        await db.flush()
        from app.engines.messaging_gateway.booking_updates import send_stage_update
        await send_stage_update(db, job, JS_QUOTE_REQUIRED)
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

        # Canonical mappings supersede the legacy workflow boolean. Their
        # explicit completion_gate is the sole authority for *when* a
        # checklist blocks (pre-work, inspection, completion, or handover).
        # Treating checklist_required as an unconditional pre-work gate
        # deadlocked modern EXECUTION/COMPLETION checklists: technicians had
        # to certify work outcomes before they were allowed to start work.
        # Only query the canonical engine for persisted ServiceJob-shaped
        # records. Legacy/imported records that only carry an id must continue
        # through the compatibility gate below.
        offering_id = getattr(job, "offering_id", None)
        job_type_id = getattr(job, "job_type_id", None)
        if isinstance(offering_id, uuid.UUID) and isinstance(job_type_id, uuid.UUID):
            from app.engines.checklist_catalog.service import get_applicable_mappings
            if await get_applicable_mappings(db, job):
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
                ERR_CANCELLATION_NOT_ALLOWED,
                "This job type cannot be cancelled once it has been created.",
                status_code=422,
            )

        await self._set_status(db, job, JS_CANCELLED, EV_JOB_CANCELLED, user_id, actor_role, notes=reason, request_id=request_id)
        job.failure_reason = reason
        job.assignment_status = "cancelled"

        # Close the assignment record too. Previously the job became
        # cancelled while its assignment remained current/accepted, leaving
        # dispatch, the staff app and the booking with three different states.
        from app.engines.home_service_assignment.models import ServiceJobAssignment
        current_assignment = (await db.execute(
            select(ServiceJobAssignment).where(
                ServiceJobAssignment.job_id == job.id,
                ServiceJobAssignment.is_current.is_(True),
            )
        )).scalars().first()
        if current_assignment:
            current_assignment.is_current = False
            current_assignment.assignment_status = "cancelled"
            current_assignment.cancelled_at = _now()
            current_assignment.notes = reason
            db.add(current_assignment)

        from app.engines.final_records.models import ServiceBooking
        booking = await db.get(ServiceBooking, job.booking_id)
        if booking:
            booking.status = JS_CANCELLED
            booking.assignment_status = "cancelled"
            booking.failure_reason = reason
            db.add(booking)
        db.add(job)
        await db.flush()

        if actor_role == "provider":
            from app.engines.tenant_engine.health import refresh_provider_operational_health
            await refresh_provider_operational_health(db, tenant_id)
        # A customer whose booking the provider cancelled heard nothing at
        # all: they waited for a technician who was never coming.
        from app.engines.messaging_gateway.booking_updates import send_provider_cancelled
        await send_provider_cancelled(db, job, reason)
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

    @staticmethod
    async def _inventory_part(db: AsyncSession, tenant_id: uuid.UUID, item_id: uuid.UUID):
        """A live item from this provider's own inventory, or a clear refusal."""
        from app.engines.inventory.models import InventoryItem
        item = (await db.execute(
            select(InventoryItem).where(
                InventoryItem.id == item_id, InventoryItem.tenant_id == tenant_id,
                InventoryItem.is_active.is_(True), InventoryItem.status == "published",
            )
        )).scalars().first()
        if not item:
            raise ServiceOSException(
                ERR_PARTS_INVENTORY_ITEM_UNAVAILABLE,
                "That part is no longer in your provider's inventory.",
                status_code=404,
            )
        return item

    @staticmethod
    def _inventory_part_price(item) -> Decimal:
        # The customer price, with the same fallback the inventory workspace uses.
        price = item.selling_price if item.selling_price is not None else item.unit_cost
        return Decimal(str(price))

    @staticmethod
    async def _available_stock(db: AsyncSession, tenant_id: uuid.UUID, item_ids: list) -> dict:
        """Unreserved stock per item, as (location_id, available, staff_id) for
        each active location holding it."""
        from app.engines.inventory.models import StockBalance, StockLocation
        rows = (await db.execute(
            select(
                StockBalance.item_id, StockBalance.location_id,
                StockBalance.quantity - StockBalance.reserved_qty, StockLocation.staff_id,
            )
            .join(StockLocation, StockLocation.id == StockBalance.location_id)
            .where(
                StockBalance.tenant_id == tenant_id, StockLocation.tenant_id == tenant_id,
                StockLocation.is_active.is_(True), StockBalance.item_id.in_(item_ids),
            )
        )).all()
        stock: dict = {}
        for item_id, location_id, available, staff_id in rows:
            stock.setdefault(item_id, []).append((location_id, max(0, int(available)), staff_id))
        return stock

    async def _stock_location_for_part(
        self, db: AsyncSession, tenant_id: uuid.UUID, item, quantity: int, holders: set[str],
    ) -> uuid.UUID:
        """Where the part will be reserved from once the customer approves.

        A reservation draws on one location, so one location must hold the
        whole quantity. The technician's own stock (a van) comes first, then
        the fullest location.
        """
        locations = (await self._available_stock(db, tenant_id, [item.id])).get(item.id, [])
        usable = sorted(
            (loc for loc in locations if loc[1] >= quantity),
            key=lambda loc: (str(loc[2]) not in holders, -loc[1]),
        )
        if not usable:
            best = max((loc[1] for loc in locations), default=0)
            raise ServiceOSException(
                ERR_PARTS_INSUFFICIENT_STOCK,
                f"Only {best} of {item.name} in stock." if best else f"{item.name} is out of stock.",
                status_code=409,
                context={"available": best, "requested": quantity},
            )
        return usable[0][0]

    async def list_parts_catalog(
        self, db: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID,
        staff_member_id: uuid.UUID, search: str | None = None,
    ) -> dict:
        """The provider's inventory as a technician picks parts from it: the
        customer price and stock on hand, never the provider's cost or margin."""
        from sqlalchemy import or_
        from app.engines.inventory.models import InventoryItem

        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        q = select(InventoryItem).where(
            InventoryItem.tenant_id == tenant_id,
            InventoryItem.is_active.is_(True), InventoryItem.status == "published",
        )
        term = (search or "").strip()
        if term:
            like = f"%{term}%"
            q = q.where(or_(InventoryItem.name.ilike(like), InventoryItem.sku.ilike(like),
                            InventoryItem.category.ilike(like)))
        items = (await db.execute(q.order_by(InventoryItem.name).limit(200))).scalars().all()
        stock = await self._available_stock(db, tenant_id, [item.id for item in items])
        parts = []
        for item in items:
            locations = stock.get(item.id, [])
            parts.append({
                "item_id": str(item.id),
                "name": item.name,
                "sku": item.sku,
                "category": item.category,
                "unit": item.unit,
                "unit_price": float(self._inventory_part_price(item)),
                "warranty": item.warranty,
                "available_qty": sum(loc[1] for loc in locations),
                # The most one request can take: a reservation draws on one location.
                "max_request_qty": max((loc[1] for loc in locations), default=0),
            })
        # In-stock parts first; the sort is stable, so names stay alphabetical.
        parts.sort(key=lambda part: part["max_request_qty"] <= 0)
        return {"items": parts}

    async def create_parts_request(
        self,
        db: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        staff_member_id: uuid.UUID,
        user_id: uuid.UUID,
        inventory_item_id: uuid.UUID | None,
        quantity: int,
        reason: str,
        photo_ids: list | None = None,
        technician_note: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        """A technician's part request, always picked from the provider's inventory.

        The provider already priced the item for customers in its catalogue,
        so the request needs no second business sign-off: it goes straight to
        the customer. Stock is reserved only once the customer approves
        (`customer_decide_parts_request`). The caller commits, then asks the
        customer with `notify_customer_parts_pending`.
        """
        from app.engines.execution.models import PartsRequest

        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)

        if not inventory_item_id:
            raise ServiceOSException(
                ERR_PARTS_INVENTORY_ITEM_REQUIRED,
                "Choose the part from your provider's inventory.",
                status_code=422,
            )
        if quantity is None or quantity <= 0:
            raise ServiceOSException(ERR_QUANTITY_INVALID, "Quantity must be a positive number.", status_code=422)
        if not reason or not reason.strip():
            raise ServiceOSException(ERR_PARTS_REASON_REQUIRED, "Reason is required.", status_code=422)
        if job.status not in PARTS_REQUEST_ALLOWED_JOB_STATUSES:
            raise ServiceOSException(
                ERR_PARTS_NOT_ALLOWED_STATUS,
                "Parts can only be requested after inspection has started.",
                status_code=422,
            )

        item = await self._inventory_part(db, tenant_id, inventory_item_id)
        stock_location_id = await self._stock_location_for_part(
            db, tenant_id, item, quantity, holders={str(staff_member_id), str(user_id)},
        )
        unit_price = self._inventory_part_price(item)

        pr = PartsRequest(
            job_id=job.id, tenant_id=tenant_id, technician_id=staff_member_id,
            part_name=item.name, quantity=quantity, estimated_cost=unit_price,
            reason=reason.strip(), photo_ids=photo_ids or [], technician_note=technician_note,
            customer_approval_required=True,
            business_approval_required=False,
            status=PARTS_STATUS_CUSTOMER_APPROVAL_PENDING,
            procurement_source="inventory",
            inventory_item_id=item.id,
            stock_location_id=stock_location_id,
            unit_price_snapshot=unit_price,
            request_id=request_id,
        )
        db.add(pr)
        # A part found during inspection reshapes the estimate, so the job
        # waits in quote_required (HS8's mark_parts_required mapping). Once work
        # has started it stays started: dashboards read quote_required as
        # "send an estimate", and the technician would be offered Start work
        # again. The pending part blocks mark_work_done instead.
        if job.status not in (JS_QUOTE_REQUIRED, JS_SERVICE_STARTED):
            await self._set_status(db, job, JS_QUOTE_REQUIRED, EV_PARTS_REQUIRED, user_id, "staff", request_id=request_id)
        else:
            await self._log_event(
                db, job, EV_PARTS_REQUIRED, job.status, job.status,
                actor_user_id=user_id, actor_role="staff", request_id=request_id,
            )
        await db.flush()
        return pr.to_dict()

    async def cancel_parts_request(
        self, db: AsyncSession, job_id: uuid.UUID, parts_request_id: uuid.UUID,
        tenant_id: uuid.UUID, staff_member_id: uuid.UUID, user_id: uuid.UUID,
        request_id: str | None = None,
    ) -> dict:
        """The technician cancels a part request nobody has decided on yet.

        Without this a customer who never answers in chat would block the job
        forever: nothing else moves a request out of customer_approval_pending.
        No stock is held before approval, so there is nothing to release.
        """
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
        pr = await self._get_parts_request(db, parts_request_id, tenant_id)
        if pr.job_id != job.id:
            raise ServiceOSException(ERR_PARTS_REQUEST_NOT_FOUND, "Parts request not found.", status_code=404)
        if pr.status not in PARTS_PENDING_STATUSES:
            raise ServiceOSException(
                ERR_PARTS_ALREADY_DECIDED,
                f"This parts request has already been {pr.status.replace('_', ' ')}.",
                status_code=409,
            )
        pr.status = PARTS_STATUS_CANCELLED
        db.add(pr)
        await self._log_event(
            db, job, EV_PARTS_REQUEST_CANCELLED, job.status, job.status,
            actor_user_id=user_id, actor_role="staff",
            notes=f"parts_request_id={pr.id}", request_id=request_id,
        )
        await db.flush()
        return pr.to_dict()

    async def _assert_no_pending_parts(self, db: AsyncSession, job) -> None:
        from app.engines.execution.models import PartsRequest
        pending = (await db.execute(
            select(PartsRequest).where(
                PartsRequest.job_id == job.id, PartsRequest.status.in_(PARTS_PENDING_STATUSES),
            )
        )).scalars().all()
        if pending:
            raise ServiceOSException(
                ERR_PARTS_PENDING_BLOCK_WORK_DONE,
                "A part is still waiting for approval. Wait for the customer's answer, "
                "or cancel the request, before finishing work.",
                status_code=409,
                context={"pending_part_request_ids": [str(p.id) for p in pending]},
            )

    async def _install_approved_parts(self, db: AsyncSession, job) -> None:
        """Finishing work means the approved parts went in: mark them installed
        and deduct inventory parts from the stock reserved for them.

        Nothing else consumes a reservation in practice (the provider install
        endpoint has no screen), so without this stock stayed reserved forever.
        A legacy inventory part with no reservation is left approved rather
        than blocking the technician; the provider can reconcile it.
        """
        from app.engines.execution.models import PartsRequest
        approved = (await db.execute(
            select(PartsRequest).where(
                PartsRequest.job_id == job.id, PartsRequest.status.in_(PARTS_APPROVED_STATUSES),
            )
        )).scalars().all()
        for pr in approved:
            if pr.procurement_source == "inventory":
                if not pr.stock_reservation_id:
                    import structlog
                    structlog.get_logger(__name__).warning(
                        "parts_request.install_skipped_no_reservation", parts_request_id=str(pr.id))
                    continue
                await self._consume_parts_inventory(db, pr)
            pr.status = PARTS_STATUS_INSTALLED
            db.add(pr)

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

    @staticmethod
    def _parts_inventory_job_ref(pr) -> str:
        # One job can legitimately request the same item more than once.  The
        # request id makes the inventory reservation key unique and auditable.
        return f"{pr.job_id}:{pr.id}"

    async def _reserve_parts_inventory(self, db: AsyncSession, pr, actor_id: uuid.UUID) -> None:
        if pr.procurement_source != "inventory":
            return
        if not pr.inventory_item_id or not pr.stock_location_id:
            raise ServiceOSException(
                "PARTS_INVENTORY_ALLOCATION_REQUIRED",
                "Select an inventory item and stock location before approval.",
                status_code=422,
            )
        from app.engines.inventory.service import InventoryService
        inv = InventoryService(db, actor_id=actor_id, actor_role="system",
                               actor_tenant_id=pr.tenant_id)
        if pr.unit_price_snapshot is None:
            # A price already shown to the customer is the price they approved;
            # a later catalogue change must not rewrite it.
            item = await inv.get_item(pr.inventory_item_id)
            pr.estimated_cost = Decimal(str(item["selling_price"]))
            pr.unit_price_snapshot = Decimal(str(item["selling_price"]))
        result = await inv.create_reservation(
            self._parts_inventory_job_ref(pr), pr.inventory_item_id,
            pr.stock_location_id, pr.tenant_id, pr.quantity,
        )
        pr.stock_reservation_id = uuid.UUID(result["reservation_id"])

    async def _consume_parts_inventory(self, db: AsyncSession, pr) -> None:
        if pr.procurement_source != "inventory":
            return
        if not pr.inventory_item_id or not pr.stock_location_id or not pr.stock_reservation_id:
            raise ServiceOSException(
                "PARTS_INVENTORY_RESERVATION_MISSING",
                "This part has no active stock reservation. Reallocate stock before installation.",
                status_code=409,
            )
        from app.engines.inventory.service import InventoryService
        inv = InventoryService(db, actor_role="system", actor_tenant_id=pr.tenant_id)
        await inv.confirm_reservation(
            self._parts_inventory_job_ref(pr), pr.inventory_item_id,
            pr.stock_location_id, pr.tenant_id,
        )

    async def approve_parts_request(
        self, db: AsyncSession, parts_request_id: uuid.UUID, tenant_id: uuid.UUID,
        approver_user_id: uuid.UUID, procurement_source: str = "external",
        inventory_item_id: uuid.UUID | None = None,
        stock_location_id: uuid.UUID | None = None,
        request_id: str | None = None,
    ) -> dict:
        pr = await self._get_parts_request(db, parts_request_id, tenant_id)
        if pr.status != PARTS_STATUS_REQUESTED:
            raise ServiceOSException(
                ERR_PARTS_ALREADY_DECIDED,
                f"This parts request has already been {pr.status}.",
                status_code=422,
            )
        if procurement_source not in {"inventory", "external"}:
            raise ServiceOSException("PARTS_PROCUREMENT_SOURCE_INVALID",
                                     "Procurement source must be inventory or external.", status_code=422)
        if procurement_source == "inventory" and (not inventory_item_id or not stock_location_id):
            raise ServiceOSException("PARTS_INVENTORY_ALLOCATION_REQUIRED",
                                     "Select an inventory item and stock location.", status_code=422)
        pr.procurement_source = procurement_source
        pr.inventory_item_id = inventory_item_id if procurement_source == "inventory" else None
        pr.stock_location_id = stock_location_id if procurement_source == "inventory" else None
        if procurement_source == "inventory":
            # Price it from the catalogue now, so a customer asked to approve
            # the part sees what they will actually pay.
            item = await self._inventory_part(db, tenant_id, inventory_item_id)
            pr.estimated_cost = pr.unit_price_snapshot = self._inventory_part_price(item)
        pr.status = (
            PARTS_STATUS_CUSTOMER_APPROVAL_PENDING if pr.customer_approval_required
            else PARTS_STATUS_BUSINESS_APPROVED
        )
        pr.approved_by = approver_user_id
        pr.approved_at = _now()
        # Hold stock only when all required approvals are complete.  A request
        # awaiting the customer cannot consume provider availability yet.
        if not pr.customer_approval_required:
            await self._reserve_parts_inventory(db, pr, approver_user_id)
        db.add(pr)
        await db.flush()
        return pr.to_dict()

    @staticmethod
    async def notify_customer_parts_pending(part: dict) -> bool:
        """Ask the customer to approve a part on the WhatsApp/Instagram chat
        they booked through. `part` is the request's `to_dict()`.

        Call it only after the request is committed: the customer's tap looks
        the request up, and a message must never announce a part that rolled
        back. It uses its own session, like quote notifications, so a messaging
        failure can never abort the caller's transaction.

        Only lands inside Meta's 24-hour customer service window; outside it the
        request waits for the customer's next message, where the chat shows it
        first. Best-effort: returns whether a message went out.
        """
        import structlog
        from app.database import get_session_factory
        from app.engines.final_records.models import ServiceBooking, ServiceJob
        from app.engines.messaging_gateway.constants import PICKER_SEP, PICK_PARTS
        from app.engines.messaging_gateway.flow import (
            PARTS_HEADER, PARTS_LINE, PARTS_REASON, _money,
        )
        from app.engines.messaging_gateway.service import notify_customer

        if part.get("status") != PARTS_STATUS_CUSTOMER_APPROVAL_PENDING:
            return False
        try:
            async with get_session_factory()() as messaging_db:
                try:
                    job = await messaging_db.get(ServiceJob, uuid.UUID(str(part["job_id"])))
                    if not job or not job.customer_id:
                        return False
                    booking = (
                        await messaging_db.get(ServiceBooking, job.booking_id)
                        if job.booking_id else None
                    )
                    line_total = Decimal(str(part["estimated_cost"])) * int(part["quantity"])
                    lines = [PARTS_HEADER, ""]
                    if booking and booking.booking_number:
                        lines.append(f"Booking {booking.booking_number}")
                    lines.append(PARTS_LINE.format(
                        part=part["part_name"], quantity=part["quantity"],
                        total=_money("INR", line_total)))
                    if part.get("reason"):
                        lines.append(PARTS_REASON.format(reason=str(part["reason"])[:300]))
                    part_request_id = str(part["parts_request_id"])
                    sent = await notify_customer(
                        messaging_db, job.customer_id, "\n".join(lines),
                        rows=[
                            {"id": PICKER_SEP.join((PICK_PARTS, part_request_id, "approve")),
                             "title": "Approve part"},
                            {"id": PICKER_SEP.join((PICK_PARTS, part_request_id, "decline")),
                             "title": "Decline part"},
                        ],
                        source_ai_session_id=(booking.ai_session_id if booking else None),
                        section_title="Part approval",
                    )
                    await messaging_db.commit()
                    return sent
                except Exception:
                    await messaging_db.rollback()
                    raise
        except Exception as exc:  # noqa: BLE001
            structlog.get_logger(__name__).warning(
                "parts_request.customer_notify_failed",
                parts_request_id=str(part.get("parts_request_id")), error=str(exc))
            return False

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
        await self._consume_parts_inventory(db, pr)
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
            await self._reserve_parts_inventory(db, pr, customer_id)
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
        from app.engines.execution.models import CompletionProof, PartsRequest
        from app.engines.invoice_payment.models import ServicePaymentRecord
        from app.engines.invoice_payment.direct_payments_constants import RS_CONFIRMED
        from app.engines.invoice_payment.direct_payments_service import DirectPaymentsService

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

        # These are server-side closure invariants, not merely UI steps.  The
        # mobile wrapper already checked them, but the older staff endpoint
        # called this canonical method directly and could bypass proof,
        # customer handover and payment reconciliation entirely.
        proof = (await db.execute(select(CompletionProof).where(
            CompletionProof.job_id == job.id,
            CompletionProof.tenant_id == tenant_id,
        ))).scalars().first()
        if not proof or proof.status != "submitted":
            raise ServiceOSException(
                "COMPLETION_PROOF_NOT_SUBMITTED",
                "Submit the completion proof before completing this job.",
                status_code=409,
            )
        if proof.handover_status not in ("acknowledged", "customer_unavailable"):
            raise ServiceOSException(
                "CUSTOMER_HANDOVER_NOT_ACKNOWLEDGED",
                "Customer handover must be acknowledged before completing this job.",
                status_code=409,
            )
        payment = (await db.execute(select(ServicePaymentRecord).where(
            ServicePaymentRecord.job_id == job.id,
            ServicePaymentRecord.tenant_id == tenant_id,
        ).order_by(ServicePaymentRecord.created_at.desc()).limit(1))).scalars().first()
        if payment is None:
            raise ServiceOSException(
                "PAYMENT_NOT_DECLARED",
                "Record the customer's direct payment before completing this job.",
                status_code=409,
            )
        if DirectPaymentsService.derive_status(payment) != RS_CONFIRMED:
            raise ServiceOSException(
                "PAYMENT_NOT_RECONCILED",
                "Customer payment must be confirmed before completing this job.",
                status_code=409,
            )
        if abs(Decimal(str(collected_amount)) - Decimal(str(payment.collected_amount))) > Decimal("0.01"):
            raise ServiceOSException(
                "COLLECTED_AMOUNT_MISMATCH",
                "The completion amount must match the confirmed payment record.",
                status_code=409,
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
        from app.engines.invoice_payment.models import ServiceInvoice

        # Use the issued invoice snapshot as the financial basis. The amount
        # collected from the customer can include the platform fee, so using
        # it as the commission base would charge commission on Fuvay's
        # own fee and recalculating that fee would create fee-on-fee drift.
        invoice = (await db.execute(
            select(ServiceInvoice).where(
                ServiceInvoice.job_id == job.id,
                ServiceInvoice.tenant_id == tenant_id,
                ServiceInvoice.status != "cancelled",
            ).order_by(ServiceInvoice.created_at.desc()).limit(1)
        )).scalars().first()
        # Customer-approved parts are billed at exactly the approved price;
        # the provider's charge is on the service value without them.
        from app.engines.invoice_payment.invoice_service import approved_parts_amount
        service_charge_basis = (
            max(
                Decimal("0"),
                Decimal(str(invoice.total_amount)) - await approved_parts_amount(db, invoice.id),
            )
            if invoice is not None
            else Decimal(str(collected_amount))
        )
        platform_fee_snapshot = (
            Decimal(str(invoice.platform_fee_amount or 0)) if invoice is not None else None
        )
        # Snapshot the provider-owned warranty at completion. The service row
        # is job-type scoped, just like pricing, and the platform floor is five
        # days. This value must not drift when the live offering changes later.
        from app.engines.admin_catalog.models import TenantService
        tenant_service = (await db.execute(
            select(TenantService).where(
                TenantService.tenant_id == tenant_id,
                TenantService.master_service_id == job.offering_id,
                TenantService.job_type_id == job.job_type_id,
                TenantService.is_enabled.is_(True),
                TenantService.deleted_at.is_(None),
            ).limit(1)
        )).scalar_one_or_none()
        warranty_days = max(5, int(tenant_service.warranty_days if tenant_service else 5))
        completed_at = datetime.fromisoformat(job.completion_data["completed_at"])
        job.warranty_days_snapshot = warranty_days
        job.warranty_expires_at = completed_at + timedelta(days=warranty_days)

        job.completion_data = {
            **job.completion_data,
            "provider_charge_basis": float(service_charge_basis),
            "provider_charge_basis_source": (
                "service_invoice.total_amount_excluding_approved_parts"
                if invoice else "collected_amount_fallback"
            ),
            "platform_fee_snapshot": float(platform_fee_snapshot) if platform_fee_snapshot is not None else None,
            "warranty_days": warranty_days,
            "warranty_expires_at": job.warranty_expires_at.isoformat(),
        }

        booking = await db.get(ServiceBooking, job.booking_id)
        from app.engines.final_records.warranty_certificate import issue_warranty_certificate
        await issue_warranty_certificate(db, job, booking)
        offering_type_id = brand_id_for_deduction = None
        if booking:
            draft = await db.get(HomeServiceBookingDraft, booking.draft_id)
            if draft:
                offering_type_id = draft.offering_type_id
                brand_id_for_deduction = draft.brand_id
        chargeable_event = "job_completed"
        if job.job_type_id is not None:
            from app.engines.admin_catalog.models import JobTypeDefinition
            job_type_key = (await db.execute(
                select(JobTypeDefinition.key).where(JobTypeDefinition.id == job.job_type_id)
            )).scalar_one_or_none()
            if job_type_key == "consultation":
                chargeable_event = "consultation_completed"
        try:
            async with db.begin_nested():
                deduction = await deduct_for_completed_job(
                    db, tenant_id=tenant_id, job_id=job.id, booking_id=job.booking_id,
                    master_service_id=job.offering_id, offering_type_id=offering_type_id,
                    brand_id=brand_id_for_deduction, category_id=job.category_id,
                    job_type_id=job.job_type_id,
                    chargeable_event=chargeable_event,
                    job_price=service_charge_basis, request_id=request_id,
                )
        except Exception as exc:
            # A finance-side failure must not roll back genuine completed work.
            # The savepoint keeps this session usable so the independent
            # recovery event below is still attempted and the API exposes the
            # failed status for reconciliation/retry tooling.
            deduction = {
                "deduction_status": "failed",
                "error_type": type(exc).__name__,
                "retry_required": True,
            }
        # The customer pays the provider directly, including any platform
        # fee snapshotted by the published vertical policy. Recover that fee
        # from the provider's usage-credit balance as its own idempotent
        # ledger event; it must never be folded into the provider commission.
        from app.engines.vertical_monetization.customer_charge_recovery import (
            deduct_customer_platform_charge_recovery,
        )
        try:
            async with db.begin_nested():
                platform_charge_recovery = await deduct_customer_platform_charge_recovery(
                    db,
                    tenant_id=tenant_id,
                    job_id=job.id,
                    booking_id=job.booking_id,
                    vertical_key="home_services",
                    chargeable_amount=service_charge_basis,
                    snapshotted_fee_amount=platform_fee_snapshot,
                    policy_reference=f"service_invoice:{invoice.id}" if invoice else None,
                    request_id=request_id,
                )
        except Exception as exc:
            platform_charge_recovery = {
                "recovery_status": "failed",
                "error_type": type(exc).__name__,
                "retry_required": True,
            }
        await db.flush()

        result = job.to_dict()
        result["usage_credit_deduction"] = deduction
        result["customer_platform_charge_recovery"] = platform_charge_recovery
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
