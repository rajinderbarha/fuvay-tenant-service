"""Admin Home Services Catalog Setup Console.

Consolidates the already-real, already-working master-service / service-type
/ brand / pricing-rule CRUD (admin_router.py) into one Home-Services-scoped
console surface: grouped service list, per-service tabs (types with admin
floor/ceiling, brand behavior + brand override limits, symmetric customer
Low/Mid/High preview, audit trail). Hard-scoped to the Home Services
category — never reads or writes any other vertical's catalog data.
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_vertical_enabled
from app.engines.admin_catalog.service import AdminCatalogService
from app.schemas.base import ApiResponse, ok

router = APIRouter(
    prefix="/v1/admin/home-services/service-catalog",
    tags=["Home Services Catalog Console"],
    dependencies=[Depends(require_vertical_enabled("home_services"))],
)
ENGINE_ID = "admin_catalog"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> AdminCatalogService:
    return AdminCatalogService(db=db, request_id=getattr(r.state, "request_id", "—"),
                               actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                               actor_role=u.role)


def _rid(r): return getattr(r.state, "request_id", "—")


@router.get("/services", response_model=ApiResponse[dict],
            summary="Grouped Home Services catalog for the console's left panel")
async def list_console_services(r: Request,
                                 q: str | None = Query(None, max_length=200),
                                 service_id: uuid.UUID | None = Query(None),
                                 service_group_id: uuid.UUID | None = Query(None),
                                 is_active: bool | None = Query(None),
                                 limit: int = Query(50, ge=1, le=100),
                                 offset: int = Query(0, ge=0),
                                 u: UserContext = Depends(require_permission(P.CATALOG_PRICING_READ)),
                                 s: AdminCatalogService = Depends(_svc)):
    return ok(await s.list_home_services_catalog_console(
        q=q, service_id=service_id, service_group_id=service_group_id, is_active=is_active,
        limit=limit, offset=offset,
    ), _rid(r), ENGINE_ID)


@router.get("/services/{service_id}", response_model=ApiResponse[dict],
            summary="Selected service detail — general + types + brands")
async def get_console_service_detail(service_id: uuid.UUID, r: Request,
                                      u: UserContext = Depends(require_permission(P.CATALOG_PRICING_READ)),
                                      s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_home_services_service_console_detail(service_id), _rid(r), ENGINE_ID)


@router.get("/services/{service_id}/types", response_model=ApiResponse[dict],
            summary="Types & Pricing tab — each type with admin floor/ceiling + customer preview")
async def get_console_type_pricing(service_id: uuid.UUID, r: Request,
                                    u: UserContext = Depends(require_permission(P.CATALOG_PRICING_READ)),
                                    s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_home_services_type_pricing(service_id), _rid(r), ENGINE_ID)


@router.put("/services/{service_id}/types/{service_type_id}/limits", response_model=ApiResponse[dict],
            summary="Set admin floor/ceiling, platform fee, and deduction credits for a type")
async def set_console_type_limits(service_id: uuid.UUID, service_type_id: uuid.UUID, r: Request,
                                   u: UserContext = Depends(require_permission(P.CATALOG_PRICING_WRITE)),
                                   s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.upsert_home_services_type_limits(service_id, service_type_id, body), _rid(r), ENGINE_ID)


@router.get("/services/{service_id}/brands", response_model=ApiResponse[dict],
            summary="Brands tab — behavior + override limits + customer preview")
async def get_console_brand_pricing(service_id: uuid.UUID, r: Request,
                                     service_type_id: uuid.UUID | None = None,
                                     u: UserContext = Depends(require_permission(P.CATALOG_PRICING_READ)),
                                     s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_home_services_brand_pricing(service_id, service_type_id), _rid(r), ENGINE_ID)


@router.put("/services/{service_id}/brands/{mapping_id}/behavior", response_model=ApiResponse[dict],
            summary="Set whether a brand can override price / is routing-only")
async def set_console_brand_behavior(service_id: uuid.UUID, mapping_id: uuid.UUID, r: Request,
                                      u: UserContext = Depends(require_permission(P.CATALOG_PRICING_WRITE)),
                                      s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok({"brands": await s.set_home_services_brand_behavior(service_id, mapping_id, body)}, _rid(r), ENGINE_ID)


@router.put("/services/{service_id}/brands/{brand_id}/limits", response_model=ApiResponse[dict],
            summary="Set admin floor/ceiling for a brand override")
async def set_console_brand_limits(service_id: uuid.UUID, brand_id: uuid.UUID, r: Request,
                                    service_type_id: uuid.UUID | None = None,
                                    u: UserContext = Depends(require_permission(P.CATALOG_PRICING_WRITE)),
                                    s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(await s.upsert_home_services_brand_limits(service_id, brand_id, service_type_id, body), _rid(r), ENGINE_ID)


@router.post("/price-preview", response_model=ApiResponse[dict],
             summary="Customer Price Preview — symmetric Low/Mid/High from a provider price range")
async def console_price_preview(r: Request,
                                 u: UserContext = Depends(require_permission(P.PRICING_BARGAIN_EVALUATE_PREVIEW)),
                                 s: AdminCatalogService = Depends(_svc)):
    body = await r.json()
    return ok(s.preview_symmetric_customer_price(body), _rid(r), ENGINE_ID)


@router.get("/services/{service_id}/audit", response_model=ApiResponse[dict],
            summary="Activity tab — recent changes to this service and its pricing rules")
async def get_console_service_audit(service_id: uuid.UUID, r: Request,
                                     u: UserContext = Depends(require_permission(P.CATALOG_PRICING_READ)),
                                     s: AdminCatalogService = Depends(_svc)):
    return ok(await s.get_home_services_service_audit(service_id), _rid(r), ENGINE_ID)
