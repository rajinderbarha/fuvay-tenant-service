"""Sprint 21 — Home Service Job Execution Service."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.execution.constants import (
    JOB_TRANSITIONS,
    EV_JOB_ACCEPTED, EV_JOB_REJECTED, EV_JOB_SCHEDULED,
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
    JS_COMPLETED, COMPLETABLE_JOB_STATUSES, PAYMENT_MODE_HOME_SERVICES,
    ERR_WORK_SUMMARY_REQUIRED, ERR_COLLECTED_AMOUNT_REQUIRED,
    ERR_COLLECTED_AMOUNT_INVALID, ERR_PAYMENT_MODE_INVALID,
    ERR_JOB_NOT_COMPLETABLE, ERR_UNRESOLVED_PARTS_REQUESTS,
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
        await self._set_status(db, job, JS_INSPECTION_DONE, EV_INSPECTION_COMPLETED, user_id, "staff", request_id=request_id)
        await db.flush()
        return job.to_dict()

    async def start_service(self, db, job_id, tenant_id, staff_member_id, user_id, request_id=None):
        job = await self._get_job(db, job_id, tenant_id)
        self._assert_staff_owns_job(job, staff_member_id)
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

    async def cancel_job(self, db, job_id, tenant_id, user_id, reason: str, actor_role: str = "provider", request_id=None):
        if not reason or not reason.strip():
            raise ServiceOSException(ERR_REASON_REQUIRED, "Reason is required.", status_code=422)
        job = await self._get_job(db, job_id, tenant_id)
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
            brand_id=brand_id_for_deduction, request_id=request_id,
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
