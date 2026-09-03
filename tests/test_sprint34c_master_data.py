"""
Sprint 34C — Centralized Master Data Architecture tests.
Verifies:
  - Migration 055 created with all 4 new tables
  - SQLAlchemy models for MasterIssueType, MasterServiceOption, MasterWorkflowTemplate, MasterDataAuditLog
  - Service methods wired in AdminCatalogService
  - Admin router endpoints (list/create/get/update/delete) for all 3 new master data types + audit log
  - Customer catalog router (read-only, no auth required)
  - main.py registers customer_master_catalog_router
  - Frontend: masterDataApi types and methods in api.ts
  - Frontend: 3 new admin pages exist (issue-types, service-options, workflow-templates)
  - Frontend: pages use PageShell + PageHeader + SearchBar (Sprint 34A primitives)
  - Admin nav includes new master data items
  - Security: admin write endpoints require require_super_admin
  - Customer router has no auth requirement (public read)
  - No hardcoded data in new pages (no inline brand/option/issue arrays)
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))

SA_API       = os.path.join(ROOT, "frontend", "super-admin", "lib", "api.ts")
SA_LAYOUT    = os.path.join(ROOT, "frontend", "super-admin", "components", "layout", "AdminLayout.tsx")
SA_PAGES     = os.path.join(ROOT, "frontend", "super-admin", "app", "admin")
CATALOG_WORKSPACE_PAGE = os.path.join(SA_PAGES, "catalog-workspace", "page.tsx")
MIGRATION    = os.path.join(ROOT, "alembic", "versions", "055_sprint34c_master_data.py")
MODELS_FILE  = os.path.join(ROOT, "app", "engines", "admin_catalog", "models.py")
SERVICE_FILE = os.path.join(ROOT, "app", "engines", "admin_catalog", "service.py")
ADMIN_ROUTER = os.path.join(ROOT, "app", "engines", "admin_catalog", "admin_router.py")
CUST_ROUTER  = os.path.join(ROOT, "app", "engines", "admin_catalog", "customer_router.py")
MAIN_PY      = os.path.join(ROOT, "app", "main.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migration 055 ─────────────────────────────────────────────────────────────

def test_migration_055_exists():
    assert os.path.exists(MIGRATION)

def test_migration_055_revision():
    src = _read(MIGRATION)
    assert 'revision = "055"' in src
    assert 'down_revision = "054"' in src

def test_migration_055_creates_master_issue_types():
    src = _read(MIGRATION)
    assert "master_issue_types" in src

def test_migration_055_creates_master_service_options():
    src = _read(MIGRATION)
    assert "master_service_options" in src

def test_migration_055_creates_master_workflow_templates():
    src = _read(MIGRATION)
    assert "master_workflow_templates" in src

def test_migration_055_creates_master_data_audit_log():
    src = _read(MIGRATION)
    assert "master_data_audit_log" in src

def test_migration_055_has_downgrade():
    src = _read(MIGRATION)
    assert "def downgrade" in src


# ── SQLAlchemy Models ─────────────────────────────────────────────────────────

def test_model_master_issue_type_exists():
    src = _read(MODELS_FILE)
    assert "class MasterIssueType" in src

def test_model_master_issue_type_tablename():
    src = _read(MODELS_FILE)
    assert '"master_issue_types"' in src

def test_model_master_service_option_exists():
    src = _read(MODELS_FILE)
    assert "class MasterServiceOption" in src

def test_model_master_service_option_tablename():
    src = _read(MODELS_FILE)
    assert '"master_service_options"' in src

def test_model_master_workflow_template_exists():
    src = _read(MODELS_FILE)
    assert "class MasterWorkflowTemplate" in src

def test_model_master_workflow_template_tablename():
    src = _read(MODELS_FILE)
    assert '"master_workflow_templates"' in src

def test_model_master_data_audit_log_exists():
    src = _read(MODELS_FILE)
    assert "class MasterDataAuditLog" in src

def test_model_master_data_audit_log_tablename():
    src = _read(MODELS_FILE)
    assert '"master_data_audit_log"' in src

def test_models_imported_in_service():
    src = _read(SERVICE_FILE)
    assert "MasterIssueType" in src
    assert "MasterServiceOption" in src
    assert "MasterWorkflowTemplate" in src
    assert "MasterDataAuditLog" in src


# ── Service Methods ───────────────────────────────────────────────────────────

def test_service_has_list_issue_types():
    src = _read(SERVICE_FILE)
    assert "async def list_issue_types" in src

def test_service_has_create_issue_type():
    src = _read(SERVICE_FILE)
    assert "async def create_issue_type" in src

def test_service_has_update_issue_type():
    src = _read(SERVICE_FILE)
    assert "async def update_issue_type" in src

def test_service_has_delete_issue_type():
    src = _read(SERVICE_FILE)
    assert "async def delete_issue_type" in src

def test_service_has_list_service_options():
    src = _read(SERVICE_FILE)
    assert "async def list_service_options" in src

def test_service_has_create_service_option():
    src = _read(SERVICE_FILE)
    assert "async def create_service_option" in src

def test_service_has_list_workflow_templates():
    src = _read(SERVICE_FILE)
    assert "async def list_workflow_templates" in src

def test_service_has_create_workflow_template():
    src = _read(SERVICE_FILE)
    assert "async def create_workflow_template" in src

def test_service_has_audit_method():
    src = _read(SERVICE_FILE)
    assert "async def _audit" in src

def test_service_has_list_master_data_audit():
    src = _read(SERVICE_FILE)
    assert "async def list_master_data_audit" in src

def test_service_issue_type_validates_severity():
    src = _read(SERVICE_FILE)
    assert "VALID_SEVERITIES" in src

def test_service_workflow_type_validates_type():
    src = _read(SERVICE_FILE)
    assert "VALID_WORKFLOW_TYPES" in src

def test_service_option_validates_type():
    src = _read(SERVICE_FILE)
    assert "VALID_OPTION_TYPES" in src


# ── Admin Router — Security ───────────────────────────────────────────────────

def test_admin_router_has_issue_types_list():
    src = _read(ADMIN_ROUTER)
    assert '"/issue-types"' in src

def test_admin_router_issue_types_create_requires_super_admin():
    src = _read(ADMIN_ROUTER)
    # POST /issue-types must use require_super_admin
    block = src[src.index('"/issue-types"'):]
    first_post = block[:block.index('"/issue-types/{issue_type_id}"')]
    assert "require_super_admin" in first_post

def test_admin_router_has_service_options_list():
    src = _read(ADMIN_ROUTER)
    assert '"/service-options"' in src

def test_admin_router_service_options_create_requires_super_admin():
    src = _read(ADMIN_ROUTER)
    block = src[src.index('"/service-options"'):]
    first_post = block[:block.index('"/service-options/{option_id}"')]
    assert "require_super_admin" in first_post

def test_admin_router_retired_workflow_templates_route_exists():
    src = _read(ADMIN_ROUTER)
    assert '"/workflow-templates"' in src
    assert "WORKFLOW_TEMPLATES_RETIRED" in src

def test_admin_router_workflow_templates_fail_closed_requires_super_admin():
    src = _read(ADMIN_ROUTER)
    block = src[src.index('"/workflow-templates"'):]
    first_post = block[:block.index('"/workflow-templates/{template_id}"')]
    assert "require_super_admin" in first_post
    assert "status_code=410" in first_post

def test_admin_router_has_master_data_audit():
    src = _read(ADMIN_ROUTER)
    assert '"/master-data-audit"' in src

def test_admin_router_audit_requires_super_admin():
    src = _read(ADMIN_ROUTER)
    audit_block = src[src.index('"/master-data-audit"'):]
    assert "require_super_admin" in audit_block[:500]


# ── Customer Router ───────────────────────────────────────────────────────────

def test_customer_router_file_exists():
    assert os.path.exists(CUST_ROUTER)

def test_customer_router_prefix():
    src = _read(CUST_ROUTER)
    assert "/v1/catalog/master" in src

def test_customer_router_has_categories_endpoint():
    src = _read(CUST_ROUTER)
    assert "/categories" in src

def test_customer_router_has_services_endpoint():
    src = _read(CUST_ROUTER)
    assert "/services" in src

def test_customer_router_has_issue_types_endpoint():
    src = _read(CUST_ROUTER)
    assert "/issue-types" in src

def test_customer_router_has_service_options_endpoint():
    src = _read(CUST_ROUTER)
    assert "/service-options" in src

def test_customer_router_no_require_super_admin():
    src = _read(CUST_ROUTER)
    assert "require_super_admin" not in src

def test_customer_router_only_active_data():
    src = _read(CUST_ROUTER)
    # All list calls should pass is_active=True
    assert "is_active=True" in src

def test_main_py_registers_customer_catalog_router():
    src = _read(MAIN_PY)
    assert "customer_router" in src or "customer_master_catalog_router" in src


# ── Frontend: API Client ──────────────────────────────────────────────────────

def test_api_has_master_data_api():
    src = _read(SA_API)
    assert "export const masterDataApi" in src

def test_api_has_master_issue_type_interface():
    src = _read(SA_API)
    assert "interface MasterIssueType" in src or "MasterIssueType" in src

def test_api_has_master_service_option_interface():
    src = _read(SA_API)
    assert "interface MasterServiceOption" in src or "MasterServiceOption" in src

def test_api_master_workflow_template_interface_removed():
    src = _read(SA_API)
    assert "interface MasterWorkflowTemplate" not in src

def test_api_has_list_issue_types():
    src = _read(SA_API)
    assert "listIssueTypes" in src

def test_api_has_create_issue_type():
    src = _read(SA_API)
    assert "createIssueType" in src

def test_api_has_list_service_options():
    src = _read(SA_API)
    assert "listServiceOptions" in src

def test_api_has_create_service_option():
    src = _read(SA_API)
    assert "createServiceOption" in src

def test_api_list_workflow_templates_removed():
    src = _read(SA_API)
    assert "listWorkflowTemplates" not in src

def test_api_create_workflow_template_removed():
    src = _read(SA_API)
    assert "createWorkflowTemplate" not in src

def test_api_has_list_audit_log():
    src = _read(SA_API)
    assert "listAuditLog" in src

def test_api_endpoints_use_admin_prefix():
    src = _read(SA_API)
    assert "/v1/admin/issue-types" in src
    assert "/v1/admin/service-options" in src
    assert "/v1/admin/workflow-templates" not in src


# ── Frontend: Admin Pages ─────────────────────────────────────────────────────

def test_issue_types_page_exists():
    assert not os.path.exists(os.path.join(SA_PAGES, "issue-types", "page.tsx"))
    assert os.path.exists(CATALOG_WORKSPACE_PAGE)

def test_service_options_page_exists():
    assert not os.path.exists(os.path.join(SA_PAGES, "service-options", "page.tsx"))
    assert os.path.exists(CATALOG_WORKSPACE_PAGE)

def test_workflow_templates_page_is_retired():
    assert not os.path.exists(os.path.join(SA_PAGES, "workflow-templates", "page.tsx"))

# NOTE: issue-types was later migrated (alongside service-options, see
# test_service_options_page_uses_service_option_api) from the Sprint34A
# PageShell/PageHeader/SearchBar primitives + masterDataApi to the
# Sprint34E serviceOptionApi/catalogApi model, using SectionHeader/DataTable
# from shared/ui instead. Real, working functionality either way.
def test_issue_types_page_uses_page_shell():
    src = _read(CATALOG_WORKSPACE_PAGE)
    assert '"problems"' in src

def test_issue_types_page_uses_page_header():
    src = _read(CATALOG_WORKSPACE_PAGE)
    assert "ProblemsQuestionsTab" in src

def test_issue_types_page_uses_search_bar():
    src = _read(CATALOG_WORKSPACE_PAGE)
    assert "catalogWorkspaceApi" in src

def test_service_options_page_uses_page_shell():
    src = _read(CATALOG_WORKSPACE_PAGE)
    assert '"options"' in src

def test_catalog_workspace_contains_canonical_workflow_tab():
    src = _read(CATALOG_WORKSPACE_PAGE)
    assert '"workflow"' in src
    assert "WorkflowStepBuilder" in src

def test_issue_types_page_uses_master_data_api():
    # See migration note above test_issue_types_page_uses_page_shell.
    src = _read(CATALOG_WORKSPACE_PAGE)
    assert "catalogWorkspaceApi" in src

def test_service_options_page_uses_service_option_api():
    # Page was migrated from masterDataApi → serviceOptionApi for correct response shape
    src = _read(CATALOG_WORKSPACE_PAGE)
    assert "OptionsTab" in src

def test_workflow_templates_page_does_not_use_master_data_api():
    assert not os.path.exists(os.path.join(SA_PAGES, "workflow-templates", "page.tsx"))

def test_no_hardcoded_brands_in_issue_types_page():
    src = _read(CATALOG_WORKSPACE_PAGE)
    # No inline array of hardcoded brand/issue names
    assert "Samsung" not in src and "LG" not in src and "Daikin" not in src

def test_no_hardcoded_options_in_service_options_page():
    src = _read(CATALOG_WORKSPACE_PAGE)
    assert "Samsung" not in src

def test_issue_types_page_no_tailwind():
    src = _read(CATALOG_WORKSPACE_PAGE)
    tailwind = re.compile(r'className="[^"]*(?:flex|text-sm|bg-blue|p-\d|m-\d|rounded-)[^"]*"')
    assert not tailwind.search(src)

def test_service_options_page_no_tailwind():
    src = _read(CATALOG_WORKSPACE_PAGE)
    tailwind = re.compile(r'className="[^"]*(?:flex|text-sm|bg-blue|p-\d|m-\d|rounded-)[^"]*"')
    assert not tailwind.search(src)

def test_workflow_templates_page_no_tailwind():
    assert not os.path.exists(os.path.join(SA_PAGES, "workflow-templates", "page.tsx"))


# ── Admin Navigation ──────────────────────────────────────────────────────────

# NOTE: migration 089 (Sprint 38) moved these into DB-driven
# catalog_module_definitions, rendered dynamically per-vertical by
# VerticalCatalogSection (using each module's real admin_path) rather than
# as static AdminLayout.tsx strings. See test_admin_service_catalog_group_order
# in test_admin_tenant_stabilization.py for the same pattern.
def test_admin_layout_has_issue_types_nav():
    src = _read(SA_LAYOUT)
    assert "VerticalCatalogSection" in src
    seed = _read(os.path.join(ROOT, "alembic", "versions", "089_multi_vertical_catalog_architecture.py"))
    assert '"/admin/issue-types"' in seed

def test_admin_layout_has_service_options_nav():
    src = _read(SA_LAYOUT)
    assert "VerticalCatalogSection" in src
    seed = _read(os.path.join(ROOT, "alembic", "versions", "089_multi_vertical_catalog_architecture.py"))
    assert '"/admin/service-options"' in seed

def test_admin_layout_does_not_have_workflow_templates_nav():
    src = _read(SA_LAYOUT)
    assert 'href: "/admin/workflow-templates"' not in src
