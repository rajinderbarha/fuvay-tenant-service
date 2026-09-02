"""Regression contract for scalable Catalog admin directories."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_categories_page_includes_enterprise_controls_and_server_paging():
    src = (ROOT / "frontend/super-admin/app/admin/categories/page.tsx").read_text(encoding="utf-8")
    assert 'resourceKey="admin_categories"' in src
    assert "page_size: PAGE_SIZE" in src
    assert "sort_by: sortBy" in src


def test_verticals_page_includes_enterprise_controls_impact_and_paging():
    src = (ROOT / "frontend/super-admin/app/admin/verticals/page.tsx").read_text(encoding="utf-8")
    assert 'resourceKey="admin_verticals"' in src
    assert "getDisableImpact" in src
    assert "page_size: pageSize" in src
    assert "reason.trim().length < 10" in src


def test_category_endpoint_pages_before_enrichment():
    src = (ROOT / "app/engines/admin_catalog/category_runtime_router.py").read_text(encoding="utf-8")
    pagination = src.index(".offset((page - 1) * page_size).limit(page_size)")
    enrichment = src.index("counts_map = await _linked_counts", pagination)
    assert pagination < enrichment
    assert 'bindparam("category_ids", expanding=True)' in src
    assert "id_list =" not in src
    assert "except Exception" not in src[:src.index("# ── Summary")]


def test_catalog_export_resources_are_runtime_supported():
    from app.engines.enterprise_grid.resource_adapters import is_runtime_supported
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry

    for key in ("admin_categories", "admin_verticals"):
        assert is_runtime_supported(key)
        assert EnterpriseFilterRegistry.get_config(key)["scope_type"] == "admin_global"


def test_architecture_records_two_aggregate_roots():
    src = (ROOT / "app/engines/admin_catalog/ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "Platform vertical registry" in src
    assert "Service runtime catalog" in src
    assert "filter/count/page in PostgreSQL" in src


def test_readiness_uses_package_definition_owner_not_assignment_usage_rows():
    src = (ROOT / "app/engines/admin_catalog/category_runtime_router.py").read_text(encoding="utf-8")
    assert "sp.vertical_type = service_categories.vertical_type" in src
    assert "tpa.category_id" not in src


def test_disable_requires_auditable_reason():
    src = (ROOT / "app/engines/vertical_catalog/admin_router.py").read_text(encoding="utf-8")
    assert "len(reason) < 10" in src
    assert "disable reason of at least 10 characters" in src


def test_category_runtime_detail_keeps_composite_contract():
    src = (ROOT / "app/engines/admin_catalog/category_runtime_router.py").read_text(encoding="utf-8")
    assert '"category": data' in src
    assert '"engine_summary":' in src
    assert '"dashboard_modules": modules' in src
    assert '"active_tenant_count":' in src
    assert "_vertical_engine_mappings" in src
    assert "_vertical_dashboard_modules" in src
    assert "vertical_catalog_modules" in src
    assert "cmd.navigation_status = 'available'" in src


def test_category_runtime_includes_home_services_runtime_engine_overlays():
    src = (ROOT / "app/engines/admin_catalog/category_runtime_router.py").read_text(encoding="utf-8")
    assert "HOME_SERVICES_RUNTIME_ENGINE_OVERLAYS" in src
    for engine in ("usage_credits", "commission", "customer_svc_credit", "pricing", "compliance", "audit", "settings_config"):
        assert f'"engine_key": "{engine}"' in src
    assert "vertical_registry+runtime_usage" in src


def test_category_runtime_includes_live_home_services_module_routes():
    src = (ROOT / "app/engines/admin_catalog/category_runtime_router.py").read_text(encoding="utf-8")
    assert "HOME_SERVICES_RUNTIME_MODULE_OVERLAYS" in src
    for route in (
        "/admin/home-services/providers",
        "/admin/home-services/bookings-jobs",
        "/admin/home-services/customers",
        "/admin/home-services/staff",
        "/admin/home-services/finance",
        "/admin/service-area-requests",
    ):
        assert route in src
    # Customer complaints/remedies are provider-owned.  The category runtime
    # must not resurrect the retired admin dispute surface.
    assert '"route_path": "/admin/home-services/complaints"' not in src
    assert "runtime_route" in src
    assert "if key in retired_keys:" in src
    assert "HOME_SERVICES_REGISTRY_MODULE_ENGINE_MAP" in src


def test_category_detail_page_exposes_connected_tabs():
    src = (ROOT / "frontend/super-admin/app/admin/categories/[id]/page.tsx").read_text(encoding="utf-8")
    for label in ("Readiness", "Catalog Links", "Engines", "Modules"):
        assert label in src
    assert "useSearchParams" in src
    assert "categoryRuntimeApi.getCategoryRuntime" in src
    assert "adminCustomerFlowApi.getFlowConfig" in src
    assert "catalogApi.getCategoryCommissionAuthority" in src


def test_category_detail_engine_and_module_tabs_are_filterable_and_sourced():
    src = (ROOT / "frontend/super-admin/app/admin/categories/[id]/page.tsx").read_text(encoding="utf-8")
    assert "Search engines..." in src
    assert "Search modules..." in src
    assert "runtime_reason" in src
    assert "module.source" in src
    assert "engine.source" in src


def test_vertical_release_filter_matches_canonical_seed_values():
    src = (ROOT / "frontend/super-admin/app/admin/verticals/page.tsx").read_text(encoding="utf-8")
    assert '<option value="production">Production</option>' in src
    assert '<option value="ga">' not in src
