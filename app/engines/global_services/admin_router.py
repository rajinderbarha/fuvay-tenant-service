from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.global_services.service import GlobalServicesService
from app.schemas.base import ApiResponse, ok


router = APIRouter(prefix="/v1/admin/global-services", tags=["Global Services — Admin"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "—")


def _service(db: AsyncSession = Depends(get_db)) -> GlobalServicesService:
    return GlobalServicesService(db)


@router.get("", response_model=ApiResponse[list])
async def list_services(
    request: Request,
    include_inactive: bool = Query(True),
    _: UserContext = Depends(require_super_admin),
    service: GlobalServicesService = Depends(_service),
):
    return ok(await service.list_services(include_inactive=include_inactive), _request_id(request))


@router.post("", response_model=ApiResponse[dict])
async def create_service(
    request: Request,
    user: UserContext = Depends(require_super_admin),
    service: GlobalServicesService = Depends(_service),
    db: AsyncSession = Depends(get_db),
):
    data = await service.create_service(
        await request.json(), actor_id=uuid.UUID(user.user_id) if user.user_id else None
    )
    await db.commit()
    return ok(data, _request_id(request))


@router.put("/{service_id}", response_model=ApiResponse[dict])
async def update_service(
    service_id: uuid.UUID,
    request: Request,
    _: UserContext = Depends(require_super_admin),
    service: GlobalServicesService = Depends(_service),
    db: AsyncSession = Depends(get_db),
):
    data = await service.update_service(service_id, await request.json())
    await db.commit()
    return ok(data, _request_id(request))


@router.delete("/{service_id}", response_model=ApiResponse[dict])
async def deactivate_service(
    service_id: uuid.UUID,
    request: Request,
    _: UserContext = Depends(require_super_admin),
    service: GlobalServicesService = Depends(_service),
    db: AsyncSession = Depends(get_db),
):
    data = await service.deactivate_service(service_id)
    await db.commit()
    return ok(data, _request_id(request))


@router.get("/leads/summary", response_model=ApiResponse[dict])
async def lead_summary(
    request: Request,
    _: UserContext = Depends(require_super_admin),
    service: GlobalServicesService = Depends(_service),
):
    return ok(await service.summary(), _request_id(request))


@router.get("/leads", response_model=ApiResponse[dict])
async def list_leads(
    request: Request,
    status: str | None = Query(None),
    global_service_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: UserContext = Depends(require_super_admin),
    service: GlobalServicesService = Depends(_service),
):
    return ok(
        await service.list_leads(
            status=status,
            global_service_id=global_service_id,
            page=page,
            page_size=page_size,
        ),
        _request_id(request),
    )


@router.put("/leads/{lead_id}", response_model=ApiResponse[dict])
async def update_lead(
    lead_id: uuid.UUID,
    request: Request,
    user: UserContext = Depends(require_super_admin),
    service: GlobalServicesService = Depends(_service),
    db: AsyncSession = Depends(get_db),
):
    data = await service.update_lead(
        lead_id,
        await request.json(),
        actor_id=uuid.UUID(user.user_id) if user.user_id else None,
    )
    await db.commit()
    return ok(data, _request_id(request))
