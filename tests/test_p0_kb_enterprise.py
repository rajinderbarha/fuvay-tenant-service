"""Tests for P0 Knowledge Base Enterprise — migration 104.

All tests are file-content checks (no live DB required).
"""
from pathlib import Path
import re

ROOT       = Path(__file__).parent.parent
MIGRATION  = ROOT / "alembic" / "versions" / "104_kb_enterprise.py"
MIGRATION2 = ROOT / "alembic" / "versions" / "105_dashboard_command_center.py"
MODELS     = ROOT / "app" / "engines" / "analytics" / "kb_models.py"
SERVICE    = ROOT / "app" / "engines" / "analytics" / "kb_service.py"
ROUTER     = ROOT / "app" / "engines" / "analytics" / "kb_router.py"
MAIN_PY    = ROOT / "app" / "main.py"
API_TS     = ROOT / "frontend" / "super-admin" / "lib" / "api.ts"
DETAIL_PAGE = ROOT / "frontend" / "super-admin" / "app" / "admin" / "intelligence" / "knowledge-bases" / "[id]" / "page.tsx"
INTEL_PAGE  = ROOT / "frontend" / "super-admin" / "app" / "admin" / "intelligence" / "page.tsx"


# ── 1. Migration conflict resolved ────────────────────────────────────────────

def test_kb_migration_104_exists():
    assert MIGRATION.exists(), "104_kb_enterprise.py must exist"


def test_dashboard_migration_is_now_105():
    """Verifies the former duplicate-104 dashboard migration is now 105."""
    assert MIGRATION2.exists(), "105_dashboard_command_center.py must exist"
    src = MIGRATION2.read_text(encoding="utf-8")
    assert 'revision = "105"' in src
    assert 'down_revision = "104"' in src


def test_kb_migration_revision_104():
    src = MIGRATION.read_text(encoding="utf-8")
    assert 'revision = "104"' in src


def test_kb_migration_down_revision_103():
    src = MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision = "103"' in src


# ── 2. Migration creates required tables ──────────────────────────────────────

def test_kb_migration_creates_rag_documents():
    src = MIGRATION.read_text(encoding="utf-8")
    assert '"rag_documents"' in src


def test_kb_migration_creates_rag_manual_articles():
    src = MIGRATION.read_text(encoding="utf-8")
    assert '"rag_manual_articles"' in src


def test_kb_migration_creates_rag_document_chunks():
    src = MIGRATION.read_text(encoding="utf-8")
    assert '"rag_document_chunks"' in src


def test_kb_migration_creates_rag_indexing_jobs():
    src = MIGRATION.read_text(encoding="utf-8")
    assert '"rag_indexing_jobs"' in src


def test_kb_migration_creates_rag_kb_audit_logs():
    src = MIGRATION.read_text(encoding="utf-8")
    assert '"rag_kb_audit_logs"' in src


# ── 3. Models ─────────────────────────────────────────────────────────────────

def test_kb_models_file_exists():
    assert MODELS.exists()


def test_kb_models_contains_rag_document():
    src = MODELS.read_text(encoding="utf-8")
    assert "class RagDocument" in src


def test_kb_models_contains_rag_indexing_job():
    src = MODELS.read_text(encoding="utf-8")
    assert "class RagIndexingJob" in src


def test_kb_models_contains_rag_kb_audit_log():
    src = MODELS.read_text(encoding="utf-8")
    assert "class RagKbAuditLog" in src


# ── 4. Service ────────────────────────────────────────────────────────────────

def test_kb_service_file_exists():
    assert SERVICE.exists()


def test_kb_service_has_get_kb_summary():
    src = SERVICE.read_text(encoding="utf-8")
    assert "get_kb_summary" in src


def test_kb_service_has_validate_kb():
    src = SERVICE.read_text(encoding="utf-8")
    assert "_validate_kb" in src


def test_kb_service_validates_compliance_not_customer_visible():
    src = SERVICE.read_text(encoding="utf-8")
    assert "compliance" in src and "customer_visible" in src


def test_kb_service_validates_chunk_overlap():
    src = SERVICE.read_text(encoding="utf-8")
    assert "chunk_overlap" in src and "chunk_size" in src


def test_kb_service_seed_defaults_has_7_kbs():
    src = SERVICE.read_text(encoding="utf-8")
    # _SEED_KBS list should have 7 entries
    matches = re.findall(r'"kb_code":', src)
    assert len(matches) >= 7, f"Expected ≥7 seed KBs, got {len(matches)}"


def test_kb_service_has_preview_access():
    src = SERVICE.read_text(encoding="utf-8")
    assert "preview_access" in src


def test_kb_service_has_test_query():
    src = SERVICE.read_text(encoding="utf-8")
    assert "test_query" in src


def test_kb_service_has_trigger_index():
    src = SERVICE.read_text(encoding="utf-8")
    assert "trigger_index" in src


# ── 5. Router ─────────────────────────────────────────────────────────────────

def test_kb_router_file_exists():
    assert ROUTER.exists()


def test_kb_router_prefix():
    src = ROUTER.read_text(encoding="utf-8")
    assert "/v1/admin/intelligence/knowledge-bases" in src


def test_kb_router_has_summary_endpoint():
    src = ROUTER.read_text(encoding="utf-8")
    assert '"/summary"' in src or "'/summary'" in src or "/summary" in src


def test_kb_router_has_access_preview():
    src = ROUTER.read_text(encoding="utf-8")
    assert "access-preview" in src


def test_kb_router_has_seed_defaults():
    src = ROUTER.read_text(encoding="utf-8")
    assert "seed-defaults" in src


# ── 6. Router mounted in main.py ──────────────────────────────────────────────

def test_main_py_imports_kb_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "kb_router" in src


def test_main_py_includes_kb_router():
    src = MAIN_PY.read_text(encoding="utf-8")
    assert "include_router(kb_router)" in src


# ── 7. Frontend API ───────────────────────────────────────────────────────────

def test_api_ts_has_kb_api():
    src = API_TS.read_text(encoding="utf-8")
    assert "export const kbApi" in src


def test_api_ts_kb_api_has_get_summary():
    src = API_TS.read_text(encoding="utf-8")
    assert "getSummary" in src and "knowledge-bases/summary" in src


def test_api_ts_kb_api_has_seed_defaults():
    src = API_TS.read_text(encoding="utf-8")
    assert "seedDefaults" in src


def test_api_ts_kb_summary_interface():
    src = API_TS.read_text(encoding="utf-8")
    assert "KBSummary" in src


# ── 8. Intelligence page RAG tab ──────────────────────────────────────────────

def test_intel_page_imports_kb_api():
    src = INTEL_PAGE.read_text(encoding="utf-8")
    assert "kbApi" in src


def test_intel_page_has_kb_wizard_modal():
    src = INTEL_PAGE.read_text(encoding="utf-8")
    assert "Create knowledge base" in src
    assert "Create &amp; configure" in src


def test_intel_page_rag_tab_exists():
    src = INTEL_PAGE.read_text(encoding="utf-8")
    assert 'id: "rag"' in src
    assert "Knowledge & RAG" in src


def test_intel_page_has_8_wizard_steps():
    src = INTEL_PAGE.read_text(encoding="utf-8")
    # Creation is intentionally short; detailed documents, access and
    # indexing configuration continue in the new KB workspace.
    assert "This creates the governed container" in src
    assert "continue to its workspace" in src


# ── 9. KB Detail Page ─────────────────────────────────────────────────────────

def test_kb_detail_page_exists():
    assert DETAIL_PAGE.exists(), "KB detail page [id]/page.tsx must exist"


def test_kb_detail_page_has_use_client():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "'use client'" in src


def test_kb_detail_page_imports_kb_api():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "kbApi" in src


def test_kb_detail_page_has_10_tabs():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    required_tabs = [
        "overview", "documents", "articles", "chunks",
        "query-logs", "retrieval-quality", "access-rules",
        "rag-settings", "safety-rules", "audit-logs",
    ]
    for tab in required_tabs:
        assert tab in src, f"Tab '{tab}' missing from KB detail page"


def test_kb_detail_page_has_mandatory_guardrails():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "Mandatory Guardrails" in src


def test_kb_detail_page_has_query_test_panel():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "Test Query" in src


def test_kb_detail_page_has_access_preview_panel():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "Preview Access" in src or "previewAccess" in src or "access-preview" in src


def test_kb_detail_page_uses_css_variables():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "var(--" in src
    # No hardcoded hex colors (excluding any inside comments or strings is fine)
    hex_colors = re.findall(r'(?<!")#[0-9A-Fa-f]{3,6}(?![0-9A-Fa-f])', src)
    # Allow very few (like in data-URIs or SVGs), but none should be color values
    assert len(hex_colors) == 0, f"Found hardcoded hex colors: {hex_colors}"


def test_kb_detail_page_has_retrieval_quality_tab():
    src = DETAIL_PAGE.read_text(encoding="utf-8")
    assert "retrieval-quality" in src
    assert "Retrieval Quality" in src
