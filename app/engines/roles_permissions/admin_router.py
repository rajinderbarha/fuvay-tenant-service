"""Phase 1B — Admin Roles & Permissions read API.

Backs /admin/users/roles and /admin/users/permissions. Read-only: ServiceOS
RBAC is code-defined (app/core/permissions.py), not a DB CRUD system —
mutation endpoints return 501 with a clear explanation rather than
pretending to support role editing that doesn't actually change any
enforcement behavior.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.exceptions import NotFoundException, ServiceOSException
from app.schemas.base import ApiResponse, ok
from app.engines.roles_permissions import service as svc

router = APIRouter(prefix="/v1/admin", tags=["Admin Roles & Permissions"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/roles", summary="List all roles (code-defined + gap-flagged)",
            response_model=ApiResponse[dict])
async def list_roles(r: Request, db: AsyncSession = Depends(get_db),
                      u: UserContext = Depends(require_permission(P.PLATFORM_ROLES_READ))) -> ApiResponse[dict]:
    return ok(await svc.list_roles(db), _rid(r), "roles_permissions")


@router.get("/roles/{role_id}", summary="Role detail — permissions + assigned users",
            response_model=ApiResponse[dict])
async def get_role(role_id: str, r: Request, db: AsyncSession = Depends(get_db),
                    u: UserContext = Depends(require_permission(P.PLATFORM_ROLES_READ))) -> ApiResponse[dict]:
    detail = await svc.get_role_detail(db, role_id)
    if not detail["is_implemented"] and detail["assigned_user_count"] == 0 and role_id not in svc.REQUIRED_ROLE_ORDER:
        raise NotFoundException("Role", role_id)
    return ok(detail, _rid(r), "roles_permissions")


@router.post("/roles", summary="Create role (not supported — code-defined RBAC)",
             response_model=ApiResponse[dict])
async def create_role(r: Request, u: UserContext = Depends(require_super_admin)) -> ApiResponse[dict]:
    raise ServiceOSException("NOT_IMPLEMENTED",
        "Roles are code-defined in app/core/permissions.py, not DB rows — "
        "creating a custom role requires a code change + deployment, not an API call. "
        "See PHASE_1B_ROLES_UI_REPORT.md for the architecture rationale.", status_code=501)


@router.put("/roles/{role_id}", summary="Update role (not supported — code-defined RBAC)",
            response_model=ApiResponse[dict])
async def update_role(role_id: str, r: Request,
                       u: UserContext = Depends(require_super_admin)) -> ApiResponse[dict]:
    raise ServiceOSException("NOT_IMPLEMENTED",
        "Roles are code-defined — permission sets cannot be edited via API in this version.",
        status_code=501)


@router.post("/roles/{role_id}/enable", summary="Enable role (not supported — code-defined RBAC)",
             response_model=ApiResponse[dict])
async def enable_role(role_id: str, r: Request,
                       u: UserContext = Depends(require_super_admin)) -> ApiResponse[dict]:
    raise ServiceOSException("NOT_IMPLEMENTED",
        "All code-defined roles are always active — there is no disable mechanism.",
        status_code=501)


@router.post("/roles/{role_id}/disable", summary="Disable role (not supported — code-defined RBAC)",
             response_model=ApiResponse[dict])
async def disable_role(role_id: str, r: Request,
                        u: UserContext = Depends(require_super_admin)) -> ApiResponse[dict]:
    raise ServiceOSException("NOT_IMPLEMENTED",
        "All code-defined roles are always active — there is no disable mechanism.",
        status_code=501)


# ── Permissions ──────────────────────────────────────────────────────────────

@router.get("/permissions", summary="List all permission constants",
            response_model=ApiResponse[dict])
async def list_permissions(r: Request,
                            module: str | None = Query(None),
                            app_scope: str | None = Query(None),
                            risk_level: str | None = Query(None),
                            search: str | None = Query(None),
                            u: UserContext = Depends(require_permission(P.PLATFORM_PERMISSIONS_READ))) -> ApiResponse[dict]:
    return ok(svc.list_permissions(module=module, app_scope=app_scope,
                                    risk_level=risk_level, search=search),
              _rid(r), "roles_permissions")


@router.get("/permissions/grouped", summary="Permissions grouped by module",
            response_model=ApiResponse[dict])
async def list_permissions_grouped(r: Request,
                                    app_scope: str | None = Query(None),
                                    risk_level: str | None = Query(None),
                                    u: UserContext = Depends(require_permission(P.PLATFORM_PERMISSIONS_READ))) -> ApiResponse[dict]:
    return ok(svc.list_permissions_grouped(app_scope=app_scope, risk_level=risk_level),
              _rid(r), "roles_permissions")


@router.get("/permissions/{permission_key}", summary="Permission detail",
            response_model=ApiResponse[dict])
async def get_permission(permission_key: str, r: Request,
                          u: UserContext = Depends(require_permission(P.PLATFORM_PERMISSIONS_READ))) -> ApiResponse[dict]:
    result = svc.list_permissions(search=None)
    match = next((i for i in result["items"] if i["permission_key"] == permission_key), None)
    if not match:
        raise NotFoundException("Permission", permission_key)
    return ok(match, _rid(r), "roles_permissions")
