from __future__ import annotations

import inspect
from decimal import Decimal

import pytest


def test_arrival_distance_is_zero_for_same_point():
    from app.engines.execution.arrival_verification import distance_meters
    assert distance_meters(30.7046, 76.7179, 30.7046, 76.7179) == 0


def test_arrival_distance_detects_remote_location():
    from app.engines.execution.arrival_verification import distance_meters
    assert distance_meters(30.7046, 76.7179, 28.6139, 77.2090) > 200_000


def test_daily_penalty_has_job_and_day_idempotency():
    from app.engines.execution.sla_breach_service import _charge_penalty
    source = inspect.getsource(_charge_penalty)
    assert 'f"{source}:{job_id}:day:{day_number}"' in source
    assert "idempotency_key" in source


def test_sweep_charges_multiple_days_and_closes_only_final_day():
    from app.engines.execution.sla_breach_service import sweep
    source = inspect.getsource(sweep)
    assert "sla_penalty_day_count" in source
    assert "interval '1 day'" in source
    assert "if final_day:" in source
    assert "_close_breached_job" in source


def test_old_jobs_are_not_retroactively_enrolled():
    from pathlib import Path
    migration = Path("alembic/versions/355_daily_sla_and_verified_arrival.py").read_text("utf-8")
    assert "not backfilled" in migration
    assert "UPDATE service_jobs SET sla_enforcement_started_at" not in migration
    assert "provider_chargeable_event = 'job_completed'" in migration
    assert "credit_booking_floor = 500" in migration
    assert "job_types jt" in migration
    assert "job_type_definitions" not in migration


def test_matching_checks_live_credit_not_only_visibility_cache():
    from app.engines.home_service_booking import matching_engine
    source = inspect.getsource(matching_engine._passes_full_eligibility_gate)
    assert "get_credit_state" in source
    assert 'credit_state["below_floor"]' in source


def test_all_new_operational_rules_are_versioned_admin_policy_fields():
    from app.engines.vertical_monetization import policy_service

    expected = {
        "sla_penalty_max_days",
        "assignment_timeout_enabled",
        "assignment_timeout_minutes",
        "customer_reschedule_limit",
        "arrival_verification_enabled",
        "arrival_radius_meters",
        "arrival_location_max_age_seconds",
        "arrival_max_accuracy_meters",
        "false_arrival_auto_close",
        "false_arrival_penalty_amount",
        "false_arrival_health_weight",
        "customer_photo_retention_days",
        "completion_proof_retention_days",
        "credit_reminder_hours_low",
        "credit_reminder_hours_blocked",
        "credit_reminder_hours_arrears",
    }
    assert expected <= policy_service._DRAFT_FIELDS


def test_admin_policy_editor_exposes_operational_controls():
    from pathlib import Path

    page = Path(
        "frontend/super-admin/app/admin/home-services/finance/page.tsx"
    ).read_text("utf-8")
    for label in (
        "Assignment &amp; customer rescheduling",
        "Assignment timeout (minutes)",
        "Maximum customer reschedules",
        "Verified technician arrival",
        "Allowed radius (metres)",
        "False-arrival penalty",
        "Statuses that can breach",
        "Retention &amp; credit reminders",
        "Fixed provider deduction",
    ):
        assert label in page


def test_runtime_flows_read_published_operational_policy():
    from app.engines.execution import arrival_verification
    from app.engines.home_service_assignment import service as assignment_service
    from app.jobs import provider_assignment_timeout

    assert "get_home_services_operations_policy" in inspect.getsource(
        provider_assignment_timeout.sweep
    )
    assert "get_home_services_operations_policy" in inspect.getsource(
        arrival_verification.verify_arrival
    )
    assignment_source = inspect.getsource(
        assignment_service.HomeServiceJobAssignmentService
    )
    assert assignment_source.count("get_home_services_operations_policy") >= 2


def test_policy_clone_preserves_job_type_sla_overrides():
    from app.engines.vertical_monetization import policy_service

    source = inspect.getsource(
        policy_service.VerticalMonetizationPolicyService.save_draft
    )
    assert "sla_penalty_enabled=r.sla_penalty_enabled" in source
    assert "sla_penalty_amount=r.sla_penalty_amount" in source


def test_operational_policy_validation_rejects_unsafe_values():
    from app.engines.vertical_monetization.policy_service import (
        VerticalMonetizationPolicyService,
    )

    service = VerticalMonetizationPolicyService()
    errors = service._validate({
        "provider_model": "NONE",
        "customer_fee_model": "NONE",
        "assignment_timeout_minutes": 0,
        "customer_reschedule_limit": 21,
        "arrival_radius_meters": 24,
        "arrival_location_max_age_seconds": 12.5,
        "arrival_max_accuracy_meters": 1001,
        "false_arrival_penalty_amount": -1,
        "false_arrival_health_weight": 21,
        "assignment_timeout_enabled": "false",
    })
    assert "assignment_timeout_minutes must be between 1 and 1440" in errors
    assert "customer_reschedule_limit must be between 0 and 20" in errors
    assert "arrival_radius_meters must be between 25 and 5000" in errors
    assert "arrival_location_max_age_seconds must be a whole number" in errors
    assert "arrival_max_accuracy_meters must be between 5 and 1000" in errors
    assert "false_arrival_penalty_amount must be at least 0" in errors
    assert "false_arrival_health_weight must be at most 20" in errors
    assert "assignment_timeout_enabled must be true or false" in errors


@pytest.mark.asyncio
async def test_runtime_reader_uses_published_values_including_disabled_and_zero():
    from app.engines.vertical_monetization.runtime_operations import (
        get_home_services_operations_policy,
    )

    class Result:
        def mappings(self):
            return self

        def first(self):
            return {
                "assignment_timeout_enabled": False,
                "assignment_timeout_minutes": 45,
                "customer_reschedule_limit": 0,
                "arrival_verification_enabled": False,
                "arrival_radius_meters": 350,
                "arrival_location_max_age_seconds": 180,
                "arrival_max_accuracy_meters": 75,
                "false_arrival_auto_close": False,
                "false_arrival_penalty_amount": Decimal("80.00"),
                "false_arrival_health_weight": Decimal("1.50"),
            }

    class Db:
        async def execute(self, statement):
            assert "p.status='published'" in str(statement)
            assert "v.key='home_services'" in str(statement)
            return Result()

    policy = await get_home_services_operations_policy(Db())
    assert policy.assignment_timeout_enabled is False
    assert policy.assignment_timeout_minutes == 45
    assert policy.customer_reschedule_limit == 0
    assert policy.arrival_verification_enabled is False
    assert policy.arrival_radius_meters == 350
    assert policy.false_arrival_auto_close is False
    assert policy.false_arrival_penalty_amount == Decimal("80.00")
    assert policy.false_arrival_health_weight == Decimal("1.50")
