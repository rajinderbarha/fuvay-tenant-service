"""Regression contract for Plumbing Installation problem branching."""
from pathlib import Path
import uuid

from unittest.mock import MagicMock

from app.engines.admin_catalog.question_service import CatalogQuestionService


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


def test_commode_followup_requires_fixture_problem_and_commode_answer():
    resolver = CatalogQuestionService(db=MagicMock())
    fixture_problem, pipeline_problem, fixture_question = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    rules = [
        {"condition_type": "problem", "ref_id": str(fixture_problem)},
        {"condition_type": "answer_equals", "ref_id": str(fixture_question),
         "expected_value": "plumbing-commode-installation"},
    ]
    assert resolver._rules_pass(rules, None, fixture_problem, set(),
                                {"fixture_type": "plumbing-commode-installation"})
    for selected_problem, selection in [
        (fixture_problem, "plumbing-tap-change"),
        (fixture_problem, "plumbing-wash-basin-installation"),
        (pipeline_problem, "plumbing-commode-installation"),
    ]:
        assert not resolver._rules_pass(rules, None, selected_problem, set(), {"fixture_type": selection})
