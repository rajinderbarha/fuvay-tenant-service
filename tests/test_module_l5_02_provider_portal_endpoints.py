"""MODULE-L5-02 — tenant-portal endpoint resilience.

Live verification (as tenant_owner) of the tenant-portal found four endpoints
returning 500 for the demo tenant: provider wallet (bare ValueError) and three
that query un-provisioned tables (provider_onboarding_statuses,
provider_onboarding_items, provider_package_purchases). All now degrade
gracefully to a sensible default. These tests pin the source-level fixes.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROV_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8")
WALLET = (ROOT / "app/engines/invoice_payment/provider_router.py").read_text(encoding="utf-8")


def test_provider_wallet_handles_missing_wallet():
    idx = WALLET.index("async def provider_get_wallet(")
    body = WALLET[idx:idx + 900]
    assert "except ValueError" in body and '"current_balance": "0"' in body


def _guarded(marker: str) -> bool:
    idx = PROV_ROUTER.index(marker)
    body = PROV_ROUTER[idx:idx + 1400]
    return "except Exception" in body and "rollback" in body


def test_onboarding_status_guarded():
    assert _guarded('async def get_onboarding_status(')


def test_onboarding_items_guarded():
    assert _guarded('async def get_onboarding_items(')


def test_packages_status_guarded():
    assert _guarded('async def get_packages_status(')


def test_bookability_price_range_counts_fixed_price_services():
    """MODULE-L5-02: PROVIDER_PRICE_RANGE_MISSING must not permanently block a
    provider whose published services are all fixed-price / no-override (they
    are priced at the admin level and cannot set a tenant range). The priced
    check now also counts master_services with tenant_override_allowed=false
    and a base/min price."""
    assert "ms.tenant_override_allowed = false" in PROV_ROUTER
    assert "COALESCE(ms.base_price, ms.min_price) IS NOT NULL" in PROV_ROUTER
