"""Regression contract for the canonical provider Dispatch workspace."""
from __future__ import annotations

import datetime as dt
import inspect
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend/tenant-portal/app/(tenant)/home-services/dispatch/DispatchPage.tsx"
API = ROOT / "frontend/tenant-portal/lib/api-tenant-workspaces.ts"
NAV = ROOT / "frontend/tenant-portal/components/layout/TenantLayout.tsx"
LEGACY = ROOT / "frontend/tenant-portal/app/(tenant)/dispatch/page.tsx"


def test_dispatch_page_has_no_dead_week_or_review_controls():
    source = PAGE.read_text(encoding="utf-8")
    assert "Week view isn&apos;t built yet" not in source
    assert 'view === "week"' in source
    assert "WeekSchedule" in source
    assert "Review unassigned" not in source


def test_dispatch_filters_and_pagination_are_url_backed():
    source = PAGE.read_text(encoding="utf-8")
    for key in ("search", "service", "technician", "focus", "page", "page_size", "job_id"):
        assert f'params.get("{key}")' in source or f"{key}:" in source
    assert "<Pagination" in source
    assert "offering_id" in source and "technician_id" in source


def test_dispatch_navigation_uses_only_canonical_home_services_route():
    nav = NAV.read_text(encoding="utf-8")
    assert 'href: "/home-services/dispatch"' in nav
    assert not LEGACY.exists()


def test_dispatch_mutations_surface_inner_http_200_failures():
    source = API.read_text(encoding="utf-8")
    assert "requireDispatchMutationSuccess" in source
    assert "DISPATCH_ACTION_FAILED" in source
    assert ".then(requireDispatchMutationSuccess)" in source


def test_schedule_rechecks_slot_capacity_before_moving_commitment():
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    source = inspect.getsource(HomeServiceJobAssignmentService.schedule_job)
    assert "slot_has_capacity" in source
    assert "ERR_SLOT_UNAVAILABLE" in source


@pytest.mark.asyncio
async def test_schedule_rejects_a_slot_that_lost_capacity(monkeypatch):
    from app.engines.home_service_assignment.constants import ERR_SLOT_UNAVAILABLE
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
    from app.engines.home_service_booking import provider_slot_service

    tenant_id = uuid.uuid4()
    job = MagicMock(
        id=uuid.uuid4(), tenant_id=tenant_id, status="assigned",
        offering_id=uuid.uuid4(), scheduled_date=None,
        scheduled_time_window=None,
    )
    result = MagicMock()
    result.scalars.return_value.first.return_value = job
    db = AsyncMock()
    db.execute.return_value = result
    monkeypatch.setattr(
        provider_slot_service,
        "slot_has_capacity",
        AsyncMock(return_value=False),
    )

    with pytest.raises(ValueError, match=ERR_SLOT_UNAVAILABLE):
        await HomeServiceJobAssignmentService(db).schedule_job(
            job.id, tenant_id, dt.date(2026, 8, 22), "10:00-12:00",
        )


@pytest.mark.asyncio
async def test_conflict_resolution_detects_overlapping_not_only_equal_windows():
    from app.engines.home_service_assignment.dispatch_service import HomeServiceDispatchProjectionService

    tenant_id = uuid.uuid4()
    staff_id = uuid.uuid4()
    job = MagicMock(
        id=uuid.uuid4(), scheduled_date=dt.date(2026, 8, 21),
        scheduled_time_window="09:00-11:00",
    )
    overlap = MagicMock(
        assigned_staff_member_id=staff_id,
        scheduled_date=dt.date(2026, 8, 21),
        scheduled_time_window="10:30-12:00",
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [overlap]
    db = AsyncMock()
    db.execute.return_value = result

    conflicts = await HomeServiceDispatchProjectionService(db)._conflicting_staff_ids(
        tenant_id, job, [staff_id],
    )

    assert conflicts == {staff_id}
    assert db.execute.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("existing_date", "existing_window"),
    [
        (dt.date(2026, 9, 13), "09:00-11:00"),
        (dt.date(2026, 9, 14), "07:00-09:00"),
        (dt.date(2026, 9, 14), "11:00-13:00"),
    ],
)
async def test_open_job_on_another_date_or_consecutive_slot_does_not_block_assignment(
    existing_date, existing_window,
):
    """Regression for the live Test Provider contradiction.

    Dispatch showed four open slots for the technician on 14 September but
    excluded them merely because any other open job existed. Calendar work is
    sequential: only an overlapping visit on the same date is a conflict.
    """
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    tenant_id = uuid.uuid4()
    staff_id = uuid.uuid4()
    job = MagicMock(
        id=uuid.uuid4(), tenant_id=tenant_id,
        scheduled_date=dt.date(2026, 9, 14),
        scheduled_time_window="09:00-11:00",
    )
    result = MagicMock()
    result.all.return_value = [(existing_date, existing_window)]
    db = AsyncMock()
    db.execute.return_value = result

    reason = await HomeServiceJobAssignmentService(db).staff_assignment_conflict_reason(
        job, staff_id, exclude_job_id=job.id,
    )

    assert reason is None


@pytest.mark.asyncio
async def test_overlapping_job_still_blocks_assignment_with_precise_reason():
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    tenant_id = uuid.uuid4()
    staff_id = uuid.uuid4()
    job = MagicMock(
        id=uuid.uuid4(), tenant_id=tenant_id,
        scheduled_date=dt.date(2026, 9, 14),
        scheduled_time_window="09:00-11:00",
    )
    result = MagicMock()
    result.all.return_value = [(dt.date(2026, 9, 14), "10:30-12:00")]
    db = AsyncMock()
    db.execute.return_value = result

    reason = await HomeServiceJobAssignmentService(db).staff_assignment_conflict_reason(
        job, staff_id, exclude_job_id=job.id,
    )

    assert reason == "schedule_conflict"


@pytest.mark.asyncio
async def test_unscheduled_job_retains_safe_open_work_fallback():
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    job = MagicMock(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        scheduled_date=None, scheduled_time_window=None,
    )
    service = HomeServiceJobAssignmentService(AsyncMock())
    service.staff_has_open_job = AsyncMock(return_value=True)

    reason = await service.staff_assignment_conflict_reason(
        job, uuid.uuid4(), exclude_job_id=job.id,
    )

    assert reason == "active_job_in_progress"


def test_assignment_mutation_uses_visit_conflict_instead_of_blanket_open_job_gate():
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    source = inspect.getsource(HomeServiceJobAssignmentService.assign_job)
    assert "staff_assignment_conflict_reason" in source
    assert "and not has_timed_slot" in source


def test_projection_uses_canonical_status_and_bounded_queries():
    from app.engines.home_service_assignment.dispatch_service import HomeServiceDispatchProjectionService

    source = inspect.getsource(HomeServiceDispatchProjectionService.get_dispatch_projection)
    assert 'job.status == "on_the_way"' in source
    assert ".limit(limit).offset(offset)" in source
    assert "schedule_cap = 5000" in source
    assert "TERMINAL_STATUSES" in source
    assert "ServiceJob.assigned_staff_id.is_(None)" in source
    assert "ServiceJob.assignment_status == \"unassigned\"" not in source
    assert "ServiceJob.assigned_staff_id.is_not(None)" in source
    assert "func.coalesce" in source
    assert 'entry.get("is_overdue")' in source
    assert '"sla_breached_count"' in source


def test_provider_workspace_links_stay_in_home_services():
    bookings_page = (
        ROOT / "frontend/tenant-portal/app/(tenant)/home-services/bookings-jobs/BookingsJobsPage.tsx"
    ).read_text(encoding="utf-8")
    dispatch_page = PAGE.read_text(encoding="utf-8")

    assert "router.push(dispatchUrl)" in bookings_page
    assert "`/home-services/bookings-jobs?job_id=${selectedJobId}`" in dispatch_page
    assert "router.push(`/service-jobs/${selectedJobId}`)" not in dispatch_page


def test_provider_acceptance_does_not_fabricate_a_technician_assignment():
    from app.engines.final_records.creation_service import HomeServiceFinalCreationService

    source = inspect.getsource(HomeServiceFinalCreationService.finalize)
    assert 'assignment_status = "unassigned"' in source
    assert 'assignment_status = "accepted" if auto_accept' not in source


def test_dispatch_projects_real_technician_photos_with_ui_fallbacks():
    from app.engines.home_service_assignment.dispatch_service import HomeServiceDispatchProjectionService
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    projection = inspect.getsource(HomeServiceDispatchProjectionService)
    eligibility = inspect.getsource(HomeServiceJobAssignmentService.list_eligible_staff_for_job)
    page = PAGE.read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")

    assert '"profile_photo_url"' in projection
    assert '"profile_photo_url"' in eligibility
    assert "profile_photo_url?: string | null" in api
    assert "<DefaultAvatar" in page
    assert "src={technician.profile_photo_url}" in page


def test_dispatch_job_cards_include_service_icon_slot_and_service_address():
    from app.engines.home_service_assignment.dispatch_service import HomeServiceDispatchProjectionService

    projection = inspect.getsource(HomeServiceDispatchProjectionService)
    page = PAGE.read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")

    assert "MasterService.icon_url" in projection
    assert '"requested_time_window"' in projection
    assert '"customer_address"' in projection
    assert "service_icon_url?: string | null" in api
    assert "<ServiceJobIcon job={job}" in page
    assert "job.customer_address || job.locality" in page


def test_assignment_notification_resolves_team_member_login_identity():
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    source = inspect.getsource(HomeServiceJobAssignmentService._notify_staff_assigned)
    assert "ProviderTeamMember.user_id" in source
    assert "user_id=recipient_user_id" in source
