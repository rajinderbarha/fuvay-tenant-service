"""Technician Mobile App Phase H — Home projection.

One purpose-built read aggregation for the technician mobile Home screen,
composed ENTIRELY from existing canonical sources -- no second job store,
no parallel status vocabulary:

  - HomeServiceJobAssignmentService.get_staff_assigned_jobs (real ServiceJob rows)
  - HomeServiceJobExecutionService.get_work_start_status + the existing
    _next_required_action projection (workflow-action authority)
  - ProviderTeamMember (technician identity/availability)
  - NotificationService.get_unread_count
  - MasterOffering / JobTypeDefinition (service + exact job-type labels)
  - _customer_alias (existing masking convention)

Deterministic current-job selection (spec section 5):
  1. A job actively in execution
  2. A job needing an immediate technician action (assigned/accepted)
  3. The next scheduled job today
  4. None
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_assignment.staff_model import ProviderTeamMember

_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "closed_estimate_declined"}
_ACTIVE_EXECUTION_STATUSES = {
    "on_the_way", "reached_site", "inspection_started", "inspection_done", "service_started", "work_done",
}
_IMMEDIATE_ACTION_STATUSES = {"assigned", "accepted"}


async def _customer_already_contacted(db: AsyncSession, job_id: uuid.UUID) -> bool:
    """Whether the provider has logged the required first customer call.

    Presence of a real `customer_contacted` execution event -- never inferred
    from status or elapsed time, so the "call the customer first" step can only
    be satisfied by actually doing it.

    Masked calling writes this same event when a bridged call genuinely
    CONNECTS (see masked_calling.service._record_customer_contacted), so there
    is one definition of "contacted" shared by the platform call and the manual
    log-it endpoint -- and a ring-out satisfies neither.
    """
    from sqlalchemy import text as _sa_text
    from app.engines.execution.constants import EV_CUSTOMER_CONTACTED
    row = (await db.execute(_sa_text(
        "SELECT 1 FROM service_job_execution_events "
        "WHERE job_id=:jid AND event_type=:et LIMIT 1"
    ), {"jid": str(job_id), "et": EV_CUSTOMER_CONTACTED})).fetchone()
    return row is not None


def _select_current_job(jobs: list[dict]) -> dict | None:
    """Pure, deterministic selection over already tenant/staff-scoped jobs
    (spec section 5) -- never "first row returned"."""
    today = date.today()
    live = [j for j in jobs if j["status"] not in _TERMINAL_STATUSES]

    active = [j for j in live if j["status"] in _ACTIVE_EXECUTION_STATUSES]
    if active:
        # Most recently updated active job -- the one the technician was
        # last working on, not an arbitrary one.
        return max(active, key=lambda j: j.get("updated_at") or "")

    immediate = [j for j in live if j["status"] in _IMMEDIATE_ACTION_STATUSES]
    if immediate:
        return min(immediate, key=lambda j: j.get("scheduled_date") or "9999-99-99")

    scheduled_today = [
        j for j in live
        if j.get("scheduled_date") == today.isoformat() and j["status"] not in _IMMEDIATE_ACTION_STATUSES
    ]
    if scheduled_today:
        return min(scheduled_today, key=lambda j: j.get("scheduled_time_window") or "99:99")

    return None


def _customer_alias(customer_id) -> str:
    if not customer_id:
        return "Customer"
    return f"Customer HS-{str(customer_id).replace('-', '')[:4].upper()}"


class TechnicianMobileHomeService:
    async def get_home(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        from app.engines.home_service_assignment.service import _next_required_action
        from app.engines.platform_notifications.notification_service import NotificationService
        from app.engines.final_records.models import ServiceJob, ServiceBooking

        staff_id = await self._resolve_staff_member_id(db, user_id)

        assignment_svc = HomeServiceJobAssignmentService(db)
        jobs = await assignment_svc.get_staff_assigned_jobs(staff_id, tenant_id)

        today = date.today()
        live = [j for j in jobs if j["status"] not in _TERMINAL_STATUSES]
        completed_today = [
            j for j in jobs
            if j["status"] == "completed" and j.get("scheduled_date") == today.isoformat()
        ]
        today_jobs = [j for j in live if j.get("scheduled_date") == today.isoformat()]
        shift_summary = {
            "jobs_today": len(today_jobs) + len(completed_today),
            "completed": len(completed_today),
            "remaining": len(today_jobs),
        }

        current_job_row = _select_current_job(jobs)
        current_job = None
        if current_job_row:
            current_job = await self._build_current_job(db, current_job_row, tenant_id)

        today_schedule = [
            self._schedule_row(j) for j in sorted(today_jobs, key=lambda j: j.get("scheduled_time_window") or "99:99")
        ]

        action_required = await self._action_required(db, tenant_id, staff_id, jobs)

        technician_row = await db.get(ProviderTeamMember, staff_id)
        notif_svc = NotificationService()
        unread_count = await notif_svc.get_unread_count(db, user_id)

        return {
            "technician": {
                "id": str(staff_id),
                "display_name": (technician_row.full_name.split(" ")[0] if technician_row and technician_row.full_name else "Technician"),
                "status": technician_row.status if technician_row else "active",
            },
            "availability": {
                "state": technician_row.availability_state if technician_row else "available",
                "updated_at": technician_row.availability_updated_at.isoformat()
                if technician_row and technician_row.availability_updated_at else None,
            },
            "shift_summary": shift_summary,
            "current_job": current_job,
            "today_schedule": today_schedule,
            "action_required": action_required,
            "unread_notification_count": unread_count,
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _resolve_staff_member_id(self, db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
        """Identical fallback convention to my_work_router.py /
        home_service_assignment/staff_router.py -- provider_team_members is
        unpopulated in real/demo data, so ServiceJob.assigned_staff_id
        actually stores the raw auth user id."""
        res = await db.execute(select(ProviderTeamMember.id).where(ProviderTeamMember.user_id == user_id))
        row = res.scalars().first()
        return row if row else user_id

    async def _build_current_job(self, db: AsyncSession, job_row: dict, tenant_id: uuid.UUID) -> dict:
        from app.engines.final_records.models import ServiceJob, ServiceBooking
        from app.engines.admin_catalog.models import MasterOffering
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        from app.engines.home_service_assignment.service import _next_required_action

        job = await db.get(ServiceJob, uuid.UUID(job_row["id"]))
        work_start_status = await HomeServiceJobExecutionService().get_work_start_status(db, job)
        next_action = _next_required_action(
            job.status, work_start_status,
            customer_contacted=await _customer_already_contacted(db, job.id),
        )

        service_label = None
        if job.offering_id:
            offering = await db.get(MasterOffering, job.offering_id)
            service_label = offering.name if offering else None

        booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
        customer_alias = _customer_alias(booking.customer_id if booking else None)

        blocker = None
        if work_start_status.get("start_work_block_code"):
            blocker = {
                "code": work_start_status["start_work_block_code"],
                "message": next_action.get("blocked_message"),
            }

        return {
            "job_id": str(job.id),
            "job_reference": job.job_number,
            "offering_id": str(job.offering_id) if job.offering_id else None,
            "service_label": service_label,
            "job_type_id": work_start_status.get("job_type_id"),
            "job_type_label": work_start_status.get("job_type_label"),
            "workflow_status": job.status,
            "scheduled_date": job.scheduled_date.isoformat() if job.scheduled_date else None,
            "scheduled_time_window": job.scheduled_time_window,
            "locality_label": ", ".join(p for p in [job.city, job.zipcode] if p) or None,
            "customer_alias": customer_alias,
            "next_required_action": {
                "key": next_action.get("action_type"),
                "label": next_action.get("action_label"),
                "allowed": next_action.get("allowed", False),
            },
            "blocker": blocker,
            "entity_version": None,   # ServiceJob has no version column (audited) -- never fabricated.
            "workflow_version": None,
        }

    def _schedule_row(self, job_row: dict) -> dict:
        return {
            "job_id": job_row["id"],
            "job_reference": job_row["job_number"],
            "job_type_id": job_row.get("job_type_id"),
            "workflow_status": job_row["status"],
            "scheduled_time_window": job_row.get("scheduled_time_window"),
            "locality_label": ", ".join(p for p in [job_row.get("city"), job_row.get("zipcode")] if p) or None,
        }

    async def _action_required(self, db: AsyncSession, tenant_id: uuid.UUID, staff_id: uuid.UUID, jobs: list[dict]) -> list[dict]:
        """Genuine backend-provided technician actions only (spec section 2)
        -- derived from real quote/parts state, never invented categories."""
        from app.engines.quote_checklist.models import ServiceJobQuote
        from app.engines.execution.models import PartsRequest

        items: list[dict] = []
        live_ids = [uuid.UUID(j["id"]) for j in jobs if j["status"] not in _TERMINAL_STATUSES]
        if not live_ids:
            return items

        quotes = (await db.execute(
            select(ServiceJobQuote).where(ServiceJobQuote.job_id.in_(live_ids), ServiceJobQuote.is_current.is_(True))
        )).scalars().all()
        job_number_by_id = {j["id"]: j["job_number"] for j in jobs}
        for q in quotes:
            job_number = job_number_by_id.get(str(q.job_id), "")
            if q.status == "draft":
                items.append({"key": "estimate_awaiting_submission", "label": "Estimate awaiting submission",
                              "job_id": str(q.job_id), "job_reference": job_number})
            elif q.status == "revision_requested":
                items.append({"key": "estimate_revision_required", "label": "Estimate revision required",
                              "job_id": str(q.job_id), "job_reference": job_number})

        parts = (await db.execute(
            select(PartsRequest).where(PartsRequest.job_id.in_(live_ids))
        )).scalars().all()
        for p in parts:
            job_number = job_number_by_id.get(str(p.job_id), "")
            if p.status in ("business_approved", "customer_approved"):
                items.append({"key": "parts_awaiting_installation_confirmation", "label": "Parts approval response",
                              "job_id": str(p.job_id), "job_reference": job_number})

        return items
