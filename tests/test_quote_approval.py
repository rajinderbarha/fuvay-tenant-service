"""
Phase 9 — Quote and Approval System. Builds on Phase 7's JobQuote model,
adding: parts list + labour estimate breakdown, expiry date + enforcement,
and findings/recommendation snapshots (so a quote stays a faithful
point-in-time record even if the job's findings are edited afterward).
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import ServiceOSException
from app.engines.field_ops.constants import JS, JobType


def make_job(status=JS.ASSESSMENT_COMPLETE, job_type=JobType.REPAIR, **kw):
    defaults = dict(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), status=status, job_type=job_type,
        customer_id=uuid.uuid4(), findings="Compressor leaking refrigerant",
        recommendation="Replace compressor unit", title="AC issue",
    )
    defaults.update(kw)
    return MagicMock(**defaults)


def svc_with(job, actor_role="tenant_owner"):
    from app.engines.field_ops.service import FieldOpsService
    result = MagicMock(); result.scalar_one_or_none.return_value = job
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.flush = AsyncMock()
    def fake_add(obj):
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)
    db.add = MagicMock(side_effect=fake_add)
    s = FieldOpsService(db=db, actor_id=uuid.uuid4(), actor_role=actor_role)
    s._write_history = AsyncMock()
    s._publish = AsyncMock()
    return s, db


@pytest.mark.asyncio
async def test_create_quote_captures_parts_and_labour_estimate_separately():
    job = make_job()
    svc, _ = svc_with(job)

    result = await svc.create_quote(
        job.id, Decimal("4500"),
        parts=[{"name": "Compressor", "cost": 3500}, {"name": "Refrigerant", "cost": 500}],
        labour_estimate=Decimal("500"), notes="Standard replacement", expiry_days=7,
    )
    assert result["amount"] == 4500.0
    assert result["labour_estimate"] == 500.0
    assert len(result["parts"]) == 2
    assert result["parts"][0]["name"] == "Compressor"


@pytest.mark.asyncio
async def test_create_quote_snapshots_findings_and_recommendation_from_job():
    job = make_job(findings="Leaking compressor", recommendation="Full unit replacement")
    svc, _ = svc_with(job)

    result = await svc.create_quote(job.id, Decimal("1000"), [], None, None)
    assert result["findings"] == "Leaking compressor"
    assert result["recommendation"] == "Full unit replacement"


@pytest.mark.asyncio
async def test_create_quote_sets_expiry_date_from_expiry_days():
    job = make_job()
    svc, db = svc_with(job)

    before = datetime.now(timezone.utc)
    result = await svc.create_quote(job.id, Decimal("1000"), [], None, None, expiry_days=10)
    after = datetime.now(timezone.utc)

    expires_at = datetime.fromisoformat(result["expires_at"])
    assert before + timedelta(days=10) <= expires_at <= after + timedelta(days=10)


@pytest.mark.asyncio
async def test_quote_snapshot_survives_later_edits_to_job_findings():
    """A quote is a point-in-time record — editing Job.findings afterward must
    not retroactively change what the customer already saw and decided on."""
    job = make_job(findings="Original finding")
    svc, _ = svc_with(job)

    result = await svc.create_quote(job.id, Decimal("1000"), [], None, None)
    job.findings = "Technician changed their mind"  # job edited after quote sent

    assert result["findings"] == "Original finding"


@pytest.mark.asyncio
async def test_respond_to_quote_rejects_when_expired():
    quote = MagicMock(id=uuid.uuid4(), job_id=uuid.uuid4(), customer_id=uuid.uuid4(),
                       status="pending", expires_at=datetime.now(timezone.utc) - timedelta(days=1))
    quote_result = MagicMock(); quote_result.scalar_one_or_none.return_value = quote
    db = MagicMock()
    db.execute = AsyncMock(return_value=quote_result)

    from app.engines.field_ops.service import FieldOpsService
    svc = FieldOpsService(db=db, actor_id=quote.customer_id, actor_role="customer")

    with pytest.raises(ServiceOSException) as exc:
        await svc.respond_to_quote(quote.id, quote.customer_id, True)
    assert exc.value.error_code == "QUOTE_EXPIRED"
    assert quote.status == "expired"  # lazily marked so subsequent reads are accurate


@pytest.mark.asyncio
async def test_respond_to_quote_allows_approval_before_expiry():
    job = make_job(status=JS.QUOTE_PENDING)
    customer_id = job.customer_id
    quote = MagicMock(id=uuid.uuid4(), job_id=job.id, customer_id=customer_id, status="pending",
                       expires_at=datetime.now(timezone.utc) + timedelta(days=3), amount=Decimal("1000"))

    quote_result = MagicMock(); quote_result.scalar_one_or_none.return_value = quote
    job_result = MagicMock(); job_result.scalar_one_or_none.return_value = job
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[quote_result, job_result])

    from app.engines.field_ops.service import FieldOpsService
    svc = FieldOpsService(db=db, actor_id=customer_id, actor_role="customer")
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    result = await svc.respond_to_quote(quote.id, customer_id, True)
    assert quote.status == "approved"
    assert result["approved"] is True


@pytest.mark.asyncio
async def test_quote_dict_marks_expired_pending_quote_as_is_expired():
    from app.engines.field_ops.service import FieldOpsService
    quote = MagicMock(id=uuid.uuid4(), job_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
                       customer_id=uuid.uuid4(), amount=Decimal("500"), parts=[], labour_estimate=None,
                       findings_snapshot=None, recommendation_snapshot=None, notes=None,
                       status="pending", expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                       responded_at=None, created_at=datetime.now(timezone.utc))
    svc = FieldOpsService(db=MagicMock())
    d = svc._quote_dict(quote)
    assert d["is_expired"] is True


@pytest.mark.asyncio
async def test_list_quotes_by_job_returns_newest_first():
    from app.engines.field_ops.service import FieldOpsService
    job_id = uuid.uuid4()
    q1 = MagicMock(id=uuid.uuid4(), job_id=job_id, tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
                   amount=Decimal("100"), parts=[], labour_estimate=None, findings_snapshot=None,
                   recommendation_snapshot=None, notes=None, status="rejected", expires_at=None,
                   responded_at=None, created_at=datetime.now(timezone.utc))
    q2 = MagicMock(id=uuid.uuid4(), job_id=job_id, tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
                   amount=Decimal("150"), parts=[], labour_estimate=None, findings_snapshot=None,
                   recommendation_snapshot=None, notes=None, status="pending", expires_at=None,
                   responded_at=None, created_at=datetime.now(timezone.utc))

    scalars_result = MagicMock(); scalars_result.all.return_value = [q2, q1]
    exec_result = MagicMock(); exec_result.scalars.return_value = scalars_result
    db = MagicMock(); db.execute = AsyncMock(return_value=exec_result)

    svc = FieldOpsService(db=db)
    result = await svc.list_quotes_by_job(job_id)
    assert len(result["quotes"]) == 2
    assert result["quotes"][0]["amount"] == 150.0
