"""Inventory Engine — Router (14 endpoints). Zero inline imports."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_tenant_vertical_active
from app.engines.inventory.service import InventoryService
from app.schemas.base import ApiResponse, ok
logger = structlog.get_logger("inventory.router")
router = APIRouter(prefix="/v1/inventory", tags=["Inventory Engine"])
ENGINE_ID = "inventory"
def _svc(r: Request, db: AsyncSession=Depends(get_db), u: UserContext=Depends(get_current_user)):
    return InventoryService(db=db, request_id=getattr(r.state,"request_id","—"),
                             actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
                             actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)
def _rid(r): return getattr(r.state,"request_id","—")
@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID,"name":"Inventory Engine","version":"10.0.0",
            "endpoint_count": 20,"status":"active",
            "capabilities":["select_for_update","append_only_ledger","ledger_reconciliation",
                            "reservation_ttl","low_stock_alerts","cycle_count"]}
# Inventory's "inventory" capability is currently declared only by the
# home_services vertical (confirmed live -- no other vertical's capability
# list includes it). This guard binds mutations to that vertical being
# enabled AND this tenant's own home_services enrollment being active, in
# addition to the existing permission check below. If inventory ever
# becomes a multi-vertical capability, this needs to resolve the tenant's
# actual vertical dynamically rather than a fixed "home_services" binding.
_require_hs_vertical_active = require_tenant_vertical_active("home_services")

@router.post("/tenants/{tenant_id}/items", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_item(tenant_id: uuid.UUID, r: Request, u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       _v=Depends(_require_hs_vertical_active),
                       s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.create_item(tenant_id, await r.json()), _rid(r), ENGINE_ID)
@router.get("/items/{item_id}", response_model=ApiResponse[dict])
async def get_item(item_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                    s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_item(item_id), _rid(r), ENGINE_ID)
@router.get("/tenants/{tenant_id}/items", response_model=ApiResponse[dict])
async def list_items(tenant_id: uuid.UUID, r: Request, limit: int=Query(50,ge=1,le=200),
                      cursor: str|None=Query(None), search: str|None=Query(None, max_length=100),
                      category_id: uuid.UUID|None=Query(None),
                      stock_status: str=Query("all", pattern="^(all|healthy|low|out)$"),
                      sort: str=Query("name_asc", pattern="^(name_asc|name_desc|stock_asc|stock_desc|value_desc)$"),
                      offset: int=Query(0, ge=0), include_archived: bool=Query(False),
                      u: UserContext=Depends(get_current_user),
                      s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_items(tenant_id, limit, cursor, search, category_id,
                                 stock_status, sort, offset, include_archived), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/workspace-summary", response_model=ApiResponse[dict])
async def workspace_summary(tenant_id: uuid.UUID, r: Request,
                            u: UserContext=Depends(get_current_user),
                            s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.workspace_summary(tenant_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/locations", response_model=ApiResponse[dict])
async def list_locations(tenant_id: uuid.UUID, r: Request, include_archived: bool=Query(False),
                         u: UserContext=Depends(get_current_user),
                         s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_locations(tenant_id, include_archived), _rid(r), ENGINE_ID)

@router.post("/tenants/{tenant_id}/locations", status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def create_location(tenant_id: uuid.UUID, r: Request,
                          u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                          _v=Depends(_require_hs_vertical_active),
                          s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.create_location(tenant_id, await r.json()), _rid(r), ENGINE_ID)

@router.patch("/tenants/{tenant_id}/locations/{location_id}", response_model=ApiResponse[dict])
async def update_location(tenant_id: uuid.UUID, location_id: uuid.UUID, r: Request,
                          u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                          _v=Depends(_require_hs_vertical_active),
                          s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.update_location(tenant_id, location_id, await r.json()), _rid(r), ENGINE_ID)
@router.put("/tenants/{tenant_id}/items/{item_id}", response_model=ApiResponse[dict])
async def update_item(tenant_id: uuid.UUID, item_id: uuid.UUID, r: Request,
                       u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       _v=Depends(_require_hs_vertical_active),
                       s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.update_item(item_id, tenant_id, await r.json()), _rid(r), ENGINE_ID)
@router.delete("/tenants/{tenant_id}/items/{item_id}", response_model=ApiResponse[dict])
async def delete_item(tenant_id: uuid.UUID, item_id: uuid.UUID, r: Request,
                       u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       _v=Depends(_require_hs_vertical_active),
                       s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_item(item_id, tenant_id), _rid(r), ENGINE_ID)
@router.post("/items/{item_id}/locations/{location_id}/receive", response_model=ApiResponse[dict])
async def receive_stock(item_id: uuid.UUID, location_id: uuid.UUID, r: Request,
                         u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                         _v=Depends(_require_hs_vertical_active),
                         s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.receive_stock(item_id, location_id, uuid.UUID(body["tenant_id"]),
              body["quantity"], None, body.get("reference_id"), body.get("notes")), _rid(r), ENGINE_ID)

@router.post("/items/{item_id}/locations/{location_id}/count", response_model=ApiResponse[dict],
             summary="Post a reconciled cycle count adjustment")
async def count_stock(item_id: uuid.UUID, location_id: uuid.UUID, r: Request,
                      u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                      _v=Depends(_require_hs_vertical_active),
                      s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.count_stock(item_id, location_id, uuid.UUID(body["tenant_id"]),
              body["counted_quantity"], body.get("reason", ""),
              body.get("idempotency_key")), _rid(r), ENGINE_ID)

@router.post("/items/{item_id}/transfer", response_model=ApiResponse[dict],
             summary="Transfer available stock between provider locations")
async def transfer_stock(item_id: uuid.UUID, r: Request,
                         u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                         _v=Depends(_require_hs_vertical_active),
                         s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.transfer_stock(item_id, uuid.UUID(body["from_location_id"]),
              uuid.UUID(body["to_location_id"]), uuid.UUID(body["tenant_id"]),
              body["quantity"], body.get("reason", ""), body.get("idempotency_key")),
              _rid(r), ENGINE_ID)
@router.get("/items/{item_id}/locations/{location_id}/balance",
            summary="Balance with ledger reconciliation on every read", response_model=ApiResponse[dict])
async def get_balance(item_id: uuid.UUID, location_id: uuid.UUID, r: Request,
                       u: UserContext=Depends(get_current_user), s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_stock_level(item_id, location_id), _rid(r), ENGINE_ID)
@router.get("/items/{item_id}/locations/{location_id}/transactions", response_model=ApiResponse[dict])
async def list_txns(item_id: uuid.UUID, location_id: uuid.UUID, r: Request,
                     limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                     u: UserContext=Depends(get_current_user), s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_stock_transactions(item_id, location_id, limit, cursor), _rid(r), ENGINE_ID)
@router.post("/reservations", status_code=status.HTTP_201_CREATED,
             summary="Reserve stock for a job — SELECT FOR UPDATE prevents race conditions",
             response_model=ApiResponse[dict])
async def create_reservation(r: Request, u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                              _v=Depends(_require_hs_vertical_active),
                              s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_reservation(body["job_id"], uuid.UUID(body["item_id"]),
              uuid.UUID(body["location_id"]), uuid.UUID(body["tenant_id"]),
              body["quantity"]), _rid(r), ENGINE_ID)
@router.post("/reservations/confirm", response_model=ApiResponse[dict])
async def confirm_reservation(r: Request, u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                               _v=Depends(_require_hs_vertical_active),
                               s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.confirm_reservation(body["job_id"], uuid.UUID(body["item_id"]),
              uuid.UUID(body["location_id"]), uuid.UUID(body["tenant_id"])), _rid(r), ENGINE_ID)
@router.post("/reservations/release", response_model=ApiResponse[dict])
async def release_reservation(r: Request, u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                               _v=Depends(_require_hs_vertical_active),
                               s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.release_reservation(body["job_id"], uuid.UUID(body["item_id"]),
              uuid.UUID(body["location_id"]), uuid.UUID(body["tenant_id"])), _rid(r), ENGINE_ID)
@router.get("/tenants/{tenant_id}/low-stock", response_model=ApiResponse[dict])
async def low_stock(tenant_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                     s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_below_minimum(tenant_id), _rid(r), ENGINE_ID)
@router.post("/tenants/{tenant_id}/items/{item_id}/replenish", response_model=ApiResponse[dict])
async def replenish(tenant_id: uuid.UUID, item_id: uuid.UUID, r: Request,
                     u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                     s: InventoryService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.request_replenishment(tenant_id, item_id, body["quantity"]), _rid(r), ENGINE_ID)
