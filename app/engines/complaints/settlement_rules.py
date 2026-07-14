"""MODULE-L5-02 — AI settlement rule engine.

The admin only sets the rule (on complaint_policies); everything else is
automatic:

  * AI settlement is not started by hand. It starts automatically once the
    PROVIDER has failed to solve the complaint — no response within the SLA, or
    the customer rejected the resolution they offered.
  * Starting a session CHARGES THE PROVIDER a fee (default 20 credits), taken
    from their credit wallet and falling back to their security deposit.
  * The AI may offer at most a capped share of the job's value (default 25%).
  * If the case is strong enough to warrant MORE than the cap, the AI does NOT
    settle it — the complaint goes to admin manual review.
  * Compensation is paid in CREDIT POINTS, never real money. Every monetary
    remedy is rejected in code, regardless of what the model returns.
  * The customer's credits are funded by deducting from the PROVIDER's credit
    wallet, falling back to their security deposit.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.complaints.constants import (
    AI_ALLOWED_REMEDIES, AI_SETTLEMENT_DEFAULT_MAX_PCT, AI_SETTLEMENT_FEE_CREDITS,
    MONETARY_REMEDIES, REMEDY_TO_SETTLEMENT_TYPE, SETTLEMENT_DEDUCTION_STRATEGY,
)
from app.engines.complaints.models import ComplaintPolicy, CustomerComplaint


@dataclass
class AISettlementRule:
    enabled: bool
    auto_start_on_provider_failure: bool
    max_pct: Decimal
    allowed_remedies: list[str]
    credits_only: bool
    fee_credits: Decimal

    def cap_amount(self, job_value: Decimal) -> Decimal:
        """The most the AI is allowed to offer on a job of this value."""
        return (job_value * self.max_pct / Decimal("100")).quantize(Decimal("0.01"))


DEFAULT_RULE = AISettlementRule(
    enabled=True,
    auto_start_on_provider_failure=True,
    max_pct=AI_SETTLEMENT_DEFAULT_MAX_PCT,
    allowed_remedies=list(AI_ALLOWED_REMEDIES),
    credits_only=True,
    fee_credits=AI_SETTLEMENT_FEE_CREDITS,
)


async def resolve_rule(db: AsyncSession, complaint: CustomerComplaint) -> AISettlementRule:
    """Most specific active policy wins: tenant+category > tenant > category >
    platform default."""
    q = select(ComplaintPolicy).where(ComplaintPolicy.is_active.is_(True))
    policies = (await db.execute(q)).scalars().all()
    if not policies:
        return DEFAULT_RULE

    def score(p: ComplaintPolicy) -> int:
        s = 0
        if p.tenant_id and str(p.tenant_id) == str(complaint.tenant_id):
            s += 2
        elif p.tenant_id:
            return -1  # a different tenant's policy never applies
        if p.category_id and str(p.category_id) == str(complaint.category_id):
            s += 1
        elif p.category_id:
            return -1
        return s

    ranked = sorted(((score(p), p) for p in policies), key=lambda t: t[0], reverse=True)
    best = next((p for s, p in ranked if s >= 0), None)
    if best is None:
        return DEFAULT_RULE

    return AISettlementRule(
        enabled=bool(getattr(best, "ai_settlement_enabled", True)),
        auto_start_on_provider_failure=bool(
            getattr(best, "ai_auto_start_on_provider_failure", True)),
        max_pct=Decimal(str(getattr(best, "ai_settlement_max_pct", None)
                            or AI_SETTLEMENT_DEFAULT_MAX_PCT)),
        allowed_remedies=list(getattr(best, "ai_settlement_allowed_remedies", None)
                              or AI_ALLOWED_REMEDIES),
        credits_only=bool(getattr(best, "settlement_payout_in_credits_only", True)),
        fee_credits=AI_SETTLEMENT_FEE_CREDITS,
    )


async def resolve_job_value(db: AsyncSession, complaint: CustomerComplaint) -> Decimal:
    """What the customer actually paid — the base the AI's cap is a percentage of.

    Prefers the invoice total, then the job's booking price, then the booking.
    Returns 0 when nothing is billable (the cap then forbids any credit, which is
    the safe direction: the AI cannot invent value out of nothing).
    """
    async def _scalar(sql: str, **params) -> Decimal | None:
        row = (await db.execute(text(sql), params)).scalar_one_or_none()
        return Decimal(str(row)) if row is not None else None

    if complaint.invoice_id:
        v = await _scalar(
            "SELECT total_amount FROM service_invoices WHERE id = :i",
            i=str(complaint.invoice_id))
        if v:
            return v

    if complaint.job_id:
        v = await _scalar(
            """SELECT si.total_amount FROM service_invoices si
                WHERE si.job_id = :j ORDER BY si.created_at DESC LIMIT 1""",
            j=str(complaint.job_id))
        if v:
            return v
        v = await _scalar(
            """SELECT sb.selected_price_amount FROM service_bookings sb
                JOIN service_jobs sj ON sj.booking_id = sb.id
               WHERE sj.id = :j""",
            j=str(complaint.job_id))
        if v:
            return v

    if complaint.booking_id:
        v = await _scalar(
            "SELECT selected_price_amount FROM service_bookings WHERE id = :b",
            b=str(complaint.booking_id))
        if v:
            return v

    return Decimal("0.00")


@dataclass
class ProposalVerdict:
    """The authoritative decision about what the model came back with.

    The LLM is never trusted: whatever it returns is re-checked here against the
    admin's rule, and anything monetary or over-cap is refused.
    """
    allowed: bool
    remedy: str
    amount: Decimal
    settlement_type: str
    escalate_to_admin: bool
    reason: str


def evaluate_proposal(
    rule: AISettlementRule,
    job_value: Decimal,
    remedy: str,
    amount: Decimal | None,
) -> ProposalVerdict:
    """Decide whether the AI is allowed to make this proposal, or whether the
    case must go to a human instead."""
    remedy = (remedy or "").strip().lower()
    amount = Decimal(str(amount or "0")).quantize(Decimal("0.01"))
    cap = rule.cap_amount(job_value)

    # 1. Never money. Not by the model's choice, not by anyone's.
    if remedy in MONETARY_REMEDIES or (rule.credits_only and remedy == "refund"):
        return ProposalVerdict(
            allowed=False, remedy=remedy, amount=amount,
            settlement_type="", escalate_to_admin=True,
            reason=("The AI proposed a monetary remedy, which the platform never "
                    "settles with. Escalated for a human decision."),
        )

    # 2. Only remedies the admin has permitted.
    if remedy not in rule.allowed_remedies:
        return ProposalVerdict(
            allowed=False, remedy=remedy, amount=amount,
            settlement_type="", escalate_to_admin=True,
            reason=f"Remedy '{remedy}' is not permitted by the settlement policy.",
        )

    # 3. The cap. A case that deserves more than the cap is a case for a human —
    #    this is the whole point of the rule, so it escalates rather than
    #    silently clamping the offer down to the cap.
    if amount > cap:
        return ProposalVerdict(
            allowed=False, remedy=remedy, amount=amount,
            settlement_type="", escalate_to_admin=True,
            reason=(f"The case warrants {amount} — more than the {rule.max_pct}% cap "
                    f"({cap}) the AI may settle. Escalated to admin manual review."),
        )

    return ProposalVerdict(
        allowed=True, remedy=remedy, amount=amount,
        settlement_type=REMEDY_TO_SETTLEMENT_TYPE.get(remedy, "no_compensation"),
        escalate_to_admin=False, reason="",
    )


async def charge_ai_settlement_fee(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    complaint_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
) -> dict:
    """Charge the PROVIDER for running an AI settlement — from their credit
    wallet, falling back to their security deposit (the same cascade the payout
    uses). Never fatal: a provider who cannot pay the fee still gets the
    settlement, and the shortfall is reported so finance can chase it."""
    from app.engines.customer_credits.service import DisputeSettlementService

    svc = DisputeSettlementService(db=db, actor_id=actor_id)
    preview = await svc.preview_deduction(
        tenant_id, AI_SETTLEMENT_FEE_CREDITS, SETTLEMENT_DEDUCTION_STRATEGY)

    wallet_take = Decimal(str(preview["wallet_deduction"]))
    if wallet_take > Decimal("0"):
        from app.engines.platform_commerce.models import TenantWallet, WalletTransaction
        wallet = (await db.execute(
            select(TenantWallet).where(TenantWallet.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if wallet:
            before = wallet.credit_balance
            wallet.credit_balance -= wallet_take
            db.add(WalletTransaction(
                tenant_id=tenant_id,
                txn_type="manual_deduct",
                amount=-wallet_take,
                balance_before=before,
                balance_after=wallet.credit_balance,
                reference_id=str(complaint_id),
                reference_type="ai_settlement_fee",
                idempotency_key=f"ai_fee_{complaint_id}",
                description=f"AI settlement fee — complaint {complaint_id}",
            ))
        await db.flush()

    return {
        "fee": float(AI_SETTLEMENT_FEE_CREDITS),
        "charged_from_wallet": float(wallet_take),
        "charged_from_deposit": float(preview["deposit_deduction"]),
        "uncovered": float(preview["uncovered_amount"]),
    }
