"""Admin Job Type management -- service layer.

CRUD over the job_types table (migration 151). Backs the approved Admin
Catalog page's "Add Job Type" action + job-type tab configuration.

IMPORTANT runtime-coupling note (surfaced honestly, not hidden): the
field-ops execution engine's transition graph
(app.engines.field_ops.constants) is still keyed off a fixed set of 9
job-type KEYS. Creating a job type with a brand-new key here makes it
selectable/configurable in the catalog, but at execution time an unknown key
falls back to the full repair transition graph (mandatory assessment). This
service therefore warns when a new key is outside the runtime-known set,
rather than silently implying full runtime support that doesn't exist yet.
NO monetary fields (structure/workflow only).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.admin_catalog.models import JobTypeDefinition, MasterService
from app.exceptions import ServiceOSException, NotFoundException

# Keys the field-ops runtime transition graph actually differentiates today
# (see app.engines.field_ops.constants.JOB_TYPES). A new key outside this set
# is allowed but flagged as runtime_supported=False.
RUNTIME_KNOWN_KEYS = {
    "repair", "service", "consultation", "installation", "uninstallation",
    "inspection", "maintenance", "cleaning", "custom",
}
EDITABLE_FIELDS = {"label", "description", "requires_assessment", "allows_quote",
                   "requires_checklist", "is_active", "display_order"}


class JobTypeService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None):
        self.db = db
        self.actor_id = actor_id

    async def list_job_types(self, include_inactive: bool = False) -> list[dict]:
        q = select(JobTypeDefinition).order_by(JobTypeDefinition.display_order)
        if not include_inactive:
            q = q.where(JobTypeDefinition.is_active == True)  # noqa: E712
        rows = (await self.db.execute(q)).scalars().all()
        return [self._to_dict(jt) for jt in rows]

    async def create_job_type(self, data: dict) -> dict:
        key = (data.get("key") or "").strip().lower()
        label = (data.get("label") or "").strip()
        if not key or not label:
            raise ServiceOSException("JOB_TYPE_KEY_LABEL_REQUIRED", "key and label are required.", status_code=422)
        existing = (await self.db.execute(
            select(JobTypeDefinition).where(JobTypeDefinition.key == key))).scalar_one_or_none()
        if existing:
            raise ServiceOSException("JOB_TYPE_KEY_EXISTS", f"A job type with key '{key}' already exists.", status_code=409)
        jt = JobTypeDefinition(
            key=key, label=label, description=data.get("description"),
            requires_assessment=bool(data.get("requires_assessment", True)),
            allows_quote=bool(data.get("allows_quote", True)),
            requires_checklist=bool(data.get("requires_checklist", False)),
            display_order=int(data.get("display_order", 0)),
        )
        self.db.add(jt)
        await self.db.commit()
        await self.db.refresh(jt)
        return self._to_dict(jt)

    async def update_job_type(self, job_type_id: uuid.UUID, data: dict) -> dict:
        jt = await self._load(job_type_id)
        for field in EDITABLE_FIELDS:
            if field in data and data[field] is not None:
                setattr(jt, field, data[field])
        await self.db.commit()
        await self.db.refresh(jt)
        return self._to_dict(jt)

    def _to_dict(self, jt: JobTypeDefinition) -> dict:
        return {
            "id": str(jt.id), "key": jt.key, "label": jt.label, "description": jt.description,
            "requires_assessment": jt.requires_assessment, "allows_quote": jt.allows_quote,
            "requires_checklist": jt.requires_checklist, "is_active": jt.is_active,
            "display_order": jt.display_order,
            # Honest runtime-support signal -- see module docstring.
            "runtime_supported": jt.key in RUNTIME_KNOWN_KEYS,
        }

    async def _load(self, job_type_id: uuid.UUID) -> JobTypeDefinition:
        jt = (await self.db.execute(
            select(JobTypeDefinition).where(JobTypeDefinition.id == job_type_id))).scalar_one_or_none()
        if not jt:
            raise NotFoundException("JobType", str(job_type_id))
        return jt
