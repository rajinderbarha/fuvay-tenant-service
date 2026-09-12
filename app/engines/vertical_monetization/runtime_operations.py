"""Published Home Services operational policy used by background and job flows.

The admin edits these values through the versioned monetization policy.  This
small reader keeps fallbacks in one place for installations that do not yet
have a published Home Services policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class HomeServicesOperationsPolicy:
    assignment_timeout_enabled: bool = True
    assignment_timeout_minutes: int = 15
    customer_reschedule_limit: int = 3
    arrival_verification_enabled: bool = True
    arrival_radius_meters: int = 250
    arrival_location_max_age_seconds: int = 120
    arrival_max_accuracy_meters: int = 100
    false_arrival_auto_close: bool = True
    false_arrival_penalty_amount: Decimal = Decimal("150.00")
    false_arrival_health_weight: Decimal = Decimal("3.00")


async def get_home_services_operations_policy(
    db: AsyncSession,
) -> HomeServicesOperationsPolicy:
    row = (await db.execute(text(
        "SELECT p.assignment_timeout_enabled, p.assignment_timeout_minutes, "
        "p.customer_reschedule_limit, p.arrival_verification_enabled, "
        "p.arrival_radius_meters, p.arrival_location_max_age_seconds, "
        "p.arrival_max_accuracy_meters, p.false_arrival_auto_close, "
        "p.false_arrival_penalty_amount, p.false_arrival_health_weight "
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
    )
