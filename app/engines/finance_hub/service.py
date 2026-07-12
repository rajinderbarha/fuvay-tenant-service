"""Finance Hub Engine — FinanceHubService.

Composes platform_commerce (wallets/deposits/warranty) and payment (payouts)
engines into one enterprise admin surface, rather than duplicating their
business logic. Only credit-top-up order tracking is genuinely new.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.engines.finance_hub.models import CreditTopupOrder
from app.engines.platform_commerce.constants import DepositTxnType
from app.engines.platform_commerce.ledger import credit_deposit, debit_deposit
from app.engines.platform_commerce.models import (
    TenantWallet, WalletTransaction, SecurityDeposit, SecurityDepositTransaction,
    WarrantyClaim, CommissionRecord, CreditPackage,
)
from app.engines.platform_commerce.service import CommerceService
from app.engines.payment.models import PayoutRecord
from app.engines.payment.service import PaymentService
from app.engines.security.models import PlatformAuditLog
from app.engines.tenant_engine.models import Tenant
from app.exceptions import ServiceOSException, NotFoundException

logger = structlog.get_logger("finance_hub.service")
utcnow = lambda: datetime.now(timezone.utc)

LOW_BALANCE_DEFAULT_THRESHOLD = Decimal("500.00")

DEPOSIT_ACTIVE_STATUSES = ("paid", "partially_paid")
CLAIM_OPEN_STATUSES = ("pending", "pending_review", "investigating", "awaiting_documents")
PAYOUT_OPEN_STATUSES = ("pending", "approved", "processing")


class FinanceHubService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None):
        self.db = db
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self._commerce = CommerceService(db=db, request_id=request_id, actor_id=actor_id, actor_role=actor_role)
        self._payment = PaymentService(db=db, request_id=request_id, actor_id=actor_id, actor_role=actor_role)

    async def _audit(self, operation: str, entity_type: str, entity_id: str,
                      tenant_id: uuid.UUID | None = None,
                      before: dict | None = None, after: dict | None = None) -> None:
        await record_platform_audit(
            self.db, operation=operation, engine_id="finance_hub",
            entity_type=entity_type, entity_id=entity_id, tenant_id=tenant_id,
            actor_id=self.actor_id, actor_role=self.actor_role, request_id=self.request_id,
            before=before, after=after,
        )

    async def list_audit_logs(self, entity_type: str, entity_id: str, limit: int = 50) -> dict:
        stmt = (select(PlatformAuditLog)
                .where(PlatformAuditLog.entity_type == entity_type, PlatformAuditLog.entity_id == entity_id)
                .order_by(PlatformAuditLog.created_at.desc()).limit(min(limit, 200)))
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return {"audit_log": [{
            "id": str(a.id), "operation": a.operation, "engine_id": a.engine_id,
            "actor_id": str(a.actor_id) if a.actor_id else None, "actor_role": a.actor_role,
            "before": a.before_state, "after": a.after_state,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in rows]}

    # ═══════════════════════════════════════════════════════════════
    # OVERVIEW
    # ═══════════════════════════════════════════════════════════════

    async def get_finance_summary(self) -> dict:
        active_wallets = (await self.db.execute(
            select(func.count()).select_from(TenantWallet).where(TenantWallet.is_active == True)
        )).scalar_one()
        low_balance_wallets = (await self.db.execute(
            select(func.count()).select_from(TenantWallet).where(
                TenantWallet.is_active == True,
                TenantWallet.credit_balance <= func.coalesce(TenantWallet.low_balance_threshold, LOW_BALANCE_DEFAULT_THRESHOLD),
            )
        )).scalar_one()
        credits_issued = (await self.db.execute(
            select(func.coalesce(func.sum(TenantWallet.lifetime_purchased), 0))
        )).scalar_one()
        commission_earned = (await self.db.execute(
            select(func.coalesce(func.sum(CommissionRecord.commission_amount), 0))
        )).scalar_one()
        deposits = (await self.db.execute(select(SecurityDeposit))).scalars().all()
        deposit_held = sum((d.current_balance for d in deposits if d.status in DEPOSIT_ACTIVE_STATUSES), Decimal("0"))
        deposit_pending = sum(1 for d in deposits if d.status in ("unpaid", "partially_paid", "pending_verification"))
        recovered_refunded = sum(1 for d in deposits if d.status == "refunded")
        pending_claims = (await self.db.execute(
            select(func.count()).select_from(WarrantyClaim).where(WarrantyClaim.status.in_(CLAIM_OPEN_STATUSES))
        )).scalar_one()
        pending_payouts = (await self.db.execute(
            select(func.count()).select_from(PayoutRecord).where(PayoutRecord.status.in_(PAYOUT_OPEN_STATUSES))
        )).scalar_one()
        at_risk = (await self.db.execute(
            select(func.count()).select_from(Tenant).where(Tenant.health_band.in_(["at_risk", "critical"]), Tenant.status == "active")
        )).scalar_one()
        pending_deposit_actions = sum(1 for d in deposits if d.status in ("pending_verification", "refund_requested"))

        return {
            "active_wallets": active_wallets,
            "low_balance_wallets": low_balance_wallets,
            "credits_issued": float(credits_issued),
            "commission_earned": float(commission_earned),
            "deposit_held": float(deposit_held),
            "deposit_pending": deposit_pending,
            "pending_warranty_claims": pending_claims,
            "pending_payouts": pending_payouts,
            "at_risk_tenants": at_risk,
            "recovered_refunded_deposits": recovered_refunded,
            "pending_deposit_actions": pending_deposit_actions,
        }

    async def get_finance_overview(self) -> dict:
        # Wallet health distribution (reuses Tenant.health_band, already fed by credit_wallet_health signal)
        band_result = await self.db.execute(
            select(Tenant.health_band, func.count()).where(Tenant.status == "active").group_by(Tenant.health_band))
        wallet_health_distribution = {band: cnt for band, cnt in band_result.all()}

        # Top low-balance tenants
        low_bal_result = await self.db.execute(
            select(TenantWallet, Tenant).join(Tenant, Tenant.id == TenantWallet.tenant_id)
            .where(TenantWallet.is_active == True).order_by(TenantWallet.credit_balance.asc()).limit(10))
        top_low_balance = [{
            "tenant_id": str(t.id), "tenant_name": t.tenant_name,
            "wallet_balance": float(w.credit_balance), "health_band": t.health_band,
        } for w, t in low_bal_result.all()]

        # Deposit status breakdown
        dep_result = await self.db.execute(select(SecurityDeposit.status, func.count()).group_by(SecurityDeposit.status))
        deposit_status_breakdown = {status: cnt for status, cnt in dep_result.all()}

        # Top commission contributors
        comm_result = await self.db.execute(
            select(CommissionRecord.tenant_id, func.sum(CommissionRecord.commission_amount).label("total"))
            .group_by(CommissionRecord.tenant_id).order_by(func.sum(CommissionRecord.commission_amount).desc()).limit(10))
        comm_rows = comm_result.all()
        tenant_ids = [row[0] for row in comm_rows]
        tenant_map = {}
        if tenant_ids:
            tres = await self.db.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))
            tenant_map = {t.id: t.tenant_name for t in tres.scalars().all()}
        top_commission_contributors = [{
            "tenant_id": str(tid), "tenant_name": tenant_map.get(tid, "—"), "commission_total": float(total),
        } for tid, total in comm_rows]

        # Recent finance activity — combine the most recent rows across the 4 ledgers
        activity: list[dict] = []
        wt_result = await self.db.execute(select(WalletTransaction).order_by(WalletTransaction.created_at.desc()).limit(10))
        for t in wt_result.scalars().all():
            activity.append({"type": "wallet_transaction", "label": f"{t.txn_type} — ₹{t.amount}",
                              "tenant_id": str(t.tenant_id), "created_at": t.created_at.isoformat()})
        sdt_result = await self.db.execute(select(SecurityDepositTransaction).order_by(SecurityDepositTransaction.created_at.desc()).limit(10))
        for t in sdt_result.scalars().all():
            activity.append({"type": "deposit_transaction", "label": f"{t.txn_type} — ₹{t.amount}",
                              "tenant_id": str(t.tenant_id), "created_at": t.created_at.isoformat()})
        claims_result = await self.db.execute(select(WarrantyClaim).order_by(WarrantyClaim.updated_at.desc()).limit(10))
        for c in claims_result.scalars().all():
            activity.append({"type": "warranty_claim", "label": f"Claim {c.status} — ₹{c.amount_requested}",
                              "tenant_id": str(c.tenant_id), "created_at": (c.resolved_at or c.updated_at or c.created_at).isoformat()})
        payouts_result = await self.db.execute(select(PayoutRecord).order_by(PayoutRecord.updated_at.desc()).limit(10))
        for p in payouts_result.scalars().all():
            activity.append({"type": "payout", "label": f"Payout {p.status} — ₹{p.amount}",
                              "tenant_id": str(p.tenant_id), "created_at": (p.processed_at or p.updated_at or p.created_at).isoformat()})
        activity.sort(key=lambda x: x["created_at"], reverse=True)
        recent_activity = activity[:20]

        # Pending actions queue
        failed_topups = (await self.db.execute(
            select(func.count()).select_from(CreditTopupOrder).where(CreditTopupOrder.payment_status == "failed")
        )).scalar_one()
        deposit_verification_pending = (await self.db.execute(
            select(func.count()).select_from(SecurityDeposit).where(SecurityDeposit.status == "pending_verification")
        )).scalar_one()
        payout_pending_approval = (await self.db.execute(
            select(func.count()).select_from(PayoutRecord).where(PayoutRecord.status == "pending")
        )).scalar_one()
        claim_pending_review = (await self.db.execute(
            select(func.count()).select_from(WarrantyClaim).where(WarrantyClaim.status.in_(CLAIM_OPEN_STATUSES))
        )).scalar_one()

        at_risk = await self._commerce.get_at_risk_tenants()

        return {
            "wallet_health_distribution": wallet_health_distribution,
            "top_low_balance_tenants": top_low_balance,
            "deposit_status_breakdown": deposit_status_breakdown,
            "top_commission_contributors": top_commission_contributors,
            "recent_finance_activity": recent_activity,
            "pending_actions_queue": {
                "deposit_verification_pending": deposit_verification_pending,
                "payout_pending_approval": payout_pending_approval,
                "warranty_claim_pending_review": claim_pending_review,
                "failed_topup_payment": failed_topups,
            },
            "at_risk_tenants": at_risk["tenants"],
        }

    # ═══════════════════════════════════════════════════════════════
    # DEPOSITS
    # ═══════════════════════════════════════════════════════════════

    def _deposit_dict(self, d: SecurityDeposit, tenant: Tenant | None = None) -> dict:
        return {
            "deposit_id": str(d.id), "tenant_id": str(d.tenant_id),
            "tenant_name": tenant.tenant_name if tenant else None,
            "vertical": tenant.vertical if tenant else None,
            "city": tenant.city if tenant else None, "state": tenant.state if tenant else None,
            "required_amount": float(d.required_amount), "received_amount": float(d.total_paid),
            "pending_amount": max(float(d.required_amount - d.total_paid), 0.0),
            "status": d.status, "hold_state": d.hold_state,
            "adjusted_amount": float(d.replenishment_total), "refunded_amount": float(d.warranty_drawn),
            "current_balance": float(d.current_balance),
            "package_purchase_id": str(d.package_purchase_id) if d.package_purchase_id else None,
            "rejection_reason": d.rejection_reason, "clarification_notes": d.clarification_notes,
            "approved_by": str(d.approved_by) if d.approved_by else None,
            "approved_at": d.approved_at.isoformat() if d.approved_at else None,
            "paid_at": d.paid_at.isoformat() if d.paid_at else None,
            "refunded_at": d.refunded_at.isoformat() if d.refunded_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }

    async def list_deposits(self, status: str | None = None, vertical: str | None = None,
                             state: str | None = None, city: str | None = None, q: str | None = None,
                             page: int = 1, page_size: int = 50,
                             sort_by: str = "created_at", sort_dir: str = "desc") -> dict:
        stmt = select(SecurityDeposit, Tenant).join(Tenant, Tenant.id == SecurityDeposit.tenant_id)
        if status: stmt = stmt.where(SecurityDeposit.status == status)
        if vertical: stmt = stmt.where(Tenant.vertical == vertical)
        if state: stmt = stmt.where(func.lower(Tenant.state) == state.lower())
        if city: stmt = stmt.where(func.lower(Tenant.city) == city.lower())
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(Tenant.tenant_name).like(like) | func.lower(Tenant.business_name).like(like))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        sort_col = SecurityDeposit.created_at if sort_by != "required_amount" else SecurityDeposit.required_amount
        stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)

        result = await self.db.execute(stmt)
        rows = result.all()
        items = [self._deposit_dict(d, t) for d, t in rows]
        return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size)}}

    async def get_deposits_summary(self) -> dict:
        deposits = (await self.db.execute(select(SecurityDeposit))).scalars().all()
        return {
            "total_deposit_accounts": len(deposits),
            "active_held_deposits": sum(1 for d in deposits if d.status == "paid"),
            "pending_deposits": sum(1 for d in deposits if d.status in ("unpaid", "partially_paid", "pending_verification")),
            "refund_pending": sum(1 for d in deposits if d.status == "refund_requested"),
            "refunded": sum(1 for d in deposits if d.status == "refunded"),
            "deposit_risk_cases": sum(1 for d in deposits if d.status in ("blocked", "forfeited")),
        }

    async def _load_deposit(self, deposit_id: uuid.UUID) -> SecurityDeposit:
        r = await self.db.execute(select(SecurityDeposit).where(SecurityDeposit.id == deposit_id))
        d = r.scalar_one_or_none()
        if not d: raise NotFoundException("SecurityDeposit", str(deposit_id))
        return d

    async def get_deposit_detail(self, deposit_id: uuid.UUID) -> dict:
        d = await self._load_deposit(deposit_id)
        tr = await self.db.execute(select(Tenant).where(Tenant.id == d.tenant_id))
        tenant = tr.scalar_one_or_none()
        ledger_r = await self.db.execute(
            select(SecurityDepositTransaction).where(SecurityDepositTransaction.deposit_id == deposit_id)
            .order_by(SecurityDepositTransaction.created_at.desc()))
        ledger = [{
            "txn_id": str(t.id), "txn_type": t.txn_type, "amount": float(t.amount),
            "balance_before": float(t.balance_before), "balance_after": float(t.balance_after),
            "notes": t.notes, "created_at": t.created_at.isoformat(),
        } for t in ledger_r.scalars().all()]
        audit = await self.list_audit_logs("security_deposit", str(deposit_id))
        return {"deposit": self._deposit_dict(d, tenant), "ledger": ledger, "audit_log": audit["audit_log"]}

    async def approve_deposit(self, deposit_id: uuid.UUID, notes: str | None = None) -> dict:
        d = await self._load_deposit(deposit_id)
        before = self._deposit_dict(d)
        d.status = "paid"; d.hold_state = "held"; d.approved_by = self.actor_id; d.approved_at = utcnow()
        if not d.paid_at: d.paid_at = utcnow()
        await self.db.flush()
        await self._audit("deposit.approve", "security_deposit", str(deposit_id), d.tenant_id, before, self._deposit_dict(d))
        return self._deposit_dict(d)

    async def reject_deposit(self, deposit_id: uuid.UUID, reason: str) -> dict:
        d = await self._load_deposit(deposit_id)
        before = self._deposit_dict(d)
        d.rejection_reason = reason
        await self.db.flush()
        await self._audit("deposit.reject", "security_deposit", str(deposit_id), d.tenant_id, before, self._deposit_dict(d))
        return self._deposit_dict(d)

    async def record_offline_deposit(self, deposit_id: uuid.UUID, amount: Decimal, reference: str | None, notes: str | None) -> dict:
        d = await self._load_deposit(deposit_id)
        before = self._deposit_dict(d)
        await credit_deposit(self.db, d, Decimal(str(amount)), DepositTxnType.INITIAL_PAYMENT,
                              reference, notes or "Offline deposit recorded by admin", self.actor_id)
        if d.total_paid >= d.required_amount:
            d.status = "paid"; d.hold_state = "held"
            if not d.paid_at: d.paid_at = utcnow()
        else:
            d.status = "partially_paid"
        await self._audit("deposit.record_offline", "security_deposit", str(deposit_id), d.tenant_id, before, self._deposit_dict(d))
        return self._deposit_dict(d)

    async def refund_deposit(self, deposit_id: uuid.UUID, amount: Decimal, reason: str) -> dict:
        d = await self._load_deposit(deposit_id)
        before = self._deposit_dict(d)
        await debit_deposit(self.db, d, Decimal(str(amount)), "refund", None, reason, self.actor_id)
        d.status = "refunded"; d.hold_state = "released"; d.refunded_at = utcnow()
        await self._audit("deposit.refund", "security_deposit", str(deposit_id), d.tenant_id, before, self._deposit_dict(d))
        return self._deposit_dict(d)

    async def adjust_deposit(self, deposit_id: uuid.UUID, amount: Decimal, reason: str, category: str = "manual") -> dict:
        d = await self._load_deposit(deposit_id)
        before = self._deposit_dict(d)
        await self._commerce.admin_adjust_deposit(d.tenant_id, Decimal(str(amount)), reason, category)
        if d.status == "paid" and d.current_balance < d.required_amount:
            d.status = "partially_adjusted"
        await self._audit("deposit.adjust", "security_deposit", str(deposit_id), d.tenant_id, before, self._deposit_dict(d))
        return self._deposit_dict(d)

    async def export_deposits(self, **filters) -> list[dict]:
        filters.setdefault("page", 1); filters["page_size"] = 5000
        data = await self.list_deposits(**filters)
        return data["items"]

    # ═══════════════════════════════════════════════════════════════
    # CREDIT TOP-UPS
    # ═══════════════════════════════════════════════════════════════

    async def list_topups(self, tenant_id: uuid.UUID | None = None, payment_status: str | None = None,
                           q: str | None = None, page: int = 1, page_size: int = 50,
                           sort_by: str = "created_at", sort_dir: str = "desc") -> dict:
        stmt = select(CreditTopupOrder, Tenant).join(Tenant, Tenant.id == CreditTopupOrder.tenant_id)
        if tenant_id: stmt = stmt.where(CreditTopupOrder.tenant_id == tenant_id)
        if payment_status: stmt = stmt.where(CreditTopupOrder.payment_status == payment_status)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                func.lower(func.coalesce(CreditTopupOrder.order_ref, "")).like(like) |
                func.lower(Tenant.tenant_name).like(like)
            )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()
        sort_col = CreditTopupOrder.created_at if sort_by != "amount_paid" else CreditTopupOrder.amount_paid
        stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.db.execute(stmt)
        items = []
        for t, tenant in result.all():
            d = t.to_dict(); d["tenant_name"] = tenant.tenant_name
            items.append(d)
        return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size)}}

    async def get_topups_summary(self) -> dict:
        topups = (await self.db.execute(select(CreditTopupOrder))).scalars().all()
        now = utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return {
            "total_topups": len(topups),
            "total_topup_value": float(sum((t.amount_paid for t in topups), Decimal("0"))),
            "pending_topups": sum(1 for t in topups if t.payment_status in ("initiated", "paid_pending_credit")),
            "failed_topups": sum(1 for t in topups if t.payment_status == "failed"),
            "refunded_topups": sum(1 for t in topups if t.payment_status in ("refunded", "partially_refunded")),
            "topup_value_this_month": float(sum(
                (t.amount_paid for t in topups if t.created_at and t.created_at >= month_start), Decimal("0"))),
        }

    async def _load_topup(self, topup_id: uuid.UUID) -> CreditTopupOrder:
        r = await self.db.execute(select(CreditTopupOrder).where(CreditTopupOrder.id == topup_id))
        t = r.scalar_one_or_none()
        if not t: raise NotFoundException("CreditTopupOrder", str(topup_id))
        return t

    async def get_topup_detail(self, topup_id: uuid.UUID) -> dict:
        t = await self._load_topup(topup_id)
        tr = await self.db.execute(select(Tenant).where(Tenant.id == t.tenant_id))
        tenant = tr.scalar_one_or_none()
        pkg = None
        if t.credit_package_id:
            pr = await self.db.execute(select(CreditPackage).where(CreditPackage.id == t.credit_package_id))
            p = pr.scalar_one_or_none()
            pkg = {"package_id": str(p.id), "name": p.name} if p else None
        ledger_entry = None
        if t.usage_credit_ledger_event_id:
            from app.engines.tenant_engine.models import UsageCreditLedger
            lr = await self.db.execute(select(UsageCreditLedger).where(
                UsageCreditLedger.id == t.usage_credit_ledger_event_id))
            led = lr.scalar_one_or_none()
            if led:
                ledger_entry = {"ledger_id": str(led.id), "amount": float(led.credit_delta),
                                 "balance_after": float(led.balance_after),
                                 "created_at": led.created_at.isoformat()}
        elif t.wallet_transaction_id:
            # Legacy top-ups granted before FINAL-L5-05K -- historical
            # reference only, no new rows are ever created here.
            wr = await self.db.execute(select(WalletTransaction).where(WalletTransaction.id == t.wallet_transaction_id))
            w = wr.scalar_one_or_none()
            if w:
                ledger_entry = {"txn_id": str(w.id), "amount": float(w.amount),
                                 "balance_after": float(w.balance_after), "created_at": w.created_at.isoformat(),
                                 "legacy": True}
        audit = await self.list_audit_logs("credit_topup_order", str(topup_id))
        d = t.to_dict(); d["tenant_name"] = tenant.tenant_name if tenant else None
        return {"topup": d, "package": pkg, "ledger_entry": ledger_entry, "audit_log": audit["audit_log"]}

    async def retry_credit_posting(self, topup_id: uuid.UUID) -> dict:
        """FINAL-L5-05K: grants through the same canonical
        UsageCreditService.grant_topup_credit identity
        (topup_credit_grant:{topup_id}:1) that confirm_purchase uses --
        if confirm_purchase already granted (e.g. this retry fires after a
        transient failure that happened *after* the grant but *before* the
        topup row was updated), this becomes a safe idempotent no-op
        instead of a second, TenantWallet-targeted credit."""
        from app.engines.usage_credits.service import UsageCreditService
        t = await self._load_topup(topup_id)
        if t.wallet_credit_status == "credited":
            raise ServiceOSException("CONFLICT", "Credits have already been posted for this top-up.")
        before = t.to_dict()
        total = t.credits_purchased + t.bonus_credits
        uc_svc = UsageCreditService(self.db, actor_id=self.actor_id, actor_role=self.actor_role,
                                     request_id=self.request_id)
        grant = await uc_svc.grant_topup_credit(
            tenant_id=t.tenant_id, topup_order_id=str(t.id), amount=total,
            reason="Retried credit posting from Finance Hub",
        )
        t.usage_credit_ledger_event_id = uuid.UUID(grant["ledger_id"])
        t.wallet_credit_status = "credited"
        t.payment_status = "credited"
        await self._audit("topup.retry_credit", "credit_topup_order", str(topup_id), t.tenant_id, before, t.to_dict())
        return t.to_dict()

    async def refund_topup(self, topup_id: uuid.UUID, amount: Decimal, reason: str) -> dict:
        t = await self._load_topup(topup_id)
        before = t.to_dict()
        t.refunded_amount = Decimal(str(amount))
        t.payment_status = "refunded" if Decimal(str(amount)) >= t.amount_paid else "partially_refunded"
        t.failure_reason = t.failure_reason or reason
        await self._audit("topup.refund", "credit_topup_order", str(topup_id), t.tenant_id, before, t.to_dict())
        return t.to_dict()

    async def export_topups(self, **filters) -> list[dict]:
        filters.setdefault("page", 1); filters["page_size"] = 5000
        data = await self.list_topups(**filters)
        return data["items"]

    # ═══════════════════════════════════════════════════════════════
    # WARRANTY CLAIMS
    # ═══════════════════════════════════════════════════════════════

    def _claim_dict(self, c: WarrantyClaim, tenant: Tenant | None = None) -> dict:
        return {
            "claim_id": str(c.id), "tenant_id": str(c.tenant_id),
            "tenant_name": tenant.tenant_name if tenant else None,
            "customer_id": str(c.customer_id), "job_id": c.job_id, "claim_type": c.claim_type,
            "description": c.description, "amount_requested": float(c.amount_requested),
            "amount_approved": float(c.amount_approved) if c.amount_approved is not None else None,
            "status": c.status, "assigned_reviewer_id": str(c.assigned_reviewer_id) if c.assigned_reviewer_id else None,
            "admin_notes": c.admin_notes, "rejection_reason": c.rejection_reason,
            "settled_at": c.settled_at.isoformat() if c.settled_at else None,
            "settled_amount": float(c.settled_amount) if c.settled_amount is not None else None,
            "documents_requested_at": c.documents_requested_at.isoformat() if c.documents_requested_at else None,
            "documents_requested_notes": c.documents_requested_notes,
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }

    async def list_claims(self, status: str | None = None, category: str | None = None, q: str | None = None,
                           page: int = 1, page_size: int = 50,
                           sort_by: str = "created_at", sort_dir: str = "desc") -> dict:
        stmt = select(WarrantyClaim, Tenant).join(Tenant, Tenant.id == WarrantyClaim.tenant_id)
        if status: stmt = stmt.where(WarrantyClaim.status == status)
        if category: stmt = stmt.where(WarrantyClaim.claim_type == category)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(WarrantyClaim.job_id).like(like) | func.lower(Tenant.tenant_name).like(like))
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()
        sort_col = WarrantyClaim.created_at if sort_by != "amount_requested" else WarrantyClaim.amount_requested
        stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.db.execute(stmt)
        items = [self._claim_dict(c, t) for c, t in result.all()]
        return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size)}}

    async def get_claims_summary(self) -> dict:
        claims = (await self.db.execute(select(WarrantyClaim))).scalars().all()
        return {
            "total_claims": len(claims),
            "pending_review": sum(1 for c in claims if c.status in ("pending", "pending_review")),
            "investigation_ongoing": sum(1 for c in claims if c.status in ("investigating", "awaiting_documents")),
            "approved_claims": sum(1 for c in claims if c.status == "approved"),
            "rejected_claims": sum(1 for c in claims if c.status == "rejected"),
            "settled_value": float(sum((c.settled_amount or Decimal("0")) for c in claims if c.status == "settled")),
        }

    async def _load_claim(self, claim_id: uuid.UUID) -> WarrantyClaim:
        r = await self.db.execute(select(WarrantyClaim).where(WarrantyClaim.id == claim_id))
        c = r.scalar_one_or_none()
        if not c: raise NotFoundException("WarrantyClaim", str(claim_id))
        return c

    async def get_claim_detail(self, claim_id: uuid.UUID) -> dict:
        c = await self._load_claim(claim_id)
        tr = await self.db.execute(select(Tenant).where(Tenant.id == c.tenant_id))
        tenant = tr.scalar_one_or_none()
        audit = await self.list_audit_logs("warranty_claim", str(claim_id))
        return {"claim": self._claim_dict(c, tenant), "audit_log": audit["audit_log"]}

    async def assign_reviewer(self, claim_id: uuid.UUID, reviewer_id: uuid.UUID) -> dict:
        c = await self._load_claim(claim_id)
        before = self._claim_dict(c)
        c.assigned_reviewer_id = reviewer_id
        if c.status == "pending": c.status = "pending_review"
        await self._audit("claim.assign_reviewer", "warranty_claim", str(claim_id), c.tenant_id, before, self._claim_dict(c))
        return self._claim_dict(c)

    async def request_documents(self, claim_id: uuid.UUID, notes: str) -> dict:
        c = await self._load_claim(claim_id)
        before = self._claim_dict(c)
        c.status = "awaiting_documents"
        c.documents_requested_at = utcnow(); c.documents_requested_notes = notes
        await self._audit("claim.request_documents", "warranty_claim", str(claim_id), c.tenant_id, before, self._claim_dict(c))
        return self._claim_dict(c)

    async def approve_claim(self, claim_id: uuid.UUID, amount_approved: Decimal, admin_notes: str | None = None) -> dict:
        before = self._claim_dict(await self._load_claim(claim_id))
        result = await self._commerce.approve_claim(claim_id, Decimal(str(amount_approved)), admin_notes)
        await self._audit("claim.approve", "warranty_claim", str(claim_id), uuid.UUID(before["tenant_id"]), before, result)
        return result

    async def reject_claim(self, claim_id: uuid.UUID, rejection_reason: str, admin_notes: str | None = None) -> dict:
        before = self._claim_dict(await self._load_claim(claim_id))
        result = await self._commerce.reject_claim(claim_id, rejection_reason, admin_notes)
        await self._audit("claim.reject", "warranty_claim", str(claim_id), uuid.UUID(before["tenant_id"]), before, result)
        return result

    async def settle_claim(self, claim_id: uuid.UUID) -> dict:
        c = await self._load_claim(claim_id)
        if c.status != "approved":
            raise ServiceOSException("CONFLICT", "Only approved claims can be settled.")
        before = self._claim_dict(c)
        c.status = "settled"; c.settled_at = utcnow(); c.settled_amount = c.amount_approved
        await self._audit("claim.settle", "warranty_claim", str(claim_id), c.tenant_id, before, self._claim_dict(c))
        return self._claim_dict(c)

    async def export_claims(self, **filters) -> list[dict]:
        filters.setdefault("page", 1); filters["page_size"] = 5000
        data = await self.list_claims(**filters)
        return data["items"]

    # ═══════════════════════════════════════════════════════════════
    # PAYOUTS
    # ═══════════════════════════════════════════════════════════════

    def _payout_dict(self, p: PayoutRecord, tenant: Tenant | None = None) -> dict:
        return {
            "payout_id": str(p.id), "payout_number": p.payout_number,
            "tenant_id": str(p.tenant_id), "tenant_name": tenant.tenant_name if tenant else None,
            "payout_type": p.payout_type, "requested_amount": float(p.amount),
            "approved_amount": float(p.approved_amount) if p.approved_amount is not None else None,
            "status": p.status, "gateway": p.gateway, "method": p.gateway,
            "gateway_transfer_id": p.gateway_transfer_id,
            "approved_by": str(p.approved_by) if p.approved_by else None,
            "approved_at": p.approved_at.isoformat() if p.approved_at else None,
            "rejection_reason": p.rejection_reason, "failure_reason": p.failure_reason,
            "requested_on": p.created_at.isoformat() if p.created_at else None,
            "processed_on": p.processed_at.isoformat() if p.processed_at else None,
        }

    async def list_payouts(self, status: str | None = None, tenant_id: uuid.UUID | None = None, q: str | None = None,
                            page: int = 1, page_size: int = 50,
                            sort_by: str = "created_at", sort_dir: str = "desc") -> dict:
        stmt = select(PayoutRecord, Tenant).join(Tenant, Tenant.id == PayoutRecord.tenant_id)
        if status: stmt = stmt.where(PayoutRecord.status == status)
        if tenant_id: stmt = stmt.where(PayoutRecord.tenant_id == tenant_id)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(func.coalesce(PayoutRecord.payout_number, "")).like(like) |
                              func.lower(Tenant.tenant_name).like(like))
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()
        sort_col = PayoutRecord.created_at if sort_by != "amount" else PayoutRecord.amount
        stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        result = await self.db.execute(stmt)
        items = [self._payout_dict(p, t) for p, t in result.all()]
        return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size)}}

    async def get_payouts_summary(self) -> dict:
        payouts = (await self.db.execute(select(PayoutRecord))).scalars().all()
        return {
            "pending_payouts": sum(1 for p in payouts if p.status == "pending"),
            "approved_payouts": sum(1 for p in payouts if p.status == "approved"),
            "processing": sum(1 for p in payouts if p.status == "processing"),
            "failed_payouts": sum(1 for p in payouts if p.status == "failed"),
            "completed_payouts": sum(1 for p in payouts if p.status == "completed"),
            "total_payout_value": float(sum((p.amount for p in payouts), Decimal("0"))),
        }

    async def _load_payout(self, payout_id: uuid.UUID) -> PayoutRecord:
        r = await self.db.execute(select(PayoutRecord).where(PayoutRecord.id == payout_id))
        p = r.scalar_one_or_none()
        if not p: raise NotFoundException("PayoutRecord", str(payout_id))
        return p

    async def get_payout_detail(self, payout_id: uuid.UUID) -> dict:
        p = await self._load_payout(payout_id)
        tr = await self.db.execute(select(Tenant).where(Tenant.id == p.tenant_id))
        tenant = tr.scalar_one_or_none()
        audit = await self.list_audit_logs("payout_record", str(payout_id))
        return {"payout": self._payout_dict(p, tenant), "bank_account": p.bank_account, "audit_log": audit["audit_log"]}

    def _require_status(self, p: PayoutRecord, allowed: tuple[str, ...]) -> None:
        if p.status not in allowed:
            raise ServiceOSException("CONFLICT",
                f"Payout is '{p.status}'; expected one of {allowed} for this action.")

    async def approve_payout(self, payout_id: uuid.UUID, approved_amount: Decimal | None = None) -> dict:
        p = await self._load_payout(payout_id)
        self._require_status(p, ("pending",))
        before = self._payout_dict(p)
        p.status = "approved"
        p.approved_amount = Decimal(str(approved_amount)) if approved_amount is not None else p.amount
        p.approved_by = self.actor_id; p.approved_at = utcnow()
        await self._audit("payout.approve", "payout_record", str(payout_id), p.tenant_id, before, self._payout_dict(p))
        return self._payout_dict(p)

    async def reject_payout(self, payout_id: uuid.UUID, reason: str) -> dict:
        p = await self._load_payout(payout_id)
        self._require_status(p, ("pending", "approved"))
        before = self._payout_dict(p)
        p.status = "rejected"; p.rejection_reason = reason
        await self._audit("payout.reject", "payout_record", str(payout_id), p.tenant_id, before, self._payout_dict(p))
        return self._payout_dict(p)

    async def mark_processing(self, payout_id: uuid.UUID) -> dict:
        p = await self._load_payout(payout_id)
        self._require_status(p, ("approved",))
        before = self._payout_dict(p)
        p.status = "processing"
        await self._audit("payout.mark_processing", "payout_record", str(payout_id), p.tenant_id, before, self._payout_dict(p))
        return self._payout_dict(p)

    async def mark_completed(self, payout_id: uuid.UUID, gateway_transfer_id: str | None = None) -> dict:
        p = await self._load_payout(payout_id)
        self._require_status(p, ("processing",))
        before = self._payout_dict(p)
        p.status = "completed"; p.processed_at = utcnow()
        if gateway_transfer_id: p.gateway_transfer_id = gateway_transfer_id
        await self._audit("payout.mark_completed", "payout_record", str(payout_id), p.tenant_id, before, self._payout_dict(p))
        return self._payout_dict(p)

    async def mark_failed(self, payout_id: uuid.UUID, failure_reason: str) -> dict:
        p = await self._load_payout(payout_id)
        self._require_status(p, ("processing", "approved"))
        before = self._payout_dict(p)
        p.status = "failed"; p.failure_reason = failure_reason
        await self._audit("payout.mark_failed", "payout_record", str(payout_id), p.tenant_id, before, self._payout_dict(p))
        return self._payout_dict(p)

    async def export_payouts(self, **filters) -> list[dict]:
        filters.setdefault("page", 1); filters["page_size"] = 5000
        data = await self.list_payouts(**filters)
        return data["items"]

    # ═══════════════════════════════════════════════════════════════
    # WALLETS
    # ═══════════════════════════════════════════════════════════════

    async def list_wallets(self, q: str | None = None, health_band: str | None = None,
                            page: int = 1, page_size: int = 50) -> dict:
        stmt = select(TenantWallet, Tenant).join(Tenant, Tenant.id == TenantWallet.tenant_id)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(Tenant.tenant_name).like(like))
        if health_band:
            stmt = stmt.where(Tenant.health_band == health_band)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(TenantWallet.credit_balance.asc()).limit(page_size).offset((page - 1) * page_size)
        result = await self.db.execute(stmt)
        items = [{
            "wallet_id": str(w.id), "tenant_id": str(w.tenant_id), "tenant_name": t.tenant_name,
            "available_balance": float(w.credit_balance), "reserved_balance": float(w.reserved_balance),
            "low_balance_threshold": float(w.low_balance_threshold) if w.low_balance_threshold is not None else None,
            "last_transaction_at": w.last_transaction_at.isoformat() if w.last_transaction_at else None,
            "health_band": t.health_band, "is_active": w.is_active,
        } for w, t in result.all()]
        return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size)}}

    async def get_wallet_ledger(self, wallet_id: uuid.UUID, page: int = 1, page_size: int = 50) -> dict:
        wr = await self.db.execute(select(TenantWallet).where(TenantWallet.id == wallet_id))
        w = wr.scalar_one_or_none()
        if not w: raise NotFoundException("TenantWallet", str(wallet_id))
        tr = await self.db.execute(select(Tenant).where(Tenant.id == w.tenant_id))
        tenant = tr.scalar_one_or_none()
        count_stmt = select(func.count()).select_from(WalletTransaction).where(WalletTransaction.tenant_id == w.tenant_id)
        total = (await self.db.execute(count_stmt)).scalar_one()
        txn_stmt = (select(WalletTransaction).where(WalletTransaction.tenant_id == w.tenant_id)
                    .order_by(WalletTransaction.created_at.desc()).limit(page_size).offset((page - 1) * page_size))
        txns = (await self.db.execute(txn_stmt)).scalars().all()
        return {
            "wallet": {
                "wallet_id": str(w.id), "tenant_id": str(w.tenant_id),
                "tenant_name": tenant.tenant_name if tenant else None,
                "available_balance": float(w.credit_balance), "reserved_balance": float(w.reserved_balance),
                "lifetime_purchased": float(w.lifetime_purchased), "lifetime_consumed": float(w.lifetime_consumed),
                "low_balance_threshold": float(w.low_balance_threshold) if w.low_balance_threshold is not None else None,
                "health_band": tenant.health_band if tenant else None, "is_active": w.is_active,
            },
            "ledger": [{
                "txn_id": str(t.id), "txn_type": t.txn_type, "amount": float(t.amount),
                "balance_before": float(t.balance_before), "balance_after": float(t.balance_after),
                "reference_id": t.reference_id, "reference_type": t.reference_type,
                "description": t.description, "created_at": t.created_at.isoformat(),
            } for t in txns],
            "pagination": {"page": page, "page_size": page_size, "total": total,
                           "total_pages": max(1, (total + page_size - 1) // page_size)},
        }
