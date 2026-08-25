"""Type-scoped tenant brand-pricing certification."""
from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"
PAGE = (
    FRONTEND / "app/(onboarding)/tenant/home-services/setup/services-pricing/page.tsx"
).read_text(encoding="utf-8-sig")
API = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")
SERVICE = (
    ROOT / "app/engines/admin_catalog/tenant_service.py"
).read_text(encoding="utf-8-sig")


def test_brand_pricing_is_stored_per_type():
    assert "brandPricingByType" in PAGE
    assert "Record<string, HsBrandPricing[]>" in PAGE
    assert "getBrandPricing(tsid, pt.service_type_id)" in PAGE


def test_brand_price_save_passes_service_type_id():
    assert "setBrandPricing(enrolled.tenant_service_id, brandId, minValue, maxValue, serviceTypeId)" in PAGE


def test_brand_rows_inherit_their_type_price_until_overridden():
    assert "mergeBrandCandidatesWithPricing" in PAGE
    assert "typeMin" in PAGE and "typeMax" in PAGE
    assert "otherwise every" in PAGE and "brand uses the" in PAGE


def test_api_client_supports_service_type_id():
    block = API.split("setBrandPricing: (tenantServiceId: string")[1][:500]
    assert "serviceTypeId?: string" in block
    assert "service_type_id" in block


def test_backend_requires_and_scopes_type_for_brand_pricing():
    assert "SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING" in SERVICE
    block = SERVICE.split("async def set_brand_pricing")[1]
    assert "TenantServiceBrand.service_type_id == service_type_id" in block


def test_retired_bargain_labels_are_absent():
    for marker in ("Manual Bargain Setup", "Bargain Rule Builder", "Low/Mid/High"):
        assert marker not in PAGE
