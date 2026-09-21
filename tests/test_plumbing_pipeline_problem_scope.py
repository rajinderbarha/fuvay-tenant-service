"""Regression contract for Plumbing Installation problem branching."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "alembic" / "versions" / "375_scope_plumbing_pipeline_problem.py"
SEED = ROOT / "scripts" / "seed_home_services_and_computer_catalog.py"


def test_pipeline_is_a_distinct_exact_catalog_leaf():
    migration = MIGRATION.read_text(encoding="utf-8")
    assert "plumbing-appliance-pipeline-installation" in migration
    assert "default_service_type_slug" in migration
    assert "New pipeline for appliance" in SEED.read_text(encoding="utf-8")


def test_fixture_questions_are_problem_scoped():
    migration = MIGRATION.read_text(encoding="utf-8")
    assert "cq.question_key IN ('fixture_type', 'commode_type')" in migration
    assert "lower(tap_issue.name)='new tap / fixture installation'" in migration
    assert "'problem', tap_issue.id" in migration


def test_pipeline_is_not_in_fixture_carousel_allowlist():
    migration = MIGRATION.read_text(encoding="utf-8")
    allowlist_line = next(
        line for line in migration.splitlines()
        if "allowed_type_slugs" in line and "plumbing-tap-change" in line
    )
    assert "plumbing-appliance-pipeline-installation" not in allowlist_line
