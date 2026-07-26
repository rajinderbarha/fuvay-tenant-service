"""Tests for P0 Issue Types — service-mapped, customer flow connected."""
from pathlib import Path
import re

ROOT            = Path(__file__).parent.parent
SERVICE_SVC     = ROOT / "app" / "engines" / "admin_catalog" / "service_option_service.py"
ADMIN_ROUTER    = ROOT / "app" / "engines" / "admin_catalog" / "service_option_admin_router.py"
CUSTOMER_ROUTER = ROOT / "app" / "engines" / "admin_catalog" / "service_option_customer_router.py"
MODELS          = ROOT / "app" / "engines" / "admin_catalog" / "models.py"
MIGRATION       = ROOT / "alembic" / "versions" / "074_issue_type_mapping_enhancements.py"
FRONTEND_PAGE   = ROOT / "frontend" / "super-admin" / "app" / "admin" / "issue-types" / "page.tsx"
API_TS          = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
SEED_SCRIPT     = ROOT / "scripts" / "seed_issue_types.py"
MAIN_PY         = ROOT / "app" / "main.py"


# ── Migration ────────────────────────────────────────────────────────────────

def test_migration_074_exists():
    assert MIGRATION.exists()

def test_migration_adds_customer_visible_to_mappings():
    src = MIGRATION.read_text(encoding="utf-8")
    assert "service_issue_mappings" in src
    assert "customer_visible" in src

def test_migration_adds_severity_override():
    src = MIGRATION.read_text(encoding="utf-8")
    assert "severity_override" in src

def test_migration_adds_customer_visible_to_issue_types():
    src = MIGRATION.read_text(encoding="utf-8")
    assert "master_issue_types" in src
    assert "customer_visible" in src


# ── Models ───────────────────────────────────────────────────────────────────

def test_model_master_issue_type_has_customer_visible():
    src = MODELS.read_text(encoding="utf-8")
    start = src.find("class MasterIssueType")
    end   = src.find("class ", start + 1)
    block = src[start:end]
    assert "customer_visible" in block

def test_model_service_issue_mapping_has_customer_visible():
    src = MODELS.read_text(encoding="utf-8")
    start = src.find("class ServiceIssueMapping")
    end   = src.find("class ", start + 1)
    block = src[start:end]
    assert "customer_visible" in block

def test_model_service_issue_mapping_has_severity_override():
    src = MODELS.read_text(encoding="utf-8")
    start = src.find("class ServiceIssueMapping")
    end   = src.find("class ", start + 1)
    block = src[start:end]
    assert "severity_override" in block

def test_model_service_issue_mapping_to_dict_includes_new_fields():
    src = MODELS.read_text(encoding="utf-8")
    start = src.find("class ServiceIssueMapping")
    end   = src.find("class ", start + 1)
    block = src[start:end]
    assert '"customer_visible"' in block
    assert '"severity_override"' in block

def test_model_master_issue_type_to_dict_includes_customer_visible():
    src = MODELS.read_text(encoding="utf-8")
    start = src.find("class MasterIssueType")
    end   = src.find("class ", start + 1)
    block = src[start:end]
    assert '"customer_visible"' in block


# ── Service layer ─────────────────────────────────────────────────────────────

def test_service_list_issue_types_returns_mapped_services_count():
    src = SERVICE_SVC.read_text(encoding="utf-8")
    assert "mapped_services_count" in src

def test_service_creates_issue_type_with_customer_visible():
    src = SERVICE_SVC.read_text(encoding="utf-8")
    start = src.find("def create_issue_type")
    end   = src.find("\n    async def ", start + 1)
    block = src[start:end]
    assert "customer_visible" in block

def test_service_updates_issue_type_with_customer_visible():
    src = SERVICE_SVC.read_text(encoding="utf-8")
    start = src.find("def update_issue_type")
    end   = src.find("\n    async def ", start + 1)
    block = src[start:end]
    assert "customer_visible" in block

def test_service_add_issue_mapping_supports_customer_visible():
    src = SERVICE_SVC.read_text(encoding="utf-8")
    start = src.find("def add_service_issue_mapping")
    end   = src.find("\n    async def ", start + 1)
    block = src[start:end]
    assert "customer_visible" in block

def test_service_add_issue_mapping_supports_severity_override():
    src = SERVICE_SVC.read_text(encoding="utf-8")
    start = src.find("def add_service_issue_mapping")
    end   = src.find("\n    async def ", start + 1)
    block = src[start:end]
    assert "severity_override" in block

def test_service_update_mapping_supports_new_fields():
    src = SERVICE_SVC.read_text(encoding="utf-8")
    start = src.find("def update_service_issue_mapping")
    end   = src.find("\n    async def ", start + 1)
    block = src[start:end]
    assert "customer_visible" in block
    assert "severity_override" in block

def test_service_customer_issues_respects_customer_visible():
    src = SERVICE_SVC.read_text(encoding="utf-8")
    start = src.find("def get_customer_issue_types")
    end   = src.find("\n    async def ", start + 1)
    block = src[start:end]
    assert "customer_visible" in block

def test_service_customer_issues_uses_severity_override():
    src = SERVICE_SVC.read_text(encoding="utf-8")
    start = src.find("def get_customer_issue_types")
    end   = src.find("\n    async def ", start + 1)
    block = src[start:end]
    assert "severity_override" in block

def test_service_list_issue_types_filters_by_mapping_when_service_id():
    src = SERVICE_SVC.read_text(encoding="utf-8")
    start = src.find("def list_issue_types")
    end   = src.find("\n    async def ", start + 1)
    block = src[start:end]
    assert "ServiceIssueMapping" in block

def test_service_list_issue_types_search_includes_code():
    src = SERVICE_SVC.read_text(encoding="utf-8")
    start = src.find("def list_issue_types")
    end   = src.find("\n    async def ", start + 1)
    block = src[start:end]
    assert "code" in block and "ilike" in block.lower()


# ── Admin router endpoints ────────────────────────────────────────────────────

def test_admin_router_has_issue_types_v2_prefix():
    src = ADMIN_ROUTER.read_text(encoding="utf-8")
    assert "/v1/admin/issue-types-v2" in src

def test_admin_router_has_activate_endpoint():
    src = ADMIN_ROUTER.read_text(encoding="utf-8")
    assert "/activate" in src

def test_admin_router_has_deactivate_endpoint():
    src = ADMIN_ROUTER.read_text(encoding="utf-8")
    assert "/deactivate" in src

def test_admin_router_has_archive_endpoint():
    src = ADMIN_ROUTER.read_text(encoding="utf-8")
    assert "/archive" in src

def test_admin_router_has_service_issue_mapping_endpoints():
    src = ADMIN_ROUTER.read_text(encoding="utf-8")
    assert "/issues" in src
    assert "list_service_issue_mappings" in src
    assert "add_service_issue_mapping" in src
    assert "remove_service_issue_mapping" in src


# ── Customer router ───────────────────────────────────────────────────────────

def test_customer_router_has_issue_types_endpoint():
    src = CUSTOMER_ROUTER.read_text(encoding="utf-8")
    assert "/issue-types" in src

def test_customer_router_accepts_service_id():
    src = CUSTOMER_ROUTER.read_text(encoding="utf-8")
    assert "service_id" in src

def test_customer_router_calls_get_customer_issue_types():
    src = CUSTOMER_ROUTER.read_text(encoding="utf-8")
    assert "get_customer_issue_types" in src

def test_customer_router_under_v1_customer_catalog():
    src = CUSTOMER_ROUTER.read_text(encoding="utf-8")
    assert "/v1/customer/catalog" in src


# ── main.py registration ──────────────────────────────────────────────────────

def test_main_registers_issue_type_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "svc_iss_router" in src

def test_main_registers_service_map_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "svc_map_router" in src

def test_main_registers_customer_issue_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "service_option_customer_router" in src or "svc_opt_customer" in src or "customer_catalog" in src.lower()


# ── Frontend page ─────────────────────────────────────────────────────────────
# MODULE-L5-56: /admin/issue-types is intentionally retired as a standalone
# page (Job-Type Blueprint consolidation) -- Problems & Questions are now
# configured only per exact Job Type inside Catalog Workspace's Problems &
# Questions tab. The page file now renders a retired-notice redirect (see
# tests/test_module_l5_56_blueprint_consolidation.py::TestStandalonePageRetirement
# for its replacement contract). These content assertions test the OLD page
# and are expected to fail post-retirement; skipped rather than silently
# deleted so the historical intent stays visible in git history.
import pytest as _pytest_skip_marker  # noqa: E402

pytestmark_frontend_retired = _pytest_skip_marker.mark.skip(
    reason="MODULE-L5-56: /admin/issue-types retired as a standalone page; superseded by "
           "Catalog Workspace's Problems & Questions tab."
)


@pytestmark_frontend_retired
def test_frontend_uses_service_option_api_not_old_master_data():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "serviceOptionApi" in src
    # Old API that pointed to wrong endpoint should not be sole usage
    # masterDataApi.listIssueTypes pointed to /v1/admin/issue-types (legacy)
    # page may still import masterDataApi but should call serviceOptionApi for list

@pytestmark_frontend_retired
def test_frontend_has_category_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "categoryFilter" in src or "category" in src.lower()

@pytestmark_frontend_retired
def test_frontend_has_service_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "serviceFilter" in src or "service_id" in src

@pytestmark_frontend_retired
def test_frontend_has_severity_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "severityFilter" in src or "severity" in src

@pytestmark_frontend_retired
def test_frontend_has_status_filter():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "statusFilter" in src or "status" in src

@pytestmark_frontend_retired
def test_frontend_shows_mapped_services_count():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "mapped_services_count" in src

@pytestmark_frontend_retired
def test_frontend_shows_requires_photo_column():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "requires_photo" in src

@pytestmark_frontend_retired
def test_frontend_shows_requires_description_column():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "requires_description" in src

@pytestmark_frontend_retired
def test_frontend_shows_customer_visible_column():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "customer_visible" in src

@pytestmark_frontend_retired
def test_frontend_has_mapping_section_in_modal():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "Map to Service" in src or "map" in src.lower()

@pytestmark_frontend_retired
def test_frontend_has_activate_action():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "activateIssueType" in src or "activateAction" in src

@pytestmark_frontend_retired
def test_frontend_has_deactivate_action():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "deactivateIssueType" in src or "deactivateAction" in src

@pytestmark_frontend_retired
def test_frontend_has_archive_action():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "archiveIssueType" in src or "archiveAction" in src

@pytestmark_frontend_retired
def test_frontend_has_map_to_service_button():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "MappingModal" in src or "mapping" in src.lower()

@pytestmark_frontend_retired
def test_frontend_no_blocker_empty_state_when_filters_active():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "No issue types match" in src

@pytestmark_frontend_retired
def test_frontend_create_modal_has_customer_visible():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "customer_visible" in src

@pytestmark_frontend_retired
def test_frontend_cascading_service_selector():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "ServiceSelector" in src or "mapCatId" in src

@pytestmark_frontend_retired
def test_frontend_has_pagination():
    src = FRONTEND_PAGE.read_text(encoding="utf-8")
    assert "totalPages" in src or "total_pages" in src


# ── API client ────────────────────────────────────────────────────────────────

def test_api_ts_has_service_option_api_list_issue_types():
    src = API_TS.read_text(encoding="utf-8")
    assert "listIssueTypes" in src
    assert "/v1/admin/issue-types-v2" in src

def test_api_ts_has_create_issue_type():
    src = API_TS.read_text(encoding="utf-8")
    assert "createIssueType" in src

def test_api_ts_has_activate_deactivate_archive():
    src = API_TS.read_text(encoding="utf-8")
    assert "activateIssueType" in src
    assert "deactivateIssueType" in src
    assert "archiveIssueType" in src

def test_api_ts_has_service_issue_mapping_methods():
    src = API_TS.read_text(encoding="utf-8")
    assert "listServiceIssueMappings" in src
    assert "addServiceIssueMapping" in src
    assert "removeServiceIssueMapping" in src

def test_customer_router_endpoint_url_is_correct():
    src = CUSTOMER_ROUTER.read_text(encoding="utf-8")
    assert "/v1/customer/catalog" in src
    assert "/issue-types" in src

def test_api_ts_issue_type_interface_has_key_fields():
    src = API_TS.read_text(encoding="utf-8")
    start = src.find("export interface IssueType34E")
    end   = src.find("}", start)
    block = src[start:end]
    for field in ["id", "code", "name", "severity", "requires_photo", "requires_description"]:
        assert field in block

def test_api_ts_service_issue_mapping_interface_exists():
    src = API_TS.read_text(encoding="utf-8")
    assert "ServiceIssueMapping34E" in src


# ── Seed script ───────────────────────────────────────────────────────────────

def test_seed_script_exists():
    assert SEED_SCRIPT.exists()

def test_seed_script_has_ac_repair_issues():
    src = SEED_SCRIPT.read_text(encoding="utf-8")
    assert "AC Not Cooling" in src
    assert "ac_repair" in src

def test_seed_script_has_plumbing_issues():
    src = SEED_SCRIPT.read_text(encoding="utf-8")
    assert "Pipe Leakage" in src or "Leakage" in src

def test_seed_script_has_electrical_issues():
    src = SEED_SCRIPT.read_text(encoding="utf-8")
    assert "Short Circuit" in src or "No Power" in src

def test_seed_script_has_washing_machine_issues():
    src = SEED_SCRIPT.read_text(encoding="utf-8")
    assert "Not Spinning" in src

def test_seed_script_is_idempotent():
    src = SEED_SCRIPT.read_text(encoding="utf-8")
    assert "existing" in src and "skip" in src

def test_seed_script_maps_issues_to_services():
    src = SEED_SCRIPT.read_text(encoding="utf-8")
    assert "ServiceIssueMapping" in src
    assert "SERVICE_ISSUE_MAP" in src or "service_issue_map" in src.lower()

def test_seed_script_handles_missing_service_gracefully():
    src = SEED_SCRIPT.read_text(encoding="utf-8")
    assert "not found" in src.lower() or "skip" in src.lower()
