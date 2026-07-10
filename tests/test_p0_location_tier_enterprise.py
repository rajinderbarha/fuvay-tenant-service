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
        snippet = src[idx:idx + 300]
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
# Group 4: Frontend page — new features present
# ═══════════════════════════════════════════════════════════════

class TestFrontendPage:
    def test_page_file_exists(self):
        assert os.path.exists(PAGE_FILE)

    def test_page_has_advanced_filters_drawer(self):
        src = _read(PAGE_FILE)
        assert "FiltersDrawer" in src or "Advanced Filters" in src

    def test_page_has_bulk_selection(self):
        src = _read(PAGE_FILE)
        assert "selected" in src and "toggleAll" in src

    def test_page_has_detail_drawer(self):
        src = _read(PAGE_FILE)
        assert "DetailDrawer" in src

    def test_page_has_conflict_resolution_drawer(self):
        src = _read(PAGE_FILE)
        assert "ConflictDrawer" in src or "resolve-conflict" in src.lower() or "resolveConflict" in src

    def test_page_has_bulk_change_tier(self):
        src = _read(PAGE_FILE)
        assert "bulkChangeTierLocations" in src or "bulk/change-tier" in src or "bulkTierModal" in src

    def test_page_has_bulk_deactivate(self):
        src = _read(PAGE_FILE)
        assert "bulkDeactivateTierLocations" in src or "bulk/deactivate" in src

    def test_page_has_mapping_type_column(self):
        src = _read(PAGE_FILE)
        assert "MappingTypeBadge" in src or "mapping_type" in src

    def test_page_has_enhanced_resolve_test(self):
        src = _read(PAGE_FILE)
        # Should have district + zone inputs for resolve test
        assert "resolveDistrict" in src or "resolveZone" in src

    def test_page_has_import_history(self):
        src = _read(PAGE_FILE)
        assert "listImportBatches" in src or "showImports" in src or "Import History" in src

    def test_page_has_clickable_summary_cards(self):
        src = _read(PAGE_FILE)
        assert "onClick" in src and ("handleCardClick" in src or "setConflictOnly" in src)

    def test_page_has_checkbox_select_all(self):
        src = _read(PAGE_FILE)
        assert "CheckSquare" in src or "allSelected" in src

    def test_page_has_conflict_badge_component(self):
        src = _read(PAGE_FILE)
        assert "ConflictBadge" in src

    def test_page_has_state_resolve_input(self):
        src = _read(PAGE_FILE)
        assert "resolveState" in src

    def test_page_has_zone_resolve_input(self):
        src = _read(PAGE_FILE)
        assert "resolveZone" in src

    def test_page_has_updated_at_column(self):
        src = _read(PAGE_FILE)
        assert "updated_at" in src

    def test_page_imports_filters_icon(self):
        src = _read(PAGE_FILE)
        assert "SlidersHorizontal" in src or "Filter" in src

    def test_page_imports_history_icon(self):
        src = _read(PAGE_FILE)
        assert "History" in src

    def test_page_has_advanced_filter_state(self):
        src = _read(PAGE_FILE)
        assert "advFilters" in src or "AdvancedFilters" in src

    def test_page_passes_all_filters_to_api(self):
        src = _read(PAGE_FILE)
        assert "listTierLocationsGrid" in src
        idx = src.find("listTierLocationsGrid")
        snippet = src[idx:idx + 400]
        # Should pass state, district, city, zipcode
        assert "state" in snippet and "district" in snippet

    def test_page_has_zone_field_in_create_form(self):
        src = _read(PAGE_FILE)
        # Create/edit modal should include zone_name field
        assert "zone_name" in src

    def test_page_has_priority_field_in_create_form(self):
        src = _read(PAGE_FILE)
        assert "priority" in src

    def test_page_resolves_with_five_params(self):
        src = _read(PAGE_FILE)
        # handleResolve calls resolveAction.execute with up to 5 params
        idx = src.find("resolveAction.execute")
        assert idx != -1
        snippet = src[idx:idx + 200]
        # Should pass city, zip, state, district, zone
        assert "resolveCity" in snippet or "resolveZip" in snippet


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
# ═══════════════════════════════════════════════════════════════

class TestSummaryCardsClick:
    def test_summary_cards_have_onclick(self):
        src = _read(PAGE_FILE)
        # Summary cards should have onClick handlers — find the JSX usage, not the import
        idx = src.find("<SummaryCardsRow")
        assert idx != -1
        snippet = src[idx:idx + 800]
        assert "onClick" in snippet

    def test_conflict_card_sets_conflict_only(self):
        src = _read(PAGE_FILE)
        # The "Duplicate Conflicts" card click should filter to conflict only
        assert "setConflictOnly" in src or "handleCardClick" in src
