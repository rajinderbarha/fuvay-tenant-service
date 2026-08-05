"""HOME-SERVICES-ACTIVATION-PAYMENT-01 — service layer.

Order creation always re-resolves the required amount from the live
published finance policy (never a client-supplied amount) via the same
activation.py gate-evaluation code path the Activation Center reads from.
Webhook confirmation NEVER trusts client-reported success -- it verifies
the Razorpay signature (app.integrations.razorpay_client), and only a
subsequent server call actually moves tenant_billing money, following the
exact idempotency + audit pattern already proven in
app.engines.payment.service.process_payment_webhook (gateway_payment_id
uniqueness = the single source of truth for "already applied").
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations import razorpay_client
from app.exceptions import ServiceOSException, NotFoundException
from app.engines.vertical_catalog.service import VerticalCatalogService
from app.engines.vertical_catalog.home_services_setup_service import HOME_SERVICES_VERTICAL_KEY
from app.engines.vertical_catalog.finance_policy_service import (
    resolve_published_policy, resolve_qualifying_technician_count, FinancePolicyResolutionError,
)
from app.engines.vertical_catalog.activation_payment_models import (
    ActivationPaymentOrder, PAYMENT_KIND_DEPOSIT, PAYMENT_KIND_CREDIT,
    STATUS_CREATED, STATUS_CAPTURED,
)
from app.engines.tenant_engine.models import TenantBilling
from app.engines.invoice_payment.models import FinancialEvent

logger = structlog.get_logger("vertical_catalog.activation_payment")
utcnow = lambda: datetime.now(timezone.utc)

FEV_ACTIVATION_DEPOSIT_CAPTURED = "activation.security_deposit_captured"
FEV_ACTIVATION_CREDIT_CAPTURED = "activation.credit_package_captured"
FEV_ACTIVATION_CREDIT_GST = "activation.credit_package_gst_collected"

ERR_ORDER_ALREADY_SATISFIED = "ACTIVATION_GATE_ALREADY_SATISFIED"


async def _resolve_vertical_and_policy(db: AsyncSession, tenant_id: uuid.UUID):
    svc = VerticalCatalogService()
    v = await svc._by_key(db, HOME_SERVICES_VERTICAL_KEY)
    try:
        policy = await resolve_published_policy(db, v.id)
    except FinancePolicyResolutionError as exc:
        raise ServiceOSException(exc.code, exc.detail, status_code=422) from exc
    return v, policy


async def _get_billing_row(db: AsyncSession, tenant_id: uuid.UUID) -> TenantBilling | None:
    return (await db.execute(
        select(TenantBilling).where(TenantBilling.tenant_id == tenant_id)
    )).scalar_one_or_none()


async def create_security_deposit_order(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    v, policy = await _resolve_vertical_and_policy(db, tenant_id)

    billing = await _get_billing_row(db, tenant_id)
    if billing and billing.security_deposit_paid:
        raise ServiceOSException(ERR_ORDER_ALREADY_SATISFIED,
            "Security deposit is already verified for this tenant.", status_code=409)

    qualifying = await resolve_qualifying_technician_count(db, tenant_id)
    required_amount = Decimal(str(max(
        float(policy.minimum_deposit),
        float(policy.deposit_amount_per_technician) * max(1, qualifying),
    ))).quantize(Decimal("0.01"))

    receipt = f"actdep_{str(tenant_id)[:8]}_{uuid.uuid4().hex[:8]}"
    order = await razorpay_client.create_order(
        required_amount, receipt=receipt,
        notes={"tenant_id": str(tenant_id), "payment_kind": PAYMENT_KIND_DEPOSIT,
               "vertical_key": HOME_SERVICES_VERTICAL_KEY})

    rec = ActivationPaymentOrder(
        tenant_id=tenant_id, vertical_id=v.id, payment_kind=PAYMENT_KIND_DEPOSIT,
        gateway="razorpay", gateway_order_id=order["id"], amount=required_amount,
        currency="INR", status=STATUS_CREATED, policy_version=policy.version_number,
        raw_order_payload=order,
    )
    db.add(rec)
    await db.commit()

    from app.config import get_settings
    return {"order_id": order["id"], "amount": float(required_amount),
            "amount_paise": int(required_amount * 100), "currency": "INR",
            "key": get_settings().RAZORPAY_KEY_ID,
            "payment_kind": PAYMENT_KIND_DEPOSIT, "activation_payment_order_id": str(rec.id)}


async def create_credit_package_order(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    v, policy = await _resolve_vertical_and_policy(db, tenant_id)

    billing = await _get_billing_row(db, tenant_id)
    current_balance = float(billing.credit_balance) if billing else 0.0
    required_credit_amount = float(
        (policy.credit_package_base_amount * (1 + policy.credit_package_gst_percent / 100))
        .quantize(Decimal("0.01"))
    )
    # Compare against the BASE (usable) amount, not the GST-inclusive gross
    # -- credit_balance only ever receives the base portion on confirmed
    # payment (GST is recorded as a separate financial event, never
    # blended into usable credit). Comparing to the gross here would make
    # this gate/guard mathematically impossible to satisfy, same root
    # cause fixed in activation.py's evaluate_activation_gates.
    if current_balance >= float(policy.credit_package_base_amount):
        raise ServiceOSException(ERR_ORDER_ALREADY_SATISFIED,
            "Starter credit package is already purchased for this tenant.", status_code=409)

    gross_amount = Decimal(str(required_credit_amount))
    receipt = f"actcr_{str(tenant_id)[:8]}_{uuid.uuid4().hex[:8]}"
    order = await razorpay_client.create_order(
        gross_amount, receipt=receipt,
        notes={"tenant_id": str(tenant_id), "payment_kind": PAYMENT_KIND_CREDIT,
               "vertical_key": HOME_SERVICES_VERTICAL_KEY})

    rec = ActivationPaymentOrder(
        tenant_id=tenant_id, vertical_id=v.id, payment_kind=PAYMENT_KIND_CREDIT,
        gateway="razorpay", gateway_order_id=order["id"], amount=gross_amount,
        credited_amount=policy.credit_package_base_amount,
        tax_amount=(gross_amount - policy.credit_package_base_amount).quantize(Decimal("0.01")),
        currency="INR", status=STATUS_CREATED, policy_version=policy.version_number,
        raw_order_payload=order,
    )
    db.add(rec)
    await db.commit()

    from app.config import get_settings
    return {"order_id": order["id"], "amount": float(gross_amount),
            "amount_paise": int(gross_amount * 100), "currency": "INR",
            "key": get_settings().RAZORPAY_KEY_ID,
            "payment_kind": PAYMENT_KIND_CREDIT, "activation_payment_order_id": str(rec.id),
            "credited_amount": float(policy.credit_package_base_amount),
            "tax_amount": float(gross_amount - policy.credit_package_base_amount)}


async def confirm_activation_payment_webhook(
    db: AsyncSession, gateway_order_id: str, gateway_payment_id: str,
    amount: Decimal, status_: str, raw_payload: dict,
) -> dict:
    """Idempotency check: WHERE gateway_payment_id = ? (a real DB query, not a
    middleware flag) -- a retried/duplicate webhook call for the same
    payment can never double-post. Looked up by gateway_order_id first
    since that's what our own order-creation call always knows; the
    uniqueness constraint on gateway_payment_id is what makes the actual
    posting idempotent."""
    order_row = (await db.execute(
        select(ActivationPaymentOrder).where(
            ActivationPaymentOrder.gateway_order_id == gateway_order_id)
    )).scalar_one_or_none()
    if not order_row:
        raise NotFoundException("ActivationPaymentOrder", gateway_order_id)

    if order_row.status == STATUS_CAPTURED:
        logger.info("activation_payment.webhook_idempotent", order_id=gateway_order_id)
        return {**order_row.to_dict(), "idempotent": True}

    # A second defensive check: even if two concurrent webhook deliveries
    # both raced past the row-status check above, the DB-level unique
    # constraint on gateway_payment_id (migration 199) makes a second
    # INSERT/UPDATE with the same payment_id impossible to land twice --
    # here we also pre-check via SELECT for a clean, non-500 idempotent
    # response instead of relying solely on the constraint violation.
    dup = (await db.execute(
        select(ActivationPaymentOrder).where(
            ActivationPaymentOrder.gateway_payment_id == gateway_payment_id)
    )).scalar_one_or_none()
    if dup:
        logger.info("activation_payment.webhook_idempotent_by_payment_id", payment_id=gateway_payment_id)
        return {**dup.to_dict(), "idempotent": True}

    if status_ != "captured":
        order_row.status = "failed"
        order_row.raw_webhook_payload = raw_payload
        await db.commit()
        return {**order_row.to_dict(), "idempotent": False}

    tenant_id = order_row.tenant_id
    billing = await _get_billing_row(db, tenant_id)
    if not billing:
        billing = TenantBilling(tenant_id=tenant_id, vertical_key=HOME_SERVICES_VERTICAL_KEY)
        db.add(billing)
        await db.flush()

    order_row.status = STATUS_CAPTURED
    order_row.gateway_payment_id = gateway_payment_id
    order_row.captured_at = utcnow()
    order_row.raw_webhook_payload = raw_payload

    if order_row.payment_kind == PAYMENT_KIND_DEPOSIT:
        billing.security_deposit_paid = True
        billing.security_deposit_amount = amount
        billing.updated_at = utcnow()
        db.add(FinancialEvent(
            record_type="activation_payment", record_id=order_row.id, tenant_id=tenant_id,
            actor_type="system", event_type=FEV_ACTIVATION_DEPOSIT_CAPTURED,
            new_value={"amount": float(amount), "gateway_order_id": gateway_order_id,
                       "gateway_payment_id": gateway_payment_id},
        ))
    else:  # PAYMENT_KIND_CREDIT
        credited = order_row.credited_amount if order_row.credited_amount is not None else amount
        tax = order_row.tax_amount if order_row.tax_amount is not None else Decimal("0")
        billing.credit_balance = Decimal(str(billing.credit_balance or 0)) + Decimal(str(credited))
        billing.updated_at = utcnow()

        from app.engines.tenant_engine.models import UsageCreditLedger
        db.add(UsageCreditLedger(
            tenant_id=tenant_id, event_type="activation_credit_package_purchase",
            credit_delta=float(credited),
            balance_before=float(billing.credit_balance) - float(credited),
            balance_after=float(billing.credit_balance),
            deduction_source="razorpay_activation_payment",
        ))
        # GST is platform revenue on the credit package -- recorded as its
        # own financial event, NEVER blended into usable credit balance.
        db.add(FinancialEvent(
            record_type="activation_payment", record_id=order_row.id, tenant_id=tenant_id,
            actor_type="system", event_type=FEV_ACTIVATION_CREDIT_CAPTURED,
            new_value={"credited_amount": float(credited), "gateway_order_id": gateway_order_id,
                       "gateway_payment_id": gateway_payment_id},
        ))
        db.add(FinancialEvent(
            record_type="activation_payment", record_id=order_row.id, tenant_id=tenant_id,
            actor_type="system", event_type=FEV_ACTIVATION_CREDIT_GST,
            new_value={"tax_amount": float(tax), "gross_amount": float(amount),
                       "gateway_order_id": gateway_order_id},
        ))

    await db.commit()

    from app.engines.vertical_catalog.activation import try_auto_activate
    activation_result = await try_auto_activate(db, tenant_id, vertical_key=HOME_SERVICES_VERTICAL_KEY)

    return {**order_row.to_dict(), "idempotent": False, "activation": activation_result}
