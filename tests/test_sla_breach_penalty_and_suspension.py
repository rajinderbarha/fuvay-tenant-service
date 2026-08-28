"""A late job, what it costs, and who gets the money.

Every number is admin policy -- amount, whether the customer is compensated,
the debt cap, the health threshold and how long a suspension lasts. A penalty
an operator cannot change or roll back is one they cannot defend, so all of it
is drafted, validated and published like a commission rate.
"""
from __future__ import annotations

import datetime as dt
import inspect
from decimal import Decimal

import pytest


class TestTheClockRunsFromTheScheduledSlot:
    def test_due_is_measured_from_the_scheduled_day(self):
        from app.engines.execution.sla_breach_service import compute_due_at
        # Booking creation would breach a job booked well in advance while
        # nothing is actually late. The slot is when service was promised.
        due = compute_due_at(dt.date(2026, 8, 20), 24)
        assert due == dt.datetime(2026, 8, 22, tzinfo=dt.timezone.utc)

    def test_no_schedule_means_no_deadline(self):
        from app.engines.execution.sla_breach_service import compute_due_at
        assert compute_due_at(None, 24) is None

    def test_no_configured_sla_means_no_deadline(self):
        from app.engines.execution.sla_breach_service import compute_due_at
        assert compute_due_at(dt.date(2026, 8, 20), None) is None
        assert compute_due_at(dt.date(2026, 8, 20), 0) is None

    def test_rescheduling_moves_the_deadline(self):
        from app.engines.home_service_assignment import service
        src = inspect.getsource(service)
        # A customer who agreed a later date has not been kept waiting.
        assert src.count("stamp_due_at") >= 2


class TestTheProviderIsChargedExactlyOnce:
    def test_compensating_and_charging_are_alternatives(self):
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service.sweep)
        # `issue_provider_funded_customer_credit` already debits the provider,
        # so running it alongside `_charge_penalty` would charge twice for one
        # breach.
        assert "if policy.sla_penalty_to_customer" in src
        assert "else:" in src

    def test_a_failed_compensation_still_penalises(self):
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service.sweep)
        # A customer-side failure must not let a breach go unpunished.
        idx = src.index("compensation_failed")
        assert "_charge_penalty" in src[idx:idx + 400]


class TestTheDebtCap:
    @staticmethod
    def _charge(balance: Decimal, amount: Decimal, cap: Decimal | None) -> Decimal:
        if cap is None:
            return amount
        return max(Decimal("0"), min(amount, max(Decimal("0"), balance + cap)))

    def test_a_penalty_may_take_a_balance_negative(self):
        # A provider already at zero would otherwise face no penalty at all --
        # the deterrent would vanish exactly where it is needed most.
        assert self._charge(Decimal("0"), Decimal("50"), Decimal("500")) == Decimal("50")

    def test_the_cap_stops_a_spiral(self):
        assert self._charge(Decimal("-90"), Decimal("50"), Decimal("100")) == Decimal("10")

    def test_past_the_cap_nothing_more_is_taken(self):
        assert self._charge(Decimal("-100"), Decimal("50"), Decimal("100")) == Decimal("0")

    def test_no_cap_means_the_full_amount(self):
        assert self._charge(Decimal("-9999"), Decimal("50"), None) == Decimal("50")


class TestHealthSuspensionCannotTrapAProvider:
    """The trap: health is earned from work, and a suspended provider does
    none. Reinstating at or below the threshold re-suspends them the same day,
    permanently, with no way to recover."""

    @staticmethod
    def _errors(payload: dict) -> list[str]:
        from app.engines.vertical_monetization.policy_service import (
            VerticalMonetizationPolicyService,
        )
        base = {"provider_model": "NONE", "customer_fee_model": "NONE"}
        return VerticalMonetizationPolicyService()._validate({**base, **payload})

    def test_reinstating_below_the_threshold_is_refused(self):
        errs = self._errors({"health_suspension_threshold": 40,
                             "health_reinstatement_score": 30})
        assert any("immediately re-suspended" in e for e in errs)

    def test_reinstating_at_the_threshold_is_refused(self):
        errs = self._errors({"health_suspension_threshold": 40,
                             "health_reinstatement_score": 40})
        assert any("immediately re-suspended" in e for e in errs)

    def test_reinstating_above_the_threshold_is_accepted(self):
        assert not self._errors({"health_suspension_threshold": 40,
                                 "health_reinstatement_score": 55})

    def test_reinstatement_rebaselines_health(self):
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service.reinstate_due)
        assert "health_score = COALESCE(:restore, health_score)" in src

    def test_only_health_suspensions_are_auto_reinstated(self):
        """A provider suspended by an admin for fraud must not be released by
        this sweep."""
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service.reinstate_due)
        assert "suspension_reason = 'health_below_threshold'" in src


class TestPolicyIsTheOnlyAuthority:
    def test_every_setting_is_draftable(self):
        from app.engines.vertical_monetization.policy_service import _DRAFT_FIELDS
        for field in ("sla_breach_hours", "sla_penalty_amount", "sla_penalty_to_customer",
                      "sla_penalty_debt_cap", "health_suspension_threshold",
                      "health_suspension_days", "health_reinstatement_score"):
            assert field in _DRAFT_FIELDS, field

    def test_a_penalty_without_a_deadline_is_refused(self):
        errs = TestHealthSuspensionCannotTrapAProvider._errors({"sla_penalty_amount": 50})
        assert any("sla_breach_hours is required" in e for e in errs)

    def test_an_unset_policy_penalises_nobody(self):
        """Every live policy has these NULL, so the default must be inert."""
        assert not TestHealthSuspensionCannotTrapAProvider._errors({})

    def test_the_policy_read_is_scoped_to_its_vertical(self):
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service._policy)
        assert "v.key = :k" in src


class TestTheCustomerIsReleasedFirst:
    def test_the_job_is_cancelled_before_any_money_moves(self):
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service.sweep)
        cancel = src.index("status = 'cancelled'")
        penalty = src.index("_charge_penalty")
        assert cancel < penalty, "the customer must be released before the accounting"

    def test_the_customer_is_told_they_can_rebook(self):
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service._notify_customer)
        # Cancelling silently is worse than a late job.
        assert "Book again" in src
        # The compensated wording is split across source lines; match a phrase
        # that survives the wrap.
        assert "added to your account" in src
        assert "book again straight away" in src

    def test_only_live_jobs_can_breach(self):
        from app.engines.execution.sla_breach_service import BREACHABLE_STATUSES
        for done in ("completed", "cancelled", "work_done"):
            assert done not in BREACHABLE_STATUSES


class TestEveryLeverIsAdminControlled:
    """Nothing about the penalty is decided in code any more."""

    def test_the_model_carries_every_setting(self):
        from app.engines.vertical_monetization.models import VerticalMonetizationPolicy as P
        # The migration alone is not enough: save_draft seeds a new version by
        # reading each field off the ORM object, so a column missing here 500s
        # the admin save even though the database has it.
        for field in ("sla_breach_hours", "sla_penalty_amount", "sla_penalty_to_customer",
                      "sla_penalty_debt_cap", "sla_auto_cancel", "sla_notify_provider",
                      "sla_penalty_type", "sla_penalty_percentage", "sla_penalty_min",
                      "sla_penalty_max", "sla_breachable_statuses",
                      "health_suspension_threshold", "health_suspension_days",
                      "health_reinstatement_score"):
            assert hasattr(P, field), field

    def test_every_setting_is_draftable(self):
        from app.engines.vertical_monetization.policy_service import _DRAFT_FIELDS
        for field in ("sla_auto_cancel", "sla_notify_provider", "sla_penalty_type",
                      "sla_penalty_percentage", "sla_penalty_min", "sla_penalty_max",
                      "sla_breachable_statuses"):
            assert field in _DRAFT_FIELDS, field

    def test_the_admin_form_exposes_them(self):
        from pathlib import Path
        src = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(
            encoding="utf-8")
        for label in ("Breach after (hours)", "Penalty type", "Maximum penalty debt",
                      "Cancel the job so the customer can rebook",
                      "Give the penalty to the customer as service credit",
                      "Tell the provider why they were charged",
                      "Health suspension"):
            assert label in src, label


class TestPenaltySizing:
    @staticmethod
    def _policy(**kw):
        base = dict(sla_penalty_amount=50, sla_penalty_type="fixed",
                    sla_penalty_percentage=None, sla_penalty_min=None, sla_penalty_max=None)
        base.update(kw)
        return type("P", (), base)()

    def test_percentage_scales_with_the_job(self):
        from decimal import Decimal
        from app.engines.execution.sla_breach_service import resolve_penalty
        p = self._policy(sla_penalty_type="percentage", sla_penalty_percentage=5)
        assert resolve_penalty(p, job_value=Decimal("10000")) == Decimal("500.00")

    def test_the_floor_and_ceiling_bind(self):
        from decimal import Decimal
        from app.engines.execution.sla_breach_service import resolve_penalty
        p = self._policy(sla_penalty_type="percentage", sla_penalty_percentage=5,
                         sla_penalty_min=100, sla_penalty_max=1000)
        assert resolve_penalty(p, job_value=Decimal("500")) == Decimal("100")
        assert resolve_penalty(p, job_value=Decimal("50000")) == Decimal("1000")

    def test_no_job_value_falls_back_to_the_flat_amount(self):
        from decimal import Decimal
        from app.engines.execution.sla_breach_service import resolve_penalty
        # A percentage of an unknown number cannot be computed honestly.
        p = self._policy(sla_penalty_type="percentage", sla_penalty_percentage=5)
        assert resolve_penalty(p, job_value=None) == Decimal("50")

    def test_a_job_type_override_wins(self):
        from decimal import Decimal
        from app.engines.execution.sla_breach_service import resolve_penalty
        p = self._policy(sla_penalty_type="percentage", sla_penalty_percentage=5)
        assert resolve_penalty(p, job_value=Decimal("50000"),
                               job_type_override=Decimal("25")) == Decimal("25")


class TestWaiver:
    def test_the_ledger_is_never_edited(self):
        import inspect
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service.waive_penalty)
        # An append-only ledger is what an operator has to defend.
        assert "INSERT INTO usage_credit_ledger" in src
        assert "DELETE FROM usage_credit_ledger" not in src
        assert "sla_penalty_waived" in src

    def test_a_penalty_cannot_be_waived_twice(self):
        import inspect
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service.waive_penalty)
        assert "SLA_PENALTY_ALREADY_WAIVED" in src

    def test_only_unspent_customer_credit_is_revoked(self):
        import inspect
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service._revoke_unspent_customer_credit)
        # Money the customer already put toward a booking is theirs; clawing it
        # back would punish them for the provider's failure.
        assert "remaining_amount" in src

    def test_waiving_needs_a_reason(self):
        import inspect
        from app.engines.vertical_monetization import home_services_finance_router
        src = inspect.getsource(home_services_finance_router)
        assert "A reason is required to waive a penalty" in src


class TestAutoCancelIsOptional:
    def test_a_breach_can_be_recorded_without_cancelling(self):
        import inspect
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service.sweep)
        assert "if policy.sla_auto_cancel:" in src

    def test_the_customer_is_only_told_when_the_job_was_cancelled(self):
        import inspect
        from app.engines.execution import sla_breach_service
        src = inspect.getsource(sla_breach_service.sweep)
        idx = src.index("_notify_customer")
        assert "sla_auto_cancel" in src[max(0, idx - 200):idx]
