"""Home Services Dashboard — admin router. Mounted at
/v1/admin/home-services/dashboard. Category-specific, gated by
require_vertical_enabled("home_services") -- never a modification of the
generic platform /admin/dashboard.

Customer Intelligence and Operational Metrics are exposed as SEPARATE
endpoints (not only a combined one) so the frontend can independently
retry a failed section without the whole dashboard failing -- "a failed
metric must show unavailable, not zero" (USER REQ).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_vertical_enabled
from app.engines.tenant_engine.hs_dashboard_service import HomeServicesDashboardService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/home-services/dashboard", tags=["Home Services Dashboard"])
ENGINE_ID = "hs_dashboard"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.HOME_SERVICES_CUSTOMERS_VIEW)),
         _v: UserContext = Depends(require_vertical_enabled("home_services"))) -> HomeServicesDashboardService:
    return HomeServicesDashboardService(db=db, request_id=_rid(r),
                                         actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)


@router.get("/customer-intelligence", response_model=ApiResponse[dict], summary="Home Services dashboard customer intelligence cards")
async def hs_dashboard_customer_intelligence(r: Request, s: HomeServicesDashboardService = Depends(_svc)):
    return ok(await s.get_customer_intelligence(), _rid(r), ENGINE_ID)


@router.get("/operational-metrics", response_model=ApiResponse[dict], summary="Home Services dashboard operational metrics")
async def hs_dashboard_operational_metrics(r: Request, s: HomeServicesDashboardService = Depends(_svc)):
    return ok(await s.get_operational_metrics(), _rid(r), ENGINE_ID)


@router.get("", response_model=ApiResponse[dict], summary="Home Services dashboard combined summary")
async def hs_dashboard_summary(r: Request, s: HomeServicesDashboardService = Depends(_svc)):
    return ok(await s.get_summary(), _rid(r), ENGINE_ID)
