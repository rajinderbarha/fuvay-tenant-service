"""Published Home Services operational policy used by background and job flows.

The admin edits these values through the versioned monetization policy.  This
small reader keeps fallbacks in one place for installations that do not yet
have a published Home Services policy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


DEFAULT_PROVIDER_CANCELLATION_REASONS = [
    {"code": "no_technician", "label": "No technician available", "outcome": "provider_cancel", "responsibility": "provider", "active": True, "requires_note": False, "minimum_call_attempts": 0, "health_impact": True},
    {"code": "cannot_meet_slot", "label": "Cannot meet the selected slot", "outcome": "provider_cancel", "responsibility": "provider", "active": True, "requires_note": False, "minimum_call_attempts": 0, "health_impact": True},
    {"code": "service_skill_unavailable", "label": "Service, brand or skill unavailable", "outcome": "provider_cancel", "responsibility": "provider", "active": True, "requires_note": True, "minimum_call_attempts": 0, "health_impact": True},
    {"code": "capacity_issue", "label": "Provider capacity or operational issue", "outcome": "provider_cancel", "responsibility": "provider", "active": True, "requires_note": True, "minimum_call_attempts": 0, "health_impact": True},
    {"code": "customer_requested", "label": "Customer requested cancellation", "outcome": "customer_confirmation", "responsibility": "customer", "active": True, "requires_note": False, "minimum_call_attempts": 1, "health_impact": False},
    {"code": "customer_unreachable", "label": "Customer unavailable or unreachable", "outcome": "customer_confirmation", "responsibility": "customer", "active": True, "requires_note": True, "minimum_call_attempts": 2, "health_impact": False},
    {"code": "address_access_issue", "label": "Incorrect or inaccessible address", "outcome": "customer_confirmation", "responsibility": "customer", "active": True, "requires_note": True, "minimum_call_attempts": 1, "health_impact": False},
    {"code": "safety_concern", "label": "Safety concern at the location", "outcome": "provider_cancel", "responsibility": "neutral", "active": True, "requires_note": True, "minimum_call_attempts": 0, "health_impact": False},
    {"code": "other", "label": "Other provider reason", "outcome": "provider_cancel", "responsibility": "provider", "active": True, "requires_note": True, "minimum_call_attempts": 0, "health_impact": True},
]

DEFAULT_CUSTOMER_CANCELLATION_REASONS = [
    {"code": "changed_mind", "label": "Changed my mind", "active": True, "requires_detail": False},
    {"code": "found_another_provider", "label": "Found another provider", "active": True, "requires_detail": False},
    {"code": "price_concern", "label": "Price concern", "active": True, "requires_detail": False},
    {"code": "schedule_conflict", "label": "Schedule conflict", "active": True, "requires_detail": False},
    {"code": "no_longer_needed", "label": "Service no longer needed", "active": True, "requires_detail": False},
    {"code": "provider_asked_to_cancel_or_pay_direct", "label": "Provider asked me to cancel or pay directly", "active": True, "requires_detail": True},
    {"code": "other", "label": "Another reason", "active": True, "requires_detail": True},
]


@dataclass(frozen=True)
class HomeServicesOperationsPolicy:
    assignment_timeout_enabled: bool = True
    assignment_timeout_minutes: int = 30
    urgent_assignment_timeout_minutes: int = 10
    urgent_assignment_threshold_minutes: int = 120
    assignment_auto_assign_enabled: bool = True
    customer_reschedule_limit: int = 3
    provider_reschedule_limit: int = 3
    customer_cancellation_enabled: bool = True
    customer_cancellation_cutoff_minutes: int = 120
    customer_cancellation_reasons: list[dict] = field(
        default_factory=lambda: [dict(reason) for reason in DEFAULT_CUSTOMER_CANCELLATION_REASONS]
    )
    provider_reschedule_approval_hours: int = 24
    provider_departure_warning_minutes: int = 15
    provider_cancellation_confirmation_minutes: int = 15
    provider_cancellation_min_note_length: int = 10
    provider_cancellation_reasons: list[dict] = field(
        default_factory=lambda: [dict(reason) for reason in DEFAULT_PROVIDER_CANCELLATION_REASONS]
    )
    arrival_verification_enabled: bool = False
    arrival_radius_meters: int = 250
    arrival_location_max_age_seconds: int = 120
    arrival_max_accuracy_meters: int = 100
    arrival_customer_confirmation_enabled: bool = True
    arrival_challenge_ttl_minutes: int = 10
    arrival_code_max_attempts: int = 5
    arrival_denial_limit: int = 2
    false_arrival_auto_close: bool = True
    false_arrival_penalty_amount: Decimal = Decimal("150.00")
    false_arrival_health_weight: Decimal = Decimal("3.00")
    job_stall_watchdog_enabled: bool = True
    job_stall_critical_multiplier: int = 2
    job_stall_limit_minutes: dict[str, int] = field(default_factory=lambda: {
        "reached_site": 45, "inspection_started": 120,
        "inspection_done": 120, "quote_required": 2880,
        "service_started": 480, "work_done": 1440,
        "customer_not_available": 240,
    })


async def get_home_services_operations_policy(
    db: AsyncSession,
) -> HomeServicesOperationsPolicy:
    row = (await db.execute(text(
        "SELECT p.assignment_timeout_enabled, p.assignment_timeout_minutes, "
        "p.urgent_assignment_timeout_minutes, p.urgent_assignment_threshold_minutes, "
        "p.assignment_auto_assign_enabled, "
        "p.customer_reschedule_limit, p.provider_reschedule_limit, "
        "p.customer_cancellation_enabled, "
        "p.customer_cancellation_cutoff_minutes, p.customer_cancellation_reasons, "
        "p.provider_reschedule_approval_hours, "
        "p.provider_departure_warning_minutes, "
        "p.provider_cancellation_confirmation_minutes, "
        "p.provider_cancellation_min_note_length, p.provider_cancellation_reasons, "
        "p.arrival_verification_enabled, "
        "p.arrival_radius_meters, p.arrival_location_max_age_seconds, "
        "p.arrival_max_accuracy_meters, "
        "p.arrival_customer_confirmation_enabled, "
        "p.arrival_challenge_ttl_minutes, p.arrival_code_max_attempts, "
        "p.arrival_denial_limit, p.false_arrival_auto_close, "
        "p.false_arrival_penalty_amount, p.false_arrival_health_weight, "
        "p.job_stall_watchdog_enabled, p.job_stall_critical_multiplier, "
        "p.job_stall_limit_minutes "
        "FROM vertical_monetization_policies p "
        "JOIN verticals v ON v.id=p.vertical_id "
        "WHERE v.key='home_services' AND p.status='published' "
        "AND p.is_current=true LIMIT 1"
    ))).mappings().first()
    if not row:
        return HomeServicesOperationsPolicy()
    defaults = HomeServicesOperationsPolicy()
    return HomeServicesOperationsPolicy(
        assignment_timeout_enabled=bool(row["assignment_timeout_enabled"]),
        assignment_timeout_minutes=int(
            row["assignment_timeout_minutes"] or defaults.assignment_timeout_minutes
        ),
        urgent_assignment_timeout_minutes=int(
            row.get("urgent_assignment_timeout_minutes") or defaults.urgent_assignment_timeout_minutes
        ),
        urgent_assignment_threshold_minutes=int(
            row.get("urgent_assignment_threshold_minutes") or defaults.urgent_assignment_threshold_minutes
        ),
        assignment_auto_assign_enabled=(
            bool(row["assignment_auto_assign_enabled"])
            if row.get("assignment_auto_assign_enabled") is not None else
            defaults.assignment_auto_assign_enabled
        ),
        customer_reschedule_limit=int(
            row["customer_reschedule_limit"]
            if row["customer_reschedule_limit"] is not None
            else defaults.customer_reschedule_limit
        ),
        provider_reschedule_limit=int(
            row.get("provider_reschedule_limit")
            if row.get("provider_reschedule_limit") is not None
            else defaults.provider_reschedule_limit
        ),
        customer_cancellation_enabled=(
            bool(row["customer_cancellation_enabled"])
            if row.get("customer_cancellation_enabled") is not None else
            defaults.customer_cancellation_enabled
        ),
        customer_cancellation_cutoff_minutes=int(
            row["customer_cancellation_cutoff_minutes"]
            if row.get("customer_cancellation_cutoff_minutes") is not None
            else defaults.customer_cancellation_cutoff_minutes
        ),
        customer_cancellation_reasons=list(
            row.get("customer_cancellation_reasons")
            or defaults.customer_cancellation_reasons
        ),
        arrival_verification_enabled=bool(row["arrival_verification_enabled"]),
        arrival_radius_meters=int(row["arrival_radius_meters"] or defaults.arrival_radius_meters),
        arrival_location_max_age_seconds=int(
            row["arrival_location_max_age_seconds"]
            or defaults.arrival_location_max_age_seconds
        ),
        arrival_max_accuracy_meters=int(
            row["arrival_max_accuracy_meters"] or defaults.arrival_max_accuracy_meters
        ),
        provider_reschedule_approval_hours=int(
            row.get("provider_reschedule_approval_hours")
            or defaults.provider_reschedule_approval_hours
        ),
        provider_departure_warning_minutes=int(
            row.get("provider_departure_warning_minutes")
            or defaults.provider_departure_warning_minutes
        ),
        provider_cancellation_confirmation_minutes=int(
            row.get("provider_cancellation_confirmation_minutes")
            or defaults.provider_cancellation_confirmation_minutes
        ),
        provider_cancellation_min_note_length=int(
            row.get("provider_cancellation_min_note_length")
            if row.get("provider_cancellation_min_note_length") is not None
            else defaults.provider_cancellation_min_note_length
        ),
        provider_cancellation_reasons=(
            list(row.get("provider_cancellation_reasons") or defaults.provider_cancellation_reasons)
        ),
        arrival_customer_confirmation_enabled=(
            bool(row["arrival_customer_confirmation_enabled"])
            if row.get("arrival_customer_confirmation_enabled") is not None else
            defaults.arrival_customer_confirmation_enabled
        ),
        arrival_challenge_ttl_minutes=int(
            row.get("arrival_challenge_ttl_minutes")
            or defaults.arrival_challenge_ttl_minutes
        ),
        arrival_code_max_attempts=int(
            row.get("arrival_code_max_attempts") or defaults.arrival_code_max_attempts
        ),
        arrival_denial_limit=int(
            row.get("arrival_denial_limit") or defaults.arrival_denial_limit
        ),
        false_arrival_auto_close=bool(row["false_arrival_auto_close"]),
        false_arrival_penalty_amount=Decimal(str(
            row["false_arrival_penalty_amount"]
            if row["false_arrival_penalty_amount"] is not None
            else defaults.false_arrival_penalty_amount
        )),
        false_arrival_health_weight=Decimal(str(
            row["false_arrival_health_weight"]
            if row["false_arrival_health_weight"] is not None
            else defaults.false_arrival_health_weight
        )),
        job_stall_watchdog_enabled=(
            bool(row["job_stall_watchdog_enabled"])
            if row.get("job_stall_watchdog_enabled") is not None else True
        ),
        job_stall_critical_multiplier=int(
            row.get("job_stall_critical_multiplier")
            or defaults.job_stall_critical_multiplier
        ),
        job_stall_limit_minutes=(
            dict(row.get("job_stall_limit_minutes") or defaults.job_stall_limit_minutes)
        ),
    )
