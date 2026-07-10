"""Bargain Module — Customer Range + Platform Fee Floor Fix certification.

Tests the pure bargain_engine functions directly (no DB) for exact formula
correctness across the ticket's 8 required cases, plus the response-shape and
naming requirements. Live end-to-end verification of the DB-backed
evaluate_bargain service method (which delegates to this same pure engine)
is documented separately in BARGAIN_MODULE_TEST_RESULTS.md.
"""
import pytest
from app.engines.admin_catalog.bargain_engine import (
    evaluate_customer_bargain, compute_bargain_floor, validate_price_range_config,
    BargainValidationError,
)

ADMIN_MIN, ADMIN_MAX = 300, 500
CUST_MIN, CUST_MAX = 350, 450
FEE_PCT = 10


def _eval(offer):
    return evaluate_customer_bargain(
        service_name="AC Service",
        admin_min_price=ADMIN_MIN, admin_max_price=ADMIN_MAX, admin_base_price=400,
        customer_min_price=CUST_MIN, customer_max_price=CUST_MAX,
        platform_fee_percent=FEE_PCT, customer_offer=offer,
    )


# ── Formula correctness ─────────────────────────────────────────────────────
def test_bargain_floor_formula():
    assert compute_bargain_floor(350, 10) == 385
    assert compute_bargain_floor(350, 10, 0) == 385


def test_bargain_floor_fixed_fee_formula():
    assert compute_bargain_floor(350, 0, 35) == 385


def test_base_price_never_used_as_floor():
    result = _eval(400)
    assert result["bargain_floor"] == 385
    assert result["bargain_floor"] != result["admin_base_price"]


# ── Case 1: offer 350 → rejected (below 385 floor) ─────────────────────────
def test_case1_offer_350_rejected():
    r = _eval(350)
    assert r["decision"] == "rejected"
    assert "below" in r["reason"].lower()
    assert r["bargain_floor"] == 385


# ── Case 2: offer 384 → rejected ────────────────────────────────────────────
def test_case2_offer_384_rejected():
    r = _eval(384)
    assert r["decision"] == "rejected"


# ── Case 3: offer 385 → accepted (boundary, inclusive) ──────────────────────
def test_case3_offer_385_accepted():
    r = _eval(385)
    assert r["decision"] == "accepted"
    assert r["allowed_offer_min"] == 385


# ── Case 4: offer 400 → accepted ────────────────────────────────────────────
def test_case4_offer_400_accepted():
    r = _eval(400)
    assert r["decision"] == "accepted"


# ── Case 5: offer 451 → rejected (above customer max) ───────────────────────
def test_case5_offer_451_rejected_above_max():
    r = _eval(451)
    assert r["decision"] == "rejected"
    assert "above" in r["reason"].lower()


# ── Case 6: customer_min below admin_min → rejected at config time ─────────
def test_case6_customer_min_below_admin_min_rejected():
    with pytest.raises(BargainValidationError) as exc:
        evaluate_customer_bargain(
            service_name="AC Service",
            admin_min_price=300, admin_max_price=500,
            customer_min_price=250, customer_max_price=450,
            platform_fee_percent=10,
        )
    assert exc.value.code == "CUSTOMER_MIN_BELOW_ADMIN_MIN"


# ── Case 7: customer_max above admin_max → rejected at config time ─────────
def test_case7_customer_max_above_admin_max_rejected():
    with pytest.raises(BargainValidationError) as exc:
        evaluate_customer_bargain(
            service_name="AC Service",
            admin_min_price=300, admin_max_price=500,
            customer_min_price=350, customer_max_price=550,
            platform_fee_percent=10,
        )
    assert exc.value.code == "CUSTOMER_MAX_ABOVE_ADMIN_MAX"


# ── Case 8: floor > customer_max → invalid range ────────────────────────────
def test_case8_floor_exceeds_customer_max_invalid():
    with pytest.raises(BargainValidationError) as exc:
        evaluate_customer_bargain(
            service_name="AC Service",
            admin_min_price=300, admin_max_price=500,
            customer_min_price=450, customer_max_price=460,
            platform_fee_percent=10,
        )
    assert exc.value.code == "CUSTOMER_RANGE_TOO_NARROW"
    assert "too narrow" in exc.value.message.lower()


# ── Additional validation rules ─────────────────────────────────────────────
def test_admin_min_must_be_lte_admin_max():
    with pytest.raises(BargainValidationError) as exc:
        validate_price_range_config(500, 300, 350, 450, 10)
    assert exc.value.code == "ADMIN_RANGE_INVALID"


def test_customer_min_must_be_lte_customer_max():
    with pytest.raises(BargainValidationError) as exc:
        validate_price_range_config(300, 500, 450, 350, 10)
    assert exc.value.code == "CUSTOMER_RANGE_INVALID"


def test_negative_platform_fee_rejected():
    with pytest.raises(BargainValidationError) as exc:
        validate_price_range_config(300, 500, 350, 450, -5)
    assert exc.value.code == "PLATFORM_FEE_INVALID"


def test_bargain_floor_within_customer_range_when_valid():
    validate_price_range_config(300, 500, 350, 450, 10)  # should not raise
    floor = compute_bargain_floor(350, 10)
    assert 350 <= floor <= 450


# ── Response shape (exact field names, from ticket) ─────────────────────────
def test_response_shape_matches_required_schema():
    r = _eval(380)
    required_fields = {
        "service_name", "currency", "admin_min_price", "admin_max_price", "admin_base_price",
        "customer_min_price", "customer_max_price", "platform_fee_percent", "platform_fee_amount",
        "bargain_floor", "allowed_offer_min", "allowed_offer_max", "customer_offer",
        "decision", "reason", "payment_mode",
    }
    assert required_fields.issubset(r.keys())


def test_rejected_offer_380_matches_ticket_example():
    r = _eval(380)
    assert r["admin_min_price"] == 300
    assert r["admin_max_price"] == 500
    assert r["customer_min_price"] == 350
    assert r["customer_max_price"] == 450
    assert r["platform_fee_percent"] == 10
    assert r["platform_fee_amount"] == 35
    assert r["bargain_floor"] == 385
    assert r["allowed_offer_min"] == 385
    assert r["allowed_offer_max"] == 450
    assert r["decision"] == "rejected"
    assert r["payment_mode"] == "customer_pays_provider_directly"


def test_accepted_offer_400_matches_ticket_example():
    r = _eval(400)
    assert r["customer_offer"] == 400
    assert r["decision"] == "accepted"
    assert r["allowed_offer_min"] == 385
    assert r["allowed_offer_max"] == 450


def test_provider_approval_required_decision():
    r = evaluate_customer_bargain(
        service_name="AC Service",
        admin_min_price=300, admin_max_price=500,
        customer_min_price=350, customer_max_price=450,
        platform_fee_percent=10, customer_offer=400,
        provider_approval_required=True,
    )
    assert r["decision"] == "provider_approval_required"
