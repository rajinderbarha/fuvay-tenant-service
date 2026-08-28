"""Tell a provider their balance is running out, at a rate they will listen to.

A fixed every-two-hours reminder is how a provider learns to mute the channel,
and they mute all of it -- including the job assignment that arrives next. The
cadence is tied to how bad the situation actually is, so the platform earns the
right to be loud at the point where it is genuinely blocking someone's business:

  low       under the warning threshold        once a day
  blocked   under the floor, no new bookings   every 6 hours
  arrears   negative, or the team suspended    every 2 hours

Crossing INTO a worse level notifies immediately rather than waiting out the
previous tier's interval: the moment bookings stop is the moment worth telling
someone about, not six hours later.

Recovery clears the state, so a provider who has just paid is never chased by a
reminder queued before their payment landed.
"""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("vertical_catalog.credit_reminder")

#: Hours between reminders at each level, used when the policy leaves it unset.
DEFAULT_CADENCE_HOURS = {"low": 24, "blocked": 6, "arrears": 2}

#: Worst first. Used to tell an escalation from a routine repeat.
_SEVERITY = {"low": 1, "blocked": 2, "arrears": 3}

_HS_KEY = "home_services"

_COPY = {
    "low": ("Your credit is running low",
            "Top up to avoid interruption. Below the booking floor you stop receiving "
            "new bookings."),
    "blocked": ("You are not receiving new bookings",
                "Your credit is below the booking floor. Jobs already booked are "
                "unaffected and will finish normally — top up to start taking new "
                "bookings again."),
    "arrears": ("Your workspace is suspended",
                "Your credit balance is negative and your technicians cannot be "
                "assigned work. Top up to restore your team straight away."),
}


async def _cadence(db: AsyncSession) -> dict:
    row = (await db.execute(text(
        "SELECT p.credit_reminder_hours_low, p.credit_reminder_hours_blocked, "
        "       p.credit_reminder_hours_arrears "
        "FROM vertical_monetization_policies p "
        "JOIN verticals v ON v.id = p.vertical_id "
        "WHERE p.is_current = true AND p.status = 'published' AND v.key = :k LIMIT 1"
    ), {"k": _HS_KEY})).first()
    if row is None:
        return dict(DEFAULT_CADENCE_HOURS)
    return {
        "low": row.credit_reminder_hours_low or DEFAULT_CADENCE_HOURS["low"],
        "blocked": row.credit_reminder_hours_blocked or DEFAULT_CADENCE_HOURS["blocked"],
        "arrears": row.credit_reminder_hours_arrears or DEFAULT_CADENCE_HOURS["arrears"],
    }


def resolve_level(balance: Decimal, floor: Decimal, warning: Decimal) -> str | None:
    """Which tier this balance falls in, or None when there is nothing to say.

    Deliberately the same ordering the header credit pill uses, so a provider
    is never told one thing by a notification and another by their own screen.
    """
    if balance < 0:
        return "arrears"
    if balance < floor:
        return "blocked"
    if balance < warning:
        return "low"
    return None


def is_due(level: str, previous_level: str | None,
           last_sent: dt.datetime | None, cadence_hours: dict,
           now: dt.datetime | None = None) -> bool:
    """Whether to send now.

    An ESCALATION always sends: waiting out the previous, gentler interval
    would mean the provider learns that bookings have stopped hours after they
    stopped. Anything else waits for this level's cadence.
    """
    if previous_level is not None and _SEVERITY[level] > _SEVERITY.get(previous_level, 0):
        return True
    if last_sent is None:
        return True
    now = now or dt.datetime.now(dt.timezone.utc)
    hours = cadence_hours.get(level, DEFAULT_CADENCE_HOURS[level])
    return (now - last_sent) >= dt.timedelta(hours=hours)


async def sweep(db: AsyncSession, *, limit: int = 500) -> dict:
    """One pass over Home Services workspaces."""
    from app.engines.platform_notifications.models import InAppNotification

    cadence = await _cadence(db)
    policy = (await db.execute(text(
        "SELECT p.credit_warning_threshold, p.credit_booking_floor "
        "FROM home_services_activation_finance_policies p "
        "JOIN verticals v ON v.id = p.vertical_id "
        "WHERE p.is_current = true AND v.key = :k "
        "ORDER BY p.version_number DESC LIMIT 1"
    ), {"k": _HS_KEY})).first()
    if policy is None:
        return {"sent": 0, "recovered": 0, "reason": "no_finance_policy"}

    floor = Decimal(str(policy.credit_booking_floor or 0))
    warning = Decimal(str(policy.credit_warning_threshold or 0))

    rows = (await db.execute(text(
        "SELECT tenant_id, COALESCE(credit_balance, 0) AS balance, "
        "       last_credit_reminder_at, credit_reminder_level "
        "FROM tenant_billing WHERE vertical_key = :k LIMIT :lim"
    ), {"k": _HS_KEY, "lim": limit})).fetchall()

    sent = recovered = 0
    for row in rows:
        level = resolve_level(Decimal(str(row.balance)), floor, warning)

        if level is None:
            # Recovered. Clearing BOTH fields matters: leaving the level set
            # would make the next dip look like a repeat rather than a fresh
            # escalation, and delay the notification that matters most.
            if row.credit_reminder_level is not None:
                await db.execute(text(
                    "UPDATE tenant_billing SET credit_reminder_level = NULL, "
                    "  last_credit_reminder_at = NULL, updated_at = now() "
                    "WHERE tenant_id = :t"), {"t": row.tenant_id})
                recovered += 1
            continue

        if not is_due(level, row.credit_reminder_level, row.last_credit_reminder_at, cadence):
            continue

        owner = (await db.execute(text(
            "SELECT id FROM users WHERE tenant_id = :t AND role = 'tenant_owner' "
            "AND is_active = true LIMIT 1"), {"t": row.tenant_id})).scalar()
        if owner is None:
            continue

        title, body = _COPY[level]
        db.add(InAppNotification(
            user_id=owner, tenant_id=row.tenant_id,
            notification_type=f"credit_{level}",
            title=title,
            body=f"{body} Current balance: Rs.{Decimal(str(row.balance)):,.2f}.",
            action_url="/home-services/finance", action_label="Top up",
            source_record_type="tenant_billing", source_record_id=row.tenant_id,
            severity="danger" if level == "arrears" else "warning",
        ))
        await db.execute(text(
            "UPDATE tenant_billing SET last_credit_reminder_at = now(), "
            "  credit_reminder_level = :lvl, updated_at = now() WHERE tenant_id = :t"
        ), {"lvl": level, "t": row.tenant_id})
        sent += 1
        logger.info("credit_reminder.sent", tenant_id=str(row.tenant_id), level=level)

    return {"sent": sent, "recovered": recovered}
