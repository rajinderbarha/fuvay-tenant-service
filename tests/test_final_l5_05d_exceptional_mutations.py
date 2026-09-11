"""FINAL-L5-05D — status override / force-close / void against service_jobs.

Live-verified via curl against real data (see docs/final-l5-05/
FINAL_L5_05D_JOBS_EXCEPTIONAL_MUTATIONS.md); these are the corresponding
unit/contract tests for the policy service and router wiring.
"""
from __future__ import annotations
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _job(tenant_id: uuid.UUID, status: str = "assigned") -> MagicMock:
    from app.engines.final_records.models import ServiceJob
    j = MagicMock(spec=ServiceJob)
    j.id = uuid.uuid4()
    j.tenant_id = tenant_id
    j.booking_id = uuid.uuid4()
    j.assigned_staff_id = None
    j.status = status
    j.completion_data = None
    return j


def _db_returning(*results) -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    responses = list(results)

    async def _execute(*_a, **_k):
        res = MagicMock()
        val = responses.pop(0)
        res.scalars.return_value.first.return_value = val
        return res

    db.execute = AsyncMock(side_effect=_execute)
    return db


class TestAllowedOverrideTargets:
    def test_non_terminal_status_allows_cancelled(self):
        from app.engines.execution.admin_job_actions import AdminJobActionsService
        svc = AdminJobActionsService(AsyncMock())
        assert svc.get_allowed_override_targets("assigned") == ["cancelled"]

    def test_terminal_status_allows_only_explicit_recovery(self):
        from app.engines.execution.admin_job_actions import AdminJobActionsService
        svc = AdminJobActionsService(AsyncMock())
        for status in ("completed", "force_closed", "voided"):
            assert svc.get_allowed_override_targets(status) == []
        for status in ("cancelled", "failed"):
            assert svc.get_allowed_override_targets(status) == ["pending_assignment"]


class TestStatusOverride:
    @pytest.mark.asyncio
    async def test_reason_required(self):
        from app.engines.execution.admin_job_actions import AdminJobActionsService
        svc = AdminJobActionsService(AsyncMock())
        with pytest.raises(Exception) as exc:
            await svc.override_status(uuid.uuid4(), "cancelled", "assigned", "code", "",
                                       uuid.uuid4(), "super_admin", "req-1")
        assert exc.value.error_code == "REASON_REQUIRED"

    @pytest.mark.asyncio
    async def test_stale_expected_status_conflicts(self):
        from app.engines.execution.admin_job_actions import AdminJobActionsService
        job = _job(uuid.uuid4(), status="cancelled")
        db = _db_returning(job)
        svc = AdminJobActionsService(db)
        with pytest.raises(Exception) as exc:
            await svc.override_status(job.id, "cancelled", "assigned", "code", "real reason",
                                       uuid.uuid4(), "super_admin", "req-1")
        assert exc.value.error_code == "JOB_STATUS_CONFLICT"

    @pytest.mark.asyncio
    async def test_terminal_job_cannot_be_overridden(self):
        from app.engines.execution.admin_job_actions import AdminJobActionsService
        job = _job(uuid.uuid4(), status="completed")
        db = _db_returning(job)
        svc = AdminJobActionsService(db)
        with pytest.raises(Exception) as exc:
            await svc.override_status(job.id, "cancelled", "completed", "code", "real reason",
                                       uuid.uuid4(), "super_admin", "req-1")
        assert exc.value.error_code == "JOB_ALREADY_TERMINAL"

    @pytest.mark.asyncio
    async def test_disallowed_target_rejected(self):
        from app.engines.execution.admin_job_actions import AdminJobActionsService
        job = _job(uuid.uuid4(), status="assigned")
        db = _db_returning(job)
        svc = AdminJobActionsService(db)
        with pytest.raises(Exception) as exc:
            await svc.override_status(job.id, "completed", "assigned", "code", "real reason",
                                       uuid.uuid4(), "super_admin", "req-1")
        assert exc.value.error_code == "INVALID_ADMIN_OVERRIDE_TRANSITION"

    @pytest.mark.asyncio
    async def test_success_mutates_status_and_logs_event(self, monkeypatch):
        from app.engines.execution import admin_job_actions
        job = _job(uuid.uuid4(), status="assigned")
        db = _db_returning(job)
        audit_calls = []
        async def fake_audit(*a, **kw): audit_calls.append(kw)
        monkeypatch.setattr(admin_job_actions, "record_platform_audit", fake_audit)
        svc = admin_job_actions.AdminJobActionsService(db)
        result = await svc.override_status(job.id, "cancelled", "assigned", "stuck", "real reason",
                                             uuid.uuid4(), "super_admin", "req-1")
        assert result["new_status"] == "cancelled"
        assert job.status == "cancelled"
        assert len(audit_calls) == 1
        assert audit_calls[0]["operation"] == "service_job.status_overridden"


class TestForceClose:
    @pytest.mark.asyncio
    async def test_already_closed_conflicts(self):
        from app.engines.execution.admin_job_actions import AdminJobActionsService
        job = _job(uuid.uuid4(), status="force_closed")
        db = _db_returning(job)
        svc = AdminJobActionsService(db)
        with pytest.raises(Exception) as exc:
            await svc.force_close(job.id, "force_closed", "code", "real reason", None,
                                   uuid.uuid4(), "super_admin", "req-1")
        assert exc.value.error_code == "JOB_ALREADY_CLOSED"

    @pytest.mark.asyncio
    async def test_terminal_job_cannot_be_force_closed(self):
        from app.engines.execution.admin_job_actions import AdminJobActionsService
        job = _job(uuid.uuid4(), status="cancelled")
        db = _db_returning(job)
        svc = AdminJobActionsService(db)
        with pytest.raises(Exception) as exc:
            await svc.force_close(job.id, "cancelled", "code", "real reason", None,
                                   uuid.uuid4(), "super_admin", "req-1")
        assert exc.value.error_code == "JOB_FORCE_CLOSE_NOT_ALLOWED"

    @pytest.mark.asyncio
    async def test_success_never_creates_deduction(self, monkeypatch):
        from app.engines.execution import admin_job_actions
        job = _job(uuid.uuid4(), status="in_progress")
        db = _db_returning(job)
        async def fake_audit(*a, **kw): pass
        monkeypatch.setattr(admin_job_actions, "record_platform_audit", fake_audit)
        svc = admin_job_actions.AdminJobActionsService(db)
        result = await svc.force_close(job.id, "in_progress", "unrecoverable", "real reason", "note",
                                        uuid.uuid4(), "super_admin", "req-1")
        assert result["new_status"] == "force_closed"
        assert result["deduction_created"] is False
        assert job.status == "force_closed"
        assert job.completion_data == {"force_close_note": "note"}


class TestVoid:
    @pytest.mark.asyncio
    async def test_already_voided_conflicts(self):
        from app.engines.execution.admin_job_actions import AdminJobActionsService
        job = _job(uuid.uuid4(), status="voided")
        db = _db_returning(job)
        svc = AdminJobActionsService(db)
        with pytest.raises(Exception) as exc:
            await svc.void(job.id, "voided", "code", "real reason", uuid.uuid4(), "super_admin", "req-1")
        assert exc.value.error_code == "JOB_ALREADY_VOIDED"

    @pytest.mark.asyncio
    async def test_blocked_when_deduction_exists(self, monkeypatch):
        from app.engines.execution import admin_job_actions
        job = _job(uuid.uuid4(), status="completed")
        db = _db_returning(job)
        svc = admin_job_actions.AdminJobActionsService(db)
        monkeypatch.setattr(svc, "_has_deduction", AsyncMock(return_value=True))
        with pytest.raises(Exception) as exc:
            await svc.void(job.id, "completed", "code", "real reason", uuid.uuid4(), "super_admin", "req-1")
        assert exc.value.error_code == "JOB_DEDUCTION_REVERSAL_REQUIRED"

    @pytest.mark.asyncio
    async def test_success_when_no_deduction(self, monkeypatch):
        from app.engines.execution import admin_job_actions
        job = _job(uuid.uuid4(), status="new")
        db = _db_returning(job)
        async def fake_audit(*a, **kw): pass
        monkeypatch.setattr(admin_job_actions, "record_platform_audit", fake_audit)
        svc = admin_job_actions.AdminJobActionsService(db)
        monkeypatch.setattr(svc, "_has_deduction", AsyncMock(return_value=False))
        result = await svc.void(job.id, "new", "duplicate", "real reason", uuid.uuid4(), "super_admin", "req-1")
        assert result["new_status"] == "voided"
        assert job.status == "voided"


class TestRouterWiring:
    def test_admin_router_exposes_all_four_endpoints(self):
        from app.engines.execution.home_service_router import admin_router
        paths = {r.path for r in admin_router.routes}
        assert "/v1/admin/service-jobs/{job_id}/allowed-override-targets" in paths
        assert "/v1/admin/service-jobs/{job_id}/status-override" in paths
        assert "/v1/admin/service-jobs/{job_id}/force-close" in paths
        assert "/v1/admin/service-jobs/{job_id}/void" in paths
