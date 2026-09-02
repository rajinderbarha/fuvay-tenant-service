"""P0 guard for the retired provider service-setup duplicate."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
LEGACY = ROOT / "frontend/tenant-portal/app/(tenant)/provider/service-setup/page.tsx"
WORKSPACE = ROOT / "frontend/tenant-portal/app/(tenant)/home-services/services/[[...serviceId]]/page.tsx"
NAV = ROOT / "frontend/tenant-portal/lib/nav-config.ts"
LAYOUT = ROOT / "frontend/tenant-portal/components/layout/TenantLayout.tsx"


def test_legacy_route_exists_only_as_a_redirect():
    src = LEGACY.read_text(encoding="utf-8-sig")
    assert 'redirect("/home-services/services")' in src
    assert '"use client"' not in src
    assert "providerOfferingsApi" not in src


def test_operational_services_workspace_exists():
    assert WORKSPACE.exists()
    src = WORKSPACE.read_text(encoding="utf-8-sig")
    assert "Services & Pricing" in src
    assert "homeServicesSetupApi" in src


def test_navigation_has_no_legacy_destination():
    nav = NAV.read_text(encoding="utf-8-sig")
    layout = LAYOUT.read_text(encoding="utf-8-sig")
    assert 'href: "/home-services/services"' in layout
    assert 'href: "/provider/service-setup"' not in nav + layout
