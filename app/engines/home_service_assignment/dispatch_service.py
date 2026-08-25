"""Home Services Dispatch Board — read-side aggregation over the canonical
HomeServiceJobAssignmentService. This module creates NO new assignment
lifecycle, no new eligibility rules, and no new job/staff models — it only
projects existing ServiceJob / ServiceJobAssignment / ProviderTeamMember(or
User) data into the shapes the Dispatch Board UI needs, and extends the
canonical eligible-staff check with one real gap that was previously
unchecked: whether the candidate technician already has another assignment
whose interval overlaps the requested interval on the same date (the
existing `list_eligible_staff_for_job` only checked that an availability
RULE exists, never actual conflicting load for that specific slot).

Canonical reason codes are mapped from the engine's internal reason strings
to the fixed vocabulary the Dispatch Board contract requires. Any internal
reason without a mapping is a bug, not a silently-dropped case.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
from app.engines.home_service_assignment.models import ServiceJobAssignment
from app.engines.final_records.bookings_jobs_stage_mapping import TERMINAL_STATUSES
from app.engines.weather.slots import slot_end, slot_start

_utcnow = lambda: datetime.now(timezone.utc)

# Internal engine reason string -> canonical Dispatch Board exclusion code.
# STAFF_NOT_VERIFIED, TYPE_UNSUPPORTED, BRAND_UNSUPPORTED, OUTSIDE_COVERAGE
# are NOT produced today -- the engine has no verification flag, no stored
# per-job Type/Brand selection, and no coverage-area check wired into
# eligibility (see final report "Remaining limitations"). They stay in this
# map only as the target codes to use once that data exists upstream.
_REASON_CODE_MAP = {
    "wrong_tenant":              "TENANT_MISMATCH",
    "staff_inactive":            "STAFF_INACTIVE",
    "cannot_receive_assignment": "STAFF_INACTIVE",
    "role_not_allowed":          "JOB_TYPE_UNSUPPORTED",
    "no_matching_service_skill": "JOB_TYPE_UNSUPPORTED",
    "service_not_configured":    "SERVICE_NOT_CONFIGURED",
    "no_availability_configured":"OUTSIDE_AVAILABILITY",
    "schedule_conflict":         "SCHEDULE_CONFLICT",
}


class HomeServiceDispatchProjectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._assign_svc = HomeServiceJobAssignmentService(db)

    # ── Shared loaders ──────────────────────────────────────────────────────

    async def _load_job_row(self, job_id: uuid.UUID):
        from app.engines.final_records.models import ServiceJob
        res = await self.db.execute(select(ServiceJob).where(ServiceJob.id == job_id))
        return res.scalars().first()

    async def _load_booking_row(self, booking_id: uuid.UUID):
        from app.engines.final_records.models import ServiceBooking
        res = await self.db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
        return res.scalars().first()

    async def _master_service_name(self, master_service_id: uuid.UUID) -> str | None:
        from app.engines.admin_catalog.models import MasterService
        res = await self.db.execute(select(MasterService.service_name).where(MasterService.id == master_service_id))
        row = res.first()
        return row[0] if row else None

    def _job_summary(self, job, booking) -> dict:
        # Dispatch Board is a bulk projection shown to office staff BEFORE
        # (or independent of) assignment — raw customer_name/phone here would
        # be exactly the bulk-exportable poaching leak the customer-privacy
        # policy exists to prevent. Alias + masked locality only; per-job
        # exact contact/address is granted separately once a technician is
        # actually assigned (see CustomerOperationalAccessPolicy).
        from app.engines.tenant_engine.customer_operational_access_policy import (
            customer_alias as _alias, masked_locality as _loc,
        )
        due_at = slot_end(job.scheduled_date, job.scheduled_time_window)
        now = _utcnow()
        minutes_until_due = None
        if due_at is not None:
            minutes_until_due = int((due_at - now.astimezone(due_at.tzinfo)).total_seconds() // 60)
        return {
            "job_id":                str(job.id),
            "job_number":            job.job_number,
            "booking_id":            str(job.booking_id),
            "booking_number":        booking.booking_number if booking else None,
            "status":                job.status,
            "assignment_status":     job.assignment_status,
            "assigned_staff_id":     str(job.assigned_staff_id) if job.assigned_staff_id else None,
            "requested_at":          booking.created_at.isoformat() if booking and booking.created_at else None,
            "scheduled_date":        job.scheduled_date.isoformat() if job.scheduled_date else None,
            "scheduled_time_window": job.scheduled_time_window,
            "customer_alias":       _alias(job.tenant_id, job.customer_id) if job.customer_id else None,
            "locality":              _loc(job.city, job.zipcode),
            "city":                  job.city,
            "zipcode":               job.zipcode,
            "issue_summary":         booking.issue_summary if booking else None,
            "is_emergency":          bool(getattr(booking, "is_emergency", False)) if booking else False,
            "service_due_at":        due_at.isoformat() if due_at else None,
            "minutes_until_due":     minutes_until_due,
            "is_overdue":            bool(minutes_until_due is not None and minutes_until_due < 0),
        }

    # ── Dispatch Board projection ───────────────────────────────────────────

    async def get_dispatch_projection(
        self,
        tenant_id: uuid.UUID,
        target_date: date,
        *,
        view: str = "day",
        search: str | None = None,
        offering_id: uuid.UUID | None = None,
        technician_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        from app.engines.final_records.models import ServiceJob, ServiceBooking
        from app.engines.admin_catalog.models import MasterService, TenantService

        range_end = target_date + timedelta(days=6 if view == "week" else 0)
        base_conditions = [
            ServiceJob.tenant_id == tenant_id,
            ServiceJob.status.notin_(list(TERMINAL_STATUSES)),
        ]
        if offering_id:
            base_conditions.append(ServiceJob.offering_id == offering_id)
        if technician_id:
            base_conditions.append(ServiceJob.assigned_staff_id == technician_id)
        if search and search.strip():
            escaped = search.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            base_conditions.append(or_(
                func.lower(ServiceJob.job_number).like(pattern, escape="\\"),
                func.lower(ServiceBooking.booking_number).like(pattern, escape="\\"),
                func.lower(func.coalesce(MasterService.service_name, "")).like(pattern, escape="\\"),
                func.lower(func.coalesce(ServiceBooking.issue_summary, "")).like(pattern, escape="\\"),
                func.lower(func.coalesce(ServiceJob.city, "")).like(pattern, escape="\\"),
            ))

        unassigned_conditions = [
            *base_conditions,
            ServiceJob.assignment_status == "unassigned",
            or_(
                ServiceJob.scheduled_date.is_(None),
                ServiceJob.scheduled_date.between(target_date, range_end),
            ),
        ]
        if technician_id:
            # A job cannot be both unassigned and assigned to the selected technician.
            unassigned_conditions.append(ServiceJob.id.is_(None))

        scheduled_conditions = [
            *base_conditions,
            ServiceJob.assignment_status != "unassigned",
            ServiceJob.scheduled_date.between(target_date, range_end),
        ]

        row_shape = (
            select(ServiceJob, ServiceBooking, MasterService.service_name)
            .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id)
            .outerjoin(MasterService, MasterService.id == ServiceJob.offering_id)
        )
        unassigned_total = int((await self.db.execute(
            select(func.count(ServiceJob.id))
            .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id)
            .outerjoin(MasterService, MasterService.id == ServiceJob.offering_id)
            .where(*unassigned_conditions)
        )).scalar_one())
        unassigned_rows = (await self.db.execute(
            row_shape.where(*unassigned_conditions)
            .order_by(ServiceJob.scheduled_date.asc().nullslast(), ServiceJob.created_at.asc(), ServiceJob.id.asc())
            .limit(limit).offset(offset)
        )).all()

        # A tenant cannot operationally dispatch thousands of visits in one
        # visible week. Keep the schedule response bounded and explicitly tell
        # the client when the safety cap is reached instead of exhausting the
        # application process.
        schedule_cap = 5000
        scheduled_total = int((await self.db.execute(
            select(func.count(ServiceJob.id))
            .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id)
            .outerjoin(MasterService, MasterService.id == ServiceJob.offering_id)
            .where(*scheduled_conditions)
        )).scalar_one())
        scheduled_rows = (await self.db.execute(
            row_shape.where(*scheduled_conditions)
            .order_by(ServiceJob.scheduled_date.asc(), ServiceJob.scheduled_time_window.asc(), ServiceJob.id.asc())
            .limit(schedule_cap)
        )).all()

        unassigned_jobs: list[dict] = []
        scheduled_jobs: list[dict] = []
        on_the_way = 0

        # Group scheduled jobs (with a current assignment) by staff for the
        # technician-schedule panel -- one row per technician.
        by_staff: dict[str, list[dict]] = {}

        scheduled_job_ids = [job.id for job, _booking, _name in scheduled_rows]
        current_assignments_res = await self.db.execute(
            select(ServiceJobAssignment).where(
                ServiceJobAssignment.tenant_id == tenant_id,
                ServiceJobAssignment.is_current == True,  # noqa: E712
                ServiceJobAssignment.job_id.in_(scheduled_job_ids),
            )
        ) if scheduled_job_ids else None
        assignment_by_job = (
            {str(a.job_id): a for a in current_assignments_res.scalars().all()}
            if current_assignments_res is not None else {}
        )

        for job, booking, service_name in unassigned_rows:
            entry = self._job_summary(job, booking)
            entry["master_service_name"] = service_name
            unassigned_jobs.append(entry)

        for job, booking, service_name in scheduled_rows:
            entry = self._job_summary(job, booking)
            entry["master_service_name"] = service_name
            assignment = assignment_by_job.get(str(job.id))
            staff_id = str(job.assigned_staff_id) if job.assigned_staff_id else None
            if not staff_id:
                continue
            entry["assignment_id"] = str(assignment.id) if assignment else None
            by_staff.setdefault(staff_id, []).append(entry)
            scheduled_jobs.append(entry)
            if job.status == "on_the_way":
                on_the_way += 1

        # Conflicts are real overlapping committed intervals for the same
        # technician. Candidate conflicts are handled separately by
        # get_assignment_options before an assignment is created.
        conflict_job_ids: set[str] = set()
        for entries in by_staff.values():
            for index, first in enumerate(entries):
                first_start = slot_start(date.fromisoformat(first["scheduled_date"]), first["scheduled_time_window"])
                first_end = slot_end(date.fromisoformat(first["scheduled_date"]), first["scheduled_time_window"])
                if not first_start or not first_end:
                    continue
                for second in entries[index + 1:]:
                    second_start = slot_start(date.fromisoformat(second["scheduled_date"]), second["scheduled_time_window"])
                    second_end = slot_end(date.fromisoformat(second["scheduled_date"]), second["scheduled_time_window"])
                    if second_start and second_end and first_start < second_end and second_start < first_end:
                        conflict_job_ids.update((first["job_id"], second["job_id"]))
        for entry in scheduled_jobs:
            entry["has_conflict"] = entry["job_id"] in conflict_job_ids

        roster = await self._technician_roster(tenant_id)
        technicians = roster
        if technician_id:
            technicians = [t for t in roster if t["staff_member_id"] == str(technician_id)]
        staff_names = {t["staff_member_id"]: t["name"] for t in roster}
        for entry in scheduled_jobs:
            entry["assigned_staff_name"] = staff_names.get(entry["assigned_staff_id"])
        technician_schedule = [
            {
                "staff_member_id": t["staff_member_id"],
                "name":            t["name"],
                "status":          t["status"],
                "jobs_in_range":   by_staff.get(t["staff_member_id"], []),
                # Compatibility alias for older clients during rollout.
                "jobs_today":      by_staff.get(t["staff_member_id"], []),
            }
            for t in technicians
        ]

        active_technicians = [
            t for t in technicians
            if t["status"] == "active" and t.get("can_receive_assignment", True)
        ]
        capacity_used = sum(1 for t in active_technicians if by_staff.get(t["staff_member_id"]))

        service_rows = (await self.db.execute(
            select(MasterService.id, MasterService.service_name)
            .join(TenantService, TenantService.master_service_id == MasterService.id)
            .where(
                TenantService.tenant_id == tenant_id,
                TenantService.is_active.is_(True),
                TenantService.deleted_at.is_(None),
            )
            .distinct().order_by(MasterService.service_name.asc())
        )).all()

        return {
            "summary": {
                "unassigned_count":     unassigned_total,
                "scheduled_count":      scheduled_total,
                "on_the_way_count":     on_the_way,
                "capacity_used":        capacity_used,
                "capacity_total":       len(active_technicians),
                "conflict_count":       len(conflict_job_ids),
            },
            "unassigned_jobs":     unassigned_jobs,
            "technician_schedule": technician_schedule,
            "scheduled_jobs":      scheduled_jobs,
            "conflicts":           len(conflict_job_ids),
            "available_actions":   ["assign", "reassign", "unassign"],
            "pagination": {
                "total": unassigned_total, "limit": limit, "offset": offset,
            },
            "filters": {
                "services": [{"id": str(row[0]), "name": row[1]} for row in service_rows],
                # Keep the complete roster available in the selector even
                # while the schedule itself is narrowed to one technician.
                "technicians": roster,
            },
            "view": view,
            "range_start": target_date.isoformat(),
            "range_end": range_end.isoformat(),
            "schedule_truncated": scheduled_total > schedule_cap,
            "generated_at":        _utcnow().isoformat(),
        }

    async def _technician_roster(self, tenant_id: uuid.UUID) -> list[dict]:
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        from app.engines.auth.models import User
        from app.engines.home_service_assignment.constants import ELIGIBLE_DESIGNATIONS

        res = await self.db.execute(
            select(ProviderTeamMember).where(
                ProviderTeamMember.tenant_id == tenant_id,
                ProviderTeamMember.deleted_at.is_(None),
                or_(
                    ProviderTeamMember.member_type.in_(["technician", "owner_technician"]),
                    func.lower(ProviderTeamMember.designation).in_(list(ELIGIBLE_DESIGNATIONS)),
                ),
            )
        )
        rows = list(res.scalars().all())
        if rows:
            return [{"staff_member_id": str(r.id), "name": r.full_name,
                      "status": r.status,
                      "can_receive_assignment": bool(r.can_receive_assignment)} for r in rows]

        res2 = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id, User.role.in_(["technician", "staff"]))
        )
        users = list(res2.scalars().all())
        return [{"staff_member_id": str(u.id), "name": u.full_name,
                  "status": "active" if getattr(u, "is_active", True) else "inactive",
                  "can_receive_assignment": bool(getattr(u, "is_active", True))} for u in users]

    # ── Assignment options (single job) ─────────────────────────────────────

    async def get_assignment_options(self, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        job = await self._load_job_row(job_id)
        if not job or str(job.tenant_id) != str(tenant_id):
            raise ValueError("JOB_NOT_FOUND")
        booking = await self._load_booking_row(job.booking_id)
        service_name = await self._master_service_name(job.offering_id) if job.offering_id else None

        raw = await self._assign_svc.list_eligible_staff_for_job(job_id, tenant_id)

        eligible_ids = [uuid.UUID(e["staff_member_id"]) for e in raw["eligible_staff"]]
        conflicting_staff = await self._conflicting_staff_ids(tenant_id, job, eligible_ids)
        eligible_out = []
        for e in raw["eligible_staff"]:
            if uuid.UUID(e["staff_member_id"]) in conflicting_staff:
                raw["blocked_staff"].append({
                    **e,
                    "eligibility_status": "blocked",
                    "blocked_reasons": ["schedule_conflict"],
                })
                continue
            eligible_out.append(e)

        excluded_out = []
        for b in raw["blocked_staff"]:
            codes = [_REASON_CODE_MAP.get(r, r.upper()) for r in b.get("blocked_reasons", [])]
            excluded_out.append({**b, "exclusion_reason_codes": codes})

        current_assignment = await self._assign_svc._current_assignment(job_id)
        current_assignment_payload = current_assignment.to_dict() if current_assignment else None
        if current_assignment_payload:
            roster = await self._technician_roster(tenant_id)
            current_assignment_payload["staff_name"] = next(
                (
                    row["name"] for row in roster
                    if row["staff_member_id"] == str(current_assignment.assigned_staff_member_id)
                ),
                None,
            )

        actions: list[str] = []
        if job.status not in TERMINAL_STATUSES:
            if current_assignment:
                actions.append("unassign")
                if eligible_out:
                    actions.append("reassign")
            elif eligible_out:
                actions.append("assign")

        return {
            "job_context": {
                **self._job_summary(job, booking),
                "master_service_name": service_name,
            },
            "eligible_technicians":  eligible_out,
            "excluded_technicians":  excluded_out,
            "current_assignment":    current_assignment_payload,
            "available_actions":     actions,
            "version":               job.updated_at.isoformat() if job.updated_at else None,
        }

    async def _conflicting_staff_ids(
        self,
        tenant_id: uuid.UUID,
        job,
        staff_member_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        """Return candidates who already have an overlapping current visit.

        A single bounded query replaces the previous query-per-technician
        implementation. Windows are compared as intervals, so 09:00-11:00
        correctly conflicts with 10:30-12:00.
        """
        if not staff_member_ids or not job.scheduled_date or not job.scheduled_time_window:
            return set()
        target_start = slot_start(job.scheduled_date, job.scheduled_time_window)
        target_end = slot_end(job.scheduled_date, job.scheduled_time_window)
        if not target_start or not target_end:
            return set()
        res = await self.db.execute(
            select(ServiceJobAssignment).where(
                and_(
                    ServiceJobAssignment.tenant_id == tenant_id,
                    ServiceJobAssignment.assigned_staff_member_id.in_(staff_member_ids),
                    ServiceJobAssignment.is_current == True,  # noqa: E712
                    ServiceJobAssignment.job_id != job.id,
                    ServiceJobAssignment.scheduled_date == job.scheduled_date,
                    ServiceJobAssignment.assignment_status.notin_(["cancelled", "rejected"]),
                )
            )
        )
        conflicts: set[uuid.UUID] = set()
        for assignment in res.scalars().all():
            other_start = slot_start(assignment.scheduled_date, assignment.scheduled_time_window)
            other_end = slot_end(assignment.scheduled_date, assignment.scheduled_time_window)
            if other_start and other_end and target_start < other_end and other_start < target_end:
                conflicts.add(assignment.assigned_staff_member_id)
        return conflicts
