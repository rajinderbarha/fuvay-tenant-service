from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.engines.home_service_assignment.service import (
    CustomerCancellationBlocked,
    HomeServiceJobAssignmentService,
)
from app.engines.vertical_monetization.policy_service import VerticalMonetizationPolicyService
from app.engines.vertical_monetization.runtime_operations import (
    DEFAULT_CUSTOMER_CANCELLATION_REASONS,
    HomeServicesOperationsPolicy,
)


def _job(*, status="scheduled"):
    return SimpleNamespace(
        status=status,
        scheduled_date=date(2026, 10, 10),
        scheduled_time_window="14:00-16:00",
    )


def test_customer_cancellation_is_allowed_before_admin_cutoff():
    policy = HomeServicesOperationsPolicy(customer_cancellation_cutoff_minutes=120)
    # 11:59 IST; cancellation closes at 12:00 IST for a 14:00 visit.
    now = datetime(2026, 10, 10, 6, 29, tzinfo=timezone.utc)
    with patch("app.engines.home_service_assignment.service._utcnow", return_value=now):
        decision = HomeServiceJobAssignmentService._customer_cancellation_decision(
            _job(), None, policy,
        )
    assert decision["can_cancel"] is True
    assert decision["cancel_block_message"] is None
    assert decision["cancellation_deadline_at"].endswith("+05:30")


def test_customer_cancellation_is_blocked_at_cutoff_with_exact_reason():
    policy = HomeServicesOperationsPolicy(customer_cancellation_cutoff_minutes=120)
    # 12:01 IST; the configured cutoff has passed.
    now = datetime(2026, 10, 10, 6, 31, tzinfo=timezone.utc)
    with patch("app.engines.home_service_assignment.service._utcnow", return_value=now):
        decision = HomeServiceJobAssignmentService._customer_cancellation_decision(
            _job(), None, policy,
        )
    assert decision["can_cancel"] is False
    assert decision["cancel_block_reason"] == "customer_cancellation_cutoff_passed"
    assert "10 Oct 2026, 12:00 PM IST" in decision["cancel_block_message"]
    assert "120 minutes before" in decision["cancel_block_message"]


def test_customer_cancellation_stage_lock_cannot_be_bypassed_by_zero_cutoff():
    policy = HomeServicesOperationsPolicy(customer_cancellation_cutoff_minutes=0)
    decision = HomeServiceJobAssignmentService._customer_cancellation_decision(
        _job(status="on_the_way"), None, policy,
    )
    assert decision["can_cancel"] is False
    assert decision["cancel_block_reason"] == "booking_not_in_cancellable_state"
    assert "technician has already started" in decision["cancel_block_message"]


def test_only_active_admin_reasons_are_exposed():
    reasons = [dict(DEFAULT_CUSTOMER_CANCELLATION_REASONS[0]), {
        "code": "retired", "label": "Retired", "active": False,
        "requires_detail": False,
    }]
    policy = HomeServicesOperationsPolicy(
        customer_cancellation_cutoff_minutes=0,
        customer_cancellation_reasons=reasons,
    )
    now = datetime(2026, 10, 10, 5, 0, tzinfo=timezone.utc)
    with patch("app.engines.home_service_assignment.service._utcnow", return_value=now):
        decision = HomeServiceJobAssignmentService._customer_cancellation_decision(
            _job(), None, policy,
        )
    assert [row["code"] for row in decision["cancellation_reason_options"]] == [
        "changed_mind"
    ]


def test_admin_policy_validates_customer_cancellation_controls():
    service = VerticalMonetizationPolicyService()
    errors = service._validate({
        "customer_cancellation_enabled": "yes",
        "customer_cancellation_cutoff_minutes": 10081,
        "customer_cancellation_reasons": [
            {"code": "duplicate", "label": "First", "active": False, "requires_detail": False},
            {"code": "duplicate", "label": "Second", "active": False, "requires_detail": False},
        ],
    })
    assert "customer_cancellation_enabled must be true or false" in errors
    assert "customer_cancellation_cutoff_minutes must be between 0 and 10080" in errors
    assert "Duplicate customer cancellation reason code: duplicate" in errors
    assert "At least one customer cancellation reason must be active" in errors


def test_customer_api_receives_the_safe_policy_denial_message():
    from app.engines.home_service_assignment.customer_router import _cancel_reschedule_error
    from app.exceptions import ServiceOSException

    message = "Cancellation closed at 10 Oct 2026, 12:00 PM IST."
    with pytest.raises(ServiceOSException) as caught:
        _cancel_reschedule_error(CustomerCancellationBlocked(message))
    assert caught.value.status_code == 409
    assert caught.value.detail == message


@pytest.mark.asyncio
async def test_instagram_surfaces_server_block_reason_and_admin_reason_label():
    from app.engines.messaging_gateway import flow

    class Thread:
        id = "thread-1"
        channel = "instagram"
        customer_id = "customer-1"

    class BlockedIdentity:
        async def cancel_options(self, thread, booking_number):
            return {
                "can_cancel": False,
                "block_message": (
                    "Cancellation closed at 10 Oct 2026, 12:00 PM IST, "
                    "120 minutes before the visit."
                ),
                "reasons": [],
            }

        async def live_bookings(self, thread):
            return [{"number": "BK-1", "service": "AC repair", "status": "Scheduled"}]

    blocked = await flow._cancel_step(
        Thread(), BlockedIdentity(), "BK-1", "instagram",
    )
    assert "12:00 PM IST" in blocked.text
    assert all(not row["id"].startswith("cx|") for row in blocked.picker["rows"])

    class AllowedIdentity(BlockedIdentity):
        async def cancel_options(self, thread, booking_number):
            return {
                "can_cancel": True,
                "reasons": ["schedule_conflict"],
                "reason_options": [{
                    "code": "schedule_conflict",
                    "label": "My timing changed",
                    "active": True,
                    "requires_detail": False,
                }],
            }

    allowed = await flow._cancel_step(
        Thread(), AllowedIdentity(), "BK-1", "instagram",
    )
    assert allowed.picker["rows"][0]["title"] == "My timing changed"
