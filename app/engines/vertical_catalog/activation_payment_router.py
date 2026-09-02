"""Tenant-facing activation order creation and Razorpay webhook confirmation.

The top-up plan grants credit plus technician seats without needing an admin
to manually confirm anything.

tenant_id is always resolved server-side from the caller's JWT
(UserContext.tenant_id), never accepted from the client, matching the
pattern already used across vertical_catalog's tenant-facing routers.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.core.permissions import require_tenant_owner_mutation
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.integrations import razorpay_client
from app.engines.vertical_catalog.activation_payment_service import (
    create_credit_package_order,
    create_activation_funding_order, resolve_activation_funding_quote,
    confirm_activation_checkout, reconcile_activation_order,
    confirm_activation_payment_webhook,
)

router = APIRouter(prefix="/v1/tenant/home-services/activation", tags=["Tenant Activation Payments"])


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")


@router.get("/funding/quote")
async def get_funding_quote_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    return ok(await resolve_activation_funding_quote(db, _tid(user)), _rid(request))


@router.post("/funding/order")
async def create_funding_order_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    return ok(await create_activation_funding_order(db, _tid(user)), _rid(request))


class ConfirmFundingRequest(BaseModel):
    razorpay_order_id: str = Field(min_length=3, max_length=100)
    razorpay_payment_id: str = Field(min_length=3, max_length=100)
    razorpay_signature: str = Field(min_length=3, max_length=255)


@router.post("/funding/confirm")
async def confirm_funding_endpoint(
    body: ConfirmFundingRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    data = await confirm_activation_checkout(
        db,
        tenant_id=_tid(user),
        gateway_order_id=body.razorpay_order_id,
        gateway_payment_id=body.razorpay_payment_id,
        signature=body.razorpay_signature,
    )
    return ok(data, _rid(request))


@router.post("/funding/{gateway_order_id}/reconcile")
async def reconcile_funding_endpoint(
    gateway_order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    data = await reconcile_activation_order(
        db, tenant_id=_tid(user), gateway_order_id=gateway_order_id,
    )
    return ok(data, _rid(request))


# POST /security-deposit/order was removed in migration 317: there is no
# deposit to pay. The single activation checkout is the top-up plan, created
# by POST /activation-funding/order.


@router.post("/credit-package/order")
async def create_credit_order_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    data = await create_credit_package_order(db, tid)
    return ok(data, _rid(request))


@router.post("/webhook", summary="Razorpay webhook -- proven idempotent on gateway_payment_id")
async def activation_payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Never trusts client-reported payment success. Verifies the Razorpay
    webhook HMAC signature over the raw request body before applying any
    effect (app.integrations.razorpay_client.verify_webhook_signature --
    same function payment/router.py's proven webhook already uses)."""
    raw_body = await request.body()
    sig = request.headers.get("x-razorpay-signature", "")
    from app.config import get_settings
    if not get_settings().RAZORPAY_WEBHOOK_SECRET:
        raise ServiceOSException(
            "ACTIVATION_WEBHOOK_NOT_CONFIGURED",
            "Activation webhook is disabled until a Razorpay webhook secret is configured.",
            status_code=503,
        )
    if not razorpay_client.verify_webhook_signature(raw_body, sig):
        raise ServiceOSException("WEBHOOK_VERIFICATION_FAILED", "Invalid Razorpay webhook signature.")

    body = await request.json()
    data = await confirm_activation_payment_webhook(
        db,
        gateway_order_id=body["gateway_order_id"],
        gateway_payment_id=body["gateway_payment_id"],
        amount=Decimal(str(body["amount"])),
        status_=body.get("status", "captured"),
        raw_payload=body,
    )
    return ok(data, _rid(request))
