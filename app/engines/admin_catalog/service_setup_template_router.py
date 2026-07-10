"""Sprint 34F — Admin + Provider routers for Service Setup Templates."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.auth import UserContext, require_super_admin, require_technician
from app.engines.admin_catalog.service_setup_template_service import ServiceSetupTemplateService

admin_router = APIRouter(prefix="/v1/admin/service-setup-templates", tags=["Admin Setup Templates"])
provider_router = APIRouter(prefix="/v1/provider/setup/templates", tags=["Provider Setup Templates"])


def _svc(r: Request, db: AsyncSession, u: UserContext) -> ServiceSetupTemplateService:
    return ServiceSetupTemplateService(
        db=db,
        actor_id=uuid.UUID(u.user_id) if u.user_id else uuid.uuid4(),
        actor_role=u.role,
        request_id=getattr(r.state, "request_id", str(uuid.uuid4())),
    )


# ── Admin — Templates CRUD + Lifecycle ───────────────────────────────────────

@admin_router.get("")
async def list_templates(
    r: Request,
    status: str | None = Query(None),
    vertical_type: str | None = Query(None),
    template_type: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).list_templates(
        status=status, vertical_type=vertical_type,
        template_type=template_type, search=search,
        page=page, page_size=page_size,
    )


@admin_router.post("")
async def create_template(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).create_template(body)


@admin_router.get("/{template_id}")
async def get_template(
    r: Request,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    t = await _svc(r, db, u).get_template(template_id)
    return t.to_dict()


@admin_router.put("/{template_id}")
async def update_template(
    r: Request,
    template_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).update_template(template_id, body)


@admin_router.post("/{template_id}/publish")
async def publish_template(
    r: Request,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).publish_template(template_id)


@admin_router.post("/{template_id}/archive")
async def archive_template(
    r: Request,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).archive_template(template_id)


@admin_router.delete("/{template_id}")
async def delete_template(
    r: Request,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).delete_template(template_id)


# ── Admin — Template Items ────────────────────────────────────────────────────

@admin_router.get("/{template_id}/items")
async def list_items(
    r: Request,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).list_items(template_id)


@admin_router.post("/{template_id}/items")
async def add_item(
    r: Request,
    template_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).add_item(template_id, body)


@admin_router.put("/{template_id}/items/{item_id}")
async def update_item(
    r: Request,
    template_id: uuid.UUID,
    item_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).update_item(template_id, item_id, body)


@admin_router.delete("/{template_id}/items/{item_id}")
async def remove_item(
    r: Request,
    template_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).remove_item(template_id, item_id)


# ── Admin — Relationships ─────────────────────────────────────────────────────

@admin_router.get("/{template_id}/relationships")
async def list_relationships(
    r: Request,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).list_relationships(template_id)


@admin_router.post("/{template_id}/relationships")
async def add_relationship(
    r: Request,
    template_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).add_relationship(template_id, body)


@admin_router.delete("/{template_id}/relationships/{rel_id}")
async def remove_relationship(
    r: Request,
    template_id: uuid.UUID,
    rel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).remove_relationship(template_id, rel_id)


# ── Admin — Preview + Apply ───────────────────────────────────────────────────

@admin_router.post("/{template_id}/preview")
async def preview_template(
    r: Request,
    template_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).preview_template(template_id, body)


@admin_router.post("/{template_id}/apply")
async def apply_template(
    r: Request,
    template_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).apply_template(template_id, body)


# ── Admin — Runs ──────────────────────────────────────────────────────────────

@admin_router.get("/{template_id}/runs")
async def list_runs(
    r: Request,
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).list_runs(template_id)


@admin_router.get("/runs/{run_id}")
async def get_run_detail(
    r: Request,
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_super_admin),
):
    return await _svc(r, db, u).get_run_detail(run_id)


# ── Provider — Recommendations ────────────────────────────────────────────────

@provider_router.get("/recommended")
async def get_recommended_templates(
    r: Request,
    vertical_type: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_technician),
):
    svc = ServiceSetupTemplateService(
        db=db,
        actor_id=uuid.UUID(u.user_id) if u.user_id else uuid.uuid4(),
        actor_role=u.role,
        request_id=getattr(r.state, "request_id", str(uuid.uuid4())),
    )
    return await svc.get_recommended_templates(
        vertical_type=vertical_type,
        category_id=category_id,
    )
