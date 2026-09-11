"""Regression coverage for provider finance deduction clarity.

These checks intentionally do not require PostgreSQL or a running frontend.
They protect the two user-visible regressions found on the live tenant portal:
the related-job link routed to a non-existent page, and the headline usage
total omitted the customer platform-fee recovery that had moved the wallet.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "app/engines/finance_hub/tenant_hs_finance_service.py"
PAGE = ROOT / "frontend/tenant-portal/app/(tenant)/home-services/finance/FinancePage.tsx"
API = ROOT / "frontend/tenant-portal/lib/api-hs-finance-tenant.ts"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_related_job_opens_the_unified_provider_workspace() -> None:
    page = source(PAGE)
    assert "/home-services/bookings-jobs?job_id=${encodeURIComponent(r.related_job_id)}" in page
    assert "href={`/jobs/${r.related_job_id}`}" not in page
    assert "Open job →" in page


def test_usage_total_reconciles_commission_and_customer_fee_recovery() -> None:
    service = source(SERVICE)
    assert "commission_this_month = await event_debits(" in service
    assert "fee_recovery_this_month = await event_debits(" in service
    assert "used_this_month = commission_this_month + fee_recovery_this_month" in service
    assert "deducted_total = commission_total + fee_recovery_total" in service
    for key in (
        "provider_commission_this_month",
        "customer_fee_recovery_this_month",
        "provider_commission_total",
        "customer_fee_recovery_total",
    ):
        assert f'"{key}"' in service


def test_provider_policy_discloses_fee_remittance_separately() -> None:
    service = source(SERVICE)
    api = source(API)
    page = source(PAGE)
    assert '"customer_fee_recovery_enabled"' in service
    assert '"customer_fee_percentage"' in service
    assert "it is not a second provider commission" in service
    assert "customer_fee_recovery_enabled: boolean" in api
    assert 'title="Job settlement deductions"' in page
    assert "Platform charge" in page
    assert "Total job deductions this month" in page


def test_ledger_labels_identify_the_two_distinct_movements() -> None:
    service = source(SERVICE)
    assert 'EVENT_COMPLETED_JOB_DEDUCTION: "Provider commission"' in service
    assert 'RECOVERY_EVENT_TYPE: "Platform charge"' in service
