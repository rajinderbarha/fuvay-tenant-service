"""Read-only platform oversight for automatic provider SLA penalties.

Disputes, remedies, settlements, and customer credits are owned by the
customer and provider. Platform admins deliberately have no route here to
create, approve, execute, cancel, or alter those records.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.db import get_db
from app.engines.customer_credits.service import CustomerCreditService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/finance", tags=["admin-finance-oversight"])
ENGINE_ID = "customer_credits"


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@router.get("/penalties/summary")
async def get_penalty_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(P.FINANCE_PENALTIES_READ)),
) -> ApiResponse[dict]:
    service = CustomerCreditService(db, user.user_id, user.role)
    return ok(await service.get_penalty_summary(), _rid(request), ENGINE_ID)


@router.get("/penalties")
async def list_penalties(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(P.FINANCE_PENALTIES_READ)),
) -> ApiResponse[dict]:
    service = CustomerCreditService(db, user.user_id, user.role)
    data = await service.list_penalties(
        tenant_id=tenant_id, status=status, page=page, limit=limit,
    )
    return ok(data, _rid(request), ENGINE_ID)


@router.get("/vertical-config/{vertical_type}")
async def get_vertical_config(
    request: Request,
    vertical_type: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permission(P.FINANCE_READ)),
) -> ApiResponse[dict]:
    service = CustomerCreditService(db, user.user_id, user.role)
    return ok(await service.get_vertical_config(vertical_type), _rid(request), ENGINE_ID)
