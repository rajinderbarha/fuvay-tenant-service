"""Tenant Home Services setup source-of-truth certification."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"
SETUP = (
    FRONTEND / "app/(onboarding)/tenant/home-services/setup/services-pricing/page.tsx"
).read_text(encoding="utf-8-sig")
LEGACY = FRONTEND / "app/(tenant)/tenant/setup/services/page.tsx"
API = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")


def test_legacy_parallel_wizard_is_deleted():
    assert not LEGACY.exists()


def test_setup_loads_available_and_enabled_catalog_services():
    assert "homeServicesSetupApi.listAvailable" in SETUP
    assert "homeServicesSetupApi.listEnabled" in SETUP
    assert "ServiceRequirementsPanel" in SETUP


def test_provider_owns_default_type_and_brand_prices():
    for marker in (
        "updateEnabledService",
        "setTypePricing",
        "setBrandPricing",
        "tenant_min_price",
        "tenant_max_price",
    ):
        assert marker in SETUP


def test_inspection_services_use_one_visit_fee_not_type_brand_prices():
    assert "isInspectionMode" in SETUP
    assert "Type and Brand never change the Repair price" in SETUP
    assert "tenant_visit_fee" in SETUP


def test_provider_wide_consultation_fee_is_configurable_once():
    assert "consultationFee" in SETUP
    assert "updatePricingPolicy" in SETUP


def test_warranty_has_platform_minimum():
    assert 'useState("5")' in SETUP
    assert "platform minimum is 5 days" in SETUP


def test_admin_tiers_and_bargain_preview_are_absent():
    for retired in (
        "Low/Mid/High",
        "Bargain Rules",
        "compute_price_tiers",
        "Customer Price Options",
    ):
        assert retired not in SETUP


def test_setup_supports_post_activation_return_path():
    assert 'searchParams.get("return_to")' in SETUP
    assert "returnTo" in SETUP


def test_api_client_has_canonical_setup_methods():
    for marker in (
        "listAvailable",
        "listEnabled",
        "setTypePricing",
        "setBrandPricing",
        "updatePricingPolicy",
    ):
        assert marker in API
