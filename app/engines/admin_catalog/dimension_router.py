"""Generic Catalog Dimension Engine -- admin router (migration 154).

Backs the approved Admin Catalog page's Dimensions tab. All writes are
super-admin only. Reads are open to authenticated users (the tenant wizard
also needs to know which dimensions a service-job enables).
"""
import uuid

from fastapi import APIRouter, Depends, Query, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.admin_catalog.dimension_service import CatalogDimensionService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/catalog/dimensions", tags=["Admin Catalog Dimensions"])
ENGINE_ID = "admin_catalog"


def _svc(db: AsyncSession = Depends(get_db), u: UserContext = Depends(get_current_user)) -> CatalogDimensionService:
    return CatalogDimensionService(db=db, actor_id=uuid.UUID(u.user_id) if u.user_id else None)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Dimension definitions ─────────────────────────────────────────────────────
@router.get("", response_model=ApiResponse[dict], summary="List dimension definitions")
async def list_dimensions(r: Request, include_inactive: bool = Query(False),
                           u: UserContext = Depends(get_current_user),
                           s: CatalogDimensionService = Depends(_svc)):
    data = await s.list_dimensions(include_inactive)
    return ok({"items": data, "total": len(data)}, _rid(r), ENGINE_ID)


@router.post("", response_model=ApiResponse[dict], status_code=201, summary="Create a generic dimension")
async def create_dimension(r: Request, payload: dict = Body(...),
                            u: UserContext = Depends(require_super_admin),
                            s: CatalogDimensionService = Depends(_svc)):
    return ok(await s.create_dimension(payload), _rid(r), ENGINE_ID)


@router.put("/{dimension_id}", response_model=ApiResponse[dict], summary="Update a dimension definition")
async def update_dimension(dimension_id: uuid.UUID, r: Request, payload: dict = Body(...),
                            u: UserContext = Depends(require_super_admin),
                            s: CatalogDimensionService = Depends(_svc)):
    return ok(await s.update_dimension(dimension_id, payload), _rid(r), ENGINE_ID)


@router.delete("/{dimension_id}", response_model=ApiResponse[dict], summary="Delete a custom dimension definition")
async def delete_dimension(dimension_id: uuid.UUID, r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: CatalogDimensionService = Depends(_svc)):
    return ok(await s.delete_dimension(dimension_id), _rid(r), ENGINE_ID)


# ── Dimension values ──────────────────────────────────────────────────────────
@router.get("/{dimension_id}/values", response_model=ApiResponse[dict],
            summary="List a dimension's values (proxies legacy Type/Brand tables)")
async def list_values(dimension_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(get_current_user),
                       s: CatalogDimensionService = Depends(_svc)):
    return ok(await s.list_values(dimension_id), _rid(r), ENGINE_ID)


@router.post("/{dimension_id}/values", response_model=ApiResponse[dict], status_code=201,
             summary="Add a value to a generic dimension")
async def add_value(dimension_id: uuid.UUID, r: Request, payload: dict = Body(...),
                     u: UserContext = Depends(require_super_admin),
                     s: CatalogDimensionService = Depends(_svc)):
    return ok(await s.add_value(dimension_id, payload), _rid(r), ENGINE_ID)


@router.put("/{dimension_id}/values/{value_id}", response_model=ApiResponse[dict],
            summary="Update a generic dimension value")
async def update_value(dimension_id: uuid.UUID, value_id: uuid.UUID, r: Request, payload: dict = Body(...),
                        u: UserContext = Depends(require_super_admin),
                        s: CatalogDimensionService = Depends(_svc)):
    return ok(await s.update_value(dimension_id, value_id, payload), _rid(r), ENGINE_ID)


@router.delete("/{dimension_id}/values/{value_id}", response_model=ApiResponse[dict],
               summary="Delete a generic dimension value")
async def delete_value(dimension_id: uuid.UUID, value_id: uuid.UUID, r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: CatalogDimensionService = Depends(_svc)):
    return ok(await s.delete_value(dimension_id, value_id), _rid(r), ENGINE_ID)


# ── Service-job dimension blueprint config (the Dimensions grid) ──────────────
@router.get("/blueprint/config", response_model=ApiResponse[dict],
            summary="Dimension grid for a (master_service, job_type): every dimension + its config + value count")
async def get_service_job_dimensions(r: Request,
                                      master_service_id: uuid.UUID = Query(...),
                                      job_type_id: uuid.UUID | None = Query(None),
                                      u: UserContext = Depends(get_current_user),
                                      s: CatalogDimensionService = Depends(_svc)):
    return ok(await s.get_service_job_dimensions(master_service_id, job_type_id), _rid(r), ENGINE_ID)


@router.put("/blueprint/config", response_model=ApiResponse[dict],
            summary="Set structural flags for one dimension of a (master_service, job_type)")
async def set_service_job_dimension(r: Request, payload: dict = Body(...),
                                    u: UserContext = Depends(require_super_admin),
                                    s: CatalogDimensionService = Depends(_svc)):
    master_service_id = uuid.UUID(payload["master_service_id"])
    job_type_id = uuid.UUID(payload["job_type_id"]) if payload.get("job_type_id") else None
    dimension_id = uuid.UUID(payload["dimension_id"])
    flags = payload.get("flags", {})
    return ok(await s.set_service_job_dimension(master_service_id, job_type_id, dimension_id, flags),
              _rid(r), ENGINE_ID)


# ── Blueprint readiness (right-panel checklist + percentage) ──────────────────
@router.get("/blueprint/readiness", response_model=ApiResponse[dict],
            summary="Canonical blueprint readiness for a (master_service, job_type): "
                    "checklist + percentage + affected tenant count")
async def get_blueprint_readiness(r: Request,
                                  master_service_id: uuid.UUID = Query(...),
                                  job_type_id: uuid.UUID | None = Query(None),
                                  u: UserContext = Depends(get_current_user),
                                  s: CatalogDimensionService = Depends(_svc)):
    return ok(await s.get_blueprint_readiness(master_service_id, job_type_id), _rid(r), ENGINE_ID)
