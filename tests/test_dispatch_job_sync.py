"""
Phase 6 critical fix: dispatch_job()/accept_job()/reassign_job() only ever
wrote to DispatchRecord.assigned_staff_id — the real Job row's
assigned_staff_id was NEVER set. This silently broke staff performance
signals, geo active-job decrements, review-request staff attribution, and
all of Phase 5's staff-ownership scoping (job.assigned_staff_id == actor_id
checks would never match since the column was always NULL).

Also verifies: job status advances along the dispatch-owned segment of the
lifecycle (draft->confirmed->dispatched->accepted), and invoice generation
on the INVOICE_GENERATED transition actually creates a Document.
"""
import uuid
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock


def make_job(status="draft", assigned_staff_id=None):
    return MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), status=status,
                      assigned_staff_id=assigned_staff_id, job_number="JOB-1",
                      customer_id=uuid.uuid4(), title="AC Repair")


@pytest.mark.asyncio
async def test_dispatch_manual_mode_sets_job_assigned_staff_id_and_advances_status():
    from app.engines.dispatch.service import DispatchService
    from app.engines.dispatch.constants import DispatchMode

    job = make_job(status="confirmed")
    staff_id = uuid.uuid4()

    existing_dispatch_result = MagicMock()
    existing_dispatch_result.scalar_one_or_none.return_value = None  # no idempotent dup

    db = MagicMock()
    # Only the idempotency check now goes through db.execute -- the
    # job-ownership pre-check and the post-assignment Job sync (both added
    # since this test was written) call self._get_job(), mocked directly
    # below instead of routed through db.execute's side_effect, since it's
    # invoked twice (pre-check + sync) and must return the *same* job
    # object both times for this test's mutation-based assertions to work.
    db.execute = AsyncMock(side_effect=[existing_dispatch_result])
    db.flush = AsyncMock()

    # Slice 2F-39: actor_tenant_id added -- Slice 2F-36's
    # _require_trusted_tenant guard (dispatch.service.py) now requires it;
    # this test predates that fix and previously left it unset (None),
    # which the guard correctly rejects ("No tenant context.").
    svc = DispatchService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                           actor_tenant_id=job.tenant_id)
    svc._get_score_weights = AsyncMock(return_value={})
    # Slice 2F-39: _get_job() is a newer helper (added alongside the
    # job-ownership pre-check and Job-row sync) that this test predates.
    svc._get_job = AsyncMock(return_value=job)
    await svc.dispatch_job(str(job.id), job.tenant_id, DispatchMode.MANUAL, staff_id,
                            None, None, "ac_repair")

    assert job.assigned_staff_id == staff_id
    assert job.status == "dispatched"


@pytest.mark.asyncio
async def test_accept_job_sets_job_assigned_staff_id_and_advances_to_accepted():
    from app.engines.dispatch.service import DispatchService
    from app.engines.dispatch.constants import DispatchStatus

    job = make_job(status="dispatched")
    staff_id = uuid.uuid4()
    rec = MagicMock(status=DispatchStatus.ASSIGNED, expires_at=None)

    rec_result = MagicMock()
    rec_result.scalar_one_or_none.return_value = rec
    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[rec_result, job_result])

    svc = DispatchService(db=db, actor_id=staff_id, actor_role="staff")
    await svc.accept_job(str(job.id), staff_id)

    assert job.assigned_staff_id == staff_id
    assert job.status == "accepted"


@pytest.mark.asyncio
async def test_advance_job_never_touches_a_job_already_past_acceptance():
    """Dispatch must never clobber a job that's already mid-work (e.g. en_route)."""
    from app.engines.dispatch.service import DispatchService

    job = make_job(status="en_route")
    db = MagicMock()
    svc = DispatchService(db=db, actor_id=uuid.uuid4(), actor_role="staff")

    await svc._advance_job(job, "accepted", "should be a no-op")
    assert job.status == "en_route"


@pytest.mark.asyncio
async def test_reassign_job_updates_job_assigned_staff_id():
    from app.engines.dispatch.service import DispatchService

    job = make_job(status="dispatched", assigned_staff_id=uuid.uuid4())
    new_staff = uuid.uuid4()
    rec = MagicMock(assigned_staff_id=job.assigned_staff_id, escalation_count=0, tenant_id=job.tenant_id)

    rec_result = MagicMock()
    rec_result.scalar_one_or_none.return_value = rec
    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[rec_result, job_result])

    # Slice 2F-39: actor_tenant_id added, same reason as
    # test_dispatch_manual_mode_sets_job_assigned_staff_id_and_advances_status above.
    svc = DispatchService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                           actor_tenant_id=job.tenant_id)
    await svc.reassign_job(str(job.id), new_staff, "no-show")

    assert job.assigned_staff_id == new_staff


# ── Invoice generation on status transition ─────────────────────────────────

@pytest.mark.asyncio
async def test_invoice_generated_transition_actually_creates_a_document():
    from app.engines.field_ops.service import FieldOpsService
    from decimal import Decimal

    job = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), status="signed_off",
                     job_number="JOB-1", title="AC Repair", service_type_id="ac_repair",
                     customer_id=uuid.uuid4(), final_price=Decimal("1500"), quoted_price=None,
                     started_at=None, completed_at=None)

    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job
    db = MagicMock()
    db.execute = AsyncMock(return_value=job_result)

    svc = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner")
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    captured = {}
    async def fake_generate_document(self, tenant_id, doc_type, **kwargs):
        captured["doc_type"] = doc_type
        captured["tenant_id"] = tenant_id
        captured["variables"] = kwargs.get("variables")
        return {"document_id": str(uuid.uuid4())}

    import app.engines.document.service as doc_module
    real_init = doc_module.DocumentService.__init__
    real_generate_document = doc_module.DocumentService.generate_document
    doc_module.DocumentService.__init__ = lambda self, *a, **kw: None
    doc_module.DocumentService.generate_document = fake_generate_document
    try:
        result = await svc.update_status(job.id, "invoice_generated", None, None, None)
    finally:
        # Slice 2F-39 fix: generate_document was patched onto the class
        # directly but never restored, permanently replacing it with this
        # stub for the rest of the test session -- caused
        # test_phase2f35_critical_authorization_batch.py's
        # test_generate_document_calls_trusted_tenant (which inspects
        # DocumentService.generate_document's real source) to fail only
        # when running after this test in the same process, never in
        # isolation. Both class attributes must be restored, not just
        # __init__.
        doc_module.DocumentService.__init__ = real_init
        doc_module.DocumentService.generate_document = real_generate_document

    assert captured["doc_type"] == "invoice"
    assert captured["variables"]["amount"] == "1500"
    assert job.status == "invoice_generated"
