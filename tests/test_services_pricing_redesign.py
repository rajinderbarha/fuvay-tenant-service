"""Regression coverage for the consolidated Services & Pricing workspace.

The operational workspace, onboarding setup, and Admin Catalog Workspace must
all resolve an offering by the same (master_service_id, job_type_id) identity.
"""
from pathlib import Path


BASE = Path(__file__).parent.parent
WORKSPACE_ROUTE = BASE / "frontend/tenant-portal/app/(tenant)/home-services/services/[[...serviceId]]/page.tsx"
ONBOARDING_ROUTE = BASE / "frontend/tenant-portal/app/(onboarding)/tenant/home-services/setup/services-pricing/page.tsx"
WORKSPACE = BASE / "frontend/tenant-portal/components/services/ServicesPricingPage.tsx"
ONBOARDING = BASE / "frontend/tenant-portal/components/services/ServicesPricingSetupPage.tsx"
SETUP = ONBOARDING
TENANT_SERVICE = BASE / "app/engines/admin_catalog/tenant_service.py"
WORKSPACE_ROUTER = BASE / "app/engines/admin_catalog/tenant_services_workspace_router.py"
WORKSPACE_API = BASE / "frontend/tenant-portal/lib/api-tenant-workspaces.ts"
COMPAT_ROUTE = BASE / "frontend/tenant-portal/app/(tenant)/home-services/servicesnow/page.tsx"
ADMIN_WORKSPACE = BASE / "frontend/super-admin/app/admin/catalog-workspace/page.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_workspace_filters_are_real_controls_and_have_a_clear_state():
    page = read(WORKSPACE)
    assert 'aria-label="Search services"' in page
    assert 'aria-label="Filter by service group"' in page
    assert 'aria-label="Filter by setup status"' in page
    assert "clearFilters" in page
    assert "visibleGroups" in page


def test_no_disabled_import_dead_action_and_guided_setup_route_exists():
    page = read(WORKSPACE)
    assert "Import pricing" not in page
    assert "/tenant/home-services/setup/services-pricing?return_to=" in page
    assert ONBOARDING_ROUTE.exists()


def test_add_service_filter_uses_master_service_and_job_type_pair():
    page = read(WORKSPACE)
    assert '`${service.master_service_id}:${service.job_type_id ?? ""}`' in page
    assert '`${service.service_id}:${service.job_type_id ?? ""}`' in page


def test_brand_override_writes_include_service_type_scope():
    page = read(WORKSPACE)
    assert "function BrandPricingRows" in page
    assert "setBrandPricing(tenantServiceId, args.brandId, args.min, args.max, serviceTypeId)" in page


def test_setup_surfaces_use_pair_identity_for_cards_and_enabled_rows():
    setup = read(SETUP)
    onboarding = read(ONBOARDING)
    assert "`${e.master_service_id}:${e.job_type_id}`" in setup
    assert "`${selectedService.service_id}:${selectedService.job_type_id}`" in setup
    assert 'enabledByMasterService.has(`${s.service_id}:${s.job_type_id}`)' in onboarding


def test_admin_options_flow_is_visible_in_tenant_requirements_projection():
    service = read(TENANT_SERVICE)
    admin = read(ADMIN_WORKSPACE)
    assert "list_service_option_mappings" in service
    assert '"service_options"' in service
    assert "function OptionsTab" in admin
    assert "job_type_id: jobTypeId" in admin


def test_old_servicesnow_link_redirects_to_the_single_canonical_workspace():
    assert not COMPAT_ROUTE.exists()


def test_route_layout_owns_the_tenant_shell_once():
    page = read(WORKSPACE_ROUTE)
    assert "import { TenantLayout }" not in page
    assert '<TenantLayout activeNav="provider-services">' not in page


def test_routes_are_thin_component_entry_points():
    workspace_route = read(WORKSPACE_ROUTE)
    onboarding_route = read(ONBOARDING_ROUTE)
    assert "<ServicesPricingPage />" in workspace_route
    assert "<ServicesPricingSetupPage />" in onboarding_route
    assert "useState" not in workspace_route
    assert "useState" not in onboarding_route


def test_tabs_and_filters_are_deep_linkable_query_state():
    page = read(WORKSPACE)
    assert "useSearchParams" in page
    assert 'searchParams.get("tab")' in page
    assert 'searchParams.get("q")' in page
    assert 'searchParams.get("status")' in page
    assert 'searchParams.get("group")' in page


def test_inspection_services_never_render_dimension_price_editors():
    page = read(WORKSPACE)
    service = read(TENANT_SERVICE)
    router = read(WORKSPACE_ROUTER)
    assert "INSPECTION_PRICING_BEHAVIORS" in page
    assert 'pricingMode === "dimension"' in page
    assert "DIMENSION_PRICING_NOT_APPLICABLE" in service
    assert "dimension_pricing_applies" in router
    assert "INSPECTION_ESTIMATE_WORKFLOW" in router


def test_workspace_visibility_and_attention_derive_from_publish_validation():
    page = read(WORKSPACE)
    router = read(WORKSPACE_ROUTER)
    api = read(WORKSPACE_API)
    assert '"readiness_ready": validation["valid"]' in router
    assert '"customer_visible": s["setup_status"] == "published" and validation["valid"]' in router
    assert "service.customer_visible" in page
    assert "!service.readiness_ready" in page
    assert "customer_visible: boolean" in api


def test_missing_pricing_kpi_includes_each_active_pricing_model():
    router = read(WORKSPACE_ROUTER)
    for code in (
        "MISSING_TENANT_PRICE", "MISSING_VISIT_FEE", "MISSING_CONSULTATION_FEE",
        "INCOMPLETE_TYPE_PRICE_OVERRIDE", "INCOMPLETE_BRAND_PRICE_OVERRIDE",
    ):
        assert code in router


def test_setup_and_operational_workspace_share_mutation_api():
    page = read(WORKSPACE)
    onboarding = read(ONBOARDING)
    api = read(WORKSPACE_API)
    assert "homeServicesSetupApi" in page
    assert "homeServicesSetupApi" in onboarding
    assert "/v1/tenant/home-services/services" in api
    for method in ("getAvailableTypes", "getAvailableBrands", "updateEnabledService", "publish"):
        assert f"homeServicesSetupApi.{method}" in page


def test_setup_price_ranges_never_autosave_empty_fields_as_zero():
    onboarding = read(ONBOARDING)
    assert "Number(min || 0)" not in onboarding
    assert "Number(max || 0)" not in onboarding
    assert "onBlur={() => onSave(localMin, localMax)}" not in onboarding
    assert "Save ${label} price range" in onboarding
    assert "minValue <= 0" in onboarding
