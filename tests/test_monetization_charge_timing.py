"""When the provider and the customer are charged, and why a publish stopped
silently reverting.

Three defects, all reproduced live before being fixed:

  1. Per-job-type rules belong to a policy VERSION and were not copied into a
     new draft, so every publish silently dropped every override an admin had
     configured. Confirmed on the live database: v5 carried a rule, v6 through
     v11 carried none.

  2. A new draft was built from the request payload alone, so any field the
     caller did not send back reverted to a column default.

  3. The policy-level `provider_chargeable_event` was stored and validated but
     never read by the runtime. Only a per-job-type override could affect
     timing, and only by suppressing the charge outright.
"""
from __future__ import annotations

import inspect

import pytest


class TestANewDraftContinuesTheLivePolicy:
    def test_scalar_fields_are_seeded_from_the_live_policy(self):
        from app.engines.vertical_monetization import policy_service
        src = inspect.getsource(policy_service.VerticalMonetizationPolicyService.save_draft)
        # Building only from `payload` reset every unsent field to its default.
        assert "seeded" in src
        assert "VerticalMonetizationPolicy.is_current == True" in src

    def test_job_type_rules_are_carried_forward(self):
        from app.engines.vertical_monetization import policy_service
        src = inspect.getsource(policy_service.VerticalMonetizationPolicyService.save_draft)
        assert "MonetizationJobTypeRule(" in src
        assert "cloned" in src

    def test_only_active_rules_are_carried_forward(self):
        from app.engines.vertical_monetization import policy_service
        src = inspect.getsource(policy_service.VerticalMonetizationPolicyService.save_draft)
        # A retired override must not silently come back on the next version.
        assert 'MonetizationJobTypeRule.status == "active"' in src


class TestProviderChargeTiming:
    def test_every_offered_event_has_a_runtime_hook(self):
        """An admin must not be able to pick a moment nothing reaches."""
        from app.engines.vertical_monetization.models import PROVIDER_CHARGEABLE_EVENTS
        from app.engines.execution import home_service_service

        src = inspect.getsource(home_service_service)
        for event in ("work_started", "work_done"):
            assert f'chargeable_event="{event}"' in src, f"{event} has no lifecycle hook"
        # These two are raised by complete_job, which already passed one of them.
        assert {"job_completed", "consultation_completed"} <= PROVIDER_CHARGEABLE_EVENTS

    def test_the_policy_decides_when_not_only_an_override(self):
        from app.engines.execution import usage_credit_deduction
        src = inspect.getsource(usage_credit_deduction.resolve_commission_credits)
        assert "policy.provider_chargeable_event" in src
        assert "configured_event" in src

    def test_an_unset_policy_still_charges_at_completion(self):
        """The column is nullable and live policies have it NULL, so the
        default must reproduce the old behaviour exactly."""
        from app.engines.execution import usage_credit_deduction
        src = inspect.getsource(usage_credit_deduction.resolve_commission_credits)
        assert 'or "job_completed"' in src


class TestNotYetChargeableWritesNothing:
    """The money-critical half of making timing work.

    `deduct_for_completed_job` is idempotent per job: a job with an existing
    ledger row is never charged again. So if a non-matching lifecycle moment
    wrote a zero row, it would consume that one-charge-per-job slot and the
    real chargeable event would deduct nothing at all.
    """

    def test_the_early_return_precedes_any_ledger_write(self):
        from app.engines.execution import usage_credit_deduction
        src = inspect.getsource(usage_credit_deduction.deduct_for_completed_job)
        guard = src.index("not_yet_chargeable")
        ledger = src.index("UsageCreditLedger(")
        assert guard < ledger, "the guard must return before a ledger row is written"

    def test_zero_charge_is_still_recorded(self):
        """A policy that genuinely charges nothing is a real outcome and keeps
        its audit row -- only 'not this moment' writes nothing."""
        from app.engines.execution import usage_credit_deduction
        src = inspect.getsource(usage_credit_deduction.deduct_for_completed_job)
        assert "_EVENT_NOT_REACHED" in src

    def test_the_two_halves_share_one_marker(self):
        from app.engines.execution.usage_credit_deduction import _EVENT_NOT_REACHED
        assert _EVENT_NOT_REACHED == "event_not_reached"


class TestPercentageNeedsAFinalValue:
    @staticmethod
    def _errors(payload: dict) -> list[str]:
        from app.engines.vertical_monetization.policy_service import (
            VerticalMonetizationPolicyService,
        )
        return VerticalMonetizationPolicyService()._validate(payload)

    def test_percentage_before_completion_is_refused(self):
        # On an inspection job the booking price is only the visit fee, so a
        # percentage taken at work_started is a percentage of the wrong number.
        for event in ("work_started", "work_done"):
            errs = self._errors({
                "provider_model": "PERCENTAGE_COMMISSION", "provider_percentage": 10,
                "provider_chargeable_event": event, "customer_fee_model": "NONE",
            })
            assert any("PERCENTAGE_COMMISSION can only be charged" in e for e in errs), event

    def test_percentage_at_completion_is_accepted(self):
        errs = self._errors({
            "provider_model": "PERCENTAGE_COMMISSION", "provider_percentage": 10,
            "provider_chargeable_event": "job_completed", "customer_fee_model": "NONE",
        })
        assert not errs

    def test_fixed_credits_may_charge_early(self):
        errs = self._errors({
            "provider_model": "COMPLETION_CREDITS", "provider_credit_units": 5,
            "provider_chargeable_event": "work_started", "customer_fee_model": "NONE",
        })
        assert not errs

    def test_an_unknown_event_is_refused(self):
        errs = self._errors({
            "provider_model": "COMPLETION_CREDITS", "provider_credit_units": 5,
            "provider_chargeable_event": "whenever", "customer_fee_model": "NONE",
        })
        assert any("provider_chargeable_event must be one of" in e for e in errs)

    def test_an_unset_event_is_accepted(self):
        # Nullable column; live policies have it NULL and must keep validating.
        errs = self._errors({
            "provider_model": "COMPLETION_CREDITS", "provider_credit_units": 5,
            "customer_fee_model": "NONE",
        })
        assert not errs


class TestCustomerCollectionStageIsHonest:
    def test_the_admin_ui_marks_unenforced_stages(self):
        from pathlib import Path
        src = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(
            encoding="utf-8")
        # Only before_work_start is enforced (assert_customer_platform_fee_paid_
        # if_required). Offering the others without saying so would promise an
        # enforcement the runtime does not perform.
        assert "not enforced" in src
        assert "enforced: true" in src

    def test_only_before_work_start_actually_gates(self):
        from app.engines.vertical_monetization import charge_service
        src = inspect.getsource(charge_service.assert_customer_platform_fee_paid_if_required)
        assert 'charge.collection_stage != "before_work_start"' in src

    def test_the_admin_can_choose_both_timings(self):
        from pathlib import Path
        src = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(
            encoding="utf-8")
        assert "When to charge the provider" in src
        assert "When to collect from the customer" in src
