"""TENANT-HS-FINANCE-HUB-01 — Security-deposit refund request.

The only new table this feature introduces. Everything else the Finance
Hub renders (usage-credit wallet + ledger, credit top-up orders, held
security deposit, published finance policy, financial events, direct
customer-payment records) already exists and is composed, never forked.

State machine (spec section 12):
    draft -> submitted -> eligibility_review -> liability_review
          -> admin_decision -> processing -> refunded
    (any non-terminal state) -> rejected / withdrawn
    admin_decision <-> info_requested (admin asks, tenant responds)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ServiceOSBase

STATUS_DRAFT = "draft"
STATUS_SUBMITTED = "submitted"
STATUS_ELIGIBILITY_REVIEW = "eligibility_review"
STATUS_LIABILITY_REVIEW = "liability_review"
STATUS_ADMIN_DECISION = "admin_decision"
STATUS_INFO_REQUESTED = "info_requested"
STATUS_PROCESSING = "processing"
STATUS_REFUNDED = "refunded"
STATUS_REJECTED = "rejected"
STATUS_WITHDRAWN = "withdrawn"

TERMINAL_STATUSES = (STATUS_REFUNDED, STATUS_REJECTED, STATUS_WITHDRAWN)

# The ordered happy path the UI renders as a progress tracker.
WORKFLOW_STAGES = (
    STATUS_DRAFT, STATUS_SUBMITTED, STATUS_ELIGIBILITY_REVIEW,
    STATUS_LIABILITY_REVIEW, STATUS_ADMIN_DECISION, STATUS_PROCESSING,
    STATUS_REFUNDED,
)

STATUS_LABELS = {
    STATUS_DRAFT: "Draft",
    STATUS_SUBMITTED: "Submitted",
    STATUS_ELIGIBILITY_REVIEW: "Eligibility review",
    STATUS_LIABILITY_REVIEW: "Liability / hold review",
    STATUS_ADMIN_DECISION: "Admin decision",
    STATUS_INFO_REQUESTED: "Information requested",
    STATUS_PROCESSING: "Processing",
    STATUS_REFUNDED: "Refunded",
    STATUS_REJECTED: "Rejected",
    STATUS_WITHDRAWN: "Withdrawn",
}


class HsDepositRefundRequest(ServiceOSBase):
    __tablename__ = "hs_deposit_refund_requests"
    __table_args__ = (
        UniqueConstraint("request_ref", name="uq_hsdrr_request_ref"),
        Index("ix_hsdrr_tenant_id", "tenant_id"),
        Index("ix_hsdrr_status", "status"),
    )

    tenant_id:    Mapped[uuid.UUID]        = mapped_column(UUID(as_uuid=True), nullable=False)
    vertical_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    vertical_key: Mapped[str]              = mapped_column(String(50), nullable=False, default="home_services")
    request_ref:  Mapped[str]              = mapped_column(String(40), nullable=False)
    status:       Mapped[str]              = mapped_column(String(30), nullable=False, default=STATUS_DRAFT)

    requested_amount:                Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    approved_amount:                 Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    eligible_amount_snapshot:        Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    deposit_held_snapshot:           Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    deposit_required_snapshot:       Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    qualifying_technicians_snapshot: Mapped[int]     = mapped_column(Integer, nullable=False, default=0)
    policy_version:                  Mapped[int | None] = mapped_column(Integer, nullable=True)

    reason:                     Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_account_name:          Mapped[str | None] = mapped_column(String(160), nullable=True)
    bank_account_number_masked: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bank_ifsc:                  Mapped[str | None] = mapped_column(String(20), nullable=True)

    eligibility_checks: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    blockers:           Mapped[list | None] = mapped_column(JSONB, nullable=True)

    submitted_at:        Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    decision_at:         Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note:       Mapped[str | None]      = mapped_column(Text, nullable=True)
    info_requested_note: Mapped[str | None]      = mapped_column(Text, nullable=True)
    tenant_response:     Mapped[str | None]      = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at:         Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payout_reference:    Mapped[str | None]      = mapped_column(String(80), nullable=True)
    created_by_user_id:  Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "refund_request_id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "vertical_key": self.vertical_key,
            "request_ref": self.request_ref,
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, self.status),
            "workflow_stages": list(WORKFLOW_STAGES),
            "is_terminal": self.status in TERMINAL_STATUSES,
            "requested_amount": str(self.requested_amount),
            "approved_amount": str(self.approved_amount) if self.approved_amount is not None else None,
            "eligible_amount_snapshot": str(self.eligible_amount_snapshot),
            "deposit_held_snapshot": str(self.deposit_held_snapshot),
            "deposit_required_snapshot": str(self.deposit_required_snapshot),
            "qualifying_technicians_snapshot": self.qualifying_technicians_snapshot,
            "policy_version": self.policy_version,
            "reason": self.reason,
            "bank_account_name": self.bank_account_name,
            "bank_account_number_masked": self.bank_account_number_masked,
            "bank_ifsc": self.bank_ifsc,
            "eligibility_checks": self.eligibility_checks or {},
            "blockers": self.blockers or [],
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "decision_at": self.decision_at.isoformat() if self.decision_at else None,
            "decision_note": self.decision_note,
            "info_requested_note": self.info_requested_note,
            "tenant_response": self.tenant_response,
            "refunded_at": self.refunded_at.isoformat() if self.refunded_at else None,
            "payout_reference": self.payout_reference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
