"""Dispute Settlement + Customer Service Credit — core service.

Business rule: Home Services customers pay tenant directly on-site.
Platform does NOT collect the original payment. Therefore:
- Platform issues ServiceOS service credit (not cash) after disputes.
- Platform recovers from tenant credit alone; the balance may go negative.
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
    FinanceAuditLog,
    FinanceVerticalConfig,
)
from app.engines.tenant_engine.models import TenantBilling, UsageCreditLedger
from app.engines.complaints.models import CustomerComplaint
from app.engines.booking.models import Booking
from app.exceptions import ServiceOSException, NotFoundException

log = structlog.get_logger("customer_credits.service")

VALID_SETTLEMENT_TYPES = {
    "customer_service_credit", "tenant_revisit", "tenant_direct_refund",
    "no_compensation", "platform_goodwill_credit", "manual_customer_refund_exception",
}
VALID_DEDUCTION_STRATEGIES = {
    "tenant_wallet",
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


async def issue_provider_funded_customer_credit(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    amount: Decimal,
    reference_type: str,
    reference_id: uuid.UUID,
    reason: str,
    actor_id: uuid.UUID | None,
    actor_role: str = "super_admin",
    request_id: str = "-",
    booking_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    currency: str = "INR",
) -> dict:
    """Issue service points funded by provider credit.

    The caller owns the transaction and must lock its claim/refund row first.
    No partial remedy is ever posted: both funding sources are locked and
    checked before any balance is changed.
    """
    amount = _two(Decimal(str(amount)))
    if amount <= 0:
        raise ServiceOSException("VALIDATION_ERROR", "Credit amount must be positive.", status_code=422)

    existing_ledger = await db.scalar(
        select(CustomerCreditLedger).where(
            CustomerCreditLedger.reference_type == reference_type,
            CustomerCreditLedger.reference_id == reference_id,
            CustomerCreditLedger.transaction_type == "issued",
        ).limit(1)
    )
    if existing_ledger:
        existing_credit = await db.get(CustomerServiceCredit, existing_ledger.customer_credit_id)
        return {
            "credit": existing_credit,
            "provider_credit_deducted": Decimal("0"),
            "idempotent_replay": True,
        }

    billing = await db.scalar(
        select(TenantBilling).where(TenantBilling.tenant_id == tenant_id).with_for_update()
    )
    usage_available = _two(Decimal(str(billing.credit_balance or 0))) if billing else Decimal("0")

    # The whole remedy comes out of provider credit, and it is allowed to take
    # the balance NEGATIVE. There is no security deposit to fall back on any
    # more (migration 318), and refusing the deduction would be worse than a
    # negative balance: the customer is owed this credit either way, and a
    # refusal would leave the platform funding it. A negative balance sits
    # below `credit_booking_floor`, which stops new bookings until the tenant
    # tops up, so the debt is collected rather than written off.
    usage_deduct = amount
    if usage_deduct > 0 and billing:
        before = _two(Decimal(str(billing.credit_balance or 0)))
        billing.credit_balance = before - usage_deduct
        db.add(UsageCreditLedger(
            tenant_id=tenant_id,
            job_id=job_id,
            booking_id=booking_id,
            event_type="customer_remedy_deduction",
            credit_delta=-usage_deduct,
            balance_before=before,
            balance_after=billing.credit_balance,
            deduction_source="provider_usage_credits",
            reason=reason,
            created_by=actor_id,
            request_id=request_id,
            idempotency_key=f"customer_remedy:{reference_type}:{reference_id}:credits",
            source_type=reference_type,
            source_id=str(reference_id),
            reason_code="provider_failed_resolution",
            actor_role=actor_role,
        ))

    credit = CustomerServiceCredit(
        credit_number=_gen_number("CSC"),
        customer_id=customer_id,
        tenant_id=tenant_id,
        booking_id=booking_id,
        job_id=job_id,
        amount=amount,
        remaining_amount=amount,
        currency=currency,
        credit_type=("warranty_compensation" if reference_type == "warranty_claim" else "refund_compensation"),
        source="provider_funded_remedy",
        status="active",
        issued_by_admin_id=actor_id,
        issued_reason=reason,
        customer_message=(
            f"We issued {float(amount):,.2f} service points to your account. "
            "You can apply them to another service booking."
        ),
        valid_from=_utcnow(),
        expires_at=_utcnow() + timedelta(days=CREDIT_EXPIRY_DAYS),
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(credit)
    await db.flush()
    db.add(CustomerCreditLedger(
        customer_credit_id=credit.id,
        customer_id=customer_id,
        booking_id=booking_id,
        transaction_type="issued",
        amount=amount,
        balance_after=amount,
        description="Provider-funded service credit; not a cash refund.",
        reference_type=reference_type,
        reference_id=reference_id,
        created_at=_utcnow(),
    ))
    db.add(FinanceAuditLog(
        event_type="customer_credit.provider_funded_remedy",
        actor_user_id=actor_id,
        actor_role=actor_role,
        request_id=request_id,
        tenant_id=tenant_id,
        customer_id=customer_id,
        booking_id=booking_id,
        amount=amount,
        reason=reason,
        metadata_json={
            "reference_type": reference_type,
            "reference_id": str(reference_id),
            "provider_credit_deducted": str(usage_deduct),
            "credit_number": credit.credit_number,
        },
        created_at=_utcnow(),
    ))
    return {
        "credit": credit,
        "provider_credit_deducted": usage_deduct,
        "idempotent_replay": False,
    }


class DisputeSettlementService:
    """Manages the full dispute settlement flow — create, approve, execute, cancel."""

    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None,
                 actor_role: str = "super_admin", request_id: str = "—"):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_wallet(self, tenant_id: uuid.UUID, *, for_update: bool = False) -> TenantBilling | None:
        """Canonical provider usage-credit balance used by job completion."""
        stmt = select(TenantBilling).where(TenantBilling.tenant_id == tenant_id)
        if for_update:
            stmt = stmt.with_for_update()
        return await self.db.scalar(stmt)

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
        """Show what a settlement will take from the tenant's credit balance.

        Only two funded strategies are real: take it from tenant credit, or
        have the platform absorb it as goodwill.

        `tenant_wallet` deliberately does NOT cap the deduction at the current
        balance. The customer is owed the full settlement either way; capping
        it would silently leave the platform funding the difference. The
        balance is allowed to go negative, which puts the tenant below
        `credit_booking_floor` and stops new bookings until they top up.
        """
        if strategy not in VALID_DEDUCTION_STRATEGIES:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                f"deduction_strategy must be one of: {sorted(VALID_DEDUCTION_STRATEGIES)}",
                status_code=422,
            )

        wallet = await self._get_wallet(tenant_id)
        wallet_balance = _two(wallet.credit_balance if wallet else Decimal("0"))

        wallet_deduct = Decimal("0")
        goodwill_amount = Decimal("0")
        remaining = amount

        if strategy == "tenant_wallet":
            wallet_deduct = remaining
            remaining = Decimal("0")
        elif strategy == "platform_goodwill":
            goodwill_amount = amount
            remaining = Decimal("0")
        elif strategy == "none":
            remaining = Decimal("0")  # no_compensation settlement

        balance_after = wallet_balance - wallet_deduct

        return {
            "tenant_id": str(tenant_id),
            "settlement_amount": float(amount),
            "strategy": strategy,
            "wallet_balance": float(wallet_balance),
            "wallet_deduction": float(wallet_deduct),
            "wallet_balance_after": float(balance_after),
            # Surfaced so the console can warn before the admin commits: the
            # settlement still executes, but it leaves the tenant in arrears
            # and blocked from new bookings.
            "goes_negative": balance_after < Decimal("0"),
            "shortfall_amount": float(-balance_after) if balance_after < Decimal("0") else 0.0,
            "platform_goodwill_amount": float(goodwill_amount),
            "uncovered_amount": float(remaining),
            "can_fully_cover": remaining == Decimal("0"),
            "finance_status_after": "blocked" if balance_after < Decimal("0") else "normal",
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

        strategy = data.get("deduction_strategy", "tenant_wallet")
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
        if not preview["can_fully_cover"]:
            raise ServiceOSException(
                "PROVIDER_REMEDY_FUNDS_INSUFFICIENT",
                "Provider credit cannot fund this customer credit.",
                status_code=409,
                context={"uncovered_amount": preview["uncovered_amount"]},
            )
        wallet_deduct = _two(Decimal(str(preview["wallet_deduction"])))
        goodwill_amt  = _two(Decimal(str(preview["platform_goodwill_amount"])))

        # ── Step 1: Deduct tenant credit ──────────────────────────────────────
        # Takes the FULL amount, even past zero. Clamping to the available
        # balance (what this did while a deposit backed it up) would quietly
        # leave the platform funding the remainder, and the tenant would carry
        # no obligation for a failure that was theirs. Going negative puts them
        # below `credit_booking_floor`, which stops new bookings until the
        # balance is restored.
        if wallet_deduct > Decimal("0"):
            wallet = await self._get_wallet(tenant_id, for_update=True)
            actual_deduct = wallet_deduct

            if wallet and actual_deduct > Decimal("0"):
                bal_before = wallet.credit_balance
                wallet.credit_balance -= actual_deduct
                self.db.add(UsageCreditLedger(
                    tenant_id=tenant_id,
                    job_id=s.job_id,
                    booking_id=s.booking_id,
                    event_type="customer_remedy_deduction",
                    credit_delta=-actual_deduct,
                    balance_before=bal_before,
                    balance_after=wallet.credit_balance,
                    deduction_source="provider_usage_credits",
                    reason=(
                        f"Dispute settlement deduction — {s.settlement_number}. "
                        "ServiceOS platform does not collect direct payments for Home Services; "
                        "this amount is deducted to fund customer service credit."
                    ),
                    created_by=self.actor_id,
                    request_id=self.request_id,
                    idempotency_key=f"customer_remedy:dispute:{settlement_id}:credits",
                    source_type="dispute_settlement",
                    source_id=str(settlement_id),
                    reason_code="provider_failed_resolution",
                    actor_role=self.actor_role,
                ))
                s.tenant_wallet_deduction_amount = actual_deduct
                self._audit("tenant_wallet.deducted_for_dispute",
                            tenant_id=tenant_id, settlement_id=settlement_id,
                            dispute_id=s.dispute_id, amount=actual_deduct,
                            reason=f"Wallet deduction for dispute settlement {s.settlement_number}")
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
            amount=wallet_deduct,
            currency=s.currency,
            source="tenant_wallet",
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
        return {
            "total_settlements": total or 0,
            "pending_approval": pending or 0,
            "executed_settlements": executed or 0,
            "failed_cancelled": failed or 0,
            "customer_credits_issued": float(credits_total or 0),
            "tenant_wallet_deducted": float(wallet_total or 0),
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
        # customer_id arrives as a str from require_customer; comparing a str to a
        # UUID is always unequal in Python, so the owner was wrongly 404'd. Compare
        # as strings so ownership actually matches.
        if customer_id and str(credit.customer_id) != str(customer_id):
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

    async def _consume_credits(self, customer_id: uuid.UUID, credit_apply_amount: Decimal,
                               *, reference_type: str, reference_id: uuid.UUID,
                               credit_ref_id: str) -> tuple[Decimal, Decimal, str]:
        """Draw `credit_apply_amount` from the customer's live credits, oldest
        (soonest-expiring) first, writing a ledger entry per credit touched.

        Returns (actually_applied, remaining_balance, credit_number_of_first_used).
        Shared by the booking and invoice apply paths so both deduct identically.
        """
        now = _utcnow()
        credits = (await self.db.execute(
            select(CustomerServiceCredit).where(
                CustomerServiceCredit.customer_id == customer_id,
                CustomerServiceCredit.status.in_(["active", "partially_used"]),
                CustomerServiceCredit.valid_from <= now,
            ).where(
                (CustomerServiceCredit.expires_at == None) |   # noqa: E711
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
            credit.status = "used" if credit.remaining_amount == Decimal("0") else "partially_used"
            if credit.status == "used":
                credit.used_at = now
            self.db.add(CustomerCreditLedger(
                customer_credit_id=credit.id, customer_id=customer_id,
                transaction_type=credit.status,
                amount=-apply_from_this, balance_after=credit.remaining_amount,
                description=(f"ServiceOS credit applied to {reference_type}. "
                             f"Amount to collect is reduced by ₹{float(apply_from_this):,.0f}."),
                reference_type=reference_type, reference_id=reference_id, created_at=now,
            ))
            self._audit(f"{reference_type}.customer_credit_applied",
                        customer_id=customer_id, amount=apply_from_this,
                        metadata_json={"credit_number": credit.credit_number, credit_ref_id: str(reference_id)})
            remaining_to_apply -= apply_from_this
            actually_applied += apply_from_this

        remaining_balance = sum(_two(c.remaining_amount) for c in credits)
        return actually_applied, _two(remaining_balance), (credits[0].credit_number if credits else "")

    async def apply_credit_to_invoice(self, customer_id: uuid.UUID, invoice_id: uuid.UUID,
                                      credit_apply_amount: Decimal) -> dict:
        """Apply the customer's service credit to an issued invoice, reducing what
        they pay the provider.

        The invoice's own customer_payable_amount is the sole source of truth for
        the amount owed. Credit is applied ONCE per invoice: a second call is
        rejected, so a retry (or a double-tap) can never double-spend the credit —
        the flaw the booking-based path had.
        """
        from app.engines.invoice_payment.models import ServiceInvoice

        inv = (await self.db.execute(
            select(ServiceInvoice).where(ServiceInvoice.id == invoice_id))).scalar_one_or_none()
        if not inv:
            raise NotFoundException("Invoice", str(invoice_id))
        if str(inv.customer_id) != str(customer_id):
            raise ServiceOSException("PERMISSION_DENIED", "This invoice does not belong to you.")
        if inv.status in ("cancelled", "void"):
            raise ServiceOSException("INVALID_STATE", "This invoice is not payable.")
        if inv.payment_status in ("collected", "paid"):
            raise ServiceOSException("INVALID_STATE", "This invoice is already paid.")
        if _two(inv.credit_applied_amount) > Decimal("0"):
            raise ServiceOSException("CREDIT_ALREADY_APPLIED",
                                     "Credit has already been applied to this invoice.")

        payable = _two(inv.customer_payable_amount)
        credit_apply_amount = _two(credit_apply_amount)
        if credit_apply_amount <= Decimal("0"):
            raise ServiceOSException("VALIDATION_ERROR", "credit_amount_to_apply must be > 0.")
        if credit_apply_amount > payable:
            raise ServiceOSException(
                "VALIDATION_ERROR",
                "Credit cannot exceed the amount payable. Payable amount cannot be negative.")

        applied, remaining_balance, _ = await self._consume_credits(
            customer_id, credit_apply_amount,
            reference_type="invoice", reference_id=invoice_id, credit_ref_id="invoice_id")

        inv.credit_applied_amount = applied
        inv.customer_payable_amount = _two(payable - applied)
        inv.updated_at = _utcnow()
        await self.db.commit()

        return {
            "success": True,
            "invoice_id": str(invoice_id),
            "original_payable": float(payable),
            "credit_applied": float(applied),
            "new_payable": float(inv.customer_payable_amount),
            "remaining_credit_balance": float(remaining_balance),
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
        return {
            "total_penalties": total or 0,
            "applied_penalties": applied or 0,
            "pending_penalties": pending or 0,
            "reversed_penalties": reversed_ or 0,
            "wallet_deducted": float(wallet_total or 0),
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
            "manual_customer_refund_enabled": False,
        }
