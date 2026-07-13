"""Sprint 34D — Brand Management Admin Router.

Prefix: /v1/admin/brands
Tags:   Brands, Brand Mappings, Brand Requests, Brand Templates
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, get_current_user, require_super_admin
from app.dependencies.db import get_db
from app.engines.admin_catalog.brand_service import BrandService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/brands", tags=["Brands"])
req_router = APIRouter(prefix="/v1/admin/brand-requests", tags=["Brand Requests"])
tmpl_router = APIRouter(prefix="/v1/admin/brand-templates", tags=["Brand Templates"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(get_current_user),
) -> BrandService:
    actor_id = uuid.UUID(u.user_id) if u.user_id else None
    return BrandService(db=db, actor_id=actor_id, actor_role=u.role, request_id=_rid(r))


# ═══════════════════════════════════════════════════════════
# BRAND CRUD
# ═══════════════════════════════════════════════════════════

@router.get("", response_model=ApiResponse[dict], summary="List brands",
            description="List all platform brands. Supports filtering by status, category, search.")
async def list_brands(
    r: Request,
    status: str | None = Query(None, description="active|inactive|archived|deprecated|pending_review|rejected"),
    category_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.list_brands(status=status, category_id=category_id, search=search,
                                   page=page, page_size=page_size), _rid(r))


@router.post("", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create brand",
             description="Create a new platform brand. Returns BRAND_DUPLICATE_POSSIBLE warning if similar name exists; pass force=true to override.")
async def create_brand(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    return ok(await s.create_brand(body), _rid(r))


@router.post("/seed", response_model=ApiResponse[dict], summary="Seed starter brands",
             description="Idempotent: seeds 25 common appliance/electronics brands if not already present.")
async def seed_brands(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.seed_starter_brands(), _rid(r))


@router.get("/{brand_id}", response_model=ApiResponse[dict], summary="Get brand detail",
            tags=["Brands"])
async def get_brand(
    brand_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.get_brand(brand_id), _rid(r))


@router.put("/{brand_id}", response_model=ApiResponse[dict], summary="Update brand",
            tags=["Brands"])
async def update_brand(
    brand_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    return ok(await s.update_brand(brand_id, body), _rid(r))


@router.post("/{brand_id}/activate", response_model=ApiResponse[dict], summary="Activate brand",
             tags=["Brands"])
async def activate_brand(
    brand_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.activate_brand(brand_id), _rid(r))


@router.post("/{brand_id}/deactivate", response_model=ApiResponse[dict], summary="Deactivate brand",
             tags=["Brands"])
async def deactivate_brand(
    brand_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.deactivate_brand(brand_id), _rid(r))


@router.post("/{brand_id}/archive", response_model=ApiResponse[dict], summary="Archive brand",
             tags=["Brands"])
async def archive_brand(
    brand_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.archive_brand(brand_id), _rid(r))


# ═══════════════════════════════════════════════════════════
# CATEGORY MAPPINGS
# ═══════════════════════════════════════════════════════════

@router.get("/{brand_id}/category-mappings", response_model=ApiResponse[dict],
            summary="List brand's category mappings", tags=["Brand Mappings"])
async def list_category_mappings(
    brand_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.list_category_mappings(brand_id), _rid(r))


@router.post("/{brand_id}/map-categories", response_model=ApiResponse[dict],
             summary="Map brand to categories (bulk)", tags=["Brand Mappings"])
async def map_brand_categories(
    brand_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    category_ids = body.get("category_ids", [])
    return ok(await s.map_brand_to_categories(brand_id, category_ids), _rid(r))


@router.delete("/{brand_id}/category-mappings/{category_id}", response_model=ApiResponse[dict],
               summary="Remove brand from category", tags=["Brand Mappings"])
async def unmap_brand_category(
    brand_id: uuid.UUID,
    category_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.unmap_brand_from_category(brand_id, category_id), _rid(r))


# ═══════════════════════════════════════════════════════════
# SERVICE MAPPINGS
# ═══════════════════════════════════════════════════════════

@router.get("/{brand_id}/service-mappings", response_model=ApiResponse[dict],
            summary="List brand's service mappings", tags=["Brand Mappings"])
async def list_service_mappings(
    brand_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.list_service_mappings(brand_id), _rid(r))


@router.post("/{brand_id}/map-services", response_model=ApiResponse[dict],
             summary="Map brand to services (bulk)", tags=["Brand Mappings"])
async def map_brand_services(
    brand_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    service_ids = body.get("service_ids", [])
    return ok(await s.map_brand_to_services(brand_id, service_ids), _rid(r))


@router.delete("/{brand_id}/service-mappings/{service_id}", response_model=ApiResponse[dict],
               summary="Remove brand from service", tags=["Brand Mappings"])
async def unmap_brand_service(
    brand_id: uuid.UUID,
    service_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.unmap_brand_from_service(brand_id, service_id), _rid(r))


@router.post("/bulk-map-services", response_model=ApiResponse[dict],
             summary="Bulk map N brands × M services", tags=["Brand Mappings"])
async def bulk_map_services(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    return ok(await s.bulk_map_brands_to_services(
        body.get("brand_ids", []), body.get("service_ids", [])
    ), _rid(r))


# ═══════════════════════════════════════════════════════════
# MERGE
# ═══════════════════════════════════════════════════════════

@router.post("/{brand_id}/merge", response_model=ApiResponse[dict],
             summary="Merge brand into another (duplicate resolution)", tags=["Brands"])
async def merge_brand(
    brand_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    target_id = uuid.UUID(str(body["target_brand_id"]))
    return ok(await s.merge_brand(brand_id, target_id, body.get("admin_note")), _rid(r))


# ═══════════════════════════════════════════════════════════
# BRAND REQUESTS
# ═══════════════════════════════════════════════════════════

@req_router.get("", response_model=ApiResponse[dict], summary="List brand requests")
async def list_brand_requests(
    r: Request,
    status: str | None = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.list_brand_requests(status=status, tenant_id=tenant_id), _rid(r))


@req_router.post("/{request_id}/approve", response_model=ApiResponse[dict],
                 summary="Approve brand request (creates brand)")
async def approve_brand_request(
    request_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    return ok(await s.approve_brand_request(request_id, body.get("admin_note")), _rid(r))


@req_router.post("/{request_id}/reject", response_model=ApiResponse[dict],
                 summary="Reject brand request")
async def reject_brand_request(
    request_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    return ok(await s.reject_brand_request(request_id, body.get("admin_note")), _rid(r))


@req_router.post("/{request_id}/merge", response_model=ApiResponse[dict],
                 summary="Merge brand request into existing brand")
async def merge_brand_request(
    request_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    existing_brand_id = uuid.UUID(str(body["existing_brand_id"]))
    return ok(await s.merge_brand_request(request_id, existing_brand_id, body.get("admin_note")), _rid(r))


# ═══════════════════════════════════════════════════════════
# BRAND TEMPLATES
# ═══════════════════════════════════════════════════════════

@tmpl_router.get("", response_model=ApiResponse[dict], summary="List brand templates")
async def list_brand_templates(
    r: Request,
    status: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    return ok(await s.list_brand_templates(status=status, category_id=category_id), _rid(r))


@tmpl_router.post("", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
                   summary="Create brand template")
async def create_brand_template(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    return ok(await s.create_brand_template(body), _rid(r))


@tmpl_router.post("/{template_id}/apply", response_model=ApiResponse[dict],
                   summary="Apply brand template to services")
async def apply_brand_template(
    template_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    s: BrandService = Depends(_svc),
):
    body = await r.json()
    service_ids = body.get("service_ids")
    return ok(await s.apply_brand_template(template_id, service_ids), _rid(r))
