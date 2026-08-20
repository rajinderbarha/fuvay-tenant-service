"""Finance Hub Engine — Models.

The one genuinely new table this module needs. Everything else (wallets, deposits,
warranty claims, payouts) already exists in platform_commerce/payment and is
composed by FinanceHubService, not duplicated here.
"""
import uuid
from decimal import Decimal

from sqlalchemy import DateTime, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase


class CreditTopupOrder(ServiceOSBase):
    """Tracks the full lifecycle of a credit top-up purchase: initiated -> credited/failed.

    WalletTransaction (platform_commerce) is append-only and only ever records
    *successful* credits, so it cannot represent initiated/failed/cancelled attempts.
    This table is the source of truth for the Credit Top-ups admin module.
    """
    __tablename__ = "credit_topup_orders"
    __table_args__ = (
        Index("ix_cto_tenant_id", "tenant_id"),
        Index("ix_cto_payment_status", "payment_status"),
        Index("ix_cto_order_ref", "order_ref"),
        Index("ix_cto_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_cto_status_created_at", "payment_status", "created_at"),
    )

    tenant_id:            Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), nullable=False)
    credit_package_id:    Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    order_ref:            Mapped[str | None]      = mapped_column(String(60), nullable=True)
    credits_purchased:    Mapped[Decimal]         = mapped_column(Numeric(14, 4), default=Decimal("0"), nullable=False)
    bonus_credits:        Mapped[Decimal]         = mapped_column(Numeric(14, 4), default=Decimal("0"), nullable=False)
    amount_paid:          Mapped[Decimal]         = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    currency:             Mapped[str]             = mapped_column(String(10), default="INR", nullable=False)
    payment_method:       Mapped[str | None]      = mapped_column(String(30), nullable=True)
    # payment_status: initiated | paid_pending_credit | credited | failed | cancelled | refunded | partially_refunded
    payment_status:       Mapped[str]             = mapped_column(String(30), default="initiated", nullable=False)
    # wallet_credit_status: pending | credited | failed
    wallet_credit_status: Mapped[str]             = mapped_column(String(20), default="pending", nullable=False)
    wallet_transaction_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    gateway_order_id:     Mapped[str | None]      = mapped_column(String(100), nullable=True)
    gateway_payment_id:   Mapped[str | None]      = mapped_column(String(100), nullable=True)
    failure_reason:       Mapped[str | None]      = mapped_column(String(500), nullable=True)
    refunded_amount:      Mapped[Decimal | None]  = mapped_column(Numeric(12, 2), nullable=True)
    # FINAL-L5-05K: the canonical Usage Credit Ledger event this top-up's
    # grant is recorded under (app.engines.usage_credits). wallet_transaction_id
    # above is legacy/historical only -- new grants no longer populate it.
    usage_credit_ledger_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "topup_id":             str(self.id),
            "tenant_id":            str(self.tenant_id),
            "credit_package_id":    str(self.credit_package_id) if self.credit_package_id else None,
            "order_ref":            self.order_ref,
            "credits_purchased":    float(self.credits_purchased),
            "bonus_credits":        float(self.bonus_credits),
            "amount_paid":          float(self.amount_paid),
            "currency":             self.currency,
            "payment_method":       self.payment_method,
            "payment_status":       self.payment_status,
            "wallet_credit_status": self.wallet_credit_status,
            "wallet_transaction_id":str(self.wallet_transaction_id) if self.wallet_transaction_id else None,
            "usage_credit_ledger_event_id": str(self.usage_credit_ledger_event_id) if self.usage_credit_ledger_event_id else None,
            "gateway_order_id":     self.gateway_order_id,
            "gateway_payment_id":   self.gateway_payment_id,
            "failure_reason":       self.failure_reason,
            "refunded_amount":      float(self.refunded_amount) if self.refunded_amount is not None else None,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
        }
