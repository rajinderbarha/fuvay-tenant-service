"""FINAL-L5-05C Part 4/27 — Admin service_jobs reassignment mutation tests.

Covers the real gap found while building the admin reassign endpoint:
HomeServiceJobAssignmentService._load_staff previously only queried
ProviderTeamMember (unpopulated in real/demo data — real technicians live in
app.engines.auth.models.User). Fixed as part of this sprint (L5-05C-001).
"""
from __future__ import annotations
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _job(tenant_id: uuid.UUID, status: str = "new") -> MagicMock:
    from app.engines.final_records.models import ServiceJob
    j = MagicMock(spec=ServiceJob)
    j.id = uuid.uuid4()
    j.tenant_id = tenant_id
    j.booking_id = uuid.uuid4()
    j.status = status
    j.assignment_status = "unassigned"
    j.assigned_staff_id = None
    j.scheduled_date = None
    j.scheduled_time_window = None
    return j


def _user_staff(tenant_id: uuid.UUID, role: str = "technician", is_active: bool = True) -> MagicMock:
    from app.engines.auth.models import User
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.tenant_id = tenant_id
    u.role = role
    u.is_active = is_active
    return u


def _db_returning(*results) -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    responses = list(results)

    async def _execute(*_a, **_k):
        res = MagicMock()
        val = responses.pop(0)
        res.scalars.return_value.first.return_value = val
        return res

    db.execute = AsyncMock(side_effect=_execute)
    return db


class TestLoadStaffFallsBackToUser:
    @pytest.mark.asyncio
    async def test_load_staff_returns_user_when_provider_team_member_missing(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        tenant_id = uuid.uuid4()
        staff = _user_staff(tenant_id)
        db = _db_returning(None, staff)  # ProviderTeamMember miss, then User hit
        svc = HomeServiceJobAssignmentService(db)
        result = await svc._load_staff(staff.id)
        assert result is staff

    @pytest.mark.asyncio
    async def test_validate_staff_eligibility_accepts_active_technician_user(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        tenant_id = uuid.uuid4()
        job = _job(tenant_id)
        staff = _user_staff(tenant_id, role="technician", is_active=True)
        db = _db_returning(None, staff)
        svc = HomeServiceJobAssignmentService(db)
        loaded, blocked = await svc.validate_staff_eligibility(job, staff.id)
        assert blocked == []
        assert loaded is staff

    @pytest.mark.asyncio
    async def test_validate_staff_eligibility_blocks_inactive_user(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        tenant_id = uuid.uuid4()
        job = _job(tenant_id)
        staff = _user_staff(tenant_id, role="technician", is_active=False)
        db = _db_returning(None, staff)
        svc = HomeServiceJobAssignmentService(db)
        _, blocked = await svc.validate_staff_eligibility(job, staff.id)
        assert "staff_inactive" in blocked

    @pytest.mark.asyncio
    async def test_validate_staff_eligibility_blocks_wrong_tenant_user(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        job = _job(uuid.uuid4())
        staff = _user_staff(uuid.uuid4(), role="technician")  # different tenant
        db = _db_returning(None, staff)
        svc = HomeServiceJobAssignmentService(db)
        _, blocked = await svc.validate_staff_eligibility(job, staff.id)
        assert "wrong_tenant" in blocked

    @pytest.mark.asyncio
    async def test_validate_staff_eligibility_blocks_non_eligible_role(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        tenant_id = uuid.uuid4()
        job = _job(tenant_id)
        staff = _user_staff(tenant_id, role="customer")
        db = _db_returning(None, staff)
        svc = HomeServiceJobAssignmentService(db)
        _, blocked = await svc.validate_staff_eligibility(job, staff.id)
        assert "role_not_allowed" in blocked


class TestAdminReassignErrorMap:
    def test_error_map_covers_mission_required_codes(self):
        from app.engines.home_service_assignment.admin_router import _REASSIGN_ERROR_MAP
        codes = {c for _, c in _REASSIGN_ERROR_MAP.values()}
        assert "JOB_REASSIGN_FORBIDDEN" in codes
        assert "JOB_REASSIGN_NOT_ALLOWED" in codes
        assert "TECHNICIAN_TENANT_MISMATCH" in codes
        assert "TECHNICIAN_NOT_ELIGIBLE" in codes

    def test_admin_jobs_router_exposes_reassign_route(self):
        from app.engines.home_service_assignment.admin_router import admin_jobs_router
        paths = [r.path for r in admin_jobs_router.routes]
        assert "/v1/admin/service-jobs/{job_id}/reassign" in paths
