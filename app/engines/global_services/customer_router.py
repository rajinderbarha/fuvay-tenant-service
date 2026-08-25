from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, require_customer
from app.dependencies.db import get_db
from app.engines.global_services.service import GlobalServicesService
from app.schemas.base import ApiResponse, ok


router = APIRouter(prefix="/v1/customer/global-services", tags=["Global Services — Customer"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "—")


def _service(db: AsyncSession = Depends(get_db)) -> GlobalServicesService:
    return GlobalServicesService(db)


@router.get("", response_model=ApiResponse[list])
async def list_services(
    request: Request,
    _: UserContext = Depends(require_customer),
    service: GlobalServicesService = Depends(_service),
):
    return ok(await service.list_services(include_inactive=False), _request_id(request))


@router.post("/leads", response_model=ApiResponse[dict])
async def create_lead(
    request: Request,
    user: UserContext = Depends(require_customer),
    service: GlobalServicesService = Depends(_service),
    db: AsyncSession = Depends(get_db),
):
    data = await service.create_lead(
        await request.json(),
        customer_id=uuid.UUID(user.user_id) if user.user_id else None,
    )
    await db.commit()
    return ok(data, _request_id(request))
