"""Sprint 34D — Provider Brand Router.
Providers can: view available brands per service, select which they support,
and submit brand requests.
All endpoints require tenant authentication.
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_tenant, TenantContext
from app.dependencies.db import get_db
from app.engines.brands.service import BrandService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/provider", tags=["Provider Brand Setup"])


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         t: TenantContext = Depends(require_tenant)) -> BrandService:
    return BrandService(
        db=db,
        actor_id=uuid.UUID(t.user_id) if t.user_id else None,
        actor_role="provider",
        request_id=getattr(r.state, "request_id", "—"),
    )


def _rid(r): return getattr(r.state, "request_id", "—")


@router.get("/setup/services/{service_id}/available-brands",
            response_model=ApiResponse[dict],
            summary="List admin-approved brands available for a service")
async def list_available_brands(
    r: Request,
    service_id: uuid.UUID,
    t: TenantContext = Depends(require_tenant),
    s: BrandService = Depends(_svc),
):
    tenant_id = uuid.UUID(t.tenant_id) if t.tenant_id else None
    return ok(
        await s.list_available_brands_for_service(service_id, tenant_id=tenant_id),
        _rid(r), "brands"
    )


@router.get("/setup/services/{service_id}/supported-brands",
            response_model=ApiResponse[dict],
            summary="Get brands provider currently supports for a service")
async def get_supported_brands(
    r: Request,
    service_id: uuid.UUID,
    t: TenantContext = Depends(require_tenant),
    s: BrandService = Depends(_svc),
):
    tenant_id = uuid.UUID(t.tenant_id)
    return ok(
        await s.list_provider_supported_brands(tenant_id, service_id),
        _rid(r), "brands"
    )


@router.post("/setup/services/{service_id}/supported-brands",
             response_model=ApiResponse[dict],
             summary="Set brands provider supports for a service")
async def set_supported_brands(
    r: Request,
    service_id: uuid.UUID,
    body: dict = Body(...),
    t: TenantContext = Depends(require_tenant),
    s: BrandService = Depends(_svc),
):
    tenant_id = uuid.UUID(t.tenant_id)
    brand_ids = body.get("brand_ids") or []
    return ok(
        await s.set_provider_supported_brands(tenant_id, service_id, brand_ids),
        _rid(r), "brands"
    )


@router.post("/brand-requests",
             response_model=ApiResponse[dict],
             summary="Provider submits a brand request",
             status_code=201)
async def create_brand_request(
    r: Request,
    body: dict = Body(...),
    t: TenantContext = Depends(require_tenant),
    s: BrandService = Depends(_svc),
):
    tenant_id = uuid.UUID(t.tenant_id)
    return ok(
        await s.create_brand_request(body, tenant_id=tenant_id),
        _rid(r), "brands"
    )


@router.get("/brand-requests",
            response_model=ApiResponse[dict],
            summary="List this provider's brand requests")
async def list_my_brand_requests(
    r: Request,
    status: str | None = Query(None),
    t: TenantContext = Depends(require_tenant),
    s: BrandService = Depends(_svc),
):
    tenant_id = uuid.UUID(t.tenant_id)
    return ok(
        await s.list_brand_requests(status=status, tenant_id=tenant_id),
        _rid(r), "brands"
    )
