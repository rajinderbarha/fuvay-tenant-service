"""Automatic Trust & Quality refresh scheduling regressions."""

from datetime import datetime, timedelta, timezone

import pytest

from app.jobs import trust_quality_worker as worker


class _ScalarDB:
    def __init__(self, *values):
        self.values = list(values)
        self.calls = 0

    async def scalar(self, _statement):
        self.calls += 1
        return self.values.pop(0)


class _Service:
    def __init__(self, _db):
        self.seed_calls = 0
        self.enqueue_calls = []

    async def seed_defaults(self):
        self.seed_calls += 1
        return {"badges": 12, "badge_rules": 12, "health_formulas": 0}

    async def enqueue_recalculation_job(self, job_type, scope_type, triggered_by):
        self.enqueue_calls.append((job_type, scope_type, triggered_by))
        return {"already_running": False}


@pytest.mark.anyio
async def test_due_refresh_repairs_catalog_then_queues_full_sweep(monkeypatch):
    from app.engines.trust_quality import service as service_module

    instance = None

    def make_service(db):
        nonlocal instance
        instance = _Service(db)
        return instance

    monkeypatch.setattr(service_module, "TrustQualityService", make_service)
    db = _ScalarDB(None, None)  # no active job and no completed full sweep

    queued = await worker._enqueue_automatic_refresh_if_due(
        db, datetime(2026, 9, 13, tzinfo=timezone.utc)
    )

    assert queued is True
    assert instance is not None
    assert instance.seed_calls == 1
    assert instance.enqueue_calls == [("all", "all", "scheduled")]


@pytest.mark.anyio
async def test_recent_completed_sweep_is_not_queued_again(monkeypatch):
    from app.engines.trust_quality import service as service_module

    monkeypatch.setattr(
        service_module,
        "TrustQualityService",
        lambda _db: pytest.fail("fresh results must not reseed or enqueue"),
    )
    now = datetime(2026, 9, 13, tzinfo=timezone.utc)
    db = _ScalarDB(None, now - timedelta(hours=1))

    assert await worker._enqueue_automatic_refresh_if_due(db, now) is False
    assert db.calls == 2


@pytest.mark.anyio
async def test_in_flight_manual_job_blocks_automatic_duplicate(monkeypatch):
    from app.engines.trust_quality import service as service_module

    monkeypatch.setattr(
        service_module,
        "TrustQualityService",
        lambda _db: pytest.fail("an active job must short-circuit scheduling"),
    )
    db = _ScalarDB("active-job-id")

    assert await worker._enqueue_automatic_refresh_if_due(db) is False
    assert db.calls == 1
