"""Technician Mobile App Phase K — Inspection & Diagnosis read projection.

Read-only assembly for the mobile Inspection screen. All mutation
(save-response / complete-instance / complete-inspection workflow
transition) reuses the EXISTING, already-tested canonical endpoints:

  POST /v1/staff/service-jobs/checklist-instances/{id}/responses/{item_id}
  POST /v1/staff/service-jobs/checklist-instances/{id}/complete
  POST /v1/staff/service-jobs/{job_id}/complete-inspection

(checklist_catalog/execution_router.py + execution/home_service_router.py).
This module does not duplicate that write path -- it only resolves and
projects the exact per-job-type checklist definition + current responses +
readiness so the mobile client has one call to render the whole screen.

Checklist definition/instance resolution is the checklist_catalog engine's
own canonical resolver (`get_applicable_mappings` /
`_resolve_master_service_job_type_id`) -- never re-derived by job category.
There is no separate admin-curated "diagnosis/fault library" table in this
repository (confirmed by audit): a Diagnosis single/multi-select is just a
normal ChecklistItem inside a "Diagnosis" ChecklistSection, authored by the
same admin checklist tooling as any other section. Free-text technician
findings route through the existing `add_diagnosis_note` execution note,
not a new model.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException

_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "closed_estimate_declined"}
_INSPECTION_PHASE = "INSPECTION"


def _fail_not_found() -> ServiceOSException:
    return ServiceOSException("ENTITY_NOT_FOUND", "Job not found.", status_code=404)


class MobileInspectionService:
    async def get_detail(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        from app.engines.final_records.models import ServiceJob, ServiceBooking
        from app.engines.checklist_catalog import service as checklist_svc
        from app.engines.checklist_catalog import constants as c
        from app.engines.checklist_catalog.models import JobChecklistResponse

        staff_id = await self._resolve_staff_member_id(db, user_id)

        job = await db.get(ServiceJob, job_id)
        if not job or str(job.tenant_id) != str(tenant_id):
            raise _fail_not_found()
        if str(job.assigned_staff_id) not in (str(staff_id), str(user_id)):
            raise ServiceOSException("ENTITY_NOT_ASSIGNED", "This job is not assigned to you.", status_code=403)

        booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
        service_label = await self._resolve_service_label(db, job)
        customer_report = {
            "issue_label": booking.issue_summary if booking else None,
            "answers": (booking.issue_details or {}).get("answers", []) if booking and booking.issue_details else [],
            "notes": (booking.issue_details or {}).get("notes") if booking and booking.issue_details else None,
        }

        mappings = await checklist_svc.get_applicable_mappings(db, job, phase=_INSPECTION_PHASE)
        if not mappings:
            # No inspection checklist is mapped for this job type. That is a
            # configuration gap, not a reason the technician cannot finish
            # inspecting: `complete_inspection`'s own gate
            # (GATE_BEFORE_INSPECTION_COMPLETE) enforces REQUIRED mappings, and
            # with none it has nothing to enforce and lets the transition
            # through. Reporting `can_complete: False` here contradicted that
            # and left the job parked on `inspection_started` with no action
            # anywhere in the app that could move it.
            #
            # `definition_status` stays UNAVAILABLE so the screen still tells
            # the technician the checklist is missing rather than pretending
            # there was nothing to fill in.
            can_complete = job.status not in _TERMINAL_STATUSES
            return {
                "job": self._job_identity(job, service_label),
                "customer_report": customer_report,
                "instance": None,
                "sections": [],
                "readiness": {
                    "total_required": 0, "completed_required": 0,
                    "missing_item_ids": [], "missing_evidence_item_ids": [],
                    "can_complete": can_complete, "blockers": [],
                },
                "allowed_actions": ["complete_inspection"] if can_complete else [],
                "definition_status": "UNAVAILABLE",
            }

        # A job has exactly one primary inspection checklist in practice --
        # prefer the REQUIRED-usage mapping, otherwise the first applicable one.
        mapping = next((m for m in mappings if m.usage == c.USAGE_REQUIRED), mappings[0])
        instance = await checklist_svc.ensure_instance(db, job, mapping)
        items = await checklist_svc._instance_items(db, instance)
        responses = {
            r.checklist_item_id: r for r in (await db.execute(
                select(JobChecklistResponse).where(JobChecklistResponse.job_checklist_instance_id == instance.id)
            )).scalars().all()
        }

        sections = await self._build_sections(db, instance, items, responses)
        readiness = self._build_readiness(items, responses, instance)

        is_terminal = job.status in _TERMINAL_STATUSES
        allowed_actions: list[str] = []
        if not is_terminal and instance.state != c.INSTANCE_COMPLETED:
            allowed_actions.append("save_inspection_draft")
            if readiness["can_complete"]:
                allowed_actions.append("complete_inspection")

        return {
            "job": self._job_identity(job, service_label),
            "customer_report": customer_report,
            "instance": {
                "instance_id": str(instance.id),
                "state": instance.state,
                "started_at": instance.started_at.isoformat() if instance.started_at else None,
                "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
            },
            "sections": sections,
            "readiness": readiness,
            "allowed_actions": allowed_actions,
            "definition_status": "AVAILABLE",
        }

    def _job_identity(self, job, service_label: str | None) -> dict:
        return {
            "job_id": str(job.id),
            "job_reference": job.job_number,
            "service_label": service_label,
            "workflow_status": job.status,
            "is_terminal": job.status in _TERMINAL_STATUSES,
        }

    async def _resolve_service_label(self, db: AsyncSession, job) -> str | None:
        # ServiceJob.offering_id is the master_services.id FK -- this is the
        # same join checklist_catalog.service._resolve_master_service_job_type_id
        # uses to resolve the exact job-type-mapped checklist, so the label
        # shown here is guaranteed consistent with what actually resolved.
        from app.engines.admin_catalog.models import MasterService
        if not job.offering_id:
            return None
        offering = await db.get(MasterService, job.offering_id)
        return offering.service_name if offering else None

    async def _build_sections(self, db: AsyncSession, instance, items, responses) -> list[dict]:
        from app.engines.checklist_catalog.models import ChecklistSection

        section_ids = {i.checklist_section_id for i in items}
        section_rows = {}
        if section_ids:
            rows = (await db.execute(select(ChecklistSection).where(ChecklistSection.id.in_(section_ids)))).scalars().all()
            section_rows = {s.id: s for s in rows}

        by_section: dict = {}
        for item in items:
            by_section.setdefault(item.checklist_section_id, []).append(item)

        sections = []
        for section_id, section_items in by_section.items():
            section = section_rows.get(section_id)
            item_dicts = []
            for item in sorted(section_items, key=lambda i: i.display_order):
                resp = responses.get(item.id)
                idict = item.to_dict()
                idict["response"] = resp.to_dict() if resp else None
                item_dicts.append(idict)
            sections.append({
                "section_id": str(section_id),
                "title": section.title if section else "Checklist",
                "display_order": section.display_order if section else 0,
                "items": item_dicts,
            })
        sections.sort(key=lambda s: s["display_order"])
        return sections

    def _build_readiness(self, items, responses, instance) -> dict:
        from app.engines.checklist_catalog import constants as c

        total_required = 0
        completed_required = 0
        missing_item_ids: list[str] = []
        missing_evidence_item_ids: list[str] = []
        for item in items:
            if not item.is_required:
                continue
            total_required += 1
            resp = responses.get(item.id)
            answered = resp is not None and resp.response_value not in (None, {}, "")
            evidence_ok = True
            if item.evidence_required:
                evidence_ok = resp is not None and len(resp.evidence or []) >= max(item.min_evidence_count, 1)
                if not evidence_ok:
                    missing_evidence_item_ids.append(str(item.id))
            if answered and evidence_ok:
                completed_required += 1
            elif not answered:
                missing_item_ids.append(str(item.id))

        can_complete = (
            instance.state != c.INSTANCE_COMPLETED
            and total_required > 0
            and completed_required == total_required
            and not missing_evidence_item_ids
        ) if total_required > 0 else instance.state != c.INSTANCE_COMPLETED

        return {
            "total_required": total_required,
            "completed_required": completed_required,
            "missing_item_ids": missing_item_ids,
            "missing_evidence_item_ids": missing_evidence_item_ids,
            "can_complete": can_complete,
            "blockers": [],
        }

    async def _resolve_staff_member_id(self, db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        res = await db.execute(select(ProviderTeamMember.id).where(ProviderTeamMember.user_id == user_id))
        row = res.scalars().first()
        return row if row else user_id
