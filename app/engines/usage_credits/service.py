"""FINAL-L5-05J — Canonical Usage Credit Service.

Single domain owner for tenant_billing.credit_balance / usage_credit_ledger.
Every Usage Credit balance mutation in the platform (manual admin
adjustment, package credit grant) must go through this service. Job
completion continues to use the certified
app.engines.execution.usage_credit_deduction.deduct_for_completed_job
directly (this service delegates to it, never duplicates it).

Never writes TenantWallet / wallet_transactions. Not money — internal
platform credits only.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.engines.tenant_engine.models import TenantBilling, UsageCreditLedger
from app.exceptions import ServiceOSException

EVENT_MANUAL_CREDIT_ADDED = "manual_credit_added"
EVENT_MANUAL_CREDIT_REMOVED = "manual_credit_removed"
EVENT_PACKAGE_CREDIT_GRANTED = "package_credit_granted"
EVENT_COMPLETED_JOB_DEDUCTION = "completed_job_deduction"
EVENT_CREDIT_REVERSAL = "credit_reversal"
EVENT_MIGRATION_ADJUSTMENT = "migration_adjustment"
EVENT_TOPUP_CREDIT_GRANTED = "topup_credit_granted"
EVENT_TOPUP_CREDIT_REFUNDED = "topup_credit_refunded"

VALID_EVENT_TYPES = {
    EVENT_MANUAL_CREDIT_ADDED, EVENT_MANUAL_CREDIT_REMOVED,
    EVENT_PACKAGE_CREDIT_GRANTED, EVENT_COMPLETED_JOB_DEDUCTION,
    EVENT_CREDIT_REVERSAL, EVENT_MIGRATION_ADJUSTMENT, EVENT_TOPUP_CREDIT_GRANTED,
    EVENT_TOPUP_CREDIT_REFUNDED,
}

VALID_REASON_CODES = {
    "manual_operational_adjustment", "goodwill_credit", "correction",
    "package_purchase", "package_reactivation", "billing_dispute_resolution",
    "migration_backfill", "credit_topup_purchase", "credit_topup_refund",
}

SOURCE_TYPE_FINANCE_HUB_CREDIT_TOPUP = "FINANCE_HUB_CREDIT_TOPUP"

VALID_DIRECTIONS = {"credit", "debit"}


class UsageCreditService:
    """Canonical owner of tenant_billing.credit_balance / usage_credit_ledger."""

    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None, request_id: str | None = None,
                 actor_ip: str | None = None):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id
        self.actor_ip = actor_ip

    # ── Reads ────────────────────────────────────────────────────────────────

    async def get_balance(self, tenant_id: uuid.UUID) -> dict:
        billing = (await self.db.execute(
            select(TenantBilling).where(TenantBilling.tenant_id == tenant_id)
        )).scalars().first()
        balance = Decimal(str(billing.credit_balance)) if billing else Decimal("0")
        return {
            "tenant_id": str(tenant_id),
            "usage_credit_balance": float(balance),
            "has_billing_record": billing is not None,
            "source": "tenant_billing.credit_balance",
        }

    async def get_ledger(self, tenant_id: uuid.UUID, limit: int = 50, offset: int = 0) -> dict:
        limit = min(limit, 200)
        q = (select(UsageCreditLedger)
             .where(UsageCreditLedger.tenant_id == tenant_id)
             .order_by(UsageCreditLedger.created_at.desc())
             .offset(offset).limit(limit))
        rows = (await self.db.execute(q)).scalars().all()
        return {
            "tenant_id": str(tenant_id),
            "items": [r.to_dict() for r in rows],
            "limit": limit, "offset": offset,
            "source": "usage_credit_ledger",
        }

    async def check_threshold(self, tenant_id: uuid.UUID, threshold: Decimal | None = None) -> dict:
        bal = await self.get_balance(tenant_id)
        if threshold is None:
            from app.engines.usage_credits.constants import DEFAULT_LOW_USAGE_CREDIT_THRESHOLD
            threshold = DEFAULT_LOW_USAGE_CREDIT_THRESHOLD
        balance = Decimal(str(bal["usage_credit_balance"]))
        return {
            "tenant_id": str(tenant_id),
            "balance": float(balance),
            "threshold": float(threshold),
            "is_low": balance < threshold,
            "has_billing_record": bal["has_billing_record"],
        }

    # ── Core mutation primitive (transactional, idempotent, audited) ──────────

    async def _post(
        self, *, tenant_id: uuid.UUID, amount: Decimal, event_type: str,
        source_type: str | None, source_id: str | None,
        reason_code: str | None, reason: str, idempotency_key: str | None,
        job_id: uuid.UUID | None = None, booking_id: uuid.UUID | None = None,
        allow_negative: bool = True,
    ) -> dict:
        """amount is signed: positive = credit, negative = debit.
        Locks the tenant_billing row for the duration of the mutation."""
        if event_type not in VALID_EVENT_TYPES:
            raise ServiceOSException("INVALID_USAGE_CREDIT_EVENT_TYPE",
                f"event_type must be one of {sorted(VALID_EVENT_TYPES)}", status_code=422)
        if amount == 0:
            raise ServiceOSException("INVALID_CREDIT_AMOUNT", "Amount cannot be zero.", status_code=422)

        if idempotency_key:
            existing = (await self.db.execute(
                select(UsageCreditLedger).where(
                    UsageCreditLedger.idempotency_key == idempotency_key)
            )).scalars().first()
            if existing:
                return {**existing.to_dict(), "idempotent": True}

        billing = (await self.db.execute(
            select(TenantBilling).where(TenantBilling.tenant_id == tenant_id)
            .with_for_update()
        )).scalars().first()
        if not billing:
            # Race-safe first-row creation: two concurrent mutations against
            # a brand-new tenant can both see "no row" before either
            # commits. A plain INSERT would raise IntegrityError on the
            # loser (found via a real concurrent-request test, not just
            # unit tests). INSERT ... ON CONFLICT DO NOTHING makes the
            # loser's insert a safe no-op; the unconditional re-select
            # with FOR UPDATE below then blocks until the winner commits
            # and reads its row.
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(TenantBilling).values(
                tenant_id=tenant_id, credit_balance=Decimal("0"),
            ).on_conflict_do_nothing(index_elements=["tenant_id"])
            await self.db.execute(stmt)
            billing = (await self.db.execute(
                select(TenantBilling).where(TenantBilling.tenant_id == tenant_id)
                .with_for_update()
            )).scalars().first()

        balance_before = Decimal(str(billing.credit_balance))
        balance_after = balance_before + amount
        if not allow_negative and balance_after < 0:
            raise ServiceOSException("INSUFFICIENT_USAGE_CREDIT",
                f"Resulting balance would be negative ({balance_after}).", status_code=402,
                context={"balance_before": float(balance_before), "requested_amount": float(amount)})

        billing.credit_balance = balance_after

        ledger = UsageCreditLedger(
            tenant_id=tenant_id, job_id=job_id, booking_id=booking_id,
            event_type=event_type, credit_delta=amount,
            balance_before=balance_before, balance_after=balance_after,
            source_type=source_type, source_id=source_id,
            reason_code=reason_code, reason=reason,
            created_by=self.actor_id, actor_role=self.actor_role,
            idempotency_key=idempotency_key, request_id=self.request_id,
        )
        self.db.add(ledger)
        await self.db.flush()

        audit_op = {
            EVENT_MANUAL_CREDIT_ADDED: "usage_credit.adjusted",
            EVENT_MANUAL_CREDIT_REMOVED: "usage_credit.adjusted",
            EVENT_PACKAGE_CREDIT_GRANTED: "package_credit.granted",
            EVENT_CREDIT_REVERSAL: "usage_credit.reversal_created",
            EVENT_MIGRATION_ADJUSTMENT: "usage_credit.migration_adjustment",
            EVENT_TOPUP_CREDIT_GRANTED: "topup_credit.granted",
            EVENT_TOPUP_CREDIT_REFUNDED: "topup_credit.refunded",
        }.get(event_type, "usage_credit.mutated")
        await record_platform_audit(
            self.db, operation=audit_op, engine_id="usage_credits",
            tenant_id=tenant_id, entity_type="usage_credit_ledger", entity_id=str(ledger.id),
            actor_id=self.actor_id, actor_role=self.actor_role, actor_ip=self.actor_ip,
            request_id=self.request_id,
            after={"event_type": event_type, "amount": float(amount),
                   "balance_before": float(balance_before), "balance_after": float(balance_after),
                   "reason_code": reason_code, "source_type": source_type, "source_id": source_id},
        )
        return {**ledger.to_dict(), "idempotent": False}

    # ── Manual admin adjustment ────────────────────────────────────────────

    async def adjust_credit(
        self, *, tenant_id: uuid.UUID, direction: str, amount: Decimal,
        reason_code: str, reason: str, idempotency_key: str,
    ) -> dict:
        if direction not in VALID_DIRECTIONS:
            raise ServiceOSException("INVALID_ADJUSTMENT_DIRECTION",
                f"direction must be one of {sorted(VALID_DIRECTIONS)}", status_code=422)
        if amount <= 0:
            raise ServiceOSException("INVALID_CREDIT_AMOUNT", "amount must be positive.", status_code=422)
        if reason_code not in VALID_REASON_CODES:
            raise ServiceOSException("INVALID_ADJUSTMENT_REASON",
                f"reason_code must be one of {sorted(VALID_REASON_CODES)}", status_code=422)
        if not reason or not reason.strip():
            raise ServiceOSException("INVALID_ADJUSTMENT_REASON", "reason is required.", status_code=422)
        if not idempotency_key or not idempotency_key.strip():
            raise ServiceOSException("USAGE_CREDIT_CONFLICT",
                "idempotency_key is required.", status_code=422)

        signed = amount if direction == "credit" else -amount
        event_type = EVENT_MANUAL_CREDIT_ADDED if direction == "credit" else EVENT_MANUAL_CREDIT_REMOVED
        return await self._post(
            tenant_id=tenant_id, amount=signed, event_type=event_type,
            source_type="admin_manual", source_id=None,
            reason_code=reason_code, reason=reason, idempotency_key=idempotency_key,
            allow_negative=(direction == "credit"),
        )

    # ── Package Credit Grant ───────────────────────────────────────────────

    async def grant_package_credit(
        self, *, tenant_id: uuid.UUID, package_assignment_id: str,
        activation_version: int | str, amount: Decimal, reason: str = "Package credit grant",
    ) -> dict:
        """Idempotency identity: package_credit_grant:{assignment_id}:{version}
        — a duplicate activation retry for the same assignment+version
        returns the existing grant instead of crediting twice."""
        if amount <= 0:
            raise ServiceOSException("INVALID_CREDIT_AMOUNT", "amount must be positive.", status_code=422)
        idem_key = f"package_credit_grant:{package_assignment_id}:{activation_version}"
        return await self._post(
            tenant_id=tenant_id, amount=amount, event_type=EVENT_PACKAGE_CREDIT_GRANTED,
            source_type="package_assignment", source_id=str(package_assignment_id),
            reason_code="package_purchase", reason=reason, idempotency_key=idem_key,
        )

    # ── Finance Hub Credit Top-up Grant ────────────────────────────────────

    async def grant_topup_credit(
        self, *, tenant_id: uuid.UUID, topup_order_id: str, amount: Decimal,
        reason: str = "Credit top-up purchase", grant_version: int | str = 1,
    ) -> dict:
        """FINAL-L5-05K. Idempotency identity:
        topup_credit_grant:{topup_order_id}:{grant_version} — a single
        CreditTopupOrder can only ever produce one successful grant
        (Part 6: the current real product has no multi-approval-version
        concept, so grant_version is always 1); both the gateway-signature
        confirmation path and the admin retry-credit-posting path call this
        with the same identity, so whichever fires first wins and the
        other becomes a safe idempotent no-op."""
        if amount <= 0:
            raise ServiceOSException("TOPUP_INVALID_AMOUNT", "amount must be positive.", status_code=422)
        idem_key = f"topup_credit_grant:{topup_order_id}:{grant_version}"
        return await self._post(
            tenant_id=tenant_id, amount=amount, event_type=EVENT_TOPUP_CREDIT_GRANTED,
            source_type=SOURCE_TYPE_FINANCE_HUB_CREDIT_TOPUP, source_id=str(topup_order_id),
            reason_code="credit_topup_purchase", reason=reason, idempotency_key=idem_key,
        )

    async def revoke_topup_credit(
        self, *, tenant_id: uuid.UUID, topup_order_id: str, amount: Decimal,
        refund_version: str, reason: str,
    ) -> dict:
        """Remove credits corresponding to a monetary top-up refund.

        ``refund_version`` is the cumulative refunded money amount. It makes
        a retried posting idempotent while allowing multiple intentional
        partial refunds. Refunds never create a negative usage-credit balance:
        credits that have already been consumed must be resolved before cash
        can be returned.
        """
        if amount <= 0:
            raise ServiceOSException("TOPUP_INVALID_AMOUNT", "amount must be positive.", status_code=422)
        if not reason or not reason.strip():
            raise ServiceOSException("INVALID_ADJUSTMENT_REASON", "reason is required.", status_code=422)
        idem_key = f"topup_credit_refund:{topup_order_id}:{refund_version}"
        return await self._post(
            tenant_id=tenant_id, amount=-amount, event_type=EVENT_TOPUP_CREDIT_REFUNDED,
            source_type=SOURCE_TYPE_FINANCE_HUB_CREDIT_TOPUP, source_id=str(topup_order_id),
            reason_code="credit_topup_refund", reason=reason, idempotency_key=idem_key,
            allow_negative=False,
        )

    # ── Completed Job Deduction (delegates to the certified service) ──────

    async def deduct_for_completed_job(self, **kwargs) -> dict:
        from app.engines.execution.usage_credit_deduction import deduct_for_completed_job
        return await deduct_for_completed_job(self.db, **kwargs)

    # ── Reversal ────────────────────────────────────────────────────────────

    async def reverse_credit_event(self, *, ledger_event_id: uuid.UUID, reason: str) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("INVALID_ADJUSTMENT_REASON", "reason is required.", status_code=422)
        original = (await self.db.execute(
            select(UsageCreditLedger).where(UsageCreditLedger.id == ledger_event_id)
        )).scalars().first()
        if not original:
            raise ServiceOSException("NOT_FOUND", "Ledger event not found.", status_code=404)
        idem_key = f"reversal:{ledger_event_id}"
        return await self._post(
            tenant_id=original.tenant_id, amount=-Decimal(str(original.credit_delta)),
            event_type=EVENT_CREDIT_REVERSAL, source_type="ledger_reversal",
            source_id=str(ledger_event_id), reason_code="correction", reason=reason,
            idempotency_key=idem_key,
        )
