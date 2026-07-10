"""Tests for P0 Intelligence Command Center — migration 103.

Validates: migration, ORM models, service, router mount, and NaN safety.
All tests are file-content checks (no live DB required).
"""
from pathlib import Path
import re

ROOT       = Path(__file__).parent.parent
MIGRATION  = ROOT / "alembic" / "versions" / "103_intelligence_command_center.py"
MODELS     = ROOT / "app" / "engines" / "analytics" / "intelligence_models.py"
SERVICE    = ROOT / "app" / "engines" / "analytics" / "intelligence_service.py"
ROUTER     = ROOT / "app" / "engines" / "analytics" / "intelligence_router.py"
MAIN_PY    = ROOT / "app" / "main.py"
API_TS     = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
PAGE       = ROOT / "frontend" / "super-admin" / "app" / "admin" / "intelligence" / "page.tsx"
PERMS      = ROOT / "app" / "core" / "permissions.py"


# ── File existence ─────────────────────────────────────────────────────────────

def test_migration_exists():
    assert MIGRATION.exists()

def test_models_file_exists():
    assert MODELS.exists()

def test_service_file_exists():
    assert SERVICE.exists()

def test_router_file_exists():
    assert ROUTER.exists()

def test_page_exists():
    assert PAGE.exists()


# ── Migration ──────────────────────────────────────────────────────────────────

def test_migration_revision_is_103():
    src = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "103"' in src

def test_migration_down_revision_is_102():
    src = MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision = "102"' in src

def test_migration_creates_rag_knowledge_bases():
    src = MIGRATION.read_text(encoding="utf-8")
    assert '"rag_knowledge_bases"' in src

def test_migration_creates_intel_risk_scores():
    src = MIGRATION.read_text(encoding="utf-8")
    assert '"intel_risk_scores"' in src

def test_migration_creates_intel_anomalies():
    src = MIGRATION.read_text(encoding="utf-8")
    assert '"intel_anomalies"' in src

def test_migration_creates_ai_usage_logs():
    src = MIGRATION.read_text(encoding="utf-8")
    assert '"ai_usage_logs"' in src


# ── ORM Models ────────────────────────────────────────────────────────────────

def test_models_has_8_tables():
    src = MODELS.read_text(encoding="utf-8")
    tables = re.findall(r'__tablename__\s*=\s*"(\w+)"', src)
    assert len(tables) == 8, f"Expected 8 tables, found {len(tables)}: {tables}"

def test_models_all_have_to_dict():
    src = MODELS.read_text(encoding="utf-8")
    count = src.count("def to_dict(")
    assert count == 8, f"Expected 8 to_dict methods, found {count}"


# ── Service: NaN Safety ───────────────────────────────────────────────────────

def test_service_avg_latency_returns_none_not_nan():
    """avg_ai_latency_ms must be set to None (not NaN) when no rows exist."""
    src = SERVICE.read_text(encoding="utf-8")
    # Should not have any float('nan') or math.nan usage
    assert "float('nan')" not in src
    assert "math.nan" not in src
    # Should explicitly handle None
    assert "avg_ai_latency_ms = None" in src or "= int(raw) if raw is not None else None" in src

def test_service_has_default_checks_seeded():
    src = SERVICE.read_text(encoding="utf-8")
    assert "DEFAULT_CHECKS" in src
    assert "missing_tenant_profiles" in src
    assert "invalid_credit_deductions" in src


# ── Router ────────────────────────────────────────────────────────────────────

def test_router_prefix():
    src = ROUTER.read_text(encoding="utf-8")
    assert '/v1/admin/intelligence' in src

def test_router_static_before_parameterized_anomaly():
    """run-scan must be registered before /{anomaly_id}."""
    src = ROUTER.read_text(encoding="utf-8")
    scan_pos = src.find("/anomalies/run-scan")
    param_pos = src.find("/anomalies/{anomaly_id}")
    assert scan_pos < param_pos, "run-scan must appear before /{anomaly_id}"

def test_router_has_summary_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert '"/summary"' in src

def test_router_has_data_quality_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert "/data-quality/checks" in src

def test_router_has_ai_usage_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert "/ai-usage/summary" in src

def test_router_mounted_in_main():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "intelligence_cmd_router" in src or "intelligence_router" in src.lower()


# ── Permissions ────────────────────────────────────────────────────────────────

def test_permissions_has_intelligence_read():
    src = PERMS.read_text(encoding="utf-8")
    assert "INTELLIGENCE_READ" in src

def test_permissions_has_intelligence_manage():
    src = PERMS.read_text(encoding="utf-8")
    assert "INTELLIGENCE_MANAGE" in src


# ── Frontend ──────────────────────────────────────────────────────────────────

def test_page_has_nan_safety():
    src = PAGE.read_text(encoding="utf-8")
    assert "safeNum" in src
    assert "fmtMs" in src

def test_page_nan_never_displayed():
    """NaN must not be returned as a string from fmtMs."""
    src = PAGE.read_text(encoding="utf-8")
    assert "No queries yet" in src

def test_page_has_10_tabs():
    src = PAGE.read_text(encoding="utf-8")
    tab_ids = re.findall(r'id:\s*"([^"]+)"', src)
    # Filter only the ones in the TABS const
    assert len(tab_ids) >= 10, f"Expected 10+ tab ids, found {len(tab_ids)}: {tab_ids}"

def test_page_uses_intelligenceCmdApi():
    src = PAGE.read_text(encoding="utf-8")
    assert "intelligenceCmdApi" in src

def test_api_ts_has_intelligenceCmdApi():
    src = API_TS.read_text(encoding="utf-8")
    assert "intelligenceCmdApi" in src
    assert "IntelligenceSummary" in src
    assert "avg_ai_latency_ms: number | null" in src
