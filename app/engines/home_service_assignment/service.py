"""Sprint 20 — HomeServiceJobAssignmentService."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, date
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_assignment.constants import (
    ASSIGN_STATUS_ASSIGNED, ASSIGN_STATUS_ACCEPTED, ASSIGN_STATUS_REJECTED,
    ASSIGN_STATUS_CANCELLED, ASSIGN_STATUS_REASSIGNED,
    JOB_ASSIGN_UNASSIGNED, JOB_ASSIGN_ASSIGNED, JOB_ASSIGN_ACCEPTED,
    JOB_ASSIGN_REJECTED, JOB_ASSIGN_CANCELLED,
    JOB_STATUS_PENDING_ASSIGNMENT, JOB_STATUS_ASSIGNED, JOB_STATUS_ACCEPTED,
    JOB_STATUS_SCHEDULED, JOB_STATUS_CANCELLED,
    ASSIGN_TYPE_MANUAL,
    EVENT_ASSIGNMENT_CREATED, EVENT_ASSIGNMENT_REASSIGNED, EVENT_ASSIGNMENT_CANCELLED,
    EVENT_TECHNICIAN_ACCEPTED, EVENT_TECHNICIAN_REJECTED, EVENT_JOB_SCHEDULED,
    EVENT_CUSTOMER_CANCELLED, EVENT_CUSTOMER_RESCHEDULED,
    ELIGIBLE_DESIGNATIONS,
    ERR_JOB_NOT_FOUND, ERR_JOB_CANCELLED, ERR_JOB_COMPLETED,
    ERR_ASSIGNMENT_NOT_FOUND, ERR_ACCESS_DENIED, ERR_INVALID_STATUS,
    ERR_ALREADY_ASSIGNED, ERR_STAFF_NOT_FOUND, ERR_STAFF_NOT_ELIGIBLE,
    ERR_STAFF_WRONG_TENANT, ERR_STAFF_INACTIVE, ERR_ROLE_NOT_ALLOWED,
    ERR_REASON_REQUIRED, ERR_REASSIGN_NOT_ALLOWED, ERR_CANCEL_NOT_ALLOWED,
    ERR_STAFF_JOB_NOT_ASSIGNED, ERR_STAFF_JOB_ALREADY_ACCEPTED,
    ERR_STAFF_JOB_ALREADY_REJECTED,
    ERR_BOOKING_NOT_FOUND, ERR_RESCHEDULE_NOT_ALLOWED,
    CUSTOMER_CANCELLABLE_JOB_STATUSES,
)
from app.engines.home_service_assignment.models import (
    ServiceJobAssignment, ServiceJobAssignmentEvent,
)

_utcnow = lambda: datetime.now(timezone.utc)

# Statuses that block new assignments
_TERMINAL_JOB_STATUSES = {JOB_STATUS_CANCELLED, "failed", "completed"}


class HomeServiceJobAssignmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _load_job(self, job_id: uuid.UUID):
        from app.engines.final_records.models import ServiceJob
        res = await self.db.execute(select(ServiceJob).where(ServiceJob.id == job_id))
        return res.scalars().first()

    async def _load_booking(self, booking_id: uuid.UUID):
        from app.engines.final_records.models import ServiceBooking
        res = await self.db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
        return res.scalars().first()

    async def _load_staff(self, staff_id: uuid.UUID):
        """FINAL-L5-05C fix (L5-05C-001): real service_jobs.assigned_staff_id
        values reference app.engines.auth.models.User (role='technician'/'staff'),
        not ProviderTeamMember — that table is unpopulated in production/demo
        data. Check ProviderTeamMember first (back-compat for any caller that
        still seeds it), then fall back to the real User-backed staff source."""
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        res = await self.db.execute(
            select(ProviderTeamMember).where(ProviderTeamMember.id == staff_id)
        )
        staff = res.scalars().first()
        if staff:
            return staff

        from app.engines.auth.models import User
        res = await self.db.execute(select(User).where(User.id == staff_id))
        return res.scalars().first()

    async def _current_assignment(self, job_id: uuid.UUID) -> ServiceJobAssignment | None:
        res = await self.db.execute(
            select(ServiceJobAssignment).where(
                and_(
                    ServiceJobAssignment.job_id == job_id,
                    ServiceJobAssignment.is_current == True,
                )
            )
        )
        return res.scalars().first()

    async def _emit_event(
        self, job_id: uuid.UUID, booking_id: uuid.UUID, tenant_id: uuid.UUID,
        event_type: str, assignment_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None, actor_role: str | None = None,
        old_value: dict | None = None, new_value: dict | None = None,
        reason: str | None = None, request_id: str | None = None,
    ) -> None:
        ev = ServiceJobAssignmentEvent(
            job_id=job_id, booking_id=booking_id, tenant_id=tenant_id,
            assignment_id=assignment_id, actor_user_id=actor_user_id,
            actor_role=actor_role, event_type=event_type,
            old_value=old_value, new_value=new_value,
            reason=reason, request_id=request_id,
        )
        self.db.add(ev)
        await self.db.flush()

    def _validate_job_assignable(self, job) -> None:
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        if job.status in _TERMINAL_JOB_STATUSES:
            if job.status == JOB_STATUS_CANCELLED:
                raise ValueError(ERR_JOB_CANCELLED)
            raise ValueError(ERR_JOB_COMPLETED)

    async def validate_staff_eligibility(
        self, job, staff_member_id: uuid.UUID
    ) -> tuple[Any, list[str]]:
        """Return (staff, blocked_reasons). blocked_reasons empty = eligible.

        Handles both the legacy ProviderTeamMember shape (status/designation/
        can_receive_assignment) and the real User shape (is_active/role) --
        see _load_staff for why both are supported."""
        staff = await self._load_staff(staff_member_id)
        blocked = []
        if not staff:
            raise ValueError(ERR_STAFF_NOT_FOUND)
        if str(staff.tenant_id) != str(job.tenant_id):
            blocked.append("wrong_tenant")
            return staff, blocked

        is_user = hasattr(staff, "role") and not hasattr(staff, "designation")
        if is_user:
            if not getattr(staff, "is_active", True):
                blocked.append("staff_inactive")
            designation = (staff.role or "").lower()
        else:
            if staff.status != "active":
                blocked.append("staff_inactive")
            if not getattr(staff, "can_receive_assignment", True):
                blocked.append("cannot_receive_assignment")
            designation = (staff.designation or "").lower()

        if designation and designation not in ELIGIBLE_DESIGNATIONS:
            blocked.append("role_not_allowed")
        return staff, blocked

    # ── Phase 4 methods ───────────────────────────────────────────────────────

    async def list_assignable_jobs(
        self, tenant_id: uuid.UUID, assignment_status: str | None = None,
        limit: int = 50, offset: int = 0,
    ) -> list[dict]:
        from app.engines.final_records.models import ServiceJob
        q = select(ServiceJob).where(ServiceJob.tenant_id == tenant_id)
        if assignment_status:
            q = q.where(ServiceJob.assignment_status == assignment_status)
        q = q.order_by(ServiceJob.created_at.desc()).limit(limit).offset(offset)
        res = await self.db.execute(q)
        return [j.to_dict() for j in res.scalars().all()]

    async def get_job_assignment_context(
        self, job_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> dict:
        job = await self._load_job(job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        if str(job.tenant_id) != str(tenant_id):
            raise ValueError(ERR_ACCESS_DENIED)
        assignment = await self._current_assignment(job_id)
        return {
            "job":               job.to_dict(),
            "current_assignment": assignment.to_dict() if assignment else None,
        }

    async def list_eligible_staff_for_job(
        self, job_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> dict:
        # FINAL-L5-05V: this method only ever queried ProviderTeamMember,
        # which has 0 rows in this environment (confirmed live) -- every
        # real technician is a User row (role='technician'/'staff'), per
        # the same L5-05C-001 finding _load_staff/validate_staff_eligibility
        # already handle. Since this method never had the User fallback,
        # the tenant-portal's own job-assignment UI
        # (GET /v1/provider/service-jobs/{job_id}/eligible-staff) has been
        # showing ZERO eligible staff for every job, always, even when real
        # active technicians exist for the tenant -- confirmed live via
        # direct DB query (5 eligible User rows, 0 ProviderTeamMember rows).
        # Mirrors the same dual-shape handling validate_staff_eligibility
        # already uses, rather than duplicating a second staff-listing
        # implementation.
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        from app.engines.auth.models import User
        job = await self._load_job(job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        if str(job.tenant_id) != str(tenant_id):
            raise ValueError(ERR_ACCESS_DENIED)

        res = await self.db.execute(
            select(ProviderTeamMember).where(
                and_(
                    ProviderTeamMember.tenant_id == tenant_id,
                    ProviderTeamMember.deleted_at == None,
                )
            )
        )
        all_staff = list(res.scalars().all())

        if not all_staff:
            res2 = await self.db.execute(
                select(User).where(
                    and_(
                        User.tenant_id == tenant_id,
                        User.role.in_(["technician", "staff"]),
                    )
                )
            )
            all_staff = list(res2.scalars().all())

        eligible, blocked = [], []
        for s in all_staff:
            is_user = hasattr(s, "role") and not hasattr(s, "designation")
            reasons = []
            if is_user:
                if not getattr(s, "is_active", True):
                    reasons.append("staff_inactive")
                designation = (s.role or "").lower()
                status = "active" if getattr(s, "is_active", True) else "inactive"
                name = s.full_name
            else:
                if s.status != "active":
                    reasons.append("staff_inactive")
                if not getattr(s, "can_receive_assignment", True):
                    reasons.append("cannot_receive_assignment")
                designation = (s.designation or "").lower()
                status = s.status
                name = s.full_name
            if designation and designation not in ELIGIBLE_DESIGNATIONS:
                reasons.append("role_not_allowed")

            base = {
                "staff_member_id": str(s.id),
                "name":            name,
                "role":            designation or "unknown",
                "status":          status,
            }
            if not reasons:
                eligible.append({
                    **base,
                    "eligibility_status": "eligible",
                    "match_reasons":      ["same_tenant", "active", designation or "staff"],
                })
            else:
                blocked.append({
                    **base,
                    "eligibility_status": "blocked",
                    "blocked_reasons":    reasons,
                })

        return {"job_id": str(job_id), "eligible_staff": eligible, "blocked_staff": blocked}

    async def assign_job(
        self,
        job_id:          uuid.UUID,
        staff_member_id: uuid.UUID,
        tenant_id:       uuid.UUID,
        actor_user_id:   uuid.UUID | None = None,
        scheduled_date:  date | None      = None,
        scheduled_time_window: str | None = None,
        notes:           str | None       = None,
        request_id:      str | None       = None,
    ) -> dict:
        job = await self._load_job(job_id)
        self._validate_job_assignable(job)
        if str(job.tenant_id) != str(tenant_id):
            raise ValueError(ERR_ACCESS_DENIED)

        # Validate staff eligibility
        staff, blocked = await self.validate_staff_eligibility(job, staff_member_id)
        if "wrong_tenant" in blocked:
            raise ValueError(ERR_STAFF_WRONG_TENANT)
        if "staff_inactive" in blocked:
            raise ValueError(ERR_STAFF_INACTIVE)
        if "role_not_allowed" in blocked:
            raise ValueError(ERR_ROLE_NOT_ALLOWED)
        if blocked:
            raise ValueError(ERR_STAFF_NOT_ELIGIBLE)

        # Retire old current assignment if any
        old_assignment = await self._current_assignment(job_id)
        old_status = None
        if old_assignment:
            if old_assignment.assignment_status == ASSIGN_STATUS_ACCEPTED:
                raise ValueError(ERR_REASSIGN_NOT_ALLOWED)
            old_status = old_assignment.assignment_status
            old_assignment.is_current = False
            old_assignment.assignment_status = ASSIGN_STATUS_REASSIGNED
            await self.db.flush()

        # Create new assignment
        assignment = ServiceJobAssignment(
            job_id=job_id, booking_id=job.booking_id, tenant_id=tenant_id,
            assigned_staff_member_id=staff_member_id,
            assigned_by_user_id=actor_user_id,
            assignment_status=ASSIGN_STATUS_ASSIGNED,
            assignment_type=ASSIGN_TYPE_MANUAL,
            scheduled_date=scheduled_date,
            scheduled_time_window=scheduled_time_window,
            notes=notes,
            is_current=True,
        )
        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)

        # Update job snapshot
        job.assigned_staff_id    = staff_member_id
        job.status               = JOB_STATUS_ASSIGNED
        job.assignment_status    = JOB_ASSIGN_ASSIGNED
        if scheduled_date:
            job.scheduled_date        = scheduled_date
            job.scheduled_time_window = scheduled_time_window
        await self.db.flush()

        # Sync booking
        await self._sync_booking(job.booking_id, JOB_ASSIGN_ASSIGNED, "assigned")

        # Event
        event_type = EVENT_ASSIGNMENT_REASSIGNED if old_status else EVENT_ASSIGNMENT_CREATED
        await self._emit_event(
            job_id=job_id, booking_id=job.booking_id, tenant_id=tenant_id,
            event_type=event_type, assignment_id=assignment.id,
            actor_user_id=actor_user_id, actor_role="provider",
            old_value={"assignment_status": old_status},
            new_value={"assigned_staff_member_id": str(staff_member_id),
                       "assignment_status": ASSIGN_STATUS_ASSIGNED},
            request_id=request_id,
        )

        # MODULE-L5-25: tell the technician they have a new job. assign_job only
        # emitted an internal audit event, so a staff member was given work and
        # never told — the whole point of an assignment is that they act on it.
        # (service_jobs.assigned_staff_id = users.id, so the staff id is the
        # recipient user id directly.)
        await self._notify_staff_assigned(
            job=job, staff_member_id=staff_member_id, tenant_id=tenant_id,
            scheduled_date=scheduled_date, scheduled_time_window=scheduled_time_window,
            reassigned=bool(old_status))

        return {
            "job_id":                  str(job_id),
            "assignment_id":           str(assignment.id),
            "assigned_staff_member_id":str(staff_member_id),
            "status":                  job.status,
            "assignment_status":       job.assignment_status,
            "scheduled_date":          scheduled_date.isoformat() if scheduled_date else None,
            "scheduled_time_window":   scheduled_time_window,
        }

    async def _notify_staff_assigned(
        self, *, job, staff_member_id: uuid.UUID, tenant_id: uuid.UUID,
        scheduled_date: date | None, scheduled_time_window: str | None,
        reassigned: bool,
    ) -> None:
        from app.engines.platform_notifications.models import InAppNotification
        when = ""
        if scheduled_date:
            when = f" for {scheduled_date.isoformat()}"
            if scheduled_time_window:
                when += f" ({scheduled_time_window})"
        verb = "reassigned to you" if reassigned else "assigned to you"
        self.db.add(InAppNotification(
            user_id=staff_member_id,
            tenant_id=tenant_id,
            notification_type="job_assigned",
            title="New job assigned to you" if not reassigned else "A job was reassigned to you",
            body=f"A service job has been {verb}{when}. Tap to view the details and accept it.",
            action_url=f"/staff/jobs/{job.id}",
            action_label="View job",
            source_record_type="service_jobs",
            source_record_id=job.id,
            severity="info",
        ))

    async def reassign_job(
        self,
        job_id:          uuid.UUID,
        staff_member_id: uuid.UUID,
        tenant_id:       uuid.UUID,
        reason:          str,
        actor_user_id:   uuid.UUID | None = None,
        request_id:      str | None       = None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        return await self.assign_job(
            job_id=job_id, staff_member_id=staff_member_id,
            tenant_id=tenant_id, actor_user_id=actor_user_id,
            request_id=request_id,
        )

    async def cancel_assignment(
        self,
        job_id:       uuid.UUID,
        tenant_id:    uuid.UUID,
        reason:       str,
        actor_user_id:uuid.UUID | None = None,
        request_id:   str | None       = None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        job = await self._load_job(job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        if str(job.tenant_id) != str(tenant_id):
            raise ValueError(ERR_ACCESS_DENIED)

        assignment = await self._current_assignment(job_id)
        if not assignment:
            raise ValueError(ERR_ASSIGNMENT_NOT_FOUND)
        if assignment.assignment_status == ASSIGN_STATUS_ACCEPTED:
            raise ValueError(ERR_CANCEL_NOT_ALLOWED)

        old_status = assignment.assignment_status
        assignment.assignment_status = ASSIGN_STATUS_CANCELLED
        assignment.cancelled_at = _utcnow()
        assignment.is_current = False
        await self.db.flush()

        job.assigned_staff_id = None
        job.status            = JOB_STATUS_PENDING_ASSIGNMENT
        job.assignment_status = JOB_ASSIGN_UNASSIGNED
        await self.db.flush()

        await self._sync_booking(job.booking_id, JOB_ASSIGN_UNASSIGNED, JOB_STATUS_PENDING_ASSIGNMENT)

        await self._emit_event(
            job_id=job_id, booking_id=job.booking_id, tenant_id=tenant_id,
            event_type=EVENT_ASSIGNMENT_CANCELLED, assignment_id=assignment.id,
            actor_user_id=actor_user_id, actor_role="provider",
            old_value={"assignment_status": old_status},
            new_value={"assignment_status": ASSIGN_STATUS_CANCELLED},
            reason=reason, request_id=request_id,
        )

        return {"job_id": str(job_id), "assignment_status": JOB_ASSIGN_UNASSIGNED,
                "status": JOB_STATUS_PENDING_ASSIGNMENT}

    # ── Customer self-service cancel/reschedule ──────────────────────────────
    # MODULE-L5-29: previously a customer had no way to cancel or reschedule a
    # CONFIRMED booking at all — cancel_draft only covered pre-confirmation
    # drafts, and BOOKING_STATUS_CANCELLED/JOB_STATUS_CANCELLED existed as
    # constants but nothing in the live app ever wrote them for a real booking.
    # A customer whose plans changed had no path except contacting support to
    # get an admin to force-void the job.

    async def _load_booking_and_job(self, booking_id: uuid.UUID, customer_id: uuid.UUID):
        from app.engines.final_records.models import ServiceBooking, ServiceJob
        booking = (await self.db.execute(
            select(ServiceBooking).where(ServiceBooking.id == booking_id)
        )).scalars().first()
        if not booking:
            raise ValueError(ERR_BOOKING_NOT_FOUND)
        if str(booking.customer_id) != str(customer_id):
            raise ValueError(ERR_ACCESS_DENIED)
        job = (await self.db.execute(
            select(ServiceJob).where(ServiceJob.booking_id == booking_id)
        )).scalars().first()
        return booking, job

    async def customer_cancel_booking(
        self, booking_id: uuid.UUID, customer_id: uuid.UUID,
        reason: str, request_id: str | None = None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        booking, job = await self._load_booking_and_job(booking_id, customer_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        if job.status not in CUSTOMER_CANCELLABLE_JOB_STATUSES:
            # Work has progressed far enough (quote approved / invoiced /
            # completed / already terminal) that a bare cancel is unsafe —
            # the customer must raise a complaint instead so a human resolves
            # any money already owed.
            raise ValueError(ERR_CANCEL_NOT_ALLOWED)

        old_job_status = job.status
        job.status = JOB_STATUS_CANCELLED
        job.updated_at = _utcnow()

        assignment = await self._current_assignment(job.id)
        if assignment and assignment.assignment_status != ASSIGN_STATUS_ACCEPTED:
            assignment.is_current = False
            assignment.assignment_status = ASSIGN_STATUS_CANCELLED
            assignment.cancelled_at = _utcnow()
        await self.db.flush()

        await self._sync_booking(booking.id, JOB_ASSIGN_CANCELLED, JOB_STATUS_CANCELLED)

        await self._emit_event(
            job_id=job.id, booking_id=booking.id, tenant_id=job.tenant_id,
            event_type=EVENT_CUSTOMER_CANCELLED,
            actor_user_id=customer_id, actor_role="customer",
            old_value={"status": old_job_status}, new_value={"status": JOB_STATUS_CANCELLED},
            reason=reason, request_id=request_id,
        )
        await self._notify_booking_change(
            booking=booking, job=job, title="Booking cancelled by customer",
            body=f"The customer cancelled booking {booking.booking_number}. Reason: {reason}",
            notif_type="booking.cancelled")
        await self.db.commit()

        return {"booking_id": str(booking_id), "job_id": str(job.id),
                "status": JOB_STATUS_CANCELLED, "reason": reason}

    async def customer_reschedule_booking(
        self, booking_id: uuid.UUID, customer_id: uuid.UUID,
        scheduled_date: date, scheduled_time_window: str | None,
        reason: str, request_id: str | None = None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        booking, job = await self._load_booking_and_job(booking_id, customer_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        if job.status not in CUSTOMER_CANCELLABLE_JOB_STATUSES:
            raise ValueError(ERR_RESCHEDULE_NOT_ALLOWED)

        old_date = job.scheduled_date.isoformat() if job.scheduled_date else None
        job.scheduled_date = scheduled_date
        job.scheduled_time_window = scheduled_time_window
        job.updated_at = _utcnow()
        booking.preferred_date = scheduled_date
        booking.preferred_time_window = scheduled_time_window
        await self.db.flush()

        await self._emit_event(
            job_id=job.id, booking_id=booking.id, tenant_id=job.tenant_id,
            event_type=EVENT_CUSTOMER_RESCHEDULED,
            actor_user_id=customer_id, actor_role="customer",
            old_value={"scheduled_date": old_date},
            new_value={"scheduled_date": scheduled_date.isoformat(),
                       "scheduled_time_window": scheduled_time_window},
            reason=reason, request_id=request_id,
        )
        await self._notify_booking_change(
            booking=booking, job=job, title="Customer requested a reschedule",
            body=(f"Booking {booking.booking_number} was rescheduled to "
                  f"{scheduled_date.isoformat()}{f' ({scheduled_time_window})' if scheduled_time_window else ''}. "
                  f"Reason: {reason}"),
            notif_type="booking.rescheduled")
        await self.db.commit()

        return {"booking_id": str(booking_id), "job_id": str(job.id),
                "scheduled_date": scheduled_date.isoformat(),
                "scheduled_time_window": scheduled_time_window}

    async def _notify_booking_change(self, *, booking, job, title: str, body: str,
                                     notif_type: str) -> None:
        """Best-effort: tell the provider owner + assigned technician. Never
        blocks the cancel/reschedule itself on a notification failure."""
        try:
            from app.engines.platform_notifications.models import InAppNotification
            recipients: set[str] = set()
            if job.tenant_id:
                from app.engines.tenant_engine.models import Tenant
                tenant = await self.db.get(Tenant, job.tenant_id)
                owner_id = getattr(tenant, "owner_user_id", None) if tenant else None
                if owner_id:
                    recipients.add(str(owner_id))
            if job.assigned_staff_id:
                recipients.add(str(job.assigned_staff_id))
            for rid in recipients:
                self.db.add(InAppNotification(
                    user_id=uuid.UUID(rid), tenant_id=job.tenant_id,
                    notification_type=notif_type, title=title, body=body,
                    action_url="/service-jobs", action_label="View jobs",
                    source_record_type="service_bookings", source_record_id=booking.id,
                    severity="warning",
                ))
        except Exception:
            pass

    async def technician_accept_job(
        self,
        job_id:       uuid.UUID,
        staff_id:     uuid.UUID,
        request_id:   str | None = None,
    ) -> dict:
        job = await self._load_job(job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)

        assignment = await self._current_assignment(job_id)
        if not assignment or str(assignment.assigned_staff_member_id) != str(staff_id):
            raise ValueError(ERR_STAFF_JOB_NOT_ASSIGNED)
        if assignment.assignment_status == ASSIGN_STATUS_ACCEPTED:
            raise ValueError(ERR_STAFF_JOB_ALREADY_ACCEPTED)
        if assignment.assignment_status == ASSIGN_STATUS_REJECTED:
            raise ValueError(ERR_STAFF_JOB_ALREADY_REJECTED)

        accepted_at = _utcnow()
        assignment.assignment_status = ASSIGN_STATUS_ACCEPTED
        assignment.accepted_at = accepted_at
        await self.db.flush()

        job.status            = JOB_STATUS_ACCEPTED
        job.assignment_status = JOB_ASSIGN_ACCEPTED
        await self.db.flush()

        await self._sync_booking(job.booking_id, JOB_ASSIGN_ACCEPTED, JOB_STATUS_ACCEPTED)

        await self._emit_event(
            job_id=job_id, booking_id=job.booking_id, tenant_id=job.tenant_id,
            event_type=EVENT_TECHNICIAN_ACCEPTED, assignment_id=assignment.id,
            actor_user_id=staff_id, actor_role="staff",
            new_value={"assignment_status": ASSIGN_STATUS_ACCEPTED,
                       "accepted_at": accepted_at.isoformat()},
            request_id=request_id,
        )

        return {
            "job_id":            str(job_id),
            "status":            JOB_STATUS_ACCEPTED,
            "assignment_status": JOB_ASSIGN_ACCEPTED,
            "accepted_at":       accepted_at.isoformat(),
        }

    async def technician_reject_job(
        self,
        job_id:     uuid.UUID,
        staff_id:   uuid.UUID,
        reason:     str,
        request_id: str | None = None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)

        job = await self._load_job(job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)

        assignment = await self._current_assignment(job_id)
        if not assignment or str(assignment.assigned_staff_member_id) != str(staff_id):
            raise ValueError(ERR_STAFF_JOB_NOT_ASSIGNED)
        if assignment.assignment_status == ASSIGN_STATUS_ACCEPTED:
            raise ValueError(ERR_STAFF_JOB_ALREADY_ACCEPTED)
        if assignment.assignment_status == ASSIGN_STATUS_REJECTED:
            raise ValueError(ERR_STAFF_JOB_ALREADY_REJECTED)

        rejected_at = _utcnow()
        assignment.assignment_status = ASSIGN_STATUS_REJECTED
        assignment.rejection_reason  = reason
        assignment.rejected_at       = rejected_at
        assignment.is_current        = False
        await self.db.flush()

        job.assigned_staff_id = None
        job.status            = JOB_STATUS_PENDING_ASSIGNMENT
        job.assignment_status = JOB_ASSIGN_REJECTED
        await self.db.flush()

        await self._sync_booking(job.booking_id, JOB_ASSIGN_REJECTED, JOB_STATUS_PENDING_ASSIGNMENT)

        await self._emit_event(
            job_id=job_id, booking_id=job.booking_id, tenant_id=job.tenant_id,
            event_type=EVENT_TECHNICIAN_REJECTED, assignment_id=assignment.id,
            actor_user_id=staff_id, actor_role="staff",
            new_value={"assignment_status": ASSIGN_STATUS_REJECTED,
                       "rejected_at": rejected_at.isoformat()},
            reason=reason, request_id=request_id,
        )

        return {
            "job_id":            str(job_id),
            "status":            JOB_STATUS_PENDING_ASSIGNMENT,
            "assignment_status": JOB_ASSIGN_REJECTED,
            "rejected_at":       rejected_at.isoformat(),
        }

    async def schedule_job(
        self,
        job_id:              uuid.UUID,
        tenant_id:           uuid.UUID,
        scheduled_date:      date,
        scheduled_time_window: str,
        actor_user_id:       uuid.UUID | None = None,
        request_id:          str | None       = None,
    ) -> dict:
        job = await self._load_job(job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        if str(job.tenant_id) != str(tenant_id):
            raise ValueError(ERR_ACCESS_DENIED)
        if job.status not in {JOB_STATUS_ASSIGNED, JOB_STATUS_ACCEPTED}:
            raise ValueError(ERR_INVALID_STATUS)

        assignment = await self._current_assignment(job_id)

        job.scheduled_date        = scheduled_date
        job.scheduled_time_window = scheduled_time_window
        job.status                = JOB_STATUS_SCHEDULED
        await self.db.flush()

        if assignment:
            assignment.scheduled_date        = scheduled_date
            assignment.scheduled_time_window = scheduled_time_window
            await self.db.flush()

        await self._sync_booking(job.booking_id, job.assignment_status, JOB_STATUS_SCHEDULED)

        await self._emit_event(
            job_id=job_id, booking_id=job.booking_id, tenant_id=tenant_id,
            event_type=EVENT_JOB_SCHEDULED,
            assignment_id=assignment.id if assignment else None,
            actor_user_id=actor_user_id, actor_role="provider",
            new_value={"scheduled_date": scheduled_date.isoformat(),
                       "scheduled_time_window": scheduled_time_window,
                       "status": JOB_STATUS_SCHEDULED},
            request_id=request_id,
        )

        return {
            "job_id":                str(job_id),
            "status":                JOB_STATUS_SCHEDULED,
            "scheduled_date":        scheduled_date.isoformat(),
            "scheduled_time_window": scheduled_time_window,
        }

    async def get_assignment_timeline(
        self, job_id: uuid.UUID, tenant_id: uuid.UUID | None = None,
    ) -> list[dict]:
        q = select(ServiceJobAssignmentEvent).where(
            ServiceJobAssignmentEvent.job_id == job_id
        )
        if tenant_id:
            q = q.where(ServiceJobAssignmentEvent.tenant_id == tenant_id)
        q = q.order_by(ServiceJobAssignmentEvent.created_at)
        res = await self.db.execute(q)
        return [e.to_dict() for e in res.scalars().all()]

    async def get_staff_assigned_jobs(
        self, staff_id: uuid.UUID, tenant_id: uuid.UUID | None = None,
    ) -> list[dict]:
        from app.engines.final_records.models import ServiceJob
        q = select(ServiceJob).where(
            ServiceJob.assigned_staff_id == staff_id
        )
        if tenant_id:
            q = q.where(ServiceJob.tenant_id == tenant_id)
        q = q.order_by(ServiceJob.created_at.desc())
        res = await self.db.execute(q)
        return [j.to_dict() for j in res.scalars().all()]

    async def get_staff_job_detail(
        self, job_id: uuid.UUID, staff_id: uuid.UUID,
    ) -> dict:
        job = await self._load_job(job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        if str(job.assigned_staff_id) != str(staff_id):
            raise ValueError(ERR_STAFF_JOB_NOT_ASSIGNED)
        assignment = await self._current_assignment(job_id)
        booking = await self._load_booking(job.booking_id)
        return {
            "job":        job.to_dict(),
            "assignment": assignment.to_dict() if assignment else None,
            "booking":    _safe_booking_view(booking) if booking else None,
        }

    async def _sync_booking(
        self, booking_id: uuid.UUID, assignment_status: str, status: str
    ) -> None:
        from app.engines.final_records.models import ServiceBooking
        res = await self.db.execute(
            select(ServiceBooking).where(ServiceBooking.id == booking_id)
        )
        booking = res.scalars().first()
        if booking:
            booking.assignment_status = assignment_status
            booking.status            = status
            await self.db.flush()


def _safe_booking_view(booking) -> dict:
    """Return customer-safe booking fields — no internal notes or pricing details."""
    return {
        "id":                    str(booking.id),
        "booking_number":        booking.booking_number,
        "customer_name":         booking.customer_name,
        "city":                  booking.city,
        "zipcode":               booking.zipcode,
        "preferred_date":        booking.preferred_date.isoformat() if booking.preferred_date else None,
        "preferred_time_window": booking.preferred_time_window,
        "issue_summary":         booking.issue_summary,
        "status":                booking.status,
        "assignment_status":     booking.assignment_status,
        "address_snapshot":      booking.address_snapshot,
    }
