"""Regression contract for the canonical provider Dispatch workspace."""
from __future__ import annotations

import datetime as dt
import inspect
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend/tenant-portal/app/(tenant)/home-services/dispatch/page.tsx"
API = ROOT / "frontend/tenant-portal/lib/api-tenant-workspaces.ts"
NAV = ROOT / "frontend/tenant-portal/lib/nav-config.ts"
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
    legacy = LEGACY.read_text(encoding="utf-8")
    assert 'href: "/home-services/dispatch"' in nav
    assert 'redirect("/home-services/dispatch")' in legacy


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


def test_projection_uses_canonical_status_and_bounded_queries():
    from app.engines.home_service_assignment.dispatch_service import HomeServiceDispatchProjectionService

    source = inspect.getsource(HomeServiceDispatchProjectionService.get_dispatch_projection)
    assert 'job.status == "on_the_way"' in source
    assert ".limit(limit).offset(offset)" in source
    assert "schedule_cap = 5000" in source
    assert "TERMINAL_STATUSES" in source
