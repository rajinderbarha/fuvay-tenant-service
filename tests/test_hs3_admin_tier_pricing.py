"""Guard that retired Admin Home Services tier pricing stays removed."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADMIN = ROOT / "frontend/super-admin"
MATCHING = (
    ROOT / "app/engines/home_service_booking/matching_engine.py"
).read_text(encoding="utf-8-sig")
NAV = (ADMIN / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8-sig")


def test_retired_admin_pricing_pages_are_deleted():
    for rel in (
        "app/admin/home-services/price-experience/page.tsx",
        "app/admin/pricing-rules/page.tsx",
        "app/admin/pricing/bargain-rules/page.tsx",
        "app/admin/pricing/provider-overrides/page.tsx",
    ):
        assert not (ADMIN / rel).exists()


def test_tier_computation_is_absent_from_runtime_engines():
    for marker in (
        "compute_symmetric_customer_price_tiers",
        "compute_price_tiers",
        "PRICE_TIER_TO_FIELD",
    ):
        assert marker not in MATCHING


def test_retired_bargain_engine_is_deleted():
    assert not (ROOT / "app/engines/admin_catalog/bargain_engine.py").exists()
    assert not (ROOT / "app/engines/admin_catalog/bargain_schemas.py").exists()


def test_admin_navigation_has_no_tier_or_bargain_surface():
    for marker in ("Price Experience", "Bargain Rules", "Provider Overrides"):
        assert marker not in NAV
