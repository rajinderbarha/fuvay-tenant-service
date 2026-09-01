"""Sprint 20 — HomeServiceJobAssignmentService."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Any

from sqlalchemy import select, and_, text
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
    ERR_RESCHEDULE_LIMIT_REACHED, ERR_STALE_VERSION, ERR_SLOT_UNAVAILABLE,
    ERR_INVALID_REASON, ERR_PAST_DATE,
    CUSTOMER_CANCELLABLE_JOB_STATUSES, MAX_RESCHEDULE_COUNT,
    CUSTOMER_CANCELLATION_REASONS, CANCELLATION_REASON_REQUIRES_DETAIL,
    TRACKING_ACTIVE_JOB_STATUSES, LOCATION_STALE_SECONDS,
    ERR_LOCATION_NOT_TRACKABLE, ERR_LOCATION_INVALID_COORDS,
)
from app.engines.home_service_assignment.models import (
    ServiceJobAssignment, ServiceJobAssignmentEvent, TechnicianLiveLocation,
)
from app.engines.home_service_assignment.eligibility import (
    is_technician_role,
    normalise_designation,
)

_utcnow = lambda: datetime.now(timezone.utc)

# Statuses that block new assignments
_TERMINAL_JOB_STATUSES = {JOB_STATUS_CANCELLED, "failed", "completed"}


def _normalise_designation(value: str | None) -> str:
    """Back-compat alias for the shared normaliser.

    The implementation moved to `home_service_assignment.eligibility` so
    billing, slot capacity and assignment all fold designations identically.
    """
    return normalise_designation(value)


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

    async def _job_requires_technician(self, job) -> bool:
        """Resolve the technician gate from the job's snapshotted workflow.

        Jobs created before workflow snapshots are resolved through the
        offering's master service and job type. If neither can be resolved,
        fail closed so an unconfigured person is never assigned field work.
        """
        from app.engines.admin_catalog.models import ServiceJobWorkflow

        if getattr(job, "service_job_workflow_id", None):
            result = await self.db.execute(select(ServiceJobWorkflow.technician_required).where(
                ServiceJobWorkflow.id == job.service_job_workflow_id
            ))
            value = result.scalar_one_or_none()
            if value is not None:
                return bool(value)

        if getattr(job, "offering_id", None) and getattr(job, "job_type_id", None):
            result = await self.db.execute(select(ServiceJobWorkflow.technician_required).where(
                # ServiceJob.offering_id is the canonical MasterService id.
                # TenantService ids are tenant/job-type scoped and are only
                # used for provider skill assignments (resolved separately).
                ServiceJobWorkflow.master_service_id == job.offering_id,
                ServiceJobWorkflow.job_type_id == job.job_type_id,
                ServiceJobWorkflow.is_current == True,
            ))
            value = result.scalar_one_or_none()
            if value is not None:
                return bool(value)
        return True

    async def _tenant_service_id_for_job(self, job) -> uuid.UUID | None:
        """Resolve a job's master-service identity to its tenant offering.

        ProviderTeamMember.supported_offering_ids stores TenantService ids,
        while ServiceJob.offering_id stores a MasterService id.  Keeping this
        translation in one place prevents dispatch and assignment from
        comparing identifiers from different namespaces.
        """
        from app.engines.admin_catalog.models import TenantService

        if not getattr(job, "offering_id", None) or not getattr(job, "job_type_id", None):
            return None
        result = await self.db.execute(
            select(TenantService.id).where(
                TenantService.tenant_id == job.tenant_id,
                TenantService.master_service_id == job.offering_id,
                TenantService.job_type_id == job.job_type_id,
                TenantService.is_active == True,
                TenantService.deleted_at == None,
            )
        )
        return result.scalar_one_or_none()

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

    async def _availability_block_reasons(self, job, staff_member_id: uuid.UUID) -> list[str]:
        """Why the availability resolver says this technician cannot work this job's date.

        Dispatch did not ask this question at all. Eligibility was tenant + active +
        designation, none of which involve a date, so booking a technician off on the
        availability board changed the board and changed nothing else: the same
        technician stayed in the eligible list and could still be assigned the day they
        were on leave. The board was writing rows nobody read.

        Deliberately narrow about when it applies:

        * No `scheduled_date` on the job means there is no date to be unavailable ON.
          Blocking would refuse assignment for unscheduled work, which is the normal way
          jobs are triaged here.
        * The resolver reads `provider_team_members`. Some tenants' technicians are User
          rows instead (see `_load_staff`), and for those the resolver has nothing to look
          up and would report STAFF_INACTIVE for everyone. So this runs only when the id
          is a real team-member row, and otherwise returns nothing rather than blocking
          the whole roster on a lookup that was never going to succeed.
        * Capacity reasons do NOT block. Being full is a judgement the dispatcher is
          allowed to override -- they can see the count and decide. Being on leave or
          outside working hours is not a judgement call, it is a fact about the day.
        """
        scheduled = getattr(job, "scheduled_date", None)
        if not scheduled:
            return []

        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        row = (await self.db.execute(
            select(ProviderTeamMember.id).where(ProviderTeamMember.id == staff_member_id)
        )).first()
        if not row:
            return []

        from app.engines.home_service_assignment.availability_resolver import (
            resolve_staff_day, R_DAILY_CAPACITY_EXCEEDED, R_CONCURRENT_CAPACITY_EXCEEDED,
            R_SCHEDULE_CONFLICT,
        )
        day = await resolve_staff_day(self.db, job.tenant_id, staff_member_id, scheduled)
        advisory = {R_DAILY_CAPACITY_EXCEEDED, R_CONCURRENT_CAPACITY_EXCEEDED, R_SCHEDULE_CONFLICT}
        return [r.lower() for r in day.get("reasons", []) if r not in advisory]

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
            designation = _normalise_designation(staff.role)
        else:
            if staff.status != "active":
                blocked.append("staff_inactive")
            # The team-member row and the LOGIN are two different records, and
            # only the login decides whether this person can actually open the
            # app. Checking `ptm.status` alone let a job be assigned to someone
            # whose user account had been deactivated — confirmed live: a member
            # with status='active' and users.is_active=false accepted an
            # assignment and could never have worked it. Deactivating a
            # technician must stop new work reaching them.
            elif getattr(staff, "user_id", None):
                from app.engines.auth.models import User
                user_active = (await self.db.execute(
                    select(User.is_active).where(User.id == staff.user_id)
                )).scalar()
                if user_active is False:
                    blocked.append("staff_inactive")
            if not getattr(staff, "can_receive_assignment", True):
                blocked.append("cannot_receive_assignment")
            designation = _normalise_designation(staff.designation)

        # `member_type` counts alongside the typed designation, so an
        # owner_technician is not refused for having written something else in
        # the free-text field. Mirrors list_eligible_staff_for_job exactly --
        # a person shown as eligible must not then be refused on assign.
        if is_user:
            # The User-backed staff source is already restricted to field
            # roles, and "staff" is not a designation key, so gating on the
            # set here only produced false refusals.
            role_ok = designation in ELIGIBLE_DESIGNATIONS or designation == "staff"
        else:
            role_ok = is_technician_role(staff.designation, staff.member_type)
        if designation and not role_ok:
            blocked.append("role_not_allowed")

        # Basic account/role failures are definitive. Avoid workflow, skill,
        # and availability lookups for a person who cannot be assigned under
        # any circumstance, and preserve the precise rejection reason.
        if blocked:
            return staff, blocked

        if await self._job_requires_technician(job) and not is_user:
            tenant_service_id = await self._tenant_service_id_for_job(job)
            supported = {str(value) for value in (getattr(staff, "supported_offering_ids", None) or [])}
            if tenant_service_id is None:
                blocked.append("service_not_configured")
            elif str(tenant_service_id) not in supported:
                blocked.append("no_matching_service_skill")

            has_availability = (await self.db.execute(text(
                "SELECT 1 FROM provider_availability_rules "
                "WHERE tenant_id=:tid AND scope_type='staff_member' "
                "AND scope_id=:sid AND is_active=true LIMIT 1"
            ), {"tid": str(job.tenant_id), "sid": str(staff_member_id)})).first()
            if not has_availability:
                blocked.append("no_availability_configured")

        blocked.extend(await self._availability_block_reasons(job, staff_member_id))
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
        jobs = res.scalars().all()

        # The provider is committed to a SLOT the customer was shown and
        # accepted before confirming, so the queue must be orderable by when
        # each job is actually DUE -- not just when it was created. Derived
        # from the slot already stored on the job (no extra column, no
        # second source of truth to drift). `service_due_at` is null for a
        # legacy job that never carried a slot; callers must treat that as
        # "no commitment recorded", never as "due now".
        import datetime as _dt
        now = _dt.datetime.now()
        out = []
        for j in jobs:
            d = j.to_dict()
            due_at = None
            if j.scheduled_date and j.scheduled_time_window:
                try:
                    end_str = str(j.scheduled_time_window).split("-")[-1].strip()
                    end_t = _dt.datetime.strptime(end_str, "%H:%M").time()
                    due_at = _dt.datetime.combine(j.scheduled_date, end_t)
                except (ValueError, IndexError):
                    due_at = None
            d["service_due_at"] = due_at.isoformat() if due_at else None
            d["minutes_until_due"] = (
                int((due_at - now).total_seconds() // 60) if due_at else None
            )
            d["is_overdue"] = bool(
                due_at and due_at < now and j.status not in ("completed", "cancelled", "failed")
            )
            out.append(d)
        return out

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

        provider_staff_ids = [s.id for s in all_staff if hasattr(s, "designation")]
        # The roster row and the LOGIN are different records. A member can sit
        # at status='active' while their user account is deactivated -- the
        # assign path already refuses those, so listing them as eligible only
        # sent the dispatcher to a dead end. Resolved in ONE query rather than
        # per member.
        deactivated_login_ids: set[str] = set()
        _login_ids = [
            getattr(s, "user_id", None) for s in all_staff if getattr(s, "user_id", None)
        ]
        if _login_ids:
            from app.engines.auth.models import User
            rows = (await self.db.execute(
                select(User.id).where(and_(User.id.in_(_login_ids), User.is_active == False))
            )).all()
            deactivated_login_ids = {str(r[0]) for r in rows}
        technician_required = bool(provider_staff_ids) and await self._job_requires_technician(job)
        tenant_service_id = (
            await self._tenant_service_id_for_job(job)
            if technician_required else None
        )
        # Skills are ADVISORY. A technician without the service in
        # `supported_offering_ids` is still offered, carrying a warning the
        # dispatcher can override. Blocking here would let the slot search
        # sell capacity (which is pure headcount) that assignment then
        # refuses, stranding a booking the customer already holds.
        eligible, blocked = [], []
        for s in all_staff:
            is_user = hasattr(s, "role") and not hasattr(s, "designation")
            reasons: list[str] = []
            warnings: list[str] = []
            if is_user:
                if not getattr(s, "is_active", True):
                    reasons.append("staff_inactive")
                # The User fallback query already restricts to field roles
                # (technician/staff), so re-checking the role here only
                # produced false blocks -- "staff" is not a designation key.
                designation = normalise_designation(getattr(s, "role", None))
                status = "active" if getattr(s, "is_active", True) else "inactive"
                name = s.full_name
                profile_photo_url = getattr(s, "avatar_url", None)
            else:
                if s.status != "active":
                    reasons.append("staff_inactive")
                elif str(getattr(s, "user_id", "") or "") in deactivated_login_ids:
                    reasons.append("staff_inactive")
                if not getattr(s, "can_receive_assignment", True):
                    reasons.append("cannot_receive_assignment")
                designation = normalise_designation(getattr(s, "designation", None))
                status = s.status
                name = s.full_name
                profile_photo_url = getattr(s, "profile_photo_url", None)
                # Raw-lowercasing left every MULTI-WORD designation unmatched,
                # so a real "Senior Technician" was refused with
                # role_not_allowed while a plain "Technician" passed.
                if designation and not is_technician_role(s.designation, s.member_type):
                    reasons.append("role_not_allowed")

                if technician_required:
                    supported = {
                        str(value)
                        for value in (getattr(s, "supported_offering_ids", None) or [])
                    }
                    if tenant_service_id is None:
                        warnings.append("service_not_configured")
                    elif str(tenant_service_id) not in supported:
                        warnings.append("no_matching_service_skill")

            # Same availability question the assign path asks, asked here too so the
            # dispatcher sees a technician on leave as blocked in the list instead of
            # picking them and being refused at the point of assignment.
            reasons.extend(await self._availability_block_reasons(job, s.id))

            base = {
                "staff_member_id": str(s.id),
                "name":            name,
                "role":            designation or "unknown",
                "status":          status,
                "profile_photo_url": profile_photo_url,
            }
            if not reasons:
                eligible.append({
                    **base,
                    "eligibility_status": "eligible",
                    "warnings":           warnings,
                    "match_reasons":      ["same_tenant", "active", designation or "staff"],
                })
            else:
                blocked.append({
                    **base,
                    "eligibility_status": "blocked",
                    "warnings":           warnings,
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

        # Work-in-progress gate: a tenant may hold at most one open job per
        # technician. Blocking ASSIGNMENT rather than booking means the request
        # waits in `pending_assignment` instead of being refused -- the
        # customer never loses their slot, the provider just cannot hoard work
        # its team cannot start.
        from app.engines.vertical_catalog.seat_enforcement import assert_wip_capacity
        await assert_wip_capacity(self.db, tenant_id)

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
        # The notifier resolves the roster record to its authenticated user.
        await self._notify_staff_assigned(
            job=job, staff_member_id=staff_member_id, tenant_id=tenant_id,
            scheduled_date=scheduled_date, scheduled_time_window=scheduled_time_window,
            reassigned=bool(old_status))

        # Assignment is the first point a job has a date to be judged against.
        from app.engines.execution.sla_breach_service import stamp_due_at
        await stamp_due_at(self.db, job.id)

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
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        from app.engines.auth.models import User

        # Assignments store the provider-team-member id, while notifications
        # belong to an authenticated User. These ids are intentionally not the
        # same. Resolve the login identity and allow non-login roster members
        # to be assigned without creating an invalid notification row.
        recipient_user_id = (await self.db.execute(
            select(ProviderTeamMember.user_id).where(
                ProviderTeamMember.id == staff_member_id,
                ProviderTeamMember.tenant_id == tenant_id,
                ProviderTeamMember.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if recipient_user_id is None:
            recipient_user_id = (await self.db.execute(
                select(User.id).where(User.id == staff_member_id)
            )).scalar_one_or_none()
        if recipient_user_id is None:
            return

        when = ""
        if scheduled_date:
            when = f" for {scheduled_date.isoformat()}"
            if scheduled_time_window:
                when += f" ({scheduled_time_window})"
        verb = "reassigned to you" if reassigned else "assigned to you"
        self.db.add(InAppNotification(
            user_id=recipient_user_id,
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

    @staticmethod
    def _version_of(job) -> str:
        """Optimistic-concurrency token. Reuses the row's own updated_at
        instead of adding a dedicated version column — ServiceJob has no
        version int, and updated_at is already bumped on every mutation
        this service performs, so it's an equally valid compare-and-swap key."""
        return job.updated_at.isoformat() if job.updated_at else ""

    def _check_version(self, job, expected_version: str | None) -> None:
        if expected_version and expected_version != self._version_of(job):
            raise ValueError(ERR_STALE_VERSION)

    async def get_customer_eligibility(
        self, booking_id: uuid.UUID, customer_id: uuid.UUID,
    ) -> dict:
        """Server-authoritative eligibility read — the mobile app must not
        reproduce CUSTOMER_CANCELLABLE_JOB_STATUSES/MAX_RESCHEDULE_COUNT
        client-side; it only renders what this returns."""
        booking, job = await self._load_booking_and_job(booking_id, customer_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)

        # The published job-type blueprint is the authority exposed to the
        # customer UI. Return disabled actions instead of throwing from this
        # read endpoint so the app can explain why an action is unavailable.
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        workflow = await HomeServiceJobExecutionService()._resolve_job_type_workflow(self.db, job)
        workflow_allows_cancel = workflow is None or workflow.allows_cancellation
        workflow_allows_reschedule = workflow is None or workflow.allows_reschedule

        state_eligible = job.status in CUSTOMER_CANCELLABLE_JOB_STATUSES
        eligible = state_eligible and workflow_allows_cancel
        if not workflow_allows_cancel:
            cancel_block_reason = "service_policy_disallows_cancellation"
        else:
            cancel_block_reason = None if state_eligible else "booking_not_in_cancellable_state"

        remaining_reschedules = max(0, MAX_RESCHEDULE_COUNT - (job.reschedule_count or 0))
        can_reschedule = state_eligible and workflow_allows_reschedule and remaining_reschedules > 0
        if not workflow_allows_reschedule:
            reschedule_block_reason = "service_policy_disallows_reschedule"
        elif not state_eligible:
            reschedule_block_reason = "booking_not_in_reschedulable_state"
        elif remaining_reschedules <= 0:
            reschedule_block_reason = "reschedule_limit_reached"
        else:
            reschedule_block_reason = None

        return {
            "booking_id": str(booking_id), "job_id": str(job.id),
            "status": job.status,
            "version": self._version_of(job),
            "can_cancel": eligible,
            "cancel_block_reason": cancel_block_reason,
            "allowed_cancellation_reasons": sorted(CUSTOMER_CANCELLATION_REASONS),
            "cancellation_reasons_requiring_detail": sorted(CANCELLATION_REASON_REQUIRES_DETAIL),
            "can_reschedule": can_reschedule,
            "reschedule_block_reason": reschedule_block_reason,
            "remaining_reschedule_allowance": remaining_reschedules,
            "max_reschedule_allowance": MAX_RESCHEDULE_COUNT,
            "requires_provider_approval": False,
            "cancellation_fee": None,
            "cancellation_cutoff": None,
        }

    async def get_reschedule_available_dates(
        self, booking_id: uuid.UUID, customer_id: uuid.UUID, horizon_days: int = 14,
    ) -> dict:
        """Real day-level availability for the reschedule date picker — reuses
        the exact aggregate_slot_available() check the mutation itself
        enforces, so the UI never shows a date the backend would then reject.
        No canonical time-of-day slot catalog exists anywhere in this repo
        (booking creation itself only ever took a free-text time window), so
        this intentionally returns dates only, not hour-level slots — those
        stay a free-text field, not an invented fixed list."""
        booking, job = await self._load_booking_and_job(booking_id, customer_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)


        # Rescheduling follows the same published blueprint as every other
        # job action; the UI must never offer a date change the workflow
        # explicitly forbids.
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        workflow = await HomeServiceJobExecutionService()._resolve_job_type_workflow(self.db, job)
        if workflow is not None and not workflow.allows_reschedule:
            raise ValueError(ERR_RESCHEDULE_NOT_ALLOWED)
        horizon_days = max(1, min(horizon_days, 30))

        from app.engines.home_service_assignment.availability_resolver import aggregate_slot_available
        today = _utcnow().date()
        dates: list[dict] = []
        if job.tenant_id:
            for i in range(1, horizon_days + 1):
                d = today + timedelta(days=i)
                slot = await aggregate_slot_available(self.db, job.tenant_id, d)
                dates.append({"date": d.isoformat(), "available": bool(slot.get("available"))})

        return {"booking_id": str(booking_id), "job_id": str(job.id), "dates": dates}

    async def customer_cancel_booking(
        self, booking_id: uuid.UUID, customer_id: uuid.UUID,
        reason: str, detail: str | None = None,
        expected_version: str | None = None, request_id: str | None = None,
    ) -> dict:
        # `reason` stays free text for backward compatibility with the
        # existing live contract (tests/test_module_l5_29_*.py already POST
        # arbitrary strings like "changed my mind"). CUSTOMER_CANCELLATION_REASONS
        # is exposed via get_customer_eligibility() as a suggested allow-list
        # for the mobile app's UI, not enforced server-side — no policy
        # decision was made to reject free-text reasons outright, and
        # breaking the live contract without that decision would be a
        # regression, not a fix. If a canonical code is recognized and it
        # requires detail (e.g. "other"), detail must be non-empty.
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        if reason in CANCELLATION_REASON_REQUIRES_DETAIL and not (detail or "").strip():
            raise ValueError(ERR_REASON_REQUIRED)
        booking, job = await self._load_booking_and_job(booking_id, customer_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)

        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        workflow = await HomeServiceJobExecutionService()._resolve_job_type_workflow(self.db, job)
        if workflow is not None and not workflow.allows_cancellation:
            raise ValueError(ERR_CANCEL_NOT_ALLOWED)

        # Idempotent retry: ONLY a replay of the same request (matched by
        # request_id against the event that performed the original cancel)
        # is a no-op success. A different/new cancel attempt against an
        # already-cancelled booking is still a hard conflict — preserves the
        # existing live contract (a second, distinct cancel call must 409).
        if job.status == JOB_STATUS_CANCELLED:
            if request_id:
                replay = (await self.db.execute(
                    select(ServiceJobAssignmentEvent).where(
                        ServiceJobAssignmentEvent.booking_id == booking.id,
                        ServiceJobAssignmentEvent.event_type == EVENT_CUSTOMER_CANCELLED,
                        ServiceJobAssignmentEvent.request_id == request_id,
                    )
                )).scalars().first()
                if replay:
                    return {"booking_id": str(booking_id), "job_id": str(job.id),
                            "status": JOB_STATUS_CANCELLED, "reason": reason,
                            "version": self._version_of(job)}
            raise ValueError(ERR_CANCEL_NOT_ALLOWED)

        if job.status not in CUSTOMER_CANCELLABLE_JOB_STATUSES:
            # Work has progressed far enough (quote approved / invoiced /
            # completed / already terminal) that a bare cancel is unsafe —
            # the customer must raise a complaint instead so a human resolves
            # any money already owed.
            raise ValueError(ERR_CANCEL_NOT_ALLOWED)
        self._check_version(job, expected_version)

        old_job_status = job.status
        job.status = JOB_STATUS_CANCELLED
        job.updated_at = _utcnow()

        # Release the assignment regardless of its status — a job that is
        # cancelled must never leave a stale "accepted"/"assigned" row
        # behind implying a technician is still on the hook for it.
        assignment = await self._current_assignment(job.id)
        if assignment:
            assignment.is_current = False
            assignment.assignment_status = ASSIGN_STATUS_CANCELLED
            assignment.cancelled_at = _utcnow()
        job.assigned_staff_id = None
        job.assignment_status = JOB_ASSIGN_CANCELLED
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
        await self._notify_customer(
            booking=booking, customer_id=customer_id,
            title="Your booking was cancelled",
            body=f"Booking {booking.booking_number} has been cancelled as requested.",
            notif_type="booking.cancelled")
        await self.db.commit()

        return {"booking_id": str(booking_id), "job_id": str(job.id),
                "status": JOB_STATUS_CANCELLED, "reason": reason,
                "version": self._version_of(job)}

    async def customer_reschedule_booking(
        self, booking_id: uuid.UUID, customer_id: uuid.UUID,
        scheduled_date: date, scheduled_time_window: str | None,
        reason: str, expected_version: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)
        if scheduled_date < _utcnow().date():
            raise ValueError(ERR_PAST_DATE)
        booking, job = await self._load_booking_and_job(booking_id, customer_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)

        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        workflow = await HomeServiceJobExecutionService()._resolve_job_type_workflow(self.db, job)
        if workflow is not None and not workflow.allows_reschedule:
            raise ValueError(ERR_RESCHEDULE_NOT_ALLOWED)

        # Idempotent retry: the same request_id replaying the exact same
        # already-applied reschedule returns the current state instead of
        # incrementing reschedule_count / re-emitting events a second time.
        if request_id:
            replay = (await self.db.execute(
                select(ServiceJobAssignmentEvent).where(
                    ServiceJobAssignmentEvent.booking_id == booking.id,
                    ServiceJobAssignmentEvent.event_type == EVENT_CUSTOMER_RESCHEDULED,
                    ServiceJobAssignmentEvent.request_id == request_id,
                )
            )).scalars().first()
            if replay and job.scheduled_date == scheduled_date \
                    and job.scheduled_time_window == scheduled_time_window:
                return {"booking_id": str(booking_id), "job_id": str(job.id),
                        "scheduled_date": scheduled_date.isoformat(),
                        "scheduled_time_window": scheduled_time_window,
                        "version": self._version_of(job)}

        if job.status not in CUSTOMER_CANCELLABLE_JOB_STATUSES:
            raise ValueError(ERR_RESCHEDULE_NOT_ALLOWED)
        if (job.reschedule_count or 0) >= MAX_RESCHEDULE_COUNT:
            raise ValueError(ERR_RESCHEDULE_LIMIT_REACHED)
        self._check_version(job, expected_version)

        # Re-validate the new date actually has capacity — the previous
        # implementation wrote the new date/window blind, with no check that
        # any technician (let alone the assigned one) could serve it.
        if job.tenant_id:
            from app.engines.home_service_assignment.availability_resolver import aggregate_slot_available
            slot = await aggregate_slot_available(self.db, job.tenant_id, scheduled_date)
            if not slot.get("available"):
                raise ValueError(ERR_SLOT_UNAVAILABLE)

        old_date = job.scheduled_date.isoformat() if job.scheduled_date else None
        job.scheduled_date = scheduled_date
        job.scheduled_time_window = scheduled_time_window
        job.reschedule_count = (job.reschedule_count or 0) + 1
        job.updated_at = _utcnow()
        booking.preferred_date = scheduled_date
        booking.preferred_time_window = scheduled_time_window
        await self.db.flush()

        # The SLA clock runs from the SCHEDULED SLOT, so rescheduling moves the
        # deadline with it -- a customer who agreed a later date has not been
        # kept waiting, and the provider should not be penalised as if they had.
        from app.engines.execution.sla_breach_service import stamp_due_at
        await stamp_due_at(self.db, job.id)

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
        await self._notify_customer(
            booking=booking, customer_id=customer_id,
            title="Your booking was rescheduled",
            body=(f"Booking {booking.booking_number} is now scheduled for "
                  f"{scheduled_date.isoformat()}{f' ({scheduled_time_window})' if scheduled_time_window else ''}."),
            notif_type="booking.rescheduled")
        await self.db.commit()

        return {"booking_id": str(booking_id), "job_id": str(job.id),
                "scheduled_date": scheduled_date.isoformat(),
                "scheduled_time_window": scheduled_time_window,
                "version": self._version_of(job)}

    async def _notify_customer(self, *, booking, customer_id: uuid.UUID,
                               title: str, body: str, notif_type: str) -> None:
        """Best-effort confirmation to the customer who performed the
        action — mirrors _notify_booking_change's swallow-on-failure
        contract so a notification outage never blocks the mutation."""
        try:
            from app.engines.platform_notifications.models import InAppNotification
            self.db.add(InAppNotification(
                user_id=customer_id, tenant_id=booking.tenant_id,
                notification_type=notif_type, title=title, body=body,
                action_url=f"/customer/bookings/{booking.id}", action_label="View booking",
                source_record_type="service_bookings", source_record_id=booking.id,
                severity="info",
            ))
        except Exception:
            pass

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

    # ── TRACK-TECHNICIAN — live location submission (technician) + read (customer) ──

    async def _customer_safe_technician(self, staff_id: uuid.UUID | None) -> dict | None:
        """Name/role/photo only — never phone. assigned_staff_id may resolve
        to either provider_team_members.id or a raw users.id depending on
        which assignment path wrote it (documented reconciliation quirk in
        staff_router._resolve_staff_member_id) — try both, fail closed to
        None rather than guess."""
        if not staff_id:
            return None
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        ptm = await self.db.get(ProviderTeamMember, staff_id)
        if ptm:
            return {"name": ptm.full_name, "role": ptm.designation or "Service technician",
                    "photo_url": ptm.profile_photo_url}
        from app.engines.auth.models import User
        user = await self.db.get(User, staff_id)
        if user:
            return {"name": user.full_name, "role": "Service technician", "photo_url": None}
        return None

    async def submit_technician_location(
        self, job_id: uuid.UUID, staff_id: uuid.UUID, tenant_id: uuid.UUID | None,
        latitude: float, longitude: float, accuracy_meters: float | None = None,
    ) -> dict:
        from app.engines.final_records.models import ServiceJob
        job = await self.db.get(ServiceJob, job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        if str(job.assigned_staff_id) != str(staff_id):
            raise ValueError(ERR_STAFF_JOB_NOT_ASSIGNED)
        if job.status not in TRACKING_ACTIVE_JOB_STATUSES:
            # Fail closed: never accept (or later serve) a position once the
            # job has left the live-tracking window (arrived/started/
            # completed/cancelled/reassigned-away).
            raise ValueError(ERR_LOCATION_NOT_TRACKABLE)
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise ValueError(ERR_LOCATION_INVALID_COORDS)

        now = _utcnow()
        row = (await self.db.execute(
            select(TechnicianLiveLocation).where(TechnicianLiveLocation.job_id == job_id)
        )).scalars().first()
        if row:
            row.staff_id = staff_id
            row.tenant_id = tenant_id
            row.latitude = latitude
            row.longitude = longitude
            row.accuracy_meters = accuracy_meters
            row.recorded_at = now
        else:
            self.db.add(TechnicianLiveLocation(
                job_id=job_id, staff_id=staff_id, tenant_id=tenant_id,
                latitude=latitude, longitude=longitude,
                accuracy_meters=accuracy_meters, recorded_at=now,
            ))
        await self.db.commit()
        return {"job_id": str(job_id), "recorded_at": now.isoformat()}

    async def get_customer_tracking_location(
        self, booking_id: uuid.UUID, customer_id: uuid.UUID,
    ) -> dict:
        booking, job = await self._load_booking_and_job(booking_id, customer_id)
        if not job:
            return {"available": False, "reason": "not_yet_assigned"}
        if job.status not in TRACKING_ACTIVE_JOB_STATUSES:
            return {"available": False, "reason": "tracking_ended", "job_status": job.status}

        loc = (await self.db.execute(
            select(TechnicianLiveLocation).where(TechnicianLiveLocation.job_id == job.id)
        )).scalars().first()
        if not loc:
            return {"available": False, "reason": "location_unavailable", "job_status": job.status}

        age_seconds = (_utcnow() - loc.recorded_at).total_seconds()

        # Destination coordinates: best-effort, resolved through the real
        # draft->address chain (ServiceBooking has no lat/lng of its own —
        # address_snapshot is text-only). Never fabricated if the chain
        # doesn't resolve.
        dest_lat = dest_lng = None
        try:
            from app.engines.home_service_booking.models import HomeServiceBookingDraft
            from app.engines.serviceability.models import CustomerAddress
            draft = await self.db.get(HomeServiceBookingDraft, booking.draft_id)
            if draft and draft.address_id:
                addr = await self.db.get(CustomerAddress, draft.address_id)
                if addr and addr.latitude is not None and addr.longitude is not None:
                    dest_lat, dest_lng = float(addr.latitude), float(addr.longitude)
        except Exception:
            pass

        technician = await self._customer_safe_technician(job.assigned_staff_id)

        return {
            "available": True,
            "job_status": job.status,
            "latitude": float(loc.latitude),
            "longitude": float(loc.longitude),
            "accuracy_meters": float(loc.accuracy_meters) if loc.accuracy_meters is not None else None,
            "recorded_at": loc.recorded_at.isoformat(),
            "is_stale": age_seconds > LOCATION_STALE_SECONDS,
            "destination_latitude": dest_lat,
            "destination_longitude": dest_lng,
            "technician": technician,
        }

    async def technician_accept_job(
        self,
        job_id:       uuid.UUID,
        staff_id:     uuid.UUID,
        request_id:   str | None = None,
        tenant_id:    uuid.UUID | None = None,
    ) -> dict:
        job = await self._load_job(job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        # Slice 2F-3B, Workstream 6: explicit tenant defense-in-depth. Before
        # this fix, isolation relied solely on the assignment-ownership match
        # below -- correct in practice (a technician's assignment can only
        # ever reference jobs in their own tenant) but with no redundant
        # check if that invariant were ever violated upstream. tenant_id is
        # optional (defaults to None = skip) so this cannot break any
        # existing internal caller that doesn't pass it.
        if tenant_id is not None and str(job.tenant_id) != str(tenant_id):
            raise ValueError(ERR_ACCESS_DENIED)

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
        tenant_id:  uuid.UUID | None = None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError(ERR_REASON_REQUIRED)

        job = await self._load_job(job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        # Slice 2F-3B, Workstream 6: explicit tenant defense-in-depth (see
        # technician_accept_job's identical comment for the full rationale).
        if tenant_id is not None and str(job.tenant_id) != str(tenant_id):
            raise ValueError(ERR_ACCESS_DENIED)

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
        # Recorded on the timeline event. Worth recording precisely because
        # "weather" is verified against a real reading before it can be given (see
        # the provider router's gate) -- an unverifiable reason ends up explaining
        # every moved visit, and then the record explains nothing.
        reason:              str | None       = None,
    ) -> dict:
        job = await self._load_job(job_id)
        if not job:
            raise ValueError(ERR_JOB_NOT_FOUND)
        if str(job.tenant_id) != str(tenant_id):
            raise ValueError(ERR_ACCESS_DENIED)
        if job.status not in {JOB_STATUS_ASSIGNED, JOB_STATUS_ACCEPTED}:
            raise ValueError(ERR_INVALID_STATUS)

        moving_slot = (
            job.scheduled_date != scheduled_date
            or job.scheduled_time_window != scheduled_time_window
        )
        if moving_slot:
            from app.engines.home_service_booking.provider_slot_service import slot_has_capacity
            if not await slot_has_capacity(
                self.db,
                tenant_id=tenant_id,
                day=scheduled_date,
                time_window=scheduled_time_window,
                master_service_id=job.offering_id,
            ):
                raise ValueError(ERR_SLOT_UNAVAILABLE)

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
            reason=(reason or None),
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
        # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.1 (spec section 12): expose
        # the backend's own work-start decision so the staff/tenant UI shows
        # the correct reason without recomputing it -- backend stays
        # authoritative, this is a narration of the same guard.
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        work_start_status = await HomeServiceJobExecutionService().get_work_start_status(self.db, job)
        return {
            "job":        {**job.to_dict(), **work_start_status},
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


# Found genuinely missing during the "make it 100% working" pass -- imported
# by 3 real technician-mobile projections (mobile_home_service.py,
# mobile_job_detail_service.py, mobile_jobs_service.py) but never defined
# anywhere, so every call to any of those endpoints was a hard 500. Maps a
# job's real status (app.engines.execution.constants.JS_*) to the single
# next technician action, using the SAME action route names as the real
# staff_router.py / mobile-work-execution endpoints -- never a fabricated
# route key.
_NEXT_ACTION_BY_STATUS: dict[str, tuple[str, str] | None] = {
    "assigned":            ("accept", "Accept Job"),
    "accepted":            ("on-the-way", "Start Traveling"),
    "scheduled":           ("on-the-way", "Start Traveling"),
    "on_the_way":          ("reached-site", "Mark Reached Site"),
    "reached_site":        ("start-inspection", "Start Inspection"),
    "inspection_started":  ("complete-inspection", "Complete Inspection"),
    "inspection_done":     ("start-service", "Start Service"),
    "quote_required":      None,   # waiting on customer/quote decision -- no technician action
    "service_started":     ("work-done", "Mark Work Done"),
    "work_done":           ("complete", "Complete Job"),
    "customer_not_available": None,
    "completed":           None,
    "cancelled":           None,
    "failed":              None,
    "closed_estimate_declined": None,
}


def _next_required_action(
    status: str, work_start_status: dict, customer_contacted: bool = True,
) -> dict:
    """`customer_contacted` defaults True so every existing caller keeps its
    exact previous behaviour; callers that can determine it pass the real value
    and get the contact-first step."""
    entry = _NEXT_ACTION_BY_STATUS.get(status)
    if entry is None:
        return {"action_type": None, "action_label": None, "allowed": False, "blocked_message": None}

    # FIRST TASK on a job the provider has not yet spoken to the customer
    # about: understand the request and confirm requirements by phone. Travel
    # is not the first action -- a technician arriving without knowing what
    # they are walking into is the whole problem this prevents.
    if status in ("accepted", "scheduled") and not customer_contacted:
        return {
            "action_type": "call-customer",
            "action_label": "Call Customer & Confirm Requirements",
            "allowed": True,
            "blocked_message": None,
        }

    action_type, action_label = entry
    allowed = True
    blocked_message = None
    if status == "inspection_done" and not work_start_status.get("can_start_work", True):
        allowed = False
        blocked_message = "This job cannot start work yet -- an approval or quote step is still pending."

    return {
        "action_type": action_type, "action_label": action_label,
        "allowed": allowed, "blocked_message": blocked_message,
    }


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
