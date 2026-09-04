"""Regression contract for provider-owned Repair and consultation pricing."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TENANT_SERVICE = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8")
BOOKING_SERVICE = (ROOT / "app/engines/home_service_booking/service.py").read_text(encoding="utf-8")
SETUP_PAGE = (ROOT / "frontend/tenant-portal/components/services/ServicesPricingSetupPage.tsx").read_text(encoding="utf-8")
AC_CONFIG = (ROOT / "scripts/configure_ac_catalog.py").read_text(encoding="utf-8")


def test_inspection_publish_requires_visit_fee_not_dimension_prices():
    block = TENANT_SERVICE.split("async def validate_for_publish", 1)[1].split(
        "async def get_blueprint_update_status", 1
    )[0]
    assert "is_inspection_pricing" in block
    assert '"code": "MISSING_VISIT_FEE"' in block
    assert "elif is_inspection_pricing" in block


def test_inspection_dimension_price_mutations_fail_closed():
    assert "DIMENSION_PRICING_NOT_APPLICABLE" in TENANT_SERVICE
    assert "await self._reject_dimension_price_for_inspection(ts)" in TENANT_SERVICE


def test_repair_ui_does_not_render_type_brand_price_matrix():
    assert "!isInspectionMode && ((typePricing" in SETUP_PAGE
    assert "Type and Brand control eligibility and matching" in SETUP_PAGE
    assert "Visit fee</span><ArrowRight" in SETUP_PAGE


def test_admin_catalog_marks_repair_dimensions_as_matching_only():
    assert "cfg.affects_price = dimension_affects_price" in AC_CONFIG
    assert "cfg.allow_tenant_override = dimension_affects_price" in AC_CONFIG


def test_consultation_fee_is_provider_wide_and_used_by_booking():
    assert "get_home_services_pricing_policy" in TENANT_SERVICE
    assert '"scope": "provider_all_home_services"' in TENANT_SERVICE
    assert "_resolve_provider_consultation_fee" in BOOKING_SERVICE
    assert "Any later repair is quoted and booked separately." in BOOKING_SERVICE
    assert "Provider-wide consultation fee" in SETUP_PAGE
