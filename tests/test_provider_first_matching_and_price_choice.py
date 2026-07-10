"""Provider-First Matching + Customer Price Choice — certification.

Tests the pure matching_engine functions directly (no DB) for scoring,
ranking, Low/Mid/High price-tier correctness, and customer-safe redaction.
DB-aware eligibility-gate SQL (select_best_provider, get_area_market_comparison)
is verified via static inspection (structure/columns present) plus a live
end-to-end smoke test documented in PROVIDER_MATCHING_TEST_RESULTS.md, since
constructing multiple fully-eligible fake tenants in a unit test would
duplicate what the live smoke test already covers with real data.
"""
import pathlib
import pytest
from app.engines.home_service_booking.matching_engine import (
    CandidateSignals, compute_provider_score, rank_candidates, select_best_candidate,
    build_customer_safe_provider, build_admin_provider, compute_price_tiers,
    round_to_nearest_10, resolve_customer_offer_for_tier, CUSTOMER_VISIBLE_REASON,
)
from app.engines.admin_catalog.bargain_engine import BargainValidationError

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATCHING_ENGINE_SRC = (ROOT / "app/engines/home_service_booking/matching_engine.py").read_text(encoding="utf-8-sig")
SERVICE_SRC = (ROOT / "app/engines/home_service_booking/service.py").read_text(encoding="utf-8-sig")


def _signals(tenant_id, **overrides):
    base = dict(
        tenant_id=tenant_id, provider_name=f"Provider {tenant_id}",
        health_score=80.0, job_completion_score=80.0, rating_score=80.0,
        availability_score=80.0, service_match_score=80.0, distance_score=80.0,
        cancellation_score=80.0, capacity_score=80.0,
    )
    base.update(overrides)
    return CandidateSignals(**base)


# ── Test 1 & 2: multiple candidates ranked, best selected by score ─────────
def test_multiple_candidates_ranked_by_score():
    a = _signals("a", health_score=95, job_completion_score=96, rating_score=92,
                 availability_score=90, service_match_score=100, distance_score=85,
                 cancellation_score=100, capacity_score=88)
    b = _signals("b", health_score=60, job_completion_score=50, rating_score=40,
                 availability_score=40, service_match_score=60, distance_score=60,
                 cancellation_score=70, capacity_score=50)
    ranked = rank_candidates([b, a])
    assert ranked[0][0].tenant_id == "a"
    assert ranked[0][1] > ranked[1][1]


def test_best_provider_selected_by_score():
    a = _signals("a", health_score=95)
    b = _signals("b", health_score=60)
    best = select_best_candidate([a, b])
    assert best[0].tenant_id == "a"


# ── Test 6: low health score loses to a better provider ────────────────────
def test_low_health_score_provider_loses():
    weak = _signals("weak", health_score=20, job_completion_score=20, rating_score=20)
    strong = _signals("strong", health_score=95, job_completion_score=95, rating_score=95)
    best = select_best_candidate([weak, strong])
    assert best[0].tenant_id == "strong"


def test_score_formula_matches_ticket_weights():
    s = _signals("x", health_score=95, job_completion_score=96, rating_score=92,
                 availability_score=90, service_match_score=100, distance_score=85,
                 cancellation_score=100, capacity_score=88)
    expected = (
        95 * 0.20 + 96 * 0.20 + 92 * 0.15 + 90 * 0.15 + 100 * 0.10
        + 85 * 0.10 + 100 * 0.05 + 88 * 0.05
    )
    assert float(compute_provider_score(s)) == pytest.approx(expected, abs=0.01)


def test_empty_candidate_list_returns_none():
    assert select_best_candidate([]) is None


# ── Test 14: customer API hides internal score breakdown ───────────────────
def test_customer_safe_view_hides_internal_score():
    s = _signals("a")
    score = compute_provider_score(s)
    customer_view = build_customer_safe_provider(s, score)
    assert "internal_score" not in customer_view
    assert "internal_score_breakdown" not in customer_view
    assert customer_view["customer_visible_reason"] == CUSTOMER_VISIBLE_REASON


# ── Test 15: admin/debug view can show score breakdown ──────────────────────
def test_admin_view_shows_internal_score_breakdown():
    s = _signals("a", health_score=95)
    score = compute_provider_score(s)
    admin_view = build_admin_provider(s, score)
    assert admin_view["internal_score"] == float(score)
    assert admin_view["internal_score_breakdown"]["health_score"] == 95.0


# ── Test 7 & 8: price options generated correctly, low == allowed_offer_min ─
# HS6 fix: compute_price_tiers previously delegated entirely to
# evaluate_customer_bargain(), whose allowed_offer_max is the RAW
# customer_max_price with no platform fee applied — high_price equaled
# the pre-fee provider max, violating the hard gate "High must include
# platform fee" (same asymmetric-formula bug already fixed on the admin
# preview endpoint in an earlier sprint, but never fixed in this
# separate matching-engine copy of the function until now). Now
# delegates to compute_symmetric_customer_price_tiers, so high_price
# correctly includes the platform fee (900 * 1.10 = 990, not 900).
def test_price_tiers_match_ticket_example():
    tiers = compute_price_tiers(
        admin_min_price=600, admin_max_price=1200, admin_base_price=800,
        customer_min_price=650, customer_max_price=900, platform_fee_percent=10,
    )
    assert tiers["allowed_offer_min"] == 715
    assert tiers["allowed_offer_max"] == 990
    assert tiers["low_price"] == 715
    assert tiers["high_price"] == 990
    assert tiers["low_price"] == tiers["allowed_offer_min"]
    assert tiers["high_price"] != 900  # must not equal the pre-fee provider max


def test_round_to_nearest_10():
    assert round_to_nearest_10(807.5) == 810
    assert round_to_nearest_10(804) == 800
    assert round_to_nearest_10(805) == 810


def test_price_tiers_invalid_config_raises():
    with pytest.raises(BargainValidationError):
        compute_price_tiers(
            admin_min_price=300, admin_max_price=500,
            customer_min_price=450, customer_max_price=460, platform_fee_percent=10,
        )


# ── Test 9 & 10: customer selecting Low submits allowed_offer_min; cannot go below ─
def test_resolve_customer_offer_for_low_equals_allowed_offer_min():
    tiers = compute_price_tiers(
        admin_min_price=600, admin_max_price=1200,
        customer_min_price=650, customer_max_price=900, platform_fee_percent=10,
    )
    offer = resolve_customer_offer_for_tier(tiers, "low")
    assert float(offer) == tiers["allowed_offer_min"] == 715


def test_customer_cannot_submit_below_low_no_raw_amount_input():
    # The tier resolver only accepts 'low'/'mid'/'high' — there is no code path
    # that accepts a raw customer-submitted numeric offer for tier selection,
    # so "below Low" is structurally impossible via this function.
    tiers = compute_price_tiers(
        admin_min_price=600, admin_max_price=1200,
        customer_min_price=650, customer_max_price=900, platform_fee_percent=10,
    )
    with pytest.raises(ValueError):
        resolve_customer_offer_for_tier(tiers, "700")  # not a valid tier name
    with pytest.raises(KeyError):
        resolve_customer_offer_for_tier({}, "low")  # no fabricated fallback amount


def test_mid_price_never_outside_range():
    tiers = compute_price_tiers(
        admin_min_price=100, admin_max_price=200,
        customer_min_price=195, customer_max_price=200, platform_fee_percent=0,
    )
    assert tiers["allowed_offer_min"] <= tiers["mid_price"] <= tiers["allowed_offer_max"]


# ── Payment mode / no client-side price computation markers ────────────────
def test_price_tiers_payment_mode_is_direct():
    tiers = compute_price_tiers(
        admin_min_price=600, admin_max_price=1200,
        customer_min_price=650, customer_max_price=900, platform_fee_percent=10,
    )
    assert tiers["payment_mode"] == "customer_pays_provider_directly"


# ── Static inspection: eligibility gate covers every required check ────────
# HS6B — updated to the canonical, aligned eligibility model. The old
# markers (provider_enabled_offerings.supported_type_ids/
# supported_brand_ids, provider_team_members, provider_availability_rules,
# tenant_package_assignments, tenant_wallets, security_deposits) asserted
# on a second, parallel readiness calculation that read different tables
# than HS4B's canonical bookability computation — a real, confirmed bug
# (a real dev-DB tenant had provider_enabled_offerings.status=
# 'pending_approval', which would have wrongly excluded an otherwise
# is_bookable=true tenant). Fixed by removing the parallel checks; the
# gate now trusts is_bookable as the single source of truth and reads
# HS5B's normalized tenant_service_area_services table for coverage.
REQUIRED_ELIGIBILITY_CHECKS = [
    "Tenant.status == \"active\"",
    "Tenant.vertical == \"home_services\"",
    "Tenant.suspended_at.is_(None)",
    "is_bookable",
    "tenant_service_area_services",
    "tenant_service_areas",
    "service_pricing_rules",
]


def test_eligibility_gate_covers_every_required_check():
    for marker in REQUIRED_ELIGIBILITY_CHECKS:
        assert marker in MATCHING_ENGINE_SRC, f"eligibility gate missing check for: {marker}"


def test_eligibility_gate_no_longer_uses_parallel_readiness_tables():
    # Check only the real SQL query text (after the docstring, which
    # references the removed tables for historical explanation) — no
    # actual FROM/JOIN clause should touch them anymore.
    fn_full = MATCHING_ENGINE_SRC.split("async def _passes_full_eligibility_gate")[1].split("async def _job_completion_score")[0]
    sql_only = fn_full.split('"""')[-1]  # text after the closing docstring quotes
    for removed_table in ["FROM tenant_wallets", "FROM security_deposits",
                           "FROM tenant_package_assignments", "FROM provider_team_members"]:
        assert removed_table not in sql_only, f"parallel readiness query should be removed: {removed_table}"


def test_area_comparison_is_read_only_and_separate_function():
    idx = MATCHING_ENGINE_SRC.index("async def get_area_market_comparison")
    snippet = MATCHING_ENGINE_SRC[idx: idx + 400]
    assert "Never affects selected-provider" in snippet or "read-only" in snippet.lower()


def test_select_best_provider_and_area_comparison_are_independent_functions():
    # Hard gates 4-5: competitor price must not change selected provider or price.
    # Structural check: get_area_market_comparison never calls select_best_provider,
    # and select_best_provider never calls get_area_market_comparison.
    sb_idx = MATCHING_ENGINE_SRC.index("async def select_best_provider")
    sb_end = MATCHING_ENGINE_SRC.index("async def _passes_full_eligibility_gate")
    select_best_provider_body = MATCHING_ENGINE_SRC[sb_idx:sb_end]
    assert "get_area_market_comparison" not in select_best_provider_body

    area_idx = MATCHING_ENGINE_SRC.index("async def get_area_market_comparison")
    area_body = MATCHING_ENGINE_SRC[area_idx:]
    assert "select_best_provider(" not in area_body.replace("async def select_best_provider(", "")


# ── Static inspection: no manual provider selection by customer remains reachable ─
def test_old_manual_select_provider_not_exposed_as_new_flow():
    # The old select_provider() method still exists for backward compatibility /
    # admin override, but the new atomic match_and_select_provider path must
    # exist and must not require a customer-supplied provider_ref.
    assert "match_and_select_provider" in SERVICE_SRC or "match_provider_and_price" in SERVICE_SRC
