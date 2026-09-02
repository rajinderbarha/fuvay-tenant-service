"""MODULE-L5-02 — tenant-portal endpoint resilience.

Live verification (as tenant_owner) found endpoints querying un-provisioned
legacy tables. Onboarding is now projected from the canonical operational
gates; the wallet still degrades safely when no row exists.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROV_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8")
WALLET = (ROOT / "app/engines/invoice_payment/provider_router.py").read_text(encoding="utf-8")


def test_provider_wallet_handles_missing_wallet():
    idx = WALLET.index("async def provider_get_wallet(")
    body = WALLET[idx:idx + 900]
    assert "except ValueError" in body and '"current_balance": "0"' in body


def test_onboarding_status_uses_live_canonical_gates():
    helper = PROV_ROUTER[PROV_ROUTER.index("async def _build_live_provider_onboarding"):]
    assert "_evaluate_provider_bookability" in helper
    assert "provider_onboarding_statuses" not in helper
    assert '"progress_percentage"' in helper


def test_onboarding_items_are_actionable_not_an_empty_placeholder():
    helper = PROV_ROUTER[PROV_ROUTER.index("async def _build_live_provider_onboarding"):]
    for key in ("services_published", "service_area", "technician_ready", "technician_seats"):
        assert key in helper
    body = PROV_ROUTER[PROV_ROUTER.index("async def get_onboarding_items("):]
    assert '_build_live_provider_onboarding' in body[:800]


def test_retired_package_status_endpoint_is_absent():
    assert 'async def get_packages_status(' not in PROV_ROUTER
    assert "provider_package_purchases" not in PROV_ROUTER


def test_bookability_price_range_counts_fixed_price_services():
    """MODULE-L5-02: PROVIDER_PRICE_RANGE_MISSING must not permanently block a
    provider whose published services are all fixed-price / no-override (they
    are priced at the admin level and cannot set a tenant range). The priced
    check now also counts master_services with tenant_override_allowed=false
    and a base/min price."""
    assert "ms.tenant_override_allowed = false" in PROV_ROUTER
    assert "COALESCE(ms.base_price, ms.min_price) IS NOT NULL" in PROV_ROUTER
