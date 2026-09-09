"""Compact, PII-free unmet-area demand capture.

Failed serviceability checks are aggregated in place. They must never create
booking drafts or draft events: a postcode search is demand intelligence, not
an operational booking request.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_booking.models import HomeServiceAreaDemandSignal


ALLOWED_CHANNELS = {"customer_app", "instagram", "whatsapp"}


def normalize_zipcode(value: str | None) -> str | None:
    normalized = "".join(ch for ch in (value or "").strip() if ch.isalnum())
    return normalized[:20] or None


async def record_unserved_area_demand(
    db: AsyncSession,
    *,
    zipcode: str | None,
    channel: str,
    city: str | None = None,
    state: str | None = None,
    category_key: str | None = None,
    category_name: str | None = None,
    service_key: str | None = None,
    service_name: str | None = None,
    outcome: str = "no_coverage",
    dedupe_token: str | None = None,
) -> bool:
    """Atomically increment one daily aggregate and return whether it was saved.

    No customer id, phone, address, session id, or free-form issue text is
    accepted by this API. This makes it safe and cheap for high-volume search
    traffic while retaining the dimensions expansion teams need.
    """
    normalized_zipcode = normalize_zipcode(zipcode)
    if not normalized_zipcode:
        return False

    now = datetime.now(timezone.utc)
    category_dimension = (category_key or "").strip().lower()[:120]
    service_dimension = (service_key or "").strip().lower()[:160]
    normalized_channel = channel if channel in ALLOWED_CHANNELS else "customer_app"
    normalized_outcome = (outcome or "no_coverage")[:40]

    # Count one interest signal per actor/dimension/day. The actor token is
    # hashed and held only in Redis for a day; it is never written to the
    # analytics table. If Redis is unavailable, the database upsert still
    # succeeds so useful demand is not lost.
    if dedupe_token:
        fingerprint = hashlib.sha256(
            "|".join((str(now.date()), normalized_zipcode, category_dimension,
                      service_dimension, normalized_channel, normalized_outcome,
                      dedupe_token)).encode("utf-8")
        ).hexdigest()
        try:
            from app.redis_client import get_redis
            accepted = await get_redis().set(
                f"hs:unserved-demand:{fingerprint}", "1", ex=90000, nx=True,
            )
            if not accepted:
                return False
        except Exception:
            pass

    values = {
        "day_bucket": now.date(),
        "zipcode": normalized_zipcode,
        "city": (city or "").strip()[:100] or None,
        "state": (state or "").strip()[:100] or None,
        "category_key": category_dimension,
        "category_name": (category_name or "").strip()[:160] or None,
        "service_key": service_dimension,
        "service_name": (service_name or "").strip()[:200] or None,
        "channel": normalized_channel,
        "outcome": normalized_outcome,
        "check_count": 1,
        "first_checked_at": now,
        "last_checked_at": now,
    }
    statement = insert(HomeServiceAreaDemandSignal).values(**values)
    excluded = statement.excluded
    statement = statement.on_conflict_do_update(
        constraint="uq_hs_area_demand_daily_dimension",
        set_={
            "check_count": HomeServiceAreaDemandSignal.check_count + 1,
            "last_checked_at": now,
            "city": excluded.city,
            "state": excluded.state,
            "category_name": excluded.category_name,
            "service_name": excluded.service_name,
            "updated_at": now,
        },
    )
    await db.execute(statement)
    return True
