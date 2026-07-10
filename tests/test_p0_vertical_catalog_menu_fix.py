"""
P0 Multi-Vertical Catalog Architecture + Admin Menu Refactor — test suite
Static source-inspection style, consistent with test_p0_settings_enterprise.py /
test_p0_customers_enterprise.py conventions in this repo — no live DB fixture required.
"""
import os

ROOT           = os.path.dirname(os.path.dirname(__file__))
MODELS         = os.path.join(ROOT, "app", "engines", "vertical_catalog", "models.py")
SERVICE        = os.path.join(ROOT, "app", "engines", "vertical_catalog", "service.py")
ADMIN_ROUTER   = os.path.join(ROOT, "app", "engines", "vertical_catalog", "admin_router.py")
PERMISSIONS    = os.path.join(ROOT, "app", "core", "permissions.py")
MIGRATION_090  = os.path.join(ROOT, "alembic", "versions", "090_vertical_catalog_module_fix.py")
MIGRATION_091  = os.path.join(ROOT, "alembic", "versions", "091_fix_vertical_catalog_updated_at.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migration 090 — the actual bug fix ──────────────────────────────────────

def test_migration_090_exists():
    assert os.path.exists(MIGRATION_090)


def test_migration_090_revision_chain():
    src = _read(MIGRATION_090)
    assert 'revision = "090"' in src
    assert 'down_revision = "089"' in src


def test_migration_090_adds_coaching_specific_modules():
    src = _read(MIGRATION_090)
    for key in ("courses", "batches", "demo_classes", "counselors", "lead_forms", "fee_plans"):
        assert f'"{key}"' in src


def test_migration_090_adds_real_estate_specific_modules():
    src = _read(MIGRATION_090)
    for key in ("property_types", "listing_types", "amenities", "localities", "site_visit_workflows"):
        assert f'"{key}"' in src


def test_migration_090_adds_restaurant_specific_modules():
    src = _read(MIGRATION_090)
    for key in ("menu_categories", "menu_items", "item_variants", "addons", "cuisine_types"):
        assert f'"{key}"' in src


def test_migration_090_adds_product_marketplace_modules():
    src = _read(MIGRATION_090)
    for key in ("product_categories", "products", "product_variants", "attributes", "inventory_rules"):
        assert f'"{key}"' in src


def test_migration_090_adds_professional_services_modules():
    src = _read(MIGRATION_090)
    for key in ("consultation_types", "document_requirements", "appointment_types", "subscription_plans"):
        assert f'"{key}"' in src


def test_migration_090_coaching_assignment_excludes_home_services_modules():
    """The actual P0 bug: Coaching must NOT be assigned brands/issue_types/service_options."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("migration_090", MIGRATION_090)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    coaching_modules = mod.NEW_ASSIGNMENTS["coaching"]
    for bad in ("brands", "brand_requests", "issue_types", "service_options", "types_brands"):
        assert bad not in coaching_modules, f"Coaching must not include Home-Services module '{bad}'"
    assert "courses" in coaching_modules
    assert "batches" in coaching_modules


def test_migration_090_real_estate_assignment_excludes_home_services_modules():
    import importlib.util
    spec = importlib.util.spec_from_file_location("migration_090b", MIGRATION_090)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    re_modules = mod.NEW_ASSIGNMENTS["real_estate"]
    for bad in ("brands", "brand_requests", "issue_types", "service_options", "types_brands"):
        assert bad not in re_modules, f"Real Estate must not include Home-Services module '{bad}'"
    assert "property_types" in re_modules
    assert "amenities" in re_modules


def test_migration_090_home_services_untouched():
    """home_services keeps its full original module set — not in NEW_ASSIGNMENTS at all."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("migration_090c", MIGRATION_090)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "home_services" not in mod.NEW_ASSIGNMENTS


def test_migration_090_creates_vertical_engine_mappings_table():
    src = _read(MIGRATION_090)
    assert '"vertical_engine_mappings"' in src
    assert "engine_key" in src


def test_migration_090_module_admin_paths_point_to_placeholder():
    src = _read(MIGRATION_090)
    assert "/admin/catalog-module/" in src


# ── Migration 091 — the updated_at bug fix ──────────────────────────────────

def test_migration_091_exists():
    assert os.path.exists(MIGRATION_091)


def test_migration_091_fixes_missing_updated_at():
    src = _read(MIGRATION_091)
    assert "catalog_module_definitions" in src
    assert "vertical_catalog_modules" in src
    assert "updated_at" in src


# ── models.py ─────────────────────────────────────────────────────────────────

def test_models_importable():
    import importlib
    mod = importlib.import_module("app.engines.vertical_catalog.models")
    assert hasattr(mod, "VerticalEngineMapping")


def test_vertical_engine_mapping_model_fields():
    src = _read(MODELS)
    assert "class VerticalEngineMapping(" in src
    assert "engine_key" in src
    assert "is_required" in src


# ── service.py ────────────────────────────────────────────────────────────────

def test_service_importable():
    import importlib
    mod = importlib.import_module("app.engines.vertical_catalog.service")
    assert hasattr(mod, "VerticalCatalogService")


def test_service_has_engine_mapping_methods():
    src = _read(SERVICE)
    assert "async def list_engine_mappings" in src
    assert "async def set_engine_mappings" in src


# ── admin_router.py ──────────────────────────────────────────────────────────

def test_admin_router_importable():
    import importlib
    mod = importlib.import_module("app.engines.vertical_catalog.admin_router")
    assert hasattr(mod, "router")
    assert hasattr(mod, "modules_router")


def test_admin_router_no_longer_uses_bare_require_super_admin():
    """Writes must be gated by granular P.VERTICALS_*/P.NAVIGATION_MENU_* permissions,
    not just require_super_admin/get_current_user (the original state)."""
    src = _read(ADMIN_ROUTER)
    assert "require_permission" in src
    assert "from app.core.permissions import P, require_permission" in src


def test_admin_router_has_engine_mapping_endpoints():
    src = _read(ADMIN_ROUTER)
    assert '"/{vertical_key}/engine-mappings"' in src


def test_admin_router_permission_guarded():
    src = _read(ADMIN_ROUTER)
    for perm in ("P.VERTICALS_READ", "P.VERTICALS_ENABLE", "P.VERTICALS_DISABLE",
                 "P.VERTICALS_UPDATE", "P.NAVIGATION_MENU_READ"):
        assert perm in src


# ── permissions.py ───────────────────────────────────────────────────────────

def test_permissions_verticals_constants_exist():
    src = _read(PERMISSIONS)
    for const in ("VERTICALS_READ", "VERTICALS_CREATE", "VERTICALS_UPDATE",
                  "VERTICALS_ENABLE", "VERTICALS_DISABLE"):
        assert const in src


def test_permissions_per_vertical_catalog_constants_exist():
    src = _read(PERMISSIONS)
    for const in ("CATALOG_HOME_SERVICES_READ", "CATALOG_COACHING_READ",
                  "CATALOG_REAL_ESTATE_READ", "CATALOG_RESTAURANT_READ",
                  "CATALOG_PRODUCTS_READ", "CATALOG_PROFESSIONAL_SERVICES_READ"):
        assert const in src


def test_permissions_navigation_menu_constants_exist():
    src = _read(PERMISSIONS)
    assert "NAVIGATION_MENU_READ" in src
    assert "NAVIGATION_MENU_UPDATE" in src
