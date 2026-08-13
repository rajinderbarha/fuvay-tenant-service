"""Checklist Catalog Engine — platform-admin endpoints: template authoring,
publishing, Job-Type mapping CRUD, and audit/impact projections.

Permission: platform catalog admin only (require_super_admin) may create,
edit, publish, archive templates and mappings, per the task's permission
model. Tenant-admin read access is served from execution_router.py instead.
"""
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.checklist_catalog import service as svc
from app.engines.checklist_catalog.models import (
    ChecklistTemplate, ChecklistTemplateVersion, ChecklistSection, ChecklistItem,
    JobTypeChecklistMapping,
)

router = APIRouter(prefix="/v1/admin/checklist-catalog", tags=["admin-checklist-catalog"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Templates ─────────────────────────────────────────────────────────────

@router.get("/templates")
async def list_templates(r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    templates = (await db.execute(select(ChecklistTemplate).order_by(ChecklistTemplate.created_at.desc()))).scalars().all()
    out = []
    for t in templates:
        latest = await svc._latest_version(db, t.id)
        mapping_count = len((await db.execute(
            select(JobTypeChecklistMapping).join(
                ChecklistTemplateVersion,
                JobTypeChecklistMapping.checklist_template_version_id == ChecklistTemplateVersion.id,
            ).where(ChecklistTemplateVersion.checklist_template_id == t.id)
        )).scalars().all())
        d = t.to_dict()
        d["latest_version"] = latest.to_dict() if latest else None
        d["mapping_count"] = mapping_count
        out.append(d)
    return ok(out, _rid(r), "list_templates")


@router.get("/templates-directory")
async def list_templates_directory(
    r: Request,
    q: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    purpose: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Paged checklist library for the admin directory.

    The legacy ``/templates`` route remains for bounded picker surfaces.  This
    endpoint is deliberately batch-oriented so the main library never loads
    an unbounded table or performs one latest-version/count query per row.
    """
    filters = []
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(or_(
            ChecklistTemplate.name.ilike(term),
            ChecklistTemplate.code.ilike(term),
            ChecklistTemplate.description.ilike(term),
        ))
    if status:
        filters.append(ChecklistTemplate.status == status)
    if purpose:
        filters.append(ChecklistTemplate.purpose == purpose)

    total = int((await db.execute(
        select(func.count(ChecklistTemplate.id)).where(*filters)
    )).scalar_one())
    rows = (await db.execute(
        select(ChecklistTemplate)
        .where(*filters)
        .order_by(ChecklistTemplate.updated_at.desc(), ChecklistTemplate.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    template_ids = [row.id for row in rows]
    latest_by_template: dict[uuid.UUID, ChecklistTemplateVersion] = {}
    mapping_counts: dict[uuid.UUID, int] = {}
    if template_ids:
        versions = (await db.execute(
            select(ChecklistTemplateVersion)
            .where(ChecklistTemplateVersion.checklist_template_id.in_(template_ids))
            .order_by(
                ChecklistTemplateVersion.checklist_template_id,
                ChecklistTemplateVersion.version_number.desc(),
            )
        )).scalars().all()
        for version in versions:
            latest_by_template.setdefault(version.checklist_template_id, version)

        count_rows = (await db.execute(
            select(
                ChecklistTemplateVersion.checklist_template_id,
                func.count(JobTypeChecklistMapping.id),
            )
            .outerjoin(
                JobTypeChecklistMapping,
                JobTypeChecklistMapping.checklist_template_version_id == ChecklistTemplateVersion.id,
            )
            .where(ChecklistTemplateVersion.checklist_template_id.in_(template_ids))
            .group_by(ChecklistTemplateVersion.checklist_template_id)
        )).all()
        mapping_counts = {template_id: int(count) for template_id, count in count_rows}

    items = []
    for template in rows:
        item = template.to_dict()
        latest = latest_by_template.get(template.id)
        item["latest_version"] = latest.to_dict() if latest else None
        item["mapping_count"] = mapping_counts.get(template.id, 0)
        items.append(item)

    pages = max(1, (total + page_size - 1) // page_size)
    return ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }, _rid(r), "list_templates_directory")


@router.post("/templates")
async def create_template(body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    template = await svc.create_template(
        db, name=body["name"], code=body["code"], description=body.get("description"),
        icon_url=body.get("icon_url"),
        purpose=body["purpose"], owner_scope=body.get("owner_scope", "PLATFORM"),
        tenant_id=body.get("tenant_id"), created_by_user_id=getattr(user, "id", None),
    )
    await db.commit()
    return ok(template.to_dict(), _rid(r), "create_template")


@router.put("/templates/{template_id}")
async def update_template(template_id: str, body: dict, r: Request,
                          user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    template = await db.get(ChecklistTemplate, uuid.UUID(template_id))
    if not template:
        from app.exceptions import NotFoundException
        raise NotFoundException("ChecklistTemplate", template_id)
    fields = {k: body[k] for k in ("name", "description", "icon_url") if k in body}
    template = await svc.update_template_metadata(db, template, fields)
    await db.commit()
    return ok(template.to_dict(), _rid(r), "update_template")


@router.get("/templates/{template_id}")
async def get_template(template_id: str, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    template = await db.get(ChecklistTemplate, uuid.UUID(template_id))
    versions = (await db.execute(
        select(ChecklistTemplateVersion)
        .where(ChecklistTemplateVersion.checklist_template_id == template.id)
        .order_by(ChecklistTemplateVersion.version_number.desc())
    )).scalars().all()
    d = template.to_dict()
    d["versions"] = [v.to_dict() for v in versions]
    return ok(d, _rid(r), "get_template")


@router.get("/templates/{template_id}/draft-version")
async def get_or_create_draft(template_id: str, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    version = await svc.get_draft_version(db, uuid.UUID(template_id))
    await db.commit()
    return ok(await _version_with_content(db, version), _rid(r), "get_or_create_draft")


async def _version_with_content(db: AsyncSession, version: ChecklistTemplateVersion) -> dict:
    sections = (await db.execute(
        select(ChecklistSection)
        .where(ChecklistSection.checklist_template_version_id == version.id)
        .order_by(ChecklistSection.display_order)
    )).scalars().all()
    d = version.to_dict()
    section_list = []
    for sec in sections:
        items = (await db.execute(
            select(ChecklistItem).where(ChecklistItem.checklist_section_id == sec.id).order_by(ChecklistItem.display_order)
        )).scalars().all()
        sd = sec.to_dict()
        sd["items"] = [i.to_dict() for i in items]
        section_list.append(sd)
    d["sections"] = section_list
    return d


@router.post("/versions/{version_id}/sections")
async def add_section(version_id: str, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    version = await db.get(ChecklistTemplateVersion, uuid.UUID(version_id))
    section = await svc.add_section(db, version, title=body["title"], display_order=int(body.get("display_order", 0)))
    await db.commit()
    return ok(section.to_dict(), _rid(r), "add_section")


@router.post("/sections/{section_id}/items")
async def add_item(section_id: str, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    section = await db.get(ChecklistSection, uuid.UUID(section_id))
    version = await db.get(ChecklistTemplateVersion, section.checklist_template_version_id)
    item = await svc.add_item(
        db, section, version,
        item_type=body["item_type"], label=body["label"], help_text=body.get("help_text"),
        is_required=bool(body.get("is_required", False)),
        evidence_required=bool(body.get("evidence_required", False)),
        min_evidence_count=int(body.get("min_evidence_count", 0)),
        max_evidence_count=int(body.get("max_evidence_count", 1)),
        allowed_file_types=body.get("allowed_file_types"),
        measurement_unit=body.get("measurement_unit"),
        select_options=body.get("select_options"),
        validation_rules=body.get("validation_rules"),
        display_order=int(body.get("display_order", 0)),
        condition_rules=body.get("condition_rules"),
        failure_behavior=body.get("failure_behavior"),
        customer_visible=bool(body.get("customer_visible", False)),
    )
    await db.commit()
    return ok(item.to_dict(), _rid(r), "add_item")


@router.post("/versions/{version_id}/publish")
async def publish_version(version_id: str, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    version = await db.get(ChecklistTemplateVersion, uuid.UUID(version_id))
    published = await svc.publish_version(
        db, version, published_by=getattr(user, "id", None), change_summary=body.get("change_summary"),
    )
    await db.commit()
    return ok(published.to_dict(), _rid(r), "publish_version")


@router.post("/templates/{template_id}/archive")
async def archive_template(template_id: str, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    template = await db.get(ChecklistTemplate, uuid.UUID(template_id))
    archived = await svc.archive_template(db, template)
    await db.commit()
    return ok(archived.to_dict(), _rid(r), "archive_template")


# ── Job-Type mappings ─────────────────────────────────────────────────────

@router.get("/mappings")
async def list_mappings(r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    mappings = (await db.execute(select(JobTypeChecklistMapping).order_by(JobTypeChecklistMapping.created_at.desc()))).scalars().all()
    return ok([m.to_dict() for m in mappings], _rid(r), "list_mappings")


@router.get("/mappings-directory")
async def list_mappings_directory(
    r: Request,
    status: str | None = Query(None),
    usage: str | None = Query(None),
    actor: str | None = Query(None),
    phase: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    for column, value in (
        (JobTypeChecklistMapping.status, status),
        (JobTypeChecklistMapping.usage, usage),
        (JobTypeChecklistMapping.actor, actor),
        (JobTypeChecklistMapping.phase, phase),
    ):
        if value:
            filters.append(column == value)
    total = int((await db.execute(
        select(func.count(JobTypeChecklistMapping.id)).where(*filters)
    )).scalar_one())
    rows = (await db.execute(
        select(JobTypeChecklistMapping)
        .where(*filters)
        .order_by(JobTypeChecklistMapping.updated_at.desc(), JobTypeChecklistMapping.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()
    pages = max(1, (total + page_size - 1) // page_size)
    return ok({
        "items": [row.to_dict() for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }, _rid(r), "list_mappings_directory")


@router.post("/mappings")
async def create_mapping(body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    mapping = await svc.create_mapping(
        db,
        master_service_job_type_id=uuid.UUID(body["master_service_job_type_id"]),
        service_job_workflow_id=uuid.UUID(body["service_job_workflow_id"]) if body.get("service_job_workflow_id") else None,
        checklist_template_version_id=uuid.UUID(body["checklist_template_version_id"]),
        phase=body["phase"], usage=body.get("usage", "OPTIONAL"), actor=body.get("actor", "TECHNICIAN"),
        completion_gate=body.get("completion_gate", "NONE"), condition_rules=body.get("condition_rules"),
        display_order=int(body.get("display_order", 0)), created_by=getattr(user, "id", None),
    )
    await db.commit()
    return ok(mapping.to_dict(), _rid(r), "create_mapping")


@router.post("/mappings/{mapping_id}/disable")
async def disable_mapping(mapping_id: str, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    mapping = await db.get(JobTypeChecklistMapping, uuid.UUID(mapping_id))
    disabled = await svc.disable_mapping(db, mapping, updated_by=getattr(user, "id", None))
    await db.commit()
    return ok(disabled.to_dict(), _rid(r), "disable_mapping")


# ── Execution health (real data only, no hardcoded samples) ─────────────

@router.get("/execution-health")
async def execution_health(r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    from app.engines.checklist_catalog.models import JobChecklistInstance
    from app.engines.checklist_catalog import constants as c

    total = len((await db.execute(select(JobChecklistInstance))).scalars().all())
    blocked = len((await db.execute(
        select(JobChecklistInstance).where(JobChecklistInstance.state == c.INSTANCE_BLOCKED)
    )).scalars().all())
    completed = len((await db.execute(
        select(JobChecklistInstance).where(JobChecklistInstance.state == c.INSTANCE_COMPLETED)
    )).scalars().all())
    in_progress = len((await db.execute(
        select(JobChecklistInstance).where(JobChecklistInstance.state == c.INSTANCE_IN_PROGRESS)
    )).scalars().all())
    completion_rate = (completed / total) if total else None
    return ok({
        "total_instances": total,
        "completed_instances": completed,
        "blocked_instances": blocked,
        "in_progress_instances": in_progress,
        "required_completion_rate": completion_rate,
    }, _rid(r), "execution_health")
