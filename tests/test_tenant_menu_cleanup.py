"""Tenant navigation and retired-route cleanup certification."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"
NAV = (FRONTEND / "lib/nav-config.ts").read_text(encoding="utf-8-sig")
LAYOUT = (FRONTEND / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")
LEGACY_SETUP = (
    FRONTEND / "app/(tenant)/provider/service-setup/page.tsx"
).read_text(encoding="utf-8-sig")
CANONICAL_SERVICES = (
    FRONTEND / "app/(tenant)/home-services/services/[[...serviceId]]/page.tsx"
).read_text(encoding="utf-8-sig")


def test_navigation_uses_current_business_operations_services_and_team_routes():
    combined = NAV + LAYOUT
    for href in (
        "/home-services/services",
        "/business/coverage-hours",
        "/home-services/team",
        "/customers",
        "/home-services/bookings-jobs",
        "/home-services/dispatch",
        "/home-services/availability",
    ):
        assert href in combined


def test_navigation_has_no_retired_service_setup_or_price_preview_routes():
    combined = NAV + LAYOUT
    for href in (
        'href: "/provider/service-setup"',
        'href: "/tenant/setup/services"',
        "/provider/customer-price-preview",
        "/provider/pricing",
    ):
        assert href not in combined


def test_retired_provider_setup_is_redirect_only():
    assert 'redirect("/home-services/services")' in LEGACY_SETUP
    assert "providerOfferingsApi" not in LEGACY_SETUP


def test_deleted_customer_price_preview_page_stays_deleted():
    assert not (
        FRONTEND / "app/(tenant)/provider/customer-price-preview/page.tsx"
    ).exists()


def test_current_services_workspace_links_to_onboarding_source_of_truth():
    assert "Services & Pricing" in CANONICAL_SERVICES
    assert "/tenant/home-services/setup/services-pricing" in CANONICAL_SERVICES


def test_retired_bargain_and_price_tier_labels_are_absent_from_navigation():
    for label in ("Bargain Rules", "Manual Bargain Setup", "Low/Mid/High"):
        assert label not in NAV + LAYOUT
