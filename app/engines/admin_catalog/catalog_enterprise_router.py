"""Catalog Enterprise Router — Service Types + Type Mappings + Brand Mappings + Brand Summary.
Prefix: /v1/admin/catalog
"""
from __future__ import annotations
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, get_current_user, require_super_admin
from app.dependencies.db import get_db
from app.engines.admin_catalog.types_service import TypesService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/catalog", tags=["Catalog Enterprise"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(get_current_user),
) -> TypesService:
    actor_id = uuid.UUID(u.user_id) if u.user_id else None
    return TypesService(db=db, actor_id=actor_id, actor_role=u.role, request_id=_rid(r))


# ═══════════════════════════════════════════════════════════
# SERVICE TYPES
# ═══════════════════════════════════════════════════════════

@router.get("/types/summary", response_model=ApiResponse[dict],
            summary="Service types summary counts")
async def types_summary(r: Request, s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.summary(), _rid(r), "catalog_enterprise")


@router.get("/types/export", response_model=ApiResponse[list],
            summary="Export all service types as list")
async def export_types(r: Request,
                       u: UserContext = Depends(require_super_admin),
                       s: TypesService = Depends(_svc)) -> ApiResponse[list]:
    return ok(await s.export_types(), _rid(r), "catalog_enterprise")


@router.get("/types", response_model=ApiResponse[dict], summary="List service types")
async def list_types(
    r: Request,
    q: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    mapped: bool | None = Query(None),
    customer_visible: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: str = Query("name"),
    sort_dir: str = Query("asc"),
    s: TypesService = Depends(_svc),
) -> ApiResponse[dict]:
    return ok(
        await s.list_types(q=q, category_id=category_id, status=status, mapped=mapped,
                           customer_visible=customer_visible, page=page, page_size=page_size,
                           sort_by=sort_by, sort_dir=sort_dir),
        _rid(r), "catalog_enterprise",
    )


@router.get("/types/{type_id}", response_model=ApiResponse[dict], summary="Get service type detail")
async def get_type(type_id: uuid.UUID, r: Request,
                   s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_type(type_id), _rid(r), "catalog_enterprise")


@router.post("/types", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED,
             summary="Create service type")
async def create_type(r: Request,
                      u: UserContext = Depends(require_super_admin),
                      s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.create_type(await r.json()), _rid(r), "catalog_enterprise")


@router.put("/types/{type_id}", response_model=ApiResponse[dict], summary="Update service type")
async def update_type(type_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(require_super_admin),
                      s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.update_type(type_id, await r.json()), _rid(r), "catalog_enterprise")


@router.post("/types/{type_id}/activate", response_model=ApiResponse[dict],
             summary="Activate service type")
async def activate_type(type_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.activate_type(type_id), _rid(r), "catalog_enterprise")


@router.post("/types/{type_id}/deactivate", response_model=ApiResponse[dict],
             summary="Deactivate service type")
async def deactivate_type(type_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_super_admin),
                          s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.deactivate_type(type_id), _rid(r), "catalog_enterprise")


@router.post("/types/{type_id}/archive", response_model=ApiResponse[dict],
             summary="Archive service type")
async def archive_type(type_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_super_admin),
                       s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.archive_type(type_id), _rid(r), "catalog_enterprise")


# ═══════════════════════════════════════════════════════════
# TYPE MAPPINGS
# ═══════════════════════════════════════════════════════════

@router.get("/type-mappings/export", response_model=ApiResponse[list],
            summary="Export all type mappings")
async def export_type_mappings(r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: TypesService = Depends(_svc)) -> ApiResponse[list]:
    return ok(await s.export_type_mappings(), _rid(r), "catalog_enterprise")


@router.get("/type-mappings", response_model=ApiResponse[dict], summary="List type mappings")
async def list_type_mappings(
    r: Request,
    type_id: uuid.UUID | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    service_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    s: TypesService = Depends(_svc),
) -> ApiResponse[dict]:
    return ok(
        await s.list_type_mappings(type_id=type_id, category_id=category_id,
                                   service_id=service_id, status=status,
                                   page=page, page_size=page_size),
        _rid(r), "catalog_enterprise",
    )


@router.post("/type-mappings", response_model=ApiResponse[dict],
             status_code=status.HTTP_201_CREATED, summary="Create type mapping")
async def create_type_mapping(r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.create_type_mapping(await r.json()), _rid(r), "catalog_enterprise")


@router.put("/type-mappings/{mapping_id}", response_model=ApiResponse[dict],
            summary="Update type mapping")
async def update_type_mapping(mapping_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.update_type_mapping(mapping_id, await r.json()), _rid(r), "catalog_enterprise")


@router.delete("/type-mappings/{mapping_id}", response_model=ApiResponse[dict],
               summary="Archive / remove type mapping")
async def delete_type_mapping(mapping_id: uuid.UUID, r: Request,
                              u: UserContext = Depends(require_super_admin),
                              s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_type_mapping(mapping_id), _rid(r), "catalog_enterprise")


# ═══════════════════════════════════════════════════════════
# BRAND SUMMARY  (proxied here under /catalog namespace)
# ═══════════════════════════════════════════════════════════

@router.get("/brands/summary", response_model=ApiResponse[dict],
            summary="Brand master summary counts")
async def brand_summary(r: Request, s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.brand_summary(), _rid(r), "catalog_enterprise")


# ═══════════════════════════════════════════════════════════
# BRAND MAPPINGS
# ═══════════════════════════════════════════════════════════

@router.get("/brand-mappings/export", response_model=ApiResponse[list],
            summary="Export all brand mappings")
async def export_brand_mappings(r: Request,
                                u: UserContext = Depends(require_super_admin),
                                s: TypesService = Depends(_svc)) -> ApiResponse[list]:
    return ok(await s.export_brand_mappings(), _rid(r), "catalog_enterprise")


@router.get("/brand-mappings", response_model=ApiResponse[dict], summary="List brand mappings")
async def list_brand_mappings(
    r: Request,
    brand_id: uuid.UUID | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    service_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    s: TypesService = Depends(_svc),
) -> ApiResponse[dict]:
    return ok(
        await s.list_brand_mappings(brand_id=brand_id, category_id=category_id,
                                    service_id=service_id, status=status,
                                    page=page, page_size=page_size),
        _rid(r), "catalog_enterprise",
    )


@router.post("/brand-mappings", response_model=ApiResponse[dict],
             status_code=status.HTTP_201_CREATED, summary="Create brand mapping")
async def create_brand_mapping(r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.create_brand_mapping(await r.json()), _rid(r), "catalog_enterprise")


@router.put("/brand-mappings/{mapping_id}", response_model=ApiResponse[dict],
            summary="Update brand mapping")
async def update_brand_mapping(mapping_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.update_brand_mapping(mapping_id, await r.json()), _rid(r), "catalog_enterprise")


@router.delete("/brand-mappings/{mapping_id}", response_model=ApiResponse[dict],
               summary="Archive / remove brand mapping")
async def delete_brand_mapping(mapping_id: uuid.UUID, r: Request,
                               u: UserContext = Depends(require_super_admin),
                               s: TypesService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_brand_mapping(mapping_id), _rid(r), "catalog_enterprise")
