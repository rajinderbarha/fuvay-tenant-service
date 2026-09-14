"""Regression coverage for service-scoped Instagram problem cards."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_problem_queries_exclude_archived_cross_service_mappings():
    backend = (ROOT / "app/engines/ai_conversation/backend_tools.py").read_text(
        encoding="utf-8"
    )
    catalog = (
        ROOT / "app/engines/home_service_booking/offering_catalog_service.py"
    ).read_text(encoding="utf-8")
    start = (ROOT / "app/engines/home_service_booking/service.py").read_text(
        encoding="utf-8"
    )

    assert "ServiceIssueMapping.master_service_id == draft.offering_id" in backend
    assert "ServiceIssueMapping.deleted_at.is_(None)" in backend
    assert "MasterIssueType.customer_visible == True" in backend
    assert "ServiceIssueMapping.deleted_at.is_(None)" in catalog
    assert "ServiceIssueMapping.deleted_at.is_(None)" in start


def test_data_repair_retires_dripping_tap_only_outside_plumbing():
    migration = (
        ROOT / "alembic/versions/367_repair_problem_service_scope.py"
    ).read_text(encoding="utf-8")

    assert "dripping_tap" in migration
    assert "service_issue_mappings" in migration
    assert "service.slug" in migration and "<> 'plumbing'" in migration
    assert "customer_visible = false" in migration
