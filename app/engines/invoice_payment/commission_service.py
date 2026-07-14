"""Sprint 23 — ServiceCommissionService: commission calculation + deduction."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.invoice_payment.constants import (
    COM_PENDING, COM_CALCULATED, COM_DEDUCTED, COM_FAILED,
    COM_INSUFFICIENT_CREDIT, COM_REVERSED, COM_NOT_REQUIRED,
    DEFAULT_COMMISSION_RATE, FEV_COMMISSION_CALCULATED, FEV_COMMISSION_DEDUCTED,
    FEV_COMMISSION_FAILED, FEV_COMMISSION_REVERSED, FEV_WALLET_LOW_BALANCE,
    ERR_COMMISSION_ALREADY_DEDUCTED, ERR_COMMISSION_DEDUCTION_FAILED,
    ERR_COMMISSION_RETRY_NOT_ALLOWED, ERR_COMMISSION_REVERSAL_REASON,
    ERR_COMMISSION_NOT_REVERSIBLE,
    ERR_INVOICE_NOT_FOUND,
)
from app.engines.invoice_payment.models import (
    ServiceInvoice, SvcCommissionRecord, FinancialEvent,
)
from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
from app.engines.platform_commerce.ledger import debit_wallet, credit_wallet
from app.engines.platform_commerce.models import TenantWallet
from app.exceptions import ServiceOSException


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ServiceCommissionService:

    def __init__(self):
        self._inv_svc = ServiceInvoiceService()

    async def _get_invoice(self, db: AsyncSession, invoice_id: str) -> ServiceInvoice:
        res = await db.execute(
            select(ServiceInvoice).where(ServiceInvoice.id == uuid.UUID(invoice_id))
        )
        inv = res.scalar_one_or_none()
        if not inv:
            raise ValueError(ERR_INVOICE_NOT_FOUND)
        return inv

    async def _log_event(
        self, db: AsyncSession, inv: ServiceInvoice, cr: SvcCommissionRecord,
        event_type: str, actor_type: str, actor_user_id: str | None,
        new_value: dict | None = None, reason: str | None = None,
        request_id: str | None = None,
    ) -> None:
        ev = FinancialEvent(
            id=uuid.uuid4(),
            record_type="commission",
            record_id=cr.id,
            tenant_id=inv.tenant_id,
            actor_type=actor_type,
            actor_user_id=uuid.UUID(actor_user_id) if actor_user_id else None,
            event_type=event_type,
            new_value=new_value,
            reason=reason,
            request_id=request_id,
        )
        db.add(ev)

    async def _resolve_rate(self, db: AsyncSession, category_id) -> Decimal:
        """MODULE-L5-10: commission rate, per category. Was a hardcoded flat 10%
        for every category regardless of value; now reads the category's
        commission_pct, falling back to the platform default when it is unset."""
        if category_id is not None:
            from app.engines.admin_catalog.models import ServiceCategory
            rate = (await db.execute(
                select(ServiceCategory.commission_pct)
                .where(ServiceCategory.id == category_id)
            )).scalar_one_or_none()
            if rate is not None:
                return Decimal(str(rate))
        return Decimal(str(DEFAULT_COMMISSION_RATE))

    # ── Calculate commission ───────────────────────────────────────────────────

    async def calculate_commission(
        self, db: AsyncSession, invoice_id: str, actor_user_id: str | None = None,
    ) -> dict:
        inv = await self._get_invoice(db, invoice_id)
        # Check if record already exists
        res = await db.execute(
            select(SvcCommissionRecord).where(SvcCommissionRecord.invoice_id == inv.id)
        )
        cr = res.scalar_one_or_none()
        if cr and cr.status in {COM_DEDUCTED}:
            raise ValueError(ERR_COMMISSION_ALREADY_DEDUCTED)

        rate = await self._resolve_rate(db, inv.category_id)
        # MODULE-L5-10: commission is charged on the SERVICE value (total_amount),
        # NOT customer_payable_amount — the latter now includes the platform's own
        # customer charge, and the provider must not pay commission on that fee.
        # For invoices with no platform fee the two are equal, so this is a no-op
        # for existing data.
        base = inv.total_amount
        amount = (base * rate / Decimal("100")).quantize(Decimal("0.01"))
        now = _utcnow()

        if cr:
            await db.execute(
                update(SvcCommissionRecord)
                .where(SvcCommissionRecord.id == cr.id)
                .values(
                    status=COM_CALCULATED,
                    commission_base_amount=base,
                    commission_rate=rate,
                    commission_amount=amount,
                    calculated_at=now,
                    updated_at=now,
                )
            )
            await db.refresh(cr)
        else:
            cr = SvcCommissionRecord(
                id=uuid.uuid4(),
                invoice_id=inv.id,
                booking_id=inv.booking_id,
                job_id=inv.job_id,
                tenant_id=inv.tenant_id,
                status=COM_CALCULATED,
                commission_base_amount=base,
                commission_rate=rate,
                commission_amount=amount,
                calculated_at=now,
            )
            db.add(cr)
            await db.flush()

        await self._log_event(db, inv, cr, FEV_COMMISSION_CALCULATED, "system", actor_user_id,
                              new_value={"rate": str(rate), "amount": str(amount)})
        await db.commit()
        await db.refresh(cr)
        return cr.to_dict()

    # ── Deduct commission from wallet ──────────────────────────────────────────

    async def deduct_commission(
        self, db: AsyncSession, invoice_id: str,
        idempotency_key: str, actor_user_id: str | None = None, request_id: str | None = None,
    ) -> dict:
        inv = await self._get_invoice(db, invoice_id)
        res = await db.execute(
            select(SvcCommissionRecord).where(SvcCommissionRecord.invoice_id == inv.id)
        )
        cr = res.scalar_one_or_none()
        if not cr:
            # Auto-calculate first
            await self.calculate_commission(db, invoice_id, actor_user_id)
            res2 = await db.execute(
                select(SvcCommissionRecord).where(SvcCommissionRecord.invoice_id == inv.id)
            )
            cr = res2.scalar_one_or_none()

        if cr.status == COM_DEDUCTED:
            raise ValueError(ERR_COMMISSION_ALREADY_DEDUCTED)

        # Idempotency: same key, same record → no-op
        if cr.idempotency_key and cr.idempotency_key == idempotency_key and cr.status == COM_DEDUCTED:
            return cr.to_dict()

        now = _utcnow()
        try:
            txn = await debit_wallet(
                db=db,
                tenant_id=inv.tenant_id,
                amount=cr.commission_amount,
                txn_type="commission_deduction",
                reference_id=str(inv.id),
                reference_type="invoice",
                description=f"Commission for invoice {inv.invoice_number}",
                actor_id=uuid.UUID(actor_user_id) if actor_user_id else None,
                idempotency_key=idempotency_key,
            )
            await db.execute(
                update(SvcCommissionRecord)
                .where(SvcCommissionRecord.id == cr.id)
                .values(
                    status=COM_DEDUCTED,
                    wallet_ledger_entry_id=txn.id,
                    idempotency_key=idempotency_key,
                    deducted_at=now,
                    failure_code=None,
                    failure_message=None,
                    updated_at=now,
                )
            )
            await self._inv_svc.update_commission_status(db, inv.id, COM_DEDUCTED)
            await self._log_event(db, inv, cr, FEV_COMMISSION_DEDUCTED, "system", actor_user_id,
                                  new_value={"amount": str(cr.commission_amount),
                                              "ledger_entry": str(txn.id)},
                                  request_id=request_id)
            await db.commit()
            await db.refresh(cr)
            return cr.to_dict()

        except ServiceOSException as e:
            if "COMMISSION_WALLET_EMPTY" in str(e.error_code) or "Insufficient" in str(e.detail):
                status = COM_INSUFFICIENT_CREDIT
                fcode  = "INSUFFICIENT_CREDIT"
            else:
                status = COM_FAILED
                fcode  = "DEDUCTION_FAILED"

            await db.execute(
                update(SvcCommissionRecord)
                .where(SvcCommissionRecord.id == cr.id)
                .values(
                    status=status,
                    failure_code=fcode,
                    failure_message=str(e),
                    updated_at=now,
                )
            )
            await self._inv_svc.update_commission_status(db, inv.id, status)
            await self._log_event(db, inv, cr, FEV_COMMISSION_FAILED, "system", actor_user_id,
                                  new_value={"failure_code": fcode}, request_id=request_id)
            # Log wallet event if insufficient
            if status == COM_INSUFFICIENT_CREDIT:
                ev = FinancialEvent(
                    id=uuid.uuid4(),
                    record_type="wallet",
                    record_id=inv.tenant_id,
                    tenant_id=inv.tenant_id,
                    actor_type="system",
                    event_type=FEV_WALLET_LOW_BALANCE,
                    new_value={"required": str(cr.commission_amount)},
                )
                db.add(ev)
            await db.commit()
            await db.refresh(cr)
            raise ValueError(ERR_COMMISSION_DEDUCTION_FAILED)

    # ── Retry commission deduction ─────────────────────────────────────────────

    async def retry_commission_deduction(
        self, db: AsyncSession, commission_id: str, admin_id: str, request_id: str | None,
    ) -> dict:
        res = await db.execute(
            select(SvcCommissionRecord).where(SvcCommissionRecord.id == uuid.UUID(commission_id))
        )
        cr = res.scalar_one_or_none()
        if not cr:
            raise ValueError(ERR_INVOICE_NOT_FOUND)
        if cr.status not in {COM_FAILED, COM_INSUFFICIENT_CREDIT}:
            raise ValueError(ERR_COMMISSION_RETRY_NOT_ALLOWED)
        # Reset to calculated so deduct_commission can proceed
        await db.execute(
            update(SvcCommissionRecord)
            .where(SvcCommissionRecord.id == cr.id)
            .values(status=COM_CALCULATED, failure_code=None, failure_message=None, updated_at=_utcnow())
        )
        await db.commit()
        idem_key = f"retry-{commission_id}-{_utcnow().timestamp()}"
        return await self.deduct_commission(db, str(cr.invoice_id), idem_key, admin_id, request_id)

    # ── Reverse commission ─────────────────────────────────────────────────────

    async def reverse_commission(
        self, db: AsyncSession, commission_id: str, admin_id: str,
        reason: str, request_id: str | None,
    ) -> dict:
        if not reason or not reason.strip():
            raise ValueError(ERR_COMMISSION_REVERSAL_REASON)
        res = await db.execute(
            select(SvcCommissionRecord).where(SvcCommissionRecord.id == uuid.UUID(commission_id))
        )
        cr = res.scalar_one_or_none()
        if not cr:
            raise ValueError(ERR_INVOICE_NOT_FOUND)
        # MODULE-L5-10: only a commission that was actually DEDUCTED can be
        # reversed. Reversing one that never took money (calculated / failed /
        # insufficient_credit) would credit the provider's wallet for a charge
        # that never happened — free money — and reversing an already-reversed one
        # would double it. Guard on status before crediting anything back.
        if cr.status != COM_DEDUCTED:
            raise ValueError(ERR_COMMISSION_NOT_REVERSIBLE)
        # Credit wallet back
        idem_key = f"reversal-{commission_id}"
        await credit_wallet(
            db=db,
            tenant_id=cr.tenant_id,
            amount=cr.commission_amount,
            txn_type="reversal",
            reference_id=str(cr.invoice_id),
            reference_type="commission",
            description=f"Commission reversal: {reason}",
            actor_id=uuid.UUID(admin_id) if admin_id else None,
            idempotency_key=idem_key,
        )
        await db.execute(
            update(SvcCommissionRecord)
            .where(SvcCommissionRecord.id == cr.id)
            .values(status=COM_REVERSED, updated_at=_utcnow())
        )
        inv_res = await db.execute(
            select(ServiceInvoice).where(ServiceInvoice.id == cr.invoice_id)
        )
        inv = inv_res.scalar_one_or_none()
        if inv:
            await self._inv_svc.update_commission_status(db, inv.id, COM_REVERSED)
            await self._log_event(db, inv, cr, FEV_COMMISSION_REVERSED, "admin", admin_id,
                                  reason=reason, request_id=request_id)
        await db.commit()
        await db.refresh(cr)
        return cr.to_dict()

    # ── Get commission status ──────────────────────────────────────────────────

    async def get_commission_status(self, db: AsyncSession, invoice_id: str) -> dict | None:
        res = await db.execute(
            select(SvcCommissionRecord).where(
                SvcCommissionRecord.invoice_id == uuid.UUID(invoice_id)
            )
        )
        cr = res.scalar_one_or_none()
        return cr.to_dict() if cr else None

    async def list_all_commissions(
        self, db: AsyncSession, tenant_id: str | None = None,
        status: str | None = None, limit: int = 100, offset: int = 0,
    ) -> list[dict]:
        limit = min(limit, 500)
        q = select(SvcCommissionRecord).order_by(SvcCommissionRecord.created_at.desc())
        if tenant_id:
            q = q.where(SvcCommissionRecord.tenant_id == uuid.UUID(tenant_id))
        if status:
            q = q.where(SvcCommissionRecord.status == status)
        q = q.limit(limit).offset(offset)
        res = await db.execute(q)
        return [cr.to_dict() for cr in res.scalars().all()]
