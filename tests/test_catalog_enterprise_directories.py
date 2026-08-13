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


def test_vertical_release_filter_matches_canonical_seed_values():
    src = (ROOT / "frontend/super-admin/app/admin/verticals/page.tsx").read_text(encoding="utf-8")
    assert '<option value="production">Production</option>' in src
    assert '<option value="ga">' not in src
