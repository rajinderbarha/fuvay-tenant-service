"""Customer Service Credit + Dispute Settlement models — migration 080."""
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import String, Numeric, Boolean, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class FinanceVerticalConfig(Base):
    __tablename__ = "finance_vertical_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vertical_type: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    payment_collection_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    tenant_payouts_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    customer_service_credits_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tenant_wallet_deduction_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    manual_customer_refund_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config_notes: Mapped[str | None] = mapped_column(Text)
    updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id), "vertical_type": self.vertical_type,
            "payment_collection_enabled": self.payment_collection_enabled,
            "tenant_payouts_enabled": self.tenant_payouts_enabled,
            "customer_service_credits_enabled": self.customer_service_credits_enabled,
            "tenant_wallet_deduction_enabled": self.tenant_wallet_deduction_enabled,
            "manual_customer_refund_enabled": self.manual_customer_refund_enabled,
            "config_notes": self.config_notes,
        }


class CustomerServiceCredit(Base):
    __tablename__ = "customer_service_credits"
    __table_args__ = (
        Index("ix_csc_customer", "customer_id"),
        Index("ix_csc_tenant", "tenant_id"),
        Index("ix_csc_dispute", "dispute_id"),
        Index("ix_csc_status", "status"),
        Index("ix_csc_settlement", "settlement_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credit_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    dispute_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    settlement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    credit_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active")
    issued_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    issued_reason: Mapped[str] = mapped_column(Text, nullable=False)
    customer_message: Mapped[str | None] = mapped_column(Text)
    internal_note: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "credit_number": self.credit_number,
            "customer_id": str(self.customer_id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "booking_id": str(self.booking_id) if self.booking_id else None,
            "job_id": str(self.job_id) if self.job_id else None,
            "dispute_id": str(self.dispute_id) if self.dispute_id else None,
            "settlement_id": str(self.settlement_id) if self.settlement_id else None,
            "amount": float(self.amount),
            "remaining_amount": float(self.remaining_amount),
            "currency": self.currency,
            "credit_type": self.credit_type,
            "source": self.source,
            "status": self.status,
            "issued_reason": self.issued_reason,
            "customer_message": self.customer_message,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "used_at": self.used_at.isoformat() if self.used_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancel_reason": self.cancel_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CustomerCreditLedger(Base):
    __tablename__ = "customer_credit_ledger"
    __table_args__ = (
        Index("ix_ccl_credit", "customer_credit_id"),
        Index("ix_ccl_customer", "customer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_credit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "customer_credit_id": str(self.customer_credit_id),
            "customer_id": str(self.customer_id),
            "booking_id": str(self.booking_id) if self.booking_id else None,
            "transaction_type": self.transaction_type,
            "amount": float(self.amount),
            "balance_after": float(self.balance_after),
            "description": self.description,
            "reference_type": self.reference_type,
            "reference_id": str(self.reference_id) if self.reference_id else None,
            "created_at": self.created_at.isoformat(),
        }


class DisputeSettlement(Base):
    __tablename__ = "dispute_settlements"
    __table_args__ = (
        Index("ix_ds_dispute", "dispute_id"),
        Index("ix_ds_customer", "customer_id"),
        Index("ix_ds_tenant", "tenant_id"),
        Index("ix_ds_status", "settlement_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    settlement_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    dispute_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    settlement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    settlement_status: Mapped[str] = mapped_column(String(30), default="draft")
    settlement_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    deduction_source: Mapped[str] = mapped_column(String(50), default="tenant_wallet")
    tenant_wallet_deduction_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    platform_goodwill_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    customer_credit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    tenant_penalty_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    admin_decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    customer_message: Mapped[str | None] = mapped_column(Text)
    tenant_message: Mapped[str | None] = mapped_column(Text)
    internal_note: Mapped[str | None] = mapped_column(Text)
    created_by_admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    approved_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    executed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "settlement_number": self.settlement_number,
            "dispute_id": str(self.dispute_id),
            "booking_id": str(self.booking_id) if self.booking_id else None,
            "customer_id": str(self.customer_id),
            "tenant_id": str(self.tenant_id),
            "settlement_type": self.settlement_type,
            "settlement_status": self.settlement_status,
            "settlement_amount": float(self.settlement_amount),
            "currency": self.currency,
            "deduction_source": self.deduction_source,
            "tenant_wallet_deduction_amount": float(self.tenant_wallet_deduction_amount),
            "platform_goodwill_amount": float(self.platform_goodwill_amount),
            "customer_credit_id": str(self.customer_credit_id) if self.customer_credit_id else None,
            "tenant_penalty_id": str(self.tenant_penalty_id) if self.tenant_penalty_id else None,
            "admin_decision_reason": self.admin_decision_reason,
            "customer_message": self.customer_message,
            "tenant_message": self.tenant_message,
            "internal_note": self.internal_note,
            "created_by_admin_id": str(self.created_by_admin_id),
            "approved_by_admin_id": str(self.approved_by_admin_id) if self.approved_by_admin_id else None,
            "executed_by_admin_id": str(self.executed_by_admin_id) if self.executed_by_admin_id else None,
            "created_at": self.created_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
        }


class TenantPenalty(Base):
    __tablename__ = "tenant_penalties"
    __table_args__ = (
        Index("ix_tp_tenant", "tenant_id"),
        Index("ix_tp_status", "status"),
        Index("ix_tp_settlement", "settlement_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    penalty_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    dispute_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    settlement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    penalty_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "penalty_number": self.penalty_number,
            "tenant_id": str(self.tenant_id),
            "dispute_id": str(self.dispute_id) if self.dispute_id else None,
            "settlement_id": str(self.settlement_id) if self.settlement_id else None,
            "penalty_type": self.penalty_type,
            "amount": float(self.amount),
            "currency": self.currency,
            "source": self.source,
            "status": self.status,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }


# SecurityDepositAdjustment was removed in migration 318 along with the
# deposit it adjusted. A dispute settlement now draws from
# tenant_billing.credit_balance alone -- and is allowed to take it
# negative, which recovers the full amount instead of stopping at
# whatever collateral happened to be held.


class FinanceAuditLog(Base):
    __tablename__ = "finance_audit_logs"
    __table_args__ = (
        Index("ix_fal_event", "event_type"),
        Index("ix_fal_tenant", "tenant_id"),
        Index("ix_fal_customer", "customer_id"),
        Index("ix_fal_settlement", "settlement_id"),
        Index("ix_fal_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_role: Mapped[str | None] = mapped_column(String(40))
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    booking_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    dispute_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    settlement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    reason: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(100))
    ip_hash: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "actor_role": self.actor_role,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "settlement_id": str(self.settlement_id) if self.settlement_id else None,
            "amount": float(self.amount) if self.amount else None,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
        }
