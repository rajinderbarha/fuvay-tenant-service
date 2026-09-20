"""A single unstaffed/draft service must not disable every provider service."""

from pathlib import Path

from app.engines.execution.home_services_dashboard_service import (
    _resolve_exact_service_bookability,
)
from app.engines.provider_portal.bookability_query import (
    allows_exact_service_matching,
)


ROOT = Path(__file__).resolve().parents[1]
READINESS = (
    ROOT / "app/engines/home_service_assignment/team_readiness_service.py"
).read_text(encoding="utf-8")
PROVIDER = (ROOT / "app/engines/provider_portal/router.py").read_text(
    encoding="utf-8"
)
CATALOG = (
    ROOT / "app/engines/home_service_booking/offering_catalog_service.py"
).read_text(encoding="utf-8")
MATCHER = (
    ROOT / "app/engines/home_service_booking/matching_engine.py"
).read_text(encoding="utf-8")


def test_only_readiness_snapshot_may_enter_exact_service_matcher():
    assert allows_exact_service_matching(True, []) is True
    assert allows_exact_service_matching(
        False, [{"code": "READY_TECHNICIAN_MISSING"}],
    ) is True
    assert allows_exact_service_matching(
        False,
        [
            {"code": "READY_TECHNICIAN_MISSING"},
            {"code": "USAGE_CREDITS_INSUFFICIENT"},
        ],
    ) is False
    assert allows_exact_service_matching(False, []) is False


def test_dashboard_reconciles_soft_snapshot_only_when_a_service_is_ready():
    stale = {
        "is_bookable": False,
        "blockers": [{"code": "READY_TECHNICIAN_MISSING"}],
    }
    coverage = [
        {"offering_id": "ready", "ready_technician_count": 1},
        {"offering_id": "gap", "ready_technician_count": 0},
    ]

    assert _resolve_exact_service_bookability(stale, coverage) == {
        "is_bookable": True,
        "blockers": [],
    }
    assert _resolve_exact_service_bookability(stale, [coverage[1]]) == stale


def test_provider_gate_requires_any_ready_published_service_not_every_service():
    evaluation = PROVIDER.split("async def _evaluate_provider_bookability", 1)[1]
    assert "staff_capacity_ready = bool(service_coverage) and any(" in evaluation
    assert "staff_capacity_ready = bool(service_coverage) and all(" not in evaluation


def test_draft_and_inactive_services_do_not_create_team_coverage_gaps():
    coverage = READINESS.split("async def compute_service_coverage", 1)[1]
    assert "ts.is_active=true" in coverage
    assert "ts.setup_status='published'" in coverage


def test_postcode_candidates_reach_the_exact_production_matcher():
    candidate_query = CATALOG.split("async def _booking_candidate_pairs", 1)[1].split(
        "async def booking_ready_service_matches", 1,
    )[0]
    assert "latest_provider_bookable" not in candidate_query

    zipcode_publisher = CATALOG.split("def _publisher_filter", 1)[1].split(
        "async def list_serviceable_offerings", 1,
    )[0].split("return MasterService.id.in_(", 2)[-1]
    assert "latest_provider_bookable" not in zipcode_publisher
    assert "allows_exact_service_matching" in MATCHER
