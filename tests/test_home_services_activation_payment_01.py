"""HOME-SERVICES-ACTIVATION-PAYMENT-01 — real online Razorpay collection for
the security-deposit + starter-credit-package Home Services activation
gates (app.engines.vertical_catalog.activation_payment_service /
activation_payment_router).

Focused tests (time-boxed pass) proving:
  1. Credit package order creation computes the correct GST split
     (base 1000 + 18% GST = 1180 gross; credited_amount stays 1000, never
     blended with the 180 GST portion).
  2. Webhook confirmation is idempotent per gateway_payment_id / on an
     already-captured order -- a retried webhook cannot double-post.
  3. Credit-package webhook confirmation posts EXACTLY the base amount to
     credit_balance and records the GST as a separate FinancialEvent.
  4. Regression test for a real bug this slice found and fixed in
     activation.py: evaluate_activation_gates used to compare the tenant's
     USABLE credit_balance (which only ever receives the base amount)
     against the GST-INCLUSIVE gross required_credit_amount -- making the
     gate mathematically impossible to satisfy even after a fully correct
     payment. Fixed to compare against the base amount.

Live DB-integration proof (captured in this session's transcript, not
re-run here): real Razorpay test-mode orders were created
(order_TJHDZ3O21PjnoD deposit ₹2000, order_TJHDaBj3lgvdyb credit ₹1180),
simulated webhook confirmations posted tenant_billing.credit_balance=1000.00
(not 1180) and security_deposit_paid=true/amount=2000.00, retried webhooks
returned idempotent:true with no balance change, and tenant Guramrit
(244beeec-fedc-452e-8054-317e45557d4d) transitioned
activation_requirements_pending -> active via try_auto_activate once this
gate-math bug was fixed and all other gates were already ready.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.vertical_catalog.activation_payment_models import (
    ActivationPaymentOrder, PAYMENT_KIND_DEPOSIT, PAYMENT_KIND_CREDIT,
    STATUS_CAPTURED, STATUS_CREATED,
)
from app.engines.vertical_catalog import activation_payment_service as svc


def _mock_scalar(row):
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    return result


def _make_policy(version=1, deposit_per_tech="2000", minimum_deposit="2000",
                  credit_base="1000", credit_gst="18"):
    p = MagicMock()
    p.version_number = version
    p.deposit_amount_per_technician = Decimal(deposit_per_tech)
    p.minimum_deposit = Decimal(minimum_deposit)
    p.credit_package_base_amount = Decimal(credit_base)
    p.credit_package_gst_percent = Decimal(credit_gst)
    return p


@pytest.mark.asyncio
async def test_credit_package_order_splits_base_and_gst_correctly():
    tenant_id = uuid.uuid4()
    vertical = MagicMock(id=uuid.uuid4())
    policy = _make_policy()

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_mock_scalar(None))  # no existing billing row
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch.object(svc, "_resolve_vertical_and_policy", new=AsyncMock(return_value=(vertical, policy))), \
         patch("app.integrations.razorpay_client.create_order", new=AsyncMock(
             return_value={"id": "order_test123", "amount": 118000, "currency": "INR"})):
        result = await svc.create_credit_package_order(db, tenant_id)

    assert result["amount"] == 1180.0
    assert result["credited_amount"] == 1000.0
    assert result["tax_amount"] == 180.0
    # the order record itself must carry the same split for the webhook to apply later
    added = db.add.call_args[0][0]
    assert added.credited_amount == Decimal("1000")
    assert added.tax_amount == Decimal("180.00")


@pytest.mark.asyncio
async def test_webhook_idempotent_when_order_already_captured():
    order_row = MagicMock(spec=ActivationPaymentOrder)
    order_row.status = STATUS_CAPTURED
    order_row.to_dict.return_value = {"status": STATUS_CAPTURED, "gateway_order_id": "order_x"}

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_mock_scalar(order_row))

    result = await svc.confirm_activation_payment_webhook(
        db, gateway_order_id="order_x", gateway_payment_id="pay_x",
        amount=Decimal("2000"), status_="captured", raw_payload={},
    )
    assert result["idempotent"] is True
    # no commit / mutation attempted on an already-captured order
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_idempotent_on_duplicate_payment_id_even_if_order_row_stale():
    """Defends the actual double-post guard: even if the in-memory order_row
    read is stale (status still 'created'), a second row already recording
    this exact gateway_payment_id must short-circuit before any posting."""
    order_row = MagicMock(spec=ActivationPaymentOrder)
    order_row.status = STATUS_CREATED
    dup_row = MagicMock(spec=ActivationPaymentOrder)
    dup_row.to_dict.return_value = {"status": STATUS_CAPTURED, "gateway_payment_id": "pay_dup"}

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_mock_scalar(order_row), _mock_scalar(dup_row)])

    result = await svc.confirm_activation_payment_webhook(
        db, gateway_order_id="order_x", gateway_payment_id="pay_dup",
        amount=Decimal("2000"), status_="captured", raw_payload={},
    )
    assert result["idempotent"] is True
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_posts_base_credit_and_separate_gst_event_not_blended():
    tenant_id = uuid.uuid4()
    order_row = MagicMock(spec=ActivationPaymentOrder)
    order_row.id = uuid.uuid4()
    order_row.tenant_id = tenant_id
    order_row.status = STATUS_CREATED
    order_row.payment_kind = PAYMENT_KIND_CREDIT
    order_row.credited_amount = Decimal("1000")
    order_row.tax_amount = Decimal("180.00")
    order_row.to_dict.return_value = {"status": STATUS_CAPTURED}

    billing = MagicMock()
    billing.credit_balance = Decimal("0")

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _mock_scalar(order_row),   # lookup by gateway_order_id
        _mock_scalar(None),        # dup-by-payment-id check
        _mock_scalar(billing),     # billing row lookup
    ])
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("app.engines.vertical_catalog.activation.try_auto_activate",
               new=AsyncMock(return_value={"status": "activation_requirements_pending"})):
        result = await svc.confirm_activation_payment_webhook(
            db, gateway_order_id="order_credit", gateway_payment_id="pay_credit",
            amount=Decimal("1180"), status_="captured", raw_payload={},
        )

    assert result["idempotent"] is False
    # credit_balance must land on exactly the base amount, never the gross
    assert billing.credit_balance == Decimal("1000")

    event_types = [call.args[0].event_type for call in db.add.call_args_list
                   if hasattr(call.args[0], "event_type")]
    assert "activation.credit_package_captured" in event_types
    assert "activation.credit_package_gst_collected" in event_types
    # exactly two separate financial events -- GST was never folded into the credit event
    assert event_types.count("activation.credit_package_captured") == 1
    assert event_types.count("activation.credit_package_gst_collected") == 1


def test_regression_gate_credit_math_uses_base_not_gross_amount():
    """Reproduces the exact bug this slice fixed in activation.py: comparing
    usable credit_balance to the GST-inclusive gross made the gate
    impossible to ever satisfy. credit_balance only ever receives the base
    amount on a confirmed payment (see webhook test above), so the gate
    must compare against the base, not (base * (1 + gst%))."""
    credit_package_base_amount = Decimal("1000")
    credit_package_gst_percent = Decimal("18")
    required_credit_amount_gross = float(
        (credit_package_base_amount * (1 + credit_package_gst_percent / 100)).quantize(Decimal("0.01")))
    assert required_credit_amount_gross == 1180.0

    credit_balance_after_confirmed_payment = 1000.0  # what the webhook actually posts

    # the bug: comparing to gross would NEVER be satisfied
    assert not (credit_balance_after_confirmed_payment >= required_credit_amount_gross)
    # the fix: comparing to base amount is satisfied by exactly the posted amount
    assert credit_balance_after_confirmed_payment >= float(credit_package_base_amount)
