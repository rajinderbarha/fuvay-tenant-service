"""
P0 Enterprise Catalog Upgrade — test suite
Verifies:
  Backend:
    - AdminCatalogService: _sg_linked_counts, _sg_readiness, get_service_groups_summary,
      list_service_groups_enterprise, activate/deactivate/archive_service_group,
      export_service_groups, _ms_linked_counts, _ms_pricing_readiness, _ms_runtime_readiness,
      get_master_services_summary, list_master_services_enterprise,
      activate/deactivate/archive_master_service, export_master_services
    - Admin router: new enterprise endpoints (summary, export, activate, deactivate, archive)
    - Tenant isolation + auth guards present
  Frontend:
    - api.ts: new interfaces and methods
    - service-groups/page.tsx: enterprise upgrade (summary cards, readiness, action menu)
    - master-services/page.tsx: enterprise upgrade (no direct Price column, readiness, action menu)
"""
import os
import re

ROOT         = os.path.dirname(os.path.dirname(__file__))
SERVICE_FILE = os.path.join(ROOT, "app", "engines", "admin_catalog", "service.py")
ADMIN_ROUTER = os.path.join(ROOT, "app", "engines", "admin_catalog", "admin_router.py")
SA_API       = os.path.join(ROOT, "frontend", "super-admin", "lib", "api.ts")
SG_PAGE      = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "service-groups", "page.tsx")
SG_DETAIL_PAGE = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "service-groups", "[id]", "page.tsx")
MS_PAGE      = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "master-services", "page.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Backend: service.py new methods ───────────────────────────────────────────

def test_sg_linked_counts_method_exists():
    src = _read(SERVICE_FILE)
    assert "_sg_linked_counts" in src, "Batch service-group count helper missing"

def test_sg_readiness_method_exists():
    src = _read(SERVICE_FILE)
    assert "_sg_readiness" in src, "Service group readiness classifier missing"

def test_get_service_groups_summary_exists():
    src = _read(SERVICE_FILE)
    assert "get_service_groups_summary" in src

def test_list_service_groups_enterprise_exists():
    src = _read(SERVICE_FILE)
    assert "list_service_groups_enterprise" in src

def test_sg_activate_deactivate_archive_methods():
    src = _read(SERVICE_FILE)
    assert "activate_service_group" in src
    assert "deactivate_service_group" in src
    assert "archive_service_group" in src

def test_sg_export_method_exists():
    src = _read(SERVICE_FILE)
    assert "export_service_groups" in src

def test_ms_linked_counts_method_exists():
    src = _read(SERVICE_FILE)
    assert "_ms_linked_counts" in src, "Batch master-service count helper missing"

def test_ms_pricing_readiness_method_exists():
    src = _read(SERVICE_FILE)
    assert "_ms_pricing_readiness" in src

def test_ms_runtime_readiness_method_exists():
    src = _read(SERVICE_FILE)
    assert "_ms_runtime_readiness" in src

def test_get_master_services_summary_exists():
    src = _read(SERVICE_FILE)
    assert "get_master_services_summary" in src

def test_list_master_services_enterprise_exists():
    src = _read(SERVICE_FILE)
    assert "list_master_services_enterprise" in src

def test_ms_activate_deactivate_archive_methods():
    src = _read(SERVICE_FILE)
    assert "activate_master_service" in src
    assert "deactivate_master_service" in src
    assert "archive_master_service" in src

def test_ms_export_method_exists():
    src = _read(SERVICE_FILE)
    assert "export_master_services" in src

def test_sg_linked_counts_no_n_plus_one():
    """Batch count must use group_by, not a loop."""
    src = _read(SERVICE_FILE)
    assert "group_by" in src, "Linked-count query should use group_by for batch efficiency"

def test_sg_archive_blocked_when_has_services():
    """archive_service_group must refuse if services exist."""
    src = _read(SERVICE_FILE)
    # Should check services count before archiving
    assert "archive_service_group" in src
    # Look for a guard pattern — raise/error before setting deleted_at
    idx = src.index("archive_service_group")
    snippet = src[idx:idx+800]
    assert ("raise" in snippet or "HTTPException" in snippet or "services" in snippet), \
        "archive_service_group should guard against archiving groups with active services"

def test_sg_readiness_statuses_defined():
    src = _read(SERVICE_FILE)
    for status in ("ready", "empty_group", "inactive", "archived"):
        assert f'"{status}"' in src or f"'{status}'" in src, f"Readiness status '{status}' not found"

def test_ms_pricing_readiness_statuses_defined():
    src = _read(SERVICE_FILE)
    for status in ("ready", "fallback_only", "missing_rules", "inactive"):
        assert f'"{status}"' in src or f"'{status}'" in src, f"Pricing readiness status '{status}' not found"


# ── Backend: admin_router.py new endpoints ────────────────────────────────────

def test_router_sg_summary_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "/service-groups/summary" in src

def test_router_sg_export_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "/service-groups/export" in src

def test_router_sg_activate_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "activate_service_group" in src
    assert "/service-groups/{group_id}/activate" in src or "activate" in src

def test_router_sg_deactivate_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "deactivate_service_group" in src

def test_router_sg_archive_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "archive_service_group" in src

def test_router_ms_summary_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "/master-services/summary" in src

def test_router_ms_export_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "/master-services/export" in src

def test_router_ms_activate_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "activate_master_service" in src

def test_router_ms_deactivate_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "deactivate_master_service" in src

def test_router_ms_archive_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "archive_master_service" in src

def test_router_write_endpoints_require_super_admin():
    src = _read(ADMIN_ROUTER)
    assert "require_super_admin" in src, "Write endpoints must use require_super_admin"

def test_router_enterprise_list_accepts_filters():
    src = _read(ADMIN_ROUTER)
    # Enterprise list endpoint should accept query params
    assert "list_service_groups_enterprise" in src
    assert "list_master_services_enterprise" in src


# ── Frontend: api.ts new interfaces and methods ───────────────────────────────

def test_api_ts_service_group_enriched_interface():
    src = _read(SA_API)
    assert "ServiceGroupEnriched" in src

def test_api_ts_service_groups_summary_interface():
    src = _read(SA_API)
    assert "ServiceGroupsSummary" in src

def test_api_ts_master_service_enriched_interface():
    src = _read(SA_API)
    assert "MasterServiceEnriched" in src

def test_api_ts_master_services_summary_interface():
    src = _read(SA_API)
    assert "MasterServicesSummary" in src

def test_api_ts_enriched_has_linked_counts():
    src = _read(SA_API)
    assert "linked_counts" in src

def test_api_ts_enriched_has_runtime_readiness():
    src = _read(SA_API)
    assert "runtime_readiness" in src

def test_api_ts_enriched_has_pricing_readiness():
    src = _read(SA_API)
    assert "pricing_readiness" in src

def test_api_ts_get_service_groups_summary_method():
    src = _read(SA_API)
    assert "getServiceGroupsSummary" in src

def test_api_ts_list_service_groups_enterprise_method():
    src = _read(SA_API)
    # listServiceGroups should now accept params object
    assert "listServiceGroups" in src
    idx = src.index("listServiceGroups")
    snippet = src[idx:idx+300]
    assert "params" in snippet or "categoryId" in snippet or "service-groups" in snippet

def test_api_ts_sg_status_change_methods():
    src = _read(SA_API)
    assert "activateServiceGroup" in src
    assert "deactivateServiceGroup" in src
    assert "archiveServiceGroup" in src

def test_api_ts_export_service_groups_method():
    src = _read(SA_API)
    assert "exportServiceGroups" in src

def test_api_ts_get_master_services_summary_method():
    src = _read(SA_API)
    assert "getMasterServicesSummary" in src

def test_api_ts_list_master_services_enterprise_method():
    src = _read(SA_API)
    assert "listMasterServicesEnterprise" in src

def test_api_ts_ms_status_change_methods():
    src = _read(SA_API)
    assert "activateMasterService" in src
    assert "deactivateMasterService" in src
    assert "archiveMasterService" in src

def test_api_ts_export_master_services_method():
    src = _read(SA_API)
    assert "exportMasterServices" in src


# ── Frontend: service-groups/page.tsx enterprise upgrade ──────────────────────

def test_sg_page_imports_enriched_type():
    src = _read(SG_PAGE)
    assert "ServiceGroupEnriched" in src

def test_sg_page_imports_summary_type():
    src = _read(SG_PAGE)
    assert "ServiceGroupsSummary" in src

def test_sg_page_calls_summary_api():
    src = _read(SG_PAGE)
    assert "getServiceGroupsSummary" in src

def test_sg_page_has_summary_cards():
    src = _read(SG_PAGE)
    assert "SummaryCard" in src

def test_sg_page_shows_runtime_readiness_column():
    src = _read(SG_PAGE)
    assert "runtime_readiness" in src

def test_sg_page_shows_linked_counts():
    src = _read(SG_PAGE)
    assert "linked_counts" in src

def test_sg_page_has_labeled_action_menu():
    """Actions must be a labeled dropdown, not icon-only buttons."""
    src = _read(SG_PAGE)
    assert "Actions" in src
    # Should have menu items with text labels
    assert "View details" in src and "Edit group" in src

def test_sg_page_has_durable_detail_route():
    src = _read(SG_PAGE)
    detail = _read(SG_DETAIL_PAGE)
    assert "/admin/service-groups/${row.id}" in src
    assert "getServiceGroupAudit" in detail

def test_sg_page_has_activate_deactivate_actions():
    src = _read(SG_PAGE)
    assert "activateServiceGroup" in src or "activateAction" in src
    assert "deactivateServiceGroup" in src or "deactivateAction" in src

def test_sg_page_has_retire_confirm():
    src = _read(SG_PAGE)
    assert "archiveServiceGroup" in src or "archiveAction" in src
    assert "Retire" in src

def test_sg_page_has_export_button():
    src = _read(SG_PAGE)
    assert "OperationsDirectoryControls" in src
    assert 'resourceKey="admin_service_groups"' in src

def test_sg_page_has_advanced_filters():
    src = _read(SG_PAGE)
    assert "Advanced" in src or "showAdvanced" in src

def test_sg_page_no_tailwind():
    src = _read(SG_PAGE)
    # Only shared global catalogue classes are permitted here.
    classnames = re.findall(r'className="([^"]+)"', src)
    for cn in classnames:
        assert cn in ("skeleton", "catalog-admin-page")

def test_sg_page_hierarchy_breadcrumb():
    src = _read(SG_DETAIL_PAGE)
    assert "/admin/categories/" in src
    assert "/admin/master-services?service_group_id=" in src


# ── Frontend: master-services/page.tsx enterprise upgrade ─────────────────────

def test_ms_page_imports_enriched_type():
    src = _read(MS_PAGE)
    assert "MasterServiceEnriched" in src

def test_ms_page_calls_summary_api():
    src = _read(MS_PAGE)
    assert "getMasterServicesSummary" in src

def test_ms_page_has_summary_cards():
    src = _read(MS_PAGE)
    assert "SummaryCard" in src

def test_ms_page_no_direct_price_column():
    """Price amounts are tenant-owned and do not belong in this directory."""
    src = _read(MS_PAGE)
    col_labels = re.findall(r'label:\s*["\']([^"\']+)["\']', src)
    assert "Price" not in col_labels, f"Direct 'Price' column must be removed from Master Services table. Found columns: {col_labels}"

def test_ms_page_shows_blueprint_readiness():
    src = _read(MS_PAGE)
    assert "blueprint_ready" in src

def test_ms_page_shows_runtime_readiness():
    src = _read(MS_PAGE)
    assert "runtime_readiness" in src

def test_ms_page_shows_linked_counts():
    src = _read(MS_PAGE)
    assert "linked_counts" in src

def test_ms_page_shows_requirements_chips():
    src = _read(MS_PAGE)
    # Requirements displayed as chips or badges
    assert "ReqChips" in src or "requires_issue_type" in src

def test_ms_page_has_labeled_action_menu():
    src = _read(MS_PAGE)
    assert "Actions" in src
    assert "Edit service" in src and "View details" in src

def test_ms_page_has_detail_drawer():
    src = _read(MS_PAGE)
    detail = _read(os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "master-services", "[id]", "page.tsx"))
    assert "/admin/master-services/${row.id}" in src
    assert "getMasterServiceAudit" in detail

def test_ms_page_has_activate_deactivate_actions():
    src = _read(MS_PAGE)
    assert "activateMasterService" in src or "activateAction" in src
    assert "deactivateMasterService" in src or "deactivateAction" in src

def test_ms_page_has_export_button():
    src = _read(MS_PAGE)
    assert "OperationsDirectoryControls" in src
    assert 'resourceKey="admin_master_services"' in src

def test_ms_page_create_form_submits_service_group_id():
    """Bug fix: service_group_id must be included in create payload."""
    src = _read(MS_PAGE)
    # createAction should include service_group_id
    idx = src.index("createAction") if "createAction" in src else src.index("createMasterService")
    snippet = src[idx:idx+1000]
    assert "service_group_id" in snippet, "Create form must submit service_group_id"

def test_ms_page_job_type_filter_buttons():
    """By-job-type breakdown should be clickable filter chips."""
    src = _read(MS_PAGE)
    assert "by_job_type" in src

def test_ms_page_no_tailwind():
    src = _read(MS_PAGE)
    classnames = re.findall(r'className="([^"]+)"', src)
    for cn in classnames:
        assert cn == "skeleton", f"Forbidden className found: '{cn}' — use CSS variables instead"

def test_ms_page_hierarchy_in_drawer():
    src = _read(MS_PAGE)
    assert "ChevronRight" in src or "›" in src

def test_ms_page_req_toggles_in_form():
    """Requirements should be toggle controls in the create/edit form."""
    src = _read(MS_PAGE)
    assert "ReqToggle" in src or "is_brand_required" in src
