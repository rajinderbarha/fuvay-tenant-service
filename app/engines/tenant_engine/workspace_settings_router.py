"""Home Services Workspace Settings — tenant-facing router.

Real bug fixed here: `WorkspaceSettingsService` (workspace_settings_service.py)
was fully written -- get_general/update_general/get_team_access/get_activity,
all reading real Tenant/TenantSettings/provider_availability_rules/
platform_audit_logs data with an explicit TENANT_CONTROLLED/SERVICEOS_
CONTROLLED/ADMIN_POLICY ownership tag per field -- but no router ever called
it, so the whole feature was unreachable from any URL.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.tenant_engine.workspace_settings_service import WorkspaceSettingsService
from app.schemas.base import ok

router = APIRouter(prefix="/v1/tenant/home-services/workspace-settings", tags=["Tenant Workspace Settings"])
ENGINE_ID = "workspace_settings"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(db: AsyncSession = Depends(get_db), u: UserContext = Depends(get_current_user)) -> WorkspaceSettingsService:
    return WorkspaceSettingsService(db=db, actor=u)


@router.get("/general")
async def get_general(r: Request, s: WorkspaceSettingsService = Depends(_svc)):
    return ok(await s.get_general(), _rid(r), ENGINE_ID)


@router.put("/general")
async def update_general(
    r: Request,
    payload: dict = Body(...),
    expected_version: str | None = Body(None),
    s: WorkspaceSettingsService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
):
    data = await s.update_general(payload, expected_version)
    await db.commit()
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/team-access")
async def get_team_access(r: Request, s: WorkspaceSettingsService = Depends(_svc)):
    return ok(await s.get_team_access(), _rid(r), ENGINE_ID)


@router.get("/activity")
async def get_activity(r: Request, limit: int = Query(30, ge=1, le=100), s: WorkspaceSettingsService = Depends(_svc)):
    return ok(await s.get_activity(limit=limit), _rid(r), ENGINE_ID)
