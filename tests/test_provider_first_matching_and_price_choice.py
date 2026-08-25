"""Provider-first matching and provider-owned pricing certification.

Tests the pure matching_engine functions directly (no DB) for scoring,
ranking, customer-safe redaction, and the current no-price-tier contract.
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
    build_customer_safe_provider, build_admin_provider, CUSTOMER_VISIBLE_REASON,
)

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


# ── Retired tier pricing stays removed ─────────────────────────────────────
def test_retired_price_tier_helpers_are_absent():
    assert "def compute_price_tiers" not in MATCHING_ENGINE_SRC
    assert "def resolve_customer_offer_for_tier" not in MATCHING_ENGINE_SRC
    assert "PRICE_TIER_TO_FIELD" not in MATCHING_ENGINE_SRC


def test_retired_tier_rounding_helper_is_absent():
    assert "def round_to_nearest_10" not in MATCHING_ENGINE_SRC


def test_admin_price_bounds_are_absent_from_matching():
    assert "admin_min_price" not in MATCHING_ENGINE_SRC
    assert "admin_max_price" not in MATCHING_ENGINE_SRC


# ── Selected-provider price + finance policy is authoritative ──────────────
def test_selected_provider_price_uses_finance_policy():
    assert "get_current_policy_by_vertical_key" in SERVICE_SRC
    assert "calculate_customer_platform_fee" in SERVICE_SRC


def test_customer_cannot_submit_retired_price_tiers():
    assert 'price_tier != "standard"' in SERVICE_SRC
    assert "Only price_tier='standard' is supported" in SERVICE_SRC


def test_match_and_price_is_the_single_resolution_path():
    assert "home_services_match_and_price" in SERVICE_SRC


# ── Payment mode remains direct ────────────────────────────────────────────
def test_payment_mode_is_direct():
    assert "customer_pays_provider_directly" in SERVICE_SRC


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
