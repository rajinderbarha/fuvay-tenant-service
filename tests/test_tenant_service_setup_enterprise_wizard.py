"""Canonical tenant service setup/workspace certification."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"
LEGACY = FRONTEND / "app/(tenant)/provider/service-setup/page.tsx"
SETUP = (
    FRONTEND / "app/(onboarding)/tenant/home-services/setup/services-pricing/page.tsx"
).read_text(encoding="utf-8-sig")
WORKSPACE = (
    FRONTEND / "app/(tenant)/home-services/services/[[...serviceId]]/page.tsx"
).read_text(encoding="utf-8-sig")
NAV = (FRONTEND / "lib/nav-config.ts").read_text(encoding="utf-8-sig")
LAYOUT = (FRONTEND / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")
PROVIDER_OPTION_ROUTER = (
    ROOT / "app/engines/admin_catalog/service_option_provider_router.py"
).read_text(encoding="utf-8-sig")
CUSTOMER_OPTION_ROUTER = (
    ROOT / "app/engines/admin_catalog/service_option_customer_router.py"
).read_text(encoding="utf-8-sig")


def test_deprecated_duplicate_is_deleted():
    assert not LEGACY.exists()


def test_navigation_uses_canonical_services_workspace():
    assert 'href: "/home-services/services"' in LAYOUT
    assert 'href: "/provider/service-setup"' not in NAV
    assert 'href: "/tenant/setup/services"' not in NAV


def test_setup_uses_admin_catalog_and_provider_owned_price_inputs():
    assert "homeServicesSetupApi.listAvailable" in SETUP
    assert "homeServicesSetupApi.listEnabled" in SETUP
    assert "defaultMin" in SETUP and "defaultMax" in SETUP
    assert "Choose what you provide and set your own prices" in SETUP


def test_type_brand_prices_are_scoped_without_admin_tiers():
    assert "setTypePricing" in SETUP
    assert "setBrandPricing" in SETUP
    assert "serviceTypeId" in SETUP and "brandId" in SETUP
    for retired in ("Low/Mid/High", "Bargain Rules", "customer-price-preview"):
        assert retired not in SETUP


def test_post_activation_workspace_edits_through_setup_source_of_truth():
    assert "homeServicesSetupApi" in WORKSPACE
    assert "/tenant/home-services/setup/services-pricing" in WORKSPACE
    assert "return_to=%2Fhome-services%2Fservices" in WORKSPACE


def test_provider_option_endpoints_return_lists():
    assert "ApiResponse[list]" in PROVIDER_OPTION_ROUTER
    assert "ApiResponse[list]" in CUSTOMER_OPTION_ROUTER
