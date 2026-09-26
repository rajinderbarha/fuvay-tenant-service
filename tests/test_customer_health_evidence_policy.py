"""Evidence-gated, admin-governed customer health contract."""
from pathlib import Path
import uuid

from app.engines.platform_commerce.service import (
    CommerceService,
    customer_behavior_score,
    customer_payment_score,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = (ROOT / "app/engines/settings_engine/registry.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "app/engines/platform_commerce/service.py").read_text(encoding="utf-8")


def test_no_evidence_is_presented_as_new_customer_without_a_score():
    result = CommerceService._new_customer_health(
        uuid.uuid4(), uuid.uuid4(),
        policy={
            "payment_weight_percentage": 80,
            "behavior_weight_percentage": 20,
            "minimum_evidence_events": 1,
        },
        evidence={
            "paid_payments": 0,
            "unpaid_payments": 0,
            "payment_outcomes": 0,
            "behavior_assessments": 0,
            "total_events": 0,
            "behavior_counts": {},
        },
    )
    assert result["assessment_status"] == "unassessed"
    assert result["display_label"] == "New customer"
    assert result["score"] is None
    assert result["band"] == "new_customer"
    assert result["signals"] == {}
    assert "behavior_counts" not in result["evidence"]


def test_scoring_helpers_use_configurable_neutral_prior():
    assert customer_payment_score(0, 0, 75) == 75
    assert customer_behavior_score({}, 75) == 75
    assert customer_payment_score(1, 0, 75) > 75
    assert customer_behavior_score({"unsafe": 1}, 75) < 75


def test_health_policy_is_governed_and_reads_real_evidence_only():
    for key in (
        "customer_health_payment_weight_percentage",
        "customer_health_minimum_evidence_events",
        "customer_health_neutral_prior_score",
    ):
        assert f'key="{key}"' in REGISTRY
    assert 'has_real_consumer=True' in REGISTRY
    assert "service_payment_records" in SERVICE
    assert "customer_behavior_assessments" in SERVICE
    assert "Opening Dispatch must never manufacture an earned score" in SERVICE
