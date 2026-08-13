"""Vertical Catalog — Admin API router."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.db import get_db
from app.schemas.base import ok, ApiResponse
from app.engines.vertical_catalog.service import VerticalCatalogService
from app.engines.vertical_catalog.models import Vertical, VerticalAuditLog

router = APIRouter(prefix="/v1/admin/verticals", tags=["admin-verticals"])
modules_router = APIRouter(prefix="/v1/admin/catalog", tags=["admin-catalog-modules"])

_svc = VerticalCatalogService()


def _rid() -> str:
    return str(uuid.uuid4())


# ── Verticals ─────────────────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse)
async def list_verticals(
    include_disabled: bool = False,
    q: str | None = None,
    status: str | None = Query(None, pattern="^(enabled|disabled)$"),
    finance_model: str | None = None,
    lifecycle_status: str | None = None,
    release_stage: str | None = None,
    registration_allowed: bool | None = None,
    is_beta: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = "sort_order",
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    data = await _svc.list_verticals_directory(
        db, include_disabled=include_disabled, q=q, status=status,
        finance_model=finance_model, lifecycle_status=lifecycle_status,
        release_stage=release_stage, registration_allowed=registration_allowed,
        is_beta=is_beta, page=page, page_size=page_size, sort_by=sort_by, sort_dir=sort_dir,
    )
    return ok(data, _rid())


@router.get("/summary", response_model=ApiResponse)
async def vertical_summary(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    row = (await db.execute(select(
        func.count(Vertical.id).label("total"),
        func.count(Vertical.id).filter(Vertical.is_enabled.is_(True)).label("enabled"),
        func.count(Vertical.id).filter(Vertical.is_beta.is_(True)).label("beta"),
        func.count(Vertical.id).filter(Vertical.registration_allowed.is_(True)).label("registration_open"),
    ))).one()
    return ok({"total": int(row.total or 0), "enabled": int(row.enabled or 0),
               "disabled": int((row.total or 0) - (row.enabled or 0)), "beta": int(row.beta or 0),
               "registration_open": int(row.registration_open or 0)}, _rid())


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


@router.get("/{vertical_key}/audit", response_model=ApiResponse)
async def get_vertical_audit(
    vertical_key: str,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    """Return platform and enrollment events for one business vertical.

    This control-plane endpoint intentionally remains available while the
    vertical is disabled so administrators can investigate and restore it.
    """
    vertical = (await db.execute(
        select(Vertical).where(Vertical.key == vertical_key)
    )).scalar_one_or_none()
    if vertical is None:
        raise HTTPException(status_code=404, detail="Vertical not found")
    rows = (await db.execute(
        select(VerticalAuditLog)
        .where(VerticalAuditLog.vertical_id == vertical.id)
        .order_by(VerticalAuditLog.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return ok({"items": [row.to_dict() for row in rows], "total": len(rows)}, _rid())


@router.get("/{vertical_key}/capabilities", response_model=ApiResponse)
async def get_vertical_capabilities(
    vertical_key: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    try:
        data = await _svc.get_capability_registry(db, vertical_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(data, _rid())


@router.get("/{vertical_key}/dependency-health", response_model=ApiResponse)
async def get_vertical_dependency_health(
    vertical_key: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    try:
        data = await _svc.get_dependency_health(db, vertical_key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
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
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 10:
        raise HTTPException(status_code=422, detail="A disable reason of at least 10 characters is required")
    try:
        data = await _svc.disable_vertical(
            db, vertical_key, actor_id=uuid.UUID(_user.user_id), reason=reason,
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
    tenant_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_READ)),
):
    try:
        data = await _svc.list_enrollments(
            db, vertical_key=vertical_key, tenant_id=tenant_id, status=status,
        )
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
    # Keep the tenant connected to the scoped Admin decision. Previously a
    # vertical lifecycle transition was audited but silent, so the provider
    # had no idea why Home Services stopped or what to correct.
    notification_copy = {
        "changes_requested": (
            "Changes requested for Home Services",
            f"Please review and correct your Home Services setup: {payload.get('reason') or 'Changes are required.'}",
            "warning",
        ),
        "suspended": (
            "Home Services enrollment suspended",
            f"Your Home Services enrollment has been suspended: {payload.get('reason') or 'Contact support for details.'}",
            "danger",
        ),
        "approved_pending_activation": (
            "Home Services enrollment resumed",
            f"Your Home Services enrollment has returned to activation review: {payload.get('reason') or 'The suspension was lifted.'}",
            "info",
        ),
    }.get(new_status)
    if notification_copy:
        try:
            from app.engines.tenant_engine.notifications import notify_tenant_verification
            title, body, severity = notification_copy
            await notify_tenant_verification(
                db, uuid.UUID(str(data["tenant_id"])),
                notification_type=f"tenant.vertical.home_services.{new_status}",
                title=title, body=body, severity=severity,
            )
            await db.commit()
        except Exception:
            # The lifecycle decision is authoritative and already committed;
            # notification delivery is best-effort and must not roll it back.
            await db.rollback()
    return ok(data, _rid())


@router.post("/{vertical_key}/modules/{module_key}/enable", response_model=ApiResponse)
async def enable_vertical_module(
    vertical_key: str,
    module_key: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_UPDATE)),
):
    try:
        data = await _svc.toggle_module(
            db, vertical_key, module_key, True, actor_id=uuid.UUID(_user.user_id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok(data, _rid())


@router.post("/{vertical_key}/modules/{module_key}/disable", response_model=ApiResponse)
async def disable_vertical_module(
    vertical_key: str,
    module_key: str,
    payload: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission(P.VERTICALS_UPDATE)),
):
    reason = str(payload.get("reason") or "").strip()
    if len(reason) < 10:
        raise HTTPException(status_code=422, detail="A disable reason of at least 10 characters is required")
    try:
        data = await _svc.toggle_module(
            db, vertical_key, module_key, False,
            actor_id=uuid.UUID(_user.user_id), reason=reason,
        )
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
