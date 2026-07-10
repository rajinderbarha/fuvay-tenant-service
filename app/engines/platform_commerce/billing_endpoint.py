"""Billing Router — HTTP endpoints. Added to Platform Commerce engine."""
import uuid
from decimal import Decimal
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.platform_commerce.billing_router import BillingRouterService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("billing_router.router")
router = APIRouter(prefix="/v1/billing", tags=["Billing Router"])
ENGINE_ID = "billing_router"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> BillingRouterService:
    return BillingRouterService(db=db,
                                 request_id=getattr(r.state,"request_id","—"),
                                 actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                                 actor_role=u.role)
def _rid(r): return getattr(r.state,"request_id","—")


@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Billing Router",
            "version": "14.0.0", "endpoint_count": 10, "status": "active",
            "location": "Inside Platform Commerce engine — not a new engine",
            "capabilities": [
                "immutable_profile_after_activation",
                "select_for_update_on_activation",
                "append_only_routing_log",
                "versioned_commission_rates",
                "redis_cache_with_db_source_of_truth",
                "vertical_aware_billing_dispatch",
                "two_layer_duplicate_prevention",
                "atomic_cache_invalidation",
            ]}


@router.post("/profiles",
             summary="Activate billing profile — SELECT FOR UPDATE NOWAIT, cache invalidated first",
             status_code=status.HTTP_201_CREATED,
             response_model=ApiResponse[dict])
async def activate_profile(r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: BillingRouterService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.activate_profile(
        uuid.UUID(body["tenant_id"]), body["billing_mode"],
        body.get("vertical", "home_services"),
        body.get("plan_type")), _rid(r), ENGINE_ID)


@router.get("/profiles/{tenant_id}",
            summary="Get active billing profile — Redis cache, DB fallback",
            response_model=ApiResponse[dict])
async def get_profile(tenant_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(get_current_user),
                       s: BillingRouterService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_profile(tenant_id), _rid(r), ENGINE_ID)


@router.get("/profiles/{tenant_id}/history",
            summary="Full billing mode history — immutable, every change recorded",
            response_model=ApiResponse[dict])
async def profile_history(tenant_id: uuid.UUID, r: Request,
                           u: UserContext = Depends(require_super_admin),
                           s: BillingRouterService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_profile_history(tenant_id), _rid(r), ENGINE_ID)


@router.post("/profiles/{tenant_id}/change-mode",
             summary="Change billing mode — deactivates old + creates new atomically",
             response_model=ApiResponse[dict])
async def change_mode(tenant_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(require_super_admin),
                       s: BillingRouterService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.change_billing_mode(
        tenant_id, body["new_billing_mode"],
        body.get("new_vertical"), body.get("new_plan_type"),
        body.get("reason", "Admin initiated mode change")), _rid(r), ENGINE_ID)


@router.post("/route",
             summary="Route a billing operation to correct engine — logs every decision",
             response_model=ApiResponse[dict])
async def route_operation(r: Request,
                           u: UserContext = Depends(get_current_user),
                           s: BillingRouterService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.route(
        uuid.UUID(body["tenant_id"]),
        body["operation"],
        body.get("context", {})), _rid(r), ENGINE_ID)


@router.get("/configs",
            summary="Get vertical billing configs — versioned commission rates",
            response_model=ApiResponse[dict])
async def get_configs(r: Request,
                       vertical: str | None = Query(None),
                       u: UserContext = Depends(require_super_admin),
                       s: BillingRouterService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_billing_configs(vertical), _rid(r), ENGINE_ID)


@router.put("/configs",
            summary="Set billing config — never overwrites, closes old and inserts new version",
            response_model=ApiResponse[dict])
async def set_config(r: Request,
                      u: UserContext = Depends(require_super_admin),
                      s: BillingRouterService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.set_billing_config(
        body["vertical"], body.get("plan_type","starter"),
        body.get("billing_mode","credit_commission"),
        Decimal(str(body["commission_rate"])),
        body.get("notes")), _rid(r), ENGINE_ID)


@router.get("/logs/{tenant_id}",
            summary="Billing routing log — append-only, every decision recorded",
            response_model=ApiResponse[dict])
async def routing_logs(tenant_id: uuid.UUID, r: Request,
                        limit: int = Query(50,ge=1,le=200),
                        cursor: str | None = Query(None),
                        u: UserContext = Depends(require_super_admin),
                        s: BillingRouterService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_routing_logs(tenant_id, limit, cursor), _rid(r), ENGINE_ID)
