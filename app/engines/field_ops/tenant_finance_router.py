"""Field Ops Engine — Step 9: Tenant Finance Router (own tenant only)."""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.engines.field_ops.billing_service import BillingService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/tenant/finance", tags=["Tenant Finance"])
ENGINE_ID = "commerce"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.TENANT_BILLING_READ))) -> BillingService:
    return BillingService(db=db, request_id=getattr(r.state, "request_id", "—"),
                           actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
                           actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)


def _rid(r): return getattr(r.state, "request_id", "—")
def _tid(u: UserContext) -> uuid.UUID: return uuid.UUID(u.tenant_id)


@router.get("/summary", summary="Step 9: My tenant's finance summary", response_model=ApiResponse[dict])
async def finance_summary(r: Request, u: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                           s: BillingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_tenant_finance_summary(_tid(u)), _rid(r), ENGINE_ID)


@router.get("/invoices", summary="Step 9: My tenant's invoices", response_model=ApiResponse[dict])
async def finance_invoices(r: Request,
                            status_filter: str | None = Query(None, alias="status"),
                            u: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                            s: BillingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_tenant_invoices(_tid(u), status_filter), _rid(r), ENGINE_ID)


@router.get("/payments", summary="Step 9: My tenant's payments", response_model=ApiResponse[dict])
async def finance_payments(r: Request, u: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                            s: BillingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_tenant_payments(_tid(u)), _rid(r), ENGINE_ID)


@router.get("/commissions", summary="Step 9: My tenant's commission history", response_model=ApiResponse[dict])
async def finance_commissions(r: Request, u: UserContext = Depends(require_permission(P.TENANT_BILLING_READ)),
                               s: BillingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_tenant_commissions(_tid(u)), _rid(r), ENGINE_ID)


# GET /v1/tenant/wallet[/ledger] is owned by tenant_engine.portal_router.
