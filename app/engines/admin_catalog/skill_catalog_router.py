"""Admin-owned category skill catalog and provider selection projection."""
from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, get_current_user, require_super_admin
from app.dependencies.db import get_db
from app.exceptions import ServiceOSException
from app.schemas.base import ok

admin_router = APIRouter(prefix="/v1/admin/categories", tags=["Category Skills"])
provider_router = APIRouter(prefix="/v1/provider", tags=["Provider Team Skills"])


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _tenant_id(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_REQUIRED", "No tenant workspace is selected.", status_code=403)
    return uuid.UUID(str(user.tenant_id))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")[:100]


async def resolve_team_category_id(db: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    """Resolve the category used by the Home Services team workspace.

    New onboarding is vertical/enrollment based, while old tenants stored a
    category directly. Prefer an enabled offering (the actual runtime scope),
    then the legacy value, then the active Home Services category.
    """
    row = (await db.execute(text("""
        SELECT COALESCE(
          (SELECT ms.category_id
             FROM tenant_services ts
             JOIN master_services ms ON ms.id=ts.master_service_id
            WHERE ts.tenant_id=:tid AND ts.is_enabled=true AND ts.deleted_at IS NULL
            ORDER BY ts.created_at LIMIT 1),
          t.category_id,
          (SELECT sc.id FROM service_categories sc
            WHERE sc.vertical_type='home_services' AND sc.is_active=true
            ORDER BY sc.created_at LIMIT 1)
        ) AS category_id
        FROM tenants t WHERE t.id=:tid
    """), {"tid": str(tenant_id)})).first()
    if not row or not row.category_id:
        raise ServiceOSException(
            "TEAM_CATEGORY_UNAVAILABLE",
            "Home Services is not configured for this workspace. Configure at least one service before adding a technician.",
            status_code=422,
        )
    return uuid.UUID(str(row.category_id))


async def validate_skill_ids(
    db: AsyncSession, category_id: uuid.UUID, skill_ids: list[str]
) -> list[dict[str, Any]]:
    if not skill_ids:
        return []
    try:
        normalized = list(dict.fromkeys(str(uuid.UUID(str(value))) for value in skill_ids))
    except (ValueError, TypeError):
        raise ServiceOSException("INVALID_SKILL_SELECTION", "One or more selected skills are invalid.", status_code=422)
    rows = (await db.execute(text("""
        SELECT cs.id::text, cs.name, cs.requires_verification
          FROM category_skills cs
         WHERE cs.category_id=:cid AND cs.status='active' AND cs.id = ANY(CAST(:ids AS uuid[]))
    """), {"cid": str(category_id), "ids": normalized})).mappings().all()
    if {row["id"] for row in rows} != set(normalized):
        raise ServiceOSException(
            "INVALID_SKILL_SELECTION",
            "One or more skills are retired or do not belong to this business category.",
            status_code=422,
        )
    by_id = {row["id"]: dict(row) for row in rows}
    return [by_id[value] for value in normalized]


async def replace_member_skills(
    db: AsyncSession, *, tenant_id: uuid.UUID, member_id: uuid.UUID,
    selected: list[dict[str, Any]], actor_id: str | None,
) -> None:
    ids = [row["id"] for row in selected]
    if ids:
        await db.execute(text("""
            DELETE FROM provider_team_member_skills
             WHERE tenant_id=:tid AND staff_member_id=:mid AND NOT (skill_id = ANY(CAST(:ids AS uuid[])))
        """), {"tid": str(tenant_id), "mid": str(member_id), "ids": ids})
    else:
        await db.execute(text(
            "DELETE FROM provider_team_member_skills WHERE tenant_id=:tid AND staff_member_id=:mid"
        ), {"tid": str(tenant_id), "mid": str(member_id)})
    for row in selected:
        await db.execute(text("""
            INSERT INTO provider_team_member_skills
              (tenant_id, staff_member_id, skill_id, verification_status, assigned_by_user_id)
            VALUES (:tid,:mid,:sid,:verification,:actor)
            ON CONFLICT (staff_member_id, skill_id) DO NOTHING
        """), {
            "tid": str(tenant_id), "mid": str(member_id), "sid": row["id"],
            "verification": "pending" if row["requires_verification"] else "not_required",
            "actor": actor_id,
        })
    await db.execute(text(
        "UPDATE provider_team_members SET skills=CAST(:skills AS jsonb), updated_at=now() WHERE id=:mid AND tenant_id=:tid"
    ), {"skills": __import__("json").dumps([row["name"] for row in selected]),
        "mid": str(member_id), "tid": str(tenant_id)})


async def member_skill_ids(db: AsyncSession, tenant_id: uuid.UUID, member_ids: list[str]) -> dict[str, list[str]]:
    if not member_ids:
        return {}
    rows = (await db.execute(text("""
        SELECT staff_member_id::text, skill_id::text
          FROM provider_team_member_skills
         WHERE tenant_id=:tid AND staff_member_id = ANY(CAST(:ids AS uuid[]))
         ORDER BY created_at, id
    """), {"tid": str(tenant_id), "ids": member_ids})).fetchall()
    result: dict[str, list[str]] = {value: [] for value in member_ids}
    for row in rows:
        result.setdefault(row.staff_member_id, []).append(row.skill_id)
    return result


async def _category_exists(db: AsyncSession, category_id: uuid.UUID) -> None:
    found = (await db.execute(text("SELECT 1 FROM service_categories WHERE id=:id"), {"id": str(category_id)})).scalar()
    if not found:
        raise ServiceOSException("CATEGORY_NOT_FOUND", "Category not found.", status_code=404)


def _skill_dict(row) -> dict:
    d = dict(row._mapping if hasattr(row, "_mapping") else row)
    for key in ("id", "category_id", "service_group_id"):
        if d.get(key) is not None:
            d[key] = str(d[key])
    for key in ("created_at", "updated_at", "retired_at"):
        if d.get(key) is not None:
            d[key] = d[key].isoformat()
    return d


@admin_router.post("/{category_id}/skills/add-starters")
async def add_category_starter_skills(
    category_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(require_super_admin),
):
    vertical = (await db.execute(text(
        "SELECT vertical_type FROM service_categories WHERE id=:cid FOR UPDATE"
    ), {"cid": str(category_id)})).scalar()
    if vertical != "home_services":
        raise ServiceOSException("STARTER_SKILLS_NOT_AVAILABLE", "Starter skills are available for Home Services categories. Add custom skills for this category.", status_code=422)
    from app.engines.admin_catalog.starter_skills import add_starter_skills
    from app.core.audit import record_platform_audit
    added = await add_starter_skills(db, category_id, user.user_id)
    await record_platform_audit(
        db, operation="category_skills.starters_added", engine_id="admin_catalog",
        entity_type="service_category", entity_id=str(category_id),
        actor_id=uuid.UUID(str(user.user_id)), actor_role=user.role,
        request_id=_rid(request), after={"added": added},
    )
    await db.commit()
    return ok({"added": added}, _rid(request), "admin_catalog")


@admin_router.get("/{category_id}/skills")
async def list_category_skills(
    category_id: uuid.UUID, request: Request,
    q: str | None = Query(None, max_length=120), status: str | None = Query(None),
    service_group_id: uuid.UUID | None = Query(None), page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db), _: UserContext = Depends(require_super_admin),
):
    await _category_exists(db, category_id)
    where = ["cs.category_id=:cid"]
    params: dict[str, Any] = {"cid": str(category_id), "limit": page_size, "offset": (page - 1) * page_size}
    if q:
        where.append("(cs.name ILIKE :q OR cs.code ILIKE :q OR COALESCE(cs.description,'') ILIKE :q)")
        params["q"] = f"%{q.strip()}%"
    if status in {"active", "retired"}:
        where.append("cs.status=:status")
        params["status"] = status
    if service_group_id:
        where.append("cs.service_group_id=:gid")
        params["gid"] = str(service_group_id)
    clause = " AND ".join(where)
    total = (await db.execute(text(f"SELECT count(*) FROM category_skills cs WHERE {clause}"), params)).scalar() or 0
    rows = (await db.execute(text(f"""
        SELECT cs.*, sg.name AS service_group_name,
               (SELECT count(*) FROM provider_team_member_skills a WHERE a.skill_id=cs.id) AS assigned_count
          FROM category_skills cs LEFT JOIN service_groups sg ON sg.id=cs.service_group_id
         WHERE {clause}
         ORDER BY cs.display_order, lower(cs.name), cs.id LIMIT :limit OFFSET :offset
    """), params)).fetchall()
    return ok({"items": [_skill_dict(row) for row in rows], "total": int(total), "page": page,
               "page_size": page_size, "pages": max(1, (int(total) + page_size - 1) // page_size)}, _rid(request), "admin_catalog")


async def _validate_group(db: AsyncSession, category_id: uuid.UUID, group_id: str | None) -> str | None:
    if not group_id:
        return None
    try:
        gid = str(uuid.UUID(str(group_id)))
    except ValueError:
        raise ServiceOSException("INVALID_SERVICE_GROUP", "Choose a valid service group.", status_code=422)
    found = (await db.execute(text(
        "SELECT 1 FROM service_groups WHERE id=:gid AND category_id=:cid AND status='active' AND deleted_at IS NULL"
    ), {"gid": gid, "cid": str(category_id)})).scalar()
    if not found:
        raise ServiceOSException("INVALID_SERVICE_GROUP", "The service group is not active in this category.", status_code=422)
    return gid


@admin_router.post("/{category_id}/skills", status_code=201)
async def create_category_skill(
    category_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(require_super_admin),
):
    await _category_exists(db, category_id)
    name = str(payload.get("name") or "").strip()
    code = _slug(str(payload.get("code") or name))
    if not name or not code:
        raise ServiceOSException("SKILL_NAME_REQUIRED", "Skill name is required.", status_code=422)
    gid = await _validate_group(db, category_id, payload.get("service_group_id"))
    duplicate = (await db.execute(text(
        "SELECT 1 FROM category_skills WHERE category_id=:cid AND (code=:code OR lower(name)=lower(:name))"
    ), {"cid": str(category_id), "code": code, "name": name})).scalar()
    if duplicate:
        raise ServiceOSException("DUPLICATE_CATEGORY_SKILL", "A skill with this name or code already exists in the category.", status_code=409)
    row = (await db.execute(text("""
        INSERT INTO category_skills
          (category_id, service_group_id, code, name, description, status, requires_verification,
           display_order, created_by_user_id, updated_by_user_id)
        VALUES (:cid,:gid,:code,:name,:description,'active',:verify,:display_order,:actor,:actor)
        RETURNING *
    """), {"cid": str(category_id), "gid": gid, "code": code, "name": name,
            "description": str(payload.get("description") or "").strip() or None,
            "verify": bool(payload.get("requires_verification", False)),
            "display_order": int(payload.get("display_order") or 100), "actor": user.user_id})).first()
    await db.commit()
    return ok(_skill_dict(row), _rid(request), "admin_catalog")


@admin_router.put("/{category_id}/skills/{skill_id}")
async def update_category_skill(
    category_id: uuid.UUID, skill_id: uuid.UUID, payload: dict, request: Request,
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(require_super_admin),
):
    current = (await db.execute(text(
        "SELECT * FROM category_skills WHERE id=:id AND category_id=:cid"
    ), {"id": str(skill_id), "cid": str(category_id)})).first()
    if not current:
        raise ServiceOSException("SKILL_NOT_FOUND", "Skill not found in this category.", status_code=404)
    fields: dict[str, Any] = {}
    for key in ("name", "description"):
        if key in payload:
            fields[key] = str(payload.get(key) or "").strip() or (None if key == "description" else "")
    if "name" in fields and not fields["name"]:
        raise ServiceOSException("SKILL_NAME_REQUIRED", "Skill name is required.", status_code=422)
    if "code" in payload:
        fields["code"] = _slug(str(payload.get("code") or ""))
    if "service_group_id" in payload:
        fields["service_group_id"] = await _validate_group(db, category_id, payload.get("service_group_id"))
    if "requires_verification" in payload:
        fields["requires_verification"] = bool(payload["requires_verification"])
    if "display_order" in payload:
        fields["display_order"] = int(payload["display_order"])
    if not fields:
        raise ServiceOSException("NO_CHANGES", "No editable skill fields were supplied.", status_code=422)
    fields["updated_by_user_id"] = user.user_id
    sets = ", ".join(f"{key}=:{key}" for key in fields)
    fields.update({"id": str(skill_id), "cid": str(category_id)})
    try:
        row = (await db.execute(text(
            f"UPDATE category_skills SET {sets}, updated_at=now() WHERE id=:id AND category_id=:cid RETURNING *"
        ), fields)).first()
        await db.commit()
    except Exception as exc:
        await db.rollback()
        if "uq_category_skills_category_code" in str(exc):
            raise ServiceOSException("DUPLICATE_CATEGORY_SKILL", "A skill with this code already exists.", status_code=409)
        raise
    return ok(_skill_dict(row), _rid(request), "admin_catalog")


@admin_router.post("/{category_id}/skills/{skill_id}/retire")
async def retire_category_skill(
    category_id: uuid.UUID, skill_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(require_super_admin),
):
    row = (await db.execute(text("""
        UPDATE category_skills SET status='retired', retired_at=now(), updated_at=now(), updated_by_user_id=:actor
         WHERE id=:id AND category_id=:cid RETURNING *
    """), {"id": str(skill_id), "cid": str(category_id), "actor": user.user_id})).first()
    if not row:
        raise ServiceOSException("SKILL_NOT_FOUND", "Skill not found in this category.", status_code=404)
    await db.commit()
    return ok(_skill_dict(row), _rid(request), "admin_catalog")


@admin_router.post("/{category_id}/skills/{skill_id}/restore")
async def restore_category_skill(
    category_id: uuid.UUID, skill_id: uuid.UUID, request: Request,
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(require_super_admin),
):
    row = (await db.execute(text("""
        UPDATE category_skills SET status='active', retired_at=NULL, updated_at=now(), updated_by_user_id=:actor
         WHERE id=:id AND category_id=:cid RETURNING *
    """), {"id": str(skill_id), "cid": str(category_id), "actor": user.user_id})).first()
    if not row:
        raise ServiceOSException("SKILL_NOT_FOUND", "Skill not found in this category.", status_code=404)
    await db.commit()
    return ok(_skill_dict(row), _rid(request), "admin_catalog")


@provider_router.get("/team-skills")
async def list_provider_team_skills(
    request: Request, q: str | None = Query(None, max_length=120),
    service_group_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db), user: UserContext = Depends(get_current_user),
):
    tenant_id = _tenant_id(user)
    category_id = await resolve_team_category_id(db, tenant_id)
    where = ["cs.category_id=:cid", "cs.status='active'"]
    params: dict[str, Any] = {"cid": str(category_id)}
    if q:
        where.append("(cs.name ILIKE :q OR COALESCE(cs.description,'') ILIKE :q)")
        params["q"] = f"%{q.strip()}%"
    if service_group_id:
        where.append("(cs.service_group_id IS NULL OR cs.service_group_id=:gid)")
        params["gid"] = str(service_group_id)
    rows = (await db.execute(text(f"""
        SELECT cs.id, cs.category_id, cs.service_group_id, cs.code, cs.name, cs.description,
               cs.requires_verification, cs.display_order, sg.name AS service_group_name
          FROM category_skills cs LEFT JOIN service_groups sg ON sg.id=cs.service_group_id
         WHERE {' AND '.join(where)}
         ORDER BY COALESCE(sg.display_order,0), sg.name NULLS FIRST, cs.display_order, cs.name
    """), params)).fetchall()
    return ok({"category_id": str(category_id), "skills": [_skill_dict(row) for row in rows]},
              _rid(request), "admin_catalog", str(tenant_id))
