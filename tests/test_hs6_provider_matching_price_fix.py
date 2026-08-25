"""Provider-first matching with provider-owned pricing certification.

The retired Low/Mid/High bargain-tier model must not return. Fuvay selects
one eligible provider first, resolves that provider's published price, and
applies the current Home Services Finance policy on the server.
"""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
MATCHING_ENGINE = (
    ROOT / "app/engines/home_service_booking/matching_engine.py"
).read_text(encoding="utf-8-sig")
BOOKING_SERVICE = (
    ROOT / "app/engines/home_service_booking/service.py"
).read_text(encoding="utf-8-sig")


def test_retired_tier_pricing_helpers_are_absent():
    for marker in (
        "def compute_price_tiers",
        "def resolve_customer_offer_for_tier",
        "def round_to_nearest_10",
        "PRICE_TIER_TO_FIELD",
    ):
        assert marker not in MATCHING_ENGINE


def test_still_home_services_only():
    assert "assert_home_services_vertical" in MATCHING_ENGINE


def test_provider_is_selected_before_price_is_resolved():
    match_idx = BOOKING_SERVICE.index("match = await select_best_provider")
    selected_idx = BOOKING_SERVICE.index(
        "selected_tenant_id = uuid.UUID(signals.tenant_id)", match_idx
    )
    price_idx = BOOKING_SERVICE.index("home_services_match_and_price", selected_idx)
    assert match_idx < selected_idx < price_idx


def test_provider_price_and_finance_policy_are_authoritative():
    assert "get_current_policy_by_vertical_key" in BOOKING_SERVICE
    assert "calculate_customer_platform_fee" in BOOKING_SERVICE
    assert "home_services_match_and_price" in BOOKING_SERVICE


def test_only_standard_server_resolved_price_contract_is_accepted():
    assert 'price_tier != "standard"' in BOOKING_SERVICE
    assert "Only price_tier='standard' is supported" in BOOKING_SERVICE
    assert 'selected_tier != "standard"' in BOOKING_SERVICE


def test_competitor_comparison_cannot_set_the_booking_price():
    select_start = MATCHING_ENGINE.index("async def select_best_provider")
    eligibility_start = MATCHING_ENGINE.index("async def _passes_full_eligibility_gate")
    selection_body = MATCHING_ENGINE[select_start:eligibility_start]
    assert "get_area_market_comparison" not in selection_body
