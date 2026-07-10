"""
Phase 7-9 completeness tests: job_type + service catalog + quote approval flow.

Verifies:
  1.  SERVICE job cannot transition to quote_pending
  2.  REPAIR job can transition to quote_pending (via assessment_complete)
  3.  CONSULTATION job can transition to quote_pending (but NOT work_started directly)
  4.  REPAIR quote_rejected allows re-assessment (→ assessment_complete)
  5.  CONSULTATION quote_rejected goes to pending_sign_off (not cancelled)
  6.  get_allowed_transitions returns correct set per job_type
  7.  SERVICE job bypasses assessment → goes straight to work_started from arrived
  8.  Consultation spawns repair on quote approval
  9.  spawn_repair_from_consultation raises if job is not consultation
  10. Catalog lookup in create_job auto-fills job_type/checklist/quoted_price
  11. spawn-repair endpoint is wired (router test)
  12. Quote versioning: multiple quotes can exist per job
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, patch as mock_patch
from decimal import Decimal


# ── 1–7: Transition graph correctness ────────────────────────────────────────

def test_service_cannot_enter_quote_pending():
    from app.engines.field_ops.constants import get_allowed_transitions, JobType, JS
    allowed = get_allowed_transitions(JobType.SERVICE, JS.ARRIVED)
    assert JS.WORK_STARTED in allowed
    assert JS.ASSESSMENT_STARTED not in allowed
    assert JS.QUOTE_PENDING not in allowed


def test_repair_can_enter_quote_pending_from_assessment_complete():
    from app.engines.field_ops.constants import get_allowed_transitions, JobType, JS
    allowed = get_allowed_transitions(JobType.REPAIR, JS.ASSESSMENT_COMPLETE)
    assert JS.QUOTE_PENDING in allowed
    assert JS.WORK_STARTED in allowed


def test_consultation_assessment_complete_only_goes_to_quote_pending():
    from app.engines.field_ops.constants import get_allowed_transitions, JobType, JS
    allowed = get_allowed_transitions(JobType.CONSULTATION, JS.ASSESSMENT_COMPLETE)
    assert JS.QUOTE_PENDING in allowed
    assert JS.WORK_STARTED not in allowed
    assert JS.PARTS_REQUIRED not in allowed


def test_repair_quote_rejected_allows_reassessment():
    from app.engines.field_ops.constants import get_allowed_transitions, JobType, JS
    allowed = get_allowed_transitions(JobType.REPAIR, JS.QUOTE_REJECTED)
    assert JS.ASSESSMENT_COMPLETE in allowed
    assert JS.CANCELLED in allowed


def test_consultation_quote_rejected_goes_to_pending_sign_off():
    from app.engines.field_ops.constants import get_allowed_transitions, JobType, JS
    allowed = get_allowed_transitions(JobType.CONSULTATION, JS.QUOTE_REJECTED)
    assert JS.PENDING_SIGN_OFF in allowed
    assert JS.CANCELLED not in allowed


def test_consultation_quote_approved_goes_to_pending_sign_off():
    from app.engines.field_ops.constants import get_allowed_transitions, JobType, JS
    allowed = get_allowed_transitions(JobType.CONSULTATION, JS.QUOTE_APPROVED)
    assert JS.PENDING_SIGN_OFF in allowed
    assert JS.WORK_STARTED not in allowed


def test_service_arrived_to_work_started():
    from app.engines.field_ops.constants import get_allowed_transitions, JobType, JS
    allowed = get_allowed_transitions(JobType.SERVICE, JS.ARRIVED)
    assert JS.WORK_STARTED in allowed


# ── 8. Consultation spawns repair on quote approval ──────────────────────────

@pytest.mark.asyncio
async def test_consultation_quote_approval_spawns_repair():
    from app.engines.field_ops.service import FieldOpsService
    from app.engines.field_ops.constants import JobType, JS

    db = MagicMock()
    svc = FieldOpsService(db=db)

    consult_id = uuid.uuid4()
    quote_id   = uuid.uuid4()
    customer_id = uuid.uuid4()

    consult_job = MagicMock(
        id=consult_id, tenant_id=uuid.uuid4(), status=JS.QUOTE_PENDING,
        job_type=JobType.CONSULTATION,
        title="Consult: AC not cooling", service_type_id="ac_check",
        service_category="HVAC", customer_id=customer_id,
        address={"city":"Mumbai"}, pincode="400001",
        findings="Compressor low charge", recommendation="Top up refrigerant",
    )
    quote = MagicMock(
        id=quote_id, job_id=consult_id, customer_id=customer_id,
        status="pending", amount=Decimal("1200"), expires_at=None,
    )

    exec_results = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=quote)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=consult_job)),
    ]
    call_count = {"n": 0}
    async def fake_execute(stmt):
        n = call_count["n"]; call_count["n"] += 1
        return exec_results[n % len(exec_results)]
    db.execute = fake_execute
    db.add = MagicMock()
    db.flush = AsyncMock()

    spawned = []
    async def fake_create_job(tid, data):
        spawned.append(data)
        return {"job_id": str(uuid.uuid4()), "job_number": "JOB-202601-99999",
                "status": JS.DRAFT, "job_type": JobType.REPAIR, "allowed_transitions": []}
    svc.create_job = fake_create_job
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    with patch("app.engines.field_ops.constants.get_allowed_transitions",
               return_value=[JS.QUOTE_APPROVED, JS.QUOTE_REJECTED]):
        result = await svc.respond_to_quote(quote_id, customer_id, approved=True)

    assert result["approved"] is True
    assert "spawned_job" in result
    assert len(spawned) == 1
    assert spawned[0]["job_type"] == JobType.REPAIR
    assert spawned[0]["parent_job_id"] == str(consult_id)


# ── 9. spawn_repair_from_consultation raises for non-consultation ─────────────

@pytest.mark.asyncio
async def test_spawn_repair_raises_for_non_consultation():
    from app.engines.field_ops.service import FieldOpsService
    from app.engines.field_ops.constants import JobType, JS
    from app.exceptions import ServiceOSException

    db = MagicMock()
    svc = FieldOpsService(db=db)
    repair_job = MagicMock(id=uuid.uuid4(), job_type=JobType.REPAIR, status=JS.WORK_STARTED)

    async def fake_execute(stmt):
        return MagicMock(scalar_one_or_none=MagicMock(return_value=repair_job))
    db.execute = fake_execute

    with pytest.raises(ServiceOSException) as exc:
        await svc.spawn_repair_from_consultation(repair_job.id)
    assert exc.value.error_code == "INVALID_JOB_TYPE"


# ── 10. create_job uses service catalog when job_type not provided ────────────

@pytest.mark.asyncio
async def test_create_job_auto_fills_from_catalog():
    from app.engines.field_ops.service import FieldOpsService
    from app.engines.field_ops.constants import JobType, JS

    db = MagicMock()
    svc = FieldOpsService(db=db)
    tid = uuid.uuid4()

    # Catalog item stub
    cat_item = MagicMock(
        service_type=JobType.SERVICE,
        estimated_duration_minutes=60,
        checklist_template=["Inspect filters", "Clean coils"],
        pricing_model="fixed",
        base_price=Decimal("499"),
        is_active=True,
    )

    created_jobs: list = []
    def fake_add(obj):
        created_jobs.append(obj)
    db.add = fake_add
    db.flush = AsyncMock()

    async def fake_execute(stmt):
        return MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    db.execute = fake_execute

    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    mock_catalog_svc = AsyncMock()
    mock_catalog_svc.get_by_service_type_id = AsyncMock(return_value=cat_item)

    def fake_job_dict(j, include_timeline=False):
        return {"job_id": "x", "job_number": "x", "status": j.status,
                "job_type": j.job_type, "allowed_transitions": [],
                "created_at": "2026-01-01T00:00:00+00:00"}

    with patch("app.engines.field_ops.service.FieldOpsService._generate_job_number",
               return_value="JOB-202601-11111"), \
         patch("app.engines.service_catalog.service.ServiceCatalogService",
               return_value=mock_catalog_svc), \
         patch.object(svc, "_job_dict", fake_job_dict), \
         patch("app.redis_client.get_redis", return_value=AsyncMock(setex=AsyncMock())):
        await svc.create_job(tid, {
            "title": "AC Service",
            "service_type_id": "ac_cleaning",
            # job_type intentionally omitted — should be auto-filled
        })

    job_obj = created_jobs[0]
    assert job_obj.job_type == JobType.SERVICE
    assert job_obj.duration_estimate_minutes == 60
    assert len(job_obj.checklist) == 2
    assert job_obj.quoted_price == Decimal("499")


# ── 11. spawn-repair router endpoint exists ───────────────────────────────────

def test_spawn_repair_router_endpoint_exists():
    from app.engines.field_ops.router import router
    paths = [r.path for r in router.routes]
    assert any("spawn-repair" in p for p in paths)


# ── 12. Multiple quotes can exist per job (no unique constraint) ──────────────

def test_quote_versioning_multiple_quotes_supported():
    from app.engines.field_ops.models import JobQuote
    # All quotes go into separate rows — confirmed by inspecting model (no unique_together on job_id)
    q1 = JobQuote.__table__.columns
    col_names = [c.name for c in q1]
    assert "job_id" in col_names
    assert "status" in col_names
    assert "amount" in col_names
    # No unique constraint on (job_id) alone
    unique_constraints = [
        c for c in JobQuote.__table__.constraints
        if hasattr(c, "columns") and set(c.columns.keys()) == {"job_id"}
    ]
    assert len(unique_constraints) == 0
