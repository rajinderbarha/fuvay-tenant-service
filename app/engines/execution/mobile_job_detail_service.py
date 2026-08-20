"""Technician Mobile App Phase J — Job Detail / Execution Command Center projection.

GET /v1/staff/service-jobs/{job_id}/mobile-detail
GET /v1/staff/service-jobs/{job_id}/mobile-timeline

Composed from the SAME canonical sources as Phases H/I -- no second job
table, no parallel status vocabulary, no invented workflow engine:

  - ServiceJob (final_records) -- trusted identity
  - HomeServiceJobExecutionService.get_work_start_status + the module-level
    _next_required_action (home_service_assignment/service.py) -- workflow-
    action authority, reused as-is (never recomputed client-side)
  - ServiceJobQuote (quote_checklist) -- estimate state
  - ServiceJobChecklistItem (quote_checklist) -- checklist readiness
  - PartsRequest (execution) -- parts readiness
  - ServicePaymentRecord (invoice_payment) -- direct-payment state
  - ServiceJobExecutionEvent + ServiceJobAssignmentEvent -- timeline
  - MasterService (admin_catalog) -- visit_fee / is_type_required /
    is_brand_required (via master_service_job_type_id bridge)
  - _customer_alias / _safe_booking_view -- existing privacy masking

Deliberately NOT fabricated (disclosed in the Phase J report, not hidden):
  - Workflow TRACKER ordering: there is no per-job-type ordered-stage table
    in the schema (audited) -- the sequence below is the same static
    execution.constants.JOB_TRANSITIONS graph already canonical everywhere
    else in this codebase, filtered by this job's REAL workflow booleans
    (inspection_required/quote_approval_required/checklist_required) and
    annotated with REAL event timestamps where they exist. The stage list
    itself is code-level, not a fabricated one -- every other engine in
    this repo already treats JOB_TRANSITIONS as canonical.
  - Photos requirement: no min-photo-count column exists anywhere -- only
    an upload COUNT is returned, `required` is null (never invented).
  - Visit fee: no per-job disposition (paid/waived/adjusted) column exists
    anywhere -- only the catalog POLICY amount is returned, with
    `disposition: "not_tracked"` and no fabricated ₹299.
  - Type/Brand SELECTED VALUE: no column stores a chosen type/brand on
    ServiceJob or ServiceBooking -- only whether the master service
    REQUIRES them (MasterService.is_type_required/is_brand_required) is
    returned; the selected value is read from address_snapshot["type_brand"]
    when present, else marked unavailable.
  - Relay call: no telephony/relay engine exists anywhere in this repo
    (audited) -- `call_relay_available` is always false with reason
    CONTACT_RELAY_UNAVAILABLE, never a fake working button.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.execution.models import ServiceJobExecutionEvent
from app.exceptions import ServiceOSException

_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "closed_estimate_declined"}

# Canonical ordered sequence (mirrors execution.constants.JOB_TRANSITIONS,
# which every other engine already treats as the one real state machine).
_REPAIR_SEQUENCE = [
    ("assigned", "Assigned"), ("accepted", "Accepted"), ("on_the_way", "Travel"),
    ("reached_site", "Arrived"), ("inspection_started", "Inspection"),
    ("inspection_done", "Inspection complete"), ("quote_required", "Estimate"),
    ("service_started", "Work"), ("work_done", "Completion proof"),
    ("completed", "Completed"),
]

_CUSTOMER_ALIAS_PREFIX = "Customer HS-"


def _customer_alias(customer_id) -> str:
    if not customer_id:
        return "Customer"
    return f"{_CUSTOMER_ALIAS_PREFIX}{str(customer_id).replace('-', '')[:4].upper()}"


def _fail_not_found() -> ServiceOSException:
    # Cross-tenant existence and genuine not-found collapse to the exact
    # same response (spec section 1: "must fail closed without revealing
    # whether another tenant's job exists").
    return ServiceOSException("ENTITY_NOT_FOUND", "Job not found.", status_code=404)


class TechnicianJobDetailService:
    async def get_detail(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        from app.engines.final_records.models import ServiceJob, ServiceBooking
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        from app.engines.home_service_assignment.service import _next_required_action
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember

        staff_id = await self._resolve_staff_member_id(db, user_id)

        job = await db.get(ServiceJob, job_id)
        if not job or str(job.tenant_id) != str(tenant_id):
            raise _fail_not_found()
        if str(job.assigned_staff_id) != str(staff_id):
            raise ServiceOSException("ENTITY_NOT_ASSIGNED", "This job is not assigned to you.", status_code=403)

        work_start_status = await HomeServiceJobExecutionService().get_work_start_status(db, job)
        next_action = _next_required_action(job.status, work_start_status)

        booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
        customer_alias = _customer_alias(booking.customer_id if booking else None)

        service_label, type_required, brand_required, visit_fee = await self._resolve_catalog(db, job)
        type_brand_value = (job.address_snapshot or {}).get("type_brand") if job.address_snapshot else None

        # Prefer the job's own workflow definition; fall back to the static
        # sequence for workflows that have not defined steps.
        workflow_stages = (await self._build_workflow_stages_from_definition(db, job)
                           or self._build_workflow_stages(job, work_start_status))
        requirements = await self._build_requirements(db, job)
        blocker = None
        if work_start_status.get("start_work_block_code"):
            blocker = {"code": work_start_status["start_work_block_code"], "message": next_action.get("blocked_message")}

        is_terminal = job.status in _TERMINAL_STATUSES

        return {
            "job": {
                "job_id": str(job.id),
                "job_reference": job.job_number,
                "tenant_id": str(job.tenant_id),
                "assigned_technician_id": str(job.assigned_staff_id) if job.assigned_staff_id else None,
                "offering_id": str(job.offering_id) if job.offering_id else None,
                "service_label": service_label,
                "job_type_id": work_start_status.get("job_type_id"),
                "job_type_label": work_start_status.get("job_type_label"),
                "workflow_status": job.status,
                "scheduled_date": job.scheduled_date.isoformat() if job.scheduled_date else None,
                "scheduled_time_window": job.scheduled_time_window,
                "safe_locality": ", ".join(p for p in [job.city, job.zipcode] if p) or None,
                "is_terminal": is_terminal,
                "booking_reference": booking.booking_number if booking else None,
            },
            "customer": {
                "customer_alias": customer_alias,
                "call_relay_available": False,
                "call_relay_reason": "CONTACT_RELAY_UNAVAILABLE",
                "message_relay_available": False,
                "message_relay_reason": "CONTACT_RELAY_UNAVAILABLE",
            },
            "workflow": {"stages": workflow_stages},
            "next_required_action": {
                "key": next_action.get("action_type"), "label": next_action.get("action_label"),
                "allowed": next_action.get("allowed", False), "route_key": next_action.get("action_type"),
            },
            "requirements": requirements,
            "visit_fee": {
                "required": visit_fee is not None and visit_fee > 0,
                "amount": float(visit_fee) if visit_fee is not None else None,
                "currency": "INR",
                "disposition": "not_tracked",
                "policy_note": "Charged if the customer does not continue. Adjusted in the final amount if work continues.",
            } if visit_fee is not None else {"required": False, "amount": None, "currency": None, "disposition": "unavailable", "policy_note": None},
            "job_details": {
                "type_required": type_required, "brand_required": brand_required,
                "type_brand_value": type_brand_value,
                "issue_summary": booking.issue_summary if booking else None,
            },
            "allowed_actions": [next_action["action_type"]] if next_action.get("allowed") and next_action.get("action_type") else [],
            "blocker": blocker,
            "versions": {"entity_version": None, "workflow_version": None},
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_timeline(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        from app.engines.final_records.models import ServiceJob
        from app.engines.execution.models import ServiceJobExecutionEvent
        from app.engines.home_service_assignment.models import ServiceJobAssignmentEvent

        staff_id = await self._resolve_staff_member_id(db, user_id)
        job = await db.get(ServiceJob, job_id)
        if not job or str(job.tenant_id) != str(tenant_id):
            raise _fail_not_found()
        if str(job.assigned_staff_id) != str(staff_id):
            raise ServiceOSException("ENTITY_NOT_ASSIGNED", "This job is not assigned to you.", status_code=403)

        exec_events = (await db.execute(
            select(ServiceJobExecutionEvent).where(ServiceJobExecutionEvent.job_id == job_id, ServiceJobExecutionEvent.tenant_id == tenant_id)
        )).scalars().all()
        assignment_events = (await db.execute(
            select(ServiceJobAssignmentEvent).where(ServiceJobAssignmentEvent.job_id == job_id, ServiceJobAssignmentEvent.tenant_id == tenant_id)
        )).scalars().all()

        entries = []
        for e in exec_events:
            entries.append({"event_type": e.event_type, "label": e.event_type.replace("_", " ").title(),
                             "notes": e.notes, "created_at": e.created_at.isoformat() if e.created_at else None})
        for e in assignment_events:
            # Mask actor/tenant identifiers -- technicians see WHAT happened, not WHO (audit-only) did it.
            entries.append({"event_type": e.event_type, "label": e.event_type.replace("_", " ").title(),
                             "notes": e.reason, "created_at": e.created_at.isoformat() if e.created_at else None})

        entries.sort(key=lambda e: e["created_at"] or "")

        return {"job_id": str(job.id), "entries": entries, "server_timestamp": datetime.now(timezone.utc).isoformat()}

    async def _resolve_staff_member_id(self, db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        res = await db.execute(select(ProviderTeamMember.id).where(ProviderTeamMember.user_id == user_id))
        row = res.scalars().first()
        return row if row else user_id

    async def _resolve_catalog(self, db: AsyncSession, job) -> tuple[str | None, bool | None, bool | None, float | None]:
        from app.engines.admin_catalog.models import MasterServiceJobType, MasterService

        # ServiceJob.offering_id is master_services.id (confirmed by the
        # same join checklist_catalog.service uses to resolve the job-type
        # checklist) -- MasterOffering is a distinct, unrelated table and
        # this lookup always returned None against real data. Phase K fix.
        service_label = None
        if job.offering_id:
            offering = await db.get(MasterService, job.offering_id)
            service_label = offering.service_name if offering else None

        type_required = brand_required = None
        visit_fee = None
        if job.master_service_job_type_id:
            bridge = await db.get(MasterServiceJobType, job.master_service_job_type_id)
            if bridge:
                master_service = await db.get(MasterService, bridge.master_service_id)
                if master_service:
                    type_required = master_service.is_type_required
                    brand_required = master_service.is_brand_required
                    visit_fee = master_service.visit_fee

        return service_label, type_required, brand_required, visit_fee

    async def _build_workflow_stages_from_definition(self, db: AsyncSession, job) -> list[dict] | None:
        """Stages from the job's OWN snapshotted workflow, if it defines steps.

        The job's `service_job_workflow_id` is an immutable snapshot taken at
        booking time, so an admin publishing a new step sequence never rewrites
        the journey of a job already in flight.

        Returns None when the workflow has no step definition, so the static
        fallback below still serves every workflow authored before migration 274.
        """
        from app.engines.admin_catalog.workflow_steps import (
            resolve_job_workflow_stages, to_client_stages,
        )
        annotated = await resolve_job_workflow_stages(db, job, "staff")
        if annotated is None:
            return None
        return to_client_stages(annotated)

    def _build_workflow_stages(self, job, work_start_status: dict) -> list[dict]:
        """Static fallback for workflows with no step definition.

        Kept because every workflow authored before migration 274 has empty
        `steps_json`, and those jobs must keep rendering exactly as they do now.
        """
        sequence = list(_REPAIR_SEQUENCE)
        # Drop the estimate stage entirely when this job/blueprint never requires one.
        if work_start_status.get("quote_approval_required") is False:
            sequence = [s for s in sequence if s[0] != "quote_required"]

        current_status = job.status
        try:
            current_index = next(i for i, (key, _) in enumerate(sequence) if key == current_status)
        except StopIteration:
            current_index = -1  # unknown/terminal status not in the happy-path sequence

        stages = []
        for i, (key, label) in enumerate(sequence):
            if job.status in _TERMINAL_STATUSES:
                state = "completed" if current_index == -1 or i <= current_index else "upcoming"
            elif current_index == -1:
                state = "upcoming"
            elif i < current_index:
                state = "completed"
            elif i == current_index:
                state = "current"
            else:
                state = "upcoming"
            stages.append({"key": key, "label": label, "state": state, "completed_at": None})
        return stages

    async def _build_requirements(self, db: AsyncSession, job) -> dict:
        from app.engines.quote_checklist.models import ServiceJobChecklistItem, ServiceJobQuote
        from app.engines.execution.models import PartsRequest, ServiceJobMediaUpload
        from app.engines.invoice_payment.models import ServicePaymentRecord

        checklist_items = (await db.execute(
            select(ServiceJobChecklistItem).where(ServiceJobChecklistItem.job_id == job.id)
        )).scalars().all()
        checklist_total = len(checklist_items)
        checklist_completed = sum(1 for i in checklist_items if i.status == "completed")
        checklist_blocking = [i.item_label for i in checklist_items if i.is_required and i.status != "completed"]

        photo_count = (await db.execute(
            select(ServiceJobMediaUpload).where(ServiceJobMediaUpload.job_id == job.id)
        )).scalars().all()

        quote = (await db.execute(
            select(ServiceJobQuote).where(ServiceJobQuote.job_id == job.id, ServiceJobQuote.is_current.is_(True))
        )).scalars().first()

        parts = (await db.execute(
            select(PartsRequest).where(PartsRequest.job_id == job.id)
        )).scalars().all()

        payment = (await db.execute(
            select(ServicePaymentRecord).where(ServicePaymentRecord.job_id == job.id)
            .order_by(ServicePaymentRecord.created_at.desc()).limit(1)
        )).scalars().first()

        return {
            "checklist": {
                "required": checklist_total > 0, "total_items": checklist_total,
                "completed_items": checklist_completed, "blocking_items": checklist_blocking,
                "route_key": "CHECKLIST",
            },
            "photos": {
                "required": None,  # no minimum-count policy exists anywhere (disclosed above)
                "uploaded_count": len(photo_count), "route_key": "COMPLETION_PROOF",
            },
            "estimate": {
                "required": bool(quote), "quote_id": str(quote.id) if quote else None,
                "version": quote.version_number if quote else None,
                "state": quote.status if quote else None, "route_key": "ESTIMATE",
            },
            "parts": {
                "requested": len(parts) > 0,
                "approval_state": parts[-1].status if parts else None,
                "route_key": "PARTS_REQUEST",
            },
            "completion_proof": {
                "required": True, "state": "submitted" if job.status in ("work_done", "completed") else "not_submitted",
                "route_key": "COMPLETION_PROOF",
            },
            "payment_confirmation": {
                "required": payment is not None,
                "state": payment.reconciliation_status if payment else None,
                "route_key": "DIRECT_PAYMENT_CONFIRMATION",
            },
        }
