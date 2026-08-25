"""Service Setup Templates — Admin Router."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.db import get_db
from app.schemas.base import ok, ApiResponse
from app.engines.service_setup.templates_service import SetupTemplatesService

router = APIRouter(prefix="/v1/admin/service-setup/templates", tags=["admin-setup-templates"])

_svc = SetupTemplatesService()


def _rid() -> str:
    return str(uuid.uuid4())


# ── Fixed-path endpoints FIRST (before /{template_id}) ───────────────────────

@router.get("/summary", response_model=ApiResponse, operation_id="enterprise_setup_templates_summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_READ)),
):
    data = await _svc.get_summary(db)
    return ok(data, _rid())


@router.post("/seed-defaults/preview", response_model=ApiResponse, operation_id="enterprise_setup_templates_seed_preview")
async def seed_defaults_preview(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_WRITE)),
):
    data = await _svc.seed_defaults_preview(db)
    return ok(data, _rid())


@router.post("/seed-defaults", response_model=ApiResponse, operation_id="enterprise_setup_templates_seed")
async def seed_defaults(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_WRITE)),
):
    data = await _svc.seed_defaults(db, None)
    return ok(data, _rid())


# ── List + Create ─────────────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse, operation_id="enterprise_setup_templates_list")
async def list_templates(
    q: Optional[str] = Query(None),
    vertical: Optional[str] = Query(None),
    template_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_system: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_READ)),
):
    data = await _svc.list_templates(
        db, q=q, vertical=vertical, template_type=template_type,
        status=status, is_system=is_system,
        page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir,
    )
    return ok(data, _rid())


@router.post("", response_model=ApiResponse, operation_id="enterprise_setup_templates_create")
async def create_template(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_WRITE)),
):
    try:
        data = await _svc.create_template(db, payload, None)
        return ok(data, _rid())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Per-template endpoints ────────────────────────────────────────────────────

@router.get("/{template_id}", response_model=ApiResponse, operation_id="enterprise_setup_templates_get")
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_READ)),
):
    try:
        data = await _svc.get_template(db, template_id)
        return ok(data, _rid())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{template_id}", response_model=ApiResponse, operation_id="enterprise_setup_templates_update")
async def update_template(
    template_id: str,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_WRITE)),
):
    try:
        data = await _svc.update_template(db, template_id, payload)
        return ok(data, _rid())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/publish", response_model=ApiResponse, operation_id="enterprise_setup_templates_publish")
async def publish_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_PUBLISH)),
):
    try:
        data = await _svc.publish_template(db, template_id)
        return ok(data, _rid())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/archive", response_model=ApiResponse, operation_id="enterprise_setup_templates_archive")
async def archive_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_WRITE)),
):
    try:
        data = await _svc.archive_template(db, template_id)
        return ok(data, _rid())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/clone", response_model=ApiResponse, operation_id="enterprise_setup_templates_clone")
async def clone_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_WRITE)),
):
    try:
        data = await _svc.clone_template(db, template_id, None)
        return ok(data, _rid())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{template_id}", response_model=ApiResponse, operation_id="enterprise_setup_templates_delete")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_WRITE)),
):
    try:
        await _svc.delete_template(db, template_id)
        return ok({"deleted": True}, _rid())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/validate", response_model=ApiResponse, operation_id="enterprise_setup_templates_validate")
async def validate_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_READ)),
):
    try:
        data = await _svc.validate_template(db, template_id)
        return ok(data, _rid())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{template_id}/versions", response_model=ApiResponse, operation_id="enterprise_setup_templates_versions")
async def get_versions(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.SETUP_TEMPLATES_READ)),
):
    try:
        data = await _svc.get_versions(db, template_id)
        return ok(data, _rid())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
