"""Home Services menu and provider-price ownership certification."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADMIN = ROOT / "frontend/super-admin"
TENANT = ROOT / "frontend/tenant-portal"
ADMIN_LAYOUT = (ADMIN / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8-sig")
TENANT_NAV = (TENANT / "lib/nav-config.ts").read_text(encoding="utf-8-sig")
TENANT_LAYOUT = (TENANT / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")
SETUP = (
    TENANT / "app/(onboarding)/tenant/home-services/setup/services-pricing/page.tsx"
).read_text(encoding="utf-8-sig")
FINANCE = (
    ADMIN / "app/admin/home-services/finance/page.tsx"
).read_text(encoding="utf-8-sig")


def test_admin_menu_uses_catalog_and_finance_not_price_rules():
    combined = ADMIN_LAYOUT
    assert "/admin/catalog-workspace" in combined
    assert "/admin/home-services/finance" in combined
    for retired in ("/admin/pricing-rules", "Price Experience", "Bargain Rules"):
        assert retired not in combined


def test_tenant_menu_uses_operational_services_workspace():
    combined = TENANT_NAV + TENANT_LAYOUT
    assert "/home-services/services" in combined
    assert "/provider/service-setup" not in combined


def test_provider_sets_default_type_and_brand_price_ranges():
    assert "tenant_min_price" in SETUP
    assert "tenant_max_price" in SETUP
    assert "setTypePricing" in SETUP
    assert "setBrandPricing" in SETUP


def test_repair_uses_visit_fee_not_type_or_brand_prices():
    assert "Type and Brand never change the Repair price" in SETUP
    assert "tenant_visit_fee" in SETUP


def test_customer_and_provider_commissions_live_in_home_services_finance():
    assert "Monetization" in FINANCE
    assert "customer" in FINANCE.lower()
    assert "provider" in FINANCE.lower()


def test_old_price_pages_are_deleted():
    for path in (
        ADMIN / "app/admin/pricing-rules/page.tsx",
        ADMIN / "app/admin/home-services/price-experience/page.tsx",
        TENANT / "app/(tenant)/provider/customer-price-preview/page.tsx",
    ):
        assert not path.exists()
