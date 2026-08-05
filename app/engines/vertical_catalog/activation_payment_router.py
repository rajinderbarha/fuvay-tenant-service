"""HOME-SERVICES-ACTIVATION-PAYMENT-01 — tenant-facing order creation +
gateway webhook confirmation for the online Razorpay activation-gate
payment path (security deposit + starter credit package). Sits alongside
the existing ADMIN-ONLY offline `/verify-deposit` endpoint
(vertical_catalog/admin_router.py) -- this is the path a tenant uses
without needing an Admin to manually confirm anything.

tenant_id is always resolved server-side from the caller's JWT
(UserContext.tenant_id), never accepted from the client, matching the
pattern already used across vertical_catalog's tenant-facing routers.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.core.permissions import require_tenant_owner_mutation
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.integrations import razorpay_client
from app.engines.vertical_catalog.activation_payment_service import (
    create_security_deposit_order, create_credit_package_order,
    confirm_activation_payment_webhook,
)

router = APIRouter(prefix="/v1/tenant/home-services/activation", tags=["Tenant Activation Payments"])


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")


@router.post("/security-deposit/order")
async def create_deposit_order_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
):
    tid = _tid(user)
    data = await create_security_deposit_order(db, tid)
    return ok(data, _rid(request))


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
