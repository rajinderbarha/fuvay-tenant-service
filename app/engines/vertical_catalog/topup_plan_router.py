"""Admin — Home Services Top-up Plan (starter credit package + activation
security deposit). Canonical route: /admin/home-services/finance?tab=
monetization (rendered alongside the provider/customer charge policy, same
page, distinct backend). See topup_plan_service.py docstring for why this
needed a new service+router: the versioned table already existed with real
resolvers reading it, but nothing ever let an admin write to it.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.vertical_catalog.topup_plan_service import HomeServicesTopupPlanService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/home-services/finance/monetization/topup-plan",
                    tags=["Home Services Finance — Top-up Plan"])
_svc = HomeServicesTopupPlanService()
_HS_KEY = "home_services"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/current", response_model=ApiResponse)
async def get_current(r: Request, db: AsyncSession = Depends(get_db),
                       u: UserContext = Depends(require_super_admin)):
    return ok(await _svc.get_current(db, _HS_KEY), _rid(r))


@router.get("/draft", response_model=ApiResponse)
async def get_draft(r: Request, db: AsyncSession = Depends(get_db),
                     u: UserContext = Depends(require_super_admin)):
    return ok(await _svc.get_draft(db, _HS_KEY), _rid(r))


@router.get("/history", response_model=ApiResponse)
async def get_history(r: Request, db: AsyncSession = Depends(get_db),
                       u: UserContext = Depends(require_super_admin)):
    return ok({"items": await _svc.list_history(db, _HS_KEY)}, _rid(r))


@router.post("/draft", response_model=ApiResponse)
async def save_draft(r: Request, db: AsyncSession = Depends(get_db),
                      u: UserContext = Depends(require_super_admin)):
    body = await r.json()
    data = await _svc.save_draft(db, _HS_KEY, body, actor_id=uuid.UUID(u.user_id) if u.user_id else None)
    return ok(data, _rid(r))


@router.delete("/draft", response_model=ApiResponse)
async def discard_draft(r: Request, db: AsyncSession = Depends(get_db),
                         u: UserContext = Depends(require_super_admin)):
    data = await _svc.discard_draft(db, _HS_KEY, actor_id=uuid.UUID(u.user_id) if u.user_id else None)
    return ok(data, _rid(r))


@router.post("/validate", response_model=ApiResponse)
async def validate(r: Request, u: UserContext = Depends(require_super_admin)):
    body = await r.json()
    return ok(_svc.validate(body), _rid(r))


@router.post("/publish", response_model=ApiResponse)
async def publish(r: Request, db: AsyncSession = Depends(get_db),
                   u: UserContext = Depends(require_super_admin)):
    body = await r.json()
    data = await _svc.publish(db, _HS_KEY, actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                               reason=body.get("reason", ""))
    return ok(data, _rid(r))
