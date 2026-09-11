"""Regression coverage for the canonical amount in admin job details."""
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from app.engines.final_records.admin_router import (
    _canonical_job_price_summary,
    _job_charge_ledger_summary,
)


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


def test_commission_and_platform_charge_are_not_marked_as_duplicates():
    rows = [
        SimpleNamespace(event_type="completed_job_deduction", credit_delta=Decimal("-65.50")),
        SimpleNamespace(event_type="customer_platform_charge_recovery", credit_delta=Decimal("-65.50")),
    ]

    summary = _job_charge_ledger_summary(rows)

    assert summary["duplicate_count"] == 0
    assert summary["commission_amount"] == "65.50"
    assert summary["platform_charge_amount"] == "65.50"
    assert summary["total_provider_credit_deduction"] == "131.00"


def test_repeated_same_charge_type_is_a_real_duplicate():
    rows = [
        SimpleNamespace(event_type="completed_job_deduction", credit_delta=Decimal("-25")),
        SimpleNamespace(event_type="completed_job_deduction", credit_delta=Decimal("-25")),
    ]

    summary = _job_charge_ledger_summary(rows)

    assert summary["duplicate_count"] == 1


def test_admin_job_page_renders_approved_items_and_both_charge_types():
    page = Path(
        "frontend/super-admin/app/admin/home-services/service-jobs/[jobId]/page.tsx"
    ).read_text(encoding="utf-8")

    assert "Complete Job Details" in page
    assert "Technician Estimate & Customer Approval" in page
    assert "d.quote_items" in page
    assert "Platform Charge Recovery" in page
    assert "Commission Charge" in page


def test_customer_fee_wording_is_not_exposed_in_home_services_finance_ui():
    paths = [
        Path("frontend/super-admin/app/admin/home-services/finance/page.tsx"),
        Path("frontend/super-admin/app/admin/finance/vertical-monetization/page.tsx"),
        Path("frontend/tenant-portal/app/(tenant)/home-services/finance/FinancePage.tsx"),
    ]
    visible_copy = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()

    assert "customer platform fee" not in visible_copy
    assert "customer platform charge" not in visible_copy
    assert "customer fee model" not in visible_copy
    assert "customer fee remitted" not in visible_copy
