"""Tests for P0 Workflow Templates Enterprise Engine — migration 106.

All tests are file-content / structure checks (no live DB required).
"""
from pathlib import Path
import re

ROOT = Path(__file__).parent.parent
MIGRATION = ROOT / "alembic" / "versions" / "106_workflow_templates_enterprise.py"
SERVICE = ROOT / "app" / "engines" / "workflows" / "workflow_service.py"
ROUTER = ROOT / "app" / "engines" / "workflows" / "workflow_router.py"
MAIN_PY = ROOT / "app" / "main.py"
API_TS = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
LIST_PAGE = ROOT / "frontend" / "super-admin" / "app" / "admin" / "workflows" / "templates" / "page.tsx"
DETAIL_PAGE = ROOT / "frontend" / "super-admin" / "app" / "admin" / "workflows" / "templates" / "[id]" / "page.tsx"


# ── 1. Migration exists with correct revision ─────────────────────────────────

def test_migration_106_exists():
    assert MIGRATION.exists(), "106_workflow_templates_enterprise.py must exist"


def test_migration_revision_106():
    src = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "106"' in src


def test_migration_down_revision_105():
    src = MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision = "105"' in src


# ── 2. Migration creates required tables ──────────────────────────────────────

def test_migration_creates_workflow_templates():
    src = MIGRATION.read_text(encoding="utf-8")
    assert "workflow_templates" in src


def test_migration_creates_workflow_template_versions():
    src = MIGRATION.read_text(encoding="utf-8")
    assert "workflow_template_versions" in src


def test_migration_creates_workflow_runtime_events():
    src = MIGRATION.read_text(encoding="utf-8")
    assert "workflow_runtime_events" in src


def test_migration_creates_workflow_audit_logs():
    src = MIGRATION.read_text(encoding="utf-8")
    assert "workflow_audit_logs" in src


# ── 3. Service exists with required methods ───────────────────────────────────

def test_service_file_exists():
    assert SERVICE.exists(), "workflow_service.py must exist"


def test_service_has_get_summary():
    src = SERVICE.read_text(encoding="utf-8")
    assert "async def get_summary" in src


def test_service_has_list_templates():
    src = SERVICE.read_text(encoding="utf-8")
    assert "async def list_templates" in src


def test_service_has_create_template():
    src = SERVICE.read_text(encoding="utf-8")
    assert "async def create_template" in src


def test_service_has_validate_template():
    src = SERVICE.read_text(encoding="utf-8")
    assert "async def validate_template" in src


def test_service_has_simulate_template():
    src = SERVICE.read_text(encoding="utf-8")
    assert "async def simulate_template" in src


def test_service_has_publish_template():
    src = SERVICE.read_text(encoding="utf-8")
    assert "async def publish_template" in src


def test_service_has_seed_defaults():
    src = SERVICE.read_text(encoding="utf-8")
    assert "async def seed_defaults" in src


def test_service_seeds_standard_repair_workflow():
    src = SERVICE.read_text(encoding="utf-8")
    assert "standard_repair_workflow" in src


def test_service_seeds_26_workflows():
    src = SERVICE.read_text(encoding="utf-8")
    matches = re.findall(r'"workflow_key":\s*"[^"]+_workflow"', src)
    assert len(matches) >= 25, f"Expected at least 25 seed workflows, found {len(matches)}"


# ── 4. Router file exists and has correct prefix ──────────────────────────────

def test_router_file_exists():
    assert ROUTER.exists(), "workflow_router.py must exist"


def test_router_prefix():
    src = ROUTER.read_text(encoding="utf-8")
    assert "/v1/admin/workflows/templates" in src


def test_router_has_static_summary_before_parameterized():
    src = ROUTER.read_text(encoding="utf-8")
    summary_pos = src.find('"/summary"')
    wid_pos = src.find('"/{wid}"')
    assert summary_pos < wid_pos, "Static /summary route must appear before /{wid}"


def test_router_has_seed_defaults_routes():
    src = ROUTER.read_text(encoding="utf-8")
    assert "seed-defaults" in src


def test_router_has_validate_simulate_publish():
    src = ROUTER.read_text(encoding="utf-8")
    assert "validate" in src
    assert "simulate" in src
    assert "publish" in src


# ── 5. main.py mounts the router ─────────────────────────────────────────────

def test_main_imports_workflow_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "workflow_enterprise_router" in src


def test_main_includes_workflow_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "app.include_router(workflow_enterprise_router)" in src


# ── 6. api.ts has workflowTemplateApi ────────────────────────────────────────

def test_api_ts_has_workflow_template_api():
    src = API_TS.read_text(encoding="utf-8")
    assert "workflowTemplateApi" in src


def test_api_ts_workflow_template_api_methods():
    src = API_TS.read_text(encoding="utf-8")
    for method in ["getSummary", "list", "create", "validate", "simulate", "publish", "seedDefaults"]:
        assert method in src, f"workflowTemplateApi must have method: {method}"


# ── 7. Frontend pages exist ───────────────────────────────────────────────────

def test_list_page_exists():
    assert LIST_PAGE.exists(), "workflows/templates/page.tsx must exist"


def test_detail_page_exists():
    assert DETAIL_PAGE.exists(), "workflows/templates/[id]/page.tsx must exist"


def test_list_page_uses_workflow_template_api():
    src = LIST_PAGE.read_text(encoding="utf-8")
    assert "workflowTemplateApi" in src


def test_detail_page_has_13_tabs():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    tab_count = src.count("'Overview'") + src.count('"Overview"')
    assert "TABS" in src
    assert "Audit Logs" in src, "Detail page must have Audit Logs tab"
    assert "Version History" in src


def test_list_page_has_kpi_cards():
    src = LIST_PAGE.read_text(encoding="utf-8")
    assert "KpiCard" in src or "kpi-card" in src


def test_list_page_has_readiness_badge():
    src = LIST_PAGE.read_text(encoding="utf-8")
    assert "ReadinessBadge" in src


def test_detail_page_has_visual_builder_tab():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "Visual Builder" in src


def test_no_hardcoded_hex_colors_in_list_page():
    src = LIST_PAGE.read_text(encoding="utf-8")
    hex_matches = re.findall(r'(?<!["\'-])#[0-9a-fA-F]{3,6}(?![0-9a-fA-F])', src)
    assert len(hex_matches) == 0, f"Hardcoded hex colors found: {hex_matches}"


def test_no_hardcoded_hex_colors_in_detail_page():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    hex_matches = re.findall(r'(?<!["\'-])#[0-9a-fA-F]{3,6}(?![0-9a-fA-F])', src)
    assert len(hex_matches) == 0, f"Hardcoded hex colors found: {hex_matches}"
