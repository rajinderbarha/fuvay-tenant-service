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


@dataclass(frozen=True)
class HomeServicesOperationsPolicy:
    assignment_timeout_enabled: bool = True
    assignment_timeout_minutes: int = 30
    urgent_assignment_timeout_minutes: int = 10
    urgent_assignment_threshold_minutes: int = 120
    assignment_auto_assign_enabled: bool = True
    customer_reschedule_limit: int = 3
    arrival_verification_enabled: bool = False
    arrival_radius_meters: int = 250
    arrival_location_max_age_seconds: int = 120
    arrival_max_accuracy_meters: int = 100
    false_arrival_auto_close: bool = True
    false_arrival_penalty_amount: Decimal = Decimal("150.00")
    false_arrival_health_weight: Decimal = Decimal("3.00")
    job_stall_watchdog_enabled: bool = True
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
        "p.customer_reschedule_limit, p.arrival_verification_enabled, "
        "p.arrival_radius_meters, p.arrival_location_max_age_seconds, "
        "p.arrival_max_accuracy_meters, p.false_arrival_auto_close, "
        "p.false_arrival_penalty_amount, p.false_arrival_health_weight, "
        "p.job_stall_watchdog_enabled, p.job_stall_limit_minutes "
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
        arrival_verification_enabled=bool(row["arrival_verification_enabled"]),
        arrival_radius_meters=int(row["arrival_radius_meters"] or defaults.arrival_radius_meters),
        arrival_location_max_age_seconds=int(
            row["arrival_location_max_age_seconds"]
            or defaults.arrival_location_max_age_seconds
        ),
        arrival_max_accuracy_meters=int(
            row["arrival_max_accuracy_meters"] or defaults.arrival_max_accuracy_meters
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
        job_stall_limit_minutes=(
            dict(row.get("job_stall_limit_minutes") or defaults.job_stall_limit_minutes)
        ),
    )
