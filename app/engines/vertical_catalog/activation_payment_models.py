"""HOME-SERVICES-ACTIVATION-PAYMENT-01 — real online Razorpay collection for
the two Home Services activation gates (security deposit + starter credit
package). Alongside the existing ADMIN-ONLY offline verify-deposit path
(vertical_catalog/admin_router.py), this is the ONLINE, tenant-initiated
path: tenant creates a Razorpay order for the exact policy-resolved amount,
pays via Razorpay Checkout, and only a server-verified webhook call (never
a client-reported "success") posts money into tenant_billing.

One row per Razorpay order. gateway_order_id is unique — the create-order
call is idempotent per (tenant, kind, "still pending") via the service
layer; the webhook's OWN idempotency additionally keys off
gateway_payment_id (a retried webhook for the same order/payment can never
double-post), matching the proven pattern in
app.engines.payment.service.process_payment_webhook.
"""
from __future__ import annotations
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase

PAYMENT_KIND_DEPOSIT = "security_deposit"
PAYMENT_KIND_CREDIT = "credit_package"
PAYMENT_KIND_FUNDING = "activation_funding"
VALID_PAYMENT_KINDS = (PAYMENT_KIND_DEPOSIT, PAYMENT_KIND_CREDIT, PAYMENT_KIND_FUNDING)

STATUS_CREATED = "created"
STATUS_CAPTURED = "captured"
STATUS_FAILED = "failed"


class ActivationPaymentOrder(ServiceOSBase):
    __tablename__ = "activation_payment_orders"
    __table_args__ = (
        UniqueConstraint("gateway_order_id", name="uq_apo_gateway_order_id"),
        UniqueConstraint("gateway_payment_id", name="uq_apo_gateway_payment_id"),
        Index("ix_apo_tenant_id", "tenant_id"),
        Index("ix_apo_status", "status"),
    )

    tenant_id:          Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    vertical_id:        Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    payment_kind:       Mapped[str]             = mapped_column(String(30), nullable=False)
    gateway:            Mapped[str]             = mapped_column(String(20), nullable=False, default="razorpay")
    gateway_order_id:   Mapped[str]             = mapped_column(String(100), nullable=False)
    gateway_payment_id: Mapped[str | None]      = mapped_column(String(100), nullable=True)
    # Gross amount the order was created for (== required_deposit_amount, or
    # required_credit_amount incl. GST for credit_package).
    amount:             Mapped[Numeric]         = mapped_column(Numeric(12, 2), nullable=False)
    # For credit_package and activation_funding: the split actually posted on capture --
    # credited_amount goes to tenant_billing.credit_balance, tax_amount is
    # recorded as a separate FinancialEvent. Never blended.
    credited_amount:    Mapped[Numeric | None]  = mapped_column(Numeric(12, 2), nullable=True)
    tax_amount:         Mapped[Numeric | None]  = mapped_column(Numeric(12, 2), nullable=True)
    # ── Top-up plan snapshot (migration 317) ─────────────────────────────
    # What was bought, as priced at order time. Re-pricing or retiring the
    # plan later must never change what this tenant actually paid for, so the
    # seat count is frozen here rather than re-read from the plan at capture.
    topup_plan_id:      Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    seats_granted:      Mapped[int | None]      = mapped_column(Integer, nullable=True)

    currency:           Mapped[str]             = mapped_column(String(3), nullable=False, default="INR")
    status:             Mapped[str]             = mapped_column(String(20), nullable=False, default=STATUS_CREATED)
    policy_version:     Mapped[int | None]      = mapped_column(nullable=True)
    raw_order_payload:   Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    raw_webhook_payload: Mapped[dict | None]    = mapped_column(JSONB, nullable=True)
    captured_at:        Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        credited = Decimal(str(self.credited_amount or 0))
        tax = Decimal(str(self.tax_amount or 0))
        deposit_allocation = (
            Decimal(str(self.amount)) - credited - tax
            if self.payment_kind == PAYMENT_KIND_FUNDING else
            (Decimal(str(self.amount)) if self.payment_kind == PAYMENT_KIND_DEPOSIT else Decimal("0"))
        )
        return {
            "id": str(self.id), "tenant_id": str(self.tenant_id),
            "payment_kind": self.payment_kind, "gateway": self.gateway,
            "gateway_order_id": self.gateway_order_id,
            "gateway_payment_id": self.gateway_payment_id,
            "amount": float(self.amount),
            "credited_amount": float(self.credited_amount) if self.credited_amount is not None else None,
            "tax_amount": float(self.tax_amount) if self.tax_amount is not None else None,
            "deposit_amount": float(deposit_allocation),
            "topup_plan_id": str(self.topup_plan_id) if self.topup_plan_id else None,
            "seats_granted": self.seats_granted,
            "currency": self.currency, "status": self.status,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
