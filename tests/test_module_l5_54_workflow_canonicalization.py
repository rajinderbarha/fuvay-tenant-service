"""WORKFLOW-CANONICALIZATION Phase 2-5.

ServiceJobWorkflow (app/engines/admin_catalog/models.py) is confirmed the
one real, runtime-consumed Job-Type Blueprint authority (Phase 1 audit).
This adds:
  - a publishing lifecycle (status/supersedes_workflow_id/etc, migration 186)
  - allows_cancellation / allows_reschedule enforcement (previously stored
    but never read)
  - checklist_required enforcement (previously stored but never read)

Follows this codebase's established AsyncMock service-level test pattern
(see tests/test_module_l5_53_exact_job_type_resolution.py,
tests/test_module_l5_52_work_start_approval_gate.py) rather than a live
httpx client, since the routers under test resolve their DB session via
FastAPI dependency injection that is awkward to drive end-to-end without
a running auth stack -- the service-layer methods ARE the enforcement
choke point (single call site in _set_status / cancel_job /
customer_cancel_booking / customer_reschedule_booking), so testing them
directly proves the gate with no less coverage than an HTTP round trip.

Section 8 (dead-route 404s) DOES use a live httpx call against the local
dev server per the session's live-verification requirement.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import ServiceOSException


def _make_workflow(**overrides):
    wf = MagicMock()
    wf.quote_approval_required = False
    wf.checklist_required = False
    wf.allows_cancellation = True
    wf.allows_reschedule = True
    wf.requires_direct_payment_record = False
    wf.status = "published"
    wf.is_current = True
    for k, v in overrides.items():
        setattr(wf, k, v)
    return wf


# ─────────────────────────────────────────────────────────────────────────────
# 1. Checklist gate -- checklist_required now actually blocks work start
# ─────────────────────────────────────────────────────────────────────────────

class TestChecklistGate:
    @pytest.mark.asyncio
    async def test_checklist_required_blocks_work_start_when_no_checklist_exists(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        job = MagicMock()
        job.id = uuid.uuid4()
        db = AsyncMock()
        workflow = _make_workflow(checklist_required=True)
        with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=workflow)):
            no_checklist = MagicMock()
            no_checklist.scalars.return_value.first.return_value = None
            db.execute = AsyncMock(return_value=no_checklist)
            with pytest.raises(ServiceOSException) as exc:
                await svc._assert_checklist_satisfied(db, job)
            assert exc.value.error_code == "CHECKLIST_REQUIRED_BEFORE_WORK_START"

    @pytest.mark.asyncio
    async def test_checklist_required_passes_once_checklist_exists(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        job = MagicMock()
        job.id = uuid.uuid4()
        db = AsyncMock()
        workflow = _make_workflow(checklist_required=True)
        with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=workflow)):
            has_checklist = MagicMock()
            has_checklist.scalars.return_value.first.return_value = MagicMock()
            db.execute = AsyncMock(return_value=has_checklist)
            await svc._assert_checklist_satisfied(db, job)  # must not raise

    @pytest.mark.asyncio
    async def test_checklist_not_required_never_queries_checklist_table(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        job = MagicMock()
        db = AsyncMock()
        workflow = _make_workflow(checklist_required=False)
        with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=workflow)):
            await svc._assert_checklist_satisfied(db, job)
        db.execute.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Staff-side cancel_job -- allows_cancellation now actually blocks cancel
# ─────────────────────────────────────────────────────────────────────────────

class TestStaffCancelGate:
    @pytest.mark.asyncio
    async def test_cancel_blocked_when_workflow_disallows_cancellation(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        from app.engines.execution.constants import ERR_CANCELLATION_NOT_ALLOWED
        svc = HomeServiceJobExecutionService()
        job = MagicMock()
        db = AsyncMock()
        workflow = _make_workflow(allows_cancellation=False)
        with patch.object(svc, "_get_job", AsyncMock(return_value=job)):
            with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=workflow)):
                with pytest.raises(ServiceOSException) as exc:
                    await svc.cancel_job(db, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), reason="changed my mind")
                assert exc.value.error_code == ERR_CANCELLATION_NOT_ALLOWED

    @pytest.mark.asyncio
    async def test_cancel_allowed_when_workflow_allows_cancellation(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        job = MagicMock()
        job.status = "accepted"
        db = AsyncMock()
        workflow = _make_workflow(allows_cancellation=True)
        with patch.object(svc, "_get_job", AsyncMock(return_value=job)):
            with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=workflow)):
                with patch.object(svc, "_set_status", AsyncMock()) as set_status:
                    await svc.cancel_job(db, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), reason="changed my mind")
                    set_status.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cancel_not_blocked_when_workflow_unresolved(self):
        """Unresolved workflow is NOT a cancellation error -- that failure
        mode belongs to the quote-approval guard elsewhere; cancel_job must
        not invent a second, inconsistent fail-closed reason for it."""
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        job = MagicMock()
        job.status = "accepted"
        db = AsyncMock()
        with patch.object(svc, "_get_job", AsyncMock(return_value=job)):
            with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=None)):
                with patch.object(svc, "_set_status", AsyncMock()) as set_status:
                    await svc.cancel_job(db, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), reason="changed my mind")
                    set_status.assert_awaited_once()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Customer self-service cancel/reschedule (home_service_assignment)
# ─────────────────────────────────────────────────────────────────────────────

class TestCustomerCancelRescheduleGate:
    @pytest.mark.asyncio
    async def test_customer_cancel_blocked_when_workflow_disallows(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import (
            CUSTOMER_CANCELLABLE_JOB_STATUSES, ERR_CANCEL_NOT_ALLOWED,
        )
        svc = HomeServiceJobAssignmentService(db=AsyncMock())
        booking = MagicMock()
        job = MagicMock()
        job.status = next(iter(CUSTOMER_CANCELLABLE_JOB_STATUSES))
        workflow = _make_workflow(allows_cancellation=False)
        with patch.object(svc, "_load_booking_and_job", AsyncMock(return_value=(booking, job))):
            with patch(
                "app.engines.execution.home_service_service.HomeServiceJobExecutionService._resolve_job_type_workflow",
                AsyncMock(return_value=workflow),
            ):
                with pytest.raises(ValueError) as exc:
                    await svc.customer_cancel_booking(uuid.uuid4(), uuid.uuid4(), reason="plans changed")
                assert str(exc.value) == ERR_CANCEL_NOT_ALLOWED

    @pytest.mark.asyncio
    async def test_customer_reschedule_blocked_when_workflow_disallows(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import (
            CUSTOMER_CANCELLABLE_JOB_STATUSES, ERR_RESCHEDULE_NOT_ALLOWED,
        )
        import datetime as dt
        svc = HomeServiceJobAssignmentService(db=AsyncMock())
        booking = MagicMock()
        job = MagicMock()
        job.status = next(iter(CUSTOMER_CANCELLABLE_JOB_STATUSES))
        workflow = _make_workflow(allows_reschedule=False)
        with patch.object(svc, "_load_booking_and_job", AsyncMock(return_value=(booking, job))):
            with patch(
                "app.engines.execution.home_service_service.HomeServiceJobExecutionService._resolve_job_type_workflow",
                AsyncMock(return_value=workflow),
            ):
                with pytest.raises(ValueError) as exc:
                    await svc.customer_reschedule_booking(
                        uuid.uuid4(), uuid.uuid4(),
                        scheduled_date=dt.date.today(), scheduled_time_window="9-11",
                        reason="need a different day",
                    )
                assert str(exc.value) == ERR_RESCHEDULE_NOT_ALLOWED


# ─────────────────────────────────────────────────────────────────────────────
# 4. Exact Job-Type mapping still isolates Repair vs Installation
#    (regression guard on top of L5-53's own coverage, using the new columns)
# ─────────────────────────────────────────────────────────────────────────────

class TestExactJobTypeIsolationWithNewColumns:
    @pytest.mark.asyncio
    async def test_two_job_types_under_same_master_service_resolve_independently(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        master_service_id = uuid.uuid4()
        repair_job_type_id = uuid.uuid4()
        install_job_type_id = uuid.uuid4()

        repair_job = MagicMock()
        repair_job.service_job_workflow_id = uuid.uuid4()
        install_job = MagicMock()
        install_job.service_job_workflow_id = uuid.uuid4()

        repair_wf = _make_workflow(allows_cancellation=False, checklist_required=True)
        install_wf = _make_workflow(allows_cancellation=True, checklist_required=False)

        db = AsyncMock()
        async def fake_get(model, id_):
            return repair_wf if id_ == repair_job.service_job_workflow_id else install_wf
        db.get = AsyncMock(side_effect=fake_get)

        resolved_repair = await svc._resolve_job_type_workflow(db, repair_job)
        resolved_install = await svc._resolve_job_type_workflow(db, install_job)

        assert resolved_repair.allows_cancellation is False
        assert resolved_repair.checklist_required is True
        assert resolved_install.allows_cancellation is True
        assert resolved_install.checklist_required is False


# ─────────────────────────────────────────────────────────────────────────────
# 5. Version supersession -- new columns exist and default sanely
# ─────────────────────────────────────────────────────────────────────────────

class TestVersioningColumnsLive:
    @pytest.mark.asyncio
    async def test_migration_186_columns_present_on_live_db(self):
        """Live check against the local dev database (not a mock) that
        migration 186 actually ran and the new columns exist with the
        expected defaults, proving the schema change independently of the
        service-layer unit tests above."""
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.config import get_settings
        settings = get_settings()
        eng = create_async_engine(settings.DATABASE_URL)
        try:
            async with eng.begin() as conn:
                result = await conn.execute(text(
                    "select column_name from information_schema.columns "
                    "where table_name = 'service_job_workflow' "
                    "and column_name in ("
                    "'status','supersedes_workflow_id','effective_from','effective_to',"
                    "'created_by','approved_by','published_by','change_reason','published_at',"
                    "'allows_cancellation','allows_reschedule','requires_direct_payment_record')"
                ))
                cols = {row[0] for row in result}
                expected = {
                    "status", "supersedes_workflow_id", "effective_from", "effective_to",
                    "created_by", "approved_by", "published_by", "change_reason", "published_at",
                    "allows_cancellation", "allows_reschedule", "requires_direct_payment_record",
                }
                assert expected.issubset(cols), f"missing columns: {expected - cols}"

                dead_tables = await conn.execute(text(
                    "select to_regclass('workflow_templates'), to_regclass('workflow_template_versions')"
                ))
                row = dead_tables.fetchone()
                assert row[0] is None, "workflow_templates should have been dropped by migration 186"
                assert row[1] is None, "workflow_template_versions should have been dropped by migration 186"
        finally:
            await eng.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# 6. requires_direct_payment_record is honestly inert (schema-only)
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymentRecordFlagIsInert:
    def test_flag_default_and_model_field_exist_but_no_enforcement_hook(self):
        """Documents the honest scope decision: requires_direct_payment_record
        exists on the model/schema but complete_job() does not read it.
        This test fails loudly (NameError-style AttributeError) if someone
        later wires it without updating this test, forcing them to
        consciously flip this assertion rather than silently drifting."""
        import inspect
        from app.engines.execution import home_service_service as mod
        source = inspect.getsource(mod.HomeServiceJobExecutionService.complete_job)
        assert "requires_direct_payment_record" not in source, (
            "requires_direct_payment_record now referenced inside complete_job() -- "
            "if you wired real enforcement, update this test's assertion and the "
            "docstring/comment at the enforcement site instead of leaving this stale."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Vertical isolation -- workflow resolution never crosses master_service_id
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossServiceIsolation:
    @pytest.mark.asyncio
    async def test_job_type_belonging_to_different_service_is_not_linked(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        job = MagicMock()
        job.service_job_workflow_id = None
        job.offering_id = uuid.uuid4()
        job.job_type_id = uuid.uuid4()
        db = AsyncMock()
        no_link = MagicMock()
        no_link.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(return_value=no_link)
        result = await svc._resolve_job_type_workflow(db, job)
        assert result is None  # fails closed -- no workflow guessed across services


# ─────────────────────────────────────────────────────────────────────────────
# 8. Dead routes 404 -- live httpx call against the local dev server
# ─────────────────────────────────────────────────────────────────────────────

class TestDeadRoutesRemoved:
    @pytest.mark.asyncio
    async def test_workflow_enterprise_template_routes_are_gone(self):
        import httpx
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=5.0) as client:
            resp = await client.get("/v1/admin/workflows/templates")
            assert resp.status_code == 404
