"""Customer health is based on reconciled payments and private behavior only."""
import pytest
from pydantic import ValidationError

from app.engines.execution.mobile_customer_assessment_router import CustomerAssessmentBody
from app.engines.platform_commerce.constants import CUSTOMER_SIGNAL_WEIGHTS
from app.engines.platform_commerce.service import customer_behavior_score, customer_payment_score


def test_only_payment_and_behavior_are_weighted():
    assert CUSTOMER_SIGNAL_WEIGHTS == {"payment_reliability": 0.8, "customer_behavior": 0.2}


def test_unconfirmed_provider_claim_is_not_a_paid_or_unpaid_signal():
    assert customer_payment_score(0, 0) == 80.0
    assert customer_payment_score(1, 0) > 80.0
    assert customer_payment_score(0, 1) < 80.0


def test_single_subjective_report_cannot_block_customer():
    behavior = customer_behavior_score({"unsafe": 1})
    score = customer_payment_score(0, 0) * 0.8 + behavior * 0.2
    assert score >= 70


def test_staff_cannot_write_payment_status_in_assessment():
    with pytest.raises(ValidationError):
        CustomerAssessmentBody.model_validate({"behavior_code": "respectful", "payment_status": "unpaid"})


def test_assessment_vocabulary_is_closed():
    with pytest.raises(ValidationError):
        CustomerAssessmentBody.model_validate({"behavior_code": "customer_did_not_pay"})
