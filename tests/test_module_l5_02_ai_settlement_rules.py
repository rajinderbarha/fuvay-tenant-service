"""MODULE-L5-02 — AI settlement business rules.

  * AI settlement is not started by hand: it takes over once the PROVIDER has
    failed to solve the complaint.
  * Starting it charges the PROVIDER a fee (20 credits).
  * The AI may offer at most a capped share of the job value (default 25%).
  * A case strong enough to warrant MORE than the cap is NOT settled by the AI —
    it goes to admin manual review.
  * Compensation is CREDIT POINTS, never real money.
  * Those credits are funded from the PROVIDER's credit wallet, falling back to
    their security deposit.
  * The admin only sets the rule.
"""
import inspect
from decimal import Decimal

import pytest

from app.engines.complaints.constants import (
    AI_SETTLEMENT_DEFAULT_MAX_PCT, AI_SETTLEMENT_FEE_CREDITS, AI_ALLOWED_REMEDIES,
    MONETARY_REMEDIES, REMEDY_TO_SETTLEMENT_TYPE, SETTLEMENT_DEDUCTION_STRATEGY,
)
from app.engines.complaints.settlement_rules import DEFAULT_RULE, evaluate_proposal

JOB = Decimal("1000.00")   # cap = 250.00


def test_defaults_match_the_business_rule():
    assert AI_SETTLEMENT_DEFAULT_MAX_PCT == Decimal("25.00")
    assert AI_SETTLEMENT_FEE_CREDITS == Decimal("20.00")
    # provider credits first, then their security deposit
    assert SETTLEMENT_DEDUCTION_STRATEGY == "tenant_wallet_then_security_deposit"


def test_no_monetary_remedy_is_ever_permitted():
    """The platform never settles a dispute with real money."""
    assert not (set(AI_ALLOWED_REMEDIES) & MONETARY_REMEDIES)
    for money in ("refund", "partial_refund", "full_refund", "cash", "bank_transfer"):
        v = evaluate_proposal(DEFAULT_RULE, JOB, money, Decimal("10"))
        assert not v.allowed and v.escalate_to_admin, money


def test_offer_within_the_cap_is_settled_by_the_ai():
    v = evaluate_proposal(DEFAULT_RULE, JOB, "credit_points", Decimal("200"))
    assert v.allowed and not v.escalate_to_admin
    assert v.settlement_type == "customer_service_credit"   # credit points, not money


def test_offer_exactly_at_the_cap_is_allowed():
    assert evaluate_proposal(DEFAULT_RULE, JOB, "credit_points", Decimal("250")).allowed


def test_strong_case_over_the_cap_goes_to_admin_not_a_clamped_offer():
    """The whole point of the cap: a case that deserves more than 25% must be
    handed to a human, NOT quietly settled down at the cap."""
    v = evaluate_proposal(DEFAULT_RULE, JOB, "credit_points", Decimal("400"))
    assert not v.allowed
    assert v.escalate_to_admin
    assert "admin manual review" in v.reason


def test_remedy_outside_the_policy_is_refused():
    v = evaluate_proposal(DEFAULT_RULE, JOB, "free_holiday", Decimal("10"))
    assert not v.allowed and v.escalate_to_admin


def test_non_monetary_remedies_carry_no_amount():
    for remedy in ("rework", "callback", "apology", "no_action"):
        v = evaluate_proposal(DEFAULT_RULE, JOB, remedy, None)
        assert v.allowed, remedy
        assert REMEDY_TO_SETTLEMENT_TYPE[remedy] in ("tenant_revisit", "no_compensation")


def test_zero_value_job_permits_no_credit():
    """The AI cannot invent value out of nothing."""
    v = evaluate_proposal(DEFAULT_RULE, Decimal("0"), "credit_points", Decimal("10"))
    assert not v.allowed and v.escalate_to_admin


def test_admin_cannot_configure_money_back_in():
    """The admin sets the rule — but not their way around the no-money rule."""
    from app.engines.complaints.admin_router import PolicyIn
    PolicyIn(ai_settlement_allowed_remedies=["credit_points", "rework"])   # fine
    with pytest.raises(Exception):
        PolicyIn(ai_settlement_allowed_remedies=["credit_points", "refund"])


def test_provider_is_charged_for_the_ai_settlement():
    from app.engines.complaints import settlement_rules
    src = inspect.getsource(settlement_rules.charge_ai_settlement_fee)
    assert "AI_SETTLEMENT_FEE_CREDITS" in src
    assert "ai_settlement_fee" in src            # wallet txn reference
    assert "SETTLEMENT_DEDUCTION_STRATEGY" in src  # wallet -> deposit cascade


def test_payout_is_credits_funded_by_the_provider():
    from app.engines.complaints.complaint_service import ComplaintService
    src = inspect.getsource(ComplaintService._execute_settlement_payout)
    assert "MONETARY_REMEDIES" in src              # money can never leave this way
    assert "SETTLEMENT_DEDUCTION_STRATEGY" in src  # provider wallet -> deposit
    assert "execute_settlement" in src


def test_the_model_is_never_trusted():
    """Whatever the LLM returns is re-checked in code against the admin's rule."""
    from app.engines.complaints import ai_settlement_service
    src = inspect.getsource(ai_settlement_service.AISettlementService.analyze_and_propose)
    assert "evaluate_proposal" in src
    assert "verdict.allowed" in src
