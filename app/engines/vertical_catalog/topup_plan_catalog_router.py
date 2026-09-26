"""Top-up plan catalogue API.

Two surfaces:

  /v1/admin/home-services/topup-plans   platform admin authors what is sold
  /v1/tenant/home-services/topup-plans  a tenant sees what it can buy

The tenant surface is read-only and shows active plans only. Buying one goes
through the existing activation-funding checkout
(`POST /v1/tenant/home-services/activation/funding/order`),
which prices the order server-side from the catalogue — a client never sends
an amount.
"""
from __future__ import annotations

import uuid
from io import BytesIO
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, permission_checker, require_permission
from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok

from app.engines.vertical_catalog import topup_plan_catalog_service as svc

ENGINE_ID = "vertical_catalog"
HOME_SERVICES = "home_services"

admin_router = APIRouter(prefix="/v1/admin/home-services/topup-plans",
                         tags=["Admin — Home Services Top-up Plans"])
tenant_router = APIRouter(prefix="/v1/tenant/home-services/topup-plans",
                          tags=["Tenant — Home Services Top-up Plans"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", None) or r.headers.get("X-Request-ID", "—")


def _require_manage(user: UserContext) -> None:
    if not permission_checker.has(user.role, P.TOPUP_PLAN_MANAGE, user.permission_overrides):
        raise HTTPException(403, "You cannot manage top-up plans.")


def _require_view(user: UserContext) -> None:
    if not permission_checker.has(user.role, P.TOPUP_PLAN_VIEW, user.permission_overrides):
        raise HTTPException(403, "You cannot view top-up plans.")


class PlanIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    base_amount: Decimal = Field(..., gt=0)
    seats: int = Field(..., ge=0)
    gst_percent: Decimal = Field(Decimal("18"), ge=0, le=100)
    description: str | None = None
    is_active: bool = True
    is_default: bool = False
    sort_order: int = 0
    #: 0 = the purchase never lapses (the behaviour before validity existed).
    validity_days: int = Field(0, ge=0, le=3650)


class PlanPatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    base_amount: Decimal | None = Field(None, gt=0)
    seats: int | None = Field(None, ge=0)
    gst_percent: Decimal | None = Field(None, ge=0, le=100)
    description: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    sort_order: int | None = None
    validity_days: int | None = Field(None, ge=0, le=3650)


# ── Admin ────────────────────────────────────────────────────────────────────
@admin_router.get("", response_model=ApiResponse[dict], summary="List top-up plans")
async def admin_list(
    r: Request,
    active_only: bool = Query(False),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_view(user)
    plans = await svc.list_plans(db, vertical_key=HOME_SERVICES, active_only=active_only)
    return ok({"plans": plans, "total": len(plans)}, _rid(r), engine_id=ENGINE_ID)


@admin_router.post("", response_model=ApiResponse[dict], status_code=201,
                   summary="Create a top-up plan")
async def admin_create(
    body: PlanIn,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manage(user)
    actor = None
    try:
        actor = uuid.UUID(str(user.user_id))
    except (TypeError, ValueError):
        actor = None
    plan = await svc.create_plan(
        db, vertical_key=HOME_SERVICES, name=body.name, base_amount=body.base_amount,
        seats=body.seats, gst_percent=body.gst_percent, description=body.description,
        is_active=body.is_active, is_default=body.is_default, sort_order=body.sort_order,
        validity_days=body.validity_days,
        actor_id=actor,
    )
    await db.commit()
    return ok(plan, _rid(r), engine_id=ENGINE_ID)


@admin_router.get("/{plan_id}", response_model=ApiResponse[dict], summary="Read one plan")
async def admin_get(
    plan_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_view(user)
    return ok(await svc.get_plan(db, plan_id), _rid(r), engine_id=ENGINE_ID)


@admin_router.patch("/{plan_id}", response_model=ApiResponse[dict], summary="Edit a plan")
async def admin_update(
    plan_id: uuid.UUID,
    body: PlanPatch,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manage(user)
    plan = await svc.update_plan(
        db, plan_id, name=body.name, description=body.description,
        base_amount=body.base_amount, gst_percent=body.gst_percent, seats=body.seats,
        is_active=body.is_active, is_default=body.is_default, sort_order=body.sort_order,
        validity_days=body.validity_days,
    )
    await db.commit()
    return ok(plan, _rid(r), engine_id=ENGINE_ID)


@admin_router.delete("/{plan_id}", response_model=ApiResponse[dict],
                     summary="Delete a plan nobody has bought")
async def admin_delete(
    plan_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manage(user)
    result = await svc.delete_plan(db, plan_id)
    await db.commit()
    return ok(result, _rid(r), engine_id=ENGINE_ID)


# ── Tenant ───────────────────────────────────────────────────────────────────
def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise ServiceOSException("NO_TENANT_CONTEXT",
                                 "This endpoint requires a tenant account.", status_code=403)
    return uuid.UUID(user.tenant_id)


@tenant_router.get("/status", response_model=ApiResponse[dict],
                   summary="Credit balance, seats, and buyable plans in one call")
async def tenant_status(
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Everything the header credit pill and its top-up popup need.

    One endpoint rather than three because the pill renders on EVERY page:
    three round trips per navigation to draw one number would be a poor trade,
    and the popup must open with the plans already in hand rather than
    showing a spinner over a number the provider just clicked.
    """
    from app.engines.vertical_catalog import seat_enforcement as se
    from app.integrations import razorpay_client

    tenant_id = _tid(user)
    credit = await se.get_credit_state(db, tenant_id)
    seats = await se.get_seat_usage(db, tenant_id)
    plans = await svc.list_plans(db, vertical_key=HOME_SERVICES, active_only=True)
    from app.engines.trust_quality.provider_health import get_provider_health_snapshot
    health = await get_provider_health_snapshot(db, tenant_id, max_age_days=30)
    health_blocked = bool(
        health.get("source") == "canonical" and health.get("bookable_allowed") is False
    )

    # One word the UI can colour on, resolved server-side so the pill and any
    # other surface can never disagree about what "low" means.
    if credit["in_arrears"]:
        state = "arrears"
    elif credit["below_floor"]:
        state = "blocked"
    elif credit["below_warning"]:
        state = "low"
    else:
        state = "healthy"

    return ok({
        **credit,
        "state": state,
        "entitled_seats": seats["entitled_seats"],
        "used_seats": seats["used_seats"],
        "available_seats": seats["available_seats"],
        "seats_over_limit": seats["over_limit"],
        "plans": plans,
        "currency": "INR",
        "provider_health": health,
        "health_blocked": health_blocked,
        "credits_preserved_during_health_block": True,
        "topup_allowed_during_health_block": True,
        "health_block_notice": (
            "New job assignment is paused by Trust & Quality. Existing credits remain available and are never confiscated; purchasing credits does not remove the health block."
            if health_blocked else None
        ),
        # Expose only a boolean. The publishable key belongs on a server-created
        # order and secrets must never leave the backend. This lets the plan
        # page explain why checkout is unavailable before a provider clicks.
        "checkout_configured": await razorpay_client.is_configured(db),
    }, _rid(r), engine_id=ENGINE_ID)



@tenant_router.get("", response_model=ApiResponse[dict],
                   summary="Top-up plans this workspace can buy")
async def tenant_list(
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Active plans only — a retired plan must never be offered for purchase."""
    plans = await svc.list_plans(db, vertical_key=HOME_SERVICES, active_only=True)
    return ok({"plans": plans, "total": len(plans)}, _rid(r), engine_id=ENGINE_ID)


@tenant_router.get("/orders", response_model=ApiResponse[dict],
                   summary="List seat-plan top-up orders")
async def tenant_orders(
    r: Request,
    status: str | None = Query(None, pattern="^(created|captured|failed)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_TRANSACTIONS_READ)),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.vertical_catalog.activation_payment_service import list_topup_plan_orders
    result = await list_topup_plan_orders(
        db, tenant_id=_tid(user), status=status, page=page, page_size=page_size,
    )
    return ok(result, _rid(r), engine_id=ENGINE_ID)


@tenant_router.get("/orders/{order_id}", response_model=ApiResponse[dict],
                   summary="Read one seat-plan top-up order")
async def tenant_order(
    order_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_TRANSACTIONS_READ)),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.vertical_catalog.activation_payment_service import get_topup_plan_order
    row = await get_topup_plan_order(db, tenant_id=_tid(user), order_id=order_id)
    return ok(row.to_dict(), _rid(r), engine_id=ENGINE_ID)


@tenant_router.get("/orders/{order_id}/invoice", summary="Download the captured top-up invoice")
async def tenant_order_invoice(
    order_id: uuid.UUID,
    user: UserContext = Depends(require_permission(P.TENANT_FINANCE_RECEIPTS_DOWNLOAD)),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.vertical_catalog.activation_payment_models import STATUS_CAPTURED
    from app.engines.vertical_catalog.activation_payment_service import get_topup_plan_order
    from app.engines.vertical_catalog.topup_invoice import (
        ensure_invoice_snapshots, invoice_payload, render_topup_invoice_pdf,
    )
    row = await get_topup_plan_order(db, tenant_id=_tid(user), order_id=order_id)
    if row.status != STATUS_CAPTURED:
        raise HTTPException(409, "An invoice is available only after the payment is captured.")
    # Migration 387 gave legacy captures a number; complete the historical
    # snapshots on first access and keep them immutable thereafter.
    await ensure_invoice_snapshots(db, row)
    await db.commit()
    pdf = render_topup_invoice_pdf(invoice_payload(row))
    filename = f"{row.invoice_number or 'topup-invoice'}.pdf"
    return StreamingResponse(
        BytesIO(pdf), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
