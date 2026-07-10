"""Provider/tenant finance view — /v1/provider/finance/credits and penalties."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.auth import require_technician
from app.engines.customer_credits.service import CustomerCreditService, DisputeSettlementService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/provider/finance", tags=["provider-finance"])
ENGINE_ID = "customer_credits"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _require_tenant(u):
    if not getattr(u, "tenant_id", None):
        from app.exceptions import ServiceOSException
        raise ServiceOSException("FORBIDDEN", "No tenant context in token.")


@router.get("/credits/summary")
async def tenant_credits_summary(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_technician),
) -> ApiResponse[dict]:
    _require_tenant(u)
    svc = CustomerCreditService(db, u.user_id, u.role)
    return ok(await svc.get_credit_summary(), _rid(r), ENGINE_ID)


@router.get("/penalties/summary")
async def tenant_penalties_summary(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_technician),
) -> ApiResponse[dict]:
    _require_tenant(u)
    svc = CustomerCreditService(db, u.user_id, u.role)
    return ok(await svc.get_penalty_summary(), _rid(r), ENGINE_ID)


@router.get("/penalties")
async def list_tenant_penalties(
    r: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_technician),
) -> ApiResponse[dict]:
    _require_tenant(u)
    tid = uuid.UUID(str(u.tenant_id))
    svc = CustomerCreditService(db, u.user_id, u.role)
    return ok(await svc.list_penalties(tenant_id=tid, status=status,
                                        page=page, limit=limit), _rid(r), ENGINE_ID)


@router.get("/settlements")
async def list_tenant_settlements(
    r: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_technician),
) -> ApiResponse[dict]:
    _require_tenant(u)
    tid = uuid.UUID(str(u.tenant_id))
    svc = DisputeSettlementService(db, u.user_id, u.role)
    return ok(await svc.list_settlements(page=page, limit=limit,
                                          status=status, tenant_id=tid), _rid(r), ENGINE_ID)
