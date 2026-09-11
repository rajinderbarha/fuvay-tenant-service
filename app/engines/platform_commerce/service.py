"""
Platform Commerce Engine — CommerceService (Complete Level 5)
All business logic. No router code here.
Financial operations use ledger.py for all money movements.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.integrations import razorpay_client
from app.engines.platform_commerce.constants import (
    COMMISSION_BASE_RATE, COMMISSION_HEALTH_ADJUSTMENT,
    CUSTOMER_HEALTH_BANDS, CUSTOMER_ADVANCE_REQUIRED_PCT,
    CUSTOMER_SIGNAL_WEIGHTS, CUSTOMER_DEFAULT_SIGNALS, RESERVATION_TTL_HOURS,
    TxnType, BADGE_THRESHOLDS,
    REDIS_COMMISSION_RATE, REDIS_CUSTOMER_HEALTH,
)
from app.engines.platform_commerce.ledger import (
    get_wallet_locked, debit_wallet, credit_wallet,
    reconcile_wallet,
)
from app.engines.platform_commerce.models import (
    CreditPackage, TenantWallet, WalletTransaction,
    CommissionRecord, CustomerHealthScore, CustomerCreditBalance,
    CustomerTransaction, CreditReservation, WarrantyClaim, TenantBadge,
)
from app.engines.tenant_engine.models import Tenant
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis, cache_set, cache_delete
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("commerce.service")
utcnow = lambda: datetime.now(timezone.utc)


class CommerceService:
    def __init__(self, db: AsyncSession, request_id: str = "x",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 ip_address: str | None = None, actor_tenant_id: uuid.UUID | None = None):
        self.db = db
        self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.ip_address = ip_address
        self.actor_tenant_id = actor_tenant_id

    async def _get_tenant(self, tid):
        r = await self.db.execute(select(Tenant).where(Tenant.id == tid))
        t = r.scalar_one_or_none()
        if not t:
            raise NotFoundException("Tenant", str(tid))
        return t

    # FINAL-L5-05U: a live audit found `get_deposit_status`/`initiate_deposit`/
    # `get_deposit_transactions` are gated by TENANT_BILLING_READ/MANAGE --
    # permissions `tenant_owner` legitimately holds for self-service -- but
    # neither this class nor `require_permission()` (pure RBAC, no tenant
    # scoping) ever verified the route's `tenant_id` matched the caller's
    # own tenant. Any authenticated tenant_owner could substitute another
    # tenant's UUID and read (or, for initiate, attempt to create a payment
    # order against) that tenant's Security Deposit -- a real cross-tenant
    # vulnerability, the same class already fixed for Service Areas in
    # FINAL-L5-05Q. Mirrors ServiceabilityService._assert_owns_tenant()'s
    # established pattern exactly: only enforced for actor_role=="tenant_owner"
    # (self-service callers) -- admin/super_admin callers are unaffected
    # since they reach these via a different permission and are expected to
    # act across tenants.
    async def _get_eff_rate(self, tid):
        key = REDIS_COMMISSION_RATE.format(tenant_id=tid)
        try:
            v = await self.redis.get(key)
            if v:
                import json; return json.loads(v)
        except Exception:
            pass
        t = await self._get_tenant(tid)
        plan = t.plan_type or "starter"
        band = t.health_band or "gold"
        base = COMMISSION_BASE_RATE.get(plan, Decimal("10.00"))
        adj = COMMISSION_HEALTH_ADJUSTMENT.get(band, Decimal("0.00"))
        eff = max(Decimal("1.00"), base + adj)
        res = {"base_rate": float(base), "health_adjustment": float(adj),
               "effective_rate": float(eff), "health_band": band, "plan_type": plan}
        try:
            import json
            await self.redis.setex(key, 300, json.dumps(res))
        except Exception:
            pass
        return res

    async def _publish(self, event_type, tenant_id, entity_id, payload):
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="platform_commerce",
                tenant_id=tenant_id, entity_type="commerce", entity_id=entity_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception as e:
            logger.warning("commerce.event_failed", error=str(e))

    def _txn_dict(self, t):
        return {"txn_id": str(t.id), "txn_type": t.txn_type, "amount": float(t.amount),
                "balance_before": float(t.balance_before), "balance_after": float(t.balance_after),
                "reference_id": t.reference_id, "reference_type": t.reference_type,
                "description": t.description, "created_at": t.created_at.isoformat()}

    def _pkg_dict(self, p):
        total = p.credits_amount * (1 + p.bonus_pct / 100)
        return {"package_id": str(p.id), "name": p.name, "description": p.description,
                "credits_amount": float(p.credits_amount), "price_inr": float(p.price_inr),
                "bonus_pct": float(p.bonus_pct), "total_credits": float(total),
                "validity_days": p.validity_days, "plan_restriction": p.plan_restriction,
                "is_active": p.is_active, "sort_order": p.sort_order,
                "purchase_count": p.purchase_count}

    def _claim_dict(self, c):
        overdue = bool(
            c.provider_response_due_at and c.provider_response_due_at <= utcnow()
            and c.status == "provider_action_required"
        )
        return {"claim_id": str(c.id), "tenant_id": str(c.tenant_id), "job_id": c.job_id,
                "customer_id": str(c.customer_id), "claim_type": c.claim_type,
                "description": c.description,
                "amount_requested": float(c.amount_requested),
                "amount_approved": float(c.amount_approved) if c.amount_approved else None,
                "status": c.status,
                "provider_response_due_at": c.provider_response_due_at.isoformat() if c.provider_response_due_at else None,
                "provider_responded_at": c.provider_responded_at.isoformat() if c.provider_responded_at else None,
                "provider_resolution": c.provider_resolution,
                "provider_resolved_at": c.provider_resolved_at.isoformat() if c.provider_resolved_at else None,
                "escalated_at": c.escalated_at.isoformat() if c.escalated_at else None,
                "escalation_reason": c.escalation_reason,
                "warranty_days": c.warranty_days_snapshot,
                "warranty_expires_at": c.warranty_expires_at.isoformat() if c.warranty_expires_at else None,
                "provider_response_overdue": overdue,
                "provider_credit_deducted": float(c.provider_credit_deducted or 0),
                "customer_credit_id": str(c.customer_credit_id) if c.customer_credit_id else None,
                "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                "created_at": c.created_at.isoformat()}

    def _rec_dict(self, r):
        return {"record_id": str(r.id), "job_id": r.job_id,
                "effective_rate": float(r.effective_rate), "job_value": float(r.job_value),
                "commission_amount": float(r.commission_amount),
                "wallet_balance_before": float(r.wallet_balance_before),
                "wallet_balance_after": float(r.wallet_balance_after),
                "health_band_at_time": r.health_band_at_time,
                "deducted_at": r.deducted_at.isoformat()}

    # ── Deposit (5) ────────────────────────────────────────────────────────────
    # get/initiate/confirm/list-transactions/admin-adjust deposit were all
    # removed with the security deposit in migration 318. Nothing is held
    # any more: a top-up grants spendable credit, and the credit floor is
    # what keeps a balance available to recover from.

    async def list_packages(self, tid=None):
        r = await self.db.execute(select(CreditPackage).where(CreditPackage.is_active == True)
            .order_by(CreditPackage.sort_order, CreditPackage.price_inr))
        return {"packages": [self._pkg_dict(p) for p in r.scalars().all()]}

    async def get_package(self, pid):
        r = await self.db.execute(select(CreditPackage).where(CreditPackage.id == pid))
        p = r.scalar_one_or_none()
        if not p: raise NotFoundException("CreditPackage", str(pid))
        return self._pkg_dict(p)

    async def create_package(self, data):
        p = CreditPackage(name=data["name"], description=data.get("description"),
            credits_amount=Decimal(str(data["credits_amount"])), price_inr=Decimal(str(data["price_inr"])),
            bonus_pct=Decimal(str(data.get("bonus_pct","0"))), validity_days=data.get("validity_days"),
            plan_restriction=data.get("plan_restriction"), sort_order=data.get("sort_order",0),
            created_by=self.actor_id)
        self.db.add(p); await self.db.flush()
        await self._publish("credit_package.created", "platform", str(p.id), {"name": p.name})
        return self._pkg_dict(p)

    async def update_package(self, pid, data):
        r = await self.db.execute(select(CreditPackage).where(CreditPackage.id == pid))
        p = r.scalar_one_or_none()
        if not p: raise NotFoundException("CreditPackage", str(pid))
        if "credits_amount" in data and p.purchase_count > 0:
            raise ServiceOSException("CONFLICT", "Cannot change credits_amount for a purchased package.")
        for f in ("name","description","price_inr","bonus_pct","is_active","sort_order"):
            if f in data and data[f] is not None: setattr(p, f, data[f])
        return self._pkg_dict(p)

    async def archive_package(self, pid):
        r = await self.db.execute(select(CreditPackage).where(CreditPackage.id == pid))
        p = r.scalar_one_or_none()
        if not p: raise NotFoundException("CreditPackage", str(pid))
        p.is_active = False; p.archived_at = utcnow()
        return {"package_id": str(pid), "archived": True}

    async def delete_package_permanently(self, pid):
        """Hard-delete -- only ever safe for a package that has NEVER been
        purchased (purchase_count == 0), since CreditTopupOrder.
        credit_package_id would otherwise reference a row that no longer
        exists. Archive (above) is the only option once a package has any
        purchase history -- this is a real constraint, not just a policy."""
        r = await self.db.execute(select(CreditPackage).where(CreditPackage.id == pid))
        p = r.scalar_one_or_none()
        if not p: raise NotFoundException("CreditPackage", str(pid))
        if p.purchase_count > 0:
            raise ServiceOSException("CONFLICT",
                "Cannot permanently delete a package that has been purchased. Archive it instead.")
        await self.db.delete(p)
        return {"package_id": str(pid), "deleted": True}

    # ── Wallet (8) ─────────────────────────────────────────────────────────────
    async def get_wallet(self, tid):
        rec = await reconcile_wallet(self.db, tid)
        r = await self.db.execute(select(TenantWallet).where(TenantWallet.tenant_id == tid))
        w = r.scalar_one_or_none()
        bal = float(w.credit_balance) if w else 0.0
        last_t = w.last_transaction_at.isoformat() if w and w.last_transaction_at else None
        thirty_ago = utcnow() - timedelta(days=30)
        r2 = await self.db.execute(select(func.sum(WalletTransaction.amount))
            .where(WalletTransaction.tenant_id == tid, WalletTransaction.txn_type == TxnType.COMMISSION,
                   WalletTransaction.created_at >= thirty_ago))
        comm30 = abs(float(r2.scalar_one_or_none() or 0))
        burn = round(comm30 / 30, 2)
        days = int(bal / burn) if burn > 0 else None
        return {"tenant_id": str(tid), "credit_balance": bal,
                "lifetime_purchased": float(w.lifetime_purchased) if w else 0,
                "lifetime_consumed": float(w.lifetime_consumed) if w else 0,
                "last_transaction_at": last_t, "burn_rate_daily": burn,
                "projected_days_remaining": days, "low_balance_alert": days is not None and days < 7,
                "reconciliation_ok": rec["matches"]}

    async def initiate_purchase(self, tid, pkg_id, gateway):
        # The "pay your security deposit first" gate is gone with the deposit
        # (migration 318). Buying credit is now the only prerequisite there is.
        r = await self.db.execute(select(CreditPackage).where(CreditPackage.id == pkg_id, CreditPackage.is_active == True))
        p = r.scalar_one_or_none()
        if not p: raise NotFoundException("CreditPackage", str(pkg_id))
        order = await razorpay_client.create_order(
            p.price_inr, receipt=f"purchase_{tid}_{pkg_id}",
            notes={"tenant_id": str(tid), "package_id": str(pkg_id), "type": "credit_purchase"},
            db=self.db)
        total = float(p.credits_amount * (1 + p.bonus_pct/100))
        from app.engines.finance_hub.models import CreditTopupOrder
        topup = CreditTopupOrder(
            tenant_id=tid, credit_package_id=pkg_id,
            order_ref=f"TOPUP-{str(order['id'])[-10:]}",
            credits_purchased=p.credits_amount, bonus_credits=p.credits_amount * p.bonus_pct / Decimal("100"),
            amount_paid=p.price_inr, currency="INR", payment_method=gateway,
            payment_status="initiated", wallet_credit_status="pending",
            gateway_order_id=order["id"],
        )
        self.db.add(topup); await self.db.flush()
        return {"order_id": order["id"], "package_id": str(pkg_id), "package_name": p.name,
                "credits_to_receive": total, "amount": float(p.price_inr), "currency": "INR",
                "amount_paise": int(p.price_inr*100), "gateway": gateway,
                "key": await razorpay_client.get_key_id(self.db),
                "topup_order_id": str(topup.id)}

    async def confirm_purchase(self, tid, pkg_id, order_id, payment_id, signature):
        r = await self.db.execute(select(CreditPackage).where(CreditPackage.id == pkg_id))
        p = r.scalar_one_or_none()
        if not p: raise NotFoundException("CreditPackage", str(pkg_id))

        from app.engines.finance_hub.models import CreditTopupOrder
        topup_r = await self.db.execute(select(CreditTopupOrder).where(
            CreditTopupOrder.tenant_id == tid, CreditTopupOrder.gateway_order_id == order_id))
        topup = topup_r.scalar_one_or_none()

        # MODULE-L5-10: idempotency guard. This endpoint is fired by the client
        # AND the Razorpay webhook (and is retried), so a single payment routinely
        # confirms more than once. The credit grant is idempotent on the topup id,
        # but credit_deposit() has no idempotency and purchase_count/total_revenue
        # were incremented unconditionally — so a duplicate confirm replenished the
        # security deposit TWICE and double-counted revenue for one payment. If the
        # top-up is already credited, return the same result without moving money
        # again.
        if topup is not None and topup.wallet_credit_status == "credited":
            total = p.credits_amount * (1 + p.bonus_pct / Decimal("100"))
            return {"credits_added": float(total), "base_credits": float(p.credits_amount),
                    "bonus_credits": float(total - p.credits_amount),
                    "payment_id": payment_id, "idempotent": True}

        if not await razorpay_client.verify_payment_signature(order_id, payment_id, signature, db=self.db):
            if topup:
                topup.payment_status = "failed"
                topup.wallet_credit_status = "failed"
                topup.failure_reason = "Payment signature verification failed."
            raise ServiceOSException("PAYMENT_VERIFICATION_FAILED",
                "Razorpay payment signature verification failed.")
        total = p.credits_amount * (1 + p.bonus_pct / Decimal("100"))

        # FINAL-L5-05K: credit grant moved off ledger.credit_wallet
        # (TenantWallet) onto the canonical UsageCreditService
        # (tenant_billing/usage_credit_ledger). The 5% deposit replenishment
        # that used to follow is gone with the deposit (migration 318).
        from app.engines.usage_credits.service import UsageCreditService
        uc_svc = UsageCreditService(self.db, actor_id=self.actor_id, actor_role=self.actor_role,
                                     request_id=self.request_id)
        grant_source_id = str(topup.id) if topup else f"payment:{payment_id}"
        grant = await uc_svc.grant_topup_credit(
            tenant_id=tid, topup_order_id=grant_source_id, amount=total,
            reason=f"Credit top-up purchase: {p.name}",
        )

        p.purchase_count += 1; p.total_revenue += p.price_inr
        if topup:
            topup.payment_status = "credited"
            topup.wallet_credit_status = "credited"
            topup.gateway_payment_id = payment_id
            topup.usage_credit_ledger_event_id = uuid.UUID(grant["ledger_id"])
        await self._publish("usage_credit.topup_granted", str(tid), grant["ledger_id"],
                            {"amount": float(total), "package": p.name})
        return {"credits_added": float(total), "base_credits": float(p.credits_amount),
                "bonus_credits": float(total - p.credits_amount),
                "payment_id": payment_id}

    async def get_wallet_transactions(self, tid, txn_type, limit, cursor):
        q = (select(WalletTransaction).where(WalletTransaction.tenant_id == tid)
             .order_by(WalletTransaction.created_at.desc()))
        if txn_type: q = q.where(WalletTransaction.txn_type == txn_type)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(WalletTransaction.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1); r = await self.db.execute(q)
        txns = r.scalars().all(); has_next = len(txns) > limit; txns = txns[:limit]
        nc = encode_cursor({"created_at": txns[-1].created_at.isoformat()}) if has_next and txns else None
        return {"transactions": [self._txn_dict(t) for t in txns], "has_next": has_next, "next_cursor": nc}

    async def get_wallet_balance_for_engine(self, tid):
        info = await self._get_eff_rate(tid)
        r = await self.db.execute(select(TenantWallet).where(TenantWallet.tenant_id == tid))
        w = r.scalar_one_or_none()
        return {"tenant_id": str(tid), "credit_balance": float(w.credit_balance) if w else 0.0,
                "available_balance": float(w.credit_balance) if w else 0.0,
                "health_band": info["health_band"], "commission_rate": info["effective_rate"]}

    async def engine_deduct_wallet(self, tid, job_id, amount, description):
        idem = f"engine_deduct:{job_id}"
        txn = await debit_wallet(self.db, tid, amount, TxnType.COMMISSION,
            job_id, "job", description, self.actor_id, idempotency_key=idem)
        return {"deducted": float(amount), "balance_after": float(txn.balance_after), "job_id": job_id}

    async def admin_credit_wallet(self, tid, amount, reason, category):
        txn = await credit_wallet(self.db, tid, amount, TxnType.MANUAL_CREDIT,
            None, "admin_manual", f"[{category}] {reason}", self.actor_id)
        from app.core.audit import record_platform_audit
        await record_platform_audit(
            self.db, operation="wallet.admin_credited", engine_id="commerce",
            tenant_id=tid, entity_type="wallet_transaction", entity_id=str(txn.id),
            actor_id=self.actor_id, actor_role=self.actor_role, actor_ip=self.ip_address,
            request_id=self.request_id,
            after={"amount": float(amount), "reason": reason, "category": category,
                   "balance_after": float(txn.balance_after)},
        )
        await self._publish("wallet.admin_credited", str(tid), str(txn.id),
                            {"amount": float(amount), "reason": reason})
        return {"amount_credited": float(amount), "balance_after": float(txn.balance_after)}

    async def get_wallet_projection(self, tid):
        w = await self.get_wallet(tid)
        bal = w["credit_balance"]; burn = w["burn_rate_daily"]; days = w["projected_days_remaining"]
        r = await self.db.execute(select(CreditPackage).where(CreditPackage.is_active==True)
            .order_by(CreditPackage.price_inr))
        pkgs = r.scalars().all()
        rec = None
        if burn > 0:
            monthly = burn * 30
            for p in pkgs:
                if float(p.credits_amount * (1 + p.bonus_pct/100)) >= monthly:
                    rec = self._pkg_dict(p); break
        return {"tenant_id": str(tid), "current_balance": bal, "burn_rate_daily": burn,
                "projected_days_remaining": days, "low_balance_alert": days is not None and days < 7,
                "recommended_package": rec, "monthly_commission_estimate": round(burn*30,2)}

    # ── Commission (5) ─────────────────────────────────────────────────────────
    async def get_commission_rate(self, tid):
        info = await self._get_eff_rate(tid)
        return {"tenant_id": str(tid), **info,
                "next_review_at": (utcnow() + timedelta(hours=1)).isoformat()}

    async def deduct_commission(self, tid, job_id, job_value, description=None):
        idem = f"commission:{job_id}"
        ex = await self.db.execute(select(CommissionRecord).where(CommissionRecord.job_id == job_id))
        er = ex.scalar_one_or_none()
        if er: return {**self._rec_dict(er), "idempotent": True}

        info = await self._get_eff_rate(tid)
        eff_rate = Decimal(str(info["effective_rate"])) / Decimal("100")
        commission = (Decimal(str(job_value)) * eff_rate).quantize(Decimal("0.0001"))

        txn = await debit_wallet(self.db, tid, commission, TxnType.COMMISSION,
            job_id, "job", description or f"Commission job {job_id}",
            self.actor_id, idempotency_key=idem)

        rec = CommissionRecord(tenant_id=tid, job_id=job_id,
            base_rate=Decimal(str(info["base_rate"])),
            health_adjustment=Decimal(str(info["health_adjustment"])),
            effective_rate=Decimal(str(info["effective_rate"])),
            job_value=Decimal(str(job_value)), commission_amount=commission,
            wallet_balance_before=txn.balance_before, wallet_balance_after=txn.balance_after,
            health_band_at_time=info["health_band"], idempotency_key=idem)
        self.db.add(rec); await self.db.flush()

        await self._update_wallet_signal(tid, float(txn.balance_after))
        await cache_delete(REDIS_COMMISSION_RATE.format(tenant_id=tid))
        await self._publish("commission.deducted", str(tid), str(rec.id),
                            {"job_id": job_id, "amount": float(commission)})
        logger.info("commerce.commission_deducted", tenant_id=str(tid), job_id=job_id)
        return {**self._rec_dict(rec), "idempotent": False}

    async def _update_wallet_signal(self, tid, balance):
        try:
            from app.engines.tenant_engine.health import write_health_signal
            r = await self.db.execute(select(CommissionRecord).where(CommissionRecord.tenant_id==tid)
                .order_by(CommissionRecord.deducted_at.desc()).limit(30))
            recs = r.scalars().all()
            avg = sum(float(x.commission_amount) for x in recs) / len(recs) * 30 if recs else 0
            sig = min(100.0, (balance / (avg * 2)) * 100) if avg > 0 else 100.0
            await write_health_signal(tid, "credit_wallet_health", sig)
        except Exception as e:
            logger.warning("commerce.wallet_signal_failed", error=str(e))

    async def get_commission_history(self, tid, limit, cursor):
        q = (select(CommissionRecord).where(CommissionRecord.tenant_id==tid)
             .order_by(CommissionRecord.deducted_at.desc()))
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(CommissionRecord.deducted_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1); r = await self.db.execute(q)
        recs = r.scalars().all(); has_next = len(recs) > limit; recs = recs[:limit]
        nc = encode_cursor({"created_at": recs[-1].deducted_at.isoformat()}) if has_next and recs else None
        return {"records": [self._rec_dict(x) for x in recs], "has_next": has_next, "next_cursor": nc}

    async def get_commission_projection(self, tid):
        r = await self.db.execute(select(CommissionRecord).where(CommissionRecord.tenant_id==tid)
            .order_by(CommissionRecord.deducted_at.desc()).limit(30))
        recs = r.scalars().all()
        if not recs:
            return {"tenant_id": str(tid), "projected_monthly_cost": 0, "data_available": False}
        total = sum(float(x.commission_amount) for x in recs)
        info = await self._get_eff_rate(tid)
        return {"tenant_id": str(tid), "projected_monthly_cost": round(total/len(recs)*30, 2),
                "avg_daily_burn": round(total/30, 2), "current_rate": info["effective_rate"],
                "data_available": True}

    async def get_platform_commission_summary(self):
        today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        async def _sum(since):
            r = await self.db.execute(select(func.sum(CommissionRecord.commission_amount))
                .where(CommissionRecord.deducted_at >= since))
            return float(r.scalar_one_or_none() or 0)
        return {"today": await _sum(today), "week": await _sum(today-timedelta(days=7)),
                "month": await _sum(today-timedelta(days=30))}

    # ── Customer Health (6) ────────────────────────────────────────────────────
    async def get_customer_health(self, cid, tid):
        r = await self.db.execute(select(CustomerHealthScore).where(
            CustomerHealthScore.customer_id==cid, CustomerHealthScore.tenant_id==tid))
        h = r.scalar_one_or_none()
        if not h:
            h = CustomerHealthScore(customer_id=cid, tenant_id=tid, score=Decimal("80.00"),
                band="standard", signals=dict(CUSTOMER_DEFAULT_SIGNALS),
                can_book=True, advance_required_pct=Decimal("0.00"))
            self.db.add(h); await self.db.flush()
        band = h.band
        if h.override_band and h.override_expires_at and h.override_expires_at > utcnow():
            band = h.override_band
        adv = CUSTOMER_ADVANCE_REQUIRED_PCT.get(band, Decimal("0.00"))
        return {"customer_id": str(cid), "tenant_id": str(tid), "score": float(h.score),
                "band": band, "can_book": band != "blocked", "advance_required_pct": float(adv),
                "signals": h.signals, "computed_at": h.computed_at.isoformat()}

    async def get_customer_health_history(self, cid, tid):
        return {"customer_id": str(cid), "tenant_id": str(tid), "history": []}

    async def update_customer_signal(self, cid, tid, signal, value, event_ref, event_type=None):
        if signal not in CUSTOMER_SIGNAL_WEIGHTS:
            raise ServiceOSException("VALIDATION_ERROR", f"Unknown signal: {signal}")
        idem = f"serviceos:cust_signal:{event_ref}"
        try:
            if await self.redis.exists(idem): return {"idempotent": True}
            await self.redis.setex(idem, 86400, "1")
        except Exception: pass
        r = await self.db.execute(select(CustomerHealthScore).where(
            CustomerHealthScore.customer_id==cid, CustomerHealthScore.tenant_id==tid))
        h = r.scalar_one_or_none()
        if not h:
            h = CustomerHealthScore(customer_id=cid, tenant_id=tid,
                signals=dict(CUSTOMER_DEFAULT_SIGNALS)); self.db.add(h)
        sigs = dict(h.signals); sigs[signal] = value; h.signals = sigs
        score = sum(sigs.get(k, CUSTOMER_DEFAULT_SIGNALS[k]) * w for k, w in CUSTOMER_SIGNAL_WEIGHTS.items())
        score = round(min(100.0, max(0.0, score)), 2)
        h.score = Decimal(str(score))
        band = "blocked"
        for b, (lo, hi) in CUSTOMER_HEALTH_BANDS.items():
            if lo <= score <= hi: band = b; break
        h.band = band; h.can_book = band != "blocked"
        h.advance_required_pct = CUSTOMER_ADVANCE_REQUIRED_PCT.get(band, Decimal("0.00"))
        h.computed_at = utcnow()
        return {"signal": signal, "new_score": score, "new_band": band}

    async def recompute_customer_health(self, cid, tid):
        """Rebuild health from finalized jobs and direct-payment evidence.

        Only customer-attributable outcomes are used. Provider cancellations
        and provider complaints never reduce the customer score.
        """
        from sqlalchemy import text

        row = (await self.db.execute(text("""
            SELECT
              count(DISTINCT sj.id) FILTER (WHERE sj.status='completed') AS completed,
              count(DISTINCT ae.job_id) FILTER (
                WHERE ae.event_type='customer_cancelled_booking'
              ) AS customer_cancelled,
              count(DISTINCT sj.id) FILTER (
                WHERE sj.status='customer_not_available'
              ) AS no_show,
              min(sj.created_at) AS first_job_at
            FROM service_jobs sj
            LEFT JOIN service_job_assignment_events ae
              ON ae.job_id=sj.id AND ae.tenant_id=sj.tenant_id
            WHERE sj.customer_id=:cid AND sj.tenant_id=:tid
        """), {"cid": str(cid), "tid": str(tid)})).mappings().first() or {}

        payments = (await self.db.execute(text("""
            SELECT
              count(*) FILTER (WHERE payment_status IN ('paid','verified','collected')) AS paid,
              count(*) FILTER (
                WHERE payment_status IN ('failed','unpaid')
                   OR (payment_status='pending' AND created_at < now() - interval '24 hours')
              ) AS unpaid,
              count(*) FILTER (
                WHERE reminder_count > 0
                   OR reconciliation_status IN ('needs_review','mismatch','disputed')
              ) AS delayed
            FROM service_payment_records
            WHERE customer_id=:cid AND tenant_id=:tid
        """), {"cid": str(cid), "tid": str(tid)})).mappings().first() or {}

        completed = int(row.get("completed") or 0)
        cancelled = int(row.get("customer_cancelled") or 0)
        no_show = int(row.get("no_show") or 0)
        paid = int(payments.get("paid") or 0)
        unpaid = int(payments.get("unpaid") or 0)
        delayed = int(payments.get("delayed") or 0)
        prior = 4
        payment_evidence = paid + unpaid + delayed
        payment_reliability = (
            100.0 if payment_evidence == 0
            else round((paid * 100.0 + delayed * 50.0) / payment_evidence, 2)
        )
        first_job_at = row.get("first_job_at")
        tenure_days = max(0, (utcnow() - first_job_at).days) if first_job_at else 0
        signals = {
            "booking_completion_rate": round(100.0 * (completed + prior) / (completed + cancelled + no_show + prior), 2),
            "payment_reliability": payment_reliability,
            "cancellation_rate": round(100.0 * (completed + prior) / (completed + cancelled + prior), 2),
            "no_show_rate": round(100.0 * (completed + prior) / (completed + no_show + prior), 2),
            "platform_tenure": round(50.0 + min(50.0, tenure_days / 180.0 * 50.0), 2),
        }
        score = round(sum(signals[k] * w for k, w in CUSTOMER_SIGNAL_WEIGHTS.items()), 2)
        band = next(
            (name for name, (low, _high) in sorted(
                CUSTOMER_HEALTH_BANDS.items(), key=lambda item: item[1][0], reverse=True
            ) if score >= low),
            "blocked",
        )
        existing = (await self.db.execute(select(CustomerHealthScore).where(
            CustomerHealthScore.customer_id == cid,
            CustomerHealthScore.tenant_id == tid,
        ))).scalar_one_or_none()
        if existing is None:
            existing = CustomerHealthScore(customer_id=cid, tenant_id=tid)
            self.db.add(existing)
        existing.score = Decimal(str(score))
        existing.band = band
        existing.signals = signals
        existing.can_book = band != "blocked"
        existing.advance_required_pct = CUSTOMER_ADVANCE_REQUIRED_PCT.get(band, Decimal("0.00"))
        existing.computed_at = utcnow()
        await self.db.flush()
        return await self.get_customer_health(cid, tid)

    async def get_at_risk_customers(self, tid):
        r = await self.db.execute(select(CustomerHealthScore).where(
            CustomerHealthScore.tenant_id==tid,
            CustomerHealthScore.band.in_(["cautious","restricted","blocked"])
        ).order_by(CustomerHealthScore.score))
        customers = r.scalars().all()
        return {"customers": [{"customer_id": str(c.customer_id), "score": float(c.score),
                "band": c.band, "can_book": c.can_book,
                "advance_required_pct": float(c.advance_required_pct)} for c in customers],
                "total": len(customers)}

    async def override_customer_health(self, cid, tid, band, reason, expires_days):
        r = await self.db.execute(select(CustomerHealthScore).where(
            CustomerHealthScore.customer_id==cid, CustomerHealthScore.tenant_id==tid))
        h = r.scalar_one_or_none()
        if not h:
            h = CustomerHealthScore(customer_id=cid, tenant_id=tid); self.db.add(h)
        h.override_band = band; h.override_reason = reason
        h.override_expires_at = utcnow() + timedelta(days=expires_days)
        return {"customer_id": str(cid), "override_band": band, "reason": reason,
                "expires_at": h.override_expires_at.isoformat()}

    # ── Reservations (4) ───────────────────────────────────────────────────────
    async def create_reservation(self, cid, tid, booking_id, advance_pct, booking_value):
        ex = await self.db.execute(select(CreditReservation).where(CreditReservation.booking_id==booking_id))
        if ex.scalar_one_or_none():
            raise ServiceOSException("CONFLICT", f"Reservation for {booking_id} already exists.")
        amt = (Decimal(str(booking_value)) * Decimal(str(advance_pct)) / Decimal("100")).quantize(Decimal("0.01"))
        if amt <= 0:
            return {"reservation_id": None, "reserved_amount": 0.0, "advance_required": False}
        r = await self.db.execute(select(CustomerCreditBalance).where(
            CustomerCreditBalance.customer_id==cid, CustomerCreditBalance.tenant_id==tid
        ).with_for_update(nowait=True))
        b = r.scalar_one_or_none()
        if not b or b.available_balance < amt:
            avail = float(b.available_balance) if b else 0.0
            raise ServiceOSException("PLAN_LIMIT_EXCEEDED",
                f"Insufficient credits. Need {float(amt)}, available {avail}")
        b.reserved_amount += amt
        exp = utcnow() + timedelta(hours=RESERVATION_TTL_HOURS)
        res = CreditReservation(customer_id=cid, tenant_id=tid, booking_id=booking_id,
            reserved_amount=amt, status="active", expires_at=exp)
        self.db.add(res); await self.db.flush()
        self.db.add(CustomerTransaction(customer_id=cid, tenant_id=tid,
            txn_type=TxnType.RESERVATION_CREATE, amount=-amt,
            balance_before=b.credit_balance, balance_after=b.credit_balance,
            reference_id=booking_id, reference_type="booking"))
        await self._publish("reservation.created", str(tid), str(res.id),
                            {"booking_id": booking_id, "amount": float(amt)})
        return {"reservation_id": str(res.id), "booking_id": booking_id,
                "reserved_amount": float(amt), "status": "active",
                "expires_at": exp.isoformat(), "new_available_balance": float(b.available_balance)}

    async def confirm_reservation(self, booking_id, tid):
        r = await self.db.execute(select(CreditReservation).where(
            CreditReservation.booking_id==booking_id, CreditReservation.status=="active"))
        res = r.scalar_one_or_none()
        if not res: raise NotFoundException("CreditReservation", booking_id)
        br = await self.db.execute(select(CustomerCreditBalance).where(
            CustomerCreditBalance.customer_id==res.customer_id,
            CustomerCreditBalance.tenant_id==tid).with_for_update(nowait=True))
        b = br.scalar_one_or_none()
        if b:
            b.reserved_amount -= res.reserved_amount
            b.credit_balance -= res.reserved_amount
            b.lifetime_consumed += res.reserved_amount
        res.status = "confirmed"; res.resolved_at = utcnow(); res.resolution_type = "confirmed"
        return {"reservation_id": str(res.id), "status": "confirmed",
                "confirmed_amount": float(res.reserved_amount)}

    async def release_reservation(self, booking_id, tid):
        r = await self.db.execute(select(CreditReservation).where(
            CreditReservation.booking_id==booking_id, CreditReservation.status=="active"))
        res = r.scalar_one_or_none()
        if not res: raise NotFoundException("CreditReservation", booking_id)
        br = await self.db.execute(select(CustomerCreditBalance).where(
            CustomerCreditBalance.customer_id==res.customer_id,
            CustomerCreditBalance.tenant_id==tid).with_for_update(nowait=True))
        b = br.scalar_one_or_none()
        if b: b.reserved_amount -= res.reserved_amount
        res.status = "released"; res.resolved_at = utcnow(); res.resolution_type = "released"
        await self.update_customer_signal(res.customer_id, tid, "cancellation_rate", 90.0,
                                           f"cancel_policy:{booking_id}")
        await self._publish("reservation.released", str(tid), str(res.id), {})
        return {"reservation_id": str(res.id), "status": "released",
                "released_amount": float(res.reserved_amount)}

    async def forfeit_reservation(self, booking_id, tid):
        r = await self.db.execute(select(CreditReservation).where(
            CreditReservation.booking_id==booking_id, CreditReservation.status=="active"))
        res = r.scalar_one_or_none()
        if not res: raise NotFoundException("CreditReservation", booking_id)
        br = await self.db.execute(select(CustomerCreditBalance).where(
            CustomerCreditBalance.customer_id==res.customer_id,
            CustomerCreditBalance.tenant_id==tid).with_for_update(nowait=True))
        b = br.scalar_one_or_none()
        if b:
            b.reserved_amount -= res.reserved_amount
            b.credit_balance -= res.reserved_amount
            b.lifetime_consumed += res.reserved_amount
        res.status = "forfeited"; res.resolved_at = utcnow(); res.resolution_type = "forfeited"
        await self.update_customer_signal(res.customer_id, tid, "no_show_rate", 40.0,
                                           f"no_show:{booking_id}")
        await self._publish("reservation.forfeited", str(tid), str(res.id), {})
        return {"reservation_id": str(res.id), "status": "forfeited",
                "forfeited_amount": float(res.reserved_amount)}

    # ── Warranty (6) ───────────────────────────────────────────────────────────
    async def submit_claim(self, cid, job_id, claim_type, description, media_ids, amount=None):
        # Slice 2F-37: tid/job_id were previously fully client-supplied
        # with no proof the job belongs to that tenant or to the claiming
        # customer -- a caller could file a claim (with a client-supplied
        # amount_requested) against an arbitrary tenant/job pair. Verify
        # the parent job before creating the claim.
        from app.engines.final_records.models import ServiceJob
        try:
            job_uuid = uuid.UUID(str(job_id))
        except (TypeError, ValueError):
            raise NotFoundException("Job", str(job_id))
        job_r = await self.db.execute(select(ServiceJob).where(ServiceJob.id == job_uuid))
        job = job_r.scalar_one_or_none()
        if not job or job.customer_id != cid:
            raise NotFoundException("Job", str(job_id))
        if job.status not in ("completed", "work_done", "invoice_issued", "paid"):
            raise ServiceOSException(
                "WARRANTY_JOB_NOT_COMPLETED", "Warranty claims are available only after job completion.", status_code=409,
            )
        expiry = job.warranty_expires_at
        if not expiry and job.completion_data and job.completion_data.get("completed_at"):
            expiry = datetime.fromisoformat(job.completion_data["completed_at"]) + timedelta(days=5)
        if not expiry or expiry < utcnow():
            raise ServiceOSException(
                "WARRANTY_PERIOD_EXPIRED", "The warranty period for this service has expired.", status_code=409,
                context={"warranty_expires_at": expiry.isoformat() if expiry else None},
            )
        from app.engines.invoice_payment.models import ServiceInvoice
        invoice = await self.db.scalar(
            select(ServiceInvoice).where(
                ServiceInvoice.job_id == job_uuid,
                ServiceInvoice.status != "cancelled",
            ).order_by(ServiceInvoice.created_at.desc()).limit(1)
        )
        eligible_amount = Decimal(str(
            invoice.total_amount if invoice else (job.completion_data or {}).get("collected_amount", 0)
        ))
        requested_amount = Decimal(str(amount if amount is not None else eligible_amount))
        if requested_amount <= 0 or requested_amount > eligible_amount:
            raise ServiceOSException(
                "WARRANTY_AMOUNT_INVALID",
                "Requested remedy cannot exceed the completed service amount.",
                status_code=422,
                context={"maximum_eligible_amount": float(eligible_amount)},
            )
        ex = await self.db.execute(select(WarrantyClaim).where(WarrantyClaim.job_id == str(job_uuid)))
        if ex.scalar_one_or_none():
            raise ServiceOSException("CONFLICT", f"Claim for job {job_id} already exists.")
        c = WarrantyClaim(
            tenant_id=job.tenant_id, customer_id=cid, job_id=str(job_uuid), claim_type=claim_type,
            description=description, media_ids=media_ids, amount_requested=requested_amount,
            status="provider_action_required", provider_response_due_at=utcnow() + timedelta(hours=24),
            warranty_days_snapshot=job.warranty_days_snapshot or 5, warranty_expires_at=expiry,
        )
        self.db.add(c); await self.db.flush()
        await self._publish("warranty_claim.submitted", str(job.tenant_id), str(c.id),
                            {"job_id": str(job_uuid), "amount": float(requested_amount)})
        return self._claim_dict(c)

    async def get_claim(self, claim_id, *, customer_id=None, tenant_id=None, is_admin=False):
        r = await self.db.execute(select(WarrantyClaim).where(WarrantyClaim.id==claim_id))
        c = r.scalar_one_or_none()
        if not c: raise NotFoundException("WarrantyClaim", str(claim_id))
        if not is_admin:
            owns_customer = customer_id is not None and str(c.customer_id) == str(customer_id)
            owns_tenant = tenant_id is not None and str(c.tenant_id) == str(tenant_id)
            if not (owns_customer or owns_tenant):
                raise NotFoundException("WarrantyClaim", str(claim_id))
        return self._claim_dict(c)

    async def provider_respond_claim(self, claim_id, tenant_id, resolution, *, resolved=False):
        c = await self.db.scalar(select(WarrantyClaim).where(
            WarrantyClaim.id == claim_id, WarrantyClaim.tenant_id == tenant_id,
        ).with_for_update())
        if not c:
            raise NotFoundException("WarrantyClaim", str(claim_id))
        if c.status not in ("provider_action_required", "provider_in_progress"):
            raise ServiceOSException("WARRANTY_INVALID_STATE", f"Claim is already {c.status}.", status_code=409)
        c.provider_resolution = resolution
        c.provider_responded_at = utcnow()
        if resolved:
            c.status = "provider_resolved"
            c.provider_resolved_at = utcnow()
            c.resolved_at = utcnow()
        else:
            c.status = "provider_in_progress"
        await self._publish("warranty_claim.provider_responded", str(c.tenant_id), str(c.id), {"resolved": resolved})
        return self._claim_dict(c)

    async def escalate_claim(self, claim_id, reason, *, customer_id=None, tenant_id=None):
        c = await self.db.scalar(select(WarrantyClaim).where(WarrantyClaim.id == claim_id).with_for_update())
        if not c:
            raise NotFoundException("WarrantyClaim", str(claim_id))
        owns_customer = customer_id is not None and str(c.customer_id) == str(customer_id)
        owns_tenant = tenant_id is not None and str(c.tenant_id) == str(tenant_id)
        if not (owns_customer or owns_tenant):
            raise NotFoundException("WarrantyClaim", str(claim_id))
        if c.status not in ("provider_action_required", "provider_in_progress", "provider_resolved"):
            raise ServiceOSException("WARRANTY_INVALID_STATE", f"Claim cannot be escalated from {c.status}.", status_code=409)
        missed_deadline = bool(
            owns_customer and not c.provider_responded_at and c.provider_response_due_at
            and c.provider_response_due_at <= utcnow()
        )
        # A customer gives the provider its response window unless the provider
        # has already answered. A provider may explicitly concede immediately.
        if owns_customer and not c.provider_responded_at and c.provider_response_due_at and c.provider_response_due_at > utcnow():
            raise ServiceOSException(
                "PROVIDER_RESPONSE_WINDOW_ACTIVE",
                "The provider still has time to respond to this warranty claim.", status_code=409,
                context={"provider_response_due_at": c.provider_response_due_at.isoformat()},
            )
        if missed_deadline and c.tenant_id:
            from app.engines.usage_credits.service import UsageCreditService
            from app.engines.tenant_engine.health import compute_health_score
            await UsageCreditService(
                self.db, actor_role="system", request_id="warranty:provider_sla"
            ).charge_provider_response_sla_penalty(
                tenant_id=c.tenant_id, source_type="warranty_claim",
                source_id=str(c.id), amount=Decimal("50.00"),
            )
            await compute_health_score(c.tenant_id, db=self.db)
        c.status = "provider_action_required"
        c.escalated_at = utcnow()
        c.escalation_reason = reason
        c.provider_response_due_at = utcnow() + timedelta(hours=24)
        await self._publish("warranty_claim.escalated", str(c.tenant_id), str(c.id), {"reason": reason})
        return self._claim_dict(c)

    async def list_tenant_claims(self, tid, status_filter, limit, cursor):
        q = select(WarrantyClaim).where(WarrantyClaim.tenant_id==tid).order_by(WarrantyClaim.created_at.desc())
        if status_filter: q = q.where(WarrantyClaim.status==status_filter)
        if cursor:
            try:
                cr = decode_cursor(cursor)
                q = q.where(WarrantyClaim.created_at < datetime.fromisoformat(cr["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1); r = await self.db.execute(q)
        claims = r.scalars().all(); has_next = len(claims) > limit; claims = claims[:limit]
        nc = encode_cursor({"created_at": claims[-1].created_at.isoformat()}) if has_next and claims else None
        return {"claims": [self._claim_dict(c) for c in claims], "has_next": has_next, "next_cursor": nc}

    async def list_customer_claims(self, customer_id, status_filter, limit, cursor):
        q = (select(WarrantyClaim)
             .where(WarrantyClaim.customer_id == customer_id)
             .order_by(WarrantyClaim.created_at.desc(), WarrantyClaim.id.desc()))
        if status_filter:
            q = q.where(WarrantyClaim.status == status_filter)
        if cursor:
            try:
                cr = decode_cursor(cursor)
                q = q.where(WarrantyClaim.created_at < datetime.fromisoformat(cr["created_at"]))
            except Exception:
                pass
        rows = (await self.db.execute(q.limit(limit + 1))).scalars().all()
        has_next = len(rows) > limit
        claims = rows[:limit]
        next_cursor = encode_cursor({"created_at": claims[-1].created_at.isoformat()}) if has_next and claims else None
        return {"claims": [self._claim_dict(c) for c in claims], "has_next": has_next, "next_cursor": next_cursor}

    async def _update_warranty_signal(self, tid):
        try:
            from app.engines.tenant_engine.health import write_health_signal
            from app.engines.final_records.models import ServiceJob
            total = await self.db.execute(select(func.count(ServiceJob.id)).where(
                ServiceJob.tenant_id == tid,
                ServiceJob.status.in_(["completed", "work_done", "invoice_issued", "paid"]),
            ))
            jobs = total.scalar_one_or_none() or 0
            cr = await self.db.execute(select(func.count(WarrantyClaim.id)).where(
                WarrantyClaim.tenant_id == tid,
                WarrantyClaim.status.notin_(["rejected", "closed"]),
            ))
            claims = cr.scalar_one_or_none() or 0
            rate = claims / jobs if jobs > 0 else 0
            await write_health_signal(tid, "warranty_claim_rate", max(0.0, (1-rate*10)*100))
        except Exception as e:
            logger.warning("commerce.warranty_signal", error=str(e))

    # ── Badges (3) ─────────────────────────────────────────────────────────────
    async def get_badges(self, tid):
        r = await self.db.execute(select(TenantBadge).where(TenantBadge.tenant_id==tid,
                                                              TenantBadge.is_active==True))
        badges = r.scalars().all()
        now = utcnow()
        active = [b for b in badges if not b.expires_at or b.expires_at > now]
        return {"tenant_id": str(tid), "badges": [
            {"badge_type": b.badge_type, "earned_at": b.earned_at.isoformat(),
             "expires_at": b.expires_at.isoformat() if b.expires_at else None} for b in active],
            "badge_count": len(active)}

    async def recalculate_badges(self, tid):
        self._assert_owns_tenant_deposit(tid)
        t = await self._get_tenant(tid); earned = []
        if float(t.health_score) >= BADGE_THRESHOLDS["platinum"]["health_score_min"]:
            await self._award_badge(tid, "platinum", {"health_score": float(t.health_score)})
            earned.append("platinum")
        from app.engines.tenant_engine.models import TenantBusinessProfile
        bp_r = await self.db.execute(select(TenantBusinessProfile).where(
            TenantBusinessProfile.tenant_id==tid))
        bp = bp_r.scalar_one_or_none()
        if bp and bp.gstin_verified:
            await self._award_badge(tid, "verified", {"gstin_verified": True}); earned.append("verified")
        lookback = utcnow() - timedelta(days=180)
        cr = await self.db.execute(select(func.count(WarrantyClaim.id)).where(
            WarrantyClaim.tenant_id==tid, WarrantyClaim.created_at>=lookback,
            WarrantyClaim.status.in_(["pending","approved"])))
        if (cr.scalar_one_or_none() or 0) == 0:
            await self._award_badge(tid, "warranty_free", {"claims_180d": 0}); earned.append("warranty_free")
        return {"badges_earned": earned, "badges_expired": [], "badges_maintained": []}

    async def _award_badge(self, tid, badge_type, snapshot):
        r = await self.db.execute(select(TenantBadge).where(TenantBadge.tenant_id==tid,
                                                              TenantBadge.badge_type==badge_type))
        b = r.scalar_one_or_none()
        if b:
            b.is_active = True; b.qualification_snapshot = snapshot
        else:
            self.db.add(TenantBadge(tenant_id=tid, badge_type=badge_type,
                                     is_active=True, qualification_snapshot=snapshot))

    async def get_badges_summary(self):
        r = await self.db.execute(select(TenantBadge.badge_type, func.count(TenantBadge.tenant_id))
            .where(TenantBadge.is_active==True).group_by(TenantBadge.badge_type))
        return {"distribution": {row[0]: row[1] for row in r.all()}}

    # ── Preflight (2) ──────────────────────────────────────────────────────────
    async def run_preflight(self, tid, cid, job_value, booking_id=None):
        from app.engines.platform_commerce.preflight import run_booking_preflight
        return await run_booking_preflight(self.db, tid, cid, Decimal(str(job_value)), booking_id)

    async def get_preflight_rules(self, tid):
        info = await self._get_eff_rate(tid)
        wb = await self.get_wallet_balance_for_engine(tid)
        return {"tenant_id": str(tid), "commission_rate": info["effective_rate"],
                "wallet_balance": wb["credit_balance"],
                "advance_by_band": {k: float(v) for k, v in CUSTOMER_ADVANCE_REQUIRED_PCT.items()},
                "customer_health_thresholds": {
                    b: {"range": f"{lo}-{hi}", "advance_pct": float(CUSTOMER_ADVANCE_REQUIRED_PCT[b])}
                    for b, (lo, hi) in CUSTOMER_HEALTH_BANDS.items()}}

    # ── Platform Analytics (3) ─────────────────────────────────────────────────
    async def get_platform_summary(self):
        today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        async def _csum(since):
            r = await self.db.execute(select(func.sum(CommissionRecord.commission_amount))
                .where(CommissionRecord.deducted_at >= since))
            return float(r.scalar_one_or_none() or 0)
        return {"commission": {"today": await _csum(today), "week": await _csum(today-timedelta(days=7)),
                "month": await _csum(today-timedelta(days=30))}}

    async def get_at_risk_tenants(self):
        from app.engines.tenant_engine.models import Tenant
        r = await self.db.execute(select(Tenant).where(
            Tenant.health_band.in_(["at_risk","critical"]), Tenant.status=="active")
            .order_by(Tenant.health_score))
        tenants = r.scalars().all()
        return {"tenants": [{"tenant_id": str(t.id), "tenant_name": t.tenant_name,
                "health_band": t.health_band, "health_score": float(t.health_score)} for t in tenants],
                "total": len(tenants)}

    async def get_daily_commission_chart(self, days, cursor=None):
        from sqlalchemy import cast, Date as SADate
        since = utcnow() - timedelta(days=days)
        r = await self.db.execute(select(
            cast(CommissionRecord.deducted_at, SADate).label("date"),
            func.sum(CommissionRecord.commission_amount).label("commission"),
            func.count(CommissionRecord.id).label("job_count"))
            .where(CommissionRecord.deducted_at >= since)
            .group_by(cast(CommissionRecord.deducted_at, SADate))
            .order_by(cast(CommissionRecord.deducted_at, SADate).desc()))
        rows = r.all()
        return {"chart_data": [{"date": str(row.date), "commission_collected": float(row.commission),
                "job_count": row.job_count} for row in rows], "days": days}
