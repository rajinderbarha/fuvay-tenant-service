"""Dispute Settlement + Customer Service Credit — core service.

Business rule: Home Services customers pay tenant directly on-site.
Platform does NOT collect the original payment. Therefore:
- Platform issues ServiceOS service credit (not cash) after disputes.
- Platform recovers from tenant wallet first, then security deposit.
- No silent deductions — every deduction creates an audit trail.
"""
import uuid
import random
import string
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.customer_credits.models import (
    CustomerServiceCredit, CustomerCreditLedger,
    DisputeSettlement, TenantPenalty,
    SecurityDepositAdjustment, FinanceAuditLog,
    FinanceVerticalConfig,
)
from app.engines.platform_commerce.models import (
    TenantWallet, WalletTransaction,
    SecurityDeposit, SecurityDepositTransaction,
)
from app.engines.complaints.models import CustomerComplaint
from app.engines.booking.models import Booking
from app.exceptions import ServiceOSException, NotFoundException

log = structlog.get_logger("customer_credits.service")

VALID_SETTLEMENT_TYPES = {
    "customer_service_credit", "tenant_revisit", "tenant_direct_refund",
    "no_compensation", "platform_goodwill_credit", "manual_customer_refund_exception",
}
VALID_DEDUCTION_STRATEGIES = {
    "tenant_wallet", "security_deposit",
    "tenant_wallet_then_security_deposit",
    "platform_goodwill", "none",
}
CREDIT_EXPIRY_DAYS = 180  # 6 months default


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _gen_number(prefix: str, length: int = 8) -> str:
    chars = string.digits + string.ascii_uppercase
    return prefix + "-" + "".join(random.choices(chars, k=length))


def _two(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_DOWN)


class DisputeSettlementService:
    """Manages the full dispute settlement flow — create, approve, execute, cancel."""

    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None,
                 actor_role: str = "super_admin", request_id: str = "—"):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_wallet(self, tenant_id: uuid.UUID) -> TenantWallet | None:
        return await self.db.scalar(
            select(TenantWallet).where(TenantWallet.tenant_id == tenant_id))

    async def _get_deposit(self, tenant_id: uuid.UUID) -> SecurityDeposit | None:
        return await self.db.scalar(
            select(SecurityDeposit).where(SecurityDeposit.tenant_id == tenant_id))

    async def _get_settlement(self, settlement_id: uuid.UUID) -> DisputeSettlement:
        s = await self.db.scalar(
            select(DisputeSettlement).where(DisputeSettlement.id == settlement_id))
        if not s:
            raise ServiceOSException("NOT_FOUND", f"Settlement {settlement_id} not found.")
        return s

    def _audit(self, event_type: str, **kwargs) -> None:
        self.db.add(FinanceAuditLog(
            event_type=event_type,
            actor_user_id=self.actor_id,
            actor_role=self.actor_role,
            request_id=self.request_id,
            created_at=_utcnow(),
            **kwargs,
        ))

    # ── Preview deduction ─────────────────────────────────────────────────────

    async def preview_deduction(self, tenant_id: uuid.UUID,
                                 amount: Decimal, strategy: str) -> dict:
        """Calculate how much comes from wallet vs security deposit."""
        wallet = await self._get_wallet(tenant_id)
        deposit = await self._get_deposit(tenant_id)

        wallet_balance = _two(wallet.credit_balance if wallet else Decimal("0"))
        deposit_balance = _two(deposit.current_balance if deposit else Decimal("0"))
        deposit_total_paid = _two(deposit.total_paid + (deposit.replenishment_total or Decimal("0"))
                                   if deposit else Decimal("0"))

        wallet_deduct = Decimal("0")
        deposit_deduct = Decimal("0")
        goodwill_amount = Decimal("0")
        remaining = amount

        if strategy == "tenant_wallet":
            wallet_deduct = min(remaining, wallet_balance)
            remaining -= wallet_deduct
        elif strategy == "security_deposit":
            deposit_deduct = min(remaining, deposit_balance)
            remaining -= deposit_deduct
        elif strategy == "tenant_wallet_then_security_deposit":
            wallet_deduct = min(remaining, wallet_balance)
            remaining -= wallet_deduct
            if remaining > Decimal("0"):
                deposit_deduct = min(remaining, deposit_balance)
                remaining -= deposit_deduct
        elif strategy == "platform_goodwill":
            goodwill_amount = amount
            remaining = Decimal("0")
        elif strategy == "none":
            remaining = Decimal("0")  # no_compensation settlement

        can_fully_cover = remaining == Decimal("0")

        return {
            "tenant_id": str(tenant_id),
            "settlement_amount": float(amount),
            "strategy": strategy,
            "wallet_balance": float(wallet_balance),
            "wallet_deduction": float(wallet_deduct),
            "wallet_balance_after": float(wallet_balance - wallet_deduct),
            "deposit_held": float(deposit_total_paid),
            "deposit_available": float(deposit_balance),
            "deposit_deduction": float(deposit_deduct),
            "deposit_remaining": float(deposit_balance - deposit_deduct),
            "platform_goodwill_amount": float(goodwill_amount),
            "uncovered_amount": float(remaining),
            "can_fully_cover": can_fully_cover,
            "finance_status_after": "blocked" if remaining > Decimal("0") else "normal",
        }

    # ── Create settlement ─────────────────────────────────────────────────────

    async def create_settlement(self, dispute_id: uuid.UUID, data: dict) -> dict:
        complaint = await self.db.scalar(
            select(CustomerComplaint).where(CustomerComplaint.id == dispute_id))
        if not complaint:
            raise ServiceOSException("NOT_FOUND", f"Dispute {dispute_id} not found.")

        settlement_type = data.get("settlement_type", "")
        if settlement_type not in VALID_SETTLEMENT_TYPES:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                f"settlement_type must be one of: {sorted(VALID_SETTLEMENT_TYPES)}")

        strategy = data.get("deduction_strategy", "tenant_wallet_then_security_deposit")
        if strategy not in VALID_DEDUCTION_STRATEGIES:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                f"deduction_strategy must be one of: {sorted(VALID_DEDUCTION_STRATEGIES)}")

        amount = _two(Decimal(str(data.get("settlement_amount", 0))))
        if amount < Decimal("0"):
            raise ServiceOSException("VALIDATION_ERROR", "settlement_amount must be >= 0.")

        # Cannot execute twice
        existing = await self.db.scalar(
            select(DisputeSettlement).where(
                DisputeSettlement.dispute_id == dispute_id,
                DisputeSettlement.settlement_status.not_in(["cancelled", "reversed"])))
        if existing:
            raise ServiceOSException(
                "DUPLICATE_SETTLEMENT",
                f"An active settlement already exists for this dispute.",
                context={"existing_settlement_id": str(existing.id)})

        # Compute preview
        tenant_id = uuid.UUID(str(complaint.tenant_id))
        preview = await self.preview_deduction(tenant_id, amount, strategy)

        settlement = DisputeSettlement(
            settlement_number=_gen_number("DS"),
            dispute_id=dispute_id,
            booking_id=uuid.UUID(str(complaint.booking_id)) if complaint.booking_id else None,
            customer_id=uuid.UUID(str(complaint.customer_id)),
            tenant_id=tenant_id,
            settlement_type=settlement_type,
            settlement_status="draft",
            settlement_amount=amount,
            currency=data.get("currency", "INR"),
            deduction_source=strategy,
            tenant_wallet_deduction_amount=Decimal(str(preview["wallet_deduction"])),
            security_deposit_deduction_amount=Decimal(str(preview["deposit_deduction"])),
            platform_goodwill_amount=Decimal(str(preview["platform_goodwill_amount"])),
            admin_decision_reason=data.get("admin_decision_reason", ""),
            customer_message=data.get("customer_message"),
            tenant_message=data.get("tenant_message"),
            internal_note=data.get("internal_note"),
            created_by_admin_id=self.actor_id,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.db.add(settlement)
        await self.db.flush()

        self._audit("dispute.settlement_created",
                    dispute_id=dispute_id,
                    settlement_id=settlement.id,
                    customer_id=settlement.customer_id,
                    tenant_id=tenant_id,
                    amount=amount,
                    reason=data.get("admin_decision_reason", ""))

        await self.db.commit()

        result = settlement.to_dict()
        result["deduction_preview"] = preview
        return result

    # ── Approve settlement ────────────────────────────────────────────────────

    async def approve_settlement(self, settlement_id: uuid.UUID) -> dict:
        s = await self._get_settlement(settlement_id)
        if s.settlement_status not in ("draft", "pending_approval"):
            raise ServiceOSException(
                "INVALID_STATE",
                f"Cannot approve settlement with status '{s.settlement_status}'.")

        s.settlement_status = "approved"
        s.approved_by_admin_id = self.actor_id
        s.approved_at = _utcnow()
        s.updated_at = _utcnow()

        self._audit("dispute.settlement_approved",
                    settlement_id=settlement_id,
                    dispute_id=s.dispute_id,
                    tenant_id=s.tenant_id,
                    customer_id=s.customer_id,
                    amount=s.settlement_amount,
                    reason="Admin approved settlement")
        await self.db.commit()
        return s.to_dict()

    # ── Execute settlement ────────────────────────────────────────────────────

    async def execute_settlement(self, settlement_id: uuid.UUID) -> dict:
        s = await self._get_settlement(settlement_id)
        if s.settlement_status == "executed":
            raise ServiceOSException("ALREADY_EXECUTED", "Settlement has already been executed.")
        if s.settlement_status not in ("approved",):
            raise ServiceOSException(
                "INVALID_STATE",
                f"Settlement must be approved before execution (status: {s.settlement_status}).")

        s.settlement_status = "executing"
        s.updated_at = _utcnow()

        tenant_id = s.tenant_id
        customer_id = s.customer_id
        total = s.settlement_amount

        # Re-compute deduction amounts at execution time
        preview = await self.preview_deduction(tenant_id, total, s.deduction_source)
        wallet_deduct  = _two(Decimal(str(preview["wallet_deduction"])))
        deposit_deduct = _two(Decimal(str(preview["deposit_deduction"])))
        goodwill_amt   = _two(Decimal(str(preview["platform_goodwill_amount"])))

        # ── Step 1: Deduct tenant wallet ──────────────────────────────────────
        if wallet_deduct > Decimal("0"):
            wallet = await self._get_wallet(tenant_id)
            if not wallet or wallet.credit_balance < wallet_deduct:
                actual_deduct = _two(wallet.credit_balance if wallet else Decimal("0"))
            else:
                actual_deduct = wallet_deduct

            if wallet and actual_deduct > Decimal("0"):
                bal_before = wallet.credit_balance
                wallet.credit_balance -= actual_deduct
                wallet.last_transaction_at = _utcnow()
                self.db.add(WalletTransaction(
                    tenant_id=tenant_id,
                    txn_type="manual_deduct",
                    amount=-actual_deduct,
                    balance_before=bal_before,
                    balance_after=wallet.credit_balance,
                    reference_id=str(settlement_id),
                    reference_type="dispute_settlement",
                    idempotency_key=f"ds_wallet_{settlement_id}",
                    description=(
                        f"Dispute settlement deduction — {s.settlement_number}. "
                        "ServiceOS platform does not collect direct payments for Home Services; "
                        "this amount is deducted to fund customer service credit."
                    ),
                    actor_id=self.actor_id,
                    meta={"settlement_number": s.settlement_number,
                          "dispute_id": str(s.dispute_id)},
                ))
                s.tenant_wallet_deduction_amount = actual_deduct
                self._audit("tenant_wallet.deducted_for_dispute",
                            tenant_id=tenant_id, settlement_id=settlement_id,
                            dispute_id=s.dispute_id, amount=actual_deduct,
                            reason=f"Wallet deduction for dispute settlement {s.settlement_number}")
            elif wallet_deduct > (wallet.credit_balance if wallet else Decimal("0")):
                wallet_deduct = wallet.credit_balance if wallet else Decimal("0")
                s.tenant_wallet_deduction_amount = wallet_deduct

        # ── Step 2: Deduct security deposit if needed ─────────────────────────
        if deposit_deduct > Decimal("0"):
            deposit = await self._get_deposit(tenant_id)
            if deposit and deposit.current_balance >= deposit_deduct:
                bal_before = deposit.current_balance
                deposit.warranty_drawn = (deposit.warranty_drawn or Decimal("0")) + deposit_deduct
                self.db.add(SecurityDepositTransaction(
                    deposit_id=deposit.id,
                    tenant_id=tenant_id,
                    txn_type="admin_adjustment",
                    amount=-deposit_deduct,
                    balance_before=bal_before,
                    balance_after=deposit.current_balance,
                    reference_id=str(settlement_id),
                    notes=(f"Dispute settlement {s.settlement_number} — deposit deduction "
                           "because tenant wallet balance was insufficient."),
                    actor_id=self.actor_id,
                ))
                sda = SecurityDepositAdjustment(
                    tenant_id=tenant_id,
                    settlement_id=settlement_id,
                    dispute_id=s.dispute_id,
                    adjustment_type="deduct_for_customer_credit",
                    amount=deposit_deduct,
                    currency=s.currency,
                    reason=(f"Deposit deduction for dispute settlement {s.settlement_number}. "
                            "Tenant wallet insufficient."),
                    status="executed",
                    approved_by_admin_id=self.actor_id,
                    created_at=_utcnow(),
                    approved_at=_utcnow(),
                    executed_at=_utcnow(),
                )
                self.db.add(sda)
                s.security_deposit_deduction_amount = deposit_deduct
                self._audit("security_deposit.adjusted_for_dispute",
                            tenant_id=tenant_id, settlement_id=settlement_id,
                            dispute_id=s.dispute_id, amount=deposit_deduct,
                            reason="Security deposit deduction for dispute settlement")
            else:
                deposit_deduct = Decimal("0")
                s.security_deposit_deduction_amount = Decimal("0")

        s.platform_goodwill_amount = goodwill_amt

        # ── Step 3: Issue customer service credit ─────────────────────────────
        credit_amount = total
        credit = CustomerServiceCredit(
            credit_number=_gen_number("CSC"),
            customer_id=customer_id,
            tenant_id=tenant_id,
            booking_id=s.booking_id,
            dispute_id=s.dispute_id,
            settlement_id=settlement_id,
            amount=credit_amount,
            remaining_amount=credit_amount,
            currency=s.currency,
            credit_type="dispute_compensation",
            source=(
                "platform_goodwill" if s.deduction_source == "platform_goodwill"
                else "dispute_settlement"
            ),
            status="active",
            issued_by_admin_id=self.actor_id,
            issued_reason=s.admin_decision_reason,
            customer_message=s.customer_message or (
                f"We have issued ₹{float(credit_amount):,.0f} ServiceOS credit to your account "
                "for dispute settlement. You can use it on your next booking."),
            valid_from=_utcnow(),
            expires_at=_utcnow() + timedelta(days=CREDIT_EXPIRY_DAYS),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.db.add(credit)
        await self.db.flush()

        # Ledger entry
        ledger = CustomerCreditLedger(
            customer_credit_id=credit.id,
            customer_id=customer_id,
            transaction_type="issued",
            amount=credit_amount,
            balance_after=credit_amount,
            description=(f"ServiceOS credit issued — dispute settlement {s.settlement_number}. "
                         "This is platform service credit, not a cash refund."),
            reference_type="dispute_settlement",
            reference_id=settlement_id,
            created_at=_utcnow(),
        )
        self.db.add(ledger)

        # ── Step 4: Create tenant penalty ─────────────────────────────────────
        penalty = TenantPenalty(
            penalty_number=_gen_number("TP"),
            tenant_id=tenant_id,
            booking_id=s.booking_id,
            dispute_id=s.dispute_id,
            settlement_id=settlement_id,
            penalty_type="dispute_settlement_deduction",
            amount=wallet_deduct + deposit_deduct,
            currency=s.currency,
            source=(
                "tenant_wallet_and_security_deposit" if deposit_deduct > Decimal("0") else
                "tenant_wallet"
            ),
            status="applied",
            reason=(s.tenant_message or
                    f"₹{float(total):,.0f} deducted due to dispute settlement {s.settlement_number}."),
            created_by_admin_id=self.actor_id,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.db.add(penalty)
        await self.db.flush()

        # ── Step 5: Link credit + penalty to settlement ───────────────────────
        s.customer_credit_id = credit.id
        s.tenant_penalty_id = penalty.id
        s.settlement_status = "executed"
        s.executed_by_admin_id = self.actor_id
        s.executed_at = _utcnow()
        s.updated_at = _utcnow()

        # ── Step 6: Update complaint settlement_status ────────────────────────
        complaint = await self.db.scalar(
            select(CustomerComplaint).where(CustomerComplaint.id == s.dispute_id))
        if complaint:
            complaint.settlement_status = "settled"

        # ── Step 7: Final audit logs ──────────────────────────────────────────
        self._audit("dispute.settlement_executed",
                    dispute_id=s.dispute_id, settlement_id=settlement_id,
                    customer_id=customer_id, tenant_id=tenant_id,
                    amount=total,
                    reason=f"Settlement executed: {s.settlement_number}",
                    metadata_json={"credit_number": credit.credit_number,
                                   "penalty_number": penalty.penalty_number})
        self._audit("customer_credit.issued",
                    customer_id=customer_id, tenant_id=tenant_id,
                    settlement_id=settlement_id,
                    amount=credit_amount,
                    reason=credit.issued_reason,
                    metadata_json={"credit_number": credit.credit_number})
        self._audit("tenant_penalty.applied",
                    tenant_id=tenant_id,
                    settlement_id=settlement_id,
                    dispute_id=s.dispute_id,
                    amount=penalty.amount,
                    reason=penalty.reason)

        await self.db.commit()

        return {
            **s.to_dict(),
            "credit": credit.to_dict(),
            "penalty": penalty.to_dict(),
            "deduction_summary": {
                "wallet_deducted": float(s.tenant_wallet_deduction_amount),
                "deposit_deducted": float(s.security_deposit_deduction_amount),
                "goodwill_amount": float(s.platform_goodwill_amount),
                "customer_credit_issued": float(credit_amount),
                "credit_number": credit.credit_number,
            },
        }

    # ── Cancel settlement ─────────────────────────────────────────────────────

    async def cancel_settlement(self, settlement_id: uuid.UUID, reason: str) -> dict:
        s = await self._get_settlement(settlement_id)
        if s.settlement_status == "executed":
            raise ServiceOSException(
                "INVALID_STATE", "Cannot cancel an executed settlement. Use reversal.")
        s.settlement_status = "cancelled"
        s.cancelled_at = _utcnow()
        s.updated_at = _utcnow()
        self._audit("dispute.settlement_cancelled",
                    settlement_id=settlement_id, dispute_id=s.dispute_id,
                    tenant_id=s.tenant_id, customer_id=s.customer_id,
                    reason=reason)
        await self.db.commit()
        return s.to_dict()

    # ── List settlements ──────────────────────────────────────────────────────

    async def list_settlements(self, page: int = 1, limit: int = 50,
                                status: str | None = None,
                                tenant_id: uuid.UUID | None = None,
                                customer_id: uuid.UUID | None = None) -> dict:
        stmt = select(DisputeSettlement).order_by(DisputeSettlement.created_at.desc())
        if status:
            stmt = stmt.where(DisputeSettlement.settlement_status == status)
        if tenant_id:
            stmt = stmt.where(DisputeSettlement.tenant_id == tenant_id)
        if customer_id:
            stmt = stmt.where(DisputeSettlement.customer_id == customer_id)

        total = await self.db.scalar(
            select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
        return {
            "settlements": [s.to_dict() for s in rows],
            "meta": {"total": total or 0, "page": page, "limit": limit,
                     "total_pages": max(1, ((total or 0) + limit - 1) // limit)},
        }

    async def get_settlement_summary(self) -> dict:
        total = await self.db.scalar(select(func.count()).select_from(DisputeSettlement))
        pending = await self.db.scalar(
            select(func.count()).select_from(DisputeSettlement).where(
                DisputeSettlement.settlement_status.in_(["draft", "pending_approval", "approved"])))
        executed = await self.db.scalar(
            select(func.count()).select_from(DisputeSettlement).where(
                DisputeSettlement.settlement_status == "executed"))
        failed = await self.db.scalar(
            select(func.count()).select_from(DisputeSettlement).where(
                DisputeSettlement.settlement_status.in_(["failed", "cancelled"])))

        credits_total = await self.db.scalar(
            select(func.sum(DisputeSettlement.settlement_amount)).where(
                DisputeSettlement.settlement_status == "executed",
                DisputeSettlement.settlement_type == "customer_service_credit"))
        wallet_total = await self.db.scalar(
            select(func.sum(DisputeSettlement.tenant_wallet_deduction_amount)).where(
                DisputeSettlement.settlement_status == "executed"))
        deposit_total = await self.db.scalar(
            select(func.sum(DisputeSettlement.security_deposit_deduction_amount)).where(
                DisputeSettlement.settlement_status == "executed"))

        return {
            "total_settlements": total or 0,
            "pending_approval": pending or 0,
            "executed_settlements": executed or 0,
            "failed_cancelled": failed or 0,
            "customer_credits_issued": float(credits_total or 0),
            "tenant_wallet_deducted": float(wallet_total or 0),
            "security_deposit_deducted": float(deposit_total or 0),
        }


class CustomerCreditService:
    """Manages customer service credit lifecycle."""

    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None,
                 actor_role: str = "customer", request_id: str = "—"):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id

    def _audit(self, event_type: str, **kwargs) -> None:
        self.db.add(FinanceAuditLog(
            event_type=event_type,
            actor_user_id=self.actor_id,
            actor_role=self.actor_role,
            request_id=self.request_id,
            created_at=_utcnow(),
            **kwargs,
        ))

    # ── Issue manual credit (admin) ────────────────────────────────────────

    async def issue_credit_manual(self, customer_id: uuid.UUID, data: dict) -> dict:
        amount = _two(Decimal(str(data.get("amount", 0))))
        if amount <= Decimal("0"):
            raise ServiceOSException("VALIDATION_ERROR", "amount must be > 0.")

        credit = CustomerServiceCredit(
            credit_number=_gen_number("CSC"),
            customer_id=customer_id,
            amount=amount,
            remaining_amount=amount,
            currency=data.get("currency", "INR"),
            credit_type=data.get("credit_type", "platform_goodwill"),
            source="manual_admin_credit",
            status="active",
            issued_by_admin_id=self.actor_id,
            issued_reason=data.get("issued_reason", ""),
            customer_message=data.get("customer_message"),
            valid_from=_utcnow(),
            expires_at=_utcnow() + timedelta(
                days=data.get("validity_days", CREDIT_EXPIRY_DAYS)),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.db.add(credit)
        await self.db.flush()

        self.db.add(CustomerCreditLedger(
            customer_credit_id=credit.id,
            customer_id=customer_id,
            transaction_type="issued",
            amount=amount,
            balance_after=amount,
            description=f"Manual admin credit — {credit.credit_number}",
            reference_type="admin_manual",
            created_at=_utcnow(),
        ))
        self._audit("customer_credit.issued",
                    customer_id=customer_id, amount=amount,
                    reason=credit.issued_reason,
                    metadata_json={"credit_number": credit.credit_number})
        await self.db.commit()
        return credit.to_dict()

    # ── Cancel credit ──────────────────────────────────────────────────────

    async def cancel_credit(self, credit_id: uuid.UUID, reason: str) -> dict:
        credit = await self.db.scalar(
            select(CustomerServiceCredit).where(CustomerServiceCredit.id == credit_id))
        if not credit:
            raise ServiceOSException("NOT_FOUND", "Credit not found.")
        if credit.status in ("cancelled", "expired", "reversed"):
            raise ServiceOSException("INVALID_STATE",
                f"Credit already {credit.status}.")

        credit.status = "cancelled"
        credit.cancelled_at = _utcnow()
        credit.cancelled_by_admin_id = self.actor_id
        credit.cancel_reason = reason
        credit.updated_at = _utcnow()

        self._audit("customer_credit.cancelled",
                    customer_id=credit.customer_id, amount=credit.remaining_amount,
                    reason=reason,
                    metadata_json={"credit_number": credit.credit_number})
        await self.db.commit()
        return credit.to_dict()

    # ── Extend expiry ──────────────────────────────────────────────────────

    async def extend_credit_expiry(self, credit_id: uuid.UUID,
                                    new_expiry: datetime) -> dict:
        credit = await self.db.scalar(
            select(CustomerServiceCredit).where(CustomerServiceCredit.id == credit_id))
        if not credit:
            raise ServiceOSException("NOT_FOUND", "Credit not found.")
        if credit.status not in ("active", "partially_used"):
            raise ServiceOSException("INVALID_STATE",
                f"Cannot extend expiry for credit with status '{credit.status}'.")

        credit.expires_at = new_expiry
        credit.updated_at = _utcnow()
        self._audit("customer_credit.expiry_extended",
                    customer_id=credit.customer_id,
                    metadata_json={"credit_number": credit.credit_number,
                                   "new_expiry": new_expiry.isoformat()})
        await self.db.commit()
        return credit.to_dict()

    # ── List / get credits ─────────────────────────────────────────────────

    async def list_credits(self, customer_id: uuid.UUID | None = None,
                            status: str | None = None,
                            page: int = 1, limit: int = 50) -> dict:
        stmt = select(CustomerServiceCredit).order_by(CustomerServiceCredit.created_at.desc())
        if customer_id:
            stmt = stmt.where(CustomerServiceCredit.customer_id == customer_id)
        if status:
            stmt = stmt.where(CustomerServiceCredit.status == status)

        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()

        return {
            "credits": [c.to_dict() for c in rows],
            "meta": {"total": total or 0, "page": page, "limit": limit,
                     "total_pages": max(1, ((total or 0) + limit - 1) // limit)},
        }

    async def get_credit(self, credit_id: uuid.UUID,
                          customer_id: uuid.UUID | None = None) -> dict:
        credit = await self.db.scalar(
            select(CustomerServiceCredit).where(CustomerServiceCredit.id == credit_id))
        if not credit:
            raise ServiceOSException("NOT_FOUND", "Credit not found.")
        if customer_id and credit.customer_id != customer_id:
            raise ServiceOSException("NOT_FOUND", "Credit not found.")

        ledger = (await self.db.execute(
            select(CustomerCreditLedger)
            .where(CustomerCreditLedger.customer_credit_id == credit_id)
            .order_by(CustomerCreditLedger.created_at.desc()))).scalars().all()

        result = credit.to_dict()
        result["ledger"] = [e.to_dict() for e in ledger]
        return result

    async def get_credit_summary(self,
                                  customer_id: uuid.UUID | None = None) -> dict:
        def _count(status=None):
            s = select(func.count()).select_from(CustomerServiceCredit)
            if customer_id:
                s = s.where(CustomerServiceCredit.customer_id == customer_id)
            if status:
                s = s.where(CustomerServiceCredit.status == status)
            return s

        def _sum_field(field, status=None):
            s = select(func.sum(field))
            if customer_id:
                s = s.where(CustomerServiceCredit.customer_id == customer_id)
            if status:
                s = s.where(CustomerServiceCredit.status == status)
            return s

        total = await self.db.scalar(_count())
        active = await self.db.scalar(_count("active"))
        partially_used = await self.db.scalar(_count("partially_used"))
        used = await self.db.scalar(_count("used"))
        expired = await self.db.scalar(_count("expired"))
        cancelled = await self.db.scalar(_count("cancelled"))

        active_balance = await self.db.scalar(
            _sum_field(CustomerServiceCredit.remaining_amount).where(
                CustomerServiceCredit.status.in_(["active", "partially_used"])))
        from_disputes = await self.db.scalar(
            _count().where(CustomerServiceCredit.source == "dispute_settlement"))

        return {
            "total_credits": total or 0,
            "active_credits": (active or 0) + (partially_used or 0),
            "used_credits": used or 0,
            "expired_credits": expired or 0,
            "cancelled_credits": cancelled or 0,
            "active_credit_balance": float(active_balance or 0),
            "credits_from_disputes": from_disputes or 0,
        }

    # ── Apply credit to booking ────────────────────────────────────────────

    async def get_booking_credit_preview(self, customer_id: uuid.UUID,
                                          booking_amount: Decimal,
                                          credit_apply_amount: Decimal) -> dict:
        """Show how credit reduces payable-to-provider amount."""
        # Validate customer's active credit balance
        active_balance = await self.db.scalar(
            select(func.sum(CustomerServiceCredit.remaining_amount)).where(
                CustomerServiceCredit.customer_id == customer_id,
                CustomerServiceCredit.status.in_(["active", "partially_used"]),
                CustomerServiceCredit.valid_from <= _utcnow(),
            ).where(
                (CustomerServiceCredit.expires_at == None) |
                (CustomerServiceCredit.expires_at > _utcnow())
            ))
        active_balance = _two(active_balance or Decimal("0"))

        if credit_apply_amount > active_balance:
            credit_apply_amount = active_balance
        credit_applied = min(credit_apply_amount, booking_amount)
        if credit_applied < Decimal("0"):
            credit_applied = Decimal("0")
        payable = _two(booking_amount - credit_applied)

        return {
            "available_credit_balance": float(active_balance),
            "booking_amount": float(booking_amount),
            "credit_amount_to_apply": float(credit_apply_amount),
            "credit_applied": float(credit_applied),
            "payable_to_provider": float(payable),
            "remaining_credit_balance": float(active_balance - credit_applied),
        }

    async def apply_credit_to_booking(self, customer_id: uuid.UUID,
                                       booking_id: uuid.UUID,
                                       credit_apply_amount: Decimal,
                                       booking_amount: Decimal | None = None) -> dict:
        """Apply customer service credit to a booking, reducing payable-to-provider.

        booking_amount is NEVER trusted from the caller — the real Booking row is
        the sole source of truth for price (quoted_price), and the result is
        written back onto booking.credit_applied/payable_amount so downstream
        consumers (tenant, technician, invoice) see the correct collect-amount.
        """
        booking = (await self.db.execute(
            select(Booking).where(Booking.id == booking_id))).scalar_one_or_none()
        if not booking:
            raise NotFoundException("Booking", str(booking_id))
        if str(booking.customer_id) != str(customer_id):
            raise ServiceOSException("PERMISSION_DENIED", "This booking does not belong to you.")
        if booking.quoted_price is None:
            raise ServiceOSException("VALIDATION_ERROR", "Booking has no locked price yet.")
        booking_amount = booking.quoted_price

        if credit_apply_amount <= Decimal("0"):
            raise ServiceOSException("VALIDATION_ERROR", "credit_amount_to_apply must be > 0.")
        if credit_apply_amount > booking_amount:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                "Credit cannot exceed booking amount. Payable amount cannot be negative.")

        now = _utcnow()
        credits = (await self.db.execute(
            select(CustomerServiceCredit).where(
                CustomerServiceCredit.customer_id == customer_id,
                CustomerServiceCredit.status.in_(["active", "partially_used"]),
                CustomerServiceCredit.valid_from <= now,
            ).where(
                (CustomerServiceCredit.expires_at == None) |
                (CustomerServiceCredit.expires_at > now)
            ).order_by(CustomerServiceCredit.expires_at.asc().nullslast(),
                       CustomerServiceCredit.created_at.asc())
        )).scalars().all()

        remaining_to_apply = _two(credit_apply_amount)
        actually_applied = Decimal("0")

        for credit in credits:
            if remaining_to_apply <= Decimal("0"):
                break
            apply_from_this = min(remaining_to_apply, _two(credit.remaining_amount))
            if apply_from_this <= Decimal("0"):
                continue

            credit.remaining_amount -= apply_from_this
            credit.updated_at = now
            if credit.remaining_amount == Decimal("0"):
                credit.status = "used"
                credit.used_at = now
            else:
                credit.status = "partially_used"

            self.db.add(CustomerCreditLedger(
                customer_credit_id=credit.id,
                customer_id=customer_id,
                booking_id=booking_id,
                transaction_type="used" if credit.status == "used" else "partially_used",
                amount=-apply_from_this,
                balance_after=credit.remaining_amount,
                description=(f"ServiceOS credit applied to booking. "
                             f"Amount to collect from customer is reduced by ₹{float(apply_from_this):,.0f}."),
                reference_type="booking",
                reference_id=booking_id,
                created_at=now,
            ))
            self._audit("booking.customer_credit_applied",
                        customer_id=customer_id, booking_id=booking_id,
                        amount=apply_from_this,
                        metadata_json={"credit_number": credit.credit_number})

            remaining_to_apply -= apply_from_this
            actually_applied += apply_from_this

        payable = _two(booking_amount - actually_applied)
        booking.credit_applied = actually_applied
        booking.payable_amount = payable
        await self.db.commit()

        return {
            "success": True,
            "booking_id": str(booking_id),
            "original_amount": float(booking_amount),
            "credit_applied": float(actually_applied),
            "payable_to_provider": float(payable),
            "remaining_credit_balance": float(
                sum(_two(c.remaining_amount) for c in credits)),
        }

    # ── Tenant penalties ───────────────────────────────────────────────────

    async def list_penalties(self, tenant_id: uuid.UUID | None = None,
                              status: str | None = None,
                              page: int = 1, limit: int = 50) -> dict:
        stmt = select(TenantPenalty).order_by(TenantPenalty.created_at.desc())
        if tenant_id:
            stmt = stmt.where(TenantPenalty.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(TenantPenalty.status == status)

        total = await self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = (await self.db.execute(
            stmt.offset((page - 1) * limit).limit(limit))).scalars().all()
        return {
            "penalties": [p.to_dict() for p in rows],
            "meta": {"total": total or 0, "page": page, "limit": limit,
                     "total_pages": max(1, ((total or 0) + limit - 1) // limit)},
        }

    async def get_penalty_summary(self) -> dict:
        total = await self.db.scalar(select(func.count()).select_from(TenantPenalty))
        applied = await self.db.scalar(
            select(func.count()).select_from(TenantPenalty).where(
                TenantPenalty.status == "applied"))
        pending = await self.db.scalar(
            select(func.count()).select_from(TenantPenalty).where(
                TenantPenalty.status == "pending"))
        reversed_ = await self.db.scalar(
            select(func.count()).select_from(TenantPenalty).where(
                TenantPenalty.status == "reversed"))
        wallet_total = await self.db.scalar(
            select(func.sum(TenantPenalty.amount)).where(
                TenantPenalty.status == "applied",
                TenantPenalty.source.ilike("%wallet%")))
        deposit_total = await self.db.scalar(
            select(func.sum(TenantPenalty.amount)).where(
                TenantPenalty.status == "applied",
                TenantPenalty.source.ilike("%deposit%")))
        return {
            "total_penalties": total or 0,
            "applied_penalties": applied or 0,
            "pending_penalties": pending or 0,
            "reversed_penalties": reversed_ or 0,
            "wallet_deducted": float(wallet_total or 0),
            "deposit_deducted": float(deposit_total or 0),
        }

    # ── Finance Vertical Config ────────────────────────────────────────────

    async def get_vertical_config(self, vertical_type: str) -> dict:
        cfg = await self.db.scalar(
            select(FinanceVerticalConfig).where(
                FinanceVerticalConfig.vertical_type == vertical_type))
        if cfg:
            return cfg.to_dict()
        # Default: return home_services-safe defaults
        return {
            "vertical_type": vertical_type,
            "payment_collection_enabled": False,
            "tenant_payouts_enabled": False,
            "customer_service_credits_enabled": True,
            "tenant_wallet_deduction_enabled": True,
            "security_deposit_adjustment_enabled": True,
            "manual_customer_refund_enabled": False,
        }
