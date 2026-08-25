"""Customer-native complaint, refund and warranty reachability contract.

The retired customer web application was intentionally removed. Keep this
certification pointed at the supported React Native application so a future
change cannot accidentally pass by recreating obsolete web routes.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "mobile" / "customer-app" / "src"
LIST = APP / "screens" / "support" / "SupportRequestsScreen.tsx"
DETAIL = APP / "screens" / "support" / "SupportRequestDetailsScreen.tsx"
CREATE = APP / "screens" / "support" / "CreateSupportRequestReviewScreen.tsx"
REMEDIES = APP / "screens" / "service-remedies" / "ServiceRemediesScreen.tsx"
API = APP / "api" / "supportRequests" / "supportRequestsApi.ts"
REMEDIES_API = APP / "api" / "customerRemedies" / "customerRemediesApi.ts"
BOOKING = APP / "screens" / "booking-details" / "BookingDetailsScreen.tsx"


def test_customer_native_complaint_pages_exist():
    for path in (LIST, DETAIL, CREATE, REMEDIES, API, REMEDIES_API):
        assert path.is_file(), str(path)


def test_customer_native_can_reach_complaints_refunds_and_warranty():
    booking = BOOKING.read_text(encoding="utf-8")
    remedies = REMEDIES.read_text(encoding="utf-8")
    remedies_api = REMEDIES_API.read_text(encoding="utf-8")
    assert 'navigate("CreateSupportRequest"' in booking
    assert 'navigate("ServiceRemedies"' in booking
    for action in (
        "submitWarrantyClaim", "submitRefundRequest",
        "escalateWarrantyClaim", "escalateRefundRequest",
    ):
        assert action in remedies, action
    assert "/v1/commerce/warranty/claims" in remedies_api
    assert "/v1/customer/complaints/records/refunds/from-job" in remedies_api


def test_customer_resolutions_endpoint_exists():
    router = (ROOT / "app" / "engines" / "complaints" / "customer_router.py").read_text(encoding="utf-8")
    assert '@customer_complaint_router.get("/{complaint_id}/resolutions")' in router
    assert "list_resolutions" in router


def test_native_booking_links_to_raise_a_complaint():
    """A complaint surface nobody can reach is still no surface."""
    source = BOOKING.read_text(encoding="utf-8")
    assert '"CreateSupportRequest"' in source
    assert "bookingId" in source
