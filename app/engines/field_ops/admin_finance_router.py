"""Field Ops Engine — Step 9: Super Admin Finance Router (platform-wide)."""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.field_ops.billing_service import BillingService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/finance", tags=["Admin Finance"])
ENGINE_ID = "commerce"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_super_admin)) -> BillingService:
    return BillingService(db=db, request_id=getattr(r.state, "request_id", "—"),
                           actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)


def _rid(r): return getattr(r.state, "request_id", "—")


@router.get("/summary", summary="Step 9: Platform-wide finance summary", response_model=ApiResponse[dict])
async def admin_finance_summary(r: Request, u: UserContext = Depends(require_super_admin),
                                 s: BillingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.admin_finance_summary(), _rid(r), ENGINE_ID)


@router.get("/invoices", summary="Step 9: All invoices (platform-wide)", response_model=ApiResponse[dict])
async def admin_invoices(r: Request, u: UserContext = Depends(require_super_admin),
                          s: BillingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.admin_list_invoices(), _rid(r), ENGINE_ID)


@router.get("/payments", summary="Step 9: All payments (platform-wide)", response_model=ApiResponse[dict])
async def admin_payments(r: Request, u: UserContext = Depends(require_super_admin),
                          s: BillingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.admin_list_payments(), _rid(r), ENGINE_ID)


@router.get("/commissions", summary="Step 9: All commissions (platform-wide)", response_model=ApiResponse[dict])
async def admin_commissions(r: Request, u: UserContext = Depends(require_super_admin),
                             s: BillingService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.admin_list_commissions(), _rid(r), ENGINE_ID)


# Tenant usage-credit routes are owned exclusively by tenant_engine.admin_router.
