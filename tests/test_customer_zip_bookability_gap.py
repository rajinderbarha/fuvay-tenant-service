"""Customer discovery must never advertise a non-bookable Home provider."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_all_customer_discovery_surfaces_use_latest_canonical_bookability():
    provider_matching = source("app/engines/home_service_booking/provider_matching.py")
    assistant_catalog = source("app/engines/home_service_booking/offering_catalog_service.py")
    serviceability = source("app/engines/serviceability/service.py")

    assert "latest_provider_bookable(Tenant.id)" in provider_matching
    assert "latest_provider_bookable(TenantService.tenant_id)" in assistant_catalog
    assert serviceability.count("latest_provider_bookable(Tenant.id)") >= 2


def test_zipcode_never_falls_back_to_city_in_legacy_provider_list():
    provider_matching = source("app/engines/home_service_booking/provider_matching.py")
    assert "if not strip_zip and len(results) < limit:" in provider_matching


def test_no_provider_copy_names_the_customer_zipcode():
    booking_service = source("app/engines/home_service_booking/service.py")
    customer_screen = source(
        "mobile/customer-app/src/screens/bookingChat/BookingChatScreen.tsx"
    )

    expected = "No service is currently available in {location}."
    assert booking_service.count(expected) >= 2
    assert "This service is not currently available in ZIP code" in customer_screen
