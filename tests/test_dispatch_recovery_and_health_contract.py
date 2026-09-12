"""Focused regression coverage for provider dispatch recovery and trust signals."""

import inspect

import pytest
from pydantic import ValidationError

from app.engines.execution.admin_job_actions import AdminJobActionsService
from app.engines.final_records.bookings_jobs_stage_mapping import compute_available_actions
from app.engines.home_service_booking.matching_engine import select_best_provider
from app.engines.platform_commerce.constants import CUSTOMER_SIGNAL_WEIGHTS
from app.engines.serviceability.schemas import AddressCreate
from app.jobs.provider_assignment_timeout import ELIGIBLE_STATUSES, TIMEOUT_MINUTES


def test_cancelled_and_failed_jobs_can_be_reopened_for_dispatch():
    service = AdminJobActionsService(None)

    assert service.get_allowed_override_targets("cancelled") == ["pending_assignment"]
    assert service.get_allowed_override_targets("failed") == ["pending_assignment"]
    assert service.get_allowed_override_targets("completed") == []


def test_provider_can_cancel_any_non_terminal_job():
    actions = compute_available_actions(
        "accepted", assignment_status="accepted", has_assignee=True,
    )

    assert "cancel_job" in {action["action_key"] for action in actions}
    assert compute_available_actions("cancelled", "cancelled", has_assignee=False) == []


def test_provider_timeout_contract_is_fifteen_minutes_and_excludes_attempts():
    assert TIMEOUT_MINUTES == 15
    assert set(ELIGIBLE_STATUSES) == {"pending_assignment", "accepted"}
    assert "exclude_tenant_ids" in inspect.signature(select_best_provider).parameters


def test_customer_health_is_driven_mostly_by_payment_reliability():
    assert sum(CUSTOMER_SIGNAL_WEIGHTS.values()) == pytest.approx(1.0)
    assert CUSTOMER_SIGNAL_WEIGHTS["payment_reliability"] > 0.5
    assert CUSTOMER_SIGNAL_WEIGHTS["payment_reliability"] == max(
        CUSTOMER_SIGNAL_WEIGHTS.values()
    )


def test_address_requires_a_structured_non_placeholder_line():
    valid = AddressCreate(
        address_line_1="Flat 12, Sunrise Apartments, Model Town",
        city="Ludhiana", state="Punjab", zipcode="141002",
    )
    assert valid.address_line_1 == "Flat 12, Sunrise Apartments, Model Town"

    with pytest.raises(ValidationError):
        AddressCreate(
            address_line_1="aaaa aaaa", city="Ludhiana",
            state="Punjab", zipcode="141002",
        )
