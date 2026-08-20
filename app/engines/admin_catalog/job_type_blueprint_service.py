"""Job-Type Blueprint service -- Job Type as a child record of a Master
Service (migration 160), plus its workflow ownership (inspection/quote-
approval/checklist/schedule/address/technician/service-area/availability
+ permitted pricing BEHAVIOR, never an amount).

Brand/Type dimension usage is intentionally NOT handled here -- it already
lives in the generic dimension engine (dimension_service.py,
service_job_dimensions). This file owns exactly the two things migration
160 added: master_service_job_types and service_job_workflow.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import (
    MasterServiceJobType, ServiceJobWorkflow, JobTypeDefinition, MasterService,
)
from app.engines.admin_catalog.job_type_service import RUNTIME_KNOWN_KEYS
from app.exceptions import ServiceOSException, NotFoundException


def _job_type_dict(jt: JobTypeDefinition) -> dict:
    """JobTypeDefinition has no to_dict() of its own -- JobTypeService owns
    that shape (including the honest runtime_supported flag). Mirrored here
    rather than instantiating a full JobTypeService for a read-only shape."""
    return {
        "id": str(jt.id), "key": jt.key, "label": jt.label, "description": jt.description,
        "requires_assessment": jt.requires_assessment, "allows_quote": jt.allows_quote,
        "requires_checklist": jt.requires_checklist, "is_active": jt.is_active,
        "display_order": jt.display_order,
        "runtime_supported": jt.key in RUNTIME_KNOWN_KEYS,
    }

PRICING_BEHAVIORS = {"fixed", "range", "inspection_required", "custom_quote"}

# Explicit allowlist -- structural workflow flags + behavior only, fails
# closed against any monetary key (admin-never-sets-price rule).
WORKFLOW_EDITABLE_FIELDS = {
    "inspection_required", "quote_approval_required", "checklist_required",
    "schedule_required", "address_required", "technician_required",
    "service_area_required", "availability_required", "pricing_behavior",
    # Cross-app step choreography (migration 274). Edited through the same
    # writer as everything else so a step change supersedes into a new version
    # exactly like a capability change does — a job that snapshotted an older
    # workflow keeps the step sequence it started with.
    "steps", "transitions",
}
# The two above are named for the API; these are the columns they land in.
_STEP_FIELD_COLUMNS = {"steps": "steps_json", "transitions": "transitions_json"}


class JobTypeBlueprintService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Job types as child records of a Master Service ─────────────────────
    async def list_job_types_for_service(self, master_service_id: uuid.UUID) -> list[dict]:
        rows = (await self.db.execute(
            select(MasterServiceJobType, JobTypeDefinition)
            .join(JobTypeDefinition, MasterServiceJobType.job_type_id == JobTypeDefinition.id)
            .where(
                MasterServiceJobType.master_service_id == master_service_id,
                MasterServiceJobType.is_active.is_(True),
                JobTypeDefinition.is_active.is_(True),
            )
            .order_by(MasterServiceJobType.display_order))).all()
        out = []
        for link, jt in rows:
            d = link.to_dict()
            d["job_type"] = _job_type_dict(jt)
            out.append(d)
        return out

    async def add_job_type_to_service(self, master_service_id: uuid.UUID, data: dict) -> dict:
        svc = (await self.db.execute(
            select(MasterService).where(MasterService.id == master_service_id))).scalar_one_or_none()
        if not svc:
            raise NotFoundException("MasterService", str(master_service_id))
        job_type_id = data.get("job_type_id")
        if not job_type_id:
            raise ServiceOSException("JOB_TYPE_ID_REQUIRED", "job_type_id is required.", status_code=422)
        job_type_id = uuid.UUID(str(job_type_id))
        jt = (await self.db.execute(
            select(JobTypeDefinition).where(JobTypeDefinition.id == job_type_id))).scalar_one_or_none()
        if not jt:
            raise NotFoundException("JobTypeDefinition", str(job_type_id))
        existing = (await self.db.execute(select(MasterServiceJobType).where(
            MasterServiceJobType.master_service_id == master_service_id,
            MasterServiceJobType.job_type_id == job_type_id))).scalar_one_or_none()
        if existing:
            raise ServiceOSException("JOB_TYPE_ALREADY_ADDED",
                "This job type is already added to this service.", status_code=409)
        link = MasterServiceJobType(
            master_service_id=master_service_id, job_type_id=job_type_id,
            display_order=int(data.get("display_order", 0)))
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        d = link.to_dict()
        d["job_type"] = _job_type_dict(jt)
        return d

    async def remove_job_type_from_service(self, link_id: uuid.UUID) -> dict:
        link = (await self.db.execute(
            select(MasterServiceJobType).where(MasterServiceJobType.id == link_id))).scalar_one_or_none()
        if not link:
            raise NotFoundException("MasterServiceJobType", str(link_id))
        if not link.is_active:
            return {"deactivated": True, "id": str(link_id)}
        from app.engines.admin_catalog.tenant_setup_revision import bump_tenant_setup_revision
        await bump_tenant_setup_revision(self.db, link.master_service_id, link.job_type_id)
        link.is_active = False
        from sqlalchemy import update
        from app.engines.admin_catalog.models import TenantService
        await self.db.execute(
            update(TenantService).where(
                TenantService.master_service_id == link.master_service_id,
                TenantService.job_type_id == link.job_type_id,
                TenantService.deleted_at.is_(None),
            ).values(is_enabled=False, setup_status="draft", last_active_step="services-pricing")
        )
        await self.db.commit()
        return {"deactivated": True, "id": str(link_id)}

    # ── Workflow ownership (structure/behavior only, no amounts) ───────────
    async def get_workflow(self, master_service_id: uuid.UUID, job_type_id: uuid.UUID) -> dict:
        row = (await self.db.execute(select(ServiceJobWorkflow).where(
            ServiceJobWorkflow.master_service_id == master_service_id,
            ServiceJobWorkflow.job_type_id == job_type_id,
            ServiceJobWorkflow.is_current.is_(True),
            ServiceJobWorkflow.status == "published",
        ))).scalar_one_or_none()
        if row:
            return row.to_dict()
        # No blueprint configured yet -- honest defaults, not a guess at
        # what this job type needs.
        return {
            "id": None, "master_service_id": str(master_service_id), "job_type_id": str(job_type_id),
            "inspection_required": False, "quote_approval_required": False, "checklist_required": False,
            "schedule_required": False, "address_required": False, "technician_required": False,
            "service_area_required": False, "availability_required": False, "pricing_behavior": "fixed",
        }

    async def _current_step_definition(self, master_service_id: uuid.UUID,
                                       job_type_id: uuid.UUID) -> tuple[list, list]:
        """The step definition currently published for this (service, job type)."""
        row = (await self.db.execute(select(ServiceJobWorkflow).where(
            ServiceJobWorkflow.master_service_id == master_service_id,
            ServiceJobWorkflow.job_type_id == job_type_id,
            ServiceJobWorkflow.is_current.is_(True),
        ))).scalar_one_or_none()
        if row is None:
            return [], []
        return list(row.steps_json or []), list(row.transitions_json or [])

    async def review_workflow_steps(self, master_service_id: uuid.UUID,
                                    job_type_id: uuid.UUID) -> dict:
        """Coherence review of the published step definition (non-fatal)."""
        from app.engines.admin_catalog.workflow_steps import check_definition
        steps, transitions = await self._current_step_definition(master_service_id, job_type_id)
        result = check_definition(steps, transitions)
        result["step_count"] = len(steps)
        result["transition_count"] = len(transitions)
        return result

    async def set_workflow(self, master_service_id: uuid.UUID, job_type_id: uuid.UUID, data: dict) -> dict:
        """HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2: this previously UPDATEd
        the same row in place -- a job that had snapshotted this row's id (or
        even just its live values) at booking time would see its own
        requirements change the moment an admin edited them later. Now
        append-only: an edit supersedes the current row and INSERTs a new
        version. The row's own id is what bookings/jobs snapshot, so history
        is preserved and in-progress jobs are unaffected by future edits."""
        unknown = set(data) - WORKFLOW_EDITABLE_FIELDS
        if unknown:
            raise ServiceOSException("INVALID_WORKFLOW_FIELDS",
                f"Unknown or disallowed fields: {sorted(unknown)}.", status_code=422)
        if "pricing_behavior" in data and data["pricing_behavior"] not in PRICING_BEHAVIORS:
            raise ServiceOSException("INVALID_PRICING_BEHAVIOR",
                f"pricing_behavior must be one of {sorted(PRICING_BEHAVIORS)}.", status_code=422)

        # Steps and transitions are validated together — a transition can only
        # be checked against the step list it refers to — then renamed to their
        # column names so the rest of this method treats them like any other field.
        if "steps" in data or "transitions" in data:
            from app.engines.admin_catalog.workflow_steps import validate_workflow_steps
            existing_steps, existing_transitions = await self._current_step_definition(
                master_service_id, job_type_id)
            try:
                clean_steps, clean_transitions = validate_workflow_steps(
                    data.get("steps", existing_steps),
                    data.get("transitions", existing_transitions),
                )
            except ValueError as exc:
                raise ServiceOSException("INVALID_WORKFLOW_STEPS", str(exc), status_code=422) from None
            data = {k: v for k, v in data.items() if k not in _STEP_FIELD_COLUMNS}
            data["steps_json"] = clean_steps
            data["transitions_json"] = clean_transitions

        current = (await self.db.execute(select(ServiceJobWorkflow).where(
            ServiceJobWorkflow.master_service_id == master_service_id,
            ServiceJobWorkflow.job_type_id == job_type_id,
            ServiceJobWorkflow.is_current.is_(True),
        ))).scalar_one_or_none()

        if current is None:
            row = ServiceJobWorkflow(
                master_service_id=master_service_id, job_type_id=job_type_id,
                version_number=1, is_current=True, **data,
            )
            self.db.add(row)
            from app.engines.admin_catalog.tenant_setup_revision import bump_tenant_setup_revision
            await bump_tenant_setup_revision(self.db, master_service_id, job_type_id)
            await self.db.commit()
            await self.db.refresh(row)
            return row.to_dict()

        merged = {
            "inspection_required": current.inspection_required,
            "quote_approval_required": current.quote_approval_required,
            "checklist_required": current.checklist_required,
            "schedule_required": current.schedule_required,
            "address_required": current.address_required,
            "technician_required": current.technician_required,
            "service_area_required": current.service_area_required,
            "availability_required": current.availability_required,
            "pricing_behavior": current.pricing_behavior,
            "steps_json": current.steps_json or [],
            "transitions_json": current.transitions_json or [],
            **data,
        }
        if all(getattr(current, field) == value for field, value in merged.items()):
            return current.to_dict()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        current.is_current = False
        current.superseded_at = now
        self.db.add(current)
        await self.db.flush()
        new_row = ServiceJobWorkflow(
            master_service_id=master_service_id, job_type_id=job_type_id,
            version_number=current.version_number + 1, is_current=True, **merged,
        )
        self.db.add(new_row)
        from app.engines.admin_catalog.tenant_setup_revision import bump_tenant_setup_revision
        await bump_tenant_setup_revision(self.db, master_service_id, job_type_id)
        await self.db.commit()
        await self.db.refresh(new_row)
        return new_row.to_dict()
