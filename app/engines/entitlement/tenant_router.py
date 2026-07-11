"""FINAL-L5-04B — Tenant Self-Read Entitlement API.

  GET /v1/tenant/me/modules
  GET /v1/tenant/me/categories
  GET /v1/tenant/me/entitlements

Returns only the calling tenant's own effective entitlements — never
another tenant's, and never internal admin/audit fields.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_above, UserContext
from app.dependencies.db import get_db
from app.engines.entitlement.service import entitlement_service
from app.exceptions import ServiceOSException
from app.schemas.base import ok

router = APIRouter(prefix="/v1/tenant/me", tags=["Tenant Entitlements — Self Read"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _tenant_uuid(u: UserContext) -> uuid.UUID:
    if not u.tenant_id:
        raise ServiceOSException(error_code="PERMISSION_DENIED", detail="No tenant membership on this account.", status_code=403)
    return uuid.UUID(u.tenant_id)


@router.get("/modules")
async def get_my_modules(r: Request, u: UserContext = Depends(require_staff_or_above), db: AsyncSession = Depends(get_db)):
    tenant_id = _tenant_uuid(u)
    modules = await entitlement_service.get_tenant_modules(db, tenant_id, effective_only=True)
    return ok({"modules": modules}, _rid(r), "entitlement", tenant_id=str(tenant_id))


@router.get("/categories")
async def get_my_categories(r: Request, u: UserContext = Depends(require_staff_or_above), db: AsyncSession = Depends(get_db)):
    tenant_id = _tenant_uuid(u)
    categories = await entitlement_service.get_tenant_categories(db, tenant_id, effective_only=True)
    return ok({"categories": categories}, _rid(r), "entitlement", tenant_id=str(tenant_id))


@router.get("/entitlements")
async def get_my_entitlements(r: Request, u: UserContext = Depends(require_staff_or_above), db: AsyncSession = Depends(get_db)):
    tenant_id = _tenant_uuid(u)
    data = await entitlement_service.resolve_effective_entitlements(db, tenant_id)
    return ok(data, _rid(r), "entitlement", tenant_id=str(tenant_id))
