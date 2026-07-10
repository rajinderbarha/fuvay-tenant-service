"""Tests for P0 Enterprise Service Setup Templates (migration 091).

Coverage:
  - migration file existence and tables
  - ORM model table names and columns
  - SetupTemplatesService methods (mocked DB)
  - templates_router endpoints
  - main.py router registration
  - api.ts types and method presence
  - frontend page existence
"""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).parent.parent


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ts_source() -> str:
    return (ROOT / "frontend" / "super-admin" / "lib" / "api.ts").read_text(encoding="utf-8")


def _make_template(**kwargs) -> MagicMock:
    t = MagicMock()
    uid = uuid.uuid4()
    defaults = {
        "id": uid,
        "name": "Test Template",
        "code": "test_template",
        "description": "A test template",
        "vertical_key": "universal",
        "template_type": "starter_pack",
        "is_system": False,
        "status": "draft",
        "version": 1,
        "display_order": 0,
        "config_json": None,
        "created_by_user_id": None,
        "archived_at": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(t, k, v)
    t.to_dict.return_value = {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in defaults.items()}
    return t


def _make_module(**kwargs) -> MagicMock:
    m = MagicMock()
    uid = uuid.uuid4()
    defaults = {
        "id": uid, "template_id": uuid.uuid4(),
        "module_key": "service_groups", "module_name": "Service Groups",
        "is_enabled": True, "config_json": None, "display_order": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(m, k, v)
    m.to_dict.return_value = {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in defaults.items()}
    return m


def _make_item(**kwargs) -> MagicMock:
    it = MagicMock()
    uid = uuid.uuid4()
    defaults = {
        "id": uid, "template_id": uuid.uuid4(),
        "module_key": "service_groups", "item_type": "service_groups",
        "item_key": "ac_services", "item_name": "AC Services",
        "parent_item_key": None, "payload_json": {}, "display_order": 0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(it, k, v)
    it.to_dict.return_value = {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in defaults.items()}
    return it


def _db_with_scalar(value):
    """DB mock that returns a scalar result."""
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value if isinstance(value, int) else 0
    result.scalars.return_value.all.return_value = [value] if value is not None else []
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    return db


# ══════════════════════════════════════════════════════════════════════════════
# 1. Migration
# ══════════════════════════════════════════════════════════════════════════════

def test_migration_097_exists():
    migration = ROOT / "alembic" / "versions" / "097_service_setup_templates_enterprise.py"
    assert migration.exists(), "Migration 097 not found"


def test_migration_097_revision():
    src = (ROOT / "alembic" / "versions" / "097_service_setup_templates_enterprise.py").read_text()
    assert 'revision = "097"' in src
    assert 'down_revision = "096"' in src


def test_migration_097_creates_service_setup_templates():
    src = (ROOT / "alembic" / "versions" / "097_service_setup_templates_enterprise.py").read_text()
    assert '"service_setup_templates"' in src


def test_migration_097_creates_template_modules():
    src = (ROOT / "alembic" / "versions" / "097_service_setup_templates_enterprise.py").read_text()
    assert '"service_setup_template_modules"' in src


def test_migration_097_creates_template_items():
    src = (ROOT / "alembic" / "versions" / "097_service_setup_templates_enterprise.py").read_text()
    assert '"service_setup_template_items"' in src


def test_migration_097_creates_template_versions():
    src = (ROOT / "alembic" / "versions" / "097_service_setup_templates_enterprise.py").read_text()
    assert '"service_setup_template_versions"' in src


def test_migration_097_creates_template_usage():
    src = (ROOT / "alembic" / "versions" / "097_service_setup_templates_enterprise.py").read_text()
    assert '"service_setup_template_usage"' in src


def test_migration_097_has_downgrade():
    src = (ROOT / "alembic" / "versions" / "097_service_setup_templates_enterprise.py").read_text()
    assert "def downgrade" in src
    assert "drop_table" in src


# ══════════════════════════════════════════════════════════════════════════════
# 2. ORM Models
# ══════════════════════════════════════════════════════════════════════════════

def test_setup_template_tablename():
    from app.engines.service_setup.models import ServiceSetupTemplate
    assert ServiceSetupTemplate.__tablename__ == "service_setup_templates"


def test_setup_template_code_column():
    from app.engines.service_setup.models import ServiceSetupTemplate
    assert hasattr(ServiceSetupTemplate, "code")


def test_setup_template_vertical_key_column():
    from app.engines.service_setup.models import ServiceSetupTemplate
    assert hasattr(ServiceSetupTemplate, "vertical_key")


def test_setup_template_status_column():
    from app.engines.service_setup.models import ServiceSetupTemplate
    assert hasattr(ServiceSetupTemplate, "status")


def test_setup_template_module_tablename():
    from app.engines.service_setup.models import ServiceSetupTemplateModule
    assert ServiceSetupTemplateModule.__tablename__ == "service_setup_template_modules"


def test_setup_template_item_tablename():
    from app.engines.service_setup.models import ServiceSetupTemplateItem
    assert ServiceSetupTemplateItem.__tablename__ == "service_setup_template_items"


def test_setup_template_version_tablename():
    from app.engines.service_setup.models import ServiceSetupTemplateVersion
    assert ServiceSetupTemplateVersion.__tablename__ == "service_setup_template_versions"


def test_setup_template_usage_tablename():
    from app.engines.service_setup.models import ServiceSetupTemplateUsage
    assert ServiceSetupTemplateUsage.__tablename__ == "service_setup_template_usage"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Service — list_templates
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_list_templates_empty():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[count_result, list_result])
    db.commit = AsyncMock()
    result = await svc.list_templates(db)
    assert result["total"] == 0
    assert result["items"] == []


@pytest.mark.asyncio
async def test_get_summary_zeros():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    zero_r = MagicMock()
    zero_r.scalar.return_value = 0
    zero_r.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=zero_r)
    result = await svc.get_summary(db)
    assert result["total"] == 0
    assert result["published"] == 0
    assert result["draft"] == 0
    assert result["system_count"] == 0
    assert result["custom_count"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# 4. Service — create_template
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_template_success():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    # First execute: code check (None = no existing)
    no_result = MagicMock()
    no_result.scalar_one_or_none.return_value = None
    t = _make_template()
    get_results = [
        # for get_template: template fetch, modules, items
        MagicMock(**{"scalar_one_or_none.return_value": t}),
        MagicMock(**{"scalars.return_value.all.return_value": []}),
        MagicMock(**{"scalars.return_value.all.return_value": []}),
    ]
    db.execute = AsyncMock(side_effect=[no_result] + get_results)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    result = await svc.create_template(db, {
        "name": "Test Template", "code": "test_template",
        "vertical_key": "universal", "template_type": "starter_pack",
    }, None)
    assert result is not None


@pytest.mark.asyncio
async def test_create_template_invalid_code():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    db.execute = AsyncMock()
    with pytest.raises(ValueError, match="Invalid code format"):
        await svc.create_template(db, {"name": "Test", "code": "123-invalid"}, None)


@pytest.mark.asyncio
async def test_create_template_duplicate_code():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    existing = _make_template()
    dup_result = MagicMock()
    dup_result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=dup_result)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    with pytest.raises(ValueError, match="already exists"):
        await svc.create_template(db, {"name": "Test", "code": "test_template"}, None)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Service — get_template
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_template_not_found():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=r)
    with pytest.raises(ValueError, match="not found"):
        await svc.get_template(db, str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_get_template_with_modules_and_items():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    t = _make_template()
    m = _make_module()
    it = _make_item()
    results = [
        MagicMock(**{"scalar_one_or_none.return_value": t}),
        MagicMock(**{"scalars.return_value.all.return_value": [m]}),
        MagicMock(**{"scalars.return_value.all.return_value": [it]}),
    ]
    db.execute = AsyncMock(side_effect=results)
    result = await svc.get_template(db, str(uuid.uuid4()))
    assert "modules" in result
    assert "items" in result
    assert len(result["modules"]) == 1
    assert len(result["items"]) == 1


# ══════════════════════════════════════════════════════════════════════════════
# 6. Service — validate_template
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_validate_template_valid_draft():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    t = _make_template(code="valid_code", name="Valid Template", vertical_key="universal")
    r1 = MagicMock(**{"scalar_one_or_none.return_value": t})
    r2 = MagicMock(**{"scalars.return_value.all.return_value": []})
    db.execute = AsyncMock(side_effect=[r1, r2])
    result = await svc.validate_template(db, str(uuid.uuid4()))
    assert result["valid"] is True
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_validate_coaching_with_issue_types_error():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    t = _make_template(code="coaching_tpl", name="Coaching TPL", vertical_key="coaching_ielts")
    m = _make_module(module_key="issue_types")
    r1 = MagicMock(**{"scalar_one_or_none.return_value": t})
    r2 = MagicMock(**{"scalars.return_value.all.return_value": [m]})
    db.execute = AsyncMock(side_effect=[r1, r2])
    result = await svc.validate_template(db, str(uuid.uuid4()))
    assert result["valid"] is False
    assert any("issue_types" in e for e in result["errors"])


# ══════════════════════════════════════════════════════════════════════════════
# 7. Service — publish, archive, clone, delete
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_archive_template():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    t = _make_template(status="published")
    r = MagicMock(**{"scalar_one_or_none.return_value": t})
    db.execute = AsyncMock(return_value=r)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    result = await svc.archive_template(db, str(uuid.uuid4()))
    assert t.status == "archived"


@pytest.mark.asyncio
async def test_delete_draft_succeeds():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    t = _make_template(status="draft")
    r = MagicMock(**{"scalar_one_or_none.return_value": t})
    db.execute = AsyncMock(return_value=r)
    db.commit = AsyncMock()
    db.delete = AsyncMock()
    await svc.delete_template(db, str(uuid.uuid4()))
    db.delete.assert_called_once_with(t)


@pytest.mark.asyncio
async def test_delete_published_fails():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    t = _make_template(status="published")
    r = MagicMock(**{"scalar_one_or_none.return_value": t})
    db.execute = AsyncMock(return_value=r)
    with pytest.raises(ValueError, match="Only draft"):
        await svc.delete_template(db, str(uuid.uuid4()))


# ══════════════════════════════════════════════════════════════════════════════
# 8. Service — seed_defaults
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_seed_defaults_preview_returns_list():
    from app.engines.service_setup.templates_service import SetupTemplatesService
    svc = SetupTemplatesService()
    db = MagicMock()
    # No existing codes
    r = MagicMock(**{"scalars.return_value.all.return_value": []})
    db.execute = AsyncMock(return_value=r)
    result = await svc.seed_defaults_preview(db)
    assert "templates_to_create" in result
    assert len(result["templates_to_create"]) >= 11


# ══════════════════════════════════════════════════════════════════════════════
# 9. Router
# ══════════════════════════════════════════════════════════════════════════════

def test_router_has_list_endpoint():
    from app.engines.service_setup.templates_router import router
    paths = [r.path for r in router.routes]
    assert any("templates" in p and "{" not in p for p in paths)


def test_router_has_summary_endpoint():
    from app.engines.service_setup.templates_router import router
    paths = [r.path for r in router.routes]
    assert any("summary" in p for p in paths)


def test_router_has_seed_defaults_endpoint():
    from app.engines.service_setup.templates_router import router
    paths = [r.path for r in router.routes]
    assert any("seed-defaults" in p for p in paths)


def test_router_has_template_id_endpoint():
    from app.engines.service_setup.templates_router import router
    paths = [r.path for r in router.routes]
    assert any("{template_id}" in p for p in paths)


# ══════════════════════════════════════════════════════════════════════════════
# 10. main.py registration
# ══════════════════════════════════════════════════════════════════════════════

def test_main_py_mounts_setup_templates_router():
    src = (ROOT / "app" / "main.py").read_text()
    assert "setup_templates_router" in src
    assert "service_setup.templates_router" in src


# ══════════════════════════════════════════════════════════════════════════════
# 11. Permissions
# ══════════════════════════════════════════════════════════════════════════════

def test_permissions_has_setup_templates_read():
    from app.core.permissions import P
    assert hasattr(P, "SETUP_TEMPLATES_READ")


def test_permissions_has_setup_templates_write():
    from app.core.permissions import P
    assert hasattr(P, "SETUP_TEMPLATES_WRITE")


def test_permissions_has_setup_templates_publish():
    from app.core.permissions import P
    assert hasattr(P, "SETUP_TEMPLATES_PUBLISH")


# ══════════════════════════════════════════════════════════════════════════════
# 12. api.ts
# ══════════════════════════════════════════════════════════════════════════════

def test_api_ts_has_setup_templates_api():
    assert "serviceSetupTemplatesApi" in _ts_source()


def test_api_ts_has_setup_template_item_interface():
    assert "SetupTemplateItem" in _ts_source()


def test_api_ts_has_setup_templates_summary_interface():
    assert "SetupTemplatesSummary" in _ts_source()


def test_api_ts_has_seed_defaults_method():
    assert "seedDefaults" in _ts_source()


def test_api_ts_has_seed_defaults_preview_method():
    assert "seedDefaultsPreview" in _ts_source()


# ══════════════════════════════════════════════════════════════════════════════
# 13. Frontend Page
# ══════════════════════════════════════════════════════════════════════════════

def test_frontend_page_exists():
    page = ROOT / "frontend" / "super-admin" / "app" / "admin" / "service-setup" / "templates" / "page.tsx"
    assert page.exists(), "Frontend page not found"


def _page_src() -> str:
    return (ROOT / "frontend" / "super-admin" / "app" / "admin" / "service-setup" / "templates" / "page.tsx").read_text(encoding="utf-8")


def test_frontend_page_uses_design_tokens():
    src = _page_src()
    assert "var(--surface)" in src
    assert "var(--text-primary)" in src
    assert "var(--border)" in src


def test_frontend_page_uses_templates_api():
    src = _page_src()
    assert "serviceSetupTemplatesApi" in src


def test_frontend_page_has_wizard():
    src = _page_src()
    assert "wizardStep" in src or "WizardContent" in src


def test_frontend_page_no_hardcoded_hex():
    src = _page_src()
    import re
    # Should not have inline hex colors like #1e3a5f etc.
    hardcoded = re.findall(r'(?<!["\w])#[0-9a-fA-F]{3,6}(?![0-9a-fA-F])', src)
    # Emoji hex-like references are OK; filter real hex colors only
    actual_hex = [h for h in hardcoded if len(h) in (4, 7)]
    assert len(actual_hex) == 0, f"Hardcoded hex colors found: {actual_hex}"
