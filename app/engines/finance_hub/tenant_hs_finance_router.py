"""TENANT-HS-FINANCE-HUB-01 — tenant-facing Home Services Finance Hub API.

Every endpoint here:
  * resolves tenant_id from the caller's JWT ONLY (never a body/query param);
  * is gated on the tenant's Home Services enrollment being ACTIVE
    (require_tenant_vertical_active) so a disabled vertical blocks new
    mutations while historical records stay queryable through Admin;
  * is gated on a granular finance:tenant:* permission (section 20);
  * is Home-Services-scoped — no other vertical's ledger can be reached.

Deliberately NOT here: provider payouts, platform settlement, manual ledger
posting, and policy editing.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_tenant_vertical_active
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok
from app.integrations import razorpay_client
from app.engines.finance_hub.tenant_hs_finance_service import TenantHomeServicesFinanceService
from app.engines.vertical_catalog.home_services_setup_service import HOME_SERVICES_VERTICAL_KEY

router = APIRouter(prefix="/v1/tenant/home-services/finance",
                   tags=["Tenant Home Services Finance Hub"])
ENGINE_ID = "finance_hub"

_hs_active = require_tenant_vertical_active(HOME_SERVICES_VERTICAL_KEY)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", None) or r.headers.get("X-Request-ID", "—")


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException("NO_TENANT_CONTEXT",
                                 "This endpoint requires a tenant account.", status_code=403)
    return uuid.UUID(user.tenant_id)


def _svc(r: Request, db: AsyncSession, user: UserContext) -> TenantHomeServicesFinanceService:
    return TenantHomeServicesFinanceService(
        db, tenant_id=_tid(user), request_id=_rid(r),
        actor_id=uuid.UUID(user.user_id) if user.user_id else None,
        actor_role=user.role,
        actor_ip=r.client.host if r.client else None,
    )


# ── 1. Overview ──────────────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse, summary="Finance Hub overview (all KPI + tab seed data)")
async def get_finance_overview(
    r: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_READ)),
    _guard: UserContext = Depends(_hs_active),
):
    return ok(await _svc(r, db, user).get_overview(), _rid(r), ENGINE_ID)


# ── 2. Usage credits ─────────────────────────────────────────────────────────

@router.get("/usage-credits", response_model=ApiResponse, summary="Usage-credit wallet")
async def get_usage_credits(
    r: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_READ)),
    _guard: UserContext = Depends(_hs_active),
):
    svc = _svc(r, db, user)
    wallet = await svc.get_usage_credits()
    wallet["ledger"] = await svc.get_transactions(ledger="usage_credits", page=1, page_size=50)
    return ok(wallet, _rid(r), ENGINE_ID)



# ── 4. Transactions ──────────────────────────────────────────────────────────

@router.get("/transactions", response_model=ApiResponse, summary="Financial activity (all 4 ledgers)")
async def get_transactions(
    r: Request,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    ledger: str | None = Query(None),
    type_: str | None = Query(None, alias="type"),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_TRANSACTIONS_READ)),
    _guard: UserContext = Depends(_hs_active),
):
    svc = _svc(r, db, user)
    return ok(await svc.get_transactions(date_from=date_from, date_to=date_to, ledger=ledger,
                                        type_=type_, status=status, page=page, page_size=page_size),
              _rid(r), ENGINE_ID)


# ── 5. Policy (read-only) ────────────────────────────────────────────────────

@router.get("/policy", response_model=ApiResponse, summary="Published finance policy (read-only)")
async def get_policy(
    r: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_POLICY_READ)),
    _guard: UserContext = Depends(_hs_active),
):
    svc = _svc(r, db, user)
    data = await svc.get_policy()
    data["audit"] = await svc.list_audit(page=1, page_size=25)
    return ok(data, _rid(r), ENGINE_ID)


@router.get("/commission-rates", response_model=ApiResponse,
            summary="Provider commission rate actually applied to this tenant's completed jobs")
async def get_commission_rates(
    r: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_POLICY_READ)),
    _guard: UserContext = Depends(_hs_active),
):
    """Closes a real transparency gap: the tenant had NO way to see the
    commission rate being charged. The dashboard's "Monetization Status"
    widget read provider_monetization_statuses -- a table that does not
    exist in this schema (its endpoint swallows the failure and returns a
    hardcoded not-ready fallback), so it reported a fabricated status
    unrelated to actual charging. This returns the rate resolved the same
    way job completion resolves it."""
    svc = _svc(r, db, user)
    return ok(await svc.get_commission_rates(), _rid(r), ENGINE_ID)


# ── 6. Top-ups ───────────────────────────────────────────────────────────────

@router.get("/credit-packages", response_model=ApiResponse, summary="Admin-approved credit packages")
async def get_credit_packages(
    r: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_READ)),
    _guard: UserContext = Depends(_hs_active),
):
    return ok({"packages": await _svc(r, db, user).get_credit_packages()}, _rid(r), ENGINE_ID)


@router.get("/top-ups", response_model=ApiResponse, summary="Credit top-up orders")
async def list_topups(
    r: Request,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_TRANSACTIONS_READ)),
    _guard: UserContext = Depends(_hs_active),
):
    return ok(await _svc(r, db, user).list_topups(status=status, page=page, page_size=page_size),
              _rid(r), ENGINE_ID)


class CreateTopupRequest(BaseModel):
    quantity: int = Field(1, ge=1, le=100,
                          description="Multiplier on the flat per-unit price. Ignored if credit_package_id is set.")
    payment_method: str = Field("razorpay", max_length=30)
    credit_package_id: uuid.UUID | None = Field(
        None, description="Buy a specific admin-defined package instead of quantity x flat price.")


@router.post("/top-ups", response_model=ApiResponse, status_code=201,
             summary="Create a credit top-up order (posts NO credit)")
async def create_topup(
    body: CreateTopupRequest,
    r: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_FINANCE_BUY_CREDITS)),
    _guard: UserContext = Depends(_hs_active),
):
    """Amounts are ALWAYS re-derived server-side -- either from the
    published policy (flat per-unit price x quantity) or from an
    admin-defined CreditPackage (fixed bundle) -- never client-supplied."""
    return ok(await _svc(r, db, user).create_topup(
        quantity=body.quantity, payment_method=body.payment_method,
        credit_package_id=body.credit_package_id), _rid(r), ENGINE_ID)


class ConfirmTopupRequest(BaseModel):
    gateway_order_id: str = Field(..., max_length=100)
    gateway_payment_id: str = Field(..., max_length=100)
    signature: str = Field(..., max_length=200)


@router.post("/top-ups/confirm", response_model=ApiResponse,
             summary="Confirm a top-up via Razorpay Checkout signature")
async def confirm_topup(
    body: ConfirmTopupRequest,
    r: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_FINANCE_BUY_CREDITS)),
    _guard: UserContext = Depends(_hs_active),
):
    """Client-reported success is NOT trusted: the HMAC signature over
    "{order_id}|{payment_id}" is verified against RAZORPAY_KEY_SECRET before
    a single credit is posted, and posting itself is idempotent on
    `topup_credit_grant:{order_id}:1`."""
    return ok(await _svc(r, db, user).confirm_topup_payment(
        gateway_order_id=body.gateway_order_id,
        gateway_payment_id=body.gateway_payment_id,
        signature=body.signature), _rid(r), ENGINE_ID)


@router.get("/top-ups/{topup_id}", response_model=ApiResponse, summary="Top-up order detail + receipt")
async def get_topup(
    topup_id: uuid.UUID,
    r: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_RECEIPTS_DOWNLOAD)),
    _guard: UserContext = Depends(_hs_active),
):
    return ok(await _svc(r, db, user).get_topup(topup_id), _rid(r), ENGINE_ID)


@router.post("/top-ups/{topup_id}/cancel", response_model=ApiResponse,
             summary="Cancel an abandoned top-up order (never touches a paid/credited order)")
async def cancel_topup(
    topup_id: uuid.UUID,
    r: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_mutation_permission(P.TENANT_FINANCE_BUY_CREDITS)),
    _guard: UserContext = Depends(_hs_active),
):
    return ok(await _svc(r, db, user).cancel_topup(topup_id), _rid(r), ENGINE_ID)


# ── 7. Gateway webhook (server-to-server, no user auth) ──────────────────────

@router.post("/top-ups/webhook", response_model=ApiResponse,
             summary="Razorpay webhook — signature-verified, duplicate-safe")
async def topup_webhook(r: Request, db: AsyncSession = Depends(get_db)):
    """Server-to-server confirmation path. Verifies the X-Razorpay-Signature
    HMAC over the RAW body (app.integrations.razorpay_client.verify_webhook_
    signature — the same function the proven payment webhook uses) before any
    effect. A duplicate delivery is a safe no-op via the top-up grant's
    idempotency key, and returns idempotent=true rather than an error."""
    raw = await r.body()
    sig = r.headers.get("x-razorpay-signature", "")
    if not razorpay_client.verify_webhook_signature(raw, sig):
        raise ServiceOSException("WEBHOOK_VERIFICATION_FAILED",
                                 "Invalid Razorpay webhook signature.", status_code=400)
    body = await r.json()
    from sqlalchemy import select as _select
    from app.engines.finance_hub.models import CreditTopupOrder
    order = (await db.execute(_select(CreditTopupOrder).where(
        CreditTopupOrder.gateway_order_id == body["gateway_order_id"]))).scalar_one_or_none()
    if not order:
        raise ServiceOSException("TOPUP_ORDER_NOT_FOUND",
                                 "No credit top-up order matches this gateway order id.", status_code=404)
    svc = TenantHomeServicesFinanceService(db, tenant_id=order.tenant_id, request_id=_rid(r),
                                          actor_role="system")
    return ok(await svc.confirm_topup_payment(
        gateway_order_id=body["gateway_order_id"],
        gateway_payment_id=body["gateway_payment_id"],
        signature=None, status_=body.get("status", "captured"),
        raw_payload=body, signature_verified=True), _rid(r), ENGINE_ID)


# ── 8. Deposit refund requests ───────────────────────────────────────────────

@router.get("/export", response_model=ApiResponse, summary="Export statement (own tenant + HS only)")
async def export_statement(
    r: Request,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    ledger: str | None = Query(None),
    status: str | None = Query(None),
    # The transactions view filters by event type, but export did not accept
    # `type` at all -- so exporting a type-filtered view silently produced a
    # WIDER set of rows than the screen was showing.
    type_: str | None = Query(None, alias="type"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_EXPORT)),
    _guard: UserContext = Depends(_hs_active),
):
    return ok(await _svc(r, db, user).export_transactions(
        date_from=date_from, date_to=date_to, ledger=ledger, status=status,
        type_=type_), _rid(r), ENGINE_ID)


# ── Admin-only refund decision (mounted here for cohesion, admin-gated) ──────

# This router sits under the `/v1/admin/finance/home-services` prefix, which
# test_home_services_admin_gating enumerates and requires to carry the static
# Home Services vertical guard -- so a disabled vertical cannot still be
# administered through it. The guard was missing when this router was first
# mounted; every sibling under that prefix (admin_hs_finance_router) applies it
# the same way, at router level.
from app.dependencies.vertical_guard import require_vertical_enabled as _require_vertical_enabled

# The deposit-refund admin router was removed with the security deposit
# itself (migration 317). There is no deposit to refund: a tenant now buys
# a top-up plan, whose credit is spent down rather than held and returned.
