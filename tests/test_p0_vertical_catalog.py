"""Tests for P0 Multi-Vertical Catalog Architecture (migration 089).

Coverage:
  - migration file existence and revision
  - ORM model table names and columns
  - VerticalCatalogService methods (mocked DB)
  - admin_router endpoints (happy path + error paths)
  - main.py router registration
  - api.ts types and method presence
  - frontend page existence
"""
from __future__ import annotations

import ast
import importlib
import os
import sys
import types
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

ROOT = Path(__file__).parent.parent

# ── Helpers ────────────────────────────────────────────────────────────────────

def _ts_source() -> str:
    return (ROOT / "frontend" / "super-admin" / "lib" / "api.ts").read_text(encoding="utf-8")


def _layout_source() -> str:
    return (ROOT / "frontend" / "super-admin" / "components" / "layout" / "AdminLayout.tsx").read_text(encoding="utf-8")


def _make_vertical(**kwargs) -> MagicMock:
    v = MagicMock()
    defaults = {
        "id": uuid.uuid4(), "key": "home_services", "label": "Home Services",
        "description": None, "icon": "Wrench", "color": "#2563eb",
        "is_enabled": True, "is_beta": False, "sort_order": 1,
        "finance_model": "commission", "meta": None,
    }
    defaults.update(kwargs)
    for k, val in defaults.items():
        setattr(v, k, val)
    return v


def _make_module(**kwargs) -> MagicMock:
    m = MagicMock()
    defaults = {
        "id": uuid.uuid4(), "key": "categories", "label": "Categories",
        "icon": "Layers", "admin_path": "/admin/categories",
        "module_group": "services", "is_universal": True, "sort_order": 1,
        "description": None, "navigation_status": "available",
        "navigation_status_reason": None,
    }
    defaults.update(kwargs)
    for k, val in defaults.items():
        setattr(m, k, val)
    return m


# ══════════════════════════════════════════════════════════════════════════════
# 1. Migration
# ══════════════════════════════════════════════════════════════════════════════

def test_migration_089_exists():
    migration = ROOT / "alembic" / "versions" / "089_multi_vertical_catalog_architecture.py"
    assert migration.exists(), "Migration 089 not found"


def test_migration_089_revision():
    migration = ROOT / "alembic" / "versions" / "089_multi_vertical_catalog_architecture.py"
    src = migration.read_text()
    assert 'revision = "089"' in src
    assert 'down_revision = "088"' in src


def test_migration_089_creates_verticals_table():
    src = (ROOT / "alembic" / "versions" / "089_multi_vertical_catalog_architecture.py").read_text()
    assert '"verticals"' in src


def test_migration_089_creates_catalog_module_definitions():
    src = (ROOT / "alembic" / "versions" / "089_multi_vertical_catalog_architecture.py").read_text()
    assert '"catalog_module_definitions"' in src


def test_migration_089_creates_vertical_catalog_modules():
    src = (ROOT / "alembic" / "versions" / "089_multi_vertical_catalog_architecture.py").read_text()
    assert '"vertical_catalog_modules"' in src


def test_migration_089_creates_vertical_menu_config():
    src = (ROOT / "alembic" / "versions" / "089_multi_vertical_catalog_architecture.py").read_text()
    assert '"vertical_menu_config"' in src


def test_migration_089_seeds_verticals():
    src = (ROOT / "alembic" / "versions" / "089_multi_vertical_catalog_architecture.py").read_text()
    assert "home_services" in src
    assert "coaching" in src
    assert "real_estate" in src
    assert "beauty" in src


def test_migration_089_seeds_7_verticals():
    src = (ROOT / "alembic" / "versions" / "089_multi_vertical_catalog_architecture.py").read_text()
    expected = ["home_services", "coaching", "real_estate", "beauty",
                "restaurant", "product_marketplace", "professional_services"]
    for v in expected:
        assert v in src, f"Vertical {v} missing from migration seed"


def test_migration_089_has_downgrade():
    src = (ROOT / "alembic" / "versions" / "089_multi_vertical_catalog_architecture.py").read_text()
    assert "def downgrade" in src
    assert "drop_table" in src


# ══════════════════════════════════════════════════════════════════════════════
# 2. ORM Models
# ══════════════════════════════════════════════════════════════════════════════

def test_vertical_model_tablename():
    from app.engines.vertical_catalog.models import Vertical
    assert Vertical.__tablename__ == "verticals"


def test_vertical_model_key_column():
    from app.engines.vertical_catalog.models import Vertical
    assert hasattr(Vertical, "key")


def test_vertical_model_is_enabled_column():
    from app.engines.vertical_catalog.models import Vertical
    assert hasattr(Vertical, "is_enabled")


def test_vertical_model_finance_model_column():
    from app.engines.vertical_catalog.models import Vertical
    assert hasattr(Vertical, "finance_model")


def test_catalog_module_definition_tablename():
    from app.engines.vertical_catalog.models import CatalogModuleDefinition
    assert CatalogModuleDefinition.__tablename__ == "catalog_module_definitions"


def test_catalog_module_definition_is_universal_column():
    from app.engines.vertical_catalog.models import CatalogModuleDefinition
    assert hasattr(CatalogModuleDefinition, "is_universal")


def test_catalog_module_definition_admin_path_column():
    from app.engines.vertical_catalog.models import CatalogModuleDefinition
    assert hasattr(CatalogModuleDefinition, "admin_path")


def test_vertical_catalog_module_tablename():
    from app.engines.vertical_catalog.models import VerticalCatalogModule
    assert VerticalCatalogModule.__tablename__ == "vertical_catalog_modules"


def test_vertical_catalog_module_is_required_column():
    from app.engines.vertical_catalog.models import VerticalCatalogModule
    assert hasattr(VerticalCatalogModule, "is_required")


def test_vertical_menu_config_tablename():
    from app.engines.vertical_catalog.models import VerticalMenuConfig
    assert VerticalMenuConfig.__tablename__ == "vertical_menu_config"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Service
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_service_list_verticals_filters_disabled():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    svc = VerticalCatalogService()
    db = MagicMock()
    v1 = _make_vertical(is_enabled=True, sort_order=0)
    v2 = _make_vertical(key="coaching", is_enabled=False, sort_order=1)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [v1]
    db.execute = AsyncMock(return_value=result)
    items = await svc.list_verticals(db, include_disabled=False)
    assert all(i["is_enabled"] for i in items)


@pytest.mark.asyncio
async def test_service_list_verticals_include_disabled():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    svc = VerticalCatalogService()
    db = MagicMock()
    v1 = _make_vertical(is_enabled=True)
    v2 = _make_vertical(key="coaching", is_enabled=False)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [v1, v2]
    db.execute = AsyncMock(return_value=result)
    items = await svc.list_verticals(db, include_disabled=True)
    assert len(items) == 2


@pytest.mark.asyncio
async def test_service_enable_vertical():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    svc = VerticalCatalogService()
    db = MagicMock()
    v = _make_vertical(is_enabled=False)
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = v
    db.execute = AsyncMock(return_value=find_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    result = await svc.enable_vertical(db, "home_services")
    assert v.is_enabled is True


@pytest.mark.asyncio
async def test_service_disable_vertical():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    svc = VerticalCatalogService()
    db = MagicMock()
    v = _make_vertical(is_enabled=True)
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = v
    db.execute = AsyncMock(return_value=find_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    await svc.disable_vertical(db, "home_services")
    assert v.is_enabled is False


@pytest.mark.asyncio
async def test_service_enable_vertical_not_found():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    svc = VerticalCatalogService()
    db = MagicMock()
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=find_result)
    with pytest.raises(ValueError, match="not found"):
        await svc.enable_vertical(db, "nonexistent")


@pytest.mark.asyncio
async def test_service_update_vertical():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    svc = VerticalCatalogService()
    db = MagicMock()
    v = _make_vertical()
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = v
    db.execute = AsyncMock(return_value=find_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    await svc.update_vertical(db, "home_services", {"label": "Updated Label"})
    assert v.label == "Updated Label"


@pytest.mark.asyncio
async def test_service_update_vertical_ignores_unknown_fields():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    svc = VerticalCatalogService()
    db = MagicMock()
    v = _make_vertical()
    find_result = MagicMock()
    find_result.scalar_one_or_none.return_value = v
    db.execute = AsyncMock(return_value=find_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    # Should not raise even with unknown field
    await svc.update_vertical(db, "home_services", {"some_unknown_field": "x"})


@pytest.mark.asyncio
async def test_service_toggle_module_required_cannot_disable():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    from app.engines.vertical_catalog.models import VerticalCatalogModule
    svc = VerticalCatalogService()
    db = MagicMock()
    v = _make_vertical()
    m = _make_module()
    vcm = MagicMock()
    vcm.is_required = True
    vcm.is_enabled = True

    def _execute_side(q, *a, **kw):
        res = MagicMock()
        if hasattr(q, "whereclause"):
            res.scalar_one_or_none.return_value = vcm
        else:
            res.scalar_one_or_none.return_value = v if "Vertical" in str(q) else m
        return res

    # First call = find vertical, second = find module, third = find vcm
    find_v = MagicMock(); find_v.scalar_one_or_none.return_value = v
    find_m = MagicMock(); find_m.scalar_one_or_none.return_value = m
    find_vcm = MagicMock(); find_vcm.scalar_one_or_none.return_value = vcm
    db.execute = AsyncMock(side_effect=[find_v, find_m, find_vcm])

    with pytest.raises(ValueError, match="cannot be disabled"):
        await svc.toggle_module(db, "home_services", "categories", False)


@pytest.mark.asyncio
async def test_service_list_modules_returns_all():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    svc = VerticalCatalogService()
    db = MagicMock()
    mods = [_make_module(key=f"mod_{i}") for i in range(5)]
    result = MagicMock()
    result.scalars.return_value.all.return_value = mods
    db.execute = AsyncMock(return_value=result)
    items = await svc.list_modules(db)
    assert len(items) == 5


# ══════════════════════════════════════════════════════════════════════════════
# 4. Router
# ══════════════════════════════════════════════════════════════════════════════

def test_router_file_exists():
    assert (ROOT / "app" / "engines" / "vertical_catalog" / "admin_router.py").exists()


def test_router_has_list_verticals_endpoint():
    src = (ROOT / "app" / "engines" / "vertical_catalog" / "admin_router.py").read_text()
    assert "list_verticals" in src


def test_router_has_get_vertical_endpoint():
    src = (ROOT / "app" / "engines" / "vertical_catalog" / "admin_router.py").read_text()
    assert "get_vertical" in src


def test_router_has_enable_disable_endpoints():
    src = (ROOT / "app" / "engines" / "vertical_catalog" / "admin_router.py").read_text()
    assert "enable_vertical" in src
    assert "disable_vertical" in src


def test_router_has_module_toggle_endpoints():
    src = (ROOT / "app" / "engines" / "vertical_catalog" / "admin_router.py").read_text()
    assert "enable_vertical_module" in src
    assert "disable_vertical_module" in src


def test_router_has_effective_menu_endpoint():
    src = (ROOT / "app" / "engines" / "vertical_catalog" / "admin_router.py").read_text()
    assert "get_effective_menu" in src


def test_router_uses_require_super_admin_for_writes():
    # Superseded by the P0 Multi-Vertical Catalog Menu Fix: writes are now gated by
    # granular P.VERTICALS_*/P.NAVIGATION_MENU_* permissions (super_admin still passes
    # via its P.ALL wildcard) rather than a bare require_super_admin dependency.
    src = (ROOT / "app" / "engines" / "vertical_catalog" / "admin_router.py").read_text()
    assert "require_permission" in src


def test_router_prefix():
    src = (ROOT / "app" / "engines" / "vertical_catalog" / "admin_router.py").read_text()
    assert 'prefix="/v1/admin/verticals"' in src


def test_modules_router_prefix():
    src = (ROOT / "app" / "engines" / "vertical_catalog" / "admin_router.py").read_text()
    assert 'prefix="/v1/admin/catalog"' in src


def test_router_returns_ok_response():
    src = (ROOT / "app" / "engines" / "vertical_catalog" / "admin_router.py").read_text()
    assert "ok(" in src


# ══════════════════════════════════════════════════════════════════════════════
# 5. main.py wiring
# ══════════════════════════════════════════════════════════════════════════════

def test_main_py_includes_verticals_router():
    src = (ROOT / "app" / "main.py").read_text()
    assert "vertical_catalog" in src
    assert "verticals_router" in src


def test_main_py_includes_catalog_modules_router():
    src = (ROOT / "app" / "main.py").read_text()
    assert "catalog_modules_router" in src


# ══════════════════════════════════════════════════════════════════════════════
# 6. TypeScript api.ts
# ══════════════════════════════════════════════════════════════════════════════

def test_api_ts_has_vertical_item_interface():
    assert "VerticalItem" in _ts_source()


def test_api_ts_has_catalog_module_item_interface():
    assert "CatalogModuleItem" in _ts_source()


def test_api_ts_has_vertical_module_item_interface():
    assert "VerticalModuleItem" in _ts_source()


def test_api_ts_has_vertical_detail_interface():
    assert "VerticalDetail" in _ts_source()


def test_api_ts_has_effective_menu_interface():
    assert "EffectiveMenu" in _ts_source()


def test_api_ts_has_vertical_catalog_api():
    assert "verticalCatalogApi" in _ts_source()


def test_api_ts_has_list_verticals():
    assert "listVerticals" in _ts_source()


def test_api_ts_has_get_vertical():
    assert "getVertical" in _ts_source()


def test_api_ts_has_enable_disable_vertical():
    src = _ts_source()
    assert "enableVertical" in src
    assert "disableVertical" in src


def test_api_ts_has_module_toggles():
    src = _ts_source()
    assert "enableModule" in src
    assert "disableModule" in src


def test_api_ts_has_get_effective_menu():
    assert "getEffectiveMenu" in _ts_source()


# ══════════════════════════════════════════════════════════════════════════════
# 7. AdminLayout sidebar
# ══════════════════════════════════════════════════════════════════════════════

def test_layout_imports_vertical_catalog_api():
    assert "verticalCatalogApi" in _layout_source()


def test_layout_has_effective_menu_state():
    assert "effectiveMenu" in _layout_source()


def test_layout_fetches_effective_menu_on_mount():
    src = _layout_source()
    assert "getEffectiveMenu" in src


def test_layout_has_vertical_catalog_section_component():
    assert "VerticalCatalogSection" in _layout_source()


def test_layout_catalog_group_includes_verticals_link():
    src = _layout_source()
    assert '"/admin/verticals"' in src or "admin/verticals" in src


def test_layout_renders_per_vertical_sub_menus():
    src = _layout_source()
    assert "verticals.filter" in src or "effectiveMenu.verticals" in src


def test_layout_has_globe_icon_import():
    assert "Globe" in _layout_source()


# ══════════════════════════════════════════════════════════════════════════════
# 8. Frontend pages
# ══════════════════════════════════════════════════════════════════════════════

def test_verticals_page_exists():
    p = ROOT / "frontend" / "super-admin" / "app" / "admin" / "verticals" / "page.tsx"
    assert p.exists(), "/admin/verticals page not found"


def test_verticals_page_uses_vertical_catalog_api():
    src = (ROOT / "frontend" / "super-admin" / "app" / "admin" / "verticals" / "page.tsx").read_text()
    assert "verticalCatalogApi" in src


def test_verticals_page_has_enable_disable_actions():
    src = (ROOT / "frontend" / "super-admin" / "app" / "admin" / "verticals" / "page.tsx").read_text()
    assert "enableVertical" in src or "enable" in src.lower()
    assert "disableVertical" in src or "disable" in src.lower()


def test_verticals_page_has_module_toggle():
    src = (ROOT / "frontend" / "super-admin" / "app" / "admin" / "verticals" / "page.tsx").read_text()
    assert "enableModule" in src or "disableModule" in src


def test_verticals_page_has_admin_layout():
    src = (ROOT / "frontend" / "super-admin" / "app" / "admin" / "verticals" / "page.tsx").read_text()
    assert "AdminLayout" in src


def test_per_vertical_catalog_page_exists():
    p = ROOT / "frontend" / "super-admin" / "app" / "admin" / "catalog" / "[vertical]" / "page.tsx"
    assert p.exists(), "/admin/catalog/[vertical] page not found"


def test_per_vertical_catalog_page_uses_api():
    src = (ROOT / "frontend" / "super-admin" / "app" / "admin" / "catalog" / "[vertical]" / "page.tsx").read_text()
    assert "verticalCatalogApi" in src


def test_per_vertical_catalog_page_has_module_cards():
    src = (ROOT / "frontend" / "super-admin" / "app" / "admin" / "catalog" / "[vertical]" / "page.tsx").read_text()
    assert "ModuleCard" in src or "module" in src.lower()


def test_per_vertical_catalog_page_groups_modules_by_section():
    src = (ROOT / "frontend" / "super-admin" / "app" / "admin" / "catalog" / "[vertical]" / "page.tsx").read_text()
    assert "module_group" in src or "group" in src.lower()


def test_per_vertical_catalog_page_has_admin_layout():
    src = (ROOT / "frontend" / "super-admin" / "app" / "admin" / "catalog" / "[vertical]" / "page.tsx").read_text()
    assert "AdminLayout" in src


# ══════════════════════════════════════════════════════════════════════════════
# 9. Service v_dict / mod_dict helpers
# ══════════════════════════════════════════════════════════════════════════════

def test_service_v_dict_contains_expected_keys():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    svc = VerticalCatalogService()
    v = _make_vertical()
    d = svc._v_dict(v)
    for key in ("id", "key", "label", "is_enabled", "is_beta", "sort_order", "finance_model"):
        assert key in d, f"Key '{key}' missing from _v_dict"


def test_service_mod_dict_contains_expected_keys():
    from app.engines.vertical_catalog.service import VerticalCatalogService
    svc = VerticalCatalogService()
    m = _make_module()
    d = svc._mod_dict(m)
    for key in ("id", "key", "label", "icon", "admin_path", "is_universal", "sort_order"):
        assert key in d, f"Key '{key}' missing from _mod_dict"
