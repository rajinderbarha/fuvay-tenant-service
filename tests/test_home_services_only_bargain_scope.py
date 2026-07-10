"""Home Services Only — Provider-First Matching + Bargain Scope Guard.

The provider-first matching + Low/Mid/High bargain flow (and the
"customer pays provider directly" / Completed Job Deduction model it implies)
must apply ONLY to the Home Services vertical. Other verticals (CA/professional
services, IELTS/coaching, restaurants, real estate, education, listing/menu/
subscription-based businesses) must be hard-rejected, not silently allowed.
"""
import pathlib
import pytest
from app.engines.home_service_booking.matching_engine import (
    assert_home_services_vertical, VerticalFlowNotSupported, HOME_SERVICES_VERTICAL,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVICE_SRC = (ROOT / "app/engines/home_service_booking/service.py").read_text(encoding="utf-8-sig")
CUSTOMER_ROUTER_SRC = (ROOT / "app/engines/home_service_booking/customer_router.py").read_text(encoding="utf-8-sig")

NON_HOME_SERVICES_VERTICALS = [
    "professional_services",  # CA Services
    "coaching",                # IELTS Centers
    "restaurant",
    "real_estate",
    "education",
]


# ── Test 1-4: Home Services can use the flow ────────────────────────────────
def test_home_services_vertical_passes_guard():
    assert_home_services_vertical("home_services")  # must not raise


def test_home_services_constant_value():
    assert HOME_SERVICES_VERTICAL == "home_services"


# ── Test 5-8: non-Home-Services verticals are rejected ──────────────────────
@pytest.mark.parametrize("vertical", NON_HOME_SERVICES_VERTICALS)
def test_non_home_services_vertical_rejected(vertical):
    with pytest.raises(VerticalFlowNotSupported) as exc:
        assert_home_services_vertical(vertical)
    assert exc.value.error_code == "VERTICAL_FLOW_NOT_SUPPORTED"
    assert exc.value.status_code == 422
    assert exc.value.context["supported"] is False
    assert "Home Services" in exc.value.detail


def test_none_vertical_rejected():
    with pytest.raises(VerticalFlowNotSupported):
        assert_home_services_vertical(None)


def test_ca_services_cannot_use_home_services_bargain_endpoint():
    with pytest.raises(VerticalFlowNotSupported):
        assert_home_services_vertical("professional_services")


def test_ielts_cannot_use_home_services_bargain_endpoint():
    with pytest.raises(VerticalFlowNotSupported):
        assert_home_services_vertical("coaching")


def test_restaurant_cannot_use_home_services_bargain_endpoint():
    with pytest.raises(VerticalFlowNotSupported):
        assert_home_services_vertical("restaurant")


def test_real_estate_cannot_use_home_services_bargain_endpoint():
    with pytest.raises(VerticalFlowNotSupported):
        assert_home_services_vertical("real_estate")


# ── Guard is actually wired into the service entry point ───────────────────
def test_match_provider_and_price_calls_the_guard():
    idx = SERVICE_SRC.index("async def match_provider_and_price")
    end = SERVICE_SRC.index("async def confirm_price_choice")
    body = SERVICE_SRC[idx:end]
    assert "assert_home_services_vertical" in body
    assert "category.vertical_type" in body


# ── Route naming: Home Services scope is baked into the URL prefix ─────────
def test_routes_use_home_services_scoped_prefix():
    assert '"/v1/customer/home-services/booking-drafts"' in CUSTOMER_ROUTER_SRC
    assert "match-and-price" in CUSTOMER_ROUTER_SRC
    assert "confirm-price-choice" in CUSTOMER_ROUTER_SRC


# ── Response shape when unsupported (per ticket's alternate JSON contract) ──
def test_unsupported_vertical_error_context_matches_ticket_shape():
    try:
        assert_home_services_vertical("restaurant")
        assert False, "should have raised"
    except VerticalFlowNotSupported as e:
        assert e.context == {
            "supported": False,
            "vertical": "restaurant",
            "reason": "Provider-first bargain flow is only available for Home Services.",
        }
