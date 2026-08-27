"""Top-up plan catalogue — what an admin sells, and what a tenant may buy.

Plans are edited freely: unlike a published legal document or a finance
policy version, a plan is an OFFER, not a record of an agreement. What a
tenant actually paid is snapshotted onto their `activation_payment_orders`
row at capture (amount, credited_amount, tax_amount, seats_granted), so
re-pricing or retiring a plan can never rewrite history.

The one rule enforced here that is not obvious: a plan cannot be deleted
once an order references it. Deleting it would orphan the snapshot's
`topup_plan_id` and make a past purchase unexplainable. Retiring it
(`is_active = false`) removes it from the catalogue while keeping the
reference intact.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.models.base import utcnow

from app.engines.vertical_catalog.models import Vertical
from app.engines.vertical_catalog.topup_plan_models import HsTopupPlan

logger = structlog.get_logger("vertical_catalog.topup_plan_catalog")


async def _vertical(db: AsyncSession, key: str) -> Vertical:
    v = (await db.execute(select(Vertical).where(Vertical.key == key))).scalar_one_or_none()
    if not v:
        raise ServiceOSException("NOT_FOUND", f"Vertical '{key}' not found.", status_code=404)
    return v


async def _get(db: AsyncSession, plan_id: uuid.UUID) -> HsTopupPlan:
    row = (await db.execute(
        select(HsTopupPlan).where(HsTopupPlan.id == plan_id,
                                  HsTopupPlan.deleted_at.is_(None))
    )).scalars().first()
    if row is None:
        raise ServiceOSException("TOPUP_PLAN_NOT_FOUND", "That top-up plan does not exist.",
                                 status_code=404)
    return row


async def _order_count(db: AsyncSession, plan_id: uuid.UUID) -> int:
    """How many payment orders reference this plan (any status)."""
    from app.engines.vertical_catalog.activation_payment_models import ActivationPaymentOrder

    return int((await db.execute(
        select(func.count()).select_from(ActivationPaymentOrder)
        .where(ActivationPaymentOrder.topup_plan_id == plan_id)
    )).scalar_one())


# ── Read ─────────────────────────────────────────────────────────────────────
async def list_plans(
    db: AsyncSession, *, vertical_key: str, active_only: bool = False,
) -> list[dict]:
    v = await _vertical(db, vertical_key)
    conditions = [HsTopupPlan.vertical_id == v.id, HsTopupPlan.deleted_at.is_(None)]
    if active_only:
        conditions.append(HsTopupPlan.is_active.is_(True))
    rows = (await db.execute(
        select(HsTopupPlan).where(*conditions)
        .order_by(HsTopupPlan.sort_order, HsTopupPlan.base_amount)
    )).scalars().all()
    return [r.to_dict() for r in rows]


async def get_plan(db: AsyncSession, plan_id: uuid.UUID) -> dict:
    return (await _get(db, plan_id)).to_dict()


# ── Write ────────────────────────────────────────────────────────────────────
async def create_plan(
    db: AsyncSession, *, vertical_key: str, name: str, base_amount: Decimal,
    seats: int, gst_percent: Decimal = Decimal("18"), description: str | None = None,
    is_active: bool = True, is_default: bool = False, sort_order: int = 0,
    validity_days: int = 0,
    actor_id: uuid.UUID | None = None,
) -> dict:
    v = await _vertical(db, vertical_key)

    if base_amount <= 0:
        raise ServiceOSException("TOPUP_PLAN_INVALID", "Amount must be greater than zero.",
                                 status_code=422)
    if seats < 0:
        raise ServiceOSException("TOPUP_PLAN_INVALID", "Seats cannot be negative.",
                                 status_code=422)
    if validity_days < 0:
        raise ServiceOSException("TOPUP_PLAN_INVALID",
                                 "Validity cannot be negative. Use 0 for a plan that never expires.",
                                 status_code=422)
    if not (Decimal("0") <= gst_percent <= Decimal("100")):
        raise ServiceOSException("TOPUP_PLAN_INVALID", "GST percent must be between 0 and 100.",
                                 status_code=422)

    clash = (await db.execute(
        select(HsTopupPlan.id).where(HsTopupPlan.vertical_id == v.id,
                                     HsTopupPlan.name == name,
                                     HsTopupPlan.deleted_at.is_(None))
    )).scalars().first()
    if clash:
        raise ServiceOSException("TOPUP_PLAN_NAME_EXISTS",
                                 f"A plan named '{name}' already exists.", status_code=409)

    if is_default:
        await _clear_default(db, v.id)

    row = HsTopupPlan(
        vertical_id=v.id, name=name, description=description,
        base_amount=base_amount, gst_percent=gst_percent, seats=seats,
        is_active=is_active, is_default=is_default, sort_order=sort_order,
        validity_days=validity_days,
        created_by=actor_id,
    )
    db.add(row)
    await db.flush()
    logger.info("topup_plan.created", plan_id=str(row.id), name=name,
                base_amount=float(base_amount), seats=seats)
    return row.to_dict()


async def update_plan(
    db: AsyncSession, plan_id: uuid.UUID, *, name: str | None = None,
    description: str | None = None, base_amount: Decimal | None = None,
    gst_percent: Decimal | None = None, seats: int | None = None,
    is_active: bool | None = None, is_default: bool | None = None,
    sort_order: int | None = None, validity_days: int | None = None,
) -> dict:
    row = await _get(db, plan_id)

    if base_amount is not None:
        if base_amount <= 0:
            raise ServiceOSException("TOPUP_PLAN_INVALID", "Amount must be greater than zero.",
                                     status_code=422)
        row.base_amount = base_amount
    if validity_days is not None:
        if validity_days < 0:
            raise ServiceOSException("TOPUP_PLAN_INVALID",
                                     "Validity cannot be negative. Use 0 for a plan that never expires.",
                                     status_code=422)
        # Re-pricing or re-timing a plan never rewrites what someone already
        # bought: validity is snapshotted onto the entitlement at capture.
        row.validity_days = validity_days
    if gst_percent is not None:
        if not (Decimal("0") <= gst_percent <= Decimal("100")):
            raise ServiceOSException("TOPUP_PLAN_INVALID", "GST percent must be between 0 and 100.",
                                     status_code=422)
        row.gst_percent = gst_percent
    if seats is not None:
        if seats < 0:
            raise ServiceOSException("TOPUP_PLAN_INVALID", "Seats cannot be negative.",
                                     status_code=422)
        row.seats = seats
    if name is not None and name != row.name:
        clash = (await db.execute(
            select(HsTopupPlan.id).where(HsTopupPlan.vertical_id == row.vertical_id,
                                         HsTopupPlan.name == name,
                                         HsTopupPlan.id != row.id,
                                         HsTopupPlan.deleted_at.is_(None))
        )).scalars().first()
        if clash:
            raise ServiceOSException("TOPUP_PLAN_NAME_EXISTS",
                                     f"A plan named '{name}' already exists.", status_code=409)
        row.name = name
    if description is not None:
        row.description = description
    if sort_order is not None:
        row.sort_order = sort_order
    if is_active is not None:
        row.is_active = is_active
        # A retired plan must not stay the default anyone is offered.
        if not is_active:
            row.is_default = False
    if is_default is not None and is_default:
        await _clear_default(db, row.vertical_id, except_id=row.id)
        row.is_default = True
    elif is_default is not None:
        row.is_default = False

    await db.flush()
    return row.to_dict()


async def delete_plan(db: AsyncSession, plan_id: uuid.UUID) -> dict:
    """Soft-delete a plan that nobody has bought.

    A plan with orders against it is retired instead: deleting it would leave
    `activation_payment_orders.topup_plan_id` pointing at nothing, and a past
    purchase would become unexplainable.
    """
    row = await _get(db, plan_id)
    used = await _order_count(db, plan_id)
    if used:
        raise ServiceOSException(
            "TOPUP_PLAN_IN_USE",
            f"{used} payment order(s) reference this plan, so it cannot be deleted.",
            status_code=409,
            resolution="Set it inactive instead — it will stop being offered but stay auditable.",
        )
    row.deleted_at = utcnow()
    row.is_active = False
    row.is_default = False
    await db.flush()
    return {"deleted": True, "id": str(plan_id)}


async def _clear_default(db: AsyncSession, vertical_id: uuid.UUID,
                         except_id: uuid.UUID | None = None) -> None:
    """Only one default per vertical — a partial unique index enforces it, so
    clear the incumbent before setting a new one rather than racing it."""
    conditions = [HsTopupPlan.vertical_id == vertical_id, HsTopupPlan.is_default.is_(True)]
    if except_id is not None:
        conditions.append(HsTopupPlan.id != except_id)
    for row in (await db.execute(select(HsTopupPlan).where(*conditions))).scalars().all():
        row.is_default = False
    await db.flush()
