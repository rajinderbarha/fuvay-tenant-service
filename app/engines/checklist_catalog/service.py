"""Checklist Catalog Engine — service layer.

Covers: template/version authoring (draft-only mutation, immutable publish),
job-type mapping CRUD, job checklist instance resolution/snapshotting,
response + evidence capture, and the runtime completion-gate check consumed
by the execution engine (see gate.py wrapper used by
app/engines/execution/home_service_service.py).

Backend is the sole authority throughout -- no route or frontend flag may
short-circuit any function here.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, text as _sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.checklist_catalog import constants as c
from app.engines.checklist_catalog.models import (
    ChecklistTemplate, ChecklistTemplateVersion, ChecklistSection, ChecklistItem,
    JobTypeChecklistMapping, JobChecklistInstance, JobChecklistResponse,
    TenantServiceChecklistItem,
)
from app.exceptions import ServiceOSException


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Template / version authoring ─────────────────────────────────────────

async def create_template(
    db: AsyncSession, *, name: str, code: str, description: str | None,
    purpose: str, owner_scope: str, tenant_id: uuid.UUID | None,
    created_by_user_id: uuid.UUID | None, icon_url: str | None = None,
) -> ChecklistTemplate:
    name = (name or "").strip()
    code = (code or "").strip().upper()
    if not name:
        raise ServiceOSException("CHECKLIST_NAME_REQUIRED", "Checklist name is required.", status_code=422)
    if not code or len(code) > 80 or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in code):
        raise ServiceOSException(
            "CHECKLIST_CODE_INVALID",
            "Code may contain only uppercase letters, numbers, underscores and hyphens.", status_code=422,
        )
    if purpose not in c.TEMPLATE_PURPOSES:
        raise ServiceOSException("CHECKLIST_PURPOSE_INVALID", "Unknown checklist purpose.", status_code=422)
    if owner_scope not in c.OWNER_SCOPES:
        raise ServiceOSException("CHECKLIST_OWNER_SCOPE_INVALID", "Unknown owner scope.", status_code=422)
    template = ChecklistTemplate(
        name=name, code=code, description=description, icon_url=icon_url, purpose=purpose,
        status=c.TEMPLATE_STATUS_ACTIVE, owner_scope=owner_scope, tenant_id=tenant_id,
        created_by_user_id=created_by_user_id,
    )
    db.add(template)
    await db.flush()
    # every new template starts life as an empty, unmapped DRAFT version --
    # creating a template must never automatically activate it globally.
    version = ChecklistTemplateVersion(
        checklist_template_id=template.id, version_number=1, status=c.VERSION_DRAFT,
    )
    db.add(version)
    await db.flush()
    return template


async def update_template_metadata(
    db: AsyncSession, template: ChecklistTemplate, fields: dict,
) -> ChecklistTemplate:
    """Metadata-only edit (name/description/icon_url) -- never content.
    Template content changes always go through a new draft version (see
    create_draft_version), this only touches the template's own row.
    `fields` uses key-presence (not None-ness) to distinguish "leave
    unchanged" from "clear to null", so icon_url can be explicitly removed."""
    if "name" in fields:
        name = (fields["name"] or "").strip()
        if not name:
            raise ServiceOSException("CHECKLIST_NAME_REQUIRED", "Checklist name is required.", status_code=422)
        template.name = name
    if "description" in fields:
        template.description = fields["description"]
    if "icon_url" in fields:
        template.icon_url = fields["icon_url"]
    await db.flush()
    return template


async def _latest_version(db: AsyncSession, template_id: uuid.UUID) -> ChecklistTemplateVersion | None:
    res = await db.execute(
        select(ChecklistTemplateVersion)
        .where(ChecklistTemplateVersion.checklist_template_id == template_id)
        .order_by(ChecklistTemplateVersion.version_number.desc())
    )
    return res.scalars().first()


async def get_draft_version(db: AsyncSession, template_id: uuid.UUID) -> ChecklistTemplateVersion:
    """Returns the current editable DRAFT, creating one (via clone of the
    latest PUBLISHED version's content) if the latest version is PUBLISHED
    or ARCHIVED. Editing published content must never mutate that row."""
    latest = await _latest_version(db, template_id)
    if latest is None:
        raise ServiceOSException("CHECKLIST_CONFIGURATION_UNRESOLVED", "Template has no versions.", status_code=409)
    if latest.status == c.VERSION_DRAFT:
        return latest
    return await create_draft_version(db, template_id, source_version=latest)


async def create_draft_version(
    db: AsyncSession, template_id: uuid.UUID, source_version: ChecklistTemplateVersion | None = None,
) -> ChecklistTemplateVersion:
    if source_version is None:
        source_version = await _latest_version(db, template_id)
    next_number = (source_version.version_number + 1) if source_version else 1
    new_version = ChecklistTemplateVersion(
        checklist_template_id=template_id, version_number=next_number, status=c.VERSION_DRAFT,
    )
    db.add(new_version)
    await db.flush()

    if source_version is not None:
        sections = (await db.execute(
            select(ChecklistSection)
            .where(ChecklistSection.checklist_template_version_id == source_version.id)
            .order_by(ChecklistSection.display_order)
        )).scalars().all()
        for sec in sections:
            new_sec = ChecklistSection(
                checklist_template_version_id=new_version.id,
                title=sec.title, display_order=sec.display_order,
            )
            db.add(new_sec)
            await db.flush()
            items = (await db.execute(
                select(ChecklistItem)
                .where(ChecklistItem.checklist_section_id == sec.id)
                .order_by(ChecklistItem.display_order)
            )).scalars().all()
            for it in items:
                db.add(ChecklistItem(
                    checklist_section_id=new_sec.id, item_type=it.item_type, label=it.label,
                    help_text=it.help_text, is_required=it.is_required,
                    evidence_required=it.evidence_required, min_evidence_count=it.min_evidence_count,
                    max_evidence_count=it.max_evidence_count, allowed_file_types=it.allowed_file_types,
                    measurement_unit=it.measurement_unit, select_options=it.select_options,
                    validation_rules=it.validation_rules, display_order=it.display_order,
                    condition_rules=it.condition_rules, failure_behavior=it.failure_behavior,
                    customer_visible=it.customer_visible,
                ))
    await db.flush()
    return new_version


def _assert_version_editable(version: ChecklistTemplateVersion) -> None:
    if version.status != c.VERSION_DRAFT:
        raise ServiceOSException(
            "CHECKLIST_VERSION_NOT_EDITABLE",
            "Only a DRAFT version's content can be edited.", status_code=409,
        )


async def add_section(db: AsyncSession, version: ChecklistTemplateVersion, title: str, display_order: int = 0) -> ChecklistSection:
    _assert_version_editable(version)
    section = ChecklistSection(checklist_template_version_id=version.id, title=title, display_order=display_order)
    db.add(section)
    await db.flush()
    return section


async def add_item(db: AsyncSession, section: ChecklistSection, version: ChecklistTemplateVersion, **fields: Any) -> ChecklistItem:
    _assert_version_editable(version)
    if fields.get("item_type") not in c.ITEM_TYPES:
        raise ServiceOSException("CHECKLIST_ITEM_TYPE_INVALID", "Unknown checklist item type.", status_code=422)
    if fields.get("evidence_required") and fields["item_type"] not in c.EVIDENCE_CAPABLE_ITEM_TYPES:
        raise ServiceOSException(
            "CHECKLIST_ITEM_VALIDATION_FAILED",
            "Evidence can only be required for photo/document/signature items.", status_code=422,
        )
    item = ChecklistItem(checklist_section_id=section.id, **fields)
    db.add(item)
    await db.flush()
    return item


async def _version_readiness(db: AsyncSession, version: ChecklistTemplateVersion) -> dict:
    section_count, item_count = map(int, (await db.execute(
        select(func.count(func.distinct(ChecklistSection.id)), func.count(ChecklistItem.id))
        .select_from(ChecklistSection)
        .outerjoin(ChecklistItem, ChecklistItem.checklist_section_id == ChecklistSection.id)
        .where(ChecklistSection.checklist_template_version_id == version.id)
    )).one())
    return {"section_count": section_count, "item_count": item_count, "ready": item_count > 0}


async def publish_version(
    db: AsyncSession, version: ChecklistTemplateVersion, *, published_by: uuid.UUID | None,
    change_summary: str | None = None,
) -> ChecklistTemplateVersion:
    _assert_version_editable(version)
    readiness = await _version_readiness(db, version)
    if not readiness["ready"]:
        raise ServiceOSException(
            "CHECKLIST_CONFIGURATION_UNRESOLVED",
            "A version must contain at least one item before it can be published.", status_code=422,
        )
    version.status = c.VERSION_PUBLISHED
    version.published_by = published_by
    version.published_at = _now()
    version.change_summary = change_summary
    db.add(version)
    await db.flush()
    return version


async def archive_template(
    db: AsyncSession, template: ChecklistTemplate, *, archived_by: uuid.UUID | None,
    reason: str,
) -> ChecklistTemplate:
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise ServiceOSException(
            "CHECKLIST_RETIRE_REASON_REQUIRED",
            "A retirement reason of at least 5 characters is required.", status_code=422,
        )
    template.status = c.TEMPLATE_STATUS_ARCHIVED
    template.archived_at = _now()
    template.archived_by = archived_by
    template.archive_reason = reason
    db.add(template)
    version_ids = select(ChecklistTemplateVersion.id).where(
        ChecklistTemplateVersion.checklist_template_id == template.id
    )
    mappings = (await db.execute(
        select(JobTypeChecklistMapping).where(
            JobTypeChecklistMapping.checklist_template_version_id.in_(version_ids),
            JobTypeChecklistMapping.status == c.MAPPING_STATUS_ACTIVE,
        )
    )).scalars().all()
    for mapping in mappings:
        mapping.status = c.MAPPING_STATUS_DISABLED
        mapping.updated_by = archived_by
        mapping.disabled_at = _now()
        mapping.disable_reason = f"Template retired: {reason}"
        db.add(mapping)
    await db.flush()
    return template


async def restore_template(
    db: AsyncSession, template: ChecklistTemplate, *, restored_by: uuid.UUID | None,
    reason: str,
) -> ChecklistTemplate:
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise ServiceOSException(
            "CHECKLIST_RESTORE_REASON_REQUIRED",
            "A restoration reason of at least 5 characters is required.", status_code=422,
        )
    template.status = c.TEMPLATE_STATUS_ACTIVE
    template.archived_at = None
    template.archived_by = None
    template.archive_reason = None
    db.add(template)
    await db.flush()
    return template


# ── Job-Type mapping ─────────────────────────────────────────────────────

async def create_mapping(
    db: AsyncSession, *, master_service_job_type_id: uuid.UUID, service_job_workflow_id: uuid.UUID | None,
    checklist_template_version_id: uuid.UUID, phase: str, usage: str, actor: str,
    completion_gate: str, condition_rules: dict | None, display_order: int,
    created_by: uuid.UUID | None,
) -> JobTypeChecklistMapping:
    from app.engines.admin_catalog.models import MasterServiceJobType

    link = await db.get(MasterServiceJobType, master_service_job_type_id)
    if link is None or not link.is_active:
        raise ServiceOSException(
            "CHECKLIST_CONFIGURATION_UNRESOLVED",
            "Mapping must reference an exact, active Job Type.", status_code=422,
        )
    version = await db.get(ChecklistTemplateVersion, checklist_template_version_id)
    if version is None or version.status != c.VERSION_PUBLISHED:
        raise ServiceOSException(
            c.ERR_CHECKLIST_VERSION_NOT_PUBLISHED,
            "Only a published template version may be mapped to a Job Type.", status_code=422,
        )
    template = await db.get(ChecklistTemplate, version.checklist_template_id)
    if usage not in c.USAGES:
        raise ServiceOSException("CHECKLIST_USAGE_INVALID", "Unknown usage value.", status_code=422)
    if actor not in c.ACTORS:
        raise ServiceOSException("CHECKLIST_ACTOR_INVALID", "Unknown actor value.", status_code=422)
    if completion_gate not in c.COMPLETION_GATES:
        raise ServiceOSException("CHECKLIST_GATE_INVALID", "Unknown completion gate.", status_code=422)
    allowed_gates = c.PURPOSE_ALLOWED_GATES.get(template.purpose, {c.GATE_NONE})
    if completion_gate not in allowed_gates:
        raise ServiceOSException(
            "CHECKLIST_GATE_PURPOSE_MISMATCH",
            f"A {template.purpose} checklist cannot be configured with gate {completion_gate}.",
            status_code=422,
        )
    if service_job_workflow_id is not None:
        from app.engines.admin_catalog.models import ServiceJobWorkflow
        workflow = await db.get(ServiceJobWorkflow, service_job_workflow_id)
        if workflow is None or workflow.master_service_id != link.master_service_id or workflow.job_type_id != link.job_type_id:
            raise ServiceOSException(
                "CHECKLIST_CONFIGURATION_UNRESOLVED",
                "Workflow pin must belong to the same exact Master Service and Job Type.", status_code=422,
            )

    duplicate = (await db.execute(
        select(JobTypeChecklistMapping.id).where(
            JobTypeChecklistMapping.master_service_job_type_id == master_service_job_type_id,
            JobTypeChecklistMapping.checklist_template_version_id == checklist_template_version_id,
            JobTypeChecklistMapping.phase == phase,
        )
    )).scalar_one_or_none()
    # AsyncMock-based unit fixtures may return an awaitable placeholder here;
    # a real database scalar is either UUID or None. Close that placeholder so
    # test diagnostics stay warning-free without weakening production checks.
    if hasattr(duplicate, "close") and not isinstance(duplicate, uuid.UUID):
        duplicate.close()
        duplicate = None
    if duplicate is not None:
        raise ServiceOSException(
            "CHECKLIST_MAPPING_ALREADY_EXISTS",
            "This checklist version is already mapped to that Job Type and phase.", status_code=409,
        )

    mapping = JobTypeChecklistMapping(
        master_service_job_type_id=master_service_job_type_id,
        service_job_workflow_id=service_job_workflow_id,
        checklist_template_version_id=checklist_template_version_id,
        phase=phase, usage=usage, actor=actor, completion_gate=completion_gate,
        condition_rules=condition_rules, display_order=display_order,
        status=c.MAPPING_STATUS_ACTIVE, created_by=created_by, updated_by=created_by,
    )
    db.add(mapping)
    await db.flush()
    return mapping


async def disable_mapping(
    db: AsyncSession, mapping: JobTypeChecklistMapping, updated_by: uuid.UUID | None,
    reason: str,
) -> JobTypeChecklistMapping:
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise ServiceOSException(
            "CHECKLIST_MAPPING_DISABLE_REASON_REQUIRED",
            "A disable reason of at least 5 characters is required.", status_code=422,
        )
    mapping.status = c.MAPPING_STATUS_DISABLED
    mapping.updated_by = updated_by
    mapping.disabled_at = _now()
    mapping.disable_reason = reason
    db.add(mapping)
    await db.flush()
    return mapping


async def enable_mapping(
    db: AsyncSession, mapping: JobTypeChecklistMapping, updated_by: uuid.UUID | None,
) -> JobTypeChecklistMapping:
    version = await db.get(ChecklistTemplateVersion, mapping.checklist_template_version_id)
    template = await db.get(ChecklistTemplate, version.checklist_template_id) if version else None
    if version is None or version.status != c.VERSION_PUBLISHED or template is None or template.status != c.TEMPLATE_STATUS_ACTIVE:
        raise ServiceOSException(
            "CHECKLIST_CONFIGURATION_UNRESOLVED",
            "Only a published version of an active template can be enabled.", status_code=409,
        )
    mapping.status = c.MAPPING_STATUS_ACTIVE
    mapping.updated_by = updated_by
    mapping.disabled_at = None
    mapping.disable_reason = None
    db.add(mapping)
    await db.flush()
    return mapping


# ── Conditional rule evaluation (validated declarative structure only) ──

def evaluate_condition(rules: dict | None, context: dict[str, Any]) -> bool:
    """Evaluates a trusted declarative rule tree against job context. Never
    executes arbitrary frontend expressions server-side."""
    if not rules:
        return True

    def _eval_clause(clause: dict) -> bool:
        field, op, value = clause.get("field"), clause.get("op"), clause.get("value")
        actual = context.get(field)
        if op == "eq":
            return actual == value
        if op == "neq":
            return actual != value
        if op == "in":
            return actual in (value or [])
        return False

    if "all" in rules:
        return all(_eval_clause(cl) for cl in rules["all"])
    if "any" in rules:
        return any(_eval_clause(cl) for cl in rules["any"])
    return True


# ── Job-type resolution (reuses the canonical resolver, does not duplicate) ─

async def _resolve_master_service_job_type_id(db: AsyncSession, job) -> uuid.UUID | None:
    from app.engines.admin_catalog.models import MasterServiceJobType
    offering_id = getattr(job, "offering_id", None)
    job_type_id = getattr(job, "job_type_id", None)
    if offering_id is None or job_type_id is None:
        return None
    link = (await db.execute(
        select(MasterServiceJobType).where(
            MasterServiceJobType.master_service_id == offering_id,
            MasterServiceJobType.job_type_id == job_type_id,
            MasterServiceJobType.is_active.is_(True),
        )
    )).scalars().first()
    return link.id if link else None


async def get_applicable_mappings(
    db: AsyncSession, job, phase: str | None = None, context: dict[str, Any] | None = None,
) -> list[JobTypeChecklistMapping]:
    msjt_id = await _resolve_master_service_job_type_id(db, job)
    if msjt_id is None:
        return []
    stmt = select(JobTypeChecklistMapping).where(
        JobTypeChecklistMapping.master_service_job_type_id == msjt_id,
        JobTypeChecklistMapping.status == c.MAPPING_STATUS_ACTIVE,
        JobTypeChecklistMapping.usage != c.USAGE_DISABLED,
    )
    if phase is not None:
        stmt = stmt.where(JobTypeChecklistMapping.phase == phase)
    mappings = (await db.execute(stmt.order_by(JobTypeChecklistMapping.display_order))).scalars().all()
    now = _now()
    context = context or {}
    result = []
    for m in mappings:
        if m.effective_from and m.effective_from > now:
            continue
        if m.effective_until and m.effective_until < now:
            continue
        if not evaluate_condition(m.condition_rules, context):
            continue
        result.append(m)
    return result


# ── Job checklist instances ──────────────────────────────────────────────

async def ensure_instance(db: AsyncSession, job, mapping: JobTypeChecklistMapping) -> JobChecklistInstance:
    existing = (await db.execute(
        select(JobChecklistInstance).where(
            JobChecklistInstance.job_id == job.id, JobChecklistInstance.mapping_id == mapping.id,
        )
    )).scalars().first()
    if existing:
        return existing
    version = await db.get(ChecklistTemplateVersion, mapping.checklist_template_version_id)
    if version is None or version.status not in (c.VERSION_PUBLISHED, c.VERSION_ARCHIVED):
        raise ServiceOSException(
            c.ERR_CHECKLIST_VERSION_NOT_PUBLISHED,
            "Mapped checklist version is not published.", status_code=409,
        )
    instance = JobChecklistInstance(
        job_id=job.id, tenant_id=job.tenant_id, mapping_id=mapping.id,
        checklist_template_version_id=mapping.checklist_template_version_id,
        phase=mapping.phase, assigned_actor=mapping.actor, state=c.INSTANCE_NOT_STARTED,
        snapshot_metadata={"mapping_usage": mapping.usage, "completion_gate": mapping.completion_gate},
    )
    db.add(instance)
    await db.flush()
    return instance


async def _instance_items(db: AsyncSession, instance: JobChecklistInstance) -> list[ChecklistItem]:
    """The authored items for this instance, narrowed to the points the TENANT
    actually selected for the service.

    Falls back to the full authored list when the tenant has made no selection
    for that service. That is deliberate: silently returning an EMPTY checklist
    for a provider who has not chosen yet would quietly drop a safety/quality
    step the admin authored, which is far worse than showing them all of it.
    The tenant portal's readiness check (`tenant_selection_readiness`) is what
    surfaces the "select at least 5" obligation.
    """
    sections = (await db.execute(
        select(ChecklistSection)
        .where(ChecklistSection.checklist_template_version_id == instance.checklist_template_version_id)
        .order_by(ChecklistSection.display_order)
    )).scalars().all()
    items: list[ChecklistItem] = []
    for sec in sections:
        items.extend((await db.execute(
            select(ChecklistItem).where(ChecklistItem.checklist_section_id == sec.id).order_by(ChecklistItem.display_order)
        )).scalars().all())

    selected_ids = await _tenant_selected_item_ids_for_job(db, instance)
    if not selected_ids:
        return items
    narrowed = [i for i in items if i.id in selected_ids]
    # If the selection somehow matches nothing in this version (e.g. the admin
    # published a new version with entirely new items), keep the authored list
    # rather than handing the technician an empty checklist.
    return narrowed or items


async def _tenant_selected_item_ids_for_job(
    db: AsyncSession, instance: JobChecklistInstance,
) -> set[uuid.UUID]:
    """Active selection for the (tenant, service) this job belongs to.

    Resolved from the job rather than passed in, so every existing caller of
    `_instance_items` gets the narrowing without a signature change.
    """
    row = (await db.execute(_sa_text(
        "SELECT tenant_id, offering_id FROM service_jobs WHERE id=:jid"
    ), {"jid": str(instance.job_id)})).fetchone()
    if not row:
        return set()
    tenant_id, offering_id = row._mapping["tenant_id"], row._mapping["offering_id"]
    if not (tenant_id and offering_id):
        return set()
    rows = (await db.execute(_sa_text(
        "SELECT checklist_item_id FROM tenant_service_checklist_items "
        "WHERE tenant_id=:tid AND master_service_id=:sid AND is_active=true"
    ), {"tid": str(tenant_id), "sid": str(offering_id)})).fetchall()
    return {r._mapping["checklist_item_id"] for r in rows}


async def save_response(
    db: AsyncSession, instance: JobChecklistInstance, item_id: uuid.UUID, *,
    actor_user_id: uuid.UUID | None, actor_role: str, response_value: dict | None,
    evidence: list[dict] | None,
) -> JobChecklistResponse:
    if instance.assigned_actor not in (actor_role, "STAFF") and instance.assigned_actor != actor_role:
        raise ServiceOSException(
            c.ERR_CHECKLIST_ACTOR_NOT_AUTHORIZED,
            "This checklist is not assigned to your role.", status_code=403,
        )
    item = await db.get(ChecklistItem, item_id)
    if item is None:
        raise ServiceOSException("CHECKLIST_ITEM_NOT_FOUND", "Checklist item not found.", status_code=404)

    if item.evidence_required and len(evidence or []) < max(item.min_evidence_count, 1):
        raise ServiceOSException(
            c.ERR_CHECKLIST_EVIDENCE_REQUIRED,
            "This item requires evidence before it can be saved.", status_code=422,
        )
    if item.max_evidence_count and evidence and len(evidence) > item.max_evidence_count:
        raise ServiceOSException(
            c.ERR_CHECKLIST_ITEM_VALIDATION_FAILED,
            "Too many evidence files attached for this item.", status_code=422,
        )

    existing = (await db.execute(
        select(JobChecklistResponse).where(
            JobChecklistResponse.job_checklist_instance_id == instance.id,
            JobChecklistResponse.checklist_item_id == item_id,
        )
    )).scalars().first()
    now = _now()
    if existing:
        existing.response_value = response_value
        existing.evidence = evidence
        existing.actor_user_id = actor_user_id
        existing.last_updated_at = now
        db.add(existing)
        response = existing
    else:
        response = JobChecklistResponse(
            job_checklist_instance_id=instance.id, checklist_item_id=item_id,
            response_value=response_value, actor_user_id=actor_user_id,
            submitted_at=now, last_updated_at=now, evidence=evidence,
        )
        db.add(response)

    if instance.state == c.INSTANCE_NOT_STARTED:
        instance.state = c.INSTANCE_IN_PROGRESS
        instance.started_at = now
        db.add(instance)
    await db.flush()
    return response


async def complete_instance(db: AsyncSession, instance: JobChecklistInstance, completed_by: uuid.UUID | None) -> JobChecklistInstance:
    items = await _instance_items(db, instance)
    responses = {
        r.checklist_item_id: r for r in (await db.execute(
            select(JobChecklistResponse).where(JobChecklistResponse.job_checklist_instance_id == instance.id)
        )).scalars().all()
    }
    for item in items:
        if not item.is_required:
            continue
        resp = responses.get(item.id)
        if resp is None or resp.response_value in (None, {}, ""):
            raise ServiceOSException(
                c.ERR_CHECKLIST_ITEM_VALIDATION_FAILED,
                f"Required item '{item.label}' is not complete.", status_code=422,
            )
        if item.evidence_required and len(resp.evidence or []) < max(item.min_evidence_count, 1):
            raise ServiceOSException(
                c.ERR_CHECKLIST_EVIDENCE_REQUIRED,
                f"Required item '{item.label}' is missing evidence.", status_code=422,
            )
    instance.state = c.INSTANCE_COMPLETED
    instance.completed_at = _now()
    instance.completed_by = completed_by
    db.add(instance)
    await db.flush()
    return instance


async def waive_instance(
    db: AsyncSession, instance: JobChecklistInstance, *, waived_by: uuid.UUID, reason: str, authorized: bool,
) -> JobChecklistInstance:
    if not authorized:
        raise ServiceOSException(
            c.ERR_CHECKLIST_ACTOR_NOT_AUTHORIZED,
            "Waiving a required checklist requires an authorised override.", status_code=403,
        )
    if not reason or not reason.strip():
        raise ServiceOSException("CHECKLIST_WAIVER_REASON_REQUIRED", "A waiver reason is required.", status_code=422)
    instance.state = c.INSTANCE_WAIVED
    instance.waived_by = waived_by
    instance.waived_at = _now()
    instance.waiver_reason = reason.strip()
    db.add(instance)
    await db.flush()
    return instance


# ══════════════════════════════════════════════════════════════════════════
# Tenant selection of checklist points per service
#
# Division of responsibility (product rule):
#   ADMIN  authors the library -- templates, versions, sections, items.
#   TENANT chooses which of those points its technicians must complete for a
#          given service, at least MIN_TENANT_CHECKLIST_ITEMS_PER_SERVICE.
#
# A tenant can only ever choose from what the admin authored AND mapped to
# that service's job types: `selectable_items_for_service` is the single
# source of what is offerable, and `set_tenant_selection` validates every
# submitted id against it. A tenant cannot invent a checklist point, nor
# select one belonging to a different service.
# ══════════════════════════════════════════════════════════════════════════

async def selectable_items_for_service(
    db: AsyncSession, master_service_id: uuid.UUID,
) -> list[dict]:
    """Every authored checklist point a tenant may choose for this service.

    Walks the real chain the runtime already uses:
      master_service -> master_service_job_types -> active job-type mappings
      -> PUBLISHED template version -> sections -> items

    Only PUBLISHED versions are offerable: letting a tenant select from a
    DRAFT would let an admin's unfinished edit change what technicians are
    asked to do in the field.
    """
    job_type_ids = [r[0] for r in (await db.execute(_sa_text(
        "SELECT id FROM master_service_job_types WHERE master_service_id=:sid"
    ), {"sid": str(master_service_id)})).fetchall()]
    if not job_type_ids:
        return []

    mappings = (await db.execute(
        select(JobTypeChecklistMapping).where(
            JobTypeChecklistMapping.master_service_job_type_id.in_(job_type_ids),
            JobTypeChecklistMapping.status == "active",
        ).order_by(JobTypeChecklistMapping.display_order)
    )).scalars().all()
    if not mappings:
        return []

    out: list[dict] = []
    seen: set[uuid.UUID] = set()
    for mapping in mappings:
        version = await db.get(ChecklistTemplateVersion, mapping.checklist_template_version_id)
        if not version or version.status != c.VERSION_PUBLISHED:
            continue
        template = await db.get(ChecklistTemplate, version.checklist_template_id)
        sections = (await db.execute(
            select(ChecklistSection)
            .where(ChecklistSection.checklist_template_version_id == version.id)
            .order_by(ChecklistSection.display_order)
        )).scalars().all()
        for sec in sections:
            items = (await db.execute(
                select(ChecklistItem)
                .where(ChecklistItem.checklist_section_id == sec.id)
                .order_by(ChecklistItem.display_order)
            )).scalars().all()
            for item in items:
                if item.id in seen:
                    continue
                seen.add(item.id)
                out.append({
                    **item.to_dict(),
                    "section_title": sec.title,
                    "template_name": template.name if template else None,
                    "template_purpose": template.purpose if template else None,
                    "phase": mapping.phase,
                    "checklist_template_version_id": str(version.id),
                })
    return out


async def get_tenant_selection(
    db: AsyncSession, tenant_id: uuid.UUID, master_service_id: uuid.UUID,
) -> list[TenantServiceChecklistItem]:
    return list((await db.execute(
        select(TenantServiceChecklistItem).where(
            TenantServiceChecklistItem.tenant_id == tenant_id,
            TenantServiceChecklistItem.master_service_id == master_service_id,
            TenantServiceChecklistItem.is_active.is_(True),
        )
    )).scalars().all())


async def set_tenant_selection(
    db: AsyncSession, tenant_id: uuid.UUID, master_service_id: uuid.UUID,
    item_ids: list[uuid.UUID], *, selected_by_user_id: uuid.UUID | None,
) -> dict:
    """Replace this tenant's selected points for this service.

    Enforces both halves of the product rule:
      - at least MIN_TENANT_CHECKLIST_ITEMS_PER_SERVICE points (a 422 carrying
        the shortfall, so the portal can say exactly how many more are needed);
      - every id is genuinely selectable for THIS service.

    Deselection deactivates rather than deletes, and re-selecting a previously
    deactivated point reactivates the same row -- so a tenant changing their
    mind can never violate the unique constraint.
    """
    unique_ids = list(dict.fromkeys(item_ids))   # de-dupe, preserve order
    if len(unique_ids) < c.MIN_TENANT_CHECKLIST_ITEMS_PER_SERVICE:
        raise ServiceOSException(
            c.ERR_CHECKLIST_SELECTION_TOO_SMALL,
            f"Select at least {c.MIN_TENANT_CHECKLIST_ITEMS_PER_SERVICE} checklist points "
            f"for this service ({len(unique_ids)} selected).",
            status_code=422,
        )

    selectable = await selectable_items_for_service(db, master_service_id)
    version_by_item = {uuid.UUID(i["id"]): i["checklist_template_version_id"] for i in selectable}
    invalid = [str(i) for i in unique_ids if i not in version_by_item]
    if invalid:
        raise ServiceOSException(
            c.ERR_CHECKLIST_ITEM_NOT_SELECTABLE,
            "One or more checklist points are not available for this service.",
            status_code=422,
        )

    existing = list((await db.execute(
        select(TenantServiceChecklistItem).where(
            TenantServiceChecklistItem.tenant_id == tenant_id,
            TenantServiceChecklistItem.master_service_id == master_service_id,
        )
    )).scalars().all())
    by_item = {row.checklist_item_id: row for row in existing}
    wanted = set(unique_ids)

    for item_id in unique_ids:
        row = by_item.get(item_id)
        if row is None:
            db.add(TenantServiceChecklistItem(
                tenant_id=tenant_id, master_service_id=master_service_id,
                checklist_item_id=item_id,
                checklist_template_version_id=uuid.UUID(version_by_item[item_id]),
                is_active=True, selected_by_user_id=selected_by_user_id,
            ))
        else:
            row.is_active = True
            row.checklist_template_version_id = uuid.UUID(version_by_item[item_id])
            row.selected_by_user_id = selected_by_user_id
            row.updated_at = _now()

    for row in existing:
        if row.checklist_item_id not in wanted and row.is_active:
            row.is_active = False
            row.updated_at = _now()

    await db.flush()
    return await tenant_selection_readiness(db, tenant_id, master_service_id)


async def tenant_selection_readiness(
    db: AsyncSession, tenant_id: uuid.UUID, master_service_id: uuid.UUID,
) -> dict:
    """Whether this tenant has satisfied the minimum for this service.

    Read-only and safe on a service with nothing authored yet:
    `nothing_authored` means the ADMIN has published no checklist for it, which
    is an admin gap rather than a tenant failure -- reported distinctly so the
    portal never tells a provider to pick 5 points from an empty list.
    `cannot_satisfy` covers the case where fewer than the minimum exist at all.
    """
    selectable = await selectable_items_for_service(db, master_service_id)
    selected = await get_tenant_selection(db, tenant_id, master_service_id)
    minimum = c.MIN_TENANT_CHECKLIST_ITEMS_PER_SERVICE
    selectable_total = len(selectable)
    selected_count = len(selected)
    return {
        "master_service_id": str(master_service_id),
        "minimum_required": minimum,
        "selected_count": selected_count,
        "selectable_total": selectable_total,
        "shortfall": max(0, minimum - selected_count),
        "satisfied": selected_count >= minimum,
        "nothing_authored": selectable_total == 0,
        "cannot_satisfy": 0 < selectable_total < minimum,
        "selected_item_ids": [str(r.checklist_item_id) for r in selected],
    }

async def customer_checklist_preview(
    db: AsyncSession, tenant_id: uuid.UUID | None, master_service_id: uuid.UUID,
) -> dict:
    """What the customer is told their technician will actually do, BEFORE they
    confirm the booking.

    This is the same authored content the technician will be held to -- narrowed
    to the points the assigned provider selected, and filtered to
    `customer_visible` so an internal-only step is never shown as a promise.

    Deliberately NOT a marketing list: every line here is a real checklist point
    that exists on the job the technician receives. If nothing is authored, it
    returns an empty list and the caller shows nothing, rather than inventing
    reassuring copy the provider is not actually committed to.
    """
    authored = await selectable_items_for_service(db, master_service_id)

    selected_ids: set[uuid.UUID] = set()
    if tenant_id is not None:
        selected_ids = {
            row.checklist_item_id
            for row in await get_tenant_selection(db, tenant_id, master_service_id)
        }

    # Mirrors _instance_items' fallback: with no selection yet, the technician
    # gets the full authored list, so that is what the customer is promised.
    items = [i for i in authored if uuid.UUID(i["id"]) in selected_ids] if selected_ids else authored
    visible = [i for i in items if i.get("customer_visible")]

    sections: list[dict] = []
    for item in visible:
        title = item.get("section_title") or "Service checks"
        if not sections or sections[-1]["title"] != title:
            sections.append({"title": title, "points": []})
        sections[-1]["points"].append({
            "id": item["id"],
            "label": item["label"],
            "help_text": item.get("help_text"),
            "requires_photo": bool(item.get("evidence_required")),
        })

    return {
        "master_service_id": str(master_service_id),
        "total_points": len(visible),
        "photo_points": sum(1 for i in visible if i.get("evidence_required")),
        "sections": sections,
        # True when these are the provider's own chosen points rather than the
        # full authored list -- lets the UI word it accurately either way.
        "provider_selected": bool(selected_ids),
    }

