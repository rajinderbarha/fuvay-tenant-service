"""Subscription Engine — Router (10 endpoints). Zero inline imports."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.subscription.service import SubscriptionService
from app.schemas.base import ApiResponse, ok
logger = structlog.get_logger("subscription.router")
router = APIRouter(prefix="/v1/subscriptions", tags=["Subscription Engine"])
ENGINE_ID = "subscription"
def _svc(r: Request, db: AsyncSession=Depends(get_db), u: UserContext=Depends(get_current_user)):
    return SubscriptionService(db=db, request_id=getattr(r.state,"request_id","—"),
                                actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
def _rid(r): return getattr(r.state,"request_id","—")
@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID,"name":"Subscription Engine","version":"10.0.0",
            "endpoint_count": 10,"status":"active",
            "capabilities":["immutable_period_proration","plan_change_history",
                            "canonical_usage_source","dunning","grace_period","billing_history"]}
@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_subscription(r: Request, u: UserContext=Depends(require_super_admin),
                               s: SubscriptionService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_subscription(uuid.UUID(body["tenant_id"]), body["plan_type"],
              body.get("billing_cycle","monthly"), body.get("trial_days",14)), _rid(r), ENGINE_ID)
@router.get("/tenants/{tenant_id}", response_model=ApiResponse[dict])
async def get_subscription(tenant_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                            s: SubscriptionService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_subscription(tenant_id), _rid(r), ENGINE_ID)
@router.put("/tenants/{tenant_id}/plan",
            summary="Proven proration from immutable SubscriptionPeriod rows",
            response_model=ApiResponse[dict])
async def update_plan(tenant_id: uuid.UUID, r: Request,
                       u: UserContext=Depends(require_permission(P.TENANT_BILLING_MANAGE)),
                       s: SubscriptionService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.update_plan(tenant_id, body["new_plan"], body.get("billing_cycle","monthly")), _rid(r), ENGINE_ID)
@router.post("/tenants/{tenant_id}/cancel", response_model=ApiResponse[dict])
async def cancel(tenant_id: uuid.UUID, r: Request, u: UserContext=Depends(require_super_admin),
                  s: SubscriptionService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.cancel_subscription(tenant_id, body.get("reason","")), _rid(r), ENGINE_ID)
@router.post("/tenants/{tenant_id}/pause", response_model=ApiResponse[dict])
async def pause(tenant_id: uuid.UUID, r: Request, u: UserContext=Depends(require_super_admin),
                 s: SubscriptionService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.pause_subscription(tenant_id), _rid(r), ENGINE_ID)
@router.post("/tenants/{tenant_id}/resume", response_model=ApiResponse[dict])
async def resume(tenant_id: uuid.UUID, r: Request, u: UserContext=Depends(require_super_admin),
                  s: SubscriptionService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.resume_subscription(tenant_id), _rid(r), ENGINE_ID)
@router.get("/tenants/{tenant_id}/period",
            summary="Usage from canonical CommissionRecord source — not cached value",
            response_model=ApiResponse[dict])
async def current_period(tenant_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                          s: SubscriptionService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_current_period(tenant_id), _rid(r), ENGINE_ID)
@router.get("/tenants/{tenant_id}/history", response_model=ApiResponse[dict])
async def billing_history(tenant_id: uuid.UUID, r: Request, limit: int=Query(12,ge=1,le=60),
                           cursor: str|None=Query(None), u: UserContext=Depends(get_current_user),
                           s: SubscriptionService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_billing_history(tenant_id, limit, cursor), _rid(r), ENGINE_ID)
@router.get("/tenants/{tenant_id}/proration-preview",
            summary="Preview proration before plan change — uses immutable period records",
            response_model=ApiResponse[dict])
async def proration_preview(tenant_id: uuid.UUID, r: Request,
                             new_plan: str=Query(...), billing_cycle: str=Query("monthly"),
                             u: UserContext=Depends(get_current_user),
                             s: SubscriptionService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.preview_proration(tenant_id, new_plan, billing_cycle), _rid(r), ENGINE_ID)
