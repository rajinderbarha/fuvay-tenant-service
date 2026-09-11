"""Regression coverage for the canonical amount in admin job details."""
from decimal import Decimal
from types import SimpleNamespace

from app.engines.final_records.admin_router import _canonical_job_price_summary


def test_final_invoice_replaces_initial_booking_snapshot():
    booking = SimpleNamespace(price_snapshot={"customer_total": "157.50", "visit_fee": "150"})
    quote = SimpleNamespace(
        total_amount=Decimal("1310.00"),
        customer_payable_amount=Decimal("1375.50"),
        currency="INR",
        status="customer_approved",
        version_number=1,
    )
    invoice = SimpleNamespace(
        total_amount=Decimal("1310.00"),
        platform_fee_amount=Decimal("65.50"),
        customer_payable_amount=Decimal("1375.50"),
        credit_applied_amount=Decimal("0"),
        currency="INR",
        payment_mode="onsite",
        payment_status="paid",
        invoice_number="INV-TEST-1",
    )

    summary = _canonical_job_price_summary(booking=booking, quote=quote, invoice=invoice)

    assert summary == {
        "customer_total": "1375.50",
        "service_total": "1310.00",
        "platform_fee": "65.50",
        "credit_applied": "0",
        "currency": "INR",
        "payment_mode": "onsite",
        "payment_status": "paid",
        "invoice_number": "INV-TEST-1",
        "source": "final_invoice",
    }


def test_current_quote_is_used_when_no_invoice_exists():
    booking = SimpleNamespace(price_snapshot={"customer_total": "157.50"})
    quote = SimpleNamespace(
        total_amount=Decimal("1310.00"),
        customer_payable_amount=Decimal("1375.50"),
        currency="INR",
        status="customer_approved",
        version_number=2,
    )

    summary = _canonical_job_price_summary(booking=booking, quote=quote)

    assert summary["source"] == "current_quote"
    assert summary["customer_total"] == "1375.50"
    assert summary["service_total"] == "1310.00"
    assert summary["platform_fee"] == "65.50"


def test_booking_snapshot_remains_the_last_resort():
    booking = SimpleNamespace(price_snapshot={"customer_total": "157.50", "visit_fee": "150"})

    summary = _canonical_job_price_summary(booking=booking)

    assert summary == {
        "customer_total": "157.50",
        "visit_fee": "150",
        "source": "booking_snapshot",
    }


def test_empty_price_sources_return_none():
    assert _canonical_job_price_summary() is None
    assert _canonical_job_price_summary(booking=SimpleNamespace(price_snapshot=None)) is None
