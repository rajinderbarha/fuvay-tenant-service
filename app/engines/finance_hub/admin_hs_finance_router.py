"""Admin — Home Services Finance workspace (platform-wide).

The consolidated "Home Services Finance" admin page (frontend/super-admin/
app/admin/home-services/finance/page.tsx) was already fully built against
`HomeServicesFinanceService` (finance_hub/home_services_finance_service.py)
-- a ~1200-line, already-platform-wide service with real methods for every
tab (overview, direct payments, provider charges, credits, deposits,
warranty claims, invoices, refunds, charge config). That service was never
exposed by any admin router, so the page's `homeServicesFinanceApi` calls
(lib/api-hs-finance.ts) 404'd.

This router wires the Overview + Direct Customer Payments tabs first (the
sequencing the page owner chose): mounted at
/v1/admin/home-services/finance/* to sit alongside the already-mounted
monetization sub-router (.../finance/monetization/*) rather than colliding
with the separate, generic FinanceHubService routes already mounted at
/v1/admin/finance/* (deposits/topups/warranty-claims there are real and
unrelated to this page -- left untouched).

Supersedes the first-pass `invoice_payment/admin_direct_payments_router.py`,
which reimplemented direct-payments listing from scratch against the wrong
shape (no invoice_number, no charge-ledger detail) before this real,
already-built service was found. That file and its mount in main.py are
removed in the same change as this router's addition.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/home-services/finance", tags=["Admin — Home Services Finance"])
ENGINE_ID = "home_services_finance"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_super_admin)) -> HomeServicesFinanceService:
    return HomeServicesFinanceService(
        db=db, request_id=getattr(r.state, "request_id", "—"),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
    )


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/overview", response_model=ApiResponse[dict], summary="Home Services finance overview")
async def overview(r: Request, date_from: str | None = Query(None), date_to: str | None = Query(None),
                    s: HomeServicesFinanceService = Depends(_svc)):
    return ok(await s.get_overview(date_from, date_to), _rid(r), ENGINE_ID)


@router.get("/ledger-health", response_model=ApiResponse[dict], summary="Credit ledger health status strip")
async def ledger_health(r: Request, s: HomeServicesFinanceService = Depends(_svc)):
    return ok(await s.get_ledger_health(), _rid(r), ENGINE_ID)


# ── Direct Customer Payments ─────────────────────────────────────────────────

@router.get("/payments", response_model=ApiResponse[dict], summary="List direct customer-to-provider payments")
async def list_direct_payments(
    r: Request,
    payment_status: str | None = Query(None, alias="status"),
    tenant_id: str | None = Query(None),
    confirmed: bool | None = Query(None),
    q: str | None = Query(None),
    date_from: str | None = Query(None), date_to: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=500, alias="pageSize"),
    s: HomeServicesFinanceService = Depends(_svc),
):
    data = await s.list_direct_payments(
        payment_status=payment_status, tenant_id=tenant_id, confirmed=confirmed, q=q,
        date_from=date_from, date_to=date_to, page=page, page_size=page_size,
    )
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/payments/summary", response_model=ApiResponse[dict], summary="Direct payments summary cards")
async def direct_payments_summary(r: Request, date_from: str | None = Query(None), date_to: str | None = Query(None),
                                   s: HomeServicesFinanceService = Depends(_svc)):
    return ok(await s.get_direct_payments_summary(date_from, date_to), _rid(r), ENGINE_ID)


@router.get("/payments/{payment_id}", response_model=ApiResponse[dict], summary="Direct payment detail")
async def get_direct_payment(payment_id: uuid.UUID, r: Request, s: HomeServicesFinanceService = Depends(_svc)):
    return ok(await s.get_direct_payment_detail(payment_id), _rid(r), ENGINE_ID)


@router.post("/payments/{payment_id}/remind-customer", response_model=ApiResponse[dict],
             summary="Send a confirmation reminder to the customer")
async def remind_customer(payment_id: uuid.UUID, r: Request, u: UserContext = Depends(require_super_admin),
                           db: AsyncSession = Depends(get_db)):
    from app.engines.invoice_payment.direct_payments_service import DirectPaymentsService
    from app.engines.invoice_payment.models import ServicePaymentRecord
    pay = await db.get(ServicePaymentRecord, payment_id)
    from app.exceptions import NotFoundException
    if pay is None:
        raise NotFoundException("ServicePaymentRecord", str(payment_id))
    svc = DirectPaymentsService(db, pay.tenant_id, _rid(r))
    data = await svc.remind_customer(payment_id=payment_id, actor_user_id=u.user_id)
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/charge-config", response_model=ApiResponse[dict],
            summary="List per-service/job-type completion-charge credit amounts")
async def list_charge_config(r: Request, q: str | None = Query(None), is_active: bool | None = Query(None),
                              page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=500, alias="pageSize"),
                              s: HomeServicesFinanceService = Depends(_svc)):
    return ok(await s.list_charge_config(q=q, is_active=is_active, page=page, page_size=page_size), _rid(r), ENGINE_ID)


@router.post("/charge-config/{rule_id}", response_model=ApiResponse[dict],
             summary="Update a completion-charge credit amount")
async def update_charge_config(rule_id: uuid.UUID, r: Request, payload: dict = Body(...),
                                s: HomeServicesFinanceService = Depends(_svc)):
    data = await s.update_charge_config(rule_id, int(payload["completed_job_deduction_credits"]))
    return ok(data, _rid(r), ENGINE_ID)


@router.post("/payments/{payment_id}/open-dispute", response_model=ApiResponse[dict],
             summary="Open a payment dispute")
async def open_dispute(payment_id: uuid.UUID, r: Request, payload: dict = Body(default={}),
                        u: UserContext = Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    from app.engines.invoice_payment.direct_payments_service import DirectPaymentsService
    from app.engines.invoice_payment.models import ServicePaymentRecord
    pay = await db.get(ServicePaymentRecord, payment_id)
    from app.exceptions import NotFoundException
    if pay is None:
        raise NotFoundException("ServicePaymentRecord", str(payment_id))
    svc = DirectPaymentsService(db, pay.tenant_id, _rid(r))
    data = await svc.open_dispute(
        payment_id=payment_id, actor_user_id=u.user_id,
        description=payload.get("description") or "Opened by platform admin for review.",
    )
    return ok(data, _rid(r), ENGINE_ID)
