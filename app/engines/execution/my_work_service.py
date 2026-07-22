"""Phase 2A — Technician My Work aggregation.

Derives a role-specific action queue from real, existing canonical records
(ServiceJob + PartsRequest) rather than introducing a second, independent
workflow-state store, per docs/workflow-rearchitecture/phase-01a/my-work-contract.md.

Scope for this phase: technician role only, ServiceJob-backed jobs and their
PartsRequest sub-records. Does NOT read from Booking or field_ops Job — those
pipelines remain unresolved per
docs/workflow-rearchitecture/phase-01a/booking-job-canonical-decision.md, and
per that decision's explicit instruction, no cross-pipeline aggregation may be
built without separate approval.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.execution.constants import (
    PARTS_STATUS_REQUESTED,
    PARTS_STATUS_BUSINESS_APPROVED,
    PARTS_STATUS_BUSINESS_REJECTED,
    PARTS_STATUS_CUSTOMER_APPROVAL_PENDING,
    PARTS_STATUS_CUSTOMER_APPROVED,
    PARTS_STATUS_CUSTOMER_REJECTED,
    PARTS_STATUS_INSTALLED,
)

# ── Job-status -> My Work item template ─────────────────────────────────────
# Each entry: (work_type, category, user_facing_status, recommended_action,
#              available_actions, primary_action)
_JOB_STATUS_MAP: dict[str, tuple[str, str, str, str, list[str], str | None]] = {
    "assigned": (
        "job_assigned", "REQUIRES_MY_ACTION", "Awaiting your response",
        "Accept or reject this job", ["accept", "reject"], "accept",
    ),
    "accepted": (
        "job_scheduled", "SCHEDULED", "Scheduled",
        "Head out when it's time", ["on_the_way"], "on_the_way",
    ),
    "on_the_way": (
        "job_en_route", "REQUIRES_MY_ACTION", "En route",
        "Mark reached site on arrival", ["reached_site"], "reached_site",
    ),
    "reached_site": (
        "job_inspection_needed", "REQUIRES_MY_ACTION", "At site",
        "Start the inspection", ["start_inspection"], "start_inspection",
    ),
    "inspection_started": (
        "job_inspection_in_progress", "REQUIRES_MY_ACTION", "Inspecting",
        "Complete the inspection", ["complete_inspection"], "complete_inspection",
    ),
    "inspection_done": (
        "job_ready_to_start", "REQUIRES_MY_ACTION", "Inspection complete",
        "Start the service, or flag a quote if extra cost is needed",
        ["start_service", "quote_required"], "start_service",
    ),
    "service_started": (
        "job_in_progress", "REQUIRES_MY_ACTION", "Work in progress",
        "Mark work done or submit completion", ["work_done", "complete"], "complete",
    ),
    "work_done": (
        "job_completion_needed", "REQUIRES_MY_ACTION", "Ready to complete",
        "Submit the completion summary", ["complete"], "complete",
    ),
    "quote_required": (
        "job_awaiting_quote_decision", "WAITING_FOR_OTHERS", "Awaiting customer decision",
        "Waiting for the customer to approve the quote", [], None,
    ),
}

_TERMINAL_STATUSES = {"completed", "cancelled", "rejected", "closed"}

_PARTS_STATUS_MAP: dict[str, tuple[str, str, str, str, list[str]]] = {
    PARTS_STATUS_REQUESTED: (
        "WAITING_FOR_OTHERS", "Awaiting business approval",
        "Waiting for your business to approve this parts request", [],
    ),
    PARTS_STATUS_CUSTOMER_APPROVAL_PENDING: (
        "WAITING_FOR_OTHERS", "Awaiting customer approval",
        "Waiting for the customer to approve this parts request", [],
    ),
    PARTS_STATUS_BUSINESS_APPROVED: (
        "WAITING_FOR_OTHERS", "Approved — awaiting installation confirmation",
        "Install the part on-site; there is no technician-facing "
        "\"mark installed\" action yet, so ask your business/admin to confirm "
        "installation in the system", [],
    ),
    PARTS_STATUS_CUSTOMER_APPROVED: (
        "WAITING_FOR_OTHERS", "Approved — awaiting installation confirmation",
        "Install the part on-site; there is no technician-facing "
        "\"mark installed\" action yet, so ask your business/admin to confirm "
        "installation in the system", [],
    ),
    PARTS_STATUS_BUSINESS_REJECTED: (
        "FAILED", "Rejected by business",
        "This parts request was rejected — proceed without the part or "
        "submit a revised request", [],
    ),
    PARTS_STATUS_CUSTOMER_REJECTED: (
        "FAILED", "Rejected by customer",
        "This parts request was rejected by the customer — proceed without "
        "the part or submit a revised request", [],
    ),
}


def _job_priority(status: str, scheduled_date: date | None) -> str:
    if status == "assigned":
        return "urgent"
    if scheduled_date is not None and scheduled_date <= date.today() and status not in _TERMINAL_STATUSES:
        return "urgent"
    return "normal"


class TechnicianMyWorkService:
    """Derives My Work items for the technician role from ServiceJob + PartsRequest.

    Read-only. No new workflow-state table. See module docstring.
    """

    async def get_items(
        self,
        db: AsyncSession,
        staff_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> dict[str, Any]:
        job_items, unavailable = await self._job_items(db, staff_id, tenant_id)
        parts_items, parts_unavailable = await self._parts_items(db, staff_id, tenant_id)
        unavailable.extend(parts_unavailable)

        items = job_items + parts_items
        items.sort(key=lambda it: (it["priority"] != "urgent", it["created_at"]), reverse=False)

        return {
            "items": items,
            "count": len(items),
            "sources_unavailable": unavailable,
        }

    async def _job_items(
        self, db: AsyncSession, staff_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        try:
            from app.engines.final_records.models import ServiceJob
            res = await db.execute(
                select(ServiceJob).where(
                    ServiceJob.assigned_staff_id == staff_id,
                    ServiceJob.tenant_id == tenant_id,
                )
            )
            jobs = res.scalars().all()
        except Exception:
            return [], ["service_jobs"]

        items: list[dict[str, Any]] = []
        for job in jobs:
            template = _JOB_STATUS_MAP.get(job.status)
            if template is None:
                # Terminal or unrecognized status — not an actionable item.
                continue
            work_type, category, user_facing_status, recommended_action, available_actions, primary_action = template
            items.append({
                "id": f"job:{job.id}",
                "work_type": work_type,
                "domain": "booking",
                "category": category,
                "role": "technician",
                "priority": _job_priority(job.status, job.scheduled_date),
                "user_facing_title": f"Job {job.job_number}",
                "user_facing_description": recommended_action,
                "record_type": "ServiceJob",
                "record_id": str(job.id),
                "current_status": job.status,
                "user_facing_status": user_facing_status,
                "blocking_reason": None if category == "REQUIRES_MY_ACTION" else "Awaiting another party",
                "responsible_role": "technician" if category == "REQUIRES_MY_ACTION" else "customer",
                "assigned_user": str(staff_id),
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "due_at": job.scheduled_date.isoformat() if job.scheduled_date else None,
                "sla_state": "none",
                "time_remaining": None,
                "recommended_action": recommended_action,
                "available_actions": available_actions,
                "primary_action": primary_action,
                "destination_route": f"/staff/jobs/{job.id}",
                "required_permission": "staff_or_above",
                "tenant_id": str(tenant_id),
                "metadata": {"city": job.city, "zipcode": job.zipcode},
                "completed_at": None,
            })
        return items, []

    async def _parts_items(
        self, db: AsyncSession, staff_id: uuid.UUID, tenant_id: uuid.UUID,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        try:
            from app.engines.execution.models import PartsRequest
            res = await db.execute(
                select(PartsRequest).where(
                    PartsRequest.technician_id == staff_id,
                    PartsRequest.tenant_id == tenant_id,
                )
            )
            requests = res.scalars().all()
        except Exception:
            return [], ["parts_requests"]

        items: list[dict[str, Any]] = []
        for pr in requests:
            template = _PARTS_STATUS_MAP.get(pr.status)
            if template is None:
                if pr.status == PARTS_STATUS_INSTALLED:
                    continue  # resolved — not an active item
                continue
            category, user_facing_status, recommended_action, available_actions = template
            items.append({
                "id": f"parts:{pr.id}",
                "work_type": "parts_request",
                "domain": "booking",
                "category": category,
                "role": "technician",
                "priority": "normal",
                "user_facing_title": f"Parts request: {pr.part_name}",
                "user_facing_description": recommended_action,
                "record_type": "PartsRequest",
                "record_id": str(pr.id),
                "current_status": pr.status,
                "user_facing_status": user_facing_status,
                "blocking_reason": "Awaiting approval" if category == "WAITING_FOR_OTHERS" else None,
                "responsible_role": "tenant_owner" if category == "WAITING_FOR_OTHERS" else "technician",
                "assigned_user": str(staff_id),
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                "due_at": None,
                "sla_state": "none",
                "time_remaining": None,
                "recommended_action": recommended_action,
                "available_actions": available_actions,
                "primary_action": available_actions[0] if available_actions else None,
                "destination_route": f"/staff/jobs/{pr.job_id}",
                "required_permission": "staff_or_above",
                "tenant_id": str(tenant_id),
                "metadata": {
                    "part_name": pr.part_name,
                    "quantity": pr.quantity,
                    "estimated_cost": float(pr.estimated_cost),
                },
                "completed_at": None,
            })
        return items, []
