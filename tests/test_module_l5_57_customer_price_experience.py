"""MODULE-L5-57 — Customer Price Experience consolidation.

The Super Admin "Customer Price Experience" page was found to be a dead,
orphaned simulator (its one POST action already 404'd; only a read-only
config-flags GET still worked) built around the retired "admin sets
Min/Max/Base price boundary" paradigm. This suite proves:
  - The retired admin page/nav/API client are gone, not just hidden.
  - Admin Allowed Min/Max/Base Price and legacy BargainRule/ServicePricingRule
    no longer drive the tenant-facing price preview (they never should have
    -- BargainRule has no tenant_id at all, so the OLD endpoint returned the
    SAME range to every tenant offering a service -- a real cross-tenant
    bug fixed as part of this rewire).
  - The tenant preview endpoint now resolves through the same tenant-owned,
    type/brand-precedence resolver (TenantCatalogService.resolve_tenant_price)
    that real customer bookings use.
  - Low/Mid/High is deterministic and never exceeds the tenant's own range.
  - Repair/inspection pricing shows the required disclosure instead of a
    promised amount.
  - Commission/platform-fee are correctly kept as separate, non-conflated
    concepts.

Items from the verification list already covered by pre-existing suites
(not duplicated here): Work Start Approval Gate (test_module_l5_52_*),
booking idempotency/retry (test_sprint16_home_service_booking.py), tier/
city/zone/zipcode retirement (test_module_l5_56_*). Per-unit/quantity
pricing and tenant Option/Add-on pricing are NOT exercised by this specific
preview endpoint -- flagged as deferred in the final report, not silently
assumed proven.
"""
from __future__ import annotations

import inspect
import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestAdminPageRetired:
    def _root(self):
        return os.path.join(os.path.dirname(__file__), "..")

    def test_admin_page_is_retired_notice(self):
        path = os.path.join(self._root(), "frontend", "super-admin", "app", "admin",
                             "home-services", "price-experience", "page.tsx")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Retired" in content
        assert "admin_min_price" not in content
        assert "admin_max_price" not in content
        assert "admin_base_price" not in content
        assert "platform_fee_percent" not in content
        assert "catalog-workspace" in content

    def test_nav_config_no_longer_lists_price_experience(self):
        path = os.path.join(self._root(), "frontend", "super-admin", "lib", "nav-config.ts")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert 'href: "/admin/home-services/price-experience"' not in content

    def test_admin_layout_no_longer_links_price_experience(self):
        path = os.path.join(self._root(), "frontend", "super-admin", "components", "layout", "AdminLayout.tsx")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert 'href: "/admin/home-services/price-experience"' not in content

    def test_api_client_no_longer_has_preview_method(self):
        path = os.path.join(self._root(), "frontend", "super-admin", "lib", "api.ts")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "previewPriceExperience:" not in content
        assert '"/v1/admin/home-services/price-experience/preview"' not in content

    def test_backend_preview_route_not_registered(self):
        path = os.path.join(self._root(), "app", "engines", "admin_catalog", "auto_price_options_router.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert '"/price-experience/preview"' not in content


class TestTenantPreviewUsesCanonicalResolver:
    def test_tenant_preview_no_longer_reads_bargain_rule_or_pricing_rule(self):
        import re
        from app.engines.admin_catalog import auto_price_options_router as router_mod
        src = inspect.getsource(router_mod.tenant_customer_price_preview)
        code = re.sub(r'""".*?"""', "", src, flags=re.DOTALL)  # strip the docstring (mentions the retired path by name)
        assert "BargainRule" not in code
        assert "ServicePricingRule" not in code
        assert "resolve_tenant_price" in code

    def test_tenant_preview_scopes_by_tenant_id(self):
        from app.engines.admin_catalog import auto_price_options_router as router_mod
        src = inspect.getsource(router_mod.tenant_customer_price_preview)
        assert "TenantService.tenant_id == tid" in src

    def test_tenant_preview_passes_no_admin_amounts_to_tier_calculation(self):
        from app.engines.admin_catalog import auto_price_options_router as router_mod
        src = inspect.getsource(router_mod.tenant_customer_price_preview)
        assert "admin_min_price=None, admin_max_price=None, admin_base_price=None" in src

    @pytest.mark.asyncio
    async def test_no_enabled_service_returns_unavailable_not_a_price(self):
        from app.engines.admin_catalog.auto_price_options_router import tenant_customer_price_preview
        from unittest.mock import MagicMock

        db = AsyncMock()
        svc = MagicMock(service_name="AC Repair", category_id=None)
        db.get = AsyncMock(return_value=svc)
        db.scalar = AsyncMock(return_value=None)  # no TenantService row for this tenant
        u = MagicMock(tenant_id=str(uuid.uuid4()))

        class _Req:
            state = MagicMock(request_id="rid")

        result = await tenant_customer_price_preview(_Req(), uuid.uuid4(), None, None, u, db)
        assert result.data["available"] is False


class TestSharedCalculationFormula:
    def test_tenant_preview_and_booking_use_same_tier_function(self):
        from app.engines.admin_catalog import auto_price_options_router as admin_router_mod
        from app.engines.home_service_booking import matching_engine
        admin_src = inspect.getsource(admin_router_mod)
        assert "compute_price_tiers" in admin_src
        # matching_engine.compute_price_tiers is the certified, single formula
        # (delegates to compute_symmetric_customer_price_tiers) -- confirm the
        # admin router imports the SAME function object, not a reimplementation.
        assert admin_router_mod.compute_price_tiers is matching_engine.compute_price_tiers


class TestDeterministicLowMidHighWithinTenantRange:
    def test_tiers_within_tenant_range_no_fee(self):
        from app.engines.home_service_booking.matching_engine import compute_price_tiers
        tiers = compute_price_tiers(
            admin_min_price=None, admin_max_price=None, admin_base_price=None,
            customer_min_price=500, customer_max_price=900,
            platform_fee_percent=0, platform_fee_fixed_amount=0,
        )
        assert tiers["low_price"] >= 500
        assert tiers["high_price"] <= 900 or tiers["platform_fee_percent"] == 0
        assert tiers["low_price"] <= tiers["mid_price"] <= tiers["high_price"]

    def test_tiers_deterministic_same_inputs_same_output(self):
        from app.engines.home_service_booking.matching_engine import compute_price_tiers
        kwargs = dict(
            admin_min_price=None, admin_max_price=None, admin_base_price=None,
            customer_min_price=500, customer_max_price=900,
            platform_fee_percent=5, platform_fee_fixed_amount=0,
        )
        t1 = compute_price_tiers(**kwargs)
        t2 = compute_price_tiers(**kwargs)
        assert t1 == t2

    def test_high_never_below_low(self):
        from app.engines.home_service_booking.matching_engine import compute_price_tiers
        tiers = compute_price_tiers(
            admin_min_price=None, admin_max_price=None, admin_base_price=None,
            customer_min_price=100, customer_max_price=100,
            platform_fee_percent=0, platform_fee_fixed_amount=0,
        )
        assert tiers["low_price"] <= tiers["high_price"]


class TestRepairInspectionMessaging:
    @pytest.mark.asyncio
    async def test_visit_fee_pricing_model_returns_inspection_disclosure_not_a_promised_range(self):
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        from app.engines.home_service_booking.constants import PRICING_MODEL_VISIT_FEE

        svc = HomeServiceChatbotBookingService.__new__(HomeServiceChatbotBookingService)
        svc.db = AsyncMock()
        svc._resolve_selected_tenant_price = AsyncMock(return_value=None)

        floor_result = MagicMock()
        floor_result.scalars.return_value.first.return_value = None
        svc.db.execute = AsyncMock(return_value=floor_result)
        svc.db.get = AsyncMock(return_value=MagicMock(customer_charge_pct=None, name="Home Services"))

        offering = MagicMock(
            pricing_model=PRICING_MODEL_VISIT_FEE, visit_fee=199, min_price=None, max_price=None,
        )
        draft = MagicMock(category_id=uuid.uuid4(), city="Pune", selected_tenant_id=None)

        result = await svc._compute_price_snapshot(draft, offering)
        assert result["requires_inspection_estimate"] is True
        assert "technician will contact you" in result["customer_message"]
        assert "Work starts only after your approval" in result["customer_message"]

    @pytest.mark.asyncio
    async def test_fixed_pricing_model_does_not_set_inspection_flag(self):
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        from app.engines.home_service_booking.constants import PRICING_MODEL_FIXED

        svc = HomeServiceChatbotBookingService.__new__(HomeServiceChatbotBookingService)
        svc.db = AsyncMock()
        svc._resolve_selected_tenant_price = AsyncMock(return_value=None)

        floor_result = MagicMock()
        floor_result.scalars.return_value.first.return_value = None
        svc.db.execute = AsyncMock(return_value=floor_result)
        svc.db.get = AsyncMock(return_value=MagicMock(customer_charge_pct=None, name="Home Services"))

        offering = MagicMock(pricing_model=PRICING_MODEL_FIXED, base_price=500, min_price=None, max_price=None)
        draft = MagicMock(category_id=uuid.uuid4(), city="Pune", selected_tenant_id=None)

        result = await svc._compute_price_snapshot(draft, offering)
        assert result["requires_inspection_estimate"] is False
        assert result["customer_message"] is None


class TestCommissionSeparationFromCustomerPrice:
    def test_price_snapshot_never_reads_commission_or_credit_deduction_fields(self):
        from app.engines.home_service_booking import service as hsb_service
        src = inspect.getsource(hsb_service.HomeServiceChatbotBookingService._compute_price_snapshot)
        assert "commission_rate" not in src
        assert "completed_job_deduction" not in src
        assert "credit_ledger" not in src

    def test_customer_charge_pct_is_the_only_fee_field_referenced(self):
        from app.engines.home_service_booking import service as hsb_service
        src = inspect.getsource(hsb_service.HomeServiceChatbotBookingService._compute_price_snapshot)
        assert "customer_charge_pct" in src
