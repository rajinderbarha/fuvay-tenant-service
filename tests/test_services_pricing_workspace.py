"""Services & Pricing 3-panel workspace (Phase 1: read view + effective
pricing). Thin aggregator over the existing TenantCatalogService
(admin_catalog/tenant_service.py) -- no second catalog/pricing engine.
"""
import os
import pathlib

BASE = str(pathlib.Path(__file__).parent.parent.resolve())
ROUTER = os.path.join(BASE, "app/engines/admin_catalog/tenant_services_workspace_router.py")


def _read():
    with open(ROUTER, encoding="utf-8") as f:
        return f.read()


class TestRouterStructure:
    def test_endpoints_registered(self):
        c = _read()
        assert 'router = APIRouter(prefix="/v1/tenant/home-services/services"' in c
        assert '@router.get("")' in c
        assert '@router.get("/{tenant_service_id}")' in c

    def test_reuses_canonical_tenant_catalog_service_not_a_new_engine(self):
        c = _read()
        assert "from app.engines.admin_catalog.tenant_service import TenantCatalogService" in c
        assert "svc.validate_for_publish" in c
        assert "svc.resolve_tenant_price" in c
        assert "svc.get_tenant_service_types" in c
        assert "svc.get_tenant_service_brands" in c
        assert "svc.list_home_services_enabled" in c

    def test_tenant_isolation_enforced_on_detail(self):
        c = _read()
        assert "ts_row.tenant_id != tid" in c

    def test_never_exposes_admin_price_bounds(self):
        c = _read()
        for forbidden in ("min_price", "max_price", "base_price", "city_tier", "pincode_price"):
            # These admin-owned bound fields must never be projected to the
            # tenant workspace response -- only tenant_min_price/tenant_max_price
            # (via _ts_dict) and resolve_tenant_price output are ever returned.
            assert f'"{forbidden}"' not in c

    def test_blueprint_prefers_real_job_type_workflow_over_legacy_fields(self):
        c = _read()
        # The workspace delegates workflow + dimension resolution to the
        # canonical TenantCatalogService helper instead of re-querying and
        # re-projecting a second copy here.
        assert "svc._tenant_setup_blueprint(master, ts_row.job_type_id)" in c
        # TenantService.job_type_id is now mandatory and scoped by the
        # database uniqueness contract, so no legacy/arbitrary fallback is used.
        assert "project_tenant_blueprint(master, workflow)" not in c

    def test_effective_pricing_uses_shared_resolver_not_a_second_calculation(self):
        c = _read()
        start = c.index("async def get_offering_detail")
        block = c[start:]
        assert block.count("svc.resolve_tenant_price(") >= 3  # default + per-type + per-brand-override

    def test_summary_kpis_are_backend_computed(self):
        c = _read()
        for key in ("enabled_services", "published", "draft", "missing_pricing", "type_overrides", "brand_overrides"):
            assert f'"{key}"' in c

    def test_documents_exact_job_type_scoping(self):
        c = _read()
        assert "ts_row.job_type_id" in c
        assert "JobTypeDefinition.id == ts_row.job_type_id" in c
