"""
Platform Commerce Engine — Preflight Pipeline
4-check sequential gate run before any booking is confirmed.
Fails fast on first block. Returns HATEOAS allowed_transitions so client
knows exactly what action to take.
"""
from __future__ import annotations
import uuid
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_commerce.constants import (
    COMMISSION_BASE_RATE, COMMISSION_HEALTH_ADJUSTMENT,
    WALLET_BUFFER_MULTIPLIER, CUSTOMER_ADVANCE_REQUIRED_PCT,
)
from app.engines.platform_commerce.models import (
    SecurityDeposit, TenantWallet, CustomerHealthScore,
    CustomerCreditBalance,
)
from app.engines.tenant_engine.models import Tenant

logger = structlog.get_logger("commerce.preflight")


async def run_booking_preflight(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    estimated_job_value: Decimal,
    booking_id: str | None = None,
) -> dict:
    """
    Runs 4 checks in sequence. Fails fast on first block.
    Returns a structured result the Booking engine uses to confirm or block.
    """
    checks_run = []

    # ── Check 1: Tenant status active ─────────────────────────────────────
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()

    if not tenant or tenant.status not in ("active", "trial"):
        status = tenant.status if tenant else "not_found"
        return _blocked(
            check="tenant_active",
            reason=f"Tenant account is not active (status: {status}).",
            tenant_id=tenant_id, customer_id=customer_id,
            estimated_job_value=estimated_job_value,
            checks_run=checks_run + ["tenant_active"],
            transitions=[{
                "action": "contact_support",
                "label": "Contact support",
                "endpoint": "/v1/support/contact",
                "method": "GET",
            }],
        )
    checks_run.append("tenant_active")

    # ── Check 2: Tenant wallet has enough buffer ───────────────────────────
    plan = tenant.plan_type or "starter"
    health_band = tenant.health_band or "gold"
    base_rate = COMMISSION_BASE_RATE.get(plan, Decimal("10.00"))
    adj = COMMISSION_HEALTH_ADJUSTMENT.get(health_band, Decimal("0.00"))
    effective_rate = max(Decimal("1.00"), base_rate + adj) / Decimal("100")
    estimated_commission = (estimated_job_value * effective_rate).quantize(Decimal("0.01"))
    required_wallet = (estimated_commission * WALLET_BUFFER_MULTIPLIER).quantize(Decimal("0.01"))

    wallet_result = await db.execute(
        select(TenantWallet).where(TenantWallet.tenant_id == tenant_id)
    )
    wallet = wallet_result.scalar_one_or_none()
    wallet_balance = wallet.credit_balance if wallet else Decimal("0.00")
    wallet_ok = wallet_balance >= required_wallet

    if not wallet_ok:
        return _blocked(
            check="tenant_wallet_balance",
            reason=f"Tenant wallet balance ₹{wallet_balance} is below required ₹{required_wallet} (1.5× estimated commission).",
            tenant_id=tenant_id, customer_id=customer_id,
            estimated_job_value=estimated_job_value,
            checks_run=checks_run + ["tenant_wallet_balance"],
            transitions=[{
                "action": "purchase_credits",
                "label": "Purchase credit package",
                "endpoint": f"/v1/commerce/tenants/{tenant_id}/wallet/purchase/initiate",
                "method": "POST",
                "reason": f"Need at least ₹{required_wallet} in wallet to accept this booking.",
            }],
        )
    checks_run.append("tenant_wallet_balance")

    # ── Check 3: Customer is not Blocked ──────────────────────────────────
    health_result = await db.execute(
        select(CustomerHealthScore).where(
            CustomerHealthScore.customer_id == customer_id,
            CustomerHealthScore.tenant_id == tenant_id,
        )
    )
    customer_health = health_result.scalar_one_or_none()
    customer_band = "standard"
    advance_pct = Decimal("0.00")

    if customer_health:
        # Check override expiry
        from datetime import datetime, timezone
        utcnow = datetime.now(timezone.utc)
        if (customer_health.override_band and customer_health.override_expires_at
                and customer_health.override_expires_at > utcnow):
            customer_band = customer_health.override_band
        else:
            customer_band = customer_health.band
        advance_pct = CUSTOMER_ADVANCE_REQUIRED_PCT.get(customer_band, Decimal("0.00"))

    if customer_band == "blocked":
        return _blocked(
            check="customer_not_blocked",
            reason="Customer is blocked from making new bookings due to payment or behaviour history.",
            tenant_id=tenant_id, customer_id=customer_id,
            estimated_job_value=estimated_job_value,
            checks_run=checks_run + ["customer_not_blocked"],
            transitions=[{
                "action": "view_customer_health",
                "label": "View customer health score",
                "endpoint": f"/v1/commerce/customers/{customer_id}/health",
                "method": "GET",
                "reason": "Customer must resolve outstanding issues before booking.",
            }],
        )
    checks_run.append("customer_not_blocked")

    # ── Check 4: Customer advance credits available ────────────────────────
    advance_amount = Decimal("0.00")
    if advance_pct > 0:
        advance_amount = (estimated_job_value * advance_pct / Decimal("100")).quantize(Decimal("0.01"))
        bal_result = await db.execute(
            select(CustomerCreditBalance).where(
                CustomerCreditBalance.customer_id == customer_id,
                CustomerCreditBalance.tenant_id == tenant_id,
            )
        )
        customer_bal = bal_result.scalar_one_or_none()
        available = customer_bal.available_balance if customer_bal else Decimal("0.00")

        if available < advance_amount:
            return _blocked(
                check="customer_advance_available",
                reason=f"Customer needs ₹{advance_amount} advance ({advance_pct}% of ₹{estimated_job_value}) but only ₹{available} available.",
                tenant_id=tenant_id, customer_id=customer_id,
                estimated_job_value=estimated_job_value,
                checks_run=checks_run + ["customer_advance_available"],
                transitions=[{
                    "action": "top_up_credits",
                    "label": "Top up customer credits",
                    "endpoint": f"/v1/commerce/customers/{customer_id}/credits/purchase",
                    "method": "POST",
                    "reason": f"Need ₹{advance_amount - available} more credits to proceed.",
                }],
            )
    checks_run.append("customer_advance_available")

    # ── All checks passed ─────────────────────────────────────────────────
    logger.info("preflight.passed", tenant_id=str(tenant_id), customer_id=str(customer_id))
    return {
        "allowed": True,
        "blocking_check": None,
        "blocking_reason": None,
        "advance_required_pct": advance_pct,
        "estimated_advance_amount": advance_amount,
        "estimated_commission": estimated_commission,
        "effective_commission_rate": float(effective_rate * 100),
        "tenant_wallet_sufficient": True,
        "customer_can_book": True,
        "checks_passed": checks_run,
        "allowed_transitions": [],
    }


def _blocked(
    check: str, reason: str, tenant_id: uuid.UUID, customer_id: uuid.UUID,
    estimated_job_value: Decimal, checks_run: list, transitions: list,
) -> dict:
    logger.info("preflight.blocked", check=check, tenant_id=str(tenant_id),
                customer_id=str(customer_id))
    return {
        "allowed": False,
        "blocking_check": check,
        "blocking_reason": reason,
        "advance_required_pct": Decimal("0"),
        "estimated_advance_amount": Decimal("0"),
        "estimated_commission": Decimal("0"),
        "tenant_wallet_sufficient": check != "tenant_wallet_balance",
        "customer_can_book": check not in ("customer_not_blocked", "customer_advance_available"),
        "checks_passed": checks_run,
        "allowed_transitions": transitions,
    }
