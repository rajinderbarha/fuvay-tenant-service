"""Canonical Home Services provider pricing/setup certification."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"
PAGE = (
    FRONTEND / "app/(onboarding)/tenant/home-services/setup/services-pricing/page.tsx"
).read_text(encoding="utf-8-sig")
LEGACY = FRONTEND / "app/(tenant)/tenant/setup/services/page.tsx"


def test_one_canonical_write_surface():
    assert "homeServicesSetupApi.listAvailable" in PAGE
    assert not LEGACY.exists()


def test_provider_price_hierarchy_is_default_type_brand():
    assert "Most specific provider price wins" in PAGE
    assert "setTypePricing" in PAGE
    assert "setBrandPricing" in PAGE
    assert "brandPricingByType" in PAGE


def test_inspection_price_is_single_visit_fee():
    assert "isInspectionMode" in PAGE
    assert "Type and Brand never change the Repair price" in PAGE
    assert "tenant_visit_fee" in PAGE


def test_consultation_and_warranty_contracts_are_visible():
    assert "consultationFee" in PAGE
    assert "updatePricingPolicy" in PAGE
    assert "platform minimum is 5 days" in PAGE


def test_retired_tier_preview_is_absent():
    for marker in ("Low/Mid/High", "Customer Price Options", "Bargain Rules"):
        assert marker not in PAGE
