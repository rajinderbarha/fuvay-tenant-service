"""Notification Engine — Router (14 endpoints)."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.notification.service import NotificationService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("notification.router")
router = APIRouter(prefix="/v1/notifications", tags=["Notification Engine"])
ENGINE_ID = "notification"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> NotificationService:
    return NotificationService(db=db, request_id=getattr(r.state,"request_id","—"),
                                actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                                actor_role=u.role,
                                actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)
def _rid(r): return getattr(r.state,"request_id","—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Notification Engine", "version": "5.0.0",
            "endpoint_count": 14, "status": "active",
            "channels": ["push","sms","email","in_app"],
            "capabilities": ["template_management","async_dispatch","retry_logic",
                             "delivery_tracking","channel_config","idempotency"]}

@router.post("/send", summary="Send notification (async, idempotent)",
             status_code=status.HTTP_202_ACCEPTED, response_model=ApiResponse[dict])
async def send_notification(r: Request,
                             u: UserContext = Depends(get_current_user),
                             s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.send(
        tenant_id=uuid.UUID(body["tenant_id"]),
        recipient_id=uuid.UUID(body["recipient_id"]),
        recipient_type=body.get("recipient_type","user"),
        notif_type=body["notif_type"], channel=body["channel"],
        data=body.get("data",{}),
        reference_id=body.get("reference_id"),
        reference_type=body.get("reference_type"),
        idempotency_key=r.headers.get("X-Idempotency-Key"))
    return ok(data, _rid(r), ENGINE_ID)

@router.get("/{notification_id}", response_model=ApiResponse[dict])
async def get_status(notification_id: uuid.UUID, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_status(notification_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/list", response_model=ApiResponse[dict])
async def list_notifications(tenant_id: uuid.UUID, r: Request,
                              status_filter: str|None = Query(None, alias="status"),
                              limit: int = Query(50,ge=1,le=200),
                              cursor: str|None = Query(None),
                              u: UserContext = Depends(get_current_user),
                              s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_notifications(tenant_id, status_filter, limit, cursor), _rid(r), ENGINE_ID)

@router.post("/{notification_id}/retry", response_model=ApiResponse[dict])
async def retry(notification_id: uuid.UUID, r: Request,
                 u: UserContext = Depends(get_current_user),
                 s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.retry_failed(notification_id), _rid(r), ENGINE_ID)

# Templates
@router.get("/templates/list", response_model=ApiResponse[dict])
async def list_templates(r: Request,
                          tenant_id: uuid.UUID|None = Query(None),
                          u: UserContext = Depends(get_current_user),
                          s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_templates(tenant_id), _rid(r), ENGINE_ID)

@router.post("/templates", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_template(r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    tid = uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None
    return ok(await s.create_template(tid, body), _rid(r), ENGINE_ID)

@router.put("/templates/{template_id}", response_model=ApiResponse[dict])
async def update_template(template_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.update_template(template_id, await r.json()), _rid(r), ENGINE_ID)

@router.delete("/templates/{template_id}", response_model=ApiResponse[dict])
async def delete_template(template_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.delete_template(template_id), _rid(r), ENGINE_ID)

# Channel config
@router.get("/tenants/{tenant_id}/channels", response_model=ApiResponse[dict])
async def list_channels(tenant_id: uuid.UUID, r: Request,
                         u: UserContext = Depends(get_current_user),
                         s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_channels(tenant_id), _rid(r), ENGINE_ID)

@router.put("/tenants/{tenant_id}/channels/{channel}", response_model=ApiResponse[dict])
async def set_channel(tenant_id: uuid.UUID, channel: str, r: Request,
                       u: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_UPDATE)),
                       s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.set_channel_config(tenant_id, channel,
              body.get("config",{}), body.get("is_enabled", True)), _rid(r), ENGINE_ID)

@router.post("/tenants/{tenant_id}/channels/{channel}/test", response_model=ApiResponse[dict])
async def test_channel(tenant_id: uuid.UUID, channel: str, r: Request,
                        u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                        s: NotificationService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.test_channel(tenant_id, channel), _rid(r), ENGINE_ID)
