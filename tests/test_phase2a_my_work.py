"""Phase 2A — Technician My Work aggregation tests.

Covers TechnicianMyWorkService (app/engines/execution/my_work_service.py):
- Job-status -> category/action derivation
- Parts-request-status -> category/action derivation
- Tenant scoping (query filters, not just response filtering)
- Partial-failure handling (one source down, other still returns)
- Sorting (urgent first)

Route registration for GET /v1/staff/my-work is covered by
scripts/workflow_rearchitecture/list_routes.py (see
docs/workflow-rearchitecture/phase-02a/route-and-permission-test-report.md
for the runtime route-dump evidence), not duplicated here as a live-server test.
"""
import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.execution.my_work_service import TechnicianMyWorkService
from app.engines.execution.constants import (
    PARTS_STATUS_REQUESTED,
    PARTS_STATUS_BUSINESS_APPROVED,
    PARTS_STATUS_BUSINESS_REJECTED,
    PARTS_STATUS_INSTALLED,
)

TENANT_ID = uuid.uuid4()
STAFF_ID = uuid.uuid4()
JOB_ID = uuid.uuid4()
OTHER_JOB_ID = uuid.uuid4()
PARTS_ID = uuid.uuid4()


def _mock_job(job_id, status, scheduled_date=None):
    j = MagicMock()
    j.id = job_id
    j.job_number = f"JOB-{str(job_id)[:8]}"
    j.assigned_staff_id = STAFF_ID
    j.tenant_id = TENANT_ID
    j.status = status
    j.scheduled_date = scheduled_date
    j.created_at = None
    j.city = "Bengaluru"
    j.zipcode = "560001"
    return j


def _mock_parts(status):
    p = MagicMock()
    p.id = PARTS_ID
    p.job_id = JOB_ID
    p.technician_id = STAFF_ID
    p.tenant_id = TENANT_ID
    p.status = status
    p.part_name = "Compressor"
    p.quantity = 1
    p.estimated_cost = 4500.00
    p.created_at = None
    return p


def _db_with_results(job_result, parts_result):
    """First db.execute() call -> jobs query, second -> parts query."""
    db = AsyncMock()
    res_jobs = MagicMock()
    res_jobs.scalars.return_value.all.return_value = job_result
    res_parts = MagicMock()
    res_parts.scalars.return_value.all.return_value = parts_result
    db.execute = AsyncMock(side_effect=[res_jobs, res_parts])
    return db


@pytest.mark.asyncio
class TestJobStatusDerivation:
    async def test_assigned_job_is_requires_my_action_and_urgent(self):
        job = _mock_job(JOB_ID, "assigned")
        db = _db_with_results([job], [])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        assert result["count"] == 1
        item = result["items"][0]
        assert item["category"] == "REQUIRES_MY_ACTION"
        assert item["priority"] == "urgent"
        assert item["available_actions"] == ["accept", "reject"]
        assert item["record_type"] == "ServiceJob"
        assert item["record_id"] == str(JOB_ID)

    async def test_accepted_future_job_is_scheduled(self):
        job = _mock_job(JOB_ID, "accepted", scheduled_date=date.today() + timedelta(days=3))
        db = _db_with_results([job], [])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        assert result["items"][0]["category"] == "SCHEDULED"
        assert result["items"][0]["priority"] == "normal"

    async def test_accepted_overdue_job_is_urgent(self):
        job = _mock_job(JOB_ID, "accepted", scheduled_date=date.today() - timedelta(days=1))
        db = _db_with_results([job], [])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        assert result["items"][0]["priority"] == "urgent"

    async def test_quote_required_is_waiting_for_others_with_no_actions(self):
        job = _mock_job(JOB_ID, "quote_required")
        db = _db_with_results([job], [])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        item = result["items"][0]
        assert item["category"] == "WAITING_FOR_OTHERS"
        assert item["available_actions"] == []
        assert item["primary_action"] is None

    async def test_terminal_status_excluded(self):
        job = _mock_job(JOB_ID, "completed")
        db = _db_with_results([job], [])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        assert result["count"] == 0


@pytest.mark.asyncio
class TestPartsRequestDerivation:
    async def test_requested_parts_is_waiting_for_others(self):
        pr = _mock_parts(PARTS_STATUS_REQUESTED)
        db = _db_with_results([], [pr])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        item = result["items"][0]
        assert item["record_type"] == "PartsRequest"
        assert item["category"] == "WAITING_FOR_OTHERS"
        assert item["available_actions"] == []

    async def test_business_approved_parts_has_no_install_action(self):
        """Confirms the honest gap: no staff-facing install endpoint exists
        (only /v1/provider/service-jobs/.../install), so the technician item
        must not fabricate an 'install' action it cannot actually perform."""
        pr = _mock_parts(PARTS_STATUS_BUSINESS_APPROVED)
        db = _db_with_results([], [pr])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        item = result["items"][0]
        assert item["available_actions"] == []
        assert "ask your business/admin" in item["recommended_action"]

    async def test_rejected_parts_is_failed_category(self):
        pr = _mock_parts(PARTS_STATUS_BUSINESS_REJECTED)
        db = _db_with_results([], [pr])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        assert result["items"][0]["category"] == "FAILED"

    async def test_installed_parts_excluded_from_active_queue(self):
        pr = _mock_parts(PARTS_STATUS_INSTALLED)
        db = _db_with_results([], [pr])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        assert result["count"] == 0


@pytest.mark.asyncio
class TestAggregationBehavior:
    async def test_combines_jobs_and_parts(self):
        job = _mock_job(JOB_ID, "assigned")
        pr = _mock_parts(PARTS_STATUS_REQUESTED)
        db = _db_with_results([job], [pr])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        assert result["count"] == 2
        record_types = {it["record_type"] for it in result["items"]}
        assert record_types == {"ServiceJob", "PartsRequest"}

    async def test_urgent_items_sort_first(self):
        urgent_job = _mock_job(JOB_ID, "assigned")  # urgent
        scheduled_job = _mock_job(OTHER_JOB_ID, "accepted", scheduled_date=date.today() + timedelta(days=5))
        db = _db_with_results([scheduled_job, urgent_job], [])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        assert result["items"][0]["priority"] == "urgent"

    async def test_job_query_scoped_to_tenant_and_staff(self):
        """The service must filter by both assigned_staff_id AND tenant_id in
        the query itself (tenant isolation), not merely in the response."""
        db = _db_with_results([], [])
        svc = TechnicianMyWorkService()
        await svc.get_items(db, STAFF_ID, TENANT_ID)
        # First call is the jobs query — inspect the compiled WHERE clause text.
        jobs_call = db.execute.call_args_list[0]
        compiled = str(jobs_call.args[0])
        assert "tenant_id" in compiled
        assert "assigned_staff_id" in compiled

    async def test_partial_failure_reports_unavailable_source_not_fake_success(self):
        """If the jobs query raises, the endpoint must report that source as
        unavailable rather than silently returning an empty/zero result
        indistinguishable from 'nothing pending' (rule: no fake success states)."""
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[Exception("db down"), MagicMock(scalars=lambda: MagicMock(all=lambda: []))])
        svc = TechnicianMyWorkService()
        result = await svc.get_items(db, STAFF_ID, TENANT_ID)
        assert "service_jobs" in result["sources_unavailable"]
