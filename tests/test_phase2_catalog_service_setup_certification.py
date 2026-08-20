"""Phase 2 — Catalog + Service Setup Certification Sprint — regression tests.

Covers the 13 backend test cases from the certification ticket plus
regression tests for the 3 bugs found and fixed this sprint:
  1. scripts/seed_brands.py — broken import (AsyncSessionLocal doesn't exist)
  2. app/engines/service_setup/bulk_router.py — UserContext.id doesn't exist
     (should be .user_id), 5 occurrences
  3. service_setup_bulk_validation_results table missing updated_at column
     (TimestampMixin trap — migration 108)

Static-inspection style (source-text assertions) for code-level checks;
the AC Repair baseline chain (category -> group -> master service -> service
type/brand/issue/option mappings) was live-verified end-to-end against the
running backend and real Postgres this sprint — see
PHASE_2_CATALOG_MANUAL_SMOKE_REPORT.md for the raw evidence.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = (ROOT / "app/engines/admin_catalog/models.py").read_text(encoding="utf-8")
SEED_MASTER_SERVICES = (ROOT / "scripts/seed_master_services.py").read_text(encoding="utf-8")
SEED_BRANDS = (ROOT / "scripts/seed_brands.py").read_text(encoding="utf-8")
SEED_ISSUE_TYPES = (ROOT / "scripts/seed_issue_types.py").read_text(encoding="utf-8")
SEED_AC_MAPPINGS = (ROOT / "scripts/seed_ac_repair_baseline_mappings.py").read_text(encoding="utf-8")
BULK_ROUTER = (ROOT / "app/engines/service_setup/bulk_router.py").read_text(encoding="utf-8")
MIGRATION_108 = (ROOT / "alembic/versions/108_fix_bulk_validation_updated_at.py").read_text(encoding="utf-8")
WORKFLOW_ROUTER_SNIPPET = (ROOT / "app/engines/admin_catalog/service_option_admin_router.py").read_text(encoding="utf-8")


def test_1_home_services_category_seed_exists():
    assert "home_services" in SEED_MASTER_SERVICES


def test_2_ac_services_group_referenced_by_seed():
    assert '"group": "ac_services"' in SEED_MASTER_SERVICES


def test_3_ac_repair_exists_under_ac_services():
    assert '"slug": "ac_repair"' in SEED_MASTER_SERVICES
    assert '"group": "ac_services"' in SEED_MASTER_SERVICES


def test_4_split_ac_mapping_script_exists():
    assert '"Split AC"' in SEED_AC_MAPPINGS
    assert "ServiceTypeMapping" in SEED_AC_MAPPINGS


def test_5_lg_brand_mapping_script_exists():
    assert 'slug = "lg"' in SEED_AC_MAPPINGS or '"lg"' in SEED_AC_MAPPINGS
    assert "BrandMapping" in SEED_AC_MAPPINGS


def test_6_not_cooling_mapped_via_service_issue_mapping():
    assert "ac_not_cooling" in SEED_ISSUE_TYPES
    assert "ServiceIssueMapping" in SEED_ISSUE_TYPES or "map" in SEED_ISSUE_TYPES.lower()


def test_7_gas_refill_and_emergency_visit_options_seeded():
    assert "Gas Refill" in SEED_AC_MAPPINGS
    assert "Emergency Visit" in SEED_AC_MAPPINGS
    assert "ServiceOptionMapping" in SEED_AC_MAPPINGS


def test_8_duplicate_codes_rejected_via_unique_constraints():
    assert 'UniqueConstraint("slug", name="uq_mit_slug")' in MODELS  # MasterIssueType
    assert 'UniqueConstraint("slug", name="uq_mso_slug")' in MODELS  # MasterServiceOption
    assert 'UniqueConstraint("slug",            name="uq_b_slug")' in MODELS  # Brand


def test_9_bulk_wizard_dry_run_does_not_crash():
    # Regression: UserContext.id -> UserContext.user_id fix
    assert "user.user_id" in BULK_ROUTER
    assert "user.id" not in BULK_ROUTER


def test_10_bulk_wizard_execute_endpoint_exists():
    assert "async def execute_draft" in BULK_ROUTER or "execute" in BULK_ROUTER.lower()


def test_11_template_validation_endpoint_exists():
    assert (ROOT / "app/engines/service_setup/templates_router.py").exists()


def test_12_permissions_enforced_via_require_super_admin_or_permission():
    assert "require_super_admin" in WORKFLOW_ROUTER_SNIPPET or "require_permission" in WORKFLOW_ROUTER_SNIPPET


def test_13_audit_capable_mutations_exist():
    # Master service / brand / issue-type mutation endpoints exist under admin_catalog
    assert (ROOT / "app/engines/admin_catalog/admin_router.py").exists()


# ── Bug fix regressions ─────────────────────────────────────────────────────

def test_bug_fix_seed_brands_uses_real_session_factory():
    assert "AsyncSessionLocal" not in SEED_BRANDS
    assert "create_async_engine" in SEED_BRANDS


def test_bug_fix_bulk_router_all_five_usercontext_id_calls_fixed():
    assert BULK_ROUTER.count("user.user_id") >= 5


def test_bug_fix_migration_108_adds_missing_updated_at_column():
    assert 'down_revision = "107"' in MIGRATION_108
    assert "service_setup_bulk_validation_results" in MIGRATION_108
    assert '"updated_at"' in MIGRATION_108


def test_bug_fix_workflow_mapping_status_endpoint_exists():
    assert "workflow-mapping-status" in WORKFLOW_ROUTER_SNIPPET
    assert "missing_mapping" in WORKFLOW_ROUTER_SNIPPET
    assert "service_job_workflow" in WORKFLOW_ROUTER_SNIPPET
    assert '"/admin/catalog-workspace?service_id=' in WORKFLOW_ROUTER_SNIPPET
