"""MODULE-L5-65 — late / today / upcoming, from the one fact that is real.

The live jobs table carries only the committed slot. The columns that sound like an SLA
clock (`jobs.sla_breached`, `jobs.sla_breach_level`, `jobs.sla_minutes`) belong to the
legacy `field_ops` table, which holds ZERO rows -- reading those and calling the answer
an "SLA breach" would report a number nobody measured. So lateness is derived from the
window the provider committed to, having passed with the work unfinished.

The direction of every edge case here is deliberate: when unsure, do NOT call a job
late. Telling a customer their provider failed them when they did not is the more
expensive mistake.
"""
from __future__ import annotations

import datetime as dt

from app.engines.home_service_assignment.urgency import (
    URGENCY_LATE, URGENCY_TODAY, URGENCY_UNSCHEDULED, URGENCY_UPCOMING,
    classify, describe, minutes_late,
)

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
NOW = dt.datetime(2026, 8, 12, 14, 30, tzinfo=IST)
TODAY = NOW.date()


class TestTheThreeGroups:
    def test_a_window_that_has_passed_is_late(self):
        assert classify("accepted", TODAY, "10:00-11:00", NOW) == URGENCY_LATE

    def test_a_window_later_today_is_today(self):
        assert classify("accepted", TODAY, "18:00-19:00", NOW) == URGENCY_TODAY

    def test_a_window_still_running_is_today_not_late(self):
        # 14:30 sits inside 14:00-15:00. The provider has not missed anything yet.
        assert classify("accepted", TODAY, "14:00-15:00", NOW) == URGENCY_TODAY

    def test_a_future_date_is_upcoming(self):
        assert classify("accepted", TODAY + dt.timedelta(days=2), "10:00-11:00", NOW) == URGENCY_UPCOMING

    def test_a_job_with_no_slot_is_unscheduled_not_upcoming(self):
        # Its own answer on purpose: a job nobody has committed to is not a job
        # scheduled for later. It is a different thing to say and a different thing
        # to fix.
        assert classify("pending_assignment", None, None, NOW) == URGENCY_UNSCHEDULED

    def test_an_unreadable_window_is_unscheduled_rather_than_late(self):
        # Never invent a deadline from text nobody can parse.
        assert classify("accepted", TODAY, "sometime after lunch", NOW) == URGENCY_UNSCHEDULED


class TestLatenessIsMeasuredFromTheEnd:
    def test_arriving_inside_the_window_is_not_late(self):
        # A technician at 14:45 for a 14:00-15:00 slot is on time. Measuring from the
        # START would call that late, which is wrong in the direction that matters.
        assert classify("on_the_way", TODAY, "14:00-15:00", NOW) != URGENCY_LATE

    def test_one_minute_past_the_window_is_late(self):
        just_after = dt.datetime(2026, 8, 12, 15, 1, tzinfo=IST)
        assert classify("accepted", TODAY, "14:00-15:00", just_after) == URGENCY_LATE

    def test_a_window_with_no_end_uses_a_stated_assumption(self):
        # "14:00" alone: two hours is assumed, so 15:30 is not yet late and 16:30 is.
        assert classify("accepted", TODAY, "14:00", dt.datetime(2026, 8, 12, 15, 30, tzinfo=IST)) != URGENCY_LATE
        assert classify("accepted", TODAY, "14:00", dt.datetime(2026, 8, 12, 16, 30, tzinfo=IST)) == URGENCY_LATE

    def test_a_window_crossing_midnight_ends_the_next_day(self):
        late_night = dt.datetime(2026, 8, 13, 0, 30, tzinfo=IST)
        assert classify("accepted", TODAY, "23:00-01:00", late_night) == URGENCY_TODAY


class TestWorkInProgressAndFinishedWork:
    def test_a_started_job_past_its_window_is_still_late(self):
        # Someone turning up eventually does not un-miss the slot, and hiding it is how
        # a delay stops being visible to anyone.
        assert classify("service_started", TODAY, "09:00-10:00", NOW) == URGENCY_LATE

    def test_a_completed_job_has_no_urgency_at_all(self):
        # A finished job that ran late is history. Listing it under "Late" would tell a
        # customer something still needs doing.
        assert classify("completed", TODAY, "09:00-10:00", NOW) is None

    def test_a_cancelled_job_has_no_urgency(self):
        assert classify("cancelled", TODAY, "09:00-10:00", NOW) is None

    def test_status_case_and_padding_do_not_change_the_answer(self):
        assert classify("  COMPLETED ", TODAY, "09:00-10:00", NOW) is None


class TestCountingAndWording:
    def test_counts_real_minutes_past_the_window(self):
        assert minutes_late("accepted", TODAY, "13:00-14:00", NOW) == 30

    def test_nothing_to_count_when_not_late(self):
        assert minutes_late("accepted", TODAY, "18:00-19:00", NOW) is None
        assert minutes_late("completed", TODAY, "09:00-10:00", NOW) is None

    def test_wording_rounds_down_so_it_never_overstates(self):
        # 119 minutes is "1 hour late", not "2 hours".
        assert describe(45) == "45 min late"
        assert describe(119) == "1 hour late"
        assert describe(120) == "2 hours late"
        assert describe(60 * 24) == "1 day late"
        assert describe(60 * 49) == "2 days late"

    def test_no_wording_for_nothing(self):
        assert describe(None) is None
        assert describe(0) is None
