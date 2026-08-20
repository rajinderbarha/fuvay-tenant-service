"""MODULE-L5-57 — retired customer price experience / tier pricing.

Home Services uses provider-owned prices plus the Home Services Finance
monetization policy. Admin and tenant Low/Mid/High preview surfaces are gone.
"""
from __future__ import annotations

import os


class TestPriceExperienceRetired:
    def _root(self):
        return os.path.join(os.path.dirname(__file__), "..")

    def _read(self, *parts: str) -> str:
        with open(os.path.join(self._root(), *parts), encoding="utf-8-sig") as f:
            return f.read()

    def test_admin_and_tenant_preview_pages_are_deleted(self):
        assert not os.path.exists(os.path.join(
            self._root(), "frontend", "super-admin", "app", "admin",
            "home-services", "price-experience", "page.tsx",
        ))
        assert not os.path.exists(os.path.join(
            self._root(), "frontend", "tenant-portal", "app", "(tenant)",
            "provider", "customer-price-preview", "page.tsx",
        ))

    def test_nav_and_clients_no_longer_link_preview_surfaces(self):
        combined = "\n".join([
            self._read("frontend", "super-admin", "lib", "nav-config.ts"),
            self._read("frontend", "super-admin", "lib", "api.ts"),
            self._read("frontend", "tenant-portal", "lib", "api.ts"),
        ])
        for value in [
            "/admin/home-services/price-experience",
            "/v1/admin/home-services/price-experience/preview",
            "/v1/tenant/home-services/customer-price-preview",
            "/v1/tenant/catalog/price-options/preview",
            "previewPriceExperience",
            "getCustomerPricePreview",
        ]:
            assert value not in combined

    def test_backend_routes_no_longer_register_preview_or_admin_pricing(self):
        combined = "\n".join([
            self._read("app", "engines", "admin_catalog", "auto_price_options_router.py"),
            self._read("app", "engines", "admin_catalog", "tenant_router.py"),
            self._read("app", "engines", "admin_catalog", "admin_router.py"),
        ])
        assert '@tenant_router.get("/customer-price-preview"' not in combined
        assert '@router.post("/price-options/preview"' not in combined
        active_lines = "\n".join(
            line for line in combined.splitlines()
            if line.lstrip().startswith("@router.") or line.lstrip().startswith("@tenant_router.")
        )
        assert '"/pricing/bargain' not in active_lines
        assert '"/pricing/provider-overrides' not in active_lines

    def test_booking_standard_price_uses_finance_policy(self):
        src = self._read("app", "engines", "home_service_booking", "service.py")
        assert 'price_tier != "standard"' in src
        assert "calculate_customer_platform_fee" in src
        assert "home_services_match_and_price" in src

    def test_matching_engine_no_longer_has_tier_helpers(self):
        src = self._read("app", "engines", "home_service_booking", "matching_engine.py")
        assert "def compute_price_tiers" not in src
        assert "def resolve_customer_offer_for_tier" not in src
        assert "PRICE_TIER_TO_FIELD" not in src
