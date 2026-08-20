"""Regression coverage for the vertical admin-navigation control plane."""
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_module_lifecycle_migration_classifies_retired_and_unbuilt_routes():
    source = (ROOT / "alembic/versions/253_vertical_module_navigation_lifecycle.py").read_text(encoding="utf-8")
    for key in ("brands", "issue_types", "pricing_rules", "hs_completed_job_deduction"):
        assert f'"{key}"' in source
    for key in ("courses", "menu_items", "products", "consultation_types"):
        assert f'"{key}"' in source
    assert "is_required = false" in source


def test_current_module_scope_migration_repairs_stale_live_rows():
    source = (ROOT / "alembic/versions/276_vertical_catalog_current_module_scope.py").read_text(encoding="utf-8")
    for key in ("categories", "service_groups", "master_services", "types_brands", "checklist_templates", "hs_service_catalog"):
        assert f'"{key}"' in source
    for key in ("brands", "issue_types", "pricing_rules", "hs_completed_job_deduction"):
        assert f'"{key}"' in source
    assert "navigation_status <> 'available'" in source
    assert "No production admin workspace is implemented" in source


def test_admin_client_uses_real_vertical_diagnostic_endpoints():
    source = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
    assert "/capabilities`" in source
    assert "/dependency-health`" in source
    assert "/audit?limit=${limit}`" in source
    assert "Dependency health is not yet available for verticals" not in source
    assert "Audit history is not yet available for verticals" not in source


def test_module_manager_describes_navigation_scope_and_requires_reason():
    source = (ROOT / "frontend/super-admin/app/admin/verticals/page.tsx").read_text(encoding="utf-8")
    assert "only control current pages shown in the super-admin sidebar" in source
    assert "do not enable or disable tenant entitlements" in source
    assert "reason.trim().length < 10" in source
    assert 'allModules.filter(module => module.navigation_status === "available")' in source
    assert "retired or unavailable hidden" in source


def test_category_page_does_not_present_effective_commission_as_owned_metric():
    source = (ROOT / "frontend/super-admin/app/admin/categories/[id]/page.tsx").read_text(encoding="utf-8")
    assert 'label="Effective commission"' not in source
    assert 'label="Resolved charge source"' in source
    assert 'label="Vertical default"' not in source
    assert 'label="Category override"' not in source
    assert 'label="Resolved percentage"' not in source


def test_toggle_service_audits_navigation_changes_and_blocks_cross_assignment():
    source = (ROOT / "app/engines/vertical_catalog/service.py").read_text(encoding="utf-8")
    assert "vertical.navigation_module.enable" in source
    assert "vertical.navigation_module.disable" in source
    assert "is not assigned to vertical" in source
    assert "navigation_status != \"available\"" in source


def test_effective_menu_defensively_filters_unavailable_modules():
    source = (ROOT / "app/engines/vertical_catalog/service.py").read_text(encoding="utf-8")
    assert 'm["is_enabled"] and m["navigation_status"] == "available"' in source
    assert 'm["is_universal"] and m["navigation_status"] == "available"' in source


def test_vertical_dependency_registry_is_seeded_for_each_vertical():
    source = (ROOT / "alembic/versions/254_seed_vertical_engine_mappings.py").read_text(encoding="utf-8")
    for vertical in ("home_services", "coaching", "real_estate", "beauty", "restaurant", "product_marketplace", "professional_services"):
        assert f'"{vertical}"' in source
    for engine in ("service_catalog", "booking", "job_dispatch", "finance", "payment", "notification"):
        assert f'"{engine}"' in source
    assert "ON CONFLICT (vertical_id, engine_key) DO UPDATE" in source


def test_locked_core_engine_is_not_misreported_as_unhealthy():
    source = (ROOT / "app/engines/vertical_catalog/service.py").read_text(encoding="utf-8")
    assert 'engine.global_status not in ("enabled", "locked")' in source
