"""Global Services — customer router. List the active promotional cards
(same list for every customer, no zipcode/vertical filtering anywhere)
and submit a lead."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_customer, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.global_services.service import GlobalServicesService

router = APIRouter(prefix="/v1/customer/global-services", tags=["Global Services — Customer"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(db: AsyncSession = Depends(get_db)) -> GlobalServicesService:
    return GlobalServicesService(db)


@router.get("", response_model=ApiResponse[list])
async def list_services(r: Request, u: UserContext = Depends(require_customer),
                        s: GlobalServicesService = Depends(_svc)):
    return ok(await s.list_services(include_inactive=False), _rid(r))


@router.post("/leads", response_model=ApiResponse[dict])
async def create_lead(r: Request, u: UserContext = Depends(require_customer),
                      s: GlobalServicesService = Depends(_svc), db: AsyncSession = Depends(get_db)):
    body = await r.json()
    data = await s.create_lead(body, customer_id=uuid.UUID(u.user_id) if u.user_id else None)
    await db.commit()
    return ok(data, _rid(r))
