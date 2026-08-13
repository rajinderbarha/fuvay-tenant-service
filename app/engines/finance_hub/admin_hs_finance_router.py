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
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext, get_current_user, require_super_admin
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_vertical_enabled
from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
from app.schemas.base import ApiResponse, ok

_hs_enabled = Depends(require_vertical_enabled("home_services"))

router = APIRouter(
    prefix="/v1/admin/home-services/finance",
    tags=["Admin — Home Services Finance"],
    dependencies=[_hs_enabled],
)
canonical_router = APIRouter(
    prefix="/v1/admin/finance/home-services",
    tags=["Admin — Home Services Finance"],
    dependencies=[_hs_enabled],
)
ENGINE_ID = "home_services_finance"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_super_admin)) -> HomeServicesFinanceService:
    return HomeServicesFinanceService(
        db=db, request_id=getattr(r.state, "request_id", "—"),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
    )


def _credit_svc(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u: UserContext = Depends(get_current_user),
) -> HomeServicesFinanceService:
    return HomeServicesFinanceService(
        db=db, request_id=getattr(r.state, "request_id", "—"),
        actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
    )


class CreditAdjustmentRequest(BaseModel):
    tenant_id: uuid.UUID
    direction: Literal["credit", "debit"]
    credit_units: Decimal = Field(gt=0)
    reason_code: str = Field(min_length=1, max_length=80)
    detailed_reason: str = Field(min_length=3, max_length=1000)
    supporting_reference: str | None = Field(default=None, max_length=200)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/overview", response_model=ApiResponse[dict], summary="Home Services finance overview")
async def overview(r: Request, date_from: str | None = Query(None), date_to: str | None = Query(None),
                    s: HomeServicesFinanceService = Depends(_svc)):
    return ok(await s.get_overview(date_from, date_to), _rid(r), ENGINE_ID)


@router.get("/ledger-health", response_model=ApiResponse[dict], summary="Credit ledger health status strip")
async def ledger_health(r: Request, s: HomeServicesFinanceService = Depends(_svc)):
    return ok(await s.get_ledger_health(), _rid(r), ENGINE_ID)


# Canonical Home Services credit-account surface. These routes deliberately
# use a vertical-specific prefix: generic Finance Hub records are not
# interchangeable with provider usage credits.

@canonical_router.get(
    "/summary", response_model=ApiResponse[dict], summary="Home Services charge summary",
    dependencies=[Depends(require_permission(P.FINANCE_HOME_SERVICES_CREDITS_VIEW))],
)
async def finance_summary(
    r: Request,
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    s: HomeServicesFinanceService = Depends(_credit_svc),
):
    return ok(await s.get_summary(date_from, date_to), _rid(r), ENGINE_ID)


@canonical_router.get(
    "/credit-accounts", response_model=ApiResponse[dict], summary="List usage-credit accounts",
    dependencies=[Depends(require_permission(P.FINANCE_HOME_SERVICES_CREDITS_VIEW))],
)
async def list_credit_accounts(
    r: Request,
    q: str | None = Query(None),
    low_balance_only: bool = Query(False, alias="lowBalanceOnly"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    s: HomeServicesFinanceService = Depends(_credit_svc),
):
    data = await s.list_credit_accounts(
        q=q, low_balance_only=low_balance_only, page=page, page_size=page_size,
    )
    return ok(data, _rid(r), ENGINE_ID)


@canonical_router.get(
    "/credit-ledger", response_model=ApiResponse[dict], summary="List usage-credit ledger",
    dependencies=[Depends(require_permission(P.FINANCE_HOME_SERVICES_LEDGER_VIEW))],
)
async def list_credit_ledger(
    r: Request,
    tenant_id: uuid.UUID | None = Query(None),
    job_id: uuid.UUID | None = Query(None),
    event_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    s: HomeServicesFinanceService = Depends(_credit_svc),
):
    data = await s.list_credit_ledger(
        tenant_id=tenant_id, job_id=job_id, event_type=event_type, page=page, page_size=page_size,
    )
    return ok(data, _rid(r), ENGINE_ID)


@canonical_router.get(
    "/credit-ledger/{entry_id}", response_model=ApiResponse[dict], summary="Usage-credit ledger detail",
    dependencies=[Depends(require_permission(P.FINANCE_HOME_SERVICES_LEDGER_VIEW))],
)
async def credit_ledger_detail(
    entry_id: uuid.UUID,
    r: Request,
    s: HomeServicesFinanceService = Depends(_credit_svc),
):
    return ok(await s.get_ledger_entry_detail(entry_id), _rid(r), ENGINE_ID)


@canonical_router.post(
    "/adjustments", response_model=ApiResponse[dict], summary="Create an audited usage-credit adjustment",
    dependencies=[Depends(require_permission(P.FINANCE_HOME_SERVICES_ADJUSTMENTS_CREATE))],
)
async def create_credit_adjustment(
    r: Request,
    payload: CreditAdjustmentRequest,
    s: HomeServicesFinanceService = Depends(_credit_svc),
):
    data = await s.create_manual_adjustment(
        tenant_id=payload.tenant_id,
        direction=payload.direction,
        credit_units=payload.credit_units,
        reason_code=payload.reason_code,
        detailed_reason=payload.detailed_reason,
        supporting_reference=payload.supporting_reference,
    )
    return ok(data, _rid(r), ENGINE_ID)


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
