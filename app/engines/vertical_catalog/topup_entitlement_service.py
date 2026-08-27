"""Purchased capacity that can lapse.

`tenant_billing.entitled_seats` is an integer that only ever grew, so a plan's
validity had nowhere to live. Each purchase now writes a row here recording
what it granted and when it lapses; entitled seats are the SUM over live rows,
which can finally go down.

`tenant_billing.entitled_seats` is kept in step as a CACHED PROJECTION -- the
header credit pill and the slot search read it on every page and every
availability query, and neither should aggregate a growing table to learn one
integer. `recompute_seats` is the only writer.

HOW EXPIRING CREDIT IS COSTED

`credit_balance` stays the single spendable number, so every consumer (job
commission, invoice checkout, refunds, admin adjustments) is untouched. Plan
credit is treated as spent OLDEST FIRST, which is both the friendliest reading
for the provider and the only one that makes a lapse predictable: the lot about
to expire is the one that has already been drawn down.

What lapses is the part of the grant the provider never spent, measured from
`usage_credit_ledger` -- every real deduction writes a row there:

    spent   = |negative ledger deltas since the lot started|
    unspent = max(0, credit_granted - spent)
    withdraw = min(unspent, current balance)

Deriving `spent` from the ledger rather than from the balance is the whole
point. An earlier version costed it as `balance - grants_of_newer_lots`, which
silently confiscated money the provider already had before they ever bought
the plan: with Rs.1,000 in hand, a Rs.2,000 grant and Rs.1,500 spent, it took
Rs.1,500 instead of the Rs.500 that was actually unspent. Capping at the live
balance keeps it from ever pushing an account negative.
"""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("vertical_catalog.topup_entitlement")


def _expiry(validity_days: int, start: dt.datetime | None = None) -> dt.datetime | None:
    """None when the plan never expires -- the default for every plan today."""
    if not validity_days or validity_days <= 0:
        return None
    return (start or dt.datetime.now(dt.timezone.utc)) + dt.timedelta(days=int(validity_days))


async def grant(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    seats: int,
    credit_granted: Decimal | float | int = 0,
    plan_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    validity_days: int = 0,
) -> dict:
    """Record what one purchase granted. Idempotent per `order_id`.

    A captured payment may be delivered more than once (gateway webhook plus a
    reconcile), and seats must not be granted twice for one payment. The unique
    index on `order_id` makes the second insert a no-op.
    """
    expires_at = _expiry(validity_days)
    row = (await db.execute(text(
        "INSERT INTO tenant_topup_entitlements "
        "    (tenant_id, plan_id, order_id, seats, credit_granted, validity_days, expires_at) "
        "VALUES (CAST(:tid AS uuid), CAST(:pid AS uuid), CAST(:oid AS uuid), "
        "        :seats, :credit, :vdays, :expires) "
        "ON CONFLICT (order_id) WHERE order_id IS NOT NULL DO NOTHING "
        "RETURNING id, expires_at"
    ), {
        "tid": str(tenant_id),
        "pid": str(plan_id) if plan_id else None,
        "oid": str(order_id) if order_id else None,
        "seats": int(seats or 0),
        "credit": Decimal(str(credit_granted or 0)),
        "vdays": int(validity_days or 0),
        "expires": expires_at,
    })).first()

    if row is None:  # already granted for this order
        logger.info("topup.entitlement.duplicate_ignored", tenant_id=str(tenant_id),
                    order_id=str(order_id) if order_id else None)
        return {"granted": False, "entitled_seats": await recompute_seats(db, tenant_id)}

    entitled = await recompute_seats(db, tenant_id)
    logger.info("topup.entitlement.granted", tenant_id=str(tenant_id), seats=int(seats or 0),
                expires_at=str(expires_at), entitled_seats=entitled)
    return {"granted": True, "entitlement_id": str(row[0]),
            "expires_at": row[1], "entitled_seats": entitled}


async def live_seats(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Seats from purchases that have not lapsed."""
    return int((await db.execute(text(
        "SELECT COALESCE(SUM(seats), 0) FROM tenant_topup_entitlements "
        "WHERE tenant_id = CAST(:tid AS uuid) "
        "  AND status = 'active' "
        "  AND (expires_at IS NULL OR expires_at > now())"
    ), {"tid": str(tenant_id)})).scalar() or 0)


async def recompute_seats(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Refresh the cached projection on `tenant_billing`. The only writer."""
    seats = await live_seats(db, tenant_id)
    await db.execute(text(
        "UPDATE tenant_billing SET entitled_seats = :seats, updated_at = now() "
        "WHERE tenant_id = CAST(:tid AS uuid)"
    ), {"seats": seats, "tid": str(tenant_id)})
    return seats


async def list_for_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    """What this workspace has bought, newest first, with what is still live."""
    rows = (await db.execute(text(
        "SELECT e.id, e.seats, e.credit_granted, e.credit_expired, e.validity_days, "
        "       e.starts_at, e.expires_at, e.status, p.name AS plan_name, "
        "       (e.status = 'active' AND (e.expires_at IS NULL OR e.expires_at > now())) AS is_live "
        "FROM tenant_topup_entitlements e "
        "LEFT JOIN hs_topup_plans p ON p.id = e.plan_id "
        "WHERE e.tenant_id = CAST(:tid AS uuid) "
        "ORDER BY e.starts_at DESC"
    ), {"tid": str(tenant_id)})).fetchall()
    return [{
        "id": str(r.id),
        "plan_name": r.plan_name,
        "seats": int(r.seats or 0),
        "credit_granted": float(r.credit_granted or 0),
        "credit_expired": float(r.credit_expired or 0),
        "validity_days": int(r.validity_days or 0),
        "starts_at": r.starts_at.isoformat() if r.starts_at else None,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        "never_expires": r.expires_at is None,
        "status": r.status,
        "is_live": bool(r.is_live),
    } for r in rows]


async def expire_due(db: AsyncSession, *, tenant_id: uuid.UUID | None = None,
                     limit: int = 500) -> dict:
    """Lapse everything past its date, withdrawing unspent plan credit.

    Safe to run repeatedly and safe to run late: expiry is decided by
    `expires_at`, never by when the sweep happened to fire.
    """
    scope = "AND tenant_id = CAST(:tid AS uuid) " if tenant_id else ""
    params: dict = {"lim": limit}
    if tenant_id:
        params["tid"] = str(tenant_id)

    due = (await db.execute(text(
        "SELECT id, tenant_id, credit_granted, starts_at, expires_at "
        "FROM tenant_topup_entitlements "
        "WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= now() "
        + scope +
        "ORDER BY expires_at LIMIT :lim FOR UPDATE SKIP LOCKED"
    ), params)).fetchall()

    expired, withdrawn_total = 0, Decimal("0")
    for row in due:
        tid = row.tenant_id
        balance = Decimal(str((await db.execute(text(
            "SELECT COALESCE(credit_balance, 0) FROM tenant_billing "
            "WHERE tenant_id = :tid FOR UPDATE"), {"tid": tid})).scalar() or 0))

        # What the provider actually spent since this grant landed. Every real
        # deduction (commission, checkout, settlement) writes a ledger row, so
        # this is the only honest measure of what is left OF THIS GRANT --
        # the balance alone cannot tell plan credit from money they already had.
        spent = Decimal(str((await db.execute(text(
            "SELECT COALESCE(SUM(-credit_delta), 0) FROM usage_credit_ledger "
            "WHERE tenant_id = :tid AND credit_delta < 0 AND created_at >= :since"
        ), {"tid": tid, "since": row.starts_at})).scalar() or 0))

        granted = Decimal(str(row.credit_granted or 0))
        unspent = max(Decimal("0"), granted - spent)
        withdraw = max(Decimal("0"), min(unspent, balance))

        if withdraw > 0:
            after = balance - withdraw
            await db.execute(text(
                "UPDATE tenant_billing SET credit_balance = :bal, updated_at = now() "
                "WHERE tenant_id = :tid"), {"bal": after, "tid": tid})
            await db.execute(text(
                "INSERT INTO usage_credit_ledger "
                "    (tenant_id, event_type, credit_delta, balance_before, balance_after, "
                "     deduction_source) "
                "VALUES (:tid, 'topup_plan_credit_expired', :delta, :before, :after, "
                "        'topup_plan_validity')"
            ), {"tid": tid, "delta": float(-withdraw),
                "before": float(balance), "after": float(after)})
            withdrawn_total += withdraw

        await db.execute(text(
            "UPDATE tenant_topup_entitlements "
            "SET status = 'expired', expired_at = now(), credit_expired = :w, updated_at = now() "
            "WHERE id = :eid"), {"w": withdraw, "eid": row.id})
        await recompute_seats(db, uuid.UUID(str(tid)))
        expired += 1
        logger.info("topup.entitlement.expired", tenant_id=str(tid),
                    entitlement_id=str(row.id), credit_withdrawn=float(withdraw))

    return {"expired": expired, "credit_withdrawn": float(withdrawn_total)}
