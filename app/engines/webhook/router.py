"""Webhook Engine — Router (13 endpoints). Zero inline imports."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.webhook.service import WebhookService
from app.schemas.base import ApiResponse, ok
logger = structlog.get_logger("webhook.router")
router = APIRouter(prefix="/v1/webhooks", tags=["Webhook Engine"])
ENGINE_ID = "webhook"
def _svc(r: Request, db: AsyncSession=Depends(get_db), u: UserContext=Depends(get_current_user)):
    return WebhookService(db=db, request_id=getattr(r.state,"request_id","—"),
                           actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
def _rid(r): return getattr(r.state,"request_id","—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Webhook Engine", "version": "11.0.0",
            "endpoint_count": 13, "status": "active",
            "capabilities": ["db_level_idempotency","hmac_sha256_signing",
                             "db_consecutive_failures","auto_pause_at_5",
                             "replay_new_row","full_request_response_stored",
                             "cursor_pagination"]}

@router.post("/endpoints", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_endpoint(r: Request, u: UserContext=Depends(require_permission(P.TENANT_UPDATE)),
                           s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_endpoint(uuid.UUID(body["tenant_id"]), body["url"],
              body.get("description"), body.get("subscribed_events",[]),
              body.get("headers",{})), _rid(r), ENGINE_ID)

@router.get("/endpoints/{endpoint_id}", response_model=ApiResponse[dict])
async def get_endpoint(endpoint_id: uuid.UUID, r: Request, tenant_id: uuid.UUID=Query(...),
                        u: UserContext=Depends(get_current_user), s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_endpoint(endpoint_id, tenant_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/endpoints", response_model=ApiResponse[dict])
async def list_endpoints(tenant_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                          s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_endpoints(tenant_id), _rid(r), ENGINE_ID)

@router.put("/endpoints/{endpoint_id}", response_model=ApiResponse[dict])
async def update_endpoint(endpoint_id: uuid.UUID, r: Request, tenant_id: uuid.UUID=Query(...),
                           u: UserContext=Depends(require_permission(P.TENANT_UPDATE)),
                           s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.update_endpoint(endpoint_id, tenant_id, await r.json()), _rid(r), ENGINE_ID)

@router.delete("/endpoints/{endpoint_id}", response_model=ApiResponse[dict])
async def delete_endpoint(endpoint_id: uuid.UUID, r: Request, tenant_id: uuid.UUID=Query(...),
                           u: UserContext=Depends(require_permission(P.TENANT_UPDATE)),
                           s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_endpoint(endpoint_id, tenant_id), _rid(r), ENGINE_ID)

@router.post("/endpoints/{endpoint_id}/test",
             summary="Send test event to verify endpoint + HMAC verification", response_model=ApiResponse[dict])
async def test_endpoint(endpoint_id: uuid.UUID, r: Request, tenant_id: uuid.UUID=Query(...),
                         u: UserContext=Depends(require_permission(P.TENANT_UPDATE)),
                         s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.test_endpoint(endpoint_id, tenant_id), _rid(r), ENGINE_ID)

@router.post("/endpoints/{endpoint_id}/pause", response_model=ApiResponse[dict])
async def pause_endpoint(endpoint_id: uuid.UUID, r: Request, tenant_id: uuid.UUID=Query(...),
                          u: UserContext=Depends(require_permission(P.TENANT_UPDATE)),
                          s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.pause_endpoint(endpoint_id, tenant_id), _rid(r), ENGINE_ID)

@router.post("/endpoints/{endpoint_id}/resume", response_model=ApiResponse[dict])
async def resume_endpoint(endpoint_id: uuid.UUID, r: Request, tenant_id: uuid.UUID=Query(...),
                           u: UserContext=Depends(require_permission(P.TENANT_UPDATE)),
                           s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.resume_endpoint(endpoint_id, tenant_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/deliveries", response_model=ApiResponse[dict])
async def list_deliveries(tenant_id: uuid.UUID, r: Request,
                           endpoint_id: uuid.UUID|None=Query(None),
                           dlv_status: str|None=Query(None, alias="status"),
                           limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                           u: UserContext=Depends(get_current_user),
                           s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_deliveries(tenant_id, endpoint_id, dlv_status, limit, cursor), _rid(r), ENGINE_ID)

@router.get("/deliveries/{delivery_id}", response_model=ApiResponse[dict])
async def get_delivery(delivery_id: uuid.UUID, r: Request, tenant_id: uuid.UUID=Query(...),
                        u: UserContext=Depends(get_current_user),
                        s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_delivery(delivery_id, tenant_id), _rid(r), ENGINE_ID)

@router.post("/deliveries/{delivery_id}/replay",
             summary="Replay — creates NEW delivery row, original never modified", response_model=ApiResponse[dict])
async def replay_delivery(delivery_id: uuid.UUID, r: Request, tenant_id: uuid.UUID=Query(...),
                           u: UserContext=Depends(require_permission(P.TENANT_UPDATE)),
                           s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.replay_delivery(delivery_id, tenant_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/events/{event_type}", response_model=ApiResponse[dict])
async def list_by_event_type(tenant_id: uuid.UUID, event_type: str, r: Request,
                              limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                              u: UserContext=Depends(get_current_user),
                              s: WebhookService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_events_by_type(tenant_id, event_type, limit, cursor), _rid(r), ENGINE_ID)
