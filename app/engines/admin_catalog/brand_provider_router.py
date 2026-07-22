"""Sprint 34D — Brand Provider Router.

Provider (tenant) brand management endpoints.
Prefix: /v1/provider/brands
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, require_technician
from app.dependencies.db import get_db
from app.core.permissions import require_staff_or_above_mutation
from app.engines.admin_catalog.brand_service import BrandService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/provider/brands", tags=["Provider Brands"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(require_technician),
) -> BrandService:
    actor_id = uuid.UUID(u.user_id) if u.user_id else None
    tenant_id = uuid.UUID(u.tenant_id) if getattr(u, "tenant_id", None) else None
    return BrandService(db=db, actor_id=actor_id, actor_role=u.role,
                        request_id=_rid(r), tenant_id=tenant_id)


@router.get(
    "/services/{service_id}/available",
    response_model=ApiResponse[dict],
    summary="List admin-approved brands available for a service (provider selects from these)",
)
async def get_available_brands(
    service_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_technician),
    s: BrandService = Depends(_svc),
):
    return ok(await s.get_available_brands_for_service(service_id), _rid(r))


@router.get(
    "/categories/{category_id}/available",
    response_model=ApiResponse[dict],
    summary="List admin-approved brands available for a category (used by offerings view)",
)
async def get_available_brands_for_category(
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_technician),
    s: BrandService = Depends(_svc),
):
    return ok(await s.get_available_brands_for_category(category_id), _rid(r))


@router.get(
    "/services/{service_id}/supported",
    response_model=ApiResponse[dict],
    summary="Get brands this provider supports for a service",
)
async def get_supported_brands(
    service_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_technician),
    s: BrandService = Depends(_svc),
):
    return ok(await s.get_provider_supported_brands(service_id), _rid(r))


@router.post(
    "/services/{service_id}/supported",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Set brands this provider supports for a service",
    description=(
        "Replaces the provider's current brand selection for this service. "
        "Only brands admin has mapped to the service are accepted. "
        "Passing an empty list removes all supported brands."
    ),
)
async def set_supported_brands(
    service_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_staff_or_above_mutation),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    brand_ids: list[str] = body.get("brand_ids", [])
    support_level: str | None = body.get("support_level")
    return ok(await s.set_provider_supported_brands(service_id, brand_ids, support_level), _rid(r))


@router.post(
    "/requests",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Submit a brand request (provider requests missing brand)",
)
async def create_brand_request(
    r: Request,
    u: UserContext = Depends(require_staff_or_above_mutation),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    return ok(await s.create_brand_request(body), _rid(r))


@router.get(
    "/requests",
    response_model=ApiResponse[dict],
    summary="List provider's own brand requests",
)
async def list_my_brand_requests(
    r: Request,
    u: UserContext = Depends(require_technician),
    s: BrandService = Depends(_svc),
):
    tenant_id = uuid.UUID(u.tenant_id) if getattr(u, "tenant_id", None) else None
    return ok(await s.list_brand_requests(tenant_id=tenant_id), _rid(r))
