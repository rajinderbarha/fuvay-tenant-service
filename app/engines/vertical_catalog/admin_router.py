"""Vertical Catalog — Admin API router."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.db import get_db
from app.schemas.base import ok, ApiResponse
from app.engines.vertical_catalog.service import VerticalCatalogService

router = APIRouter(prefix="/v1/admin/verticals", tags=["admin-verticals"])
modules_router = APIRouter(prefix="/v1/admin/catalog", tags=["admin-catalog-modules"])

_svc = VerticalCatalogService()


def _rid() -> str:
    return str(uuid.uuid4())


# ── Verticals ─────────────────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse)
async def list_verticals(
    include_disabled: bool = False,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    data = await _svc.list_verticals(db, include_disabled=include_disabled)
    return ok({"items": data, "total": len(data)}, _rid())


@router.get("/{vertical_key}", response_model=ApiResponse)
async def get_vertical(
    vertical_key: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    data = await _svc.get_vertical(db, vertical_key)
    if not data:
        raise HTTPException(status_code=404, detail="Vertical not found")
    return ok(data, _rid())


@router.post("/{vertical_key}/enable", response_model=ApiResponse)
async def enable_vertical(
    vertical_key: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_ENABLE)),
):
    try:
        data = await _svc.enable_vertical(db, vertical_key, actor_id=uuid.UUID(_user.user_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


@router.get("/{vertical_key}/disable-impact", response_model=ApiResponse)
async def get_disable_impact(
    vertical_key: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    """Impact preview shown before a disable confirmation."""
    try:
        data = await _svc.disable_impact(db, vertical_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


@router.post("/{vertical_key}/disable", response_model=ApiResponse)
async def disable_vertical(
    vertical_key: str,
    payload: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_DISABLE)),
):
    try:
        data = await _svc.disable_vertical(
            db, vertical_key, actor_id=uuid.UUID(_user.user_id), reason=payload.get("reason"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


@router.patch("/{vertical_key}", response_model=ApiResponse)
async def update_vertical(
    vertical_key: str,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_UPDATE)),
):
    try:
        data = await _svc.update_vertical(db, vertical_key, payload, actor_id=uuid.UUID(_user.user_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


# ── Tenant-Vertical Enrollments ────────────────────────────────────────────────

@router.get("/{vertical_key}/enrollments", response_model=ApiResponse)
async def list_vertical_enrollments(
    vertical_key: str,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    try:
        data = await _svc.list_enrollments(db, vertical_key=vertical_key, status=status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok({"items": data, "total": len(data)}, _rid())


enrollments_router = APIRouter(prefix="/v1/admin/tenant-vertical-enrollments", tags=["admin-verticals"])


@enrollments_router.post("/{enrollment_id}/transition", response_model=ApiResponse)
async def transition_enrollment(
    enrollment_id: uuid.UUID,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_UPDATE)),
):
    """Approve / reject / request-changes / suspend / reactivate ONE tenant's
    enrollment in ONE vertical, independent of its other vertical enrollments."""
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="'status' is required")
    # "active"/"activating" are never client-requestable: reaching them
    # means every activation gate genuinely passed, which only
    # `activation.try_auto_activate` can determine. Without this guard an
    # admin could PATCH straight to "active" and mark a tenant live with
    # no service area, no payout account and no verified documents.
    from app.engines.vertical_catalog.service import CLIENT_REQUESTABLE_STATUSES
    if new_status not in CLIENT_REQUESTABLE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"'{new_status}' cannot be set directly. Activation is granted "
                "automatically once every activation requirement is met."
            ),
        )
    try:
        data = await _svc.transition_enrollment(
            db, enrollment_id, new_status,
            actor_id=uuid.UUID(_user.user_id), reason=payload.get("reason"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


@router.post("/{vertical_key}/modules/{module_key}/enable", response_model=ApiResponse)
async def enable_vertical_module(
    vertical_key: str,
    module_key: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_UPDATE)),
):
    try:
        data = await _svc.toggle_module(db, vertical_key, module_key, True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok(data, _rid())


@router.post("/{vertical_key}/modules/{module_key}/disable", response_model=ApiResponse)
async def disable_vertical_module(
    vertical_key: str,
    module_key: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_UPDATE)),
):
    try:
        data = await _svc.toggle_module(db, vertical_key, module_key, False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok(data, _rid())


# ── Engine Mappings ───────────────────────────────────────────────────────────

@router.get("/{vertical_key}/engine-mappings", response_model=ApiResponse)
async def list_engine_mappings(
    vertical_key: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    try:
        data = await _svc.list_engine_mappings(db, vertical_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok({"items": data, "total": len(data)}, _rid())


@router.put("/{vertical_key}/engine-mappings", response_model=ApiResponse)
async def set_engine_mappings(
    vertical_key: str,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_UPDATE)),
):
    try:
        data = await _svc.set_engine_mappings(db, vertical_key, payload.get("mappings", []))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok({"items": data, "total": len(data)}, _rid())


# ── Catalog Modules + Navigation ──────────────────────────────────────────────

@modules_router.get("/modules", response_model=ApiResponse)
async def list_modules(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.NAVIGATION_MENU_READ)),
):
    data = await _svc.list_modules(db)
    return ok({"items": data, "total": len(data)}, _rid())


@modules_router.get("/navigation/effective-menu", response_model=ApiResponse)
async def get_effective_menu(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.NAVIGATION_MENU_READ)),
):
    data = await _svc.get_effective_menu(db)
    return ok(data, _rid())
