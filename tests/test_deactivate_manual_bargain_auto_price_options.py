"""Certification for removing the retired admin price-experience surface.

The current product model is provider-owned service pricing plus Home Services
Finance monetization. Admin no longer configures customer price tiers, min/max
price bands, manual bargain rules, or provider pricing overrides.
"""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
SUPER_ADMIN = ROOT / "frontend/super-admin"
TENANT_PORTAL = ROOT / "frontend/tenant-portal"

ADMIN_LAYOUT = (SUPER_ADMIN / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8-sig")
API_TS = (SUPER_ADMIN / "lib/api.ts").read_text(encoding="utf-8-sig")
PROVIDER_MATCHING_PAGE = (
    SUPER_ADMIN / "app/admin/home-services/provider-matching/page.tsx"
).read_text(encoding="utf-8-sig")
MATCHING_DIAGNOSTICS_PAGE = (
    SUPER_ADMIN / "app/admin/home-services/matching-diagnostics/page.tsx"
).read_text(encoding="utf-8-sig")
TENANT_LAYOUT = (TENANT_PORTAL / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")
AUTO_PRICE_ROUTER = (
    ROOT / "app/engines/admin_catalog/auto_price_options_router.py"
).read_text(encoding="utf-8-sig")
FEATURE_FLAGS_MODULE = (ROOT / "app/core/feature_flags.py").read_text(encoding="utf-8-sig")


def test_retired_admin_pricing_pages_are_deleted():
    retired_paths = [
        "app/admin/home-services/price-experience/page.tsx",
        "app/admin/pricing/page.tsx",
        "app/admin/pricing/bargain-rules/page.tsx",
        "app/admin/pricing/provider-overrides/page.tsx",
        "app/admin/pricing/commission/page.tsx",
        "app/admin/pricing-rules/page.tsx",
    ]
    for relative in retired_paths:
        assert not (SUPER_ADMIN / relative).exists(), relative


def test_admin_navigation_no_longer_exposes_retired_pricing_surfaces():
    combined = ADMIN_LAYOUT
    forbidden = [
        "hs-price-experience",
        "Customer Price Experience",
        "/admin/home-services/price-experience",
        "/admin/pricing",
        "/admin/pricing-rules",
        "Bargain Rules",
    ]
    for value in forbidden:
        assert value not in combined


def test_admin_api_client_no_longer_exposes_retired_pricing_endpoints():
    forbidden = [
        "previewPriceExperience",
        "/v1/admin/home-services/price-experience/preview",
        "/v1/admin/pricing-rules",
        "/v1/admin/pricing/bargain-rules",
        "/v1/admin/pricing/provider-overrides",
        "/v1/admin/tiers",
        "/v1/admin/tier-locations",
    ]
    for value in forbidden:
        assert value not in API_TS


def test_backend_admin_price_preview_is_not_registered():
    assert '"/price-experience/preview"' not in AUTO_PRICE_ROUTER
    assert "compute_price_tiers" not in AUTO_PRICE_ROUTER


def test_provider_matching_and_diagnostics_remain_active():
    assert "Booking Match Policy" in PROVIDER_MATCHING_PAGE
    assert "Fuvay selects the best eligible Home Services provider" in PROVIDER_MATCHING_PAGE
    assert "Booking Match Diagnostics" in MATCHING_DIAGNOSTICS_PAGE
    assert "autoPriceOptionsApi.runMatchingDiagnostics" in MATCHING_DIAGNOSTICS_PAGE
    assert "Eligible Providers" in MATCHING_DIAGNOSTICS_PAGE
    assert "customer_visible_reason" in MATCHING_DIAGNOSTICS_PAGE
    assert "internal_score_breakdown" in MATCHING_DIAGNOSTICS_PAGE


def test_tenant_price_preview_page_and_client_are_deleted():
    assert "provider-customer-price-preview" not in TENANT_LAYOUT
    assert "Customer Price Preview" not in TENANT_LAYOUT
    assert not (TENANT_PORTAL / "app/(tenant)/provider/customer-price-preview/page.tsx").exists()
    tenant_api = (TENANT_PORTAL / "lib/api.ts").read_text(encoding="utf-8-sig")
    assert "getCustomerPricePreview" not in tenant_api
    assert "/v1/tenant/home-services/customer-price-preview" not in tenant_api
    assert "getMatchingReadiness" in tenant_api


def test_backend_tenant_endpoints_are_read_only():
    assert '"/customer-price-preview"' not in AUTO_PRICE_ROUTER
    assert '"/matching-readiness"' in AUTO_PRICE_ROUTER
    idx = AUTO_PRICE_ROUTER.index("tenant_matching_readiness")
    tenant_block = AUTO_PRICE_ROUTER[idx:]
    assert "@tenant_router.post" not in tenant_block
    assert "@tenant_router.put" not in tenant_block


def test_feature_flag_defaults_match_business_decision():
    from app.core.feature_flags import DEFAULTS, PROVIDER_FIRST_MATCHING_ENABLED

    assert DEFAULTS[PROVIDER_FIRST_MATCHING_ENABLED] is True
    flags_source = (ROOT / "app/core/feature_flags.py").read_text(encoding="utf-8")
    assert "MANUAL_BARGAIN_RULES_ENABLED" not in flags_source
    assert "AUTO_PRICE_OPTIONS_ENABLED" not in flags_source


def test_no_forbidden_finance_labels_in_remaining_ui():
    forbidden = [
        "Cash Wallet",
        "Wallet Balance",
        "Withdraw",
        "Withdrawable Balance",
        "Tenant Payout",
        "Provider Earnings Wallet",
        "Escrow",
        "Platform Collected Service Payment",
        "Provider Cash Balance",
        "Bargain Rule Builder",
        "Manual Bargain Setup",
    ]
    combined = PROVIDER_MATCHING_PAGE + MATCHING_DIAGNOSTICS_PAGE
    for label in forbidden:
        assert label not in combined
