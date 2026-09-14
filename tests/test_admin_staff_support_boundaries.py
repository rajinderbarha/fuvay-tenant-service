"""Regression coverage for the admin staff and provider-support boundaries."""
from inspect import getsource, signature
from types import SimpleNamespace

from app.engines.support.admin_router import queue, router as support_admin_router
from app.engines.vertical_directory.service import (
    VerticalStaffDirectoryService,
    _ACTIVE_JOB_STATUSES,
    _WORK_IN_PROGRESS_JOB_STATUSES,
)


def _member(*, availability_state="available", can_receive_assignment=True, status="active"):
    return SimpleNamespace(
        availability_state=availability_state,
        can_receive_assignment=can_receive_assignment,
        status=status,
    )


def test_assigned_job_is_not_reported_as_work_in_progress():
    service = VerticalStaffDirectoryService()
    assert service._derive_availability(_member(), None, 1, 0) == "assigned"


def test_started_work_is_reported_as_on_job():
    service = VerticalStaffDirectoryService()
    assert service._derive_availability(_member(), None, 1, 1) == "on_job"


def test_stale_on_job_projection_clears_without_live_work():
    service = VerticalStaffDirectoryService()
    assert service._derive_availability(
        _member(availability_state="on_job"), None, 0, 0
    ) == "available"


def test_restriction_wins_over_job_state():
    service = VerticalStaffDirectoryService()
    assert service._derive_availability(
        _member(can_receive_assignment=False), None, 1, 1
    ) == "unavailable"


def test_only_real_work_states_are_in_work_in_progress_set():
    assert "assigned" in _ACTIVE_JOB_STATUSES
    assert "assigned" not in _WORK_IN_PROGRESS_JOB_STATUSES
    assert "on_the_way" not in _WORK_IN_PROGRESS_JOB_STATUSES
    assert {"inspection_started", "service_started"}.issubset(
        _WORK_IN_PROGRESS_JOB_STATUSES
    )


def test_admin_support_exposes_read_only_status_and_server_assignee_filter():
    methods_by_path = {
        route.path: route.methods for route in support_admin_router.routes
        if hasattr(route, "methods")
    }
    assert "GET" in methods_by_path["/v1/admin/support/status"]
    assert "assignee" in signature(queue).parameters


def test_staff_activity_is_scoped_to_the_selected_staff_record():
    source = getsource(VerticalStaffDirectoryService.get_activity)
    assert "PlatformAuditLog.entity_id == entity_id" in source
    assert "PlatformAuditLog.tenant_id == ptm.tenant_id" in source
