"""Canonical tenant Coverage & Hours connectivity guards."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "frontend/tenant-portal"
PAGE = (PORTAL / "app/(tenant)/business/coverage-hours/page.tsx").read_text(encoding="utf-8-sig")
WORKSPACE = (
    PORTAL / "app/(onboarding)/tenant/home-services/setup/coverage-availability/page.tsx"
).read_text(encoding="utf-8-sig")
API = (PORTAL / "lib/api.ts").read_text(encoding="utf-8-sig")
SERVICE = (ROOT / "app/engines/serviceability/service.py").read_text(encoding="utf-8-sig")
CATALOG = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")
NAV = (ROOT / "app/engines/tenant_engine/portal_router.py").read_text(encoding="utf-8-sig")


def test_single_canonical_coverage_route_remains():
    assert "CoverageAvailabilityWorkspace" in PAGE
    assert not (PORTAL / "app/(tenant)/provider/service-areas/page.tsx").exists()
    assert not (PORTAL / "app/(tenant)/service-areas/page.tsx").exists()


def test_workspace_uses_real_serviceability_api():
    assert "providerServiceAreasApi.list()" in WORKSPACE
    assert "providerServiceAreasApi.validate" in WORKSPACE
    assert "providerServiceAreasApi.create" in WORKSPACE
    assert "providerServiceAreasApi.delete" in WORKSPACE
    assert '"/v1/tenant/service-areas"' in API


def test_coverage_is_zipcode_first_and_validated():
    assert "Pincode" in WORKSPACE
    assert "providerServiceAreasApi.validate" in WORKSPACE
    assert "Enter 6-digit pincode" in WORKSPACE
    assert "package_limit_ok" in SERVICE
    assert "_check_duplicate_area" in SERVICE


def test_new_area_maps_all_published_tenant_services():
    create_block = SERVICE[SERVICE.index("async def create_service_area("):]
    assert "select(TenantService)" in create_block
    assert 'TenantService.setup_status == "published"' in create_block
    assert "TenantServiceAreaService(" in create_block


def test_publish_maps_service_to_all_active_areas():
    publish_block = CATALOG[CATALOG.index("async def publish_service("):]
    assert "select(TenantServiceArea.id)" in publish_block
    assert "TenantServiceAreaService(" in publish_block
    assert "existing_mapping.status = \"ACTIVE\"" in publish_block


def test_home_services_navigation_uses_only_canonical_coverage_route():
    hs = NAV[NAV.index('"home_services": ['):NAV.index('"coaching": [')]
    assert '"route": "/business/coverage-hours"' in hs
    assert "/provider/service-areas" not in hs
    assert '"route": "/service-areas"' not in hs
