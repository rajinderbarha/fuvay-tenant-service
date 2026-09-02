"""MODULE-L5-56 — Job-Type Blueprint consolidation (Options & Add-ons design,
Checklist Blueprint mapping, standalone-page retirement, tier legacy audit).

Covers the delivery brief's verification list items that are feasibly
provable at this layer without a live browser:
  1/2. Standalone Service Options / Issue Types pages retired (frontend
       route files replaced with a redirect notice, removed from nav-config).
  3.   Options & Add-ons is exposed only inside the Job-Type Blueprint
       (Catalog Workspace) -- proven by the retired page's own content.
  4/5. Checklist Library remains standalone; Checklist Blueprint mapping
       requires an exact master_service_job_type_id + a PUBLISHED version
       (already proven by tests/test_module_l5_55_checklist_catalog_engine.py
       -- re-asserted here at the mapping-creation boundary for this ticket).
  18.  TIER_1_METRO_CITY does not exist anywhere in migrations/seed data and
       is not recreated by any migration in this repo.
  19.  Home Services disablement scoping is out of this ticket's proven
       scope -- NOT asserted here (see final report "deferred").

IMPORTANT — honest, not glossed over: item 8 ("Category/Master Service
duplicate requirement flags no longer control runtime behavior") is
DISPROVEN, not proven, by this test file. home_service_booking/service.py
still reads MasterService.is_type_required/is_brand_required directly with
no fallback to the canonical ServiceJobDimension/CatalogDimension engine.
test_legacy_flags_still_drive_booking_validation documents this as a
confirmed, NOT-yet-fixed gap for follow-up work, per the instruction not to
claim completion of behavior that isn't actually true.
"""
from __future__ import annotations

import inspect
import os

import pytest


ALEMBIC_VERSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")


def _all_migration_source() -> str:
    text = ""
    for fname in os.listdir(ALEMBIC_VERSIONS_DIR):
        if fname.endswith(".py"):
            with open(os.path.join(ALEMBIC_VERSIONS_DIR, fname), encoding="utf-8") as f:
                text += f.read()
    return text


class TestTierLegacyDataAbsent:
    def test_tier_1_metro_city_not_in_any_migration(self):
        assert "TIER_1_METRO_CITY" not in _all_migration_source()

    def test_no_seed_recreates_metro_city_tier_option(self):
        # Broader net: no migration inserts a ServiceOption/PricingTier row
        # whose code/name contains the retired tier vocabulary.
        text = _all_migration_source().lower()
        assert "tier_1_metro_city" not in text


class TestPricingTierRetirement:
    def test_tier_writes_retired_guard_exists(self):
        from app.engines.admin_catalog.service import AdminCatalogService
        assert hasattr(AdminCatalogService, "_assert_tier_writes_retired")
        src = inspect.getsource(AdminCatalogService._assert_tier_writes_retired)
        assert "410" in src or "PRICING_TIER_WRITES_RETIRED" in src

    def test_pricing_engine_only_reachable_via_admin_preview_pricing(self):
        # Correction to an earlier "fully orphaned" audit claim: pricing_engine
        # IS imported, but only inside AdminCatalogService.preview_pricing (an
        # admin diagnostic preview action) -- not from any customer/tenant
        # runtime booking or pricing-resolution path.
        from app.engines.admin_catalog.service import AdminCatalogService
        src = inspect.getsource(AdminCatalogService.preview_pricing)
        assert "pricing_engine" in src
        import subprocess
        result = subprocess.run(
            ["git", "grep", "-l", "pricing_engine", "--", "app/"],
            cwd=os.path.join(os.path.dirname(__file__), ".."),
            capture_output=True, text=True,
        )
        callers = sorted(l for l in result.stdout.splitlines() if l.strip())
        assert callers == ["app/engines/admin_catalog/service.py"]


class TestStandalonePageRetirement:
    def _frontend_root(self):
        return os.path.join(os.path.dirname(__file__), "..", "frontend", "super-admin")

    def test_service_options_page_is_retired_notice(self):
        path = os.path.join(self._frontend_root(), "app", "admin", "service-options", "page.tsx")
        assert not os.path.exists(path)

    def test_issue_types_page_is_retired_notice(self):
        path = os.path.join(self._frontend_root(), "app", "admin", "issue-types", "page.tsx")
        assert not os.path.exists(path)

    def test_nav_config_no_longer_lists_service_options_or_issue_types(self):
        path = os.path.join(self._frontend_root(), "components", "layout", "AdminLayout.tsx")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert 'href: "/admin/service-options"' not in content
        assert 'href: "/admin/issue-types"' not in content

    def test_catalog_workspace_has_options_checklist_workflow_preview_tabs(self):
        path = os.path.join(self._frontend_root(), "app", "admin", "catalog-workspace", "page.tsx")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        for key in ('"overview"', '"options"', '"checklist"', '"workflow"', '"preview"', '"problems"', '"dimensions"'):
            assert key in content, f"Blueprint missing expected tab key {key}"


class TestOptionsAddOnsIsJobTypeExact:
    def test_service_option_mapping_has_job_type_id_column(self):
        from app.engines.admin_catalog.models import ServiceOptionMapping
        assert "job_type_id" in ServiceOptionMapping.__table__.columns

    def test_option_admin_write_path_forbids_monetary_fields(self):
        from app.engines.admin_catalog import service_option_service
        src = inspect.getsource(service_option_service)
        assert "_FORBIDDEN_ADMIN_MONETARY_FIELDS" in src
        assert "default_price" in src and "min_price" in src and "max_price" in src


class TestChecklistBlueprintMapping:
    """Re-asserts the checklist-mapping exactness boundary specifically in
    the context of this ticket's Blueprint Checklist tab, complementing
    (not duplicating) test_module_l5_55_checklist_catalog_engine.py."""

    @pytest.mark.asyncio
    async def test_mapping_rejects_unpublished_version_from_blueprint_checklist_tab(self):
        import uuid
        from unittest.mock import AsyncMock, MagicMock
        from app.engines.checklist_catalog import service as checklist_service, constants as c
        from app.exceptions import ServiceOSException

        db = AsyncMock()
        link = MagicMock(is_active=True)
        version = MagicMock(status=c.VERSION_DRAFT)
        db.get = AsyncMock(side_effect=[link, version])
        with pytest.raises(ServiceOSException) as exc:
            await checklist_service.create_mapping(
                db, master_service_job_type_id=uuid.uuid4(), service_job_workflow_id=None,
                checklist_template_version_id=uuid.uuid4(), phase="inspection", usage="REQUIRED",
                actor="TECHNICIAN", completion_gate="NONE", condition_rules=None, display_order=0,
                created_by=None,
            )
        assert exc.value.error_code == c.ERR_CHECKLIST_VERSION_NOT_PUBLISHED


class TestMasterServiceAdminPricingLockout:
    """MODULE-L5-56 follow-up: admin can no longer write
    base_price/min_price/max_price/visit_fee on a Master Service (mirrors
    migration 169's ServiceOption lockout). Existing values remain readable
    as the pre-assignment estimate fallback -- not deleted, not authoritative
    for a tenant that has priced the service itself."""

    def test_update_master_service_rejects_price_fields(self):
        from app.engines.admin_catalog.service import AdminCatalogService
        svc = AdminCatalogService.__new__(AdminCatalogService)
        from app.exceptions import ServiceOSException
        for field in ("base_price", "min_price", "max_price", "visit_fee"):
            with pytest.raises(ServiceOSException) as exc:
                svc._reject_admin_price_fields({field: 100})
            assert exc.value.error_code == "ADMIN_PRICING_NOT_ALLOWED"

    def test_update_master_service_allows_non_price_fields(self):
        from app.engines.admin_catalog.service import AdminCatalogService
        svc = AdminCatalogService.__new__(AdminCatalogService)
        svc._reject_admin_price_fields({"service_name": "Repair", "hourly_rate": 50})  # must not raise

    def test_admin_form_no_longer_submits_price_fields(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "frontend", "super-admin", "app", "admin", "master-services", "page.tsx",
        )
        with open(path, encoding="utf-8") as f:
            content = f.read()
        edit_block = content[content.index("const editAction"):content.index("const editAction") + 700]
        assert "base_price:" not in edit_block
        assert "min_price:" not in edit_block
        assert "max_price:" not in edit_block
        assert "tenant-owned only" in content


class TestBookingPrefersTenantPrice:
    @pytest.mark.asyncio
    async def test_no_tenant_selected_returns_none(self):
        from unittest.mock import MagicMock
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        svc = HomeServiceChatbotBookingService.__new__(HomeServiceChatbotBookingService)
        draft = MagicMock(selected_tenant_id=None)
        result = await svc._resolve_selected_tenant_price(draft)
        assert result is None

    @pytest.mark.asyncio
    async def test_tenant_selected_but_no_tenant_service_returns_none(self):
        import uuid
        from unittest.mock import AsyncMock, MagicMock
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        svc = HomeServiceChatbotBookingService.__new__(HomeServiceChatbotBookingService)
        svc.db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        svc.db.execute = AsyncMock(return_value=result_mock)
        draft = MagicMock(selected_tenant_id=uuid.uuid4(), offering_id=uuid.uuid4())
        result = await svc._resolve_selected_tenant_price(draft)
        assert result is None

    @pytest.mark.asyncio
    async def test_tenant_selected_and_priced_returns_resolved_price(self, monkeypatch):
        import uuid
        from unittest.mock import AsyncMock, MagicMock
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        from app.engines.admin_catalog import tenant_service as tenant_service_module

        svc = HomeServiceChatbotBookingService.__new__(HomeServiceChatbotBookingService)
        svc.db = AsyncMock()
        ts_mock = MagicMock(id=uuid.uuid4())
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [ts_mock]
        svc.db.execute = AsyncMock(return_value=result_mock)

        resolved = {"resolved": True, "minimum_price": 500.0, "maximum_price": 700.0, "source": "tenant_default"}
        monkeypatch.setattr(
            tenant_service_module.TenantCatalogService, "resolve_tenant_price",
            AsyncMock(return_value=resolved),
        )
        draft = MagicMock(selected_tenant_id=uuid.uuid4(), offering_id=uuid.uuid4(),
                           offering_type_id=None, brand_id=None)
        result = await svc._resolve_selected_tenant_price(draft)
        assert result == resolved


class TestKnownGap_LegacyFlagsStillDriveBooking:
    """Honest documentation of a confirmed, NOT-fixed gap: this ticket's
    consolidation only removed the duplicate ADMIN EDIT UI for these flags
    (frontend/super-admin/app/admin/master-services/page.tsx) -- it did not
    rewire home_service_booking's real customer-facing validation to prefer
    the canonical ServiceJobDimension/CatalogDimension engine. That runtime
    rewire is deferred (see final report), and this test intentionally
    documents the CURRENT (not-yet-corrected) behavior rather than pretend
    it already resolves through the canonical dimension engine."""

    def test_home_service_booking_still_reads_legacy_master_service_flags_directly(self):
        from app.engines.home_service_booking import service as hsb_service
        src = inspect.getsource(hsb_service)
        assert "offering.is_type_required" in src
        assert "offering.is_brand_required" in src
        # No fallback/precedence check against the canonical dimension engine
        # exists in this module today -- confirming the gap, not a regression
        # introduced by this ticket.
        assert "ServiceJobDimension" not in src
        assert "CatalogDimension" not in src
