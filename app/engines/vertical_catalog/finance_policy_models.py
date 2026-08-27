"""HOME-SERVICES-FINANCE-POLICY-01 — canonical, admin-configurable,
versioned Home Services activation finance policy.

Replaces the hardcoded constants that used to live in
activation_deposit_policy.py (deleted in migration 317) with a real DB-backed, draft/published/retired
versioned record, vertical-scoped, following the exact same versioning
idiom already proven in app.engines.vertical_monetization.models
.VerticalMonetizationPolicy (version_number + status + is_current with a
unique partial index on is_current) rather than inventing a parallel
scheme.

Scope note (time-boxed pass): this table only covers the ACTIVATION finance
policy (top-up credit package + credit protection thresholds + completion-
deduction policy reference) — NOT provider commission / customer fee models, which
already live in VerticalMonetizationPolicy and are untouched here.
"""
from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class HomeServicesActivationFinancePolicy(ServiceOSBase):
    __tablename__ = "home_services_activation_finance_policies"
    __table_args__ = (
        Index("ix_hsafp_vertical", "vertical_id"),
        Index("ix_hsafp_vertical_current", "vertical_id", unique=True,
              postgresql_where="is_current = true"),
        Index("ix_hsafp_vertical_version", "vertical_id", "version_number", unique=True),
        Index("ix_hsafp_status", "status"),
    )

    vertical_id:    Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_number: Mapped[int]       = mapped_column(Integer, nullable=False)
    # draft -> published -> retired. Published rows are immutable (enforced
    # at the service layer, not the DB) -- publishing a new version retires
    # the previous is_current row rather than mutating it in place.
    status:         Mapped[str]       = mapped_column(String(20), default="draft", nullable=False)
    is_current:     Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)

    # ── Credit protection thresholds ──────────────────────────────────────
    # These replace the security deposit (migration 317). A deposit was
    # collateral — held, never spent, so it was still there when something
    # went wrong. Credit is consumable: completed-job commission spends it.
    # Rather than freezing a second pot the tenant paid for, two thresholds
    # sit on the single balance:
    #
    #   warning  notify the tenant to top up
    #   floor    below this, no NEW bookings are accepted; work already in
    #            flight finishes normally
    #
    # Nothing is locked. The floor stops the hole being dug deeper, so there
    # is always something left to deduct a penalty or settlement against.
    credit_warning_threshold: Mapped[Numeric] = mapped_column(Numeric(12, 2), default=1000, nullable=False)
    credit_booking_floor:     Mapped[Numeric] = mapped_column(Numeric(12, 2), default=500, nullable=False)

    # How buying a second plan affects headcount.
    #   cumulative   every purchase adds its seats (default)
    #   highest_plan entitlement is the largest plan ever bought
    seat_accrual_mode: Mapped[str] = mapped_column(String(20), default="cumulative", nullable=False)

    # ── Starter credit package ────────────────────────────────────────────
    initial_credit_purchase_required: Mapped[bool]    = mapped_column(Boolean, default=True, nullable=False)
    credit_package_base_amount:       Mapped[Numeric] = mapped_column(Numeric(12, 2), default=1000, nullable=False)
    credit_package_gst_percent:       Mapped[Numeric] = mapped_column(Numeric(6, 3), default=18, nullable=False)
    # Usable wallet credit granted on confirmed payment == base amount only.
    # GST NEVER enters the usable credit wallet — recorded as a separate tax
    # event at payment-confirmation time (see finance_policy_service.py).
    credited_wallet_amount:           Mapped[Numeric] = mapped_column(Numeric(12, 2), default=1000, nullable=False)

    # ── Completion-deduction policy reference (existing usage-credit
    # deduction engine already implements the mechanics; this only records
    # WHICH policy variant this finance-policy version assumes) ───────────
    completion_deduction_policy: Mapped[str | None] = mapped_column(String(60), nullable=True)

    currency:            Mapped[str]            = mapped_column(String(3), default="INR", nullable=False)
    effective_from:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_until:      Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    change_summary:       Mapped[str | None]      = mapped_column(Text, nullable=True)
    created_by_user_id:   Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_at:         Mapped[datetime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "vertical_id": str(self.vertical_id),
            "version_number": self.version_number, "status": self.status, "is_current": self.is_current,
            "credit_warning_threshold": float(self.credit_warning_threshold),
            "credit_booking_floor": float(self.credit_booking_floor),
            "seat_accrual_mode": self.seat_accrual_mode,
            "initial_credit_purchase_required": self.initial_credit_purchase_required,
            "credit_package_base_amount": float(self.credit_package_base_amount),
            "credit_package_gst_percent": float(self.credit_package_gst_percent),
            "credited_wallet_amount": float(self.credited_wallet_amount),
            "completion_deduction_policy": self.completion_deduction_policy,
            "currency": self.currency,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_until": self.effective_until.isoformat() if self.effective_until else None,
            "change_summary": self.change_summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
