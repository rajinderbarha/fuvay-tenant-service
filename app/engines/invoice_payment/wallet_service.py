"""Sprint 23 — ProviderCreditWalletService: wraps existing tenant_wallets/wallet_transactions."""
from __future__ import annotations
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_commerce.models import TenantWallet, WalletTransaction
from app.engines.platform_commerce.ledger import get_wallet_locked, credit_wallet, debit_wallet
from app.engines.invoice_payment.constants import ERR_WALLET_NOT_FOUND


class ProviderCreditWalletService:

    async def get_wallet(self, db: AsyncSession, tenant_id: str) -> dict:
        res = await db.execute(
            select(TenantWallet).where(TenantWallet.tenant_id == uuid.UUID(tenant_id))
        )
        w = res.scalar_one_or_none()
        if not w:
            raise ValueError(ERR_WALLET_NOT_FOUND)
        return self._wallet_dict(w)

    async def ensure_wallet_exists(self, db: AsyncSession, tenant_id: str) -> dict:
        w = await get_wallet_locked(db, uuid.UUID(tenant_id))
        await db.commit()
        return self._wallet_dict(w)

    async def get_ledger(
        self, db: AsyncSession, tenant_id: str, limit: int = 50,
    ) -> list[dict]:
        res = await db.execute(
            select(WalletTransaction)
            .where(WalletTransaction.tenant_id == uuid.UUID(tenant_id))
            .order_by(WalletTransaction.created_at.desc())
            .limit(limit)
        )
        return [self._txn_dict(t) for t in res.scalars().all()]

    async def list_all_wallets(self, db: AsyncSession, limit: int = 200, offset: int = 0) -> list[dict]:
        limit = min(limit, 500)
        res = await db.execute(
            select(TenantWallet).order_by(TenantWallet.created_at.desc()).limit(limit).offset(offset)
        )
        return [self._wallet_dict(w) for w in res.scalars().all()]

    async def admin_credit(
        self, db: AsyncSession, tenant_id: str, amount: float,
        reason: str, admin_user_id: str,
    ) -> dict:
        txn = await credit_wallet(
            db=db,
            tenant_id=uuid.UUID(tenant_id),
            amount=Decimal(str(amount)),
            txn_type="admin_adjustment",
            reference_id=None,
            reference_type="admin_adjustment",
            description=reason,
            actor_id=uuid.UUID(admin_user_id),
            idempotency_key=f"admin-credit-{tenant_id}-{amount}",
        )
        await db.commit()
        return self._txn_dict(txn)

    def _wallet_dict(self, w: TenantWallet) -> dict:
        return {
            "tenant_id":          str(w.tenant_id),
            "currency":           w.currency,
            "current_balance":    str(w.credit_balance),
            "reserved_balance":   str(w.reserved_balance),
            "total_purchased":    str(w.lifetime_purchased),
            "total_deducted":     str(w.lifetime_consumed),
            "low_balance_threshold": str(w.low_balance_threshold) if w.low_balance_threshold else None,
            "is_active":          w.is_active,
            "last_transaction_at":w.last_transaction_at.isoformat() if w.last_transaction_at else None,
        }

    def _txn_dict(self, t: WalletTransaction) -> dict:
        return {
            "id":             str(t.id),
            "tenant_id":      str(t.tenant_id),
            "txn_type":       t.txn_type,
            "amount":         str(t.amount),
            "balance_before": str(t.balance_before),
            "balance_after":  str(t.balance_after),
            "reference_id":   t.reference_id,
            "reference_type": t.reference_type,
            "description":    t.description,
            "created_at":     t.created_at.isoformat() if t.created_at else None,
        }
