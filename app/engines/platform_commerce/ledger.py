"""
Platform Commerce Engine — Ledger
Append-only financial operations with SELECT FOR UPDATE row locking.
Every function here is transactional — caller is responsible for commit/rollback.
"""
from __future__ import annotations
import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_commerce.constants import TxnType, DepositTxnType
from app.engines.platform_commerce.models import (
    TenantWallet, WalletTransaction,
    SecurityDeposit, SecurityDepositTransaction,
    CustomerCreditBalance, CustomerTransaction,
)
from app.exceptions import ServiceOSException

logger = structlog.get_logger("commerce.ledger")
utcnow = lambda: datetime.now(timezone.utc)


async def get_wallet_locked(db: AsyncSession, tenant_id: uuid.UUID) -> TenantWallet:
    """SELECT FOR UPDATE NOWAIT — raises 409 if row is locked by another tx."""
    try:
        result = await db.execute(
            select(TenantWallet)
            .where(TenantWallet.tenant_id == tenant_id)
            .with_for_update(nowait=True)
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            wallet = TenantWallet(tenant_id=tenant_id)
            db.add(wallet)
            await db.flush()
        return wallet
    except Exception as e:
        if "could not obtain lock" in str(e).lower() or "lock" in str(e).lower():
            raise ServiceOSException(
                "CONFLICT",
                "Wallet is being updated by another transaction. Retry in 1 second.",
                resolution="Retry the request — the lock is short-lived.",
                context={"retry_after_seconds": 1},
            )
        raise


async def debit_wallet(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    amount: Decimal,
    txn_type: str,
    reference_id: str | None,
    reference_type: str | None,
    description: str | None,
    actor_id: uuid.UUID | None,
    idempotency_key: str | None = None,
    meta: dict | None = None,
) -> WalletTransaction:
    """Debit wallet with row lock. Raises if insufficient balance."""
    # MODULE-L5-10: the ledger primitives must never move money the wrong way on
    # a bad amount. A non-positive amount here would pass the balance check
    # (balance < negative is False) and then run `balance -= negative`, i.e.
    # INFLATE the balance. Reject it at the source so no caller — present or
    # future — can invert a debit/credit.
    if amount is None or amount <= Decimal("0"):
        raise ServiceOSException("INVALID_LEDGER_AMOUNT",
            "Ledger amount must be a positive number.", status_code=422,
            context={"amount": float(amount) if amount is not None else None})

    if idempotency_key:
        existing = await db.execute(
            select(WalletTransaction).where(WalletTransaction.idempotency_key == idempotency_key)
        )
        existing_txn = existing.scalar_one_or_none()
        if existing_txn:
            logger.info("ledger.debit_idempotent_hit", key=idempotency_key[:16])
            return existing_txn

    wallet = await get_wallet_locked(db, tenant_id)

    if wallet.credit_balance < amount:
        raise ServiceOSException(
            "COMMISSION_WALLET_EMPTY",
            f"Insufficient usage credit balance. Required: {amount} credits, Available: {wallet.credit_balance} credits.",
            resolution="Top up usage credits before this debit, or reduce the debit amount.",
            context={"required": float(amount), "available": float(wallet.credit_balance)},
        )

    balance_before = wallet.credit_balance
    wallet.credit_balance -= amount
    wallet.lifetime_consumed += amount
    wallet.last_transaction_at = utcnow()

    txn = WalletTransaction(
        tenant_id=tenant_id,
        txn_type=txn_type,
        amount=-amount,
        balance_before=balance_before,
        balance_after=wallet.credit_balance,
        reference_id=reference_id,
        reference_type=reference_type,
        idempotency_key=idempotency_key,
        description=description,
        actor_id=actor_id,
        meta=meta or {},
    )
    db.add(txn)
    logger.info("ledger.debit", tenant_id=str(tenant_id), amount=float(amount),
                type=txn_type, balance_after=float(wallet.credit_balance))
    return txn


async def credit_wallet(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    amount: Decimal,
    txn_type: str,
    reference_id: str | None,
    reference_type: str | None,
    description: str | None,
    actor_id: uuid.UUID | None,
    idempotency_key: str | None = None,
    meta: dict | None = None,
) -> WalletTransaction:
    """Credit wallet. Also row-locked to keep balance accurate."""
    # MODULE-L5-10: the ledger primitives must never move money the wrong way on
    # a bad amount. A non-positive amount here would pass the balance check
    # (balance < negative is False) and then run `balance -= negative`, i.e.
    # INFLATE the balance. Reject it at the source so no caller — present or
    # future — can invert a debit/credit.
    if amount is None or amount <= Decimal("0"):
        raise ServiceOSException("INVALID_LEDGER_AMOUNT",
            "Ledger amount must be a positive number.", status_code=422,
            context={"amount": float(amount) if amount is not None else None})

    if idempotency_key:
        existing = await db.execute(
            select(WalletTransaction).where(WalletTransaction.idempotency_key == idempotency_key)
        )
        existing_txn = existing.scalar_one_or_none()
        if existing_txn:
            return existing_txn

    wallet = await get_wallet_locked(db, tenant_id)
    balance_before = wallet.credit_balance
    wallet.credit_balance += amount
    wallet.lifetime_purchased += amount
    wallet.last_transaction_at = utcnow()

    txn = WalletTransaction(
        tenant_id=tenant_id,
        txn_type=txn_type,
        amount=amount,
        balance_before=balance_before,
        balance_after=wallet.credit_balance,
        reference_id=reference_id,
        reference_type=reference_type,
        idempotency_key=idempotency_key,
        description=description,
        actor_id=actor_id,
        meta=meta or {},
    )
    db.add(txn)
    logger.info("ledger.credit", tenant_id=str(tenant_id), amount=float(amount),
                type=txn_type, balance_after=float(wallet.credit_balance))
    return txn


async def debit_deposit(
    db: AsyncSession,
    deposit: SecurityDeposit,
    amount: Decimal,
    txn_type: str,
    reference_id: str | None,
    notes: str | None,
    actor_id: uuid.UUID | None,
) -> SecurityDepositTransaction:
    """Draw from security deposit. Raises if insufficient balance."""
    # MODULE-L5-10: the ledger primitives must never move money the wrong way on
    # a bad amount. A non-positive amount here would pass the balance check
    # (balance < negative is False) and then run `balance -= negative`, i.e.
    # INFLATE the balance. Reject it at the source so no caller — present or
    # future — can invert a debit/credit.
    if amount is None or amount <= Decimal("0"):
        raise ServiceOSException("INVALID_LEDGER_AMOUNT",
            "Ledger amount must be a positive number.", status_code=422,
            context={"amount": float(amount) if amount is not None else None})

    current = deposit.current_balance
    if current < amount:
        raise ServiceOSException(
            "SECURITY_DEPOSIT_REQUIRED",
            f"Security deposit balance insufficient. Required: {amount}, Available: {current}",
            context={"required": float(amount), "available": float(current)},
        )
    balance_before = current
    deposit.warranty_drawn += amount

    txn = SecurityDepositTransaction(
        deposit_id=deposit.id,
        tenant_id=deposit.tenant_id,
        txn_type=txn_type,
        amount=-amount,
        balance_before=balance_before,
        balance_after=deposit.current_balance,
        reference_id=reference_id,
        notes=notes,
        actor_id=actor_id,
    )
    db.add(txn)
    return txn


async def credit_deposit(
    db: AsyncSession,
    deposit: SecurityDeposit,
    amount: Decimal,
    txn_type: str,
    reference_id: str | None,
    notes: str | None,
    actor_id: uuid.UUID | None,
) -> SecurityDepositTransaction:
    """Credit security deposit (replenishment or admin adjustment)."""
    # MODULE-L5-10: the ledger primitives must never move money the wrong way on
    # a bad amount. A non-positive amount here would pass the balance check
    # (balance < negative is False) and then run `balance -= negative`, i.e.
    # INFLATE the balance. Reject it at the source so no caller — present or
    # future — can invert a debit/credit.
    if amount is None or amount <= Decimal("0"):
        raise ServiceOSException("INVALID_LEDGER_AMOUNT",
            "Ledger amount must be a positive number.", status_code=422,
            context={"amount": float(amount) if amount is not None else None})

    balance_before = deposit.current_balance
    if txn_type == DepositTxnType.REPLENISHMENT:
        deposit.replenishment_total += amount
    elif txn_type == DepositTxnType.INITIAL_PAYMENT:
        deposit.total_paid += amount
    else:
        deposit.replenishment_total += amount

    txn = SecurityDepositTransaction(
        deposit_id=deposit.id,
        tenant_id=deposit.tenant_id,
        txn_type=txn_type,
        amount=amount,
        balance_before=balance_before,
        balance_after=deposit.current_balance,
        reference_id=reference_id,
        notes=notes,
        actor_id=actor_id,
    )
    db.add(txn)
    return txn


async def reconcile_wallet(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    """
    Verify ledger sum == wallet balance. Called on every wallet read.
    Raises CRITICAL alert if mismatch detected.
    """
    from sqlalchemy import func
    result = await db.execute(
        select(func.sum(WalletTransaction.amount))
        .where(WalletTransaction.tenant_id == tenant_id)
    )
    ledger_sum = result.scalar_one_or_none() or Decimal("0.00")

    result2 = await db.execute(
        select(TenantWallet).where(TenantWallet.tenant_id == tenant_id)
    )
    wallet = result2.scalar_one_or_none()
    wallet_balance = wallet.credit_balance if wallet else Decimal("0.00")

    epsilon = Decimal("0.0001")
    mismatch = abs(ledger_sum - wallet_balance) > epsilon

    if mismatch:
        logger.critical(
            "ledger.reconciliation_error",
            tenant_id=str(tenant_id),
            ledger_sum=float(ledger_sum),
            wallet_balance=float(wallet_balance),
            diff=float(abs(ledger_sum - wallet_balance)),
        )

    return {
        "matches": not mismatch,
        "ledger_sum": ledger_sum,
        "wallet_balance": wallet_balance,
        "diff": abs(ledger_sum - wallet_balance),
    }


async def debit_customer_balance(
    db: AsyncSession,
    customer_id: uuid.UUID,
    tenant_id: uuid.UUID,
    amount: Decimal,
    txn_type: str,
    reference_id: str | None,
    description: str | None,
    idempotency_key: str | None = None,
) -> CustomerTransaction:
    """Debit customer credit balance. SELECT FOR UPDATE."""
    if idempotency_key:
        existing = await db.execute(
            select(CustomerTransaction).where(CustomerTransaction.idempotency_key == idempotency_key)
        )
        if existing.scalar_one_or_none():
            return existing.scalar_one_or_none()

    result = await db.execute(
        select(CustomerCreditBalance)
        .where(CustomerCreditBalance.customer_id == customer_id,
               CustomerCreditBalance.tenant_id == tenant_id)
        .with_for_update(nowait=True)
    )
    bal = result.scalar_one_or_none()
    if not bal:
        raise ServiceOSException("NOT_FOUND", "Customer credit balance not found.")

    if bal.available_balance < amount:
        raise ServiceOSException(
            "PLAN_LIMIT_EXCEEDED",
            f"Insufficient customer credit balance. Available: {bal.available_balance}",
        )

    balance_before = bal.credit_balance
    bal.credit_balance -= amount
    bal.lifetime_consumed += amount

    txn = CustomerTransaction(
        customer_id=customer_id, tenant_id=tenant_id,
        txn_type=txn_type, amount=-amount,
        balance_before=balance_before, balance_after=bal.credit_balance,
        reference_id=reference_id, description=description,
        idempotency_key=idempotency_key,
    )
    db.add(txn)
    return txn
