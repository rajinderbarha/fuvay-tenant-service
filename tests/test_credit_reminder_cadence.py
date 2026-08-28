"""Reminding a provider without training them to mute you.

A fixed every-two-hours reminder is how a provider learns to silence the
channel -- and they silence all of it, including the job assignment that
arrives next. The cadence is tied to severity so the platform earns the right
to be loud at the point where it is genuinely blocking someone's business.
"""
from __future__ import annotations

import datetime as dt
import inspect
from decimal import Decimal as D

from app.engines.vertical_catalog.credit_reminder_service import (
    DEFAULT_CADENCE_HOURS as C,
    is_due,
    resolve_level,
)

NOW = dt.datetime(2026, 8, 28, 12, 0, tzinfo=dt.timezone.utc)


def ago(hours: float) -> dt.datetime:
    return NOW - dt.timedelta(hours=hours)


class TestLevel:
    def test_a_healthy_balance_says_nothing(self):
        assert resolve_level(D("1000"), D("100"), D("300")) is None

    def test_below_the_warning_is_low(self):
        assert resolve_level(D("200"), D("100"), D("300")) == "low"

    def test_below_the_floor_is_blocked(self):
        assert resolve_level(D("50"), D("100"), D("300")) == "blocked"

    def test_negative_is_arrears(self):
        assert resolve_level(D("-10"), D("100"), D("300")) == "arrears"

    def test_it_matches_the_order_the_pill_uses(self):
        """A provider must never be told one thing by a notification and
        another by their own header."""
        # Exactly at the floor is not yet blocked; below it is.
        assert resolve_level(D("100"), D("100"), D("300")) == "low"
        assert resolve_level(D("99.99"), D("100"), D("300")) == "blocked"


class TestCadenceEscalatesWithSeverity:
    def test_low_is_daily(self):
        assert not is_due("low", "low", ago(3), C, NOW)
        assert is_due("low", "low", ago(25), C, NOW)

    def test_blocked_is_six_hourly(self):
        assert not is_due("blocked", "blocked", ago(3), C, NOW)
        assert is_due("blocked", "blocked", ago(7), C, NOW)

    def test_arrears_is_two_hourly(self):
        assert not is_due("arrears", "arrears", ago(1), C, NOW)
        assert is_due("arrears", "arrears", ago(3), C, NOW)

    def test_the_defaults_escalate(self):
        assert C["low"] > C["blocked"] > C["arrears"]


class TestEscalationDoesNotWait:
    def test_crossing_into_a_worse_level_sends_immediately(self):
        """The moment bookings stop is the moment worth telling someone
        about -- not six hours later, after the gentler tier's interval."""
        assert is_due("blocked", "low", ago(0.08), C, NOW)
        assert is_due("arrears", "blocked", ago(0.08), C, NOW)

    def test_improving_does_not_trigger_a_send(self):
        # Recovering from blocked to low is good news, not an alert.
        assert not is_due("low", "blocked", ago(1), C, NOW)

    def test_the_first_reminder_always_sends(self):
        assert is_due("low", None, None, C, NOW)


class TestRecoveryClearsTheState:
    def test_both_fields_are_cleared(self):
        from app.engines.vertical_catalog import credit_reminder_service as r
        src = inspect.getsource(r.sweep)
        # Leaving the level set would make the next dip look like a repeat
        # rather than a fresh escalation, delaying the notification that
        # matters most.
        assert "credit_reminder_level = NULL" in src
        assert "last_credit_reminder_at = NULL" in src

    def test_a_recovered_provider_is_not_chased(self):
        from app.engines.vertical_catalog import credit_reminder_service as r
        src = inspect.getsource(r.sweep)
        idx = src.index("if level is None:")
        assert "continue" in src[idx:idx + 700]


class TestTheCopyIsHonest:
    def test_blocked_says_booked_work_still_finishes(self):
        from app.engines.vertical_catalog.credit_reminder_service import _COPY
        assert "already booked are unaffected" in _COPY["blocked"][1]

    def test_arrears_explains_the_team_suspension(self):
        from app.engines.vertical_catalog.credit_reminder_service import _COPY
        assert "technicians cannot be assigned" in _COPY["arrears"][1]

    def test_every_level_offers_a_way_out(self):
        from app.engines.vertical_catalog import credit_reminder_service as r
        src = inspect.getsource(r.sweep)
        assert 'action_label="Top up"' in src


class TestCadenceIsAdminPolicy:
    def test_all_three_are_draftable(self):
        from app.engines.vertical_monetization.policy_service import _DRAFT_FIELDS
        for f in ("credit_reminder_hours_low", "credit_reminder_hours_blocked",
                  "credit_reminder_hours_arrears"):
            assert f in _DRAFT_FIELDS, f

    def test_the_model_carries_them(self):
        from app.engines.vertical_monetization.models import VerticalMonetizationPolicy as P
        for f in ("credit_reminder_hours_low", "credit_reminder_hours_blocked",
                  "credit_reminder_hours_arrears"):
            assert hasattr(P, f), f

    def test_unset_falls_back_to_the_escalating_defaults(self):
        from app.engines.vertical_catalog import credit_reminder_service as r
        src = inspect.getsource(r._cadence)
        assert "DEFAULT_CADENCE_HOURS" in src

    def test_the_loop_is_wired_in(self):
        from app import main
        assert "credit_reminders" in inspect.getsource(main)
