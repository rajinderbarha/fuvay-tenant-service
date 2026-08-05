"""WORK-IN-PROGRESS-COMPLETION-RATING phase -- covers 2 real fixes:
(1) `_customer_safe_job` now exposes an allow-listed `completion` object
    only when `job.status == "completed"`.
(2) `submit_booking_rating`/`get_booking_rating` now forward/return
    `review_tags` and never leak `CustomerReview.to_dict()` verbatim.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.final_records.customer_router import _customer_safe_job
from app.engines.home_service_assignment.customer_router import submit_booking_rating, get_booking_rating
from app.exceptions import ServiceOSException


def _job(**overrides):
    defaults = dict(
        id=uuid.uuid4(), status="completed", assignment_status="assigned",
        assigned_staff_id=None, tenant_id=uuid.uuid4(),
        scheduled_date=None, scheduled_time_window=None, updated_at=None,
        completion_data=None,
    )
    defaults.update(overrides)
    job = MagicMock()
    for k, v in defaults.items():
        setattr(job, k, v)
    return job


def _scalars(items):
    result = MagicMock()
    result.scalars.return_value.first.return_value = items[0] if items else None
    return result


@pytest.mark.asyncio
async def test_completed_job_exposes_allow_listed_completion_fields():
    job = _job(completion_data={
        "work_summary": "Cooling restored, capacitor replaced.",
        "collected_amount": 2300.0,
        "payment_mode": "customer_pays_provider_directly",
        "completed_at": "2026-08-02T10:00:00+00:00",
        "before_photo_ids": ["p1"], "after_photo_ids": ["p2"], "completion_photo_ids": ["p3"],
        "customer_signature_id": "sig-1", "technician_note": "internal note",
        "completed_by_staff_id": str(uuid.uuid4()),
    })
    db = MagicMock()
    db.scalar = AsyncMock(return_value=None)
    data = await _customer_safe_job(db, job)
    assert data["completion"] == {
        "work_summary": "Cooling restored, capacitor replaced.",
        "collected_amount": 2300.0,
        "completed_at": "2026-08-02T10:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_completion_never_exposes_internal_fields():
    job = _job(completion_data={
        "work_summary": "Done", "collected_amount": 100.0, "completed_at": None,
        "technician_note": "secret", "completed_by_staff_id": str(uuid.uuid4()),
        "customer_signature_id": "sig", "before_photo_ids": ["a"],
    })
    db = MagicMock()
    db.scalar = AsyncMock(return_value=None)
    data = await _customer_safe_job(db, job)
    keys = set(data["completion"].keys())
    assert keys == {"work_summary", "collected_amount", "completed_at"}


@pytest.mark.asyncio
async def test_non_completed_job_has_no_completion_object():
    job = _job(status="service_started", completion_data=None)
    db = MagicMock()
    db.scalar = AsyncMock(return_value=None)
    data = await _customer_safe_job(db, job)
    assert data["completion"] is None


@pytest.mark.asyncio
async def test_completed_job_without_completion_data_is_handled_safely():
    job = _job(status="completed", completion_data=None)
    db = MagicMock()
    db.scalar = AsyncMock(return_value=None)
    data = await _customer_safe_job(db, job)
    assert data["completion"] is None


class _FakeReview:
    def __init__(self, **kw):
        self.overall_rating = kw.get("overall_rating", 5)
        self.review_text = kw.get("review_text")
        self.review_tags = kw.get("review_tags")
        self.created_at = kw.get("created_at")


@pytest.mark.asyncio
async def test_submit_rating_forwards_tags_and_returns_allow_listed_shape(monkeypatch):
    customer_id = uuid.uuid4()
    booking = MagicMock(customer_id=customer_id, tenant_id=uuid.uuid4(), id=uuid.uuid4())
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([booking]))
    request = MagicMock()
    request.json = AsyncMock(return_value={"rating": 5, "comment": "Great work", "tags": ["professional", "on_time"]})
    request.headers = {"content-length": "50"}
    request.state.request_id = "r1"
    user = MagicMock(user_id=str(customer_id))

    captured = {}

    async def fake_submit_review(self, db, **kwargs):
        captured.update(kwargs)
        return _FakeReview(overall_rating=5, review_text="Great work", review_tags=["professional", "on_time"])

    import app.engines.customer_reviews.review_service as review_service_module
    monkeypatch.setattr(review_service_module.ReviewService, "submit_review", fake_submit_review)

    result = await submit_booking_rating(booking_id=booking.id, r=request, user=user, db=db)

    assert captured["review_tags"] == ["professional", "on_time"]
    assert result.data["review"]["tags"] == ["professional", "on_time"]
    assert "customer_id" not in result.data["review"]
    assert "tenant_id" not in result.data["review"]
    assert "staff_member_id" not in result.data["review"]


@pytest.mark.asyncio
async def test_submit_rating_rejects_non_list_tags():
    customer_id = uuid.uuid4()
    booking = MagicMock(customer_id=customer_id, tenant_id=uuid.uuid4(), id=uuid.uuid4())
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([booking]))
    request = MagicMock()
    request.json = AsyncMock(return_value={"rating": 5, "tags": "professional"})
    request.headers = {"content-length": "30"}
    request.state.request_id = "r1"
    user = MagicMock(user_id=str(customer_id))
    with pytest.raises(ServiceOSException):
        await submit_booking_rating(booking_id=booking.id, r=request, user=user, db=db)


@pytest.mark.asyncio
async def test_get_rating_includes_tags():
    customer_id = uuid.uuid4()
    review = _FakeReview(overall_rating=4, review_text="Good", review_tags=["clean_work"], created_at=None)
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([review]))
    request = MagicMock()
    request.state.request_id = "r1"
    user = MagicMock(user_id=str(customer_id))
    result = await get_booking_rating(booking_id=uuid.uuid4(), r=request, user=user, db=db)
    assert result.data["review"]["tags"] == ["clean_work"]


@pytest.mark.asyncio
async def test_duplicate_review_returns_409(monkeypatch):
    customer_id = uuid.uuid4()
    booking = MagicMock(customer_id=customer_id, tenant_id=uuid.uuid4(), id=uuid.uuid4())
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([booking]))
    request = MagicMock()
    request.json = AsyncMock(return_value={"rating": 5})
    request.headers = {"content-length": "20"}
    request.state.request_id = "r1"
    user = MagicMock(user_id=str(customer_id))

    async def fake_submit_review(self, db, **kwargs):
        raise ValueError("REVIEW_ALREADY_EXISTS")

    import app.engines.customer_reviews.review_service as review_service_module
    monkeypatch.setattr(review_service_module.ReviewService, "submit_review", fake_submit_review)

    with pytest.raises(ServiceOSException) as exc:
        await submit_booking_rating(booking_id=booking.id, r=request, user=user, db=db)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_review_before_completion_is_rejected(monkeypatch):
    customer_id = uuid.uuid4()
    booking = MagicMock(customer_id=customer_id, tenant_id=uuid.uuid4(), id=uuid.uuid4())
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([booking]))
    request = MagicMock()
    request.json = AsyncMock(return_value={"rating": 5})
    request.headers = {"content-length": "20"}
    request.state.request_id = "r1"
    user = MagicMock(user_id=str(customer_id))

    async def fake_submit_review(self, db, **kwargs):
        raise ValueError("REVIEW_NOT_ELIGIBLE")

    import app.engines.customer_reviews.review_service as review_service_module
    monkeypatch.setattr(review_service_module.ReviewService, "submit_review", fake_submit_review)

    with pytest.raises(ServiceOSException) as exc:
        await submit_booking_rating(booking_id=booking.id, r=request, user=user, db=db)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_invalid_rating_value_rejected():
    customer_id = uuid.uuid4()
    booking = MagicMock(customer_id=customer_id, tenant_id=uuid.uuid4(), id=uuid.uuid4())
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([booking]))
    request = MagicMock()
    request.json = AsyncMock(return_value={"rating": 7})
    request.headers = {"content-length": "20"}
    request.state.request_id = "r1"
    user = MagicMock(user_id=str(customer_id))
    with pytest.raises(ServiceOSException) as exc:
        await submit_booking_rating(booking_id=booking.id, r=request, user=user, db=db)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_foreign_customer_cannot_rate_booking():
    booking = MagicMock(customer_id=uuid.uuid4(), tenant_id=uuid.uuid4(), id=uuid.uuid4())
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([booking]))
    request = MagicMock()
    request.json = AsyncMock(return_value={"rating": 5})
    request.headers = {"content-length": "20"}
    request.state.request_id = "r1"
    user = MagicMock(user_id=str(uuid.uuid4()))
    with pytest.raises(ServiceOSException) as exc:
        await submit_booking_rating(booking_id=booking.id, r=request, user=user, db=db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_rating_returns_null_when_no_review_exists():
    db = MagicMock()
    db.execute = AsyncMock(return_value=_scalars([]))
    request = MagicMock()
    request.state.request_id = "r1"
    user = MagicMock(user_id=str(uuid.uuid4()))
    result = await get_booking_rating(booking_id=uuid.uuid4(), r=request, user=user, db=db)
    assert result.data["review"] is None
