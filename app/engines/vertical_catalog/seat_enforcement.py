"""The three limits that replaced the security deposit.

Together these are what makes "we deduct from credit only" safe. A deposit
was collateral — held, never spent, so it was still there when something went
wrong. Credit is consumable, so instead of a held pot there are three gates:

  1. SEATS      a tenant may only have as many technicians as it has bought.
                Seats are the capacity lever: slot capacity is already
                derived from ready technicians, so one seat = one technician
                = one more job bookable in the same slot.

  2. WIP        a tenant may only hold as many open jobs as it has
                technicians. A seat is occupied from `assigned` until the
                technician marks `work_done` — at that moment they are
                physically free again, even though invoicing may still be
                pending, so back-office delay never blocks field work.

  3. CREDIT     below `credit_booking_floor` no NEW booking is accepted.
     FLOOR      Work already in flight finishes normally. Nothing is frozen;
                the floor simply stops the hole being dug deeper, so there is
                always a balance left to deduct a penalty or settlement
                against.

Every gate reads the published finance policy, so an admin can retune the
thresholds without a deploy.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException

logger = structlog.get_logger("vertical_catalog.seat_enforcement")

#: Seats a Home Services workspace gets without buying a plan.
#:
#: Zero, by product decision: a technician seat is bought, not granted. The
#: Team surface stays VISIBLE with no plan -- so the provider can see what a
#: plan unlocks and reach the purchase -- but it is locked until one is bought.
#: Activation itself still does not block on payment; the wall is here, at the
#: point where capacity is actually consumed, and it says how to get past it.
FREE_STARTER_SEATS = 0

#: Job states that occupy a technician. The seat frees at `work_done` — see
#: the module docstring for why that boundary and not `completed`.
OCCUPYING_JOB_STATUSES = (
    "assigned", "accepted", "scheduled", "on_the_way", "reached_site",
    "inspection_started", "inspection_done", "quote_required", "service_started",
    "customer_not_available",
)


async def _billing(db: AsyncSession, tenant_id: uuid.UUID):
    return (await db.execute(
        text("SELECT credit_balance, entitled_seats FROM tenant_billing WHERE tenant_id=:tid"),
        {"tid": str(tenant_id)},
    )).fetchone()


async def _policy(db: AsyncSession):
    """Published Home Services finance policy, or None.

    Returns None rather than raising: a missing policy must not make the
    platform unusable, and each caller decides whether to fail open or closed.
    """
    # Scoped to Home Services. `is_current` is unique PER VERTICAL, so an
    # unfiltered "WHERE is_current = true LIMIT 1" could return another
    # vertical's policy -- and with it another vertical's booking floor.
    return (await db.execute(text(
        "SELECT p.credit_warning_threshold, p.credit_booking_floor, p.seat_accrual_mode "
        "FROM home_services_activation_finance_policies p "
        "JOIN verticals v ON v.id = p.vertical_id "
        "WHERE p.is_current = true AND v.key = 'home_services' "
        "ORDER BY p.version_number DESC LIMIT 1"
    ))).fetchone()


# ── 1. Seats ─────────────────────────────────────────────────────────────────
async def get_seat_usage(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    from app.engines.vertical_catalog.finance_policy_service import (
        resolve_qualifying_technician_count,
    )

    from app.engines.vertical_catalog import topup_entitlement_service as entitlements

    # Read the ENTITLEMENTS, not the cached integer on `tenant_billing`. The
    # cache is refreshed by the expiry sweep, so trusting it here would let a
    # workspace keep capacity it had stopped paying for until the sweep next
    # ran. This is one indexed per-tenant aggregate.
    purchased = await entitlements.live_seats(db, tenant_id)
    # The free allowance is a floor, not an addition: buying a 3-seat plan
    # gives 3 seats, not 4. Otherwise every plan would quietly sell one seat
    # more than it advertises.
    entitled = max(purchased, FREE_STARTER_SEATS)
    used = await resolve_qualifying_technician_count(db, tenant_id)
    return {
        "purchased_seats": purchased,
        "free_starter_seats": FREE_STARTER_SEATS,
        "entitled_seats": entitled,
        "used_seats": used,
        "available_seats": max(0, entitled - used),
        "over_limit": used > entitled,
    }


async def assert_seat_available(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Raise if adding one more technician would exceed purchased seats."""
    usage = await get_seat_usage(db, tenant_id)
    if usage["available_seats"] <= 0:
        raise ServiceOSException(
            "TECHNICIAN_SEAT_LIMIT_REACHED",
            f"All {usage['entitled_seats']} purchased technician seat(s) are in use.",
            status_code=409,
            blocking_rule="topup_plan.seat_entitlement",
            resolution="Buy a top-up plan to add more technician seats.",
            context=usage,
        )


# ── 2. Work in progress ──────────────────────────────────────────────────────
async def get_wip_usage(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Open jobs occupying a technician, against the technician count."""
    from app.engines.vertical_catalog.finance_policy_service import (
        resolve_qualifying_technician_count,
    )

    technicians = await resolve_qualifying_technician_count(db, tenant_id)
    open_jobs = int((await db.execute(
        # service_jobs has no soft-delete column; a job leaves the pipeline by
        # reaching a terminal status, not by being flagged deleted.
        text("SELECT count(*) FROM service_jobs "
             "WHERE tenant_id = :tid AND status = ANY(:statuses)"),
        {"tid": str(tenant_id), "statuses": list(OCCUPYING_JOB_STATUSES)},
    )).scalar() or 0)
    return {
        "technician_count": technicians,
        "open_jobs": open_jobs,
        "available_capacity": max(0, technicians - open_jobs),
        "at_capacity": open_jobs >= technicians,
    }


async def assert_wip_capacity(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Raise if every technician already has an open job.

    Gates ASSIGNMENT, not booking: a job that cannot be assigned waits in
    `pending_assignment` rather than being refused, so the customer's request
    is never lost — it is simply queued until a technician frees up.
    """
    usage = await get_wip_usage(db, tenant_id)
    if usage["technician_count"] <= 0:
        raise ServiceOSException(
            "NO_TECHNICIANS_AVAILABLE",
            "This workspace has no active technicians to assign work to.",
            status_code=409,
            resolution="Add a technician, then assign the job.",
            context=usage,
        )
    if usage["at_capacity"]:
        raise ServiceOSException(
            "TECHNICIAN_CAPACITY_REACHED",
            f"All {usage['technician_count']} technician(s) already have an open job "
            f"({usage['open_jobs']} in progress).",
            status_code=409,
            blocking_rule="technician.work_in_progress_limit",
            resolution="Complete an in-progress job, or buy seats and add a technician.",
            context=usage,
        )


# ── 3. Credit floor ──────────────────────────────────────────────────────────
async def get_credit_state(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    row = await _billing(db, tenant_id)
    policy = await _policy(db)
    balance = Decimal(str(row.credit_balance)) if row and row.credit_balance is not None else Decimal("0")
    floor = Decimal(str(policy.credit_booking_floor)) if policy else Decimal("0")
    warn = Decimal(str(policy.credit_warning_threshold)) if policy else Decimal("0")
    return {
        "credit_balance": float(balance),
        "booking_floor": float(floor),
        "warning_threshold": float(warn),
        "below_floor": balance < floor,
        "below_warning": balance < warn,
        "in_arrears": balance < 0,
    }


async def assert_booking_allowed(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Raise if the tenant's credit has fallen below the booking floor.

    Deliberately gates only NEW bookings. Jobs already accepted run to
    completion — stranding a customer mid-job to punish the provider's balance
    would put the cost on the wrong person.
    """
    state = await get_credit_state(db, tenant_id)
    if state["below_floor"]:
        raise ServiceOSException(
            "CREDIT_BELOW_BOOKING_FLOOR",
            f"Credit balance ₹{state['credit_balance']:,.2f} is below the "
            f"₹{state['booking_floor']:,.2f} booking floor.",
            status_code=409,
            blocking_rule="finance_policy.credit_booking_floor",
            resolution="Buy a top-up plan to resume accepting bookings.",
            context=state,
        )


# ── 4. Credit suspension ─────────────────────────────────────────────────────
async def sync_team_credit_suspension(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """Suspend the team when credit runs out; restore it when credit returns.

    Called after anything that moves the balance. Idempotent: running it twice
    changes nothing the second time, and running it late reaches the same state
    as running it on time, because it is driven by the balance rather than by
    the event that changed it.

    Only members this function suspended are restored. `credit_suspended_at`
    is what separates them from someone the provider deactivated deliberately,
    who is left exactly as they were set.
    """
    balance = (await db.execute(
        text("SELECT COALESCE(credit_balance, 0) FROM tenant_billing WHERE tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )).scalar()
    if balance is None:
        return {"action": "no_billing_row", "suspended": 0, "restored": 0}

    exhausted = Decimal(str(balance)) <= 0
    if exhausted:
        # Only members who are active RIGHT NOW; someone already inactive is
        # left alone so restoring cannot switch on a person who was off.
        result = await db.execute(text(
            "UPDATE provider_team_members "
            "SET status = 'inactive', credit_suspended_at = now(), updated_at = now() "
            "WHERE tenant_id = CAST(:tid AS uuid) AND deleted_at IS NULL "
            "  AND status = 'active' AND credit_suspended_at IS NULL "
            "RETURNING id"
        ), {"tid": str(tenant_id)})
        n = len(result.fetchall())
        if n:
            logger.info("team.credit_suspended", tenant_id=str(tenant_id), members=n,
                        balance=float(balance))
        return {"action": "suspended", "suspended": n, "restored": 0,
                "credit_balance": float(balance)}

    result = await db.execute(text(
        "UPDATE provider_team_members "
        "SET status = 'active', credit_suspended_at = NULL, updated_at = now() "
        "WHERE tenant_id = CAST(:tid AS uuid) AND deleted_at IS NULL "
        "  AND credit_suspended_at IS NOT NULL "
        "RETURNING id"
    ), {"tid": str(tenant_id)})
    n = len(result.fetchall())
    if n:
        logger.info("team.credit_restored", tenant_id=str(tenant_id), members=n,
                    balance=float(balance))
    return {"action": "restored", "suspended": 0, "restored": n,
            "credit_balance": float(balance)}
