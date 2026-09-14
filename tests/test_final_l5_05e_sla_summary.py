"""FINAL-L5-05E — canonical SLA + operational summary against service_jobs.

Live-verified via curl against real data (see FINAL_L5_05B_JOBS_MIGRATION.md):
GET /v1/admin/final-records/jobs/summary and the sla field on list/detail.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _job(status: str, created_minutes_ago: int, city: str | None = None, zipcode: str | None = None) -> MagicMock:
    j = MagicMock()
    j.id = uuid.uuid4()
    j.status = status
    j.created_at = datetime.now(timezone.utc) - timedelta(minutes=created_minutes_ago)
    j.sla_due_at = j.created_at + timedelta(minutes=60)
    j.arrival_verified_at = None
    j.sla_stopped_at = None
    j.scheduled_date = None
    j.scheduled_time_window = None
    j.city = city
    j.zipcode = zipcode
    return j


class TestComputeSla:
    def test_terminal_job_is_not_applicable(self):
        from app.engines.final_records.sla_summary import compute_sla
        job = _job("completed", 500)
        result = compute_sla(job, 60)
        assert result["sla_status"] == "NOT_APPLICABLE"
        assert result["next_deadline"] is None

    def test_recent_job_is_on_track(self):
        from app.engines.final_records.sla_summary import compute_sla
        job = _job("assigned", 5)
        job.sla_due_at = datetime.now(timezone.utc) + timedelta(hours=2)
        result = compute_sla(job, 60)
        assert result["sla_status"] == "ON_TRACK"
        assert result["minutes_remaining"] is not None
        assert result["minutes_remaining"] > 0

    def test_job_near_deadline_is_at_risk(self):
        from app.engines.final_records.sla_summary import compute_sla
        job = _job("assigned", 55)  # 5 min left of a 60-min window = within 20% threshold
        job.sla_due_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        result = compute_sla(job, 60)
        assert result["sla_status"] == "AT_RISK"

    def test_overdue_job_is_breached(self):
        from app.engines.final_records.sla_summary import compute_sla
        job = _job("assigned", 120)
        result = compute_sla(job, 60)
        assert result["sla_status"] == "BREACHED"
        assert result["minutes_overdue"] is not None
        assert result["minutes_overdue"] > 0

    def test_force_closed_and_voided_are_not_applicable(self):
        from app.engines.final_records.sla_summary import compute_sla
        for status in ("force_closed", "voided", "cancelled", "failed"):
            job = _job(status, 500)
            assert compute_sla(job, 60)["sla_status"] == "NOT_APPLICABLE"

    def test_arrived_or_in_progress_job_is_not_a_no_show_breach(self):
        from app.engines.final_records.sla_summary import compute_sla
        for status in ("reached_site", "inspection_started", "in_progress", "service_started"):
            job = _job(status, 500)
            assert compute_sla(job)["sla_status"] == "NOT_APPLICABLE"

    def test_future_slot_is_not_labelled_overdue_from_booking_age(self):
        from app.engines.final_records.sla_summary import compute_sla
        job = _job("assigned", 500)
        job.sla_due_at = datetime.now(timezone.utc) + timedelta(days=1)
        result = compute_sla(job)
        assert result["sla_status"] == "ON_TRACK"
        assert result["minutes_overdue"] is None


class TestResolveSlaMinutesForJobs:
    @pytest.mark.asyncio
    async def test_no_location_data_uses_default(self):
        from app.engines.final_records.sla_summary import resolve_sla_minutes_for_jobs, DEFAULT_SLA_MINUTES
        jobs = [_job("assigned", 5)]  # no city/zipcode
        db = AsyncMock()
        result = await resolve_sla_minutes_for_jobs(db, jobs)
        assert result[str(jobs[0].id)] == DEFAULT_SLA_MINUTES
        db.execute.assert_not_called()  # no query needed when nothing to resolve

    @pytest.mark.asyncio
    async def test_batches_into_at_most_two_queries(self, monkeypatch):
        from app.engines.final_records import sla_summary
        jobs = [_job("assigned", 5, city="Mumbai"), _job("assigned", 10, zipcode="400001")]

        tier_id = uuid.uuid4()
        loc1 = MagicMock(zipcode=None, city="Mumbai", tier_id=tier_id)
        loc2 = MagicMock(zipcode="400001", city=None, tier_id=tier_id)
        tier = MagicMock(id=tier_id, default_sla_minutes=90)

        call_count = {"n": 0}

        async def fake_execute(*a, **k):
            call_count["n"] += 1
            res = MagicMock()
            if call_count["n"] == 1:
                res.scalars.return_value.all.return_value = [loc1, loc2]
            else:
                res.scalars.return_value.all.return_value = [tier]
            return res

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=fake_execute)
        result = await sla_summary.resolve_sla_minutes_for_jobs(db, jobs)
        assert call_count["n"] == 2
        assert all(v == 90 for v in result.values())


class TestSummaryEndpoint:
    def test_admin_router_exposes_summary_before_job_id(self):
        from app.engines.final_records.admin_router import router
        paths = [r.path for r in router.routes]
        summary_idx = paths.index("/v1/admin/final-records/jobs/summary")
        detail_idx = paths.index("/v1/admin/final-records/jobs/{job_id}")
        assert summary_idx < detail_idx  # registration order matters for FastAPI route matching
