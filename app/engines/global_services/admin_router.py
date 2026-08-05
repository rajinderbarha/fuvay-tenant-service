"""Global Services — admin router. Super-admin CRUD over the promotional
service cards, plus the lead queue an admin works through to call
customers back."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.global_services.service import GlobalServicesService

router = APIRouter(prefix="/v1/admin/global-services", tags=["Global Services — Admin"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(db: AsyncSession = Depends(get_db)) -> GlobalServicesService:
    return GlobalServicesService(db)


@router.get("", response_model=ApiResponse[list])
async def list_services(r: Request, include_inactive: bool = Query(True),
                        u: UserContext = Depends(require_super_admin),
                        s: GlobalServicesService = Depends(_svc)):
    return ok(await s.list_services(include_inactive=include_inactive), _rid(r))


@router.post("", response_model=ApiResponse[dict])
async def create_service(r: Request, u: UserContext = Depends(require_super_admin),
                         s: GlobalServicesService = Depends(_svc), db: AsyncSession = Depends(get_db)):
    body = await r.json()
    data = await s.create_service(body, actor_id=uuid.UUID(u.user_id) if u.user_id else None)
    await db.commit()
    return ok(data, _rid(r))


@router.put("/{service_id}", response_model=ApiResponse[dict])
async def update_service(service_id: uuid.UUID, r: Request, u: UserContext = Depends(require_super_admin),
                         s: GlobalServicesService = Depends(_svc), db: AsyncSession = Depends(get_db)):
    body = await r.json()
    data = await s.update_service(service_id, body)
    await db.commit()
    return ok(data, _rid(r))


@router.delete("/{service_id}", response_model=ApiResponse[dict])
async def deactivate_service(service_id: uuid.UUID, r: Request, u: UserContext = Depends(require_super_admin),
                             s: GlobalServicesService = Depends(_svc), db: AsyncSession = Depends(get_db)):
    data = await s.delete_service(service_id)
    await db.commit()
    return ok(data, _rid(r))


@router.get("/leads/summary", response_model=ApiResponse[dict])
async def leads_summary(r: Request, u: UserContext = Depends(require_super_admin),
                        s: GlobalServicesService = Depends(_svc)):
    return ok(await s.summary(), _rid(r))


@router.get("/leads", response_model=ApiResponse[dict])
async def list_leads(r: Request, status: str | None = Query(None),
                     global_service_id: uuid.UUID | None = Query(None),
                     page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                     u: UserContext = Depends(require_super_admin),
                     s: GlobalServicesService = Depends(_svc)):
    return ok(await s.list_leads(status=status, global_service_id=global_service_id,
                                 page=page, page_size=page_size), _rid(r))


@router.put("/leads/{lead_id}", response_model=ApiResponse[dict])
async def update_lead(lead_id: uuid.UUID, r: Request, u: UserContext = Depends(require_super_admin),
                      s: GlobalServicesService = Depends(_svc), db: AsyncSession = Depends(get_db)):
    body = await r.json()
    data = await s.update_lead(lead_id, body, actor_id=uuid.UUID(u.user_id) if u.user_id else None)
    await db.commit()
    return ok(data, _rid(r))
