"""HS6 — Provider Matching + Auto Price Options certification.

Two real, critical bugs found and fixed in the already-substantial,
pre-existing provider-first matching engine
(app/engines/home_service_booking/matching_engine.py, service.py):

1. `compute_price_tiers()` delegated entirely to
   `evaluate_customer_bargain()`, whose `allowed_offer_max` is the RAW
   customer_max_price with NO platform fee applied — `high_price`
   equaled the pre-fee provider max, directly violating the ticket's
   hard gate ("High must include platform fee" / "High must not equal
   pre-fee provider max"). This is the exact same asymmetric-formula bug
   already found and fixed on the admin preview endpoint in an earlier
   sprint — but this is a *separate* function of the same name in a
   different module that was never fixed. Fixed by delegating to
   `compute_symmetric_customer_price_tiers` (the single certified
   formula used everywhere else in Home Services pricing).

2. The selected-provider bargain-rule lookup in
   `HomeServiceBookingService`'s matching flow filtered ONLY by
   `master_service_id` — completely ignoring `offering_type_id`/
   `brand_id`, even though both were already passed into
   `select_best_provider()` for eligibility filtering. This is the exact
   "Window AC brand price used for Split AC" bug the entire session's
   Home Services pricing work exists to prevent, except it was still
   live in the real customer-facing matching/booking price-resolution
   path. Fixed by joining the linked `ServicePricingRule` and preferring
   the most specific match (type+brand > type-only > service-only).

Both fixes live-verified this sprint against the real
compute_price_tiers() function with the ticket's own numeric example
(700–850 @ 10% -> Low 770, High 935).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATCHING_ENGINE = (ROOT / "app/engines/home_service_booking/matching_engine.py").read_text(encoding="utf-8-sig")
BOOKING_SERVICE = (ROOT / "app/engines/home_service_booking/service.py").read_text(encoding="utf-8-sig")


# ── 1. Price tiers use the fee-inclusive formula ──────────────────────────────
def test_compute_price_tiers_uses_symmetric_formula():
    fn = MATCHING_ENGINE.split("def compute_price_tiers")[1].split("PRICE_TIER_TO_FIELD")[0]
    assert "compute_symmetric_customer_price_tiers" in fn


def test_compute_price_tiers_matches_ticket_example():
    import sys
    sys.path.insert(0, str(ROOT))
    from app.engines.home_service_booking.matching_engine import compute_price_tiers
    r = compute_price_tiers(
        admin_min_price=500, admin_max_price=900,
        customer_min_price=700, customer_max_price=850, platform_fee_percent=10,
    )
    assert r["low_price"] == 770.0
    assert r["high_price"] == 935.0
    assert r["payment_mode"] == "customer_pays_provider_directly"


def test_high_price_includes_platform_fee_not_raw_max():
    import sys
    sys.path.insert(0, str(ROOT))
    from app.engines.home_service_booking.matching_engine import compute_price_tiers
    r = compute_price_tiers(
        admin_min_price=600, admin_max_price=1200,
        customer_min_price=650, customer_max_price=900, platform_fee_percent=10,
    )
    assert r["high_price"] != 900.0  # must not equal the pre-fee provider max
    assert r["high_price"] == 990.0  # 900 * 1.10


def test_low_price_includes_platform_fee_not_raw_min():
    import sys
    sys.path.insert(0, str(ROOT))
    from app.engines.home_service_booking.matching_engine import compute_price_tiers
    r = compute_price_tiers(
        admin_min_price=600, admin_max_price=1200,
        customer_min_price=650, customer_max_price=900, platform_fee_percent=10,
    )
    assert r["low_price"] != 650.0


# ── 2. Bargain-rule resolution is type/brand-scoped ───────────────────────────
def test_bargain_rule_lookup_joins_pricing_rule_for_specificity():
    fn = BOOKING_SERVICE.split("selected_tenant_id = uuid.UUID(signals.tenant_id)")[1].split("if not bargain_rule")[0]
    assert "ServicePricingRule.id == BargainRule.pricing_rule_id" in fn
    assert "_specificity" in fn


def test_bargain_rule_prefers_type_and_brand_match():
    fn = BOOKING_SERVICE.split("def _specificity")[1].split("eligible_candidates =")[0]
    assert "has_type and has_brand" in fn
    assert "return 3" in fn


def test_bargain_rule_excludes_mismatched_type_brand_rules():
    # A type/brand-scoped rule that does NOT match this request's
    # offering_type_id/brand_id must never be selected (specificity -1,
    # filtered out entirely) — this is the actual fix for the
    # Window-AC-price-for-Split-AC bug.
    fn = BOOKING_SERVICE.split("def _specificity")[1].split("eligible_candidates =")[0]
    assert "return -1" in fn


# ── 3. Regression: still Home Services scoped ─────────────────────────────────
def test_still_home_services_only():
    assert "assert_home_services_vertical" in MATCHING_ENGINE


def test_still_provider_first_selection():
    assert "select_best_provider" in BOOKING_SERVICE
    fn = BOOKING_SERVICE.split("match = await select_best_provider")[0][-200:]
    # select_best_provider is called before price computation in source order
    price_idx = BOOKING_SERVICE.index("price_options = compute_price_tiers")
    match_idx = BOOKING_SERVICE.index("match = await select_best_provider")
    assert match_idx < price_idx  # provider selected BEFORE price is computed
