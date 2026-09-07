"""Admin catalog -> tenant setup -> customer booking mapping contract."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TENANT_CATALOG = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")
OPTIONS = (ROOT / "app/engines/admin_catalog/service_option_service.py").read_text(encoding="utf-8-sig")
MODELS = (ROOT / "app/engines/admin_catalog/models.py").read_text(encoding="utf-8-sig")
CUSTOM_CATALOG = (ROOT / "app/engines/service_catalog/service.py").read_text(encoding="utf-8-sig")
MATCHER = (ROOT / "app/engines/home_service_booking/matching_engine.py").read_text(encoding="utf-8-sig")
PAGE = (
    ROOT / "frontend/tenant-portal/components/services/ServicesPricingPage.tsx"
).read_text(encoding="utf-8-sig")
MIGRATION = (ROOT / "alembic/versions/338_tenant_option_price_exact_mapping.py").read_text(encoding="utf-8-sig")


def test_customer_matcher_requires_exact_published_tenant_service():
    assert "TenantService.master_service_id == offering_id" in MATCHER
    assert "TenantService.job_type_id == job_type_id" in MATCHER
    assert 'TenantService.setup_status == "published"' in MATCHER
    assert "tenant_service_area_services" in MATCHER


def test_home_services_custom_catalog_is_rejected():
    assert 'vertical == "home_services"' in CUSTOM_CATALOG
    assert "HOME_SERVICES_MASTER_CATALOG_REQUIRED" in CUSTOM_CATALOG
    assert "home_services_uses_canonical_master_catalog" in CUSTOM_CATALOG


def test_tenant_service_options_are_exact_job_type_only():
    available = OPTIONS[OPTIONS.index("async def get_available_options_for_service"):]
    assert "if job_type_id is None:" in available
    assert "return []" in available
    assert "ServiceOptionMapping.job_type_id == job_type_id" in available
    assert "ServiceOptionMapping.tenant_selectable == True" in available


def test_tenant_cannot_price_an_option_for_an_unselected_service():
    setter = OPTIONS[OPTIONS.index("async def set_tenant_option_price"):]
    assert "TenantService.tenant_id == tenant_id" in setter
    assert "TenantService.master_service_id == mapping.master_service_id" in setter
    assert "TenantService.job_type_id == mapping.job_type_id" in setter
    assert "Enable this exact service and Job Type" in setter


def test_option_prices_are_unique_per_exact_mapping():
    assert "uq_tsso_tenant_mapping_active" in MODELS
    assert "service_option_mapping_id IS NOT NULL" in MODELS
    assert 'revision = "338"' in MIGRATION
    assert "uq_tsso_tenant_service_option" in MIGRATION
    assert "uq_tsso_tenant_mapping_active" in MIGRATION


def test_addons_no_longer_block_setup_and_publication_still_maps_coverage():
    assert "REQUIRED_SERVICE_OPTION_NOT_CONFIGURED" not in TENANT_CATALOG
    assert "REQUIRED_SERVICE_OPTION_PRICE_MISSING" not in TENANT_CATALOG
    assert "TenantServiceAreaService(" in TENANT_CATALOG


def test_canonical_services_workspace_removes_addon_setup():
    assert "ServiceOptionsTab" not in PAGE
    assert "getAvailableForService(masterServiceId, jobTypeId)" not in PAGE
    assert "setOptionPrice" not in PAGE
    assert "homeServicesSetupApi.publish" in PAGE
