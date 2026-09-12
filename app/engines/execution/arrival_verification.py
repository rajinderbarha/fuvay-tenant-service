"""Server-authoritative technician arrival verification.

No GPS, stale GPS, or poor GPS blocks an arrival claim but does not punish the
provider. A fresh, accurate fix outside the customer geofence is affirmative
evidence: the job is closed and the requested Rs.150 false-arrival penalty is
posted exactly once.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException

# Documented fallbacks retained for callers/tests; live enforcement resolves
# the published admin policy on every arrival attempt.
ARRIVAL_RADIUS_METERS = 250.0
MAX_LOCATION_AGE_SECONDS = 120
MAX_LOCATION_ACCURACY_METERS = 100.0
FALSE_ARRIVAL_PENALTY = Decimal("150.00")


def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance between two WGS84 points."""
    radius = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def verify_arrival(db: AsyncSession, *, job, staff_member_id) -> dict:
    from app.engines.vertical_monetization.runtime_operations import (
        get_home_services_operations_policy,
    )
    policy = await get_home_services_operations_policy(db)
    if not policy.arrival_verification_enabled:
        return {"verified": False, "verification_disabled": True}

    destination = (await db.execute(text(
        "SELECT ca.latitude, ca.longitude FROM service_bookings sb "
        "JOIN home_service_booking_drafts d ON d.id=sb.draft_id "
        "JOIN customer_addresses ca ON ca.id=d.address_id "
        "WHERE sb.id=:bid LIMIT 1"
    ), {"bid": str(job.booking_id)})).first()
    if not destination or destination.latitude is None or destination.longitude is None:
        raise ServiceOSException(
            "ARRIVAL_ADDRESS_NOT_VERIFIED",
            "The customer address has no verified map location. Ask the customer to correct the address before arrival.",
            status_code=409,
        )

    location = (await db.execute(text(
        "SELECT latitude, longitude, accuracy_meters, recorded_at FROM technician_live_locations "
        "WHERE job_id=:jid AND staff_id=:sid LIMIT 1"
    ), {"jid": str(job.id), "sid": str(staff_member_id)})).first()
    if not location:
        raise ServiceOSException(
            "ARRIVAL_LOCATION_REQUIRED",
            "Enable location and submit your current position before marking arrival.",
            status_code=409,
        )

    now = datetime.now(timezone.utc)
    recorded_at = location.recorded_at
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)
    age = (now - recorded_at).total_seconds()
    accuracy = float(location.accuracy_meters) if location.accuracy_meters is not None else None
    if age > policy.arrival_location_max_age_seconds:
        raise ServiceOSException(
            "ARRIVAL_LOCATION_STALE", "Update your location before marking arrival.", status_code=409)
    if accuracy is None or accuracy > policy.arrival_max_accuracy_meters:
        raise ServiceOSException(
            "ARRIVAL_LOCATION_INACCURATE",
            "Wait for a more accurate GPS signal before marking arrival.", status_code=409,
        )

    distance = distance_meters(
        float(location.latitude), float(location.longitude),
        float(destination.latitude), float(destination.longitude),
    )
    if distance > policy.arrival_radius_meters:
        if not policy.false_arrival_auto_close:
            raise ServiceOSException(
                "ARRIVAL_OUTSIDE_SERVICE_AREA",
                "Your verified location is outside the customer address area.",
                status_code=409,
                context={"distance_meters": round(distance, 1),
                         "allowed_radius_meters": policy.arrival_radius_meters},
            )
        await _close_false_arrival(
            db, job=job, staff_member_id=staff_member_id,
            distance=distance, accuracy=accuracy,
            penalty=policy.false_arrival_penalty_amount,
        )
        # Commit before surfacing the refusal: financial and closure mutations
        # must survive the HTTP error response.
        await db.commit()
        raise ServiceOSException(
            "FALSE_ARRIVAL_JOB_CLOSED",
            "Your verified location is outside the customer address area. "
            f"The job was closed and a Rs.{policy.false_arrival_penalty_amount:,.2f} penalty applied.",
            status_code=409,
            context={"distance_meters": round(distance, 1),
                     "allowed_radius_meters": policy.arrival_radius_meters},
        )

    await db.execute(text(
        "UPDATE service_jobs SET arrival_verified_at=now(), arrival_distance_meters=:distance, "
        "updated_at=now() WHERE id=:jid"
    ), {"jid": str(job.id), "distance": round(distance, 2)})
    job.arrival_verified_at = now
    job.arrival_distance_meters = Decimal(str(round(distance, 2)))
    return {"verified": True, "distance_meters": round(distance, 1),
            "allowed_radius_meters": policy.arrival_radius_meters}


async def _close_false_arrival(db: AsyncSession, *, job, staff_member_id,
                               distance: float, accuracy: float,
                               penalty: Decimal = FALSE_ARRIVAL_PENALTY) -> None:
    from app.engines.execution.models import ServiceJobExecutionEvent
    from app.engines.execution.sla_breach_service import _charge_penalty, _close_breached_job

    taken = await _charge_penalty(
        db, tenant_id=job.tenant_id, job_id=job.id,
        amount=penalty, cap=None, day_number=1,
        source="false_arrival",
    )
    await db.execute(text(
        "UPDATE service_jobs SET sla_penalty_charged=COALESCE(sla_penalty_charged,0)+:taken, "
        "sla_stopped_at=now(), sla_next_penalty_at=NULL, updated_at=now() WHERE id=:jid"
    ), {"jid": str(job.id), "taken": taken})
    await _close_breached_job(
        db, job_id=job.id, booking_id=job.booking_id,
        reason="False arrival detected outside the customer address geofence",
    )
    db.add(ServiceJobExecutionEvent(
        booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
        staff_member_id=staff_member_id, actor_role="staff",
        event_type="false_arrival_detected", old_status=job.status,
        new_status="cancelled",
        notes="Fresh accurate GPS was outside the customer arrival geofence.",
        event_metadata={"distance_meters": round(distance, 1),
                        "accuracy_meters": round(accuracy, 1),
                        "penalty": float(taken)},
    ))
    await db.flush()
    from app.engines.tenant_engine.health import refresh_provider_operational_health
    await refresh_provider_operational_health(db, job.tenant_id)
