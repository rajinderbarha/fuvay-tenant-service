"""Retired customer price-experience/tier pricing certification."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_admin_and_tenant_price_preview_pages_are_deleted():
    assert not (
        ROOT / "frontend/super-admin/app/admin/home-services/price-experience/page.tsx"
    ).exists()
    assert not (
        ROOT / "frontend/tenant-portal/app/(tenant)/provider/customer-price-preview/page.tsx"
    ).exists()


def test_preview_routes_and_clients_are_removed():
    admin_router = (
        ROOT / "app/engines/admin_catalog/auto_price_options_router.py"
    ).read_text(encoding="utf-8-sig")
    tenant_router = (
        ROOT / "app/engines/admin_catalog/tenant_router.py"
    ).read_text(encoding="utf-8-sig")
    admin_api = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8-sig")
    tenant_api = (ROOT / "frontend/tenant-portal/lib/api.ts").read_text(encoding="utf-8-sig")

    for src in (admin_router, tenant_router, admin_api, tenant_api):
        assert "price-experience/preview" not in src
        assert "customer-price-preview" not in src
        assert "price-options/preview" not in src
        assert "previewPriceExperience" not in src


def test_matching_engine_no_longer_exposes_price_tier_helpers():
    matching_engine = (
        ROOT / "app/engines/home_service_booking/matching_engine.py"
    ).read_text(encoding="utf-8-sig")
    assert "def compute_price_tiers" not in matching_engine
    assert "def resolve_customer_offer_for_tier" not in matching_engine
    assert "PRICE_TIER_TO_FIELD" not in matching_engine


def test_booking_confirmation_accepts_standard_only():
    service = (ROOT / "app/engines/home_service_booking/service.py").read_text(encoding="utf-8-sig")
    assert 'price_tier != "standard"' in service
    assert "Only price_tier='standard' is supported" in service
    assert 'selected_tier != "standard"' in service


def test_booking_price_uses_home_services_finance_for_customer_total():
    service = (ROOT / "app/engines/home_service_booking/service.py").read_text(encoding="utf-8-sig")
    assert "get_current_policy_by_vertical_key" in service
    assert "calculate_customer_platform_fee" in service
    assert "home_services_match_and_price" in service
