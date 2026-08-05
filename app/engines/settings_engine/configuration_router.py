"""CONFIGURATION-REGISTRY-REBUILD: Platform Configuration admin API.

Mounted at /v1/admin/configuration. Every mutation requires a registered
ConfigurationDefinition (registry.py) -- there is no create-arbitrary-key
route here, unlike the legacy /v1/admin/settings POST "" route.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.db import get_db
from app.dependencies.auth import UserContext
from app.schemas.base import ok
from app.engines.settings_engine.registry import ConfigurationRegistry
from app.engines.settings_engine.configuration_service import ConfigurationService
from app.engines.settings_engine.models import SettingAuditLog
from sqlalchemy import select, func

router = APIRouter(prefix="/v1/admin/configuration", tags=["Platform Configuration"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(r: Request, db: AsyncSession, u: UserContext) -> ConfigurationService:
    return ConfigurationService(db, request_id=_rid(r),
                                actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                                actor_role=u.role)


@router.get("", summary="Configuration Registry directory + summary")
async def list_configuration(
    r: Request,
    owner_module: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    u: UserContext = Depends(require_permission(P.CONFIGURATION_READ)),
    db: AsyncSession = Depends(get_db),
):
    svc = _svc(r, db, u)
    defs = ConfigurationRegistry.all()
    rows = []
    active = pending_approval = needs_review = invalid = 0
    vertical_overrides = 0
    for d in defs.values():
        if owner_module and d.owner_module != owner_module:
            continue
        if risk_level and d.risk_level != risk_level:
            continue
        if scope and scope not in d.allowed_scopes:
            continue
        if search and search.lower() not in d.label.lower() and search.lower() not in d.key.lower():
            continue

        resolved = await svc.resolve_effective_value(d.key)
        status = "Code-Controlled Locked" if d.locked else ("Active" if resolved["source"] != "code_default" else "Needs Review")
        if d.locked:
            pass
        elif resolved["source"] != "code_default":
            active += 1
        else:
            needs_review += 1

        history = await svc.list_history(d.key)
        if any(h["status"] == "pending_approval" for h in history):
            pending_approval += 1
        if any(h["scope_type"] == "vertical" for h in history):
            vertical_overrides += 1

        rows.append({
            "key": d.key, "label": d.label, "owner_module": d.owner_module,
            "data_type": d.data_type, "allowed_scopes": d.allowed_scopes,
            "risk_level": d.risk_level, "locked": d.locked, "admin_mutable": d.admin_mutable,
            "effective_value": resolved["effective_value"], "source": resolved["source"],
            "status": status, "version": resolved["value_version"],
            "has_real_consumer": d.has_real_consumer,
        })

    return ok({
        "items": rows,
        "summary": {
            "registered_settings": len(defs), "active": active,
            "pending_approval": pending_approval, "needs_review": needs_review,
            "vertical_overrides": vertical_overrides, "invalid": invalid,
            "rollback_available": sum(1 for d in defs.values() if d.rollback_supported and not d.locked),
        },
    }, _rid(r), "configuration")


@router.get("/change-requests", summary="Cross-setting change-request queue")
async def list_change_requests(
    r: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    u: UserContext = Depends(require_permission(P.CONFIGURATION_READ)),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.settings_engine.models import ConfigurationValueVersion
    q = select(ConfigurationValueVersion)
    if status_filter:
        q = q.where(ConfigurationValueVersion.status == status_filter)
    else:
        q = q.where(ConfigurationValueVersion.status.in_(
            ["draft", "pending_approval", "scheduled", "approved"]))
    rows = (await db.execute(q.order_by(ConfigurationValueVersion.created_at.desc()).limit(limit))).scalars().all()
    items = []
    for row in rows:
        d = ConfigurationRegistry.get(row.setting_key)
        items.append({**row.to_dict(), "label": d.label if d else row.setting_key,
                     "risk_level": d.risk_level if d else None})
    return ok({"items": items}, _rid(r), "configuration")


@router.get("/version-history", summary="Cross-setting recent version history")
async def list_version_history(
    r: Request,
    limit: int = Query(50, ge=1, le=200),
    u: UserContext = Depends(require_permission(P.CONFIGURATION_READ)),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.settings_engine.models import ConfigurationValueVersion
    rows = (await db.execute(select(ConfigurationValueVersion)
            .order_by(ConfigurationValueVersion.created_at.desc()).limit(limit))).scalars().all()
    items = []
    for row in rows:
        d = ConfigurationRegistry.get(row.setting_key)
        items.append({**row.to_dict(), "label": d.label if d else row.setting_key})
    return ok({"items": items}, _rid(r), "configuration")


@router.get("/{key}/detail", summary="Setting detail inspector")
async def get_configuration_detail(
    key: str, r: Request,
    vertical_key: Optional[str] = Query(None),
    u: UserContext = Depends(require_permission(P.CONFIGURATION_READ)),
    db: AsyncSession = Depends(get_db),
):
    svc = _svc(r, db, u)
    d = svc._definition(key)
    resolved = await svc.resolve_effective_value(key, vertical_key=vertical_key)
    history = await svc.list_history(key, "vertical" if vertical_key else "global", vertical_key)
    return ok({
        "key": d.key, "label": d.label, "description": d.description, "owner_module": d.owner_module,
        "data_type": d.data_type, "allowed_scopes": d.allowed_scopes, "unit": d.unit,
        "minimum": d.minimum, "maximum": d.maximum, "enum_values": d.enum_values,
        "risk_level": d.risk_level, "admin_mutable": d.admin_mutable, "locked": d.locked,
        "approval_required": d.approval_required, "restart_required": d.restart_required,
        "snapshot_behavior": d.snapshot_behavior, "rollback_supported": d.rollback_supported,
        "deprecated": d.deprecated, "sensitivity": d.sensitivity,
        "has_real_consumer": d.has_real_consumer, "consumer_note": d.consumer_note,
        "effective": resolved, "history": history,
    }, _rid(r), "configuration")


@router.get("/{key}/history", summary="Version history")
async def get_configuration_history(
    key: str, r: Request,
    scope_type: str = Query("global"),
    scope_id: Optional[str] = Query(None),
    u: UserContext = Depends(require_permission(P.CONFIGURATION_READ)),
    db: AsyncSession = Depends(get_db),
):
    svc = _svc(r, db, u)
    return ok({"items": await svc.list_history(key, scope_type, scope_id)}, _rid(r), "configuration")


class ValidateIn(BaseModel):
    key: str
    scope_type: str = "global"
    value: object


@router.post("/validate", summary="Validate a candidate value without saving")
async def validate_configuration(
    body: ValidateIn, r: Request,
    u: UserContext = Depends(require_permission(P.CONFIGURATION_CHANGE_REQUEST_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    svc = _svc(r, db, u)
    return ok(svc.validate(body.key, body.scope_type, body.value), _rid(r), "configuration")


class ChangeRequestIn(BaseModel):
    scope_type: str = "global"
    scope_id: Optional[str] = None
    value: object
    reason: str


@router.post("/{key}/change-request", summary="Create a configuration change request (draft)")
async def create_change_request(
    key: str, body: ChangeRequestIn, r: Request,
    u: UserContext = Depends(require_permission(P.CONFIGURATION_CHANGE_REQUEST_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    svc = _svc(r, db, u)
    data = await svc.create_change_request(
        key, body.scope_type, body.scope_id, body.value,
        reason=body.reason, actor_id=uuid.UUID(u.user_id) if u.user_id else None,
    )
    return ok(data, _rid(r), "configuration")


@router.post("/change-requests/{version_id}/approve", summary="Approve a pending change request")
async def approve_change_request(
    version_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.CONFIGURATION_APPROVE)),
    db: AsyncSession = Depends(get_db),
):
    svc = _svc(r, db, u)
    data = await svc.approve(version_id, actor_id=uuid.UUID(u.user_id) if u.user_id else None)
    return ok(data, _rid(r), "configuration")


@router.post("/change-requests/{version_id}/activate", summary="Activate an approved change request")
async def activate_change_request(
    version_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_permission(P.CONFIGURATION_ACTIVATE)),
    db: AsyncSession = Depends(get_db),
):
    svc = _svc(r, db, u)
    data = await svc.activate(version_id, actor_id=uuid.UUID(u.user_id) if u.user_id else None)
    return ok(data, _rid(r), "configuration")


class RollbackIn(BaseModel):
    reason: str


@router.post("/change-requests/{version_id}/rollback", summary="Roll back an active version")
async def rollback_change_request(
    version_id: uuid.UUID, body: RollbackIn, r: Request,
    u: UserContext = Depends(require_permission(P.CONFIGURATION_ROLLBACK)),
    db: AsyncSession = Depends(get_db),
):
    svc = _svc(r, db, u)
    data = await svc.rollback(version_id, actor_id=uuid.UUID(u.user_id) if u.user_id else None, reason=body.reason)
    return ok(data, _rid(r), "configuration")


@router.get("/audit/log", summary="Configuration audit trail")
async def get_configuration_audit(
    r: Request,
    key: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    u: UserContext = Depends(require_permission(P.CONFIGURATION_AUDIT_READ)),
    db: AsyncSession = Depends(get_db),
):
    q = select(SettingAuditLog).where(
        SettingAuditLog.action_type.like("change_request.%"))
    if key:
        q = q.where(SettingAuditLog.key == key)
    rows = (await db.execute(q.order_by(SettingAuditLog.created_at.desc()).limit(limit))).scalars().all()
    return ok({"items": [{
        "id": str(x.id), "key": x.key, "tier": x.tier, "action_type": x.action_type,
        "old_value": x.old_value.get("v") if x.old_value else None,
        "new_value": x.new_value.get("v") if x.new_value else None,
        "changed_by": str(x.changed_by) if x.changed_by else None,
        "reason": x.reason, "created_at": x.created_at.isoformat() if x.created_at else None,
    } for x in rows]}, _rid(r), "configuration")
