"""Technician Mobile App Phase I — Jobs Directory projection.

GET /v1/staff/mobile-jobs. Composed from the SAME canonical sources as
Phase H's mobile-home projection -- no second job table, no parallel
status vocabulary:

  - HomeServiceJobAssignmentService.get_staff_assigned_jobs (real ServiceJob
    rows, already technician+tenant isolated)
  - HomeServiceJobExecutionService.get_work_start_status + _next_required_action
    (workflow/action authority, reused as-is)
  - ServiceJobQuote (action-required filter: draft/revision_requested/provider_rejected)
  - ServicePaymentRecord.reconciliation_status (payment_confirmation_state)
  - MasterOffering / JobTypeDefinition (labels)
  - _customer_alias (existing masking convention)

Deliberately excludes (disclosed, not fabricated):
  - workflow_status_label/tone -- the mobile client's own WORKFLOW_STATUS_MAP
    (Phase E) is already the single source of truth for this; returning a
    second copy here would create exactly the "second status vocabulary"
    this phase is told not to build.
  - sla_state/sla_label / entity_version / workflow_version -- no such
    columns exist on ServiceJob (audited in Phase H); never fabricated.

Pagination/search/filtering are currently applied in Python over this
technician's own (bounded, already tenant/assignment-isolated) job set,
reusing get_staff_assigned_jobs rather than a new raw query -- the cursor
CONTRACT (opaque, stable, encode_cursor/decode_cursor, keyset on
(created_at, id)) is real and stable regardless; pushing the filtering into
SQL is a straightforward future optimization if a tenant's per-technician
job count grows large enough to matter, without changing this contract.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.base import encode_cursor, decode_cursor

_TERMINAL_COMPLETED = {"completed"}
_TERMINAL_ARCHIVE = {"cancelled", "failed", "closed_estimate_declined"}
_CARRY_OVER_STATUSES = {
    "on_the_way", "reached_site", "inspection_started", "inspection_done",
    "quote_required", "service_started", "work_done",
    # Quote-driven statuses observed in real data but not part of
    # execution.constants.JOB_TRANSITIONS (quote_checklist engine writes
    # these directly) -- included so a job in one of these states is never
    # invisible from every tab (spec: unknown statuses must fail closed on
    # ACTIONS, never on visibility).
    "awaiting_customer_quote_approval", "quote_approved", "quote_rejected", "quote_revision",
}
_IMMEDIATE_ACTION_STATUSES = {"assigned", "accepted"}

VALID_VIEWS = {"today", "active", "upcoming", "completed", "archive"}


def _job_views(status: str, scheduled_date: str | None, today_iso: str) -> set[str]:
    if status in _TERMINAL_COMPLETED:
        return {"completed"}
    if status in _TERMINAL_ARCHIVE:
        return {"archive"}

    views: set[str] = set()
    is_today = scheduled_date == today_iso
    is_future = bool(scheduled_date) and scheduled_date > today_iso

    if is_today or status in _CARRY_OVER_STATUSES:
        views.add("today")
    if is_future:
        views.add("upcoming")
    # Broad "active" bucket -- everything live that isn't purely a
    # future-only scheduled job (those live only in Upcoming until today
    # arrives). Any status not explicitly matched still defaults into
    # Active rather than becoming invisible (spec section 4).
    if not is_future:
        views.add("active")
    return views


def _customer_alias(customer_id) -> str:
    if not customer_id:
        return "Customer"
    return f"Customer HS-{str(customer_id).replace('-', '')[:4].upper()}"


class TechnicianMobileJobsService:
    async def list_jobs(
        self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID,
        view: str, search: str | None, workflow_status: str | None,
        action_required: bool | None, cursor: str | None, limit: int,
    ) -> dict:
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

        staff_id = await self._resolve_staff_member_id(db, user_id)
        assignment_svc = HomeServiceJobAssignmentService(db)
        all_jobs = await assignment_svc.get_staff_assigned_jobs(staff_id, tenant_id)

        today_iso = date.today().isoformat()
        counts_by_view = {v: 0 for v in VALID_VIEWS}
        for j in all_jobs:
            for v in _job_views(j["status"], j.get("scheduled_date"), today_iso):
                counts_by_view[v] += 1

        candidates = [j for j in all_jobs if view in _job_views(j["status"], j.get("scheduled_date"), today_iso)]

        if workflow_status:
            candidates = [j for j in candidates if j["status"] == workflow_status]

        if search:
            needle = search.strip().lower()
            if needle:
                candidates = [
                    j for j in candidates
                    if needle in (j.get("job_number") or "").lower()
                    or needle in (j.get("city") or "").lower()
                    or needle in (j.get("zipcode") or "").lower()
                ]

        action_required_ids: set[str] | None = None
        if action_required:
            action_required_ids = await self._action_required_job_ids(db, [uuid.UUID(j["id"]) for j in candidates])
            candidates = [j for j in candidates if j["id"] in action_required_ids]

        # Stable keyset ordering: (created_at desc, id desc) -- created_at
        # alone is not unique, so ties are broken by id (spec section 12).
        candidates.sort(key=lambda j: (j["created_at"], j["id"]), reverse=True)

        start_index = 0
        if cursor:
            decoded = decode_cursor(cursor)
            for i, j in enumerate(candidates):
                if (j["created_at"], j["id"]) == (decoded.get("created_at"), decoded.get("id")):
                    start_index = i + 1
                    break

        page = candidates[start_index:start_index + limit]
        has_more = (start_index + limit) < len(candidates)
        next_cursor = encode_cursor({"created_at": page[-1]["created_at"], "id": page[-1]["id"]}) if has_more and page else None

        results = [await self._build_result_row(db, j) for j in page]

        return {
            "results": results,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "counts_by_view": counts_by_view,
            "applied_filters": {
                "view": view, "search": search, "workflow_status": workflow_status,
                "action_required": action_required,
            },
            "server_timestamp": datetime.utcnow().isoformat() + "Z",
        }

    async def _resolve_staff_member_id(self, db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
        from sqlalchemy import select
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        res = await db.execute(select(ProviderTeamMember.id).where(ProviderTeamMember.user_id == user_id))
        row = res.scalars().first()
        return row if row else user_id

    async def _action_required_job_ids(self, db: AsyncSession, job_ids: list[uuid.UUID]) -> set[str]:
        if not job_ids:
            return set()
        from sqlalchemy import select
        from app.engines.quote_checklist.models import ServiceJobQuote
        rows = (await db.execute(
            select(ServiceJobQuote.job_id).where(
                ServiceJobQuote.job_id.in_(job_ids),
                ServiceJobQuote.is_current.is_(True),
                ServiceJobQuote.status.in_(("draft", "revision_requested", "provider_rejected")),
            )
        )).scalars().all()
        return {str(jid) for jid in rows}

    async def _build_result_row(self, db: AsyncSession, job_row: dict) -> dict:
        from app.engines.final_records.models import ServiceJob, ServiceBooking
        from app.engines.admin_catalog.models import MasterOffering
        from app.engines.execution.home_service_service import (
            HomeServiceJobExecutionService, customer_already_contacted,
        )
        from app.engines.home_service_assignment.service import _next_required_action
        from sqlalchemy import select
        from app.engines.invoice_payment.models import ServicePaymentRecord

        job = await db.get(ServiceJob, uuid.UUID(job_row["id"]))
        work_start_status = await HomeServiceJobExecutionService().get_work_start_status(db, job)
        # Same input as Home and Job Detail -- one job must not advertise three
        # different next actions depending on which list it is read from.
        next_action = _next_required_action(
            job.status, work_start_status,
            customer_contacted=await customer_already_contacted(db, job.id),
        )

        service_label = None
        if job.offering_id:
            offering = await db.get(MasterOffering, job.offering_id)
            service_label = offering.name if offering else None

        booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
        customer_alias = _customer_alias(booking.customer_id if booking else None)

        payment_row = (await db.execute(
            select(ServicePaymentRecord.reconciliation_status)
            .where(ServicePaymentRecord.job_id == job.id)
            .order_by(ServicePaymentRecord.created_at.desc())
            .limit(1)
        )).scalars().first()

        blocker = None
        if work_start_status.get("start_work_block_code"):
            blocker = {
                "code": work_start_status["start_work_block_code"],
                "message": work_start_status.get("start_work_block_message") or next_action.get("blocked_message"),
            }

        allowed_actions = [next_action["action_type"]] if next_action.get("allowed") and next_action.get("action_type") else []

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
            "safe_locality": ", ".join(p for p in [job.city, job.zipcode] if p) or None,
            "customer_alias": customer_alias,
            "next_required_action": {
                "key": next_action.get("action_type"), "label": next_action.get("action_label"),
                "allowed": next_action.get("allowed", False),
            },
            "allowed_actions": allowed_actions,
            "blocker": blocker,
            "payment_confirmation_state": payment_row,
            "entity_version": None,
            "workflow_version": None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }
