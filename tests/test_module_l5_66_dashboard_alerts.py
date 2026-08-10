"""MODULE-L5-66 — what the provider dashboard interrupts about, and in what tone.

Two different messages that must never look alike: a new job is good news worth
celebrating, a job past its slot needs an action today. The `tone` on each alert is what
lets a surface tell them apart without parsing the wording, and it reuses the
notification registry's own severity vocabulary rather than a second scale.

The delay notification is the part with teeth: a dashboard polling every thirty seconds
must not become a notification every thirty seconds, and a cap meant for a popup must
never decide how many jobs get reported.
"""
from __future__ import annotations

import datetime as dt
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.home_service_assignment import dashboard_alerts
from app.engines.home_service_assignment.dashboard_alerts import (
    NEW_JOB_WINDOW_HOURS, TONE_CELEBRATE, TONE_URGENT, build_alerts, notify_delayed_jobs,
)

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
NOW = dt.datetime(2026, 8, 12, 14, 30, tzinfo=dt.timezone.utc)
TENANT = uuid.uuid4()


def job(**overrides):
    row = MagicMock()
    row.id = overrides.get("id", uuid.uuid4())
    row.job_number = overrides.get("job_number", "JOB-1")
    row.status = overrides.get("status", "accepted")
    row.scheduled_date = overrides.get("scheduled_date")
    row.scheduled_time_window = overrides.get("scheduled_time_window")
    row.created_at = overrides.get("created_at", NOW - dt.timedelta(days=3))
    row.city = overrides.get("city", "Ludhiana")
    return row


async def alerts_for(jobs, since=None, now=NOW):
    with patch.object(dashboard_alerts, "_load_jobs", new=AsyncMock(return_value=jobs)):
        return await build_alerts(MagicMock(), TENANT, since=since, now=now)


class TestNewJobs:
    @pytest.mark.asyncio
    async def test_a_job_that_just_arrived_is_celebrated(self):
        result = await alerts_for([job(
            status="pending_assignment", created_at=NOW - dt.timedelta(minutes=5),
        )])
        assert result["new_job_total"] == 1
        alert = result["new_jobs"][0]
        assert alert["tone"] == TONE_CELEBRATE
        assert "New job" in alert["title"]

    @pytest.mark.asyncio
    async def test_a_job_that_arrived_already_accepted_is_still_news(self):
        # Real bug this pins: "new" required `pending_assignment`, and on this platform
        # bookings arrive already `accepted` -- so a service booked from the customer app
        # produced no popup at all. Verified live: the newest three bookings were
        # "accepted" within minutes of being made, and new_job_total was 0.
        result = await alerts_for([job(status="accepted", created_at=NOW - dt.timedelta(minutes=5))])
        assert result["new_job_total"] == 1

    @pytest.mark.asyncio
    async def test_a_job_that_arrived_and_is_already_finished_is_not_news(self):
        # Congratulating someone for work already done would be absurd.
        result = await alerts_for([job(status="completed", created_at=NOW - dt.timedelta(minutes=5))])
        assert result["new_job_total"] == 0

    @pytest.mark.asyncio
    async def test_without_a_since_only_a_stated_window_counts_as_new(self):
        # "42 new jobs!" on a first login is a backlog, not news.
        old = job(status="pending_assignment",
                  created_at=NOW - dt.timedelta(hours=NEW_JOB_WINDOW_HOURS + 1))
        recent = job(status="pending_assignment", created_at=NOW - dt.timedelta(hours=1))
        result = await alerts_for([old, recent])
        assert result["new_job_total"] == 1

    @pytest.mark.asyncio
    async def test_since_is_what_stops_congratulating_twice(self):
        arrived = job(status="pending_assignment", created_at=NOW - dt.timedelta(hours=2))
        seen_already = await alerts_for([arrived], since=NOW - dt.timedelta(minutes=30))
        assert seen_already["new_job_total"] == 0

    @pytest.mark.asyncio
    async def test_newest_first(self):
        older = job(job_number="JOB-OLD", status="pending_assignment",
                    created_at=NOW - dt.timedelta(hours=5))
        newer = job(job_number="JOB-NEW", status="pending_assignment",
                    created_at=NOW - dt.timedelta(minutes=5))
        result = await alerts_for([older, newer])
        assert [a["label"] for a in result["new_jobs"]] == ["JOB-NEW", "JOB-OLD"]


class TestDelayedJobs:
    @pytest.mark.asyncio
    async def test_a_job_past_its_slot_is_urgent_and_says_how_late(self):
        result = await alerts_for([job(
            status="accepted",
            scheduled_date=(NOW.astimezone(IST) - dt.timedelta(days=2)).date(),
            scheduled_time_window="10:00-11:00",
        )])
        assert result["delayed_total"] == 1
        alert = result["delayed_jobs"][0]
        assert alert["tone"] == TONE_URGENT
        assert alert["lateness_label"].endswith("late")
        assert alert["minutes_late"] > 0

    @pytest.mark.asyncio
    async def test_the_worst_delay_is_first(self):
        # The one that gets seen should be the one that has waited longest.
        today_ist = NOW.astimezone(IST).date()
        mild = job(job_number="JOB-MILD", scheduled_date=today_ist, scheduled_time_window="10:00-11:00")
        severe = job(job_number="JOB-SEVERE",
                     scheduled_date=today_ist - dt.timedelta(days=4),
                     scheduled_time_window="10:00-11:00")
        result = await alerts_for([mild, severe])
        assert [a["label"] for a in result["delayed_jobs"]] == ["JOB-SEVERE", "JOB-MILD"]

    @pytest.mark.asyncio
    async def test_a_completed_job_is_never_reported_as_delayed(self):
        result = await alerts_for([job(
            status="completed",
            scheduled_date=(NOW.astimezone(IST) - dt.timedelta(days=3)).date(),
            scheduled_time_window="10:00-11:00",
        )])
        assert result["delayed_total"] == 0

    @pytest.mark.asyncio
    async def test_a_job_with_no_slot_is_not_delayed(self):
        # Nobody committed to a time, so no time has been missed.
        result = await alerts_for([job(status="pending_assignment", scheduled_date=None)])
        assert result["delayed_total"] == 0

    @pytest.mark.asyncio
    async def test_the_two_kinds_never_share_a_tone(self):
        today_ist = NOW.astimezone(IST).date()
        result = await alerts_for([
            job(status="pending_assignment", created_at=NOW - dt.timedelta(minutes=5)),
            job(status="accepted", scheduled_date=today_ist - dt.timedelta(days=1),
                scheduled_time_window="10:00-11:00"),
        ])
        assert result["new_jobs"][0]["tone"] != result["delayed_jobs"][0]["tone"]


class TestTotalsAndCapping:
    @pytest.mark.asyncio
    async def test_the_service_returns_every_delay_not_a_capped_page(self):
        # Real bug this pins: the cap used to live in the service, so the notifier only
        # ever saw the first five -- 25 late jobs produced 5 notifications and the other
        # 20 were never reported to anyone. Capping is the popup's business.
        today_ist = NOW.astimezone(IST).date()
        many = [
            job(job_number=f"JOB-{i}", scheduled_date=today_ist - dt.timedelta(days=1),
                scheduled_time_window="10:00-11:00")
            for i in range(12)
        ]
        result = await alerts_for(many)
        assert result["delayed_total"] == 12
        assert len(result["delayed_jobs"]) == 12

    @pytest.mark.asyncio
    async def test_as_of_is_returned_so_the_next_poll_can_say_since(self):
        result = await alerts_for([])
        assert result["as_of"] == NOW.isoformat()


class TestTheDelayNotification:
    @pytest.mark.asyncio
    async def test_raises_one_event_per_job(self):
        alerts = [
            {"job_id": str(uuid.uuid4()), "label": "JOB-1", "lateness_label": "2 hours late"},
            {"job_id": str(uuid.uuid4()), "label": "JOB-2", "lateness_label": "1 day late"},
        ]
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        service = MagicMock()
        service.fire_event = AsyncMock()

        with patch("app.engines.platform_notifications.notification_service.NotificationService",
                   return_value=service):
            sent = await notify_delayed_jobs(db, TENANT, alerts)

        assert sent == 2
        assert service.fire_event.await_count == 2

    @pytest.mark.asyncio
    async def test_never_reports_the_same_job_twice(self):
        # A dashboard polling every thirty seconds must not become a notification every
        # thirty seconds. The guard is what was actually SENT, not a flag on the job that
        # could drift away from reality.
        job_id = uuid.uuid4()
        alerts = [{"job_id": str(job_id), "label": "JOB-1", "lateness_label": "2 hours late"}]
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[(job_id,)])))
        service = MagicMock()
        service.fire_event = AsyncMock()

        with patch("app.engines.platform_notifications.notification_service.NotificationService",
                   return_value=service):
            sent = await notify_delayed_jobs(db, TENANT, alerts)

        assert sent == 0
        service.fire_event.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_nothing_to_report_touches_nothing(self):
        db = MagicMock()
        db.execute = AsyncMock()
        assert await notify_delayed_jobs(db, TENANT, []) == 0
        db.execute.assert_not_awaited()

    def test_the_event_is_registered_and_carries_a_warning_tone(self):
        # An unregistered key makes fire_event a silent no-op, which is how a
        # notification feature ships looking complete and never delivers anything.
        from app.engines.platform_notifications.constants import EVT_JOB_DELAYED, SEV_WARNING
        from app.engines.platform_notifications.event_registry import NotificationEventRegistry

        cfg = NotificationEventRegistry.get(EVT_JOB_DELAYED)
        assert cfg is not None
        assert cfg.severity == SEV_WARNING
        assert cfg.primary_recipient == "provider"
