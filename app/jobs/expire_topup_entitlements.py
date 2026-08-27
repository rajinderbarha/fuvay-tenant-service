"""Lapse top-up entitlements whose validity has run out.

Seats and plan credit are granted with an `expires_at`; something has to act
on that date. Expiry is decided by the timestamp, never by when this loop
happens to fire, so a missed run costs nothing but latency -- a workspace that
should have lapsed at 02:00 lapses at the next tick with the same outcome.

The read path does not depend on this loop for correctness either:
`seat_enforcement.get_seat_usage` sums live entitlements directly, so seats
stop counting the moment they expire. What the sweep adds is the part that
cannot be derived on read -- withdrawing unspent credit and settling the
cached projection on `tenant_billing`.
"""
from __future__ import annotations

import asyncio

import structlog

logger = structlog.get_logger("jobs.expire_topup_entitlements")

#: Hourly. Validity is measured in days, so a tighter cadence would only add
#: load; a looser one would let expired credit stay spendable for too long.
INTERVAL_SECONDS = 3600


async def run_once() -> dict:
    """One sweep. Returns what it lapsed, for logs and for tests."""
    from app.database import get_session_factory
    from app.engines.vertical_catalog import topup_entitlement_service as entitlements

    from sqlalchemy import text
    from app.engines.vertical_catalog.seat_enforcement import sync_team_credit_suspension

    async with get_session_factory()() as db:
        result = await entitlements.expire_due(db)

        # Expiry can withdraw credit, and a balance can also move by paths that
        # do not reconcile inline (admin adjustment, settlement). This is the
        # backstop that makes team state converge either way.
        suspended = restored = 0
        for (tid,) in (await db.execute(text(
            "SELECT tenant_id FROM tenant_billing WHERE vertical_key = 'home_services'"
        ))).all():
            try:
                r = await sync_team_credit_suspension(db, tid)
                suspended += r["suspended"]
                restored += r["restored"]
            except Exception as exc:  # noqa: BLE001 -- one tenant must not stop the sweep
                logger.warning("team.credit_sync_failed", tenant_id=str(tid), error=str(exc))

        await db.commit()
        return {**result, "team_suspended": suspended, "team_restored": restored}


async def background_loop() -> None:
    while True:
        try:
            result = await run_once()
            if result["expired"] or result["team_suspended"] or result["team_restored"]:
                logger.info("topup_entitlements.swept", **result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 -- a bad sweep must not kill the loop
            logger.warning("topup_entitlements.sweep_failed", error=str(exc))
        await asyncio.sleep(INTERVAL_SECONDS)
