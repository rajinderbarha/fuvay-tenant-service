"""Checklist Catalog Engine — platform-admin endpoints: template authoring,
publishing, Job-Type mapping CRUD, and audit/impact projections.

Permission: platform catalog admin only (require_super_admin) may create,
edit, publish, archive templates and mappings, per the task's permission
model. Tenant-admin read access is served from execution_router.py instead.
"""
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.checklist_catalog import service as svc
from app.engines.checklist_catalog.models import (
    ChecklistTemplate, ChecklistTemplateVersion, ChecklistSection, ChecklistItem,
    JobTypeChecklistMapping, JobChecklistInstance,
)
from app.engines.admin_catalog.models import MasterDataAuditLog
from app.exceptions import NotFoundException, ServiceOSException

router = APIRouter(prefix="/v1/admin/checklist-catalog", tags=["admin-checklist-catalog"])


def _user_id(user) -> uuid.UUID | None:
    value = getattr(user, "user_id", None) or getattr(user, "id", None)
    return uuid.UUID(str(value)) if value else None


def _audit(db: AsyncSession, *, entity_type: str, entity_id: uuid.UUID, action: str,
           user, request: Request, old: dict | None, new: dict | None,
           summary: str | None = None) -> None:
    db.add(MasterDataAuditLog(
        entity_type=entity_type, entity_id=entity_id, action=action,
        actor_user_id=_user_id(user), actor_role="SUPER_ADMIN",
        old_value=old, new_value=new, change_summary=summary,
        request_id=getattr(request.state, "request_id", None),
    ))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Templates ─────────────────────────────────────────────────────────────

@router.get("/templates")
async def list_templates(r: Request, status: str = Query("active"), limit: int = Query(200, ge=1, le=500),
                         user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    templates = (await db.execute(
        select(ChecklistTemplate).where(ChecklistTemplate.status == status)
        .order_by(ChecklistTemplate.name, ChecklistTemplate.id).limit(limit)
    )).scalars().all()
    template_ids = [template.id for template in templates]
    versions = (await db.execute(
        select(ChecklistTemplateVersion).where(ChecklistTemplateVersion.checklist_template_id.in_(template_ids))
        .order_by(ChecklistTemplateVersion.checklist_template_id, ChecklistTemplateVersion.version_number.desc())
    )).scalars().all() if template_ids else []
    latest_by_template = {}
    for version in versions:
        latest_by_template.setdefault(version.checklist_template_id, version)
    count_rows = (await db.execute(
        select(ChecklistTemplateVersion.checklist_template_id, func.count(JobTypeChecklistMapping.id))
        .join(JobTypeChecklistMapping, JobTypeChecklistMapping.checklist_template_version_id == ChecklistTemplateVersion.id)
        .where(ChecklistTemplateVersion.checklist_template_id.in_(template_ids))
        .group_by(ChecklistTemplateVersion.checklist_template_id)
    )).all() if template_ids else []
    count_by_template = {template_id: int(count) for template_id, count in count_rows}
    out = []
    for t in templates:
        latest = latest_by_template.get(t.id)
        d = t.to_dict()
        d["latest_version"] = latest.to_dict() if latest else None
        d["mapping_count"] = count_by_template.get(t.id, 0)
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
    sort_by: str = Query("updated_at"),
    sort_direction: str = Query("desc", pattern="^(asc|desc)$"),
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
    sort_columns = {
        "name": ChecklistTemplate.name, "code": ChecklistTemplate.code,
        "purpose": ChecklistTemplate.purpose, "status": ChecklistTemplate.status,
        "created_at": ChecklistTemplate.created_at, "updated_at": ChecklistTemplate.updated_at,
        "archived_at": ChecklistTemplate.archived_at,
    }
    sort_col = sort_columns.get(sort_by)
    if sort_col is None:
        raise ServiceOSException("CHECKLIST_SORT_INVALID", "Unknown checklist sort field.", status_code=422)
    order = sort_col.asc() if sort_direction == "asc" else sort_col.desc()
    rows = (await db.execute(
        select(ChecklistTemplate)
        .where(*filters)
        .order_by(order, ChecklistTemplate.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    template_ids = [row.id for row in rows]
    latest_by_template: dict[uuid.UUID, ChecklistTemplateVersion] = {}
    mapping_counts: dict[uuid.UUID, tuple[int, int]] = {}
    content_counts: dict[uuid.UUID, tuple[int, int]] = {}
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
                func.count(JobTypeChecklistMapping.id).filter(JobTypeChecklistMapping.status == "active"),
            )
            .outerjoin(
                JobTypeChecklistMapping,
                JobTypeChecklistMapping.checklist_template_version_id == ChecklistTemplateVersion.id,
            )
            .where(ChecklistTemplateVersion.checklist_template_id.in_(template_ids))
            .group_by(ChecklistTemplateVersion.checklist_template_id)
        )).all()
        mapping_counts = {template_id: (int(total_count), int(active_count)) for template_id, total_count, active_count in count_rows}
        latest_ids = [version.id for version in latest_by_template.values()]
        if latest_ids:
            content_rows = (await db.execute(
                select(
                    ChecklistTemplateVersion.checklist_template_id,
                    func.count(func.distinct(ChecklistSection.id)), func.count(ChecklistItem.id),
                )
                .outerjoin(ChecklistSection, ChecklistSection.checklist_template_version_id == ChecklistTemplateVersion.id)
                .outerjoin(ChecklistItem, ChecklistItem.checklist_section_id == ChecklistSection.id)
                .where(ChecklistTemplateVersion.id.in_(latest_ids))
                .group_by(ChecklistTemplateVersion.checklist_template_id)
            )).all()
            content_counts = {tid: (int(section_count), int(item_count)) for tid, section_count, item_count in content_rows}

    items = []
    for template in rows:
        item = template.to_dict()
        latest = latest_by_template.get(template.id)
        item["latest_version"] = latest.to_dict() if latest else None
        total_mappings, active_mappings = mapping_counts.get(template.id, (0, 0))
        section_count, item_count = content_counts.get(template.id, (0, 0))
        item["mapping_count"] = total_mappings
        item["active_mapping_count"] = active_mappings
        item["section_count"] = section_count
        item["item_count"] = item_count
        item["readiness"] = "ready" if latest and latest.status == "PUBLISHED" and item_count > 0 and active_mappings > 0 else "needs_attention"
        items.append(item)

    pages = max(1, (total + page_size - 1) // page_size)
    return ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }, _rid(r), "list_templates_directory")


@router.get("/summary")
async def catalog_summary(r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    values = (await db.execute(select(
        select(func.count(ChecklistTemplate.id)).where(ChecklistTemplate.status == "active").scalar_subquery(),
        select(func.count(ChecklistTemplate.id)).where(ChecklistTemplate.status == "archived").scalar_subquery(),
        select(func.count(ChecklistTemplateVersion.id)).where(ChecklistTemplateVersion.status == "PUBLISHED").scalar_subquery(),
        select(func.count(ChecklistTemplateVersion.id)).where(ChecklistTemplateVersion.status == "DRAFT").scalar_subquery(),
        select(func.count(JobTypeChecklistMapping.id)).where(JobTypeChecklistMapping.status == "active").scalar_subquery(),
        select(func.count(JobTypeChecklistMapping.id)).where(JobTypeChecklistMapping.status == "disabled").scalar_subquery(),
    ))).one()
    active_templates, retired_templates, published_versions, draft_versions, active_mappings, disabled_mappings = map(int, values)
    return ok({
        "active_templates": active_templates, "retired_templates": retired_templates,
        "published_versions": published_versions, "draft_versions": draft_versions,
        "active_mappings": active_mappings, "disabled_mappings": disabled_mappings,
        "unmapped_templates": int((await db.execute(
            select(func.count(ChecklistTemplate.id)).where(
                ChecklistTemplate.status == "active",
                ~ChecklistTemplate.id.in_(
                    select(ChecklistTemplateVersion.checklist_template_id)
                    .join(JobTypeChecklistMapping, JobTypeChecklistMapping.checklist_template_version_id == ChecklistTemplateVersion.id)
                    .where(JobTypeChecklistMapping.status == "active")
                ),
            )
        )).scalar_one()),
    }, _rid(r), "checklist_catalog_summary")


@router.get("/template-options")
async def list_published_template_options(
    r: Request,
    q: str | None = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=100),
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bounded, searchable picker of the latest published version per template."""
    latest_published = (
        select(
            ChecklistTemplateVersion.checklist_template_id.label("template_id"),
            func.max(ChecklistTemplateVersion.version_number).label("version_number"),
        )
        .where(ChecklistTemplateVersion.status == "PUBLISHED")
        .group_by(ChecklistTemplateVersion.checklist_template_id)
        .subquery()
    )
    filters = [ChecklistTemplate.status == "active"]
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(or_(ChecklistTemplate.name.ilike(term), ChecklistTemplate.code.ilike(term)))
    rows = (await db.execute(
        select(ChecklistTemplate, ChecklistTemplateVersion)
        .join(latest_published, latest_published.c.template_id == ChecklistTemplate.id)
        .join(
            ChecklistTemplateVersion,
            (ChecklistTemplateVersion.checklist_template_id == ChecklistTemplate.id)
            & (ChecklistTemplateVersion.version_number == latest_published.c.version_number),
        )
        .where(*filters)
        .order_by(ChecklistTemplate.name, ChecklistTemplate.id)
        .limit(limit)
    )).all()
    return ok([
        {**template.to_dict(), "latest_version": version.to_dict()}
        for template, version in rows
    ], _rid(r), "published_template_options")


@router.post("/templates")
async def create_template(body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    code = str(body.get("code") or "").strip().upper()
    if await db.scalar(select(ChecklistTemplate.id).where(ChecklistTemplate.code == code)):
        raise ServiceOSException("CHECKLIST_CODE_EXISTS", "A template already uses this code. Open that template or enter a different code.", status_code=409)
    template = await svc.create_template(
        db, name=body.get("name", ""), code=code, description=body.get("description"),
        icon_url=body.get("icon_url"),
        purpose=body.get("purpose", ""), owner_scope=body.get("owner_scope", "PLATFORM"),
        tenant_id=body.get("tenant_id"), created_by_user_id=_user_id(user),
    )
    _audit(db, entity_type="checklist_template", entity_id=template.id, action="CREATE",
           user=user, request=r, old=None, new=template.to_dict(), summary="Checklist template created")
    await db.commit()
    return ok(template.to_dict(), _rid(r), "create_template")


@router.put("/templates/{template_id}")
async def update_template(template_id: str, body: dict, r: Request,
                          user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    template = await db.get(ChecklistTemplate, uuid.UUID(template_id))
    if not template:
        raise NotFoundException("ChecklistTemplate", template_id)
    old = template.to_dict()
    fields = {k: body[k] for k in ("name", "description", "icon_url") if k in body}
    template = await svc.update_template_metadata(db, template, fields)
    _audit(db, entity_type="checklist_template", entity_id=template.id, action="UPDATE",
           user=user, request=r, old=old, new=template.to_dict(), summary="Checklist metadata updated")
    await db.commit()
    return ok(template.to_dict(), _rid(r), "update_template")


@router.get("/templates/{template_id}")
async def get_template(template_id: str, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    template = await db.get(ChecklistTemplate, uuid.UUID(template_id))
    if not template:
        raise NotFoundException("ChecklistTemplate", template_id)
    versions = (await db.execute(
        select(ChecklistTemplateVersion)
        .where(ChecklistTemplateVersion.checklist_template_id == template.id)
        .order_by(ChecklistTemplateVersion.version_number.desc())
    )).scalars().all()
    d = template.to_dict()
    d["versions"] = [v.to_dict() for v in versions]
    version_ids = [v.id for v in versions]
    mapping_count = int((await db.execute(
        select(func.count(JobTypeChecklistMapping.id)).where(
            JobTypeChecklistMapping.checklist_template_version_id.in_(version_ids)
        )
    )).scalar_one()) if version_ids else 0
    active_mapping_count = int((await db.execute(
        select(func.count(JobTypeChecklistMapping.id)).where(
            JobTypeChecklistMapping.checklist_template_version_id.in_(version_ids),
            JobTypeChecklistMapping.status == "active",
        )
    )).scalar_one()) if version_ids else 0
    instance_count = int((await db.execute(
        select(func.count(JobChecklistInstance.id)).where(
            JobChecklistInstance.checklist_template_version_id.in_(version_ids)
        )
    )).scalar_one()) if version_ids else 0
    d.update({"mapping_count": mapping_count, "active_mapping_count": active_mapping_count, "instance_count": instance_count})
    return ok(d, _rid(r), "get_template")


@router.get("/templates/{template_id}/audit")
async def template_audit(template_id: uuid.UUID, r: Request, page: int = Query(1, ge=1),
                         page_size: int = Query(25, ge=1, le=100),
                         user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    filters = (MasterDataAuditLog.entity_type == "checklist_template", MasterDataAuditLog.entity_id == template_id)
    total = int((await db.execute(select(func.count(MasterDataAuditLog.id)).where(*filters))).scalar_one())
    rows = (await db.execute(
        select(MasterDataAuditLog).where(*filters)
        .order_by(MasterDataAuditLog.created_at.desc(), MasterDataAuditLog.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return ok({"items": [row.to_dict() for row in rows], "total": total, "page": page,
               "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size)},
              _rid(r), "template_audit")


@router.post("/templates/{template_id}/draft-version")
async def get_or_create_draft(template_id: str, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    template = await db.get(ChecklistTemplate, uuid.UUID(template_id))
    if not template:
        raise NotFoundException("ChecklistTemplate", template_id)
    if template.status == "archived":
        raise ServiceOSException("CHECKLIST_TEMPLATE_RETIRED", "Restore this template before editing it.", status_code=409)
    version = await svc.get_draft_version(db, uuid.UUID(template_id))
    await db.commit()
    return ok(await _version_with_content(db, version), _rid(r), "get_or_create_draft")


@router.get("/templates/{template_id}/latest-version")
async def get_latest_version(template_id: str, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    template = await db.get(ChecklistTemplate, uuid.UUID(template_id))
    if not template:
        raise NotFoundException("ChecklistTemplate", template_id)
    version = await svc._latest_version(db, template.id)
    if not version:
        raise ServiceOSException("CHECKLIST_CONFIGURATION_UNRESOLVED", "Template has no versions.", status_code=409)
    return ok(await _version_with_content(db, version), _rid(r), "get_latest_version")


async def _version_with_content(db: AsyncSession, version: ChecklistTemplateVersion) -> dict:
    sections = (await db.execute(
        select(ChecklistSection)
        .where(ChecklistSection.checklist_template_version_id == version.id)
        .order_by(ChecklistSection.display_order)
    )).scalars().all()
    section_ids = [section.id for section in sections]
    items = (await db.execute(
        select(ChecklistItem)
        .where(ChecklistItem.checklist_section_id.in_(section_ids))
        .order_by(ChecklistItem.checklist_section_id, ChecklistItem.display_order, ChecklistItem.id)
    )).scalars().all() if section_ids else []
    items_by_section: dict[uuid.UUID, list[ChecklistItem]] = {}
    for item in items:
        items_by_section.setdefault(item.checklist_section_id, []).append(item)
    d = version.to_dict()
    section_list = []
    for sec in sections:
        sd = sec.to_dict()
        sd["items"] = [item.to_dict() for item in items_by_section.get(sec.id, [])]
        section_list.append(sd)
    d["sections"] = section_list
    return d


@router.post("/versions/{version_id}/sections")
async def add_section(version_id: str, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    version = await db.get(ChecklistTemplateVersion, uuid.UUID(version_id))
    if not version:
        raise NotFoundException("ChecklistTemplateVersion", version_id)
    await _editable_template(db, version)
    section = await svc.add_section(db, version, title=body.get("title", ""), display_order=int(body.get("display_order", 0)))
    await db.commit()
    return ok(section.to_dict(), _rid(r), "add_section")


@router.post("/sections/{section_id}/items")
async def add_item(section_id: str, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    section = await db.get(ChecklistSection, uuid.UUID(section_id))
    if not section:
        raise NotFoundException("ChecklistSection", section_id)
    version = await db.get(ChecklistTemplateVersion, section.checklist_template_version_id)
    await _editable_template(db, version)
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


async def _editable_template(db, version):
    if version is None:
        raise ServiceOSException("CHECKLIST_CONFIGURATION_UNRESOLVED", "Checklist version not found.", status_code=404)
    svc._assert_version_editable(version)
    template = await db.get(ChecklistTemplate, version.checklist_template_id)
    if template is None or template.status != "active":
        raise ServiceOSException("CHECKLIST_TEMPLATE_RETIRED", "Restore this template before editing or publishing.", status_code=409)


@router.put("/items/{item_id}")
async def update_item(item_id: uuid.UUID, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    item = await db.get(ChecklistItem, item_id)
    if item is None:
        raise NotFoundException("ChecklistItem", str(item_id))
    section = await db.get(ChecklistSection, item.checklist_section_id)
    version = await db.get(ChecklistTemplateVersion, section.checklist_template_version_id)
    await _editable_template(db, version)
    old = item.to_dict()
    await svc.update_item(db, item, version, body)
    _audit(db, entity_type="checklist_template", entity_id=version.checklist_template_id, action="UPDATE_ITEM",
           user=user, request=r, old=old, new=item.to_dict(), summary="Draft checklist item updated")
    await db.commit()
    return ok(item.to_dict(), _rid(r), "update_item")


@router.delete("/items/{item_id}")
async def delete_item(item_id: uuid.UUID, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    item = await db.get(ChecklistItem, item_id)
    if item is None:
        raise NotFoundException("ChecklistItem", str(item_id))
    section = await db.get(ChecklistSection, item.checklist_section_id)
    version = await db.get(ChecklistTemplateVersion, section.checklist_template_version_id)
    await _editable_template(db, version)
    _audit(db, entity_type="checklist_template", entity_id=version.checklist_template_id, action="DELETE_ITEM",
           user=user, request=r, old=item.to_dict(), new=None, summary="Draft checklist item removed")
    await db.delete(item)
    await db.commit()
    return ok({"deleted": True}, _rid(r), "delete_item")


@router.put("/sections/{section_id}")
async def update_section(section_id: uuid.UUID, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    section = await db.get(ChecklistSection, section_id)
    if section is None:
        raise NotFoundException("ChecklistSection", str(section_id))
    version = await db.get(ChecklistTemplateVersion, section.checklist_template_version_id)
    await _editable_template(db, version)
    title = str(body.get("title") or "").strip()
    if not title or len(title) > 200:
        raise ServiceOSException("CHECKLIST_SECTION_INVALID", "Enter a section title of 1–200 characters.", status_code=422)
    old = section.to_dict()
    section.title = title
    if "display_order" in body:
        section.display_order = int(body["display_order"])
    _audit(db, entity_type="checklist_template", entity_id=version.checklist_template_id, action="UPDATE_SECTION",
           user=user, request=r, old=old, new=section.to_dict(), summary="Draft section updated")
    await db.commit()
    return ok(section.to_dict(), _rid(r), "update_section")


@router.delete("/sections/{section_id}")
async def delete_section(section_id: uuid.UUID, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    section = await db.get(ChecklistSection, section_id)
    if section is None:
        raise NotFoundException("ChecklistSection", str(section_id))
    version = await db.get(ChecklistTemplateVersion, section.checklist_template_version_id)
    await _editable_template(db, version)
    _audit(db, entity_type="checklist_template", entity_id=version.checklist_template_id, action="DELETE_SECTION",
           user=user, request=r, old=section.to_dict(), new=None, summary="Draft section and its draft items removed")
    await db.execute(delete(ChecklistItem).where(ChecklistItem.checklist_section_id == section_id))
    await db.delete(section)
    await db.commit()
    return ok({"deleted": True}, _rid(r), "delete_section")


@router.post("/versions/{version_id}/publish")
async def publish_version(version_id: str, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    version = await db.get(ChecklistTemplateVersion, uuid.UUID(version_id))
    if not version:
        raise NotFoundException("ChecklistTemplateVersion", version_id)
    await _editable_template(db, version)
    published = await svc.publish_version(
        db, version, published_by=_user_id(user), change_summary=body.get("change_summary"),
    )
    _audit(db, entity_type="checklist_template", entity_id=version.checklist_template_id, action="PUBLISH_VERSION",
           user=user, request=r, old=None, new=published.to_dict(), summary=body.get("change_summary"))
    await db.commit()
    return ok(published.to_dict(), _rid(r), "publish_version")


@router.post("/templates/{template_id}/archive")
async def archive_template(template_id: str, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    template = await db.get(ChecklistTemplate, uuid.UUID(template_id))
    if not template:
        raise NotFoundException("ChecklistTemplate", template_id)
    old = template.to_dict()
    archived = await svc.archive_template(db, template, archived_by=_user_id(user), reason=body.get("reason", ""))
    _audit(db, entity_type="checklist_template", entity_id=template.id, action="RETIRE",
           user=user, request=r, old=old, new=archived.to_dict(), summary=body.get("reason"))
    await db.commit()
    return ok(archived.to_dict(), _rid(r), "archive_template")


@router.post("/templates/{template_id}/restore")
async def restore_template(template_id: str, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    template = await db.get(ChecklistTemplate, uuid.UUID(template_id))
    if not template:
        raise NotFoundException("ChecklistTemplate", template_id)
    old = template.to_dict()
    restored = await svc.restore_template(db, template, restored_by=_user_id(user), reason=body.get("reason", ""))
    _audit(db, entity_type="checklist_template", entity_id=template.id, action="RESTORE",
           user=user, request=r, old=old, new=restored.to_dict(), summary=body.get("reason"))
    await db.commit()
    return ok(restored.to_dict(), _rid(r), "restore_template")


# ── Job-Type mappings ─────────────────────────────────────────────────────

@router.get("/mappings")
async def list_mappings(r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    mappings = (await db.execute(select(JobTypeChecklistMapping).order_by(JobTypeChecklistMapping.created_at.desc()))).scalars().all()
    return ok([m.to_dict() for m in mappings], _rid(r), "list_mappings")


@router.get("/mappings-directory")
async def list_mappings_directory(
    r: Request,
    q: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    usage: str | None = Query(None),
    actor: str | None = Query(None),
    phase: str | None = Query(None),
    master_service_job_type_id: uuid.UUID | None = Query(None),
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
    if master_service_job_type_id:
        filters.append(JobTypeChecklistMapping.master_service_job_type_id == master_service_job_type_id)
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(or_(
            JobTypeChecklistMapping.phase.ilike(term),
            JobTypeChecklistMapping.completion_gate.ilike(term),
        ))
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
    enriched = []
    if rows:
        from app.engines.admin_catalog.models import JobTypeDefinition, MasterService, MasterServiceJobType
        link_ids = [row.master_service_job_type_id for row in rows]
        version_ids = [row.checklist_template_version_id for row in rows]
        links = (await db.execute(select(MasterServiceJobType).where(MasterServiceJobType.id.in_(link_ids)))).scalars().all()
        link_by_id = {link.id: link for link in links}
        service_ids = [link.master_service_id for link in links]
        job_type_ids = [link.job_type_id for link in links]
        services = (await db.execute(select(MasterService).where(MasterService.id.in_(service_ids)))).scalars().all() if service_ids else []
        job_types = (await db.execute(select(JobTypeDefinition).where(JobTypeDefinition.id.in_(job_type_ids)))).scalars().all() if job_type_ids else []
        versions = (await db.execute(select(ChecklistTemplateVersion).where(ChecklistTemplateVersion.id.in_(version_ids)))).scalars().all()
        templates = (await db.execute(select(ChecklistTemplate).where(ChecklistTemplate.id.in_([v.checklist_template_id for v in versions])))).scalars().all() if versions else []
        service_by_id = {service.id: service for service in services}
        job_type_by_id = {job_type.id: job_type for job_type in job_types}
        version_by_id = {version.id: version for version in versions}
        template_by_id = {template.id: template for template in templates}
        for row in rows:
            item = row.to_dict()
            link = link_by_id.get(row.master_service_job_type_id)
            version = version_by_id.get(row.checklist_template_version_id)
            template = template_by_id.get(version.checklist_template_id) if version else None
            service = service_by_id.get(link.master_service_id) if link else None
            job_type = job_type_by_id.get(link.job_type_id) if link else None
            item.update({
                "template_name": template.name if template else None,
                "template_code": template.code if template else None,
                "template_version": version.version_number if version else None,
                "master_service_name": service.service_name if service else None,
                "job_type_label": job_type.label if job_type else None,
            })
            enriched.append(item)
    return ok({
        "items": enriched,
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
    _audit(db, entity_type="checklist_mapping", entity_id=mapping.id, action="CREATE",
           user=user, request=r, old=None, new=mapping.to_dict(), summary="Job-type mapping created")
    await db.commit()
    return ok(mapping.to_dict(), _rid(r), "create_mapping")


@router.post("/quick-create-mapping")
async def quick_create_mapping(body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    """Create, publish and map atomically; a failed mapping leaves no orphan template."""
    labels = body.get("items")
    if not isinstance(labels, list) or not 1 <= len(labels) <= 100 or any(not isinstance(label, str) or not label.strip() for label in labels):
        raise ServiceOSException("CHECKLIST_ITEMS_REQUIRED", "Enter 1–100 checklist points, one per line.", status_code=422)
    try:
        link_id = uuid.UUID(str(body.get("master_service_job_type_id")))
    except (ValueError, TypeError):
        raise ServiceOSException("CHECKLIST_CONFIGURATION_UNRESOLVED", "Select an exact job type before creating a checklist.", status_code=422)
    try:
        async with db.begin_nested():
            template = await svc.create_template(
                db, name=body.get("name", ""), code=body.get("code", ""), description=None,
                purpose=body.get("purpose", "INSPECTION"), owner_scope="PLATFORM", tenant_id=None, created_by_user_id=_user_id(user),
            )
            version = await svc.get_draft_version(db, template.id)
            section = await svc.add_section(db, version, "Checklist")
            for index, label in enumerate(labels):
                await svc.add_item(db, section, version, item_type="CHECKBOX", label=label, is_required=True, display_order=index)
            await svc.publish_version(db, version, published_by=_user_id(user), change_summary="Created and mapped from Catalog Workspace")
            mapping = await svc.create_mapping(
                db, master_service_job_type_id=link_id, service_job_workflow_id=None,
                checklist_template_version_id=version.id, phase=body.get("phase", "inspection"),
                usage=body.get("usage", "REQUIRED"), actor=body.get("actor", "TECHNICIAN"),
                completion_gate=body.get("completion_gate", "NONE"), condition_rules=None, display_order=0, created_by=_user_id(user),
            )
            _audit(db, entity_type="checklist_template", entity_id=template.id, action="CREATE_AND_PUBLISH",
                   user=user, request=r, old=None, new=version.to_dict(), summary="Checklist created, published and mapped")
            _audit(db, entity_type="job_type_checklist_mapping", entity_id=mapping.id, action="CREATE_MAPPING",
                   user=user, request=r, old=None, new=mapping.to_dict(), summary="Checklist mapped to exact job type")
    except IntegrityError as error:
        raise ServiceOSException("CHECKLIST_CONFLICT", "This checklist code or mapping already exists. Use the existing template or choose a different code.", status_code=409) from error
    await db.commit()
    return ok({"template_id": str(template.id), "version_id": str(version.id), "mapping": mapping.to_dict()}, _rid(r), "quick_create_mapping")


@router.post("/mappings/{mapping_id}/disable")
async def disable_mapping(mapping_id: str, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    mapping = await db.get(JobTypeChecklistMapping, uuid.UUID(mapping_id))
    if not mapping:
        raise NotFoundException("JobTypeChecklistMapping", mapping_id)
    old = mapping.to_dict()
    disabled = await svc.disable_mapping(db, mapping, updated_by=_user_id(user), reason=body.get("reason", ""))
    _audit(db, entity_type="checklist_mapping", entity_id=mapping.id, action="DISABLE",
           user=user, request=r, old=old, new=disabled.to_dict(), summary=body.get("reason"))
    await db.commit()
    return ok(disabled.to_dict(), _rid(r), "disable_mapping")


@router.post("/mappings/{mapping_id}/enable")
async def enable_mapping(mapping_id: str, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    mapping = await db.get(JobTypeChecklistMapping, uuid.UUID(mapping_id))
    if not mapping:
        raise NotFoundException("JobTypeChecklistMapping", mapping_id)
    old = mapping.to_dict()
    enabled = await svc.enable_mapping(db, mapping, updated_by=_user_id(user))
    _audit(db, entity_type="checklist_mapping", entity_id=mapping.id, action="ENABLE",
           user=user, request=r, old=old, new=enabled.to_dict(), summary="Mapping enabled")
    await db.commit()
    return ok(enabled.to_dict(), _rid(r), "enable_mapping")


# ── Execution health (real data only, no hardcoded samples) ─────────────

@router.get("/execution-health")
async def execution_health(r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    from app.engines.checklist_catalog import constants as c
    total, blocked, completed, in_progress, waived = map(int, (await db.execute(select(
        func.count(JobChecklistInstance.id),
        func.count(JobChecklistInstance.id).filter(JobChecklistInstance.state == c.INSTANCE_BLOCKED),
        func.count(JobChecklistInstance.id).filter(JobChecklistInstance.state == c.INSTANCE_COMPLETED),
        func.count(JobChecklistInstance.id).filter(JobChecklistInstance.state == c.INSTANCE_IN_PROGRESS),
        func.count(JobChecklistInstance.id).filter(JobChecklistInstance.state == c.INSTANCE_WAIVED),
    ))).one())
    completion_rate = (completed / total) if total else None
    return ok({
        "total_instances": total,
        "completed_instances": completed,
        "blocked_instances": blocked,
        "in_progress_instances": in_progress,
        "waived_instances": waived,
        "required_completion_rate": completion_rate,
    }, _rid(r), "execution_health")
