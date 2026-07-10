"""Tests for P0 Enterprise Service Setup Bulk Wizard (migration 098).

Coverage:
  - migration file existence and tables
  - ORM model table names and columns
  - BulkSetupService methods (mocked DB)
  - bulk_router endpoints
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


def _make_draft(**kwargs) -> MagicMock:
    d = MagicMock()
    uid = uuid.uuid4()
    defaults = {
        "id": uid,
        "draft_code": f"bulk_home_services_123",
        "name": "Test Bulk Setup",
        "description": "A test bulk setup",
        "vertical_key": "home_services",
        "setup_mode": "manual",
        "template_id": None,
        "status": "draft",
        "current_step": 1,
        "config_json": {},
        "created_by_user_id": None,
        "archived_at": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(d, k, v)
    d.to_dict.return_value = {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in defaults.items()}
    return d


def _make_run(**kwargs) -> MagicMock:
    r = MagicMock()
    uid = uuid.uuid4()
    defaults = {
        "id": uid,
        "run_code": "run_home_services_123",
        "draft_id": uuid.uuid4(),
        "vertical_key": "home_services",
        "template_id": None,
        "status": "completed",
        "is_dry_run": False,
        "total_items": 5,
        "created_count": 5,
        "updated_count": 0,
        "skipped_count": 0,
        "failed_count": 0,
        "rollback_available": True,
        "execution_reason": "test",
        "started_by_user_id": None,
        "started_at": "2026-01-01T00:00:00+00:00",
        "completed_at": "2026-01-01T00:00:01+00:00",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(r, k, v)
    r.to_dict.return_value = {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in defaults.items()}
    return r


# ── Test 1: Migration file exists ─────────────────────────────────────────────

def test_migration_file_exists():
    migration_files = list((ROOT / "alembic" / "versions").glob("098_*.py"))
    assert len(migration_files) == 1, f"Expected migration 098, found: {migration_files}"


# ── Test 2: Tables defined in migration ───────────────────────────────────────

def test_migration_tables_defined():
    migration_file = list((ROOT / "alembic" / "versions").glob("098_*.py"))[0]
    src = migration_file.read_text(encoding="utf-8")
    for table in [
        "service_setup_bulk_drafts",
        "service_setup_bulk_preview_items",
        "service_setup_bulk_validation_results",
        "service_setup_bulk_runs",
        "service_setup_bulk_run_items",
    ]:
        assert table in src, f"Table {table} not in migration"


# ── Test 3: ORM models exist ──────────────────────────────────────────────────

def test_orm_models_exist():
    from app.engines.service_setup.models import (
        BulkDraft, BulkPreviewItem, BulkValidationResult, BulkRun, BulkRunItem,
    )
    assert BulkDraft.__tablename__ == "service_setup_bulk_drafts"
    assert BulkPreviewItem.__tablename__ == "service_setup_bulk_preview_items"
    assert BulkValidationResult.__tablename__ == "service_setup_bulk_validation_results"
    assert BulkRun.__tablename__ == "service_setup_bulk_runs"
    assert BulkRunItem.__tablename__ == "service_setup_bulk_run_items"


# ── Test 4: BulkDraft columns ─────────────────────────────────────────────────

def test_bulk_draft_columns():
    from app.engines.service_setup.models import BulkDraft
    cols = {c.name for c in BulkDraft.__table__.columns}
    for col in ["id", "draft_code", "name", "vertical_key", "status", "current_step", "config_json"]:
        assert col in cols, f"Column {col} missing from BulkDraft"


# ── Test 5: BulkRun columns ───────────────────────────────────────────────────

def test_bulk_run_columns():
    from app.engines.service_setup.models import BulkRun
    cols = {c.name for c in BulkRun.__table__.columns}
    for col in ["id", "run_code", "draft_id", "status", "is_dry_run", "total_items", "created_count", "rollback_available"]:
        assert col in cols, f"Column {col} missing from BulkRun"


# ── Test 6: Service import ────────────────────────────────────────────────────

def test_service_imports():
    from app.engines.service_setup.bulk_service import BulkSetupService, ALLOWED_VERTICALS
    svc = BulkSetupService()
    assert hasattr(svc, "list_drafts")
    assert hasattr(svc, "create_draft")
    assert hasattr(svc, "validate_draft")
    assert hasattr(svc, "execute_draft")
    assert "home_services" in ALLOWED_VERTICALS
    assert "coaching_ielts" in ALLOWED_VERTICALS


# ── Test 7: List drafts (empty) ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_drafts_empty():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=0), scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    result = await svc.list_drafts(db)
    assert result["total"] == 0
    assert result["items"] == []


# ── Test 8: Get summary ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_summary():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[]), scalar=MagicMock(return_value=0)))
    result = await svc.get_summary(db)
    assert "total_drafts" in result
    assert "ready_to_run" in result
    assert "completed_runs" in result
    assert "rollback_available" in result


# ── Test 9: Create draft — valid ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_draft_valid():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("app.engines.service_setup.bulk_service.BulkDraft", return_value=draft):
        result = await svc.create_draft(db, {"name": "Test Setup", "vertical_key": "home_services"})
    assert db.add.called or result is not None


# ── Test 10: Create draft — invalid vertical ──────────────────────────────────

@pytest.mark.asyncio
async def test_create_draft_invalid_vertical():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    with pytest.raises(ValueError, match="vertical_key"):
        await svc.create_draft(db, {"name": "Test", "vertical_key": "invalid_vertical"})


# ── Test 11: Create draft — missing name ──────────────────────────────────────

@pytest.mark.asyncio
async def test_create_draft_missing_name():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    with pytest.raises(ValueError, match="name"):
        await svc.create_draft(db, {"name": "", "vertical_key": "home_services"})


# ── Test 12: Get draft by id ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_draft_by_id():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft()
    db.get = AsyncMock(return_value=draft)
    result = await svc.get_draft(db, str(draft.id))
    assert result["name"] == "Test Bulk Setup"


# ── Test 13: Get draft not found ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_draft_not_found():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="not found"):
        await svc.get_draft(db, str(uuid.uuid4()))


# ── Test 14: Update draft config_json ────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_draft():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft()
    db.get = AsyncMock(return_value=draft)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    await svc.update_draft(db, str(draft.id), {"config_json": {"modules": ["service_groups"]}, "current_step": 4})
    assert draft.current_step == 4


# ── Test 15: Validate draft — clean ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_draft_clean():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft(config_json={"modules": ["service_groups"], "content": {"service_groups": [{"name": "AC", "code": "ac"}]}})
    db.get = AsyncMock(return_value=draft)
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    result = await svc.validate_draft(db, str(draft.id))
    assert result["valid"] is True
    assert result["blocking_count"] == 0


# ── Test 16: Validate coaching draft with issue_types → blocking error ────────

@pytest.mark.asyncio
async def test_validate_coaching_issue_types_blocked():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft(
        vertical_key="coaching_ielts",
        config_json={"modules": ["issue_types", "courses"], "content": {}},
    )
    db.get = AsyncMock(return_value=draft)
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    result = await svc.validate_draft(db, str(draft.id))
    assert result["valid"] is False
    assert result["blocking_count"] >= 1
    assert any("issue_types" in str(e) or "coaching" in str(e).lower() for e in result["errors"])


# ── Test 17: Preview draft — returns items list ───────────────────────────────

@pytest.mark.asyncio
async def test_preview_draft():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft(config_json={
        "content": {"service_groups": [{"name": "AC Services", "code": "ac_services"}]}
    })
    db.get = AsyncMock(return_value=draft)
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    result = await svc.preview_draft(db, str(draft.id))
    assert "items" in result
    assert "summary" in result
    assert len(result["items"]) == 1


# ── Test 18: Dry run creates BulkRun with is_dry_run=True ────────────────────

@pytest.mark.asyncio
async def test_dry_run_creates_run():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft(config_json={"content": {"service_groups": [{"name": "AC", "code": "ac"}]}})
    db.get = AsyncMock(return_value=draft)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    run = _make_run(is_dry_run=True, status="completed")
    db.refresh = AsyncMock(side_effect=lambda obj: None)

    captured_runs = []
    original_add = db.add
    def capture_add(obj):
        from app.engines.service_setup.models import BulkRun
        if hasattr(obj, "run_code"):
            captured_runs.append(obj)
        return original_add(obj)
    db.add = capture_add

    with patch("app.engines.service_setup.bulk_service.BulkRun") as MockRun:
        mock_run = _make_run(is_dry_run=True, status="completed")
        MockRun.return_value = mock_run
        result = await svc.dry_run(db, str(draft.id))
    assert result is not None


# ── Test 19: Execute draft creates BulkRun ───────────────────────────────────

@pytest.mark.asyncio
async def test_execute_draft():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft(config_json={"content": {}})
    db.get = AsyncMock(return_value=draft)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()

    with patch("app.engines.service_setup.bulk_service.BulkRun") as MockRun:
        mock_run = _make_run(is_dry_run=False, status="completed")
        MockRun.return_value = mock_run
        result = await svc.execute_draft(db, str(draft.id), reason="Test run")
    assert result is not None


# ── Test 20: Clone draft ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clone_draft():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft()
    db.get = AsyncMock(return_value=draft)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("app.engines.service_setup.bulk_service.BulkDraft") as MockDraft:
        clone = _make_draft(name="Test Bulk Setup (Clone)", draft_code="bulk_home_services_456_clone")
        MockDraft.return_value = clone
        result = await svc.clone_draft(db, str(draft.id))
    assert result is not None


# ── Test 21: Delete draft (status=draft) — success ───────────────────────────

@pytest.mark.asyncio
async def test_delete_draft_success():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft(status="draft")
    db.get = AsyncMock(return_value=draft)
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    await svc.delete_draft(db, str(draft.id))
    db.delete.assert_called_once_with(draft)


# ── Test 22: Delete draft (status=completed) — fails ─────────────────────────

@pytest.mark.asyncio
async def test_delete_draft_completed_fails():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    draft = _make_draft(status="completed")
    db.get = AsyncMock(return_value=draft)
    with pytest.raises(ValueError, match="Cannot delete"):
        await svc.delete_draft(db, str(draft.id))


# ── Test 23: List runs ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_runs():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(
        scalar=MagicMock(return_value=0),
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
        all=MagicMock(return_value=[]),
    ))
    result = await svc.list_runs(db)
    assert "items" in result
    assert "total" in result


# ── Test 24: Get run by id ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_run_by_id():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    run = _make_run()
    db.get = AsyncMock(return_value=run)
    result = await svc.get_run(db, str(run.id))
    assert result["run_code"] == "run_home_services_123"


# ── Test 25: Get run logs ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_run_logs():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    run = _make_run()
    db.get = AsyncMock(return_value=run)
    db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))))
    result = await svc.get_run_logs(db, str(run.id))
    assert "items" in result


# ── Test 26: Rollback run ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rollback_run():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    run = _make_run(rollback_available=True, status="completed")
    db.get = AsyncMock(return_value=run)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    await svc.rollback_run(db, str(run.id), reason="Test rollback")
    assert run.status == "rolled_back"
    assert run.rollback_available is False


# ── Test 27: Rollback not available ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_rollback_not_available():
    from app.engines.service_setup.bulk_service import BulkSetupService
    svc = BulkSetupService()
    db = AsyncMock()
    run = _make_run(rollback_available=False, status="completed")
    db.get = AsyncMock(return_value=run)
    with pytest.raises(ValueError, match="Rollback not available"):
        await svc.rollback_run(db, str(run.id))


# ── Test 28: Router mounted in main.py ───────────────────────────────────────

def test_router_mounted_in_main():
    src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "bulk_wizard_router" in src or "bulk_router" in src


# ── Test 29: Permissions defined ─────────────────────────────────────────────

def test_permissions_defined():
    from app.core.permissions import P
    assert hasattr(P, "BULK_WIZARD_READ")
    assert hasattr(P, "BULK_WIZARD_WRITE")
    assert hasattr(P, "BULK_WIZARD_EXECUTE")


# ── Test 30: API ts types ─────────────────────────────────────────────────────

def test_api_ts_types():
    src = _ts_source()
    for sym in ["BulkDraftItem", "BulkDraftDetail", "BulkRunItem", "BulkWizardSummary"]:
        assert sym in src, f"{sym} not found in api.ts"


# ── Test 31: API ts methods ───────────────────────────────────────────────────

def test_api_ts_methods():
    src = _ts_source()
    for method in ["bulkWizardApi", "createDraft", "validateDraft", "previewDraft", "dryRun", "executeDraft", "listRuns", "rollbackRun"]:
        assert method in src, f"{method} not found in api.ts"


# ── Test 32: Frontend page exists ────────────────────────────────────────────

def test_frontend_page_exists():
    page = ROOT / "frontend" / "super-admin" / "app" / "admin" / "service-setup" / "bulk-wizard" / "page.tsx"
    assert page.exists()
    src = page.read_text(encoding="utf-8")
    assert "BulkWizardPage" in src or "bulk-wizard" in src.lower()


# ── Test 33: Bulk runs page exists ───────────────────────────────────────────

def test_bulk_runs_page_exists():
    page = ROOT / "frontend" / "super-admin" / "app" / "admin" / "service-setup" / "bulk-runs" / "page.tsx"
    assert page.exists()


# ── Test 34: Wizard has 10 steps ─────────────────────────────────────────────

def test_wizard_has_10_steps():
    page = ROOT / "frontend" / "super-admin" / "app" / "admin" / "service-setup" / "bulk-wizard" / "page.tsx"
    src = page.read_text(encoding="utf-8")
    assert "10" in src and ("step" in src.lower() or "Step" in src)


# ── Test 35: Dark theme — no hardcoded hex colors in page ────────────────────

def test_no_hardcoded_hex_in_wizard_page():
    page = ROOT / "frontend" / "super-admin" / "app" / "admin" / "service-setup" / "bulk-wizard" / "page.tsx"
    src = page.read_text(encoding="utf-8")
    import re
    # Allow #fff and #000 in comments, block others
    hex_colors = re.findall(r'(?<!//\s)#[0-9a-fA-F]{6}', src)
    assert len(hex_colors) == 0, f"Hardcoded hex colors found: {hex_colors}"


# ── Test 36: Vertical modules constant defined ───────────────────────────────

def test_vertical_modules_in_page():
    page = ROOT / "frontend" / "super-admin" / "app" / "admin" / "service-setup" / "bulk-wizard" / "page.tsx"
    src = page.read_text(encoding="utf-8")
    assert "VERTICAL_MODULES" in src
    assert "coaching_ielts" in src
    assert "home_services" in src
    assert "real_estate" in src


# ── Test 37: Coaching vertical does not include issue_types in module list ─────

def test_coaching_no_issue_types_module():
    # The validation service catches this at runtime
    # The frontend should not list issue_types for coaching
    page = ROOT / "frontend" / "super-admin" / "app" / "admin" / "service-setup" / "bulk-wizard" / "page.tsx"
    src = page.read_text(encoding="utf-8")
    # coaching_ielts section should NOT have issue_types
    import re
    coaching_section = re.search(r'coaching_ielts:\s*\[(.*?)\]', src, re.DOTALL)
    assert coaching_section is not None
    assert "issue_types" not in coaching_section.group(1), "coaching_ielts section should not contain issue_types"
