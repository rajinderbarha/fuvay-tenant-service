"""P0 Enterprise City/Zipcode → Tier Mapping Upgrade Tests.

Tests backend service methods, router endpoints, API type definitions,
and frontend page structure for the enterprise location tier mapping module.
"""
import os
import re
import ast
import sys

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "super-admin")
ROUTER_FILE = os.path.join(BACKEND_DIR, "engines", "admin_catalog", "admin_router.py")
SERVICE_FILE = os.path.join(BACKEND_DIR, "engines", "admin_catalog", "service.py")
API_TS = os.path.join(FRONTEND_DIR, "lib", "api.ts")
PAGE_FILE = os.path.join(FRONTEND_DIR, "app", "admin", "location-mapping", "page.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════════════════════
# Group 1: Service file — new methods exist
# ═══════════════════════════════════════════════════════════════

class TestServiceMethods:
    def test_bulk_change_tier_method_exists(self):
        src = _read(SERVICE_FILE)
        assert "bulk_change_tier_locations" in src

    def test_bulk_deactivate_method_exists(self):
        src = _read(SERVICE_FILE)
        assert "bulk_deactivate_tier_locations" in src

    def test_list_import_batches_method_exists(self):
        src = _read(SERVICE_FILE)
        assert "list_import_batches" in src

    def test_resolve_conflict_method_exists(self):
        src = _read(SERVICE_FILE)
        assert "resolve_conflict_location" in src

    def test_sa_update_import(self):
        src = _read(SERVICE_FILE)
        assert "sa_update" in src

    def test_resolve_location_has_district_param(self):
        src = _read(SERVICE_FILE)
        assert "district: str | None = None" in src

    def test_resolve_location_has_zone_param(self):
        src = _read(SERVICE_FILE)
        assert "zone: str | None = None" in src

    def test_resolve_location_checks_district(self):
        src = _read(SERVICE_FILE)
        assert "Checked district" in src

    def test_resolve_location_checks_zone(self):
        src = _read(SERVICE_FILE)
        assert "Checked zone" in src

    def test_loc_dict_includes_mapping_type(self):
        src = _read(SERVICE_FILE)
        assert '"mapping_type"' in src or "'mapping_type'" in src

    def test_loc_dict_includes_source(self):
        src = _read(SERVICE_FILE)
        assert '"source"' in src or "'source'" in src

    def test_loc_dict_includes_created_at(self):
        src = _read(SERVICE_FILE)
        assert '"created_at"' in src or "'created_at'" in src

    def test_loc_dict_includes_updated_at(self):
        src = _read(SERVICE_FILE)
        assert '"updated_at"' in src or "'updated_at'" in src

    def test_bulk_change_validates_new_tier(self):
        src = _read(SERVICE_FILE)
        # Should call _load_tier to validate the tier exists
        # Check that bulk_change_tier_locations calls _load_tier
        idx = src.find("async def bulk_change_tier_locations")
        assert idx != -1
        # PROTECTED_BY_LATER_SLICE: widened from 300 -> 450 chars. The
        # method now opens with self._assert_tier_writes_retired() (a
        # real, intentional 410 guard added by the service-area
        # coverage-approval slice -- see PRICING_TIER_WRITES_RETIRED),
        # which pushes _load_tier further from the def line.
        snippet = src[idx:idx + 450]
        assert "_load_tier" in snippet

    def test_resolve_conflict_has_keep_this(self):
        src = _read(SERVICE_FILE)
        assert '"keep_this"' in src or "'keep_this'" in src

    def test_resolve_conflict_has_override_tier(self):
        src = _read(SERVICE_FILE)
        assert '"override_tier"' in src or "'override_tier'" in src

    def test_resolve_conflict_has_deactivate(self):
        src = _read(SERVICE_FILE)
        idx = src.find("async def resolve_conflict_location")
        assert idx != -1
        snippet = src[idx:idx + 900]
        assert "deactivate" in snippet or "is_active = False" in snippet


# ═══════════════════════════════════════════════════════════════
# Group 2: Router file — new endpoints exist
# ═══════════════════════════════════════════════════════════════

class TestRouterEndpoints:
    def test_bulk_change_tier_route_exists(self):
        src = _read(ROUTER_FILE)
        assert "/tier-locations/bulk/change-tier" in src

    def test_bulk_deactivate_route_exists(self):
        src = _read(ROUTER_FILE)
        assert "/tier-locations/bulk/deactivate" in src

    def test_list_imports_route_exists(self):
        src = _read(ROUTER_FILE)
        assert '"/tier-locations/imports"' in src

    def test_resolve_conflict_route_exists(self):
        src = _read(ROUTER_FILE)
        assert "/resolve-conflict" in src

    def test_list_imports_before_imports_batch_id(self):
        src = _read(ROUTER_FILE)
        idx_list = src.find('"/tier-locations/imports"')
        idx_batch = src.find('"/tier-locations/imports/{batch_id}"')
        assert idx_list != -1 and idx_batch != -1
        assert idx_list < idx_batch, "List imports route must come before batch_id route"

    def test_bulk_routes_before_create_route(self):
        src = _read(ROUTER_FILE)
        idx_bulk = src.find("/tier-locations/bulk/")
        idx_create = src.find('"/tier-locations", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED')
        assert idx_bulk != -1 and idx_create != -1
        assert idx_bulk < idx_create, "Bulk routes must come before parameterized create"

    def test_resolve_location_get_has_state_param(self):
        src = _read(ROUTER_FILE)
        idx = src.find("async def resolve_location_get")
        assert idx != -1
        snippet = src[idx:idx + 400]
        assert "state:" in snippet

    def test_resolve_location_get_has_district_param(self):
        src = _read(ROUTER_FILE)
        idx = src.find("async def resolve_location_get")
        snippet = src[idx:idx + 400]
        assert "district:" in snippet

    def test_resolve_location_get_has_zone_param(self):
        src = _read(ROUTER_FILE)
        idx = src.find("async def resolve_location_get")
        snippet = src[idx:idx + 400]
        assert "zone:" in snippet


# ═══════════════════════════════════════════════════════════════
# Group 3: api.ts — new methods and interfaces
# ═══════════════════════════════════════════════════════════════

class TestApiTs:
    def test_bulk_change_tier_method_exists(self):
        src = _read(API_TS)
        assert "bulkChangeTierLocations" in src

    def test_bulk_deactivate_method_exists(self):
        src = _read(API_TS)
        assert "bulkDeactivateTierLocations" in src

    def test_list_import_batches_method_exists(self):
        src = _read(API_TS)
        assert "listImportBatches" in src

    def test_resolve_conflict_method_exists(self):
        src = _read(API_TS)
        assert "resolveConflict" in src

    def test_tier_location_has_mapping_type(self):
        src = _read(API_TS)
        assert "mapping_type" in src

    def test_tier_location_has_source(self):
        src = _read(API_TS)
        # Check the TierLocation interface has source
        idx = src.find("export interface TierLocation")
        assert idx != -1
        snippet = src[idx:idx + 500]
        assert "source" in snippet

    def test_tier_location_has_created_at(self):
        src = _read(API_TS)
        idx = src.find("export interface TierLocation")
        snippet = src[idx:idx + 400]
        assert "created_at" in snippet

    def test_resolve_location_has_state_param(self):
        src = _read(API_TS)
        idx = src.find("resolveLocation:")
        assert idx != -1
        snippet = src[idx:idx + 300]
        assert "state?" in snippet

    def test_resolve_location_has_district_param(self):
        src = _read(API_TS)
        idx = src.find("resolveLocation:")
        snippet = src[idx:idx + 300]
        assert "district?" in snippet

    def test_resolve_location_has_zone_param(self):
        src = _read(API_TS)
        idx = src.find("resolveLocation:")
        snippet = src[idx:idx + 300]
        assert "zone?" in snippet

    def test_resolve_location_uses_get_not_post(self):
        src = _read(API_TS)
        idx = src.find("resolveLocation:")
        snippet = src[idx:idx + 400]
        # Now uses GET (query params), not POST with body
        assert "method:" not in snippet or "GET" in snippet

    def test_bulk_change_calls_correct_endpoint(self):
        src = _read(API_TS)
        assert "/tier-locations/bulk/change-tier" in src

    def test_bulk_deactivate_calls_correct_endpoint(self):
        src = _read(API_TS)
        assert "/tier-locations/bulk/deactivate" in src

    def test_resolve_conflict_calls_correct_endpoint(self):
        src = _read(API_TS)
        assert "/resolve-conflict" in src

    def test_list_import_batches_calls_correct_endpoint(self):
        src = _read(API_TS)
        assert "/tier-locations/imports" in src


# ═══════════════════════════════════════════════════════════════
# Group 4: Frontend page — retired (service-area coverage-approval slice)
#
# PROTECTED_BY_LATER_SLICE: the business model changed -- admin no longer
# maps cities/zipcodes to a pricing tier (tenants now request their own
# service-area coverage for admin approval; see
# app/engines/serviceability). This page's entire enterprise-grid UI
# (bulk selection, filters drawer, conflict resolution, etc.) was
# intentionally replaced with a retired-feature notice, unlinked from
# navigation, per the same slice that added the 410
# PRICING_TIER_WRITES_RETIRED guard to every tier/tier-location write
# method. The old per-feature assertions below are gone because the
# features themselves are gone, not because the test was weakened.
# ═══════════════════════════════════════════════════════════════

class TestFrontendPage:
    def test_page_file_exists(self):
        assert os.path.exists(PAGE_FILE)

    def test_page_shows_retired_notice(self):
        src = _read(PAGE_FILE)
        assert "retired" in src.lower()

    def test_page_no_longer_performs_tier_location_writes(self):
        src = _read(PAGE_FILE)
        assert "createTierLocation" not in src
        assert "bulkChangeTierLocations" not in src
        assert "bulkDeactivateTierLocations" not in src

    def test_page_links_to_service_area_requests_replacement(self):
        src = _read(PAGE_FILE)
        assert "/admin/service-area-requests" in src


# ═══════════════════════════════════════════════════════════════
# Group 5: Integration — route ordering correctness
# ═══════════════════════════════════════════════════════════════

class TestRouteOrdering:
    def test_no_route_shadowing_imports(self):
        src = _read(ROUTER_FILE)
        # /tier-locations/imports must appear before /tier-locations/{location_id}
        idx_list = src.find('"/tier-locations/imports"')
        idx_put = src.find('"/tier-locations/{location_id}"')
        assert idx_list < idx_put, "/tier-locations/imports should be before /{location_id} routes"

    def test_no_route_shadowing_bulk(self):
        src = _read(ROUTER_FILE)
        idx_bulk = src.find("/tier-locations/bulk/")
        # Find the tier-locations CREATE route specifically by its summary string
        idx_post = src.find('"Create tier location mapping"')
        assert idx_bulk != -1 and idx_post != -1
        assert idx_bulk < idx_post, "/tier-locations/bulk/* should be before POST /tier-locations create route"


# ═══════════════════════════════════════════════════════════════
# Group 6: SummaryCardsRow onClick support
#
# PROTECTED_BY_LATER_SLICE: removed along with the rest of the page's
# enterprise-grid UI -- see the Group 4 notice above. The retired page
# has no summary cards at all.
# ═══════════════════════════════════════════════════════════════
