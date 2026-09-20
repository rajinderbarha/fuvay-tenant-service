"""Provider Bookings & Jobs is an active/completed work board, not an archive."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app/engines/final_records/tenant_bookings_jobs_router.py"
PAGE = (
    ROOT
    / "frontend/tenant-portal/app/(tenant)/home-services/bookings-jobs/BookingsJobsPage.tsx"
)


def test_cancelled_jobs_are_filtered_before_pagination_and_counting():
    source = ROUTER.read_text(encoding="utf-8")

    assert 'PROVIDER_LIST_HIDDEN_STATUSES = ("cancelled",)' in source
    # Main row query, matching count query, and job-type filter options must
    # all use the same visibility boundary.
    assert source.count(
        "ServiceJob.status.notin_(PROVIDER_LIST_HIDDEN_STATUSES)"
    ) == 3


def test_cancelled_deep_link_is_closed_defensively_in_provider_workspace():
    source = PAGE.read_text(encoding="utf-8")

    assert 'detail.data?.job.status === "cancelled"' in source
    assert "updateParams({ job_id: null });" in source
