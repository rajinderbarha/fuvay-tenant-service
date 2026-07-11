"""FINAL-L5-04B — Admin Entitlement API.

  GET    /v1/admin/tenants/{tenant_id}/entitlements                — modules + categories
  POST   /v1/admin/tenants/{tenant_id}/entitlements/modules         — assign module
  POST   /v1/admin/tenants/{tenant_id}/entitlements/modules/{key}/disable
  POST   /v1/admin/tenants/{tenant_id}/entitlements/modules/{key}/reenable
  POST   /v1/admin/tenants/{tenant_id}/entitlements/categories      — assign category
  POST   /v1/admin/tenants/{tenant_id}/entitlements/categories/{category_id}/disable
  POST   /v1/admin/tenants/{tenant_id}/entitlements/categories/{category_id}/reenable
  GET    /v1/admin/tenants/{tenant_id}/entitlements/history         — audit history
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin, UserContext
from app.dependencies.db import get_db
from app.engines.entitlement.service import (
    EntitlementConflictError,
    EntitlementNotFoundError,
    entitlement_service,
)
from app.engines.tenant_engine.models import Tenant
from app.exceptions import ServiceOSException
from app.schemas.base import ok

router = APIRouter(prefix="/v1/admin/tenants/{tenant_id}/entitlements", tags=["Tenant Entitlements — Admin"])


class AssignModuleBody(BaseModel):
    module_key: str
    configuration: dict | None = None


class AssignCategoryBody(BaseModel):
    category_id: uuid.UUID
    configuration: dict | None = None


class DisableBody(BaseModel):
    reason: str | None = None


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


async def _require_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    t = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not t:
        raise ServiceOSException(error_code="NOT_FOUND", detail=f"Tenant '{tenant_id}' not found.", status_code=404)


@router.get("")
async def get_tenant_entitlements(
    tenant_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    await _require_tenant(db, tenant_id)
    # Admins must see disabled/inactive rows too (not just effective ones) —
    # otherwise there is no way to find and re-enable something that was
    # disabled, since it would simply vanish from this list.
    data = await entitlement_service.resolve_effective_entitlements(db, tenant_id, effective_only=False)
    return ok(data, _rid(r), "entitlement")


@router.get("/history")
async def get_tenant_entitlement_history(
    tenant_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    await _require_tenant(db, tenant_id)
    data = await entitlement_service.get_history(db, tenant_id)
    return ok({"history": data}, _rid(r), "entitlement")


@router.post("/modules")
async def assign_module(
    tenant_id: uuid.UUID, body: AssignModuleBody, r: Request,
    u: UserContext = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    await _require_tenant(db, tenant_id)
    try:
        data = await entitlement_service.assign_module_entitlement(
            db, tenant_id=tenant_id, module_key=body.module_key,
            actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
            request_id=_rid(r), configuration=body.configuration,
        )
    except EntitlementNotFoundError as e:
        raise ServiceOSException(error_code="NOT_FOUND", detail=str(e), status_code=404)
    return ok({"assigned": True, "module": data}, _rid(r), "entitlement")


@router.post("/modules/{module_key}/disable")
async def disable_module(
    tenant_id: uuid.UUID, module_key: str, body: DisableBody, r: Request,
    u: UserContext = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    await _require_tenant(db, tenant_id)
    try:
        data = await entitlement_service.disable_module_entitlement(
            db, tenant_id=tenant_id, module_key=module_key,
            actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
            reason=body.reason, request_id=_rid(r),
        )
    except EntitlementNotFoundError as e:
        raise ServiceOSException(error_code="NOT_FOUND", detail=str(e), status_code=404)
    return ok({"disabled": True, "module": data}, _rid(r), "entitlement")


@router.post("/modules/{module_key}/reenable")
async def reenable_module(
    tenant_id: uuid.UUID, module_key: str, r: Request,
    u: UserContext = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    await _require_tenant(db, tenant_id)
    try:
        data = await entitlement_service.reenable_module_entitlement(
            db, tenant_id=tenant_id, module_key=module_key,
            actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role, request_id=_rid(r),
        )
    except EntitlementNotFoundError as e:
        raise ServiceOSException(error_code="NOT_FOUND", detail=str(e), status_code=404)
    return ok({"reenabled": True, "module": data}, _rid(r), "entitlement")


@router.post("/categories")
async def assign_category(
    tenant_id: uuid.UUID, body: AssignCategoryBody, r: Request,
    u: UserContext = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    await _require_tenant(db, tenant_id)
    try:
        data = await entitlement_service.assign_category_entitlement(
            db, tenant_id=tenant_id, category_id=body.category_id,
            actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
            request_id=_rid(r), configuration=body.configuration,
        )
    except EntitlementNotFoundError as e:
        raise ServiceOSException(error_code="NOT_FOUND", detail=str(e), status_code=404)
    except EntitlementConflictError as e:
        raise ServiceOSException(error_code="CONFLICT", detail=str(e), status_code=409)
    return ok({"assigned": True, "category": data}, _rid(r), "entitlement")


@router.post("/categories/{category_id}/disable")
async def disable_category(
    tenant_id: uuid.UUID, category_id: uuid.UUID, body: DisableBody, r: Request,
    u: UserContext = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    await _require_tenant(db, tenant_id)
    try:
        data = await entitlement_service.disable_category_entitlement(
            db, tenant_id=tenant_id, category_id=category_id,
            actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
            reason=body.reason, request_id=_rid(r),
        )
    except EntitlementNotFoundError as e:
        raise ServiceOSException(error_code="NOT_FOUND", detail=str(e), status_code=404)
    return ok({"disabled": True, "category": data}, _rid(r), "entitlement")


@router.post("/categories/{category_id}/reenable")
async def reenable_category(
    tenant_id: uuid.UUID, category_id: uuid.UUID, r: Request,
    u: UserContext = Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    await _require_tenant(db, tenant_id)
    try:
        data = await entitlement_service.reenable_category_entitlement(
            db, tenant_id=tenant_id, category_id=category_id,
            actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role, request_id=_rid(r),
        )
    except EntitlementNotFoundError as e:
        raise ServiceOSException(error_code="NOT_FOUND", detail=str(e), status_code=404)
    except EntitlementConflictError as e:
        raise ServiceOSException(error_code="CONFLICT", detail=str(e), status_code=409)
    return ok({"reenabled": True, "category": data}, _rid(r), "entitlement")
