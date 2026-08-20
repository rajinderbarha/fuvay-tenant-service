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
    ActivationPaymentOrder, PAYMENT_KIND_DEPOSIT, PAYMENT_KIND_CREDIT, PAYMENT_KIND_FUNDING,
    STATUS_CREATED, STATUS_CAPTURED,
)
from app.engines.tenant_engine.models import TenantBilling
from app.engines.invoice_payment.models import FinancialEvent
from app.engines.platform_commerce.constants import DepositTxnType
from app.engines.platform_commerce.ledger import credit_deposit
from app.engines.platform_commerce.models import SecurityDeposit

logger = structlog.get_logger("vertical_catalog.activation_payment")
utcnow = lambda: datetime.now(timezone.utc)

FEV_ACTIVATION_DEPOSIT_CAPTURED = "activation.security_deposit_captured"
FEV_ACTIVATION_CREDIT_CAPTURED = "activation.credit_package_captured"
FEV_ACTIVATION_CREDIT_GST = "activation.credit_package_gst_collected"

ERR_ORDER_ALREADY_SATISFIED = "ACTIVATION_GATE_ALREADY_SATISFIED"


async def _post_security_deposit(
    db: AsyncSession,
    *,
    billing: TenantBilling,
    tenant_id: uuid.UUID,
    amount: Decimal,
    order_row: ActivationPaymentOrder,
    gateway_order_id: str,
    gateway_payment_id: str,
) -> None:
    """Post one deposit allocation to both compatibility projection and ledger.

    `tenant_billing` remains the activation/read-model source used throughout
    Home Services. `security_deposits` is the append-only operational ledger
    used by warranty recovery and admin finance. Keeping both in the same DB
    transaction prevents an activated provider from having an unusable deposit.
    """
    if amount <= 0:
        return

    held_before = _money(billing.security_deposit_amount)
    held_after = (held_before + amount).quantize(Decimal("0.01"))
    try:
        _v, policy = await _resolve_vertical_and_policy(db, tenant_id)
        qualifying = await resolve_qualifying_technician_count(db, tenant_id)
        required = max(
            _money(policy.minimum_deposit),
            _money(policy.deposit_amount_per_technician) * Decimal(max(1, qualifying)),
        ).quantize(Decimal("0.01")) if policy.deposit_required else Decimal("0.00")
    except Exception:
        # A captured payment must still be recorded if an administrator
        # retires a policy between order creation and webhook delivery.
        required = held_after

    billing.security_deposit_amount = held_after
    billing.security_deposit_paid = held_after >= required
    billing.updated_at = utcnow()

    deposit = (await db.execute(
        select(SecurityDeposit).where(SecurityDeposit.tenant_id == tenant_id).with_for_update()
    )).scalar_one_or_none()
    if not deposit:
        deposit = SecurityDeposit(
            tenant_id=tenant_id,
            required_amount=required,
            total_paid=held_before,
            status="paid" if held_before >= required else ("partially_paid" if held_before > 0 else "unpaid"),
        )
        db.add(deposit)
        await db.flush()
    else:
        deposit.required_amount = required

    await credit_deposit(
        db,
        deposit,
        amount,
        DepositTxnType.INITIAL_PAYMENT,
        gateway_payment_id,
        "Home Services activation security deposit",
        None,
    )
    deposit.status = "paid" if deposit.current_balance >= required else "partially_paid"
    deposit.paid_at = utcnow() if deposit.status == "paid" else deposit.paid_at
    deposit.razorpay_order_id = gateway_order_id
    deposit.razorpay_payment_id = gateway_payment_id
    deposit.payment_reference = gateway_payment_id

    db.add(FinancialEvent(
        record_type="activation_payment", record_id=order_row.id, tenant_id=tenant_id,
        actor_type="system", event_type=FEV_ACTIVATION_DEPOSIT_CAPTURED,
        new_value={
            "amount": float(amount),
            "deposit_held_after": float(held_after),
            "deposit_required": float(required),
            "gateway_order_id": gateway_order_id,
            "gateway_payment_id": gateway_payment_id,
        },
    ))


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


def _money(value: Decimal | float | int | str | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


async def resolve_activation_funding_quote(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Return the one authoritative activation-funding quote.

    The checkout may collect two allocations together, but the deposit and
    spendable credits remain separate balances.  No amount is accepted from
    the browser; every order re-runs this function against the current policy,
    technician count and held balances.
    """
    _vertical, policy = await _resolve_vertical_and_policy(db, tenant_id)
    billing = await _get_billing_row(db, tenant_id)
    qualifying = await resolve_qualifying_technician_count(db, tenant_id)

    deposit_per_technician = _money(policy.deposit_amount_per_technician)
    minimum_deposit = _money(policy.minimum_deposit)
    deposit_required = (
        max(minimum_deposit, deposit_per_technician * Decimal(max(1, qualifying)))
        if policy.deposit_required else Decimal("0.00")
    ).quantize(Decimal("0.01"))
    deposit_held = _money(billing.security_deposit_amount if billing else 0)
    deposit_shortfall = max(Decimal("0.00"), deposit_required - deposit_held).quantize(Decimal("0.01"))

    credit_balance = _money(billing.credit_balance if billing else 0)
    starter_credit = _money(policy.credit_package_base_amount)
    gst_percent = _money(policy.credit_package_gst_percent)
    credit_needed = credit_balance < starter_credit
    credit_base = starter_credit if credit_needed else Decimal("0.00")
    credit_tax = (credit_base * gst_percent / Decimal("100")).quantize(Decimal("0.01"))
    credit_gross = credit_base + credit_tax
    total_due = (deposit_shortfall + credit_gross).quantize(Decimal("0.01"))

    if deposit_shortfall > 0 and credit_gross > 0:
        checkout_mode = "deposit_and_credits"
        checkout_label = "Fund deposit & starter credits"
    elif deposit_shortfall > 0:
        checkout_mode = "deposit_top_up"
        checkout_label = "Complete security deposit"
    elif credit_gross > 0:
        checkout_mode = "credits_only"
        checkout_label = "Buy starter credits"
    else:
        checkout_mode = "funded"
        checkout_label = "Activation funding complete"

    return {
        "currency": "INR",
        "policy_version": policy.version_number,
        "qualifying_technician_count": qualifying,
        "deposit_per_technician": float(deposit_per_technician),
        "minimum_deposit": float(minimum_deposit),
        "deposit_required": float(deposit_required),
        "deposit_held": float(deposit_held),
        "deposit_shortfall": float(deposit_shortfall),
        "starter_credit_balance": float(credit_balance),
        "starter_credit_base": float(starter_credit),
        "credit_purchase_base": float(credit_base),
        "credit_gst_percent": float(gst_percent),
        "credit_tax": float(credit_tax),
        "credit_gross": float(credit_gross),
        "total_due": float(total_due),
        "checkout_mode": checkout_mode,
        "checkout_label": checkout_label,
        "can_pay": total_due > 0,
        "deposit_funded": deposit_shortfall <= 0,
        "credits_funded": not credit_needed,
        "separate_ledger_allocations": True,
    }


async def create_activation_funding_order(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Create one checkout for the exact live shortfall and allocate it on capture."""
    vertical, policy = await _resolve_vertical_and_policy(db, tenant_id)
    quote = await resolve_activation_funding_quote(db, tenant_id)
    gross_amount = _money(quote["total_due"])
    if gross_amount <= 0:
        raise ServiceOSException(
            ERR_ORDER_ALREADY_SATISFIED,
            "Security deposit and starter credits are already funded.",
            status_code=409,
        )

    # Serialize order creation per tenant. Without this, two simultaneous
    # clicks can both observe "no pending order" and create two valid gateway
    # orders before either inserts its row.
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
        {"lock_key": f"activation-funding:{tenant_id}"},
    )

    # Reuse an identical still-open order. This prevents double clicking from
    # producing multiple payable gateway orders while allowing a fresh order
    # when technician count or a held balance changes the quote.
    pending = (await db.execute(
        select(ActivationPaymentOrder).where(
            ActivationPaymentOrder.tenant_id == tenant_id,
            ActivationPaymentOrder.payment_kind == PAYMENT_KIND_FUNDING,
            ActivationPaymentOrder.status == STATUS_CREATED,
            ActivationPaymentOrder.amount == gross_amount,
            ActivationPaymentOrder.credited_amount == _money(quote["credit_purchase_base"]),
            ActivationPaymentOrder.tax_amount == _money(quote["credit_tax"]),
        ).order_by(ActivationPaymentOrder.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    if pending:
        reconciliation = await reconcile_activation_order(
            db, tenant_id=tenant_id, gateway_order_id=pending.gateway_order_id,
        )
        if reconciliation.get("status") == STATUS_CAPTURED:
            return {
                "already_confirmed": True,
                "order_id": pending.gateway_order_id,
                "payment_kind": PAYMENT_KIND_FUNDING,
                "activation_payment_order_id": str(pending.id),
                "reconciliation": reconciliation,
            }
        raw = pending.raw_order_payload or {}
        order_id = pending.gateway_order_id
        reused = True
    else:
        receipt = f"actfund_{str(tenant_id)[:8]}_{uuid.uuid4().hex[:8]}"
        raw = await razorpay_client.create_order(
            gross_amount,
            receipt=receipt,
            notes={
                "tenant_id": str(tenant_id),
                "payment_kind": PAYMENT_KIND_FUNDING,
                "vertical_key": HOME_SERVICES_VERTICAL_KEY,
                "deposit_amount": str(_money(quote["deposit_shortfall"])),
                "credit_amount": str(_money(quote["credit_purchase_base"])),
                "tax_amount": str(_money(quote["credit_tax"])),
            },
        )
        pending = ActivationPaymentOrder(
            tenant_id=tenant_id,
            vertical_id=vertical.id,
            payment_kind=PAYMENT_KIND_FUNDING,
            gateway="razorpay",
            gateway_order_id=raw["id"],
            amount=gross_amount,
            credited_amount=_money(quote["credit_purchase_base"]),
            tax_amount=_money(quote["credit_tax"]),
            currency="INR",
            status=STATUS_CREATED,
            policy_version=policy.version_number,
            raw_order_payload=raw,
        )
        db.add(pending)
        await db.commit()
        order_id = raw["id"]
        reused = False

    from app.config import get_settings
    return {
        "order_id": order_id,
        "amount": float(gross_amount),
        "amount_paise": int(gross_amount * 100),
        "currency": "INR",
        "key": get_settings().RAZORPAY_KEY_ID,
        "payment_kind": PAYMENT_KIND_FUNDING,
        "activation_payment_order_id": str(pending.id),
        "deposit_amount": quote["deposit_shortfall"],
        "credited_amount": quote["credit_purchase_base"],
        "tax_amount": quote["credit_tax"],
        "quote": quote,
        "reused": reused,
    }


async def create_security_deposit_order(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    v, policy = await _resolve_vertical_and_policy(db, tenant_id)

    billing = await _get_billing_row(db, tenant_id)
    qualifying = await resolve_qualifying_technician_count(db, tenant_id)
    required_amount = Decimal(str(max(
        float(policy.minimum_deposit),
        float(policy.deposit_amount_per_technician) * max(1, qualifying),
    ))).quantize(Decimal("0.01"))
    held_amount = _money(billing.security_deposit_amount if billing else 0)
    shortfall = max(Decimal("0.00"), required_amount - held_amount).quantize(Decimal("0.01"))
    if shortfall <= 0:
        raise ServiceOSException(ERR_ORDER_ALREADY_SATISFIED,
            "Security deposit is already fully funded for the current technician count.", status_code=409)

    receipt = f"actdep_{str(tenant_id)[:8]}_{uuid.uuid4().hex[:8]}"
    order = await razorpay_client.create_order(
        shortfall, receipt=receipt,
        notes={"tenant_id": str(tenant_id), "payment_kind": PAYMENT_KIND_DEPOSIT,
               "vertical_key": HOME_SERVICES_VERTICAL_KEY})

    rec = ActivationPaymentOrder(
        tenant_id=tenant_id, vertical_id=v.id, payment_kind=PAYMENT_KIND_DEPOSIT,
        gateway="razorpay", gateway_order_id=order["id"], amount=shortfall,
        currency="INR", status=STATUS_CREATED, policy_version=policy.version_number,
        raw_order_payload=order,
    )
    db.add(rec)
    await db.commit()

    from app.config import get_settings
    return {"order_id": order["id"], "amount": float(shortfall),
            "amount_paise": int(shortfall * 100), "currency": "INR",
            "key": get_settings().RAZORPAY_KEY_ID,
            "payment_kind": PAYMENT_KIND_DEPOSIT, "activation_payment_order_id": str(rec.id),
            "required_amount": float(required_amount), "held_amount": float(held_amount)}


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


async def confirm_activation_checkout(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    gateway_order_id: str,
    gateway_payment_id: str,
    signature: str,
) -> dict:
    """Confirm Razorpay Checkout using its signed order/payment tuple.

    This is the primary browser checkout completion path.  It is equivalent
    to the webhook posting path, but tenant-authenticated and immediately
    updates the activation UI.  The browser supplies identifiers/signature,
    never an amount or allocation.
    """
    if not razorpay_client.verify_payment_signature(gateway_order_id, gateway_payment_id, signature):
        raise ServiceOSException(
            "ACTIVATION_PAYMENT_SIGNATURE_INVALID",
            "Payment confirmation signature is invalid.",
            status_code=422,
        )
    order_row = (await db.execute(
        select(ActivationPaymentOrder).where(
            ActivationPaymentOrder.gateway_order_id == gateway_order_id,
            ActivationPaymentOrder.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not order_row:
        raise NotFoundException("ActivationPaymentOrder", gateway_order_id)

    return await confirm_activation_payment_webhook(
        db,
        gateway_order_id=gateway_order_id,
        gateway_payment_id=gateway_payment_id,
        amount=_money(order_row.amount),
        status_="captured",
        raw_payload={
            "source": "razorpay_checkout_signature",
            "gateway_order_id": gateway_order_id,
            "gateway_payment_id": gateway_payment_id,
        },
    )


async def reconcile_activation_order(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    gateway_order_id: str,
) -> dict:
    """Reconcile a Checkout order from Razorpay's authenticated payments API."""
    order_row = (await db.execute(
        select(ActivationPaymentOrder).where(
            ActivationPaymentOrder.gateway_order_id == gateway_order_id,
            ActivationPaymentOrder.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not order_row:
        raise NotFoundException("ActivationPaymentOrder", gateway_order_id)
    if order_row.status == STATUS_CAPTURED:
        return {**order_row.to_dict(), "idempotent": True, "reconciled": True}

    payments = await razorpay_client.get_order_payments(gateway_order_id)
    expected_paise = int(_money(order_row.amount) * 100)
    captured = next((
        payment for payment in payments
        if payment.get("order_id") == gateway_order_id
        and payment.get("status") == "captured"
        and bool(payment.get("captured"))
        and int(payment.get("amount") or 0) == expected_paise
        and payment.get("currency", "INR") == order_row.currency
    ), None)
    if not captured:
        failures = [
            {
                "payment_id": payment.get("id"),
                "status": payment.get("status"),
                "error_code": payment.get("error_code"),
                "error_description": payment.get("error_description"),
            }
            for payment in payments if payment.get("status") == "failed"
        ]
        return {
            **order_row.to_dict(),
            "reconciled": True,
            "captured": False,
            "failed_attempts": failures[-3:],
        }

    result = await confirm_activation_payment_webhook(
        db,
        gateway_order_id=gateway_order_id,
        gateway_payment_id=str(captured["id"]),
        amount=_money(order_row.amount),
        status_="captured",
        raw_payload={"source": "razorpay_server_reconciliation", "payment": captured},
    )
    return {**result, "reconciled": True, "captured": True}


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
            ActivationPaymentOrder.gateway_order_id == gateway_order_id
        ).with_for_update()
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

    expected_amount = _money(order_row.amount)
    received_amount = _money(amount)
    if received_amount != expected_amount:
        raise ServiceOSException(
            "ACTIVATION_PAYMENT_AMOUNT_MISMATCH",
            "Captured amount does not match the server-created activation order.",
            status_code=422,
            context={"expected_amount": float(expected_amount), "received_amount": float(received_amount)},
        )

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

    credited = Decimal("0.00")
    tax = Decimal("0.00")
    deposit_allocation = Decimal("0.00")
    if order_row.payment_kind == PAYMENT_KIND_DEPOSIT:
        deposit_allocation = received_amount
    elif order_row.payment_kind == PAYMENT_KIND_CREDIT:
        credited = _money(order_row.credited_amount if order_row.credited_amount is not None else received_amount)
        tax = _money(order_row.tax_amount)
    elif order_row.payment_kind == PAYMENT_KIND_FUNDING:
        credited = _money(order_row.credited_amount)
        tax = _money(order_row.tax_amount)
        deposit_allocation = (received_amount - credited - tax).quantize(Decimal("0.01"))
        if deposit_allocation < 0:
            raise ServiceOSException(
                "ACTIVATION_PAYMENT_ALLOCATION_INVALID",
                "Activation funding allocations exceed the captured amount.",
                status_code=422,
            )
    else:
        raise ServiceOSException(
            "ACTIVATION_PAYMENT_KIND_INVALID",
            "Activation payment order has an unsupported payment kind.",
            status_code=422,
        )

    if deposit_allocation > 0:
        await _post_security_deposit(
            db,
            billing=billing,
            tenant_id=tenant_id,
            amount=deposit_allocation,
            order_row=order_row,
            gateway_order_id=gateway_order_id,
            gateway_payment_id=gateway_payment_id,
        )

    if credited > 0:
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
            new_value={"tax_amount": float(tax), "gross_amount": float(credited + tax),
                       "gateway_order_id": gateway_order_id},
        ))

    await db.commit()

    from app.engines.vertical_catalog.activation import try_auto_activate
    activation_result = await try_auto_activate(db, tenant_id, vertical_key=HOME_SERVICES_VERTICAL_KEY)

    return {**order_row.to_dict(), "idempotent": False, "activation": activation_result}
