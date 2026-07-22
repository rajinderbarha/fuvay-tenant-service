"""Service Catalog Engine — Router. Tenant-defined services replace hardcoded ones."""
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.service_catalog.service import ServiceCatalogService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/catalog", tags=["Service Catalog Engine"])
ENGINE_ID = "service_catalog"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> ServiceCatalogService:
    return ServiceCatalogService(db=db, request_id=getattr(r.state, "request_id", "—"),
                                  actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
                                  actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)
def _rid(r): return getattr(r.state, "request_id", "—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Service Catalog Engine", "version": "1.0.0",
            "endpoint_count": 6, "status": "active",
            "capabilities": ["tenant_defined_services", "pricing_models",
                              "auto_job_type_selection", "checklist_flagging"]}

@router.post("", status_code=status.HTTP_201_CREATED, summary="Define a new service offering",
             response_model=ApiResponse[dict])
async def create_item(r: Request,
                       u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       s: ServiceCatalogService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.create_item(uuid.UUID(body["tenant_id"]), body)
    return ok(data, _rid(r), ENGINE_ID)

@router.get("/{item_id}", response_model=ApiResponse[dict])
async def get_item(item_id: uuid.UUID, r: Request,
                    u: UserContext = Depends(get_current_user),
                    s: ServiceCatalogService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_item(item_id), _rid(r), ENGINE_ID)

@router.get("", summary="List a tenant's service catalog", response_model=ApiResponse[dict])
async def list_items(r: Request,
                      tenant_id: uuid.UUID = Query(...),
                      service_type: str | None = Query(None),
                      is_active: bool | None = Query(None),
                      limit: int = Query(50, ge=1, le=200),
                      cursor: str | None = Query(None),
                      u: UserContext = Depends(get_current_user),
                      s: ServiceCatalogService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_items(tenant_id, service_type, is_active, limit, cursor), _rid(r), ENGINE_ID)

@router.put("/{item_id}", summary="Update a service offering", response_model=ApiResponse[dict])
async def update_item(item_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       s: ServiceCatalogService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.update_item(item_id, body), _rid(r), ENGINE_ID)

@router.post("/{item_id}/deactivate", summary="Retire a service offering", response_model=ApiResponse[dict])
async def deactivate_item(item_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                           s: ServiceCatalogService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.deactivate_item(item_id), _rid(r), ENGINE_ID)
