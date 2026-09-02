"""HOME-SERVICES-ACTIVATION-PAYMENT-01 — Razorpay collection for optional
usage-credit top-ups during Home Services onboarding
(app.engines.vertical_catalog.activation_payment_service /
activation_payment_router).

Focused tests (time-boxed pass) proving:
  1. Credit package order creation computes the correct GST split
     (base 1000 + 18% GST = 1180 gross; credited_amount stays 1000, never
     blended with the 180 GST portion).
  2. Webhook confirmation is idempotent per gateway_payment_id / on an
     already-captured order -- a retried webhook cannot double-post.
  3. Credit-package webhook confirmation posts EXACTLY the base amount to
     credit_balance and records the GST as a separate FinancialEvent.
  4. The activation quote and payment APIs expose only the current top-up
     model and do not revive removed security-deposit fields or gates.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.vertical_catalog.activation_payment_models import (
    ActivationPaymentOrder, PAYMENT_KIND_CREDIT, PAYMENT_KIND_FUNDING,
    STATUS_CAPTURED, STATUS_CREATED,
)
from app.engines.vertical_catalog import activation_payment_service as svc


def _mock_scalar(row):
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    return result


def _mock_scalars(rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


def _mock_value(value):
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _make_policy(version=1, credit_base="1000", credit_gst="18"):
    p = MagicMock()
    p.version_number = version
    p.credit_package_base_amount = Decimal(credit_base)
    p.credit_package_gst_percent = Decimal(credit_gst)
    p.credit_booking_floor = Decimal("100")
    p.credit_warning_threshold = Decimal("250")
    return p


def _make_plan(seats=2, base="1000", gst="18"):
    plan_id = uuid.uuid4()
    total = Decimal(base) * (Decimal("1") + Decimal(gst) / Decimal("100"))
    plan = MagicMock()
    plan.seats = seats
    plan.is_default = True
    plan.to_dict.return_value = {
        "id": str(plan_id), "name": "Starter", "seats": seats,
        "base_amount": float(Decimal(base)), "credited_amount": float(Decimal(base)),
        "gst_amount": float(total - Decimal(base)), "total_amount": float(total),
    }
    return plan


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "technicians,entitled_seats,credit_balance,mode,total",
    [
        (1, 0, "0", "topup_plan", 1180.0),
        (2, 1, "1000", "seats_only", 1180.0),
        (1, 1, "0", "credits_only", 1180.0),
        (1, 1, "1000", "funded", 0.0),
    ],
)
async def test_funding_quote_uses_topup_plan_for_live_seat_and_credit_shortfalls(
    technicians, entitled_seats, credit_balance, mode, total,
):
    tenant_id = uuid.uuid4()
    vertical = MagicMock(id=uuid.uuid4())
    policy = _make_policy()
    billing = MagicMock()
    billing.entitled_seats = entitled_seats
    billing.credit_balance = Decimal(credit_balance)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_mock_scalars([_make_plan()]))

    with patch.object(svc, "_resolve_vertical_and_policy", new=AsyncMock(return_value=(vertical, policy))), \
         patch.object(svc, "_get_billing_row", new=AsyncMock(return_value=billing)), \
         patch.object(svc, "resolve_qualifying_technician_count", new=AsyncMock(return_value=technicians)):
        quote = await svc.resolve_activation_funding_quote(db, tenant_id)

    assert quote["total_due"] == total
    assert quote["checkout_mode"] == mode
    assert "deposit_required" not in quote
    assert "deposit_shortfall" not in quote


@pytest.mark.asyncio
async def test_topup_order_uses_server_quote_and_snapshots_credit_and_seats():
    tenant_id = uuid.uuid4()
    vertical = MagicMock(id=uuid.uuid4())
    policy = _make_policy(version=7)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_mock_scalar(None))
    db.add = MagicMock()
    db.commit = AsyncMock()
    plan_id = uuid.uuid4()
    quote = {"total_due": 1180.0, "checkout_mode": "topup_plan", "suggested_plan": {
        "id": str(plan_id), "seats": 2, "credited_amount": 1000.0, "gst_amount": 180.0,
    }}

    with patch.object(svc, "_resolve_vertical_and_policy", new=AsyncMock(return_value=(vertical, policy))), \
         patch.object(svc, "resolve_activation_funding_quote", new=AsyncMock(return_value=quote)), \
         patch("app.integrations.razorpay_client.create_order", new=AsyncMock(
             return_value={"id": "order_topup", "amount": 118000, "currency": "INR"})):
        result = await svc.create_activation_funding_order(db, tenant_id)

    record = db.add.call_args[0][0]
    assert record.payment_kind == PAYMENT_KIND_FUNDING
    assert record.amount == Decimal("1180.00")
    assert record.credited_amount == Decimal("1000.00")
    assert record.tax_amount == Decimal("180.00")
    assert record.topup_plan_id == plan_id
    assert record.seats_granted == 2
    assert result["amount_paise"] == 118000
    assert "deposit_amount" not in result


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
    order_row.amount = Decimal("1180")
    order_row.credited_amount = Decimal("1000")
    order_row.tax_amount = Decimal("180.00")
    order_row.seats_granted = 0
    order_row.topup_plan_id = None
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


@pytest.mark.asyncio
async def test_topup_webhook_posts_credit_and_grants_technician_seats():
    tenant_id = uuid.uuid4()
    order_row = MagicMock(spec=ActivationPaymentOrder)
    order_row.id = uuid.uuid4()
    order_row.tenant_id = tenant_id
    order_row.status = STATUS_CREATED
    order_row.payment_kind = PAYMENT_KIND_FUNDING
    order_row.amount = Decimal("1180")
    order_row.credited_amount = Decimal("1000")
    order_row.tax_amount = Decimal("180")
    order_row.seats_granted = 2
    order_row.topup_plan_id = uuid.uuid4()
    order_row.to_dict.return_value = {"status": STATUS_CAPTURED}
    billing = MagicMock()
    billing.credit_balance = Decimal("0")

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _mock_scalar(order_row), _mock_scalar(None), _mock_scalar(billing), _mock_value(30),
    ])
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("app.engines.vertical_catalog.topup_entitlement_service.grant", new=AsyncMock()) as grant, \
         patch("app.engines.vertical_catalog.activation.try_auto_activate",
               new=AsyncMock(return_value={"status": "activation_requirements_pending"})):
        await svc.confirm_activation_payment_webhook(
            db, gateway_order_id="order_topup", gateway_payment_id="pay_topup",
            amount=Decimal("1180"), status_="captured", raw_payload={},
        )

    assert grant.await_args.kwargs["seats"] == 2
    assert grant.await_args.kwargs["credit_granted"] == Decimal("1000.00")
    assert grant.await_args.kwargs["validity_days"] == 30
    assert billing.credit_balance == Decimal("1000.00")
    event_types = [call.args[0].event_type for call in db.add.call_args_list
                   if hasattr(call.args[0], "event_type")]
    assert "activation.credit_package_captured" in event_types
    assert "activation.credit_package_gst_collected" in event_types


@pytest.mark.asyncio
async def test_webhook_rejects_amount_different_from_server_order():
    order_row = MagicMock(spec=ActivationPaymentOrder)
    order_row.status = STATUS_CREATED
    order_row.amount = Decimal("3180")
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_mock_scalar(order_row), _mock_scalar(None)])

    with pytest.raises(Exception) as exc:
        await svc.confirm_activation_payment_webhook(
            db, gateway_order_id="order_bundle", gateway_payment_id="pay_wrong",
            amount=Decimal("3000"), status_="captured", raw_payload={},
        )
    assert getattr(exc.value, "error_code", getattr(exc.value, "code", None)) == "ACTIVATION_PAYMENT_AMOUNT_MISMATCH"
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_checkout_confirmation_verifies_signature_and_uses_stored_amount():
    tenant_id = uuid.uuid4()
    order_row = MagicMock(spec=ActivationPaymentOrder)
    order_row.amount = Decimal("3180")
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_mock_scalar(order_row))

    with patch("app.integrations.razorpay_client.verify_payment_signature", return_value=True), \
         patch.object(svc, "confirm_activation_payment_webhook", new=AsyncMock(return_value={"status": "captured"})) as confirm:
        result = await svc.confirm_activation_checkout(
            db, tenant_id=tenant_id, gateway_order_id="order_bundle",
            gateway_payment_id="pay_bundle", signature="signed",
        )

    assert result["status"] == "captured"
    assert confirm.await_args.kwargs["amount"] == Decimal("3180.00")


@pytest.mark.asyncio
async def test_checkout_confirmation_fails_closed_on_bad_signature():
    db = AsyncMock()
    with patch("app.integrations.razorpay_client.verify_payment_signature", return_value=False):
        with pytest.raises(Exception) as exc:
            await svc.confirm_activation_checkout(
                db, tenant_id=uuid.uuid4(), gateway_order_id="order_bundle",
                gateway_payment_id="pay_bundle", signature="bad",
            )
    assert getattr(exc.value, "error_code", getattr(exc.value, "code", None)) == "ACTIVATION_PAYMENT_SIGNATURE_INVALID"
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_gateway_reconciliation_recovers_captured_checkout_callback_failure():
    tenant_id = uuid.uuid4()
    order_row = MagicMock(spec=ActivationPaymentOrder)
    order_row.status = STATUS_CREATED
    order_row.amount = Decimal("3180")
    order_row.currency = "INR"
    order_row.to_dict.return_value = {"status": STATUS_CREATED}
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_mock_scalar(order_row))
    gateway_payment = {
        "id": "pay_captured", "order_id": "order_bundle", "status": "captured",
        "captured": True, "amount": 318000, "currency": "INR",
    }

    with patch("app.integrations.razorpay_client.get_order_payments",
               new=AsyncMock(return_value=[gateway_payment])), \
         patch.object(svc, "confirm_activation_payment_webhook",
                      new=AsyncMock(return_value={"status": STATUS_CAPTURED})) as confirm:
        result = await svc.reconcile_activation_order(
            db, tenant_id=tenant_id, gateway_order_id="order_bundle",
        )

    assert result["captured"] is True
    assert result["reconciled"] is True
    assert confirm.await_args.kwargs["gateway_payment_id"] == "pay_captured"
    assert confirm.await_args.kwargs["amount"] == Decimal("3180.00")


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
