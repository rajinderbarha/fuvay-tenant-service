"""Settings Engine — Router (16 endpoints). Zero inline imports."""
import uuid
from typing import Any
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.core.security import get_client_ip
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.settings_engine.service import SettingsService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("settings.router")
router = APIRouter(prefix="/v1/settings", tags=["Settings Engine"])
ENGINE_ID = "settings"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> SettingsService:
    return SettingsService(db=db, request_id=getattr(r.state,"request_id","—"),
                            actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                            actor_role=u.role,
                            actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)
def _rid(r): return getattr(r.state,"request_id","—")


@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Settings Engine", "version": "5.0.0",
            "endpoint_count": 16, "status": "active",
            "capabilities": ["platform_settings","plan_settings","tenant_settings",
                             "resolution_chain","audit_log","bulk_set"]}

# Platform settings
@router.get("/platform", response_model=ApiResponse[dict])
async def list_platform(r: Request, limit: int = Query(50,ge=1,le=200),
                         cursor: str|None = Query(None),
                         u: UserContext = Depends(get_current_user),
                         s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_platform_settings(limit, cursor), _rid(r), ENGINE_ID)

@router.get("/platform/{key}", response_model=ApiResponse[dict])
async def get_platform(key: str, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_platform_setting(key), _rid(r), ENGINE_ID)

@router.put("/platform/{key}", response_model=ApiResponse[dict])
async def set_platform(key: str, r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.set_platform_setting(key, body["value"],
              body.get("type","string"), body.get("description")), _rid(r), ENGINE_ID)

@router.delete("/platform/{key}", response_model=ApiResponse[dict])
async def delete_platform(key: str, r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_platform_setting(key), _rid(r), ENGINE_ID)

@router.post("/platform/bulk", response_model=ApiResponse[dict])
async def bulk_set_platform(r: Request,
                             u: UserContext = Depends(require_super_admin),
                             s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.bulk_set_platform(body.get("settings",[])), _rid(r), ENGINE_ID)

# Plan settings
@router.get("/plans/{plan_type}", response_model=ApiResponse[dict])
async def list_plan(plan_type: str, r: Request,
                     u: UserContext = Depends(get_current_user),
                     s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_plan_settings(plan_type), _rid(r), ENGINE_ID)

@router.put("/plans/{plan_type}/{key}", response_model=ApiResponse[dict])
async def set_plan(plan_type: str, key: str, r: Request,
                    u: UserContext = Depends(require_super_admin),
                    s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.set_plan_setting(plan_type, key, body["value"],
              body.get("type","string")), _rid(r), ENGINE_ID)

@router.delete("/plans/{plan_type}/{key}", response_model=ApiResponse[dict])
async def delete_plan(plan_type: str, key: str, r: Request,
                       u: UserContext = Depends(require_super_admin),
                       s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_plan_setting(plan_type, key), _rid(r), ENGINE_ID)

# Tenant settings
@router.get("/tenants/{tenant_id}", response_model=ApiResponse[dict])
async def list_tenant(tenant_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(get_current_user),
                       s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_tenant_settings(tenant_id), _rid(r), ENGINE_ID)

@router.put("/tenants/{tenant_id}/{key}", response_model=ApiResponse[dict])
async def set_tenant(tenant_id: uuid.UUID, key: str, r: Request,
                      u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                      s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.set_tenant_setting(tenant_id, key, body["value"],
              body.get("type","string"), body.get("reason")), _rid(r), ENGINE_ID)

@router.delete("/tenants/{tenant_id}/{key}", response_model=ApiResponse[dict])
async def delete_tenant(tenant_id: uuid.UUID, key: str, r: Request,
                         u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                         s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_tenant_setting(tenant_id, key), _rid(r), ENGINE_ID)

# Resolve
@router.get("/resolve/{key}", response_model=ApiResponse[dict])
async def resolve(key: str, r: Request,
                   tenant_id: uuid.UUID|None = Query(None),
                   plan_type: str|None = Query(None),
                   u: UserContext = Depends(get_current_user),
                   s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.resolve_setting(key, tenant_id, plan_type), _rid(r), ENGINE_ID)

# Audit log
@router.get("/audit-log", response_model=ApiResponse[dict])
async def audit_log(r: Request,
                     tenant_id: uuid.UUID|None = Query(None),
                     key: str|None = Query(None),
                     limit: int = Query(50,ge=1,le=200),
                     cursor: str|None = Query(None),
                     u: UserContext = Depends(get_current_user),
                     s: SettingsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_audit_log(tenant_id, key, limit, cursor), _rid(r), ENGINE_ID)
