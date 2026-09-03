"""Finance Hub Engine — FinanceHubService.

Composes platform_commerce (wallets/warranty) and payment (payouts)
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

from app.engines.platform_commerce.models import (
    WalletTransaction,
    WarrantyClaim, CommissionRecord, CreditPackage,
)
from app.engines.platform_commerce.service import CommerceService
from app.engines.payment.models import PayoutRecord
from app.engines.payment.service import PaymentService
from app.engines.security.models import PlatformAuditLog
from app.engines.tenant_engine.models import Tenant, TenantBilling, UsageCreditLedger
from app.exceptions import ServiceOSException, NotFoundException

logger = structlog.get_logger("finance_hub.service")
utcnow = lambda: datetime.now(timezone.utc)

LOW_BALANCE_DEFAULT_THRESHOLD = Decimal("500.00")

CLAIM_OPEN_STATUSES = ("provider_action_required", "provider_in_progress", "admin_review")
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
            select(func.count()).select_from(TenantBilling)
        )).scalar_one()
        low_balance_wallets = (await self.db.execute(
            select(func.count()).select_from(TenantBilling).where(
                TenantBilling.credit_balance <= LOW_BALANCE_DEFAULT_THRESHOLD,
            )
        )).scalar_one()
        credits_issued = (await self.db.execute(
            select(func.coalesce(func.sum(UsageCreditLedger.credit_delta), 0)).where(
                UsageCreditLedger.credit_delta > 0,
            )
        )).scalar_one()
        # MODULE-L5-10: "commission earned" must count only commission actually
        # COLLECTED. Summing every status counted refunded commission (given back),
        # failed/pending (never collected) and waived (deliberately not charged) as
        # earnings — overstating the platform's headline commission number.
        commission_earned = (await self.db.execute(
            select(func.coalesce(func.sum(CommissionRecord.commission_amount), 0))
            .where(CommissionRecord.status == "deducted")
        )).scalar_one()
        pending_claims = (await self.db.execute(
            select(func.count()).select_from(WarrantyClaim).where(WarrantyClaim.status.in_(CLAIM_OPEN_STATUSES))
        )).scalar_one()
        pending_payouts = (await self.db.execute(
            select(func.count()).select_from(PayoutRecord).where(PayoutRecord.status.in_(PAYOUT_OPEN_STATUSES))
        )).scalar_one()
        at_risk = (await self.db.execute(
            select(func.count()).select_from(Tenant).where(Tenant.health_band.in_(["at_risk", "critical"]), Tenant.status == "active")
        )).scalar_one()

        return {
            "active_wallets": active_wallets,
            "low_balance_wallets": low_balance_wallets,
            "credits_issued": float(credits_issued),
            "commission_earned": float(commission_earned),
            "pending_warranty_claims": pending_claims,
            "pending_payouts": pending_payouts,
            "at_risk_tenants": at_risk,
        }

    async def get_finance_overview(self) -> dict:
        # Wallet health distribution (reuses Tenant.health_band, already fed by credit_wallet_health signal)
        band_result = await self.db.execute(
            select(Tenant.health_band, func.count()).where(Tenant.status == "active").group_by(Tenant.health_band))
        wallet_health_distribution = {band: cnt for band, cnt in band_result.all()}

        # Top low-balance tenants
        low_bal_result = await self.db.execute(
            select(TenantBilling, Tenant).join(Tenant, Tenant.id == TenantBilling.tenant_id)
            .order_by(TenantBilling.credit_balance.asc()).limit(10))
        top_low_balance = [{
            "tenant_id": str(t.id), "tenant_name": t.tenant_name,
            "wallet_balance": float(w.credit_balance), "health_band": t.health_band,
        } for w, t in low_bal_result.all()]


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
        wt_result = await self.db.execute(select(UsageCreditLedger).order_by(UsageCreditLedger.created_at.desc()).limit(10))
        for t in wt_result.scalars().all():
            activity.append({"type": "usage_credit", "label": f"{t.event_type} — {t.credit_delta} credits",
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
            "top_commission_contributors": top_commission_contributors,
            "recent_finance_activity": recent_activity,
            "pending_actions_queue": {
                "payout_pending_approval": payout_pending_approval,
                "warranty_claim_pending_review": claim_pending_review,
                "failed_topup_payment": failed_topups,
            },
            "at_risk_tenants": at_risk["tenants"],
        }

    # ═══════════════════════════════════════════════════════════════
    # DEPOSITS
    # ═══════════════════════════════════════════════════════════════

    # The platform deposit console (list/detail/approve/reject/record-offline/
    # refund/adjust/export) was removed with the deposit itself in migration
    # 318. A tenant now buys a top-up plan whose credit is spent down as
    # commission, so there is no held balance for an admin to administer.

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
        # MODULE-L5-10: "value" must count only top-ups where money was actually
        # received. Summing amount_paid across ALL statuses counted initiated /
        # failed / cancelled orders (never paid) as revenue, overstating the total.
        PAID = ("credited", "paid_pending_credit", "refunded", "partially_refunded")
        paid_topups = [t for t in topups if t.payment_status in PAID]
        return {
            "total_topups": len(topups),
            "total_topup_value": float(sum((t.amount_paid for t in paid_topups), Decimal("0"))),
            "pending_topups": sum(1 for t in topups if t.payment_status in ("initiated", "paid_pending_credit")),
            "failed_topups": sum(1 for t in topups if t.payment_status == "failed"),
            "refunded_topups": sum(1 for t in topups if t.payment_status in ("refunded", "partially_refunded")),
            "topup_value_this_month": float(sum(
                (t.amount_paid for t in paid_topups if t.created_at and t.created_at >= month_start), Decimal("0"))),
        }

    async def _load_topup(self, topup_id: uuid.UUID, *, for_update: bool = False) -> CreditTopupOrder:
        stmt = select(CreditTopupOrder).where(CreditTopupOrder.id == topup_id)
        if for_update:
            stmt = stmt.with_for_update()
        r = await self.db.execute(stmt)
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
        credit_ledger: list[dict] = []
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
        # Show the complete immutable credit history for this order, including
        # proportional reversals from partial/full monetary refunds.
        from app.engines.tenant_engine.models import UsageCreditLedger
        ledger_rows = (await self.db.execute(
            select(UsageCreditLedger).where(
                UsageCreditLedger.source_type == "FINANCE_HUB_CREDIT_TOPUP",
                UsageCreditLedger.source_id == str(t.id),
            ).order_by(UsageCreditLedger.created_at.asc(), UsageCreditLedger.id.asc())
        )).scalars().all()
        credit_ledger = [row.to_dict() for row in ledger_rows]
        audit = await self.list_audit_logs("credit_topup_order", str(topup_id))
        d = t.to_dict(); d["tenant_name"] = tenant.tenant_name if tenant else None
        return {"topup": d, "package": pkg, "ledger_entry": ledger_entry,
                "credit_ledger": credit_ledger, "audit_log": audit["audit_log"]}

    async def retry_credit_posting(self, topup_id: uuid.UUID) -> dict:
        """FINAL-L5-05K: grants through the same canonical
        UsageCreditService.grant_topup_credit identity
        (topup_credit_grant:{topup_id}:1) that confirm_purchase uses --
        if confirm_purchase already granted (e.g. this retry fires after a
        transient failure that happened *after* the grant but *before* the
        topup row was updated), this becomes a safe idempotent no-op
        instead of a second, TenantWallet-targeted credit."""
        from app.engines.usage_credits.service import UsageCreditService
        t = await self._load_topup(topup_id, for_update=True)
        if t.wallet_credit_status == "credited":
            raise ServiceOSException("CONFLICT", "Credits have already been posted for this top-up.")
        if t.payment_status not in ("paid_pending_credit", "failed"):
            raise ServiceOSException("TOPUP_INVALID_STATE",
                f"Credit posting cannot be retried for a top-up in '{t.payment_status}' state.", status_code=409)
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
        t = await self._load_topup(topup_id, for_update=True)
        amount = Decimal(str(amount))
        # MODULE-L5-10: refunded_amount used to be OVERWRITTEN (t.refunded_amount
        # = amount), so a second partial refund silently lost the first, and there
        # was no cap — an admin could record a refund larger than amount_paid, or
        # refund a fully-refunded order again. Accumulate and cap at what was paid.
        if amount <= Decimal("0"):
            raise ServiceOSException("VALIDATION_ERROR",
                "Refund amount must be positive.", status_code=422)
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "A refund reason is required.", status_code=422)
        if t.payment_status not in ("credited", "partially_refunded"):
            raise ServiceOSException("TOPUP_INVALID_STATE",
                f"A top-up in '{t.payment_status}' state cannot be refunded.", status_code=409)
        already = Decimal(str(t.refunded_amount or "0"))
        paid = Decimal(str(t.amount_paid or "0"))
        if already >= paid:
            raise ServiceOSException("TOPUP_ALREADY_REFUNDED",
                "This top-up has already been fully refunded.", status_code=409)
        if already + amount > paid:
            raise ServiceOSException("TOPUP_REFUND_EXCEEDS_PAID",
                f"Refund would exceed the amount paid. Paid {paid}, already refunded "
                f"{already}, requested {amount}.", status_code=422,
                context={"paid": float(paid), "already_refunded": float(already),
                         "requested": float(amount)})
        # Revoke the proportional share of purchased credits (including
        # bonuses) in the same transaction as the cash-refund record. Without
        # this, a provider could spend the credits and recover the purchase
        # money as well. Cumulative targets make partial refunds add up exactly;
        # a full refund always removes the complete original grant.
        from decimal import ROUND_HALF_UP
        from app.engines.usage_credits.service import UsageCreditService
        total_credits = Decimal(str(t.credits_purchased or "0")) + Decimal(str(t.bonus_credits or "0"))
        new_refunded = already + amount
        old_target = (total_credits * already / paid).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        new_target = (total_credits * new_refunded / paid).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if new_refunded >= paid:
            new_target = total_credits
        credits_to_revoke = new_target - old_target
        reversal = None
        if credits_to_revoke > 0:
            uc_svc = UsageCreditService(
                self.db, actor_id=self.actor_id, actor_role=self.actor_role,
                request_id=self.request_id,
            )
            reversal = await uc_svc.revoke_topup_credit(
                tenant_id=t.tenant_id, topup_order_id=str(t.id),
                amount=credits_to_revoke, refund_version=str(new_refunded.normalize()),
                reason=reason.strip(),
            )
        before = t.to_dict()
        t.refunded_amount = new_refunded
        t.payment_status = "refunded" if t.refunded_amount >= paid else "partially_refunded"
        t.failure_reason = t.failure_reason or reason
        await self._audit("topup.refund", "credit_topup_order", str(topup_id), t.tenant_id, before, t.to_dict())
        return {**t.to_dict(), "credits_revoked": float(credits_to_revoke),
                "credit_reversal_ledger_id": reversal.get("ledger_id") if reversal else None}

    async def export_topups(self, **filters) -> list[dict]:
        filters.setdefault("page", 1); filters["page_size"] = 5000
        data = await self.list_topups(**filters)
        return data["items"]

    # ═══════════════════════════════════════════════════════════════
    # WARRANTY CLAIMS
    # ═══════════════════════════════════════════════════════════════

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
        stmt = select(TenantBilling, Tenant).join(Tenant, Tenant.id == TenantBilling.tenant_id)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(Tenant.tenant_name).like(like))
        if health_band:
            stmt = stmt.where(Tenant.health_band == health_band)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(TenantBilling.credit_balance.asc()).limit(page_size).offset((page - 1) * page_size)
        result = await self.db.execute(stmt)
        items = [{
            "wallet_id": str(w.id), "tenant_id": str(w.tenant_id), "tenant_name": t.tenant_name,
            "available_balance": float(w.credit_balance), "reserved_balance": 0.0,
            "low_balance_threshold": float(LOW_BALANCE_DEFAULT_THRESHOLD),
            "last_transaction_at": None,
            "health_band": t.health_band, "is_active": t.status == "active",
        } for w, t in result.all()]
        return {"items": items, "pagination": {"page": page, "page_size": page_size, "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size)}}

    async def get_wallet_ledger(self, wallet_id: uuid.UUID, page: int = 1, page_size: int = 50) -> dict:
        wr = await self.db.execute(select(TenantBilling).where(TenantBilling.id == wallet_id))
        w = wr.scalar_one_or_none()
        if not w: raise NotFoundException("TenantBilling", str(wallet_id))
        tr = await self.db.execute(select(Tenant).where(Tenant.id == w.tenant_id))
        tenant = tr.scalar_one_or_none()
        count_stmt = select(func.count()).select_from(UsageCreditLedger).where(UsageCreditLedger.tenant_id == w.tenant_id)
        total = (await self.db.execute(count_stmt)).scalar_one()
        txn_stmt = (select(UsageCreditLedger).where(UsageCreditLedger.tenant_id == w.tenant_id)
                    .order_by(UsageCreditLedger.created_at.desc()).limit(page_size).offset((page - 1) * page_size))
        txns = (await self.db.execute(txn_stmt)).scalars().all()
        totals = (await self.db.execute(
            select(
                func.coalesce(func.sum(UsageCreditLedger.credit_delta).filter(
                    UsageCreditLedger.credit_delta > 0), 0),
                func.coalesce(func.sum(-UsageCreditLedger.credit_delta).filter(
                    UsageCreditLedger.credit_delta < 0), 0),
            ).where(UsageCreditLedger.tenant_id == w.tenant_id)
        )).one()
        return {
            "wallet": {
                "wallet_id": str(w.id), "tenant_id": str(w.tenant_id),
                "tenant_name": tenant.tenant_name if tenant else None,
                "available_balance": float(w.credit_balance), "reserved_balance": 0.0,
                "lifetime_purchased": float(totals[0] or 0),
                "lifetime_consumed": float(totals[1] or 0),
                "low_balance_threshold": float(LOW_BALANCE_DEFAULT_THRESHOLD),
                "health_band": tenant.health_band if tenant else None,
                "is_active": bool(tenant and tenant.status == "active"),
            },
            "ledger": [{
                "txn_id": str(t.id), "txn_type": t.event_type, "amount": float(t.credit_delta),
                "balance_before": float(t.balance_before), "balance_after": float(t.balance_after),
                "reference_id": t.source_id, "reference_type": t.source_type,
                "description": t.reason, "created_at": t.created_at.isoformat(),
            } for t in txns],
            "pagination": {"page": page, "page_size": page_size, "total": total,
                           "total_pages": max(1, (total + page_size - 1) // page_size)},
        }
