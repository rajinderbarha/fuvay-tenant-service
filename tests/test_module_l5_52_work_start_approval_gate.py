"""HOME-SERVICES-RUNTIME-SAFETY Phase 2A — Estimate Approval / Work-Start Gate.

Proves, at the service layer (the same mocked-unit-test convention used
throughout tests/test_sprint21_execution.py and
tests/test_sprint22_quote_checklist.py), that:

  1. Work cannot start while a Job-Type Blueprint requires quote approval
     and no approved-and-current estimate exists, in every quote state the
     spec enumerates (none / draft / sent / revision-requested / rejected).
  2. Work CAN start when the current quote is customer-approved, and when
     the blueprint does not require approval at all.
  3. An unresolvable/ambiguous job-type link fails CLOSED (treated as
     approval-required), never open.
  4. The guard lives in the ONLY status-mutation path (_set_status), so a
     second quote row created after approval (superseding the approved one)
     re-blocks work start -- proving there is no way to "still be approved"
     against a stale, superseded estimate.
  5. create_quote's supersession logic marks at most one quote per job
     "is_current", and customer_approve/reject/request_revision refuse a
     superseded quote outright (ERR_QUOTE_NOT_CURRENT).
  6. The job-status sync path used by the quote engine no longer bypasses
     the execution engine's own JOB_TRANSITIONS graph via unvalidated raw SQL.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import ServiceOSException

TENANT_ID   = uuid.uuid4()
CUSTOMER_ID = uuid.uuid4()
STAFF_ID    = uuid.uuid4()
USER_ID     = uuid.uuid4()
JOB_ID      = uuid.uuid4()
BOOKING_ID  = uuid.uuid4()
OFFERING_ID = uuid.uuid4()
JOB_TYPE_ID = uuid.uuid4()
QUOTE_ID    = uuid.uuid4()


def _mock_job(status="inspection_done", offering_id=OFFERING_ID, job_type_id=JOB_TYPE_ID, service_job_workflow_id=None):
    from app.engines.final_records.models import ServiceJob
    j = MagicMock(spec=ServiceJob)
    j.id = JOB_ID
    j.booking_id = BOOKING_ID
    j.tenant_id = TENANT_ID
    j.status = status
    j.job_type_id = job_type_id
    # Phase 2A.2: None here exercises the legacy (offering_id, job_type_id)
    # live-lookup fallback -- these Phase 2A.1 tests predate the snapshot
    # column and are still valid for that fallback path.
    j.service_job_workflow_id = service_job_workflow_id
    j.assigned_staff_id = STAFF_ID
    j.offering_id = offering_id
    j.updated_at = None
    j.to_dict = lambda: {"id": str(JOB_ID), "status": j.status}
    return j


def _mock_link(job_type_id=JOB_TYPE_ID, is_active=True):
    m = MagicMock()
    m.master_service_id = OFFERING_ID
    m.job_type_id = job_type_id
    m.is_active = is_active
    return m


def _mock_workflow(quote_approval_required=True):
    w = MagicMock()
    w.master_service_id = OFFERING_ID
    w.job_type_id = JOB_TYPE_ID
    w.quote_approval_required = quote_approval_required
    return w


def _mock_quote(status, is_current=True):
    from app.engines.quote_checklist.models import ServiceJobQuote
    q = MagicMock(spec=ServiceJobQuote)
    q.id = QUOTE_ID
    q.job_id = JOB_ID
    q.status = status
    q.is_current = is_current
    return q


def _all_result(items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    return r


def _first_result(item):
    r = MagicMock()
    r.scalars.return_value.first.return_value = item
    return r


# ─────────────────────────────────────────────────────────────────────────────
# 1-3. Blueprint resolution + quote-state gating (via the real guard method)
# ─────────────────────────────────────────────────────────────────────────────

class TestBlueprintResolution:
    """Phase 2A.1: exact resolution via ServiceJob.offering_id +
    ServiceJob.job_type_id -> exact MasterServiceJobType -> exact
    ServiceJobWorkflow. Multiple active Job Types under one Master Service
    is NORMAL and must NOT be treated as ambiguous -- this is the core
    architectural correction over Phase 2A's "exactly one active link"
    resolver."""

    @pytest.mark.asyncio
    async def test_missing_job_type_id_unresolved(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        db = AsyncMock()
        job = _mock_job(job_type_id=None)
        result = await svc._resolve_job_type_workflow(db, job)
        assert result is None

    @pytest.mark.asyncio
    async def test_job_type_not_linked_to_service_unresolved(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_first_result(None))  # no matching link row
        job = _mock_job()
        result = await svc._resolve_job_type_workflow(db, job)
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_workflow_row_unresolved(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[_first_result(_mock_link()), _first_result(None)])
        job = _mock_job()
        result = await svc._resolve_job_type_workflow(db, job)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_offering_id_unresolved(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        db = AsyncMock()
        job = _mock_job(offering_id=None)
        result = await svc._resolve_job_type_workflow(db, job)
        assert result is None

    @pytest.mark.asyncio
    async def test_repair_and_installation_under_same_master_service_resolve_independently(self):
        """The exact scenario Phase 2A got wrong: one Master Service (Air
        Conditioner) with BOTH Repair (quote_approval_required=True) and
        Installation (quote_approval_required=False) active at once. Each
        job resolves its OWN workflow via its own job_type_id -- neither is
        "ambiguous" merely because its sibling job type also exists."""
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        repair_type_id = uuid.uuid4()
        install_type_id = uuid.uuid4()

        repair_job = _mock_job(job_type_id=repair_type_id)
        db_repair = AsyncMock()
        db_repair.execute = AsyncMock(side_effect=[
            _first_result(_mock_link(job_type_id=repair_type_id)),
            _first_result(_mock_workflow(True)),
        ])
        repair_workflow = await svc._resolve_job_type_workflow(db_repair, repair_job)
        assert repair_workflow is not None and repair_workflow.quote_approval_required is True

        install_job = _mock_job(job_type_id=install_type_id)
        db_install = AsyncMock()
        db_install.execute = AsyncMock(side_effect=[
            _first_result(_mock_link(job_type_id=install_type_id)),
            _first_result(_mock_workflow(False)),
        ])
        install_workflow = await svc._resolve_job_type_workflow(db_install, install_job)
        assert install_workflow is not None and install_workflow.quote_approval_required is False


class TestWorkStartGate:
    async def _svc_with_required(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        return svc

    @pytest.mark.asyncio
    async def test_approval_not_required_passes_through(self):
        svc = await self._svc_with_required()
        job = _mock_job()
        with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=_mock_workflow(False))):
            await svc._assert_quote_approval_satisfied(AsyncMock(), job)  # must not raise

    @pytest.mark.asyncio
    async def test_unresolved_job_type_blocks_with_dedicated_code(self):
        svc = await self._svc_with_required()
        job = _mock_job()
        with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=None)):
            with pytest.raises(ServiceOSException) as exc:
                await svc._assert_quote_approval_satisfied(AsyncMock(), job)
        assert exc.value.error_code == "JOB_TYPE_CONTEXT_UNRESOLVED"

    @pytest.mark.asyncio
    async def test_no_current_quote_blocks_estimate_required(self):
        svc = await self._svc_with_required()
        job = _mock_job()
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_first_result(None))
        with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=_mock_workflow(True))):
            with pytest.raises(ServiceOSException) as exc:
                await svc._assert_quote_approval_satisfied(db, job)
        assert exc.value.error_code == "ESTIMATE_REQUIRED"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status,code", [
        ("draft", "ESTIMATE_REQUIRED"),
        ("submitted_to_provider", "ESTIMATE_REQUIRED"),
        ("sent_to_customer", "ESTIMATE_APPROVAL_REQUIRED"),
        ("revision_requested", "ESTIMATE_REVISION_REQUIRED"),
        ("customer_rejected", "ESTIMATE_REJECTED"),
        ("expired", "ESTIMATE_REQUIRED"),
        ("cancelled", "ESTIMATE_REQUIRED"),
    ])
    async def test_every_non_approved_quote_state_blocks(self, status, code):
        svc = await self._svc_with_required()
        job = _mock_job()
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_first_result(_mock_quote(status)))
        with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=_mock_workflow(True))):
            with pytest.raises(ServiceOSException) as exc:
                await svc._assert_quote_approval_satisfied(db, job)
        assert exc.value.error_code == code

    @pytest.mark.asyncio
    async def test_current_approved_quote_allows_work(self):
        svc = await self._svc_with_required()
        job = _mock_job()
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_first_result(_mock_quote("customer_approved")))
        with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=_mock_workflow(True))):
            await svc._assert_quote_approval_satisfied(db, job)  # must not raise

    @pytest.mark.asyncio
    async def test_superseded_approved_quote_is_invisible_to_guard(self):
        """The guard only ever queries is_current=True -- an approved-but-
        superseded quote is filtered out at the query itself, so it can never
        be the thing that (incorrectly) authorizes work."""
        svc = await self._svc_with_required()
        job = _mock_job()
        db = AsyncMock()
        # Simulates the DB-level filter: is_current=True finds nothing because
        # the only approved quote for this job has since been superseded.
        db.execute = AsyncMock(return_value=_first_result(None))
        with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=_mock_workflow(True))):
            with pytest.raises(ServiceOSException) as exc:
                await svc._assert_quote_approval_satisfied(db, job)
        assert exc.value.error_code == "ESTIMATE_REQUIRED"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Guard wired into the ONLY status-mutation path -- start_service end-to-end
# ─────────────────────────────────────────────────────────────────────────────

class TestStartServiceEndToEnd:
    @pytest.mark.asyncio
    async def test_start_service_blocked_when_approval_required_and_missing(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        job = _mock_job(status="inspection_done")
        db = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()

        async def fake_get_job(db, job_id, tenant_id):
            return job
        with patch.object(svc, "_get_job", fake_get_job):
            with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=_mock_workflow(True))):
                db.execute = AsyncMock(return_value=_first_result(None))
                with pytest.raises(ServiceOSException) as exc:
                    await svc.start_service(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert exc.value.error_code == "ESTIMATE_REQUIRED"
        assert job.status == "inspection_done"  # unchanged -- no partial mutation

    @pytest.mark.asyncio
    async def test_start_service_allowed_when_approved_and_current(self):
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        svc = HomeServiceJobExecutionService()
        job = _mock_job(status="inspection_done")
        db = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()

        async def fake_get_job(db, job_id, tenant_id):
            return job
        with patch.object(svc, "_get_job", fake_get_job):
            with patch.object(svc, "_resolve_job_type_workflow", AsyncMock(return_value=_mock_workflow(True))):
                db.execute = AsyncMock(return_value=_first_result(_mock_quote("customer_approved")))
                with patch.object(svc, "sync_booking_status", AsyncMock()):
                    result = await svc.start_service(db, JOB_ID, TENANT_ID, STAFF_ID, USER_ID)
        assert job.status == "service_started"
        assert result["status"] == "service_started"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Quote versioning / supersession / is_current enforcement
# ─────────────────────────────────────────────────────────────────────────────

class TestQuoteVersionLineage:
    @pytest.mark.asyncio
    async def test_create_quote_supersedes_prior_current_when_rejected(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        job = _mock_job()
        prior = _mock_quote("customer_rejected")
        prior.version_number = 1
        db = AsyncMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()
        prior_result = MagicMock()
        prior_result.scalar_one_or_none.return_value = prior
        db.execute = AsyncMock(side_effect=[prior_result, MagicMock()])
        with patch.object(svc, "_get_job", AsyncMock(return_value=job)):
            with patch.object(svc, "_log_event", AsyncMock()):
                with patch(
                    "app.engines.checklist_catalog.gate.assert_gate_satisfied",
                    AsyncMock(),
                ):
                    await svc.create_quote(
                        db, str(JOB_ID), str(TENANT_ID),
                        "repair_quote", str(USER_ID), None, None, None,
                    )
        new_quote = db.add.call_args[0][0]
        assert new_quote.is_current is True
        assert new_quote.version_number == 2
        assert new_quote.supersedes_quote_id == prior.id

    @pytest.mark.asyncio
    async def test_create_quote_cannot_supersede_approved_estimate(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_APPROVED_ESTIMATE_IMMUTABLE
        svc = ServiceJobQuoteService()
        job = _mock_job()
        prior = _mock_quote("customer_approved")
        db = AsyncMock()
        prior_result = MagicMock()
        prior_result.scalar_one_or_none.return_value = prior
        db.execute = AsyncMock(return_value=prior_result)
        with patch.object(svc, "_get_job", AsyncMock(return_value=job)):
            with pytest.raises(ValueError, match=ERR_APPROVED_ESTIMATE_IMMUTABLE):
                await svc.create_quote(
                    db, str(JOB_ID), str(TENANT_ID),
                    "repair_quote", str(USER_ID), None, None, None,
                )

    @pytest.mark.asyncio
    async def test_create_quote_cannot_supersede_quote_awaiting_customer_decision(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_INVALID_ESTIMATE_REVISION_STATE
        svc = ServiceJobQuoteService()
        job = _mock_job()
        prior = _mock_quote("sent_to_customer")
        db = AsyncMock()
        prior_result = MagicMock()
        prior_result.scalar_one_or_none.return_value = prior
        db.execute = AsyncMock(return_value=prior_result)
        with patch.object(svc, "_get_job", AsyncMock(return_value=job)):
            with pytest.raises(ValueError, match=ERR_INVALID_ESTIMATE_REVISION_STATE):
                await svc.create_quote(
                    db, str(JOB_ID), str(TENANT_ID),
                    "repair_quote", str(USER_ID), None, None, None,
                )

    @pytest.mark.asyncio
    async def test_customer_approve_rejects_superseded_quote(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_NOT_CURRENT
        svc = ServiceJobQuoteService()
        q = _mock_quote("sent_to_customer", is_current=False)
        q.customer_id = CUSTOMER_ID
        db = AsyncMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_NOT_CURRENT):
                await svc.customer_approve(db, str(QUOTE_ID), str(CUSTOMER_ID), "idem", str(USER_ID), None)

    @pytest.mark.asyncio
    async def test_customer_reject_rejects_superseded_quote(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_NOT_CURRENT
        svc = ServiceJobQuoteService()
        q = _mock_quote("sent_to_customer", is_current=False)
        q.customer_id = CUSTOMER_ID
        db = AsyncMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_NOT_CURRENT):
                await svc.customer_reject(db, str(QUOTE_ID), str(CUSTOMER_ID), "reason", str(USER_ID), None)

    @pytest.mark.asyncio
    async def test_customer_request_revision_rejects_superseded_quote(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_QUOTE_NOT_CURRENT
        svc = ServiceJobQuoteService()
        q = _mock_quote("sent_to_customer", is_current=False)
        q.customer_id = CUSTOMER_ID
        db = AsyncMock()
        with patch.object(svc, "_get_quote", AsyncMock(return_value=q)):
            with pytest.raises(ValueError, match=ERR_QUOTE_NOT_CURRENT):
                await svc.customer_request_revision(db, str(QUOTE_ID), str(CUSTOMER_ID), "reason", str(USER_ID), None)


# ─────────────────────────────────────────────────────────────────────────────
# 6. _sync_job_status no longer bypasses JOB_TRANSITIONS via raw SQL
# ─────────────────────────────────────────────────────────────────────────────

class TestSyncJobStatusValidated:
    @pytest.mark.asyncio
    async def test_sync_rejects_graph_invalid_transition(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        db = AsyncMock()
        # Job currently "completed" (terminal) -- JOB_TRANSITIONS allows no
        # further moves, so a quote-engine sync attempt must be rejected
        # rather than silently overwriting a terminal job's status.
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value="completed")))
        with pytest.raises(ValueError):
            await svc._sync_job_status(db, JOB_ID, "quote_required")

    @pytest.mark.asyncio
    async def test_sync_is_noop_when_already_at_target(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value="quote_required")))
        await svc._sync_job_status(db, JOB_ID, "quote_required")  # must not raise
        assert db.execute.await_count == 1  # only the read, no redundant write

    @pytest.mark.asyncio
    async def test_sync_allows_graph_valid_transition(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        svc = ServiceJobQuoteService()
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value="inspection_done")),
            MagicMock(),
        ])
        await svc._sync_job_status(db, JOB_ID, "quote_required")  # graph-valid, must not raise
        assert db.execute.await_count == 2
