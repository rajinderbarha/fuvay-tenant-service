"""Home Services Dispatch Board — read-side aggregation over the canonical
HomeServiceJobAssignmentService. This module creates NO new assignment
lifecycle, no new eligibility rules, and no new job/staff models — it only
projects existing ServiceJob / ServiceJobAssignment / ProviderTeamMember(or
User) data into the shapes the Dispatch Board UI needs, and extends the
canonical eligible-staff check with one real gap that was previously
unchecked: whether the candidate technician already has another assignment
overlapping the SAME scheduled_date + scheduled_time_window (the existing
`list_eligible_staff_for_job` only checked that an availability RULE exists,
never actual conflicting load for that specific slot).

Canonical reason codes are mapped from the engine's internal reason strings
to the fixed vocabulary the Dispatch Board contract requires. Any internal
reason without a mapping is a bug, not a silently-dropped case.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
from app.engines.home_service_assignment.models import ServiceJobAssignment

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
        return {
            "job_id":                str(job.id),
            "job_number":            job.job_number,
            "booking_id":            str(job.booking_id),
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
        }

    # ── Dispatch Board projection ───────────────────────────────────────────

    async def get_dispatch_projection(self, tenant_id: uuid.UUID, target_date: date) -> dict:
        from app.engines.final_records.models import ServiceJob, ServiceBooking
        from app.engines.admin_catalog.models import MasterService

        jobs_res = await self.db.execute(
            select(ServiceJob, ServiceBooking, MasterService.service_name)
            .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id)
            .outerjoin(MasterService, MasterService.id == ServiceJob.offering_id)
            .where(
                ServiceJob.tenant_id == tenant_id,
                ServiceJob.status.notin_(["cancelled", "failed"]),
            )
            .order_by(ServiceJob.created_at.asc())
        )
        rows = jobs_res.all()

        unassigned_jobs: list[dict] = []
        scheduled_today: list[dict] = []
        on_the_way = 0
        conflicts = 0

        # Group scheduled jobs (with a current assignment) by staff for the
        # technician-schedule panel -- one row per technician.
        by_staff: dict[str, list[dict]] = {}

        current_assignments_res = await self.db.execute(
            select(ServiceJobAssignment).where(
                ServiceJobAssignment.tenant_id == tenant_id,
                ServiceJobAssignment.is_current == True,  # noqa: E712
            )
        )
        assignment_by_job = {str(a.job_id): a for a in current_assignments_res.scalars().all()}

        for job, booking, service_name in rows:
            entry = self._job_summary(job, booking)
            entry["master_service_name"] = service_name

            if job.assignment_status == "unassigned":
                unassigned_jobs.append(entry)
                continue

            assignment = assignment_by_job.get(str(job.id))
            staff_id = str(job.assigned_staff_id) if job.assigned_staff_id else None
            if not staff_id:
                continue

            if job.scheduled_date == target_date:
                entry["assignment_id"] = str(assignment.id) if assignment else None
                by_staff.setdefault(staff_id, []).append(entry)
                scheduled_today.append(entry)
                if job.status == "accepted":
                    on_the_way += 1

        # Conflicts: two current assignments for the same staff, same date,
        # same time_window -- a real, already-committed double-booking (not
        # a hypothetical one computed against a candidate; see
        # get_assignment_options for the pre-assignment version of this check).
        for staff_id, entries in by_staff.items():
            seen: dict[tuple, int] = {}
            for e in entries:
                key = (e["scheduled_date"], e["scheduled_time_window"])
                seen[key] = seen.get(key, 0) + 1
            conflicts += sum(1 for count in seen.values() if count > 1)

        technicians = await self._technician_roster(tenant_id)
        technician_schedule = [
            {
                "staff_member_id": t["staff_member_id"],
                "name":            t["name"],
                "status":          t["status"],
                "jobs_today":      by_staff.get(t["staff_member_id"], []),
            }
            for t in technicians
        ]

        capacity_used = sum(1 for t in technicians if by_staff.get(t["staff_member_id"]))

        return {
            "summary": {
                "unassigned_count":     len(unassigned_jobs),
                "scheduled_count":      len(scheduled_today),
                "on_the_way_count":     on_the_way,
                "capacity_used":        capacity_used,
                "capacity_total":       len(technicians),
                "conflict_count":       conflicts,
            },
            "unassigned_jobs":     unassigned_jobs,
            "technician_schedule": technician_schedule,
            "conflicts":           conflicts,
            "available_actions":   ["assign", "reassign", "unassign"],
            "generated_at":        _utcnow().isoformat(),
        }

    async def _technician_roster(self, tenant_id: uuid.UUID) -> list[dict]:
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        from app.engines.auth.models import User

        res = await self.db.execute(
            select(ProviderTeamMember).where(
                ProviderTeamMember.tenant_id == tenant_id,
                ProviderTeamMember.deleted_at.is_(None),
            )
        )
        rows = list(res.scalars().all())
        if rows:
            return [{"staff_member_id": str(r.id), "name": r.full_name,
                      "status": r.status} for r in rows]

        res2 = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id, User.role.in_(["technician", "staff"]))
        )
        users = list(res2.scalars().all())
        return [{"staff_member_id": str(u.id), "name": u.full_name,
                  "status": "active" if getattr(u, "is_active", True) else "inactive"} for u in users]

    # ── Assignment options (single job) ─────────────────────────────────────

    async def get_assignment_options(self, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        job = await self._load_job_row(job_id)
        if not job or str(job.tenant_id) != str(tenant_id):
            raise ValueError("JOB_NOT_FOUND")
        booking = await self._load_booking_row(job.booking_id)
        service_name = await self._master_service_name(job.offering_id) if job.offering_id else None

        raw = await self._assign_svc.list_eligible_staff_for_job(job_id, tenant_id)

        eligible_out = []
        for e in raw["eligible_staff"]:
            conflict = await self._schedule_conflict_reason(tenant_id, uuid.UUID(e["staff_member_id"]), job)
            if conflict:
                raw["blocked_staff"].append({**e, "eligibility_status": "blocked", "blocked_reasons": [conflict]})
                continue
            eligible_out.append(e)

        excluded_out = []
        for b in raw["blocked_staff"]:
            codes = [_REASON_CODE_MAP.get(r, r.upper()) for r in b.get("blocked_reasons", [])]
            excluded_out.append({**b, "exclusion_reason_codes": codes})

        current_assignment = await self._assign_svc._current_assignment(job_id)

        return {
            "job_context": {
                **self._job_summary(job, booking),
                "master_service_name": service_name,
            },
            "eligible_technicians":  eligible_out,
            "excluded_technicians":  excluded_out,
            "current_assignment":    current_assignment.to_dict() if current_assignment else None,
            "available_actions":     ["assign", "reassign", "unassign"] if not eligible_out == [] or current_assignment else ["assign"],
            "version":               job.updated_at.isoformat() if job.updated_at else None,
        }

    async def _schedule_conflict_reason(self, tenant_id: uuid.UUID, staff_member_id: uuid.UUID, job) -> str | None:
        """Real conflict check the canonical engine never performed: does this
        candidate already hold another CURRENT, non-cancelled assignment for
        the same scheduled_date + scheduled_time_window? Equality-based (not
        true interval overlap) because scheduled_time_window is a free-form
        slot label, not a structured start/end -- documented limitation."""
        if not job.scheduled_date or not job.scheduled_time_window:
            return None
        res = await self.db.execute(
            select(ServiceJobAssignment).where(
                and_(
                    ServiceJobAssignment.tenant_id == tenant_id,
                    ServiceJobAssignment.assigned_staff_member_id == staff_member_id,
                    ServiceJobAssignment.is_current == True,  # noqa: E712
                    ServiceJobAssignment.job_id != job.id,
                    ServiceJobAssignment.scheduled_date == job.scheduled_date,
                    ServiceJobAssignment.scheduled_time_window == job.scheduled_time_window,
                    ServiceJobAssignment.assignment_status.notin_(["cancelled", "rejected"]),
                )
            )
        )
        return "schedule_conflict" if res.scalars().first() else None
