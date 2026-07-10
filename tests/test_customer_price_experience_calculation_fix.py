"""Customer Price Experience Calculation Fix certification.

The admin "Customer Price Experience" preview tool
(POST /v1/admin/home-services/price-experience/preview) was calling
matching_engine.compute_price_tiers, which only applies the platform fee
to the LOW end (bargain-floor semantics from the Provider-First Matching
flow, where "customer_min/max" is the tenant's own negotiation range, not
an admin-set boundary). For this admin testing tool, that produced the
exact bug described in the ticket: High showed ₹420 (the pre-fee selected
max) instead of ₹462 (420 + 10% fee).

Fix: this endpoint now calls bargain_engine.compute_symmetric_customer_price_tiers
(fee applied to BOTH ends), the same pure function already used by the
Admin Home Services Catalog Console and Tenant Setup Wizard, with a new
rounding_increment=5 parameter (nearest-5 for this tool, vs. the existing
callers' nearest-10 default — verified not to regress their already-
certified outputs).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROUTER = (ROOT / "app/engines/admin_catalog/auto_price_options_router.py").read_text(encoding="utf-8-sig")
BARGAIN_ENGINE = (ROOT / "app/engines/admin_catalog/bargain_engine.py").read_text(encoding="utf-8-sig")
PAGE = (ROOT / "frontend/super-admin/app/admin/home-services/price-experience/page.tsx").read_text(encoding="utf-8-sig")
API_TS = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8-sig")

import sys
sys.path.insert(0, str(ROOT))
from app.engines.admin_catalog.bargain_engine import (
    compute_symmetric_customer_price_tiers, BargainValidationError,
)


# ── 1. Calculation bug — formula-level, direct function calls ────────────────

def test_case1_ticket_example():
    r = compute_symmetric_customer_price_tiers(350, 420, 10, rounding_increment=5)
    assert r["low_price"] == 385.0
    assert r["mid_price"] == 425.0
    assert r["high_price"] == 462.0


def test_case2():
    r = compute_symmetric_customer_price_tiers(350, 450, 10, rounding_increment=5)
    assert r["low_price"] == 385.0
    assert r["high_price"] == 495.0
    assert r["mid_price"] == 440.0


def test_case3_full_admin_range():
    r = compute_symmetric_customer_price_tiers(300, 500, 10, rounding_increment=5)
    assert r["low_price"] == 330.0
    assert r["high_price"] == 550.0


def test_case6_min_greater_than_max_rejected():
    try:
        compute_symmetric_customer_price_tiers(420, 350, 10, rounding_increment=5)
        assert False, "expected BargainValidationError"
    except BargainValidationError as e:
        assert e.code == "INVALID_PRICE_RANGE"


def test_high_never_equals_pre_fee_selected_max():
    r = compute_symmetric_customer_price_tiers(350, 420, 10, rounding_increment=5)
    assert r["high_price"] != 420.0


def test_low_never_equals_raw_selected_min():
    r = compute_symmetric_customer_price_tiers(350, 420, 10, rounding_increment=5)
    assert r["low_price"] != 350.0


# ── 2. Existing certified callers unaffected (default rounding_increment=10) ──

def test_existing_tenant_wizard_example_unchanged():
    r = compute_symmetric_customer_price_tiers(550, 700, 10)
    assert (r["low_price"], r["mid_price"], r["high_price"]) == (605.0, 690.0, 770.0)


def test_existing_admin_catalog_console_example_unchanged():
    r = compute_symmetric_customer_price_tiers(850, 1100, 10)
    assert (r["low_price"], r["mid_price"], r["high_price"]) == (935.0, 1070.0, 1210.0)


# ── 3. Backend router result ──────────────────────────────────────────────────

def test_router_uses_symmetric_formula_not_asymmetric():
    endpoint_src = ROUTER.split("async def admin_price_experience_preview")[1].split("# ── Admin: Matching Diagnostics")[0]
    assert "compute_symmetric_customer_price_tiers" in endpoint_src
    assert "compute_price_tiers(" not in endpoint_src


def test_router_validates_selected_range_against_admin_range():
    endpoint_src = ROUTER.split("async def admin_price_experience_preview")[1].split("# ── Admin: Matching Diagnostics")[0]
    assert "SELECTED_RANGE_BELOW_ADMIN_MIN" in endpoint_src
    assert "SELECTED_RANGE_ABOVE_ADMIN_MAX" in endpoint_src
    assert "INVALID_ADMIN_RANGE" in endpoint_src


def test_router_uses_rounding_increment_5():
    endpoint_src = ROUTER.split("async def admin_price_experience_preview")[1].split("# ── Admin: Matching Diagnostics")[0]
    assert "rounding_increment=5" in endpoint_src


# ── 4. Required response shape ────────────────────────────────────────────────

def test_response_shape_matches_ticket_json():
    endpoint_src = ROUTER.split("async def admin_price_experience_preview")[1].split("# ── Admin: Matching Diagnostics")[0]
    for field in ["selected_min_price", "selected_max_price", "platform_fee_on_min", "platform_fee_on_max",
                  "customer_low_price", "customer_mid_price", "customer_high_price",
                  "allowed_offer_min", "allowed_offer_max", "payment_mode"]:
        assert f'"{field}"' in endpoint_src, f"missing response field: {field}"


def test_backward_compatible_aliases_present():
    endpoint_src = ROUTER.split("async def admin_price_experience_preview")[1].split("# ── Admin: Matching Diagnostics")[0]
    assert '"customer_min_price"' in endpoint_src
    assert '"low_price"' in endpoint_src and '"mid_price"' in endpoint_src and '"high_price"' in endpoint_src


# ── 5. Frontend — naming fix ──────────────────────────────────────────────────

def test_frontend_uses_renamed_labels():
    for label in ["Admin Allowed Min", "Admin Allowed Max", "Selected Range Min", "Selected Range Max",
                  "Platform Fee %"]:
        assert label in PAGE


def test_frontend_no_longer_uses_confusing_customer_min_max_labels():
    assert "Customer Min Price" not in PAGE
    assert "Customer Max Price" not in PAGE


def test_frontend_output_labels():
    assert "Customer Low" in PAGE and "Customer Mid" in PAGE and "Customer High" in PAGE


# ── 6. Breakdown card fix ─────────────────────────────────────────────────────

def test_breakdown_shows_fee_on_both_ends():
    assert "Platform Fee on Minimum" in PAGE
    assert "Platform Fee on Maximum" in PAGE
    assert "Selected Range Minimum" in PAGE
    assert "Selected Range Maximum" in PAGE


def test_breakdown_no_longer_shows_old_wrong_fields():
    assert "Minimum Allowed Customer Offer" not in PAGE
    assert "Maximum Allowed Customer Offer" not in PAGE


def test_frontend_reads_corrected_response_fields():
    assert "result.customer_low_price" in PAGE
    assert "result.customer_mid_price" in PAGE
    assert "result.customer_high_price" in PAGE
    assert "result.platform_fee_on_min" in PAGE
    assert "result.platform_fee_on_max" in PAGE


def test_api_client_sends_selected_range_not_customer_range():
    fn_src = API_TS.split("previewPriceExperience: (data: {")[1].split("=>")[0]
    assert "selected_min_price" in fn_src and "selected_max_price" in fn_src
    assert "customer_min_price" not in fn_src and "customer_max_price" not in fn_src


# ── Forbidden labels / manual bargain wording ─────────────────────────────────

def test_no_manual_bargain_setup_wording():
    assert "Manual Bargain Setup" not in PAGE
    assert "Bargain Rule Builder" not in PAGE
