"""Home Services top-up plans — what an admin sells, and what it buys.

A top-up plan is the single commercial object a Home Services tenant buys.
It carries two things at once:

  * CREDIT — the base amount lands in `tenant_billing.credit_balance`. GST
    never does; it is recorded as a separate tax event, exactly as the
    previous credit package did.
  * SEATS — how many technicians the tenant may have active. Seats are the
    real capacity lever: slot capacity is already derived from ready
    technicians (see home_service_booking/provider_slot_service.py), so
    three seats means three technicians, which means three jobs bookable in
    the same slot.

This replaces the security deposit. The deposit was collateral scaled to
headcount; seats invert that — headcount is now scaled to what was bought,
and the platform's recourse comes from the credit balance plus the floor
that stops it being spent to nothing (see `credit_booking_floor` on the
finance policy).

A plain catalogue rather than the draft/publish versioning used by the
finance policy: an admin creates "Rs.5,000 / 3 seats" and edits or retires
it. What a tenant actually paid is snapshotted onto their
`activation_payment_orders` row at capture, so re-pricing a plan can never
rewrite what someone already bought — which is the only thing the
versioning would have protected.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


class HsTopupPlan(ServiceOSBase):
    """One purchasable top-up: a price, and the seats it grants."""

    __tablename__ = "hs_topup_plans"

    vertical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Pre-tax price. This is also the amount credited to the wallet.
    base_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gst_percent: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=Decimal("18"))

    #: Technician seats granted on capture. Zero is allowed deliberately —
    #: a pure credit top-up for a tenant that already has the headcount it
    #: needs and only wants to refill the wallet.
    seats: Mapped[int] = mapped_column(Integer, nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    #: Offered to a tenant that has never bought one. At most one per
    #: vertical — enforced by a partial unique index, not by convention.
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    #: How long the seats and credit this plan grants stay live, in days.
    #: Zero means the purchase never lapses -- the behaviour every plan had
    #: before validity existed, so it is the default and no existing plan
    #: changes meaning.
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    #: Soft delete. ServiceOSBase carries timestamps but not SoftDeleteMixin,
    #: so this is declared explicitly rather than inherited. Only a plan no
    #: order references can be deleted at all — see delete_plan().
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Derived money ────────────────────────────────────────────────────────
    @property
    def gst_amount(self) -> Decimal:
        return _q(Decimal(str(self.base_amount)) * Decimal(str(self.gst_percent)) / Decimal("100"))

    @property
    def total_amount(self) -> Decimal:
        """What the tenant actually pays at the gateway."""
        return _q(Decimal(str(self.base_amount)) + self.gst_amount)

    @property
    def credited_amount(self) -> Decimal:
        """What reaches the wallet. Base only — GST is a tax event, never credit."""
        return _q(Decimal(str(self.base_amount)))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "vertical_id": str(self.vertical_id),
            "name": self.name,
            "description": self.description,
            "base_amount": float(self.base_amount),
            "gst_percent": float(self.gst_percent),
            "gst_amount": float(self.gst_amount),
            "total_amount": float(self.total_amount),
            "credited_amount": float(self.credited_amount),
            "seats": self.seats,
            "currency": self.currency,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "sort_order": self.sort_order,
            "validity_days": self.validity_days,
            "never_expires": not self.validity_days,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
