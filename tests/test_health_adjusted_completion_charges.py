"""Health-adjusted provider completion charge safety and audit rules."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.engines.execution.usage_credit_deduction import _resolve_commission_charge
from app.engines.trust_quality.provider_health import get_provider_health_snapshot
from app.engines.vertical_monetization.calculation_service import calculate_provider_completion_credits
from app.engines.vertical_monetization.policy_service import VerticalMonetizationPolicyService


def _policy(**overrides):
    data = {
        "provider_model": "PERCENTAGE_COMMISSION",
        "provider_percentage": Decimal("10"),
        "provider_min_charge_minor": None,
        "provider_max_charge_minor": None,
        "provider_credit_units": None,
        "provider_fixed_amount_minor": None,
        "provider_health_max_effective_percentage": Decimal("25"),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_health_points_increase_percentage_commission_and_are_explained():
    result = calculate_provider_completion_credits(
        policy=_policy(), service_amount=Decimal("1000"),
        health_adjustment_percentage_points=Decimal("5"),
    )
    assert result["provider_charge_credit_units"] == "150.00"
    assert result["provider_charge_breakdown"]["base_percentage"] == "10"
    assert result["provider_charge_breakdown"]["percentage"] == "15"
    assert result["provider_charge_breakdown"]["health_adjustment_percentage_points"] == "5"


def test_health_adjustment_never_exceeds_admin_cap():
    result = calculate_provider_completion_credits(
        policy=_policy(provider_health_max_effective_percentage=Decimal("12")),
        service_amount=Decimal("1000"),
        health_adjustment_percentage_points=Decimal("10"),
    )
    assert result["provider_charge_credit_units"] == "120.00"
    assert result["provider_charge_breakdown"]["percentage"] == "12"
    assert result["provider_charge_breakdown"]["health_adjustment_percentage_points"] == "2"


def test_disabled_or_zero_adjustment_never_reduces_existing_base_rate():
    result = calculate_provider_completion_credits(
        policy=_policy(
            provider_percentage=Decimal("30"),
            provider_health_max_effective_percentage=Decimal("25"),
        ),
        service_amount=Decimal("1000"),
    )
    assert result["provider_charge_credit_units"] == "300.00"
    assert result["provider_charge_breakdown"]["percentage"] == "30"


def test_health_adjustment_policy_is_safe_to_publish():
    payload = {
        "provider_model": "PERCENTAGE_COMMISSION",
        "provider_percentage": "10",
        "provider_health_adjustment_enabled": True,
        "provider_health_adjustments_json": {"gold": 0, "watchlist": 5, "at_risk": 8},
        "provider_health_score_max_age_days": 30,
        "provider_health_max_effective_percentage": "25",
        "customer_fee_model": "NONE",
        "collection_stage": "after_estimate_approval",
    }
    assert VerticalMonetizationPolicyService().validate(payload)["valid"] is True


def test_health_adjustment_rejects_negative_or_non_percentage_configuration():
    svc = VerticalMonetizationPolicyService()
    payload = {
        "provider_model": "COMPLETION_CREDITS",
        "provider_credit_units": 50,
        "provider_health_adjustment_enabled": True,
        "provider_health_adjustments_json": {"watchlist": -2},
        "customer_fee_model": "NONE",
        "collection_stage": "after_estimate_approval",
    }
    errors = svc.validate(payload)["errors"]
    assert any("only be enabled for PERCENTAGE_COMMISSION" in error for error in errors)
    assert any("between 0 and 50" in error for error in errors)


def test_health_adjustment_rejects_non_finite_numbers():
    errors = VerticalMonetizationPolicyService().validate({
        "provider_model": "PERCENTAGE_COMMISSION",
        "provider_percentage": "10",
        "provider_health_adjustment_enabled": True,
        "provider_health_adjustments_json": {"watchlist": "NaN"},
        "provider_health_max_effective_percentage": "Infinity",
        "customer_fee_model": "NONE",
        "collection_stage": "after_estimate_approval",
    })["errors"]
    assert any("watchlist must be a finite number" in error for error in errors)
    assert any("provider_health_max_effective_percentage must be a finite number" in error for error in errors)


@pytest.mark.asyncio
async def test_stale_health_is_unassessed_and_never_penalised():
    row = SimpleNamespace(
        health_score_id=uuid.uuid4(), formula_id=uuid.uuid4(),
        formula_key="provider_business_health_default", formula_version=2,
        score=35, band_key="at_risk",
        calculated_at=datetime.now(timezone.utc) - timedelta(days=31),
        health_band_rule_id=uuid.uuid4(), bookable_allowed=False,
    )
    result = MagicMock(); result.first.return_value = row
    db = MagicMock(); db.execute = AsyncMock(return_value=result)
    snapshot = await get_provider_health_snapshot(db, uuid.uuid4(), max_age_days=30)
    assert snapshot["source"] == "unassessed_default"
    assert snapshot["reason"] == "stale_health_score"
    assert snapshot["band_key"] is None


@pytest.mark.asyncio
async def test_runtime_uses_fresh_band_and_returns_auditable_snapshot():
    policy = _policy(
        id=uuid.uuid4(), version_number=7,
        provider_chargeable_event="job_completed",
        provider_health_adjustment_enabled=True,
        provider_health_adjustments_json={"watchlist": 5},
        provider_health_score_max_age_days=30,
    )
    vertical = SimpleNamespace(id=uuid.uuid4())
    health_row = SimpleNamespace(
        health_score_id=uuid.uuid4(), formula_id=uuid.uuid4(),
        formula_key="provider_business_health_default", formula_version=3,
        score=55, band_key="watchlist", calculated_at=datetime.now(timezone.utc),
        health_band_rule_id=uuid.uuid4(), bookable_allowed=True,
    )
    vertical_result = MagicMock(); vertical_result.scalar_one_or_none.return_value = vertical
    policy_result = MagicMock(); policy_result.scalar_one_or_none.return_value = policy
    health_result = MagicMock(); health_result.first.return_value = health_row
    db = MagicMock(); db.execute = AsyncMock(side_effect=[vertical_result, policy_result, health_result])

    credits, source, snapshot = await _resolve_commission_charge(
        db, tenant_id=uuid.uuid4(), job_price=Decimal("1000"),
        category_id=uuid.uuid4(), master_service_id=uuid.uuid4(),
        offering_type_id=None, brand_id=None,
    )
    assert credits == Decimal("150.00")
    assert source == f"monetization_policy:{policy.id}"
    assert snapshot["provider_health"]["band_key"] == "watchlist"
    assert snapshot["provider_health"]["adjustment_percentage_points"] == "5"
    assert snapshot["calculation"]["base_percentage"] == "10"
    assert snapshot["calculation"]["percentage"] == "15"
