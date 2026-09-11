"""TENANT-HS-FINANCE-HUB-01 — tenant-facing Home Services Finance Hub.

REUSE POLICY (this module deliberately owns almost no business logic):
  * Usage-credit balance / ledger / grants  -> app.engines.usage_credits.service.UsageCreditService
  * Completed-job credit deduction         -> app.engines.execution.usage_credit_deduction (READ ONLY here)
  * Published finance policy + qualifying technician count
                                           -> app.engines.vertical_catalog.finance_policy_service
  * Admin-side HS finance projections      -> app.engines.finance_hub.home_services_finance_service
                                              (.get_direct_payments_summary, tenant-scoped)
  * Credit top-up order storage            -> app.engines.finance_hub.models.CreditTopupOrder
  * Gateway order creation + signature     -> app.integrations.razorpay_client
Serves the tenant-facing Home Services finance console.

LEDGER SEPARATION (spec section 6) is structural here, not cosmetic: the
transactions projection tags every row as usage_credits, cash_tax, or
adjustment. Only usage-credit-moving rows carry a
`usage_credit_balance_after`; tax rows return null so the UI renders "—"
instead of fabricating a combined balance.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_platform_audit
from app.exceptions import ServiceOSException, NotFoundException
from app.integrations import razorpay_client
from app.engines.tenant_engine.models import TenantBilling, UsageCreditLedger, Tenant
from app.engines.invoice_payment.models import FinancialEvent
from app.engines.finance_hub.models import CreditTopupOrder
from app.engines.usage_credits.service import (
    UsageCreditService, EVENT_TOPUP_CREDIT_GRANTED, EVENT_TOPUP_CREDIT_REFUNDED,
    EVENT_COMPLETED_JOB_DEDUCTION,
    EVENT_CREDIT_REVERSAL, EVENT_MANUAL_CREDIT_ADDED, EVENT_MANUAL_CREDIT_REMOVED,
    EVENT_PACKAGE_CREDIT_GRANTED,
)
from app.engines.usage_credits.constants import DEFAULT_LOW_USAGE_CREDIT_THRESHOLD
from app.engines.vertical_catalog.finance_policy_service import (
    resolve_published_policy, resolve_qualifying_technician_count, FinancePolicyResolutionError,
)
from app.engines.vertical_catalog.home_services_setup_service import HOME_SERVICES_VERTICAL_KEY
from app.engines.vertical_catalog.service import VerticalCatalogService
from app.engines.vertical_monetization.customer_charge_recovery import RECOVERY_EVENT_TYPE

logger = structlog.get_logger("finance_hub.tenant_hs")
ENGINE_ID = "finance_hub"
utcnow = lambda: datetime.now(timezone.utc)

# Ledger identifiers (spec section 6/14). These are never merged.
LEDGER_USAGE_CREDITS = "usage_credits"
LEDGER_CASH_TAX = "cash_tax"
LEDGER_ADJUSTMENT = "adjustment"

LEDGER_LABELS = {
    LEDGER_USAGE_CREDITS: "Usage Credits",
    LEDGER_CASH_TAX: "Cash / Tax Transaction",
    LEDGER_ADJUSTMENT: "Adjustment / Reconciliation",
}

# Jobs that are live tenant obligations. Deliberately excludes terminal states.
ACTIVE_JOB_STATUSES = (
    "pending_assignment", "assigned", "accepted", "on_the_way",
    "in_progress", "quote_required", "quote_sent", "rework_required",
)

EVENT_TYPE_LABELS = {
    EVENT_TOPUP_CREDIT_GRANTED: "Credit top-up posted",
    EVENT_TOPUP_CREDIT_REFUNDED: "Credit top-up refunded",
    EVENT_COMPLETED_JOB_DEDUCTION: "Provider commission",
    EVENT_CREDIT_REVERSAL: "Credit reversal",
    EVENT_MANUAL_CREDIT_ADDED: "Admin credit adjustment (added)",
    EVENT_MANUAL_CREDIT_REMOVED: "Admin credit adjustment (removed)",
    EVENT_PACKAGE_CREDIT_GRANTED: "Package credit granted",
    "activation_credit_package_purchase": "Starter credit package purchased",
    RECOVERY_EVENT_TYPE: "Platform charge",
    "migration_adjustment": "Migration adjustment",
}

# Which ledger each usage_credit_ledger event_type belongs to. Manual admin
# corrections are reported under Adjustment/Reconciliation (they still move
# the usage-credit balance, so they still carry a balance_after).
ADJUSTMENT_EVENT_TYPES = {
    EVENT_MANUAL_CREDIT_ADDED, EVENT_MANUAL_CREDIT_REMOVED,
    EVENT_CREDIT_REVERSAL, "migration_adjustment",
}


def _d(v) -> Decimal:
    """Safe money coercion — Decimal only, never float arithmetic."""
    if v is None:
        return Decimal("0")
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _m(v) -> Decimal:
    """_d() normalised to 2 money decimals for DISPLAY/serialisation.

    CreditTopupOrder.credits_purchased is Numeric(14,4), so str() on it emits
    "1000.0000" — which rendered as "₹1000.0000" in the UI. Quantising here
    (never in arithmetic) keeps every serialised money string at 2 dp.
    """
    return _d(v).quantize(Decimal("0.01"))


def _mask_account(number: str | None) -> str | None:
    if not number:
        return None
    digits = "".join(ch for ch in number if ch.isalnum())
    if len(digits) <= 4:
        return "*" * len(digits)
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


class TenantHomeServicesFinanceService:
    """Every method is hard-scoped to ONE tenant + the Home Services vertical.

    tenant_id is always supplied by the router from the caller's JWT, never
    from a request body/query — the router has no code path that accepts a
    client-supplied tenant_id (spec section 2 / 21 tenant isolation).
    """

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_ip: str | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.request_id = request_id
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.actor_ip = actor_ip
        self.credits = UsageCreditService(
            db, actor_id=actor_id, actor_role=actor_role,
            request_id=request_id, actor_ip=actor_ip,
        )

    # ── infrastructure ──────────────────────────────────────────────────────

    async def _audit(self, operation: str, entity_type: str, entity_id: str | None,
                     before: dict | None = None, after: dict | None = None) -> None:
        await record_platform_audit(
            self.db, operation=operation, engine_id=ENGINE_ID,
            entity_type=entity_type, entity_id=entity_id, tenant_id=self.tenant_id,
            actor_id=self.actor_id, actor_role=self.actor_role, actor_ip=self.actor_ip,
            request_id=self.request_id, before=before, after=after,
        )

    async def _vertical_id(self) -> uuid.UUID:
        v = await VerticalCatalogService()._by_key(self.db, HOME_SERVICES_VERTICAL_KEY)
        return v.id

    async def _policy_or_none(self):
        """Never fabricates policy numbers. Returns (policy, error_code|None)."""
        try:
            vid = await self._vertical_id()
            return await resolve_published_policy(self.db, vid), None
        except FinancePolicyResolutionError as exc:
            return None, exc.code
        except Exception as exc:  # vertical row itself missing
            logger.warning("hs_finance.policy_resolution_failed", error=str(exc))
            return None, "FINANCE_POLICY_NOT_PUBLISHED"

    async def _policy_required(self):
        policy, err = await self._policy_or_none()
        if not policy:
            raise ServiceOSException(
                err or "FINANCE_POLICY_NOT_PUBLISHED",
                "No published Home Services finance policy is available. "
                "Credit purchases and deposit calculations are blocked until Admin publishes one.",
                status_code=422,
            )
        return policy

    async def _billing(self) -> TenantBilling | None:
        return (await self.db.execute(
            select(TenantBilling).where(TenantBilling.tenant_id == self.tenant_id)
        )).scalar_one_or_none()

    # ── Usage-credit wallet (ledger A) ──────────────────────────────────────

    async def get_entitled_seats(self) -> int:
        """Technician seats this tenant has bought.

        Denormalised onto tenant_billing at capture time by the top-up
        service; read here rather than recomputed so the finance console and
        the activation gate can never disagree about headroom.
        """
        row = (await self.db.execute(
            select(TenantBilling.entitled_seats).where(
                TenantBilling.tenant_id == self.tenant_id)
        )).scalar()
        return int(row or 0)

    async def get_usage_credits(self) -> dict:
        policy, policy_err = await self._policy_or_none()
        billing = await self._billing()
        available = _d(billing.credit_balance) if billing else Decimal("0")

        month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        async def event_debits(event_type: str, *, since: datetime | None = None) -> Decimal:
            filters = [
                UsageCreditLedger.tenant_id == self.tenant_id,
                UsageCreditLedger.event_type == event_type,
            ]
            if since is not None:
                filters.append(UsageCreditLedger.created_at >= since)
            delta = _d((await self.db.execute(
                select(func.coalesce(func.sum(UsageCreditLedger.credit_delta), 0)).where(*filters)
            )).scalar())
            return max(Decimal("0"), -delta)

        # A completed Home Services job can move the provider's usage-credit
        # balance in two independently idempotent entries:
        #   1. the provider's commission; and
        #   2. the customer platform fee that the provider collected on
        #      Fuvay's behalf and must remit from its usage-credit balance.
        # The old overview reported only (1), even though the canonical
        # balance included both. That made a correct balance look
        # over-deducted. Keep the immutable entries separate for auditability,
        # but reconcile every displayed total to both entries.
        commission_this_month = await event_debits(
            EVENT_COMPLETED_JOB_DEDUCTION, since=month_start,
        )
        fee_recovery_this_month = await event_debits(
            RECOVERY_EVENT_TYPE, since=month_start,
        )
        used_this_month = commission_this_month + fee_recovery_this_month

        deductions_count = (await self.db.execute(
            select(func.count(func.distinct(UsageCreditLedger.job_id))).where(
                UsageCreditLedger.tenant_id == self.tenant_id,
                UsageCreditLedger.event_type.in_((
                    EVENT_COMPLETED_JOB_DEDUCTION, RECOVERY_EVENT_TYPE,
                )),
                UsageCreditLedger.job_id.is_not(None),
            )
        )).scalar() or 0

        commission_total = await event_debits(EVENT_COMPLETED_JOB_DEDUCTION)
        fee_recovery_total = await event_debits(RECOVERY_EVENT_TYPE)
        deducted_total = commission_total + fee_recovery_total

        reversals_count = (await self.db.execute(
            select(func.count(UsageCreditLedger.id)).where(
                UsageCreditLedger.tenant_id == self.tenant_id,
                UsageCreditLedger.event_type == EVENT_CREDIT_REVERSAL,
            )
        )).scalar() or 0
        reversed_total = _d((await self.db.execute(
            select(func.coalesce(func.sum(UsageCreditLedger.credit_delta), 0)).where(
                UsageCreditLedger.tenant_id == self.tenant_id,
                UsageCreditLedger.event_type == EVENT_CREDIT_REVERSAL,
            )
        )).scalar())

        # Average real per-job deduction -> only then is "jobs remaining"
        # honestly calculable. Never guessed from a hardcoded rate.
        estimated_jobs_remaining = None
        avg_deduction = None
        if deductions_count > 0 and deducted_total > 0:
            avg_deduction = (deducted_total / Decimal(deductions_count)).quantize(Decimal("0.01"))
            if avg_deduction > 0:
                estimated_jobs_remaining = int(available / avg_deduction)

        last_topup_row = (await self.db.execute(
            select(CreditTopupOrder).where(
                CreditTopupOrder.tenant_id == self.tenant_id,
                CreditTopupOrder.payment_status == "credited",
            ).order_by(CreditTopupOrder.created_at.desc()).limit(1)
        )).scalar_one_or_none()

        failed_topups = (await self.db.execute(
            select(func.count(CreditTopupOrder.id)).where(
                CreditTopupOrder.tenant_id == self.tenant_id,
                CreditTopupOrder.payment_status.in_(("failed", "cancelled")),
            )
        )).scalar() or 0
        pending_topups = (await self.db.execute(
            select(func.count(CreditTopupOrder.id)).where(
                CreditTopupOrder.tenant_id == self.tenant_id,
                CreditTopupOrder.payment_status.in_(("initiated", "paid_pending_credit")),
            )
        )).scalar() or 0

        threshold = DEFAULT_LOW_USAGE_CREDIT_THRESHOLD
        # The one-time starter purchase is retired. Activation stopped blocking
        # on buying anything, and the admin console that configured it was
        # removed with it, so honouring the stored flag would have left the
        # requirement switched on with no way to switch it off. What protects
        # the platform is the credit FLOOR, applied when a booking is actually
        # taken. The column stays for historical policy versions.
        initial_purchase_required = False

        wallet_status = "active"
        if initial_purchase_required:
            wallet_status = "initial_purchase_required"
        elif available <= 0:
            wallet_status = "exhausted"
        elif available < _d(threshold):
            wallet_status = "low_balance"

        return {
            "currency": "INR",
            # Available == the ONE canonical balance (tenant_billing.credit_balance).
            "available_credits": str(available),
            # Honest disclosure: the platform has no reservation or pending-credit
            # mechanism for usage credits — deduction is atomic at job completion.
            # Reporting 0 with an explicit not_tracked flag instead of inventing
            # a number the backend cannot produce.
            "reserved_credits": "0",
            "reserved_credits_tracked": False,
            "pending_credits": str(await self._pending_credit_total()),
            "credits_used_this_month": str(used_this_month),
            "credits_deducted_total": str(deducted_total),
            "completed_job_deductions": deductions_count,
            "deduction_breakdown": {
                "provider_commission_this_month": str(commission_this_month),
                "customer_fee_recovery_this_month": str(fee_recovery_this_month),
                "total_this_month": str(used_this_month),
                "provider_commission_total": str(commission_total),
                "customer_fee_recovery_total": str(fee_recovery_total),
                "total": str(deducted_total),
            },
            "average_deduction_per_job": str(avg_deduction) if avg_deduction is not None else None,
            "estimated_jobs_remaining": estimated_jobs_remaining,
            "estimated_jobs_remaining_calculable": estimated_jobs_remaining is not None,
            "reversals_count": reversals_count,
            "reversals_total": str(reversed_total),
            "low_balance_threshold": str(threshold),
            "is_low_balance": available < _d(threshold),
            "wallet_status": wallet_status,
            "initial_purchase_required": initial_purchase_required,
            "failed_topups": failed_topups,
            "pending_topups": pending_topups,
            "last_topup": last_topup_row.to_dict() if last_topup_row else None,
            "deduction_policy": (policy.completion_deduction_policy if policy else None),
            "policy_version": (policy.version_number if policy else None),
            "policy_error": policy_err,
            "source": "tenant_billing.credit_balance + usage_credit_ledger",
        }

    async def _has_any_credit_purchase(self) -> bool:
        n = (await self.db.execute(
            select(func.count(UsageCreditLedger.id)).where(
                UsageCreditLedger.tenant_id == self.tenant_id,
                UsageCreditLedger.event_type.in_((
                    EVENT_TOPUP_CREDIT_GRANTED, EVENT_PACKAGE_CREDIT_GRANTED,
                    "activation_credit_package_purchase",
                )),
            )
        )).scalar() or 0
        return n > 0

    async def _pending_credit_total(self) -> Decimal:
        """Credits paid for but not yet posted (payment captured, grant pending).
        A pending payment NEVER counts toward available credits."""
        rows = (await self.db.execute(
            select(CreditTopupOrder).where(
                CreditTopupOrder.tenant_id == self.tenant_id,
                CreditTopupOrder.payment_status == "paid_pending_credit",
            )
        )).scalars().all()
        return sum((_d(r.credits_purchased) for r in rows), Decimal("0"))

    async def get_liability_holds(self) -> list[dict]:
        """Real open obligations used by tenant finance health views."""
        holds: list[dict] = []

        active_jobs = (await self.db.execute(
            text("SELECT count(*) FROM service_jobs WHERE tenant_id=:tid AND status = ANY(:st)"),
            {"tid": str(self.tenant_id), "st": list(ACTIVE_JOB_STATUSES)},
        )).scalar() or 0
        if active_jobs:
            holds.append({"code": "ACTIVE_JOBS", "label": "Active jobs in progress",
                          "count": active_jobs, "amount": None, "blocking": True})

        open_complaints = (await self.db.execute(
            text("SELECT count(*) FROM customer_complaints WHERE tenant_id=:tid "
                 "AND status NOT IN ('resolved','closed','rejected','withdrawn')"),
            {"tid": str(self.tenant_id)},
        )).scalar() or 0
        if open_complaints:
            holds.append({"code": "OPEN_COMPLAINTS", "label": "Unresolved customer complaints",
                          "count": open_complaints, "amount": None, "blocking": True})

        rework = (await self.db.execute(
            text("SELECT count(*) FROM service_rework_requests WHERE tenant_id=:tid "
                 "AND status NOT IN ('completed','cancelled','rejected')"),
            {"tid": str(self.tenant_id)},
        )).scalar() or 0
        if rework:
            holds.append({"code": "OPEN_REWORK", "label": "Open rework obligations",
                          "count": rework, "amount": None, "blocking": True})

        wc_rows = (await self.db.execute(
            text("SELECT count(*) n, coalesce(sum(amount_requested),0) amt FROM warranty_claims "
                 "WHERE tenant_id=:tid AND status IN ('pending','under_review','approved')"),
            {"tid": str(self.tenant_id)},
        )).fetchone()
        if wc_rows and wc_rows.n:
            holds.append({"code": "WARRANTY_CLAIMS", "label": "Open warranty claim obligations",
                          "count": wc_rows.n, "amount": str(_d(wc_rows.amt)), "blocking": True})

        cust_refunds = (await self.db.execute(
            text("SELECT count(*) FROM refund_requests WHERE tenant_id=:tid "
                 "AND status NOT IN ('completed','rejected','cancelled')"),
            {"tid": str(self.tenant_id)},
        )).scalar() or 0
        if cust_refunds:
            holds.append({"code": "CUSTOMER_REFUND_DISPUTES", "label": "Open customer refund/payment disputes",
                          "count": cust_refunds, "amount": None, "blocking": True})

        billing = await self._billing()
        if billing and _d(billing.credit_balance) < 0:
            holds.append({"code": "NEGATIVE_CREDIT_LIABILITY",
                          "label": "Negative usage-credit balance owed to Fuvay",
                          "count": 1, "amount": str(-_d(billing.credit_balance)), "blocking": True})

        return holds

    # ── Published policy (read-only, section 16) ────────────────────────────

    async def get_policy(self) -> dict:
        policy, err = await self._policy_or_none()
        if not policy:
            return {
                "resolved": False, "error_code": err,
                "message": "No published Home Services finance policy could be resolved. "
                           "Amounts cannot be shown until Admin publishes one.",
            }
        base = _d(policy.credit_package_base_amount)
        gst_pct = _d(policy.credit_package_gst_percent)
        gst_amount = (base * gst_pct / Decimal("100")).quantize(Decimal("0.01"))
        total = (base + gst_amount).quantize(Decimal("0.01"))
        published_by = None
        if policy.published_by_user_id:
            published_by = (await self.db.execute(
                text("SELECT full_name, email FROM users WHERE id=:uid"),
                {"uid": str(policy.published_by_user_id)},
            )).fetchone()
        return {
            "resolved": True,
            "vertical": HOME_SERVICES_VERTICAL_KEY,
            "vertical_label": "Home Services",
            "revenue_model": "Usage credits deducted on completed jobs",
            "customer_payment_model": "Customer pays the provider directly",
            "credit_purchase_rule": (
                f"₹{base} usable credit + {gst_pct.normalize()}% GST (₹{gst_amount}) "
                f"= ₹{total} payable. Exactly ₹{policy.credited_wallet_amount} is posted to the usable wallet."
            ),
            "credit_package_base_amount": str(base),
            "credit_package_gst_percent": str(gst_pct),
            "credit_package_gst_amount": str(gst_amount),
            "credit_package_total_payable": str(total),
            "credited_wallet_amount": str(_d(policy.credited_wallet_amount)),
            "initial_credit_purchase_required": policy.initial_credit_purchase_required,
            "completion_deduction_rule": (
                policy.completion_deduction_policy
                or "Per-job usage-credit deduction resolved from the job's service pricing rule at completion"
            ),
            "credit_warning_threshold": str(_d(policy.credit_warning_threshold)),
            "credit_booking_floor": str(_d(policy.credit_booking_floor)),
            "seat_accrual_mode": policy.seat_accrual_mode,
            "gst_tax_rule": f"GST {gst_pct.normalize()}% on credit purchases. GST is platform tax revenue and is NEVER credited to the usable wallet.",
            "low_balance_policy": f"Low-balance warning below ₹{DEFAULT_LOW_USAGE_CREDIT_THRESHOLD} usable credits",
            "currency": policy.currency,
            "effective_from": policy.effective_from.isoformat() if policy.effective_from else None,
            "version": policy.version_number,
            "status": policy.status,
            "published_at": policy.published_at.isoformat() if policy.published_at else None,
            "published_by": (published_by.full_name or published_by.email) if published_by else None,
            "tenant_editable": False,
            "immutable": True,
        }

    # ── Commission rates (what this tenant is actually charged) ─────────────

    async def get_commission_rates(self) -> dict:
        """The provider-commission rate actually applied to this tenant's
        completed jobs, and how it is derived.

        Deliberately mirrors execution/usage_credit_deduction.py::
        resolve_commission_credits. The published Home Services vertical
        policy is the sole authority; categories never override it.

        Only categories the tenant actually has enabled services in are
        listed, since a rate for a category they don't serve is noise.
        """
        from app.engines.vertical_catalog.models import Vertical
        from app.engines.vertical_monetization.models import VerticalMonetizationPolicy
        from app.engines.admin_catalog.models import ServiceCategory, TenantService

        vertical = (await self.db.execute(
            select(Vertical).where(Vertical.key == HOME_SERVICES_VERTICAL_KEY)
        )).scalar_one_or_none()
        policy = None
        if vertical:
            policy = (await self.db.execute(
                select(VerticalMonetizationPolicy).where(
                    VerticalMonetizationPolicy.vertical_id == vertical.id,
                    VerticalMonetizationPolicy.is_current.is_(True),
                    VerticalMonetizationPolicy.status == "published",
                )
            )).scalar_one_or_none()

        model = policy.provider_model if policy else None
        is_live = model == "PERCENTAGE_COMMISSION"
        default_pct = (
            _d(policy.provider_percentage)
            if policy is not None and policy.provider_percentage is not None else None
        )
        effective_pct = default_pct
        health_adjustment_pct = Decimal("0")
        health_snapshot = None
        if (
            is_live and policy is not None
            and policy.provider_health_adjustment_enabled
        ):
            from app.engines.trust_quality.provider_health import get_provider_health_snapshot
            health_snapshot = await get_provider_health_snapshot(
                self.db, self.tenant_id,
                max_age_days=policy.provider_health_score_max_age_days,
            )
            if health_snapshot["source"] == "canonical":
                health_adjustment_pct = _d(
                    (policy.provider_health_adjustments_json or {}).get(
                        health_snapshot["band_key"], 0
                    )
                )
            effective_pct = min(
                Decimal("100"),
                _d(policy.provider_health_max_effective_percentage),
                (default_pct or Decimal("0")) + health_adjustment_pct,
            )

        # Categories this tenant actually serves (enabled services only).
        cat_ids = (await self.db.execute(
            select(TenantService.category_id).where(
                TenantService.tenant_id == self.tenant_id,
                TenantService.is_enabled.is_(True),
                TenantService.deleted_at.is_(None),
            ).distinct()
        )).scalars().all()
        cat_ids = [c for c in cat_ids if c is not None]

        categories: list[dict] = []
        if cat_ids:
            rows = (await self.db.execute(
                select(ServiceCategory).where(ServiceCategory.id.in_(cat_ids))
                .order_by(ServiceCategory.name)
            )).scalars().all()
            for c in rows:
                categories.append({
                    "category_id": str(c.id),
                    "category_name": c.name,
                    "category_rate_pct": None,
                    "effective_rate_pct": str(effective_pct) if effective_pct is not None else None,
                    "using_default": True,
                    "source": "home_services_vertical_policy",
                })

        return {
            "is_live": is_live,
            "provider_model": model,
            "default_rate_pct": str(default_pct) if default_pct is not None else None,
            "health_adjustment_enabled": bool(
                policy and policy.provider_health_adjustment_enabled
            ),
            "health_adjustment_pct_points": str(health_adjustment_pct),
            "effective_rate_pct": str(effective_pct) if effective_pct is not None else None,
            "health_snapshot": health_snapshot,
            "basis": "Percentage of the amount you collect from the customer for each completed job",
            "charged_as": "Usage credits deducted from your balance at job completion",
            "customer_fee_recovery_enabled": bool(
                policy and policy.customer_fee_model != "NONE"
            ),
            "customer_fee_model": policy.customer_fee_model if policy else None,
            "customer_fee_percentage": (
                str(policy.customer_fee_percentage)
                if policy is not None and policy.customer_fee_percentage is not None else None
            ),
            "customer_fee_fixed_amount": (
                str((Decimal(policy.customer_fee_fixed_amount_minor) / Decimal("100")).quantize(Decimal("0.01")))
                if policy is not None and policy.customer_fee_fixed_amount_minor is not None else None
            ),
            "customer_fee_minimum": (
                str((Decimal(policy.customer_fee_min_minor) / Decimal("100")).quantize(Decimal("0.01")))
                if policy is not None and policy.customer_fee_min_minor is not None else None
            ),
            "customer_fee_maximum": (
                str((Decimal(policy.customer_fee_max_minor) / Decimal("100")).quantize(Decimal("0.01")))
                if policy is not None and policy.customer_fee_max_minor is not None else None
            ),
            "customer_fee_basis": policy.customer_fee_basis if policy else None,
            "customer_fee_recovery_note": (
                "The customer pays this fee to your business with the service payment. "
                "The same amount is then remitted to Fuvay from usage credits; it is not a second provider commission."
                if policy and policy.customer_fee_model != "NONE" else None
            ),
            "categories": categories,
            # Honest disclosure rather than showing a percentage that is not
            # charged by the selected provider model.
            "not_live_reason": None if is_live else (
                f"Percentage commission is not the active model"
                + (f" (currently {model})" if model else "")
                + ". These rates are not being charged."
            ),
        }

    # ── Transactions (section 14, all four ledgers, never merged) ───────────

    async def get_transactions(self, *, date_from: str | None = None, date_to: str | None = None,
                               ledger: str | None = None, type_: str | None = None,
                               status: str | None = None, page: int = 1, page_size: int = 25) -> dict:
        rows: list[dict] = []

        # ── (A) Usage-credit ledger + (D-adjacent) adjustments ─────────────
        credit_rows = (await self.db.execute(
            select(UsageCreditLedger).where(UsageCreditLedger.tenant_id == self.tenant_id)
            .order_by(UsageCreditLedger.created_at.desc())
        )).scalars().all()
        for r in credit_rows:
            is_adjustment = r.event_type in ADJUSTMENT_EVENT_TYPES
            delta = _d(r.credit_delta)
            rows.append({
                "row_id": f"ucl:{r.id}",
                "occurred_at": r.created_at.isoformat() if r.created_at else None,
                "reference": (r.idempotency_key or str(r.id))[:60],
                "ledger": LEDGER_ADJUSTMENT if is_adjustment else LEDGER_USAGE_CREDITS,
                "ledger_label": LEDGER_LABELS[LEDGER_ADJUSTMENT if is_adjustment else LEDGER_USAGE_CREDITS],
                "event_type": r.event_type,
                "event_label": EVENT_TYPE_LABELS.get(r.event_type, r.event_type.replace("_", " ").capitalize()),
                "description": r.reason or EVENT_TYPE_LABELS.get(r.event_type, r.event_type),
                "debit": str(-delta) if delta < 0 else None,
                "credit": str(delta) if delta > 0 else None,
                # Only usage-credit-moving rows carry a usable-credit balance.
                "usage_credit_balance_after": str(_d(r.balance_after)),
                "status": "posted",
                "related_job_id": str(r.job_id) if r.job_id else None,
                "related_transaction_ref": r.source_id,
                "receipt_available": r.event_type == EVENT_TOPUP_CREDIT_GRANTED,
                "reversible": r.event_type == EVENT_COMPLETED_JOB_DEDUCTION,
            })

        # ── (B) Cash / tax transaction ledger ──────────────────────────────
        topup_rows = (await self.db.execute(
            select(CreditTopupOrder).where(CreditTopupOrder.tenant_id == self.tenant_id)
            .order_by(CreditTopupOrder.created_at.desc())
        )).scalars().all()
        for r in topup_rows:
            gross = _m(r.amount_paid)
            base = _m(r.credits_purchased)
            gst = (gross - base).quantize(Decimal("0.01"))
            paid = r.payment_status in ("credited", "paid_pending_credit")
            rows.append({
                "row_id": f"cto:{r.id}",
                "occurred_at": r.created_at.isoformat() if r.created_at else None,
                "reference": r.order_ref or r.gateway_order_id or str(r.id),
                "ledger": LEDGER_CASH_TAX,
                "ledger_label": LEDGER_LABELS[LEDGER_CASH_TAX],
                "event_type": "credit_topup_payment",
                "event_label": "Credit top-up payment (incl. GST)",
                "description": (f"Credit top-up — base ₹{base} + GST ₹{gst} = ₹{gross} payable"),
                "debit": str(gross) if paid else None,
                "credit": None,
                "usage_credit_balance_after": None,
                "status": r.payment_status,
                "related_job_id": None,
                "related_transaction_ref": r.gateway_payment_id,
                "receipt_available": r.payment_status == "credited",
                "reversible": False,
            })
            if gst > 0 and paid:
                rows.append({
                    "row_id": f"cto-gst:{r.id}",
                    "occurred_at": r.created_at.isoformat() if r.created_at else None,
                    "reference": f"{r.order_ref or r.id}-GST",
                    "ledger": LEDGER_CASH_TAX,
                    "ledger_label": LEDGER_LABELS[LEDGER_CASH_TAX],
                    "event_type": "credit_topup_gst",
                    "event_label": "GST collected on credit top-up",
                    "description": f"GST on credit top-up — never posted to the usable wallet",
                    "debit": str(gst),
                    "credit": None,
                    "usage_credit_balance_after": None,
                    "status": "posted",
                    "related_job_id": None,
                    "related_transaction_ref": r.gateway_payment_id,
                    "receipt_available": True,
                    "reversible": False,
                })

        # Activation-time tax events are sourced here; usable credit movement
        # remains sourced exclusively from UsageCreditLedger above.
        fev_rows = (await self.db.execute(
            select(FinancialEvent).where(
                FinancialEvent.tenant_id == self.tenant_id,
                FinancialEvent.event_type.in_((
                    "activation.credit_package_gst_collected",
                )),
            ).order_by(FinancialEvent.created_at.desc())
        )).scalars().all()
        for r in fev_rows:
            payload = r.new_value or {}
            amt = payload.get("tax_amount")
            rows.append({
                "row_id": f"fev:{r.id}",
                "occurred_at": r.created_at.isoformat() if r.created_at else None,
                "reference": payload.get("gateway_payment_id") or payload.get("gateway_order_id") or str(r.id),
                "ledger": LEDGER_CASH_TAX,
                "ledger_label": LEDGER_LABELS[LEDGER_CASH_TAX],
                "event_type": r.event_type,
                "event_label": "GST collected on starter credit package",
                "description": "GST on the starter credit package — never posted to the usable wallet",
                "debit": str(_d(amt)) if amt is not None else None,
                "credit": None,
                "usage_credit_balance_after": None,
                "status": "posted",
                "related_job_id": None,
                "related_transaction_ref": payload.get("gateway_payment_id"),
                "receipt_available": False,
                "reversible": False,
            })

        # ── filters (applied uniformly after composition) ──────────────────
        def _keep(row: dict) -> bool:
            if ledger and row["ledger"] != ledger:
                return False
            if type_ and row["event_type"] != type_:
                return False
            if status and row["status"] != status:
                return False
            if date_from and row["occurred_at"] and row["occurred_at"][:10] < date_from:
                return False
            if date_to and row["occurred_at"] and row["occurred_at"][:10] > date_to:
                return False
            return True

        filtered = [r for r in rows if _keep(r)]
        filtered.sort(key=lambda r: r["occurred_at"] or "", reverse=True)
        total = len(filtered)
        page = max(1, page)
        page_size = min(max(1, page_size), 200)
        start = (page - 1) * page_size
        return {
            "items": filtered[start:start + page_size],
            "total": total, "page": page, "page_size": page_size,
            "ledgers": [{"value": k, "label": v} for k, v in LEDGER_LABELS.items()],
            # The endpoint has always accepted `type` and `status` filters, but
            # returned a facet list only for `ledger` -- so the UI could offer a
            # real picker for one filter and had to fall back to a free-text box
            # for the other two, where the caller has to guess the exact stored
            # value. These are derived from the composed (pre-filter) rows, so
            # every option offered is one that actually returns something.
            "types": sorted({
                r["event_type"] for r in rows if r.get("event_type")
            }),
            "statuses": sorted({
                r["status"] for r in rows if r.get("status")
            }),
            "ledger_totals": {
                k: {
                    "rows": sum(1 for r in filtered if r["ledger"] == k),
                    "debit_total": str(sum((_d(r["debit"]) for r in filtered if r["ledger"] == k and r["debit"]), Decimal("0"))),
                    "credit_total": str(sum((_d(r["credit"]) for r in filtered if r["ledger"] == k and r["credit"]), Decimal("0"))),
                } for k in LEDGER_LABELS
            },
            "never_combined_note": "Usage-credit balances are never combined with cash or tax transactions.",
        }

    # ── Direct customer payments summary (section 17, tenant-scoped) ────────

    async def get_direct_payments_summary(self) -> dict:
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        svc = HomeServicesFinanceService(self.db, request_id=self.request_id,
                                        actor_id=self.actor_id, actor_role=self.actor_role)
        # Canonical admin projection, reused with a tenant scope — not forked.
        data = await svc.get_direct_payments_summary_for_tenant(self.tenant_id)
        data["notice"] = "Customer pays the provider directly. Fuvay records confirmation only."
        data["link"] = "/home-services/direct-payments"
        return data

    # ── Finance readiness (section 13) ──────────────────────────────────────

    async def get_readiness(self) -> dict:
        wallet = await self.get_usage_credits()
        policy, policy_err = await self._policy_or_none()

        blockers: list[dict] = []
        warnings: list[dict] = []
        actions: list[dict] = []
        checks: list[dict] = []

        # 1. Policy resolution
        if policy:
            checks.append({"code": "FINANCE_POLICY", "label": "Finance policy published",
                           "state": "complete",
                           "detail": f"Version {policy.version_number} in effect"})
        else:
            checks.append({"code": "FINANCE_POLICY", "label": "Finance policy published",
                           "state": "blocked", "detail": "No published policy could be resolved"})
            blockers.append({"code": policy_err or "FINANCE_POLICY_NOT_PUBLISHED",
                             "message": "No published Home Services finance policy. Finance operations are blocked.",
                             "resolution": "Fuvay Admin must publish a finance policy version."})

        # 2. Initial credit purchase
        if wallet["initial_purchase_required"]:
            checks.append({"code": "INITIAL_CREDIT_PURCHASE", "label": "Starter credit package purchased",
                           "state": "blocked", "detail": "Required before jobs can be charged"})
            blockers.append({"code": "INITIAL_CREDIT_PURCHASE_REQUIRED",
                             "message": "The mandatory starter credit package has not been purchased.",
                             "resolution": "Buy usage credits to complete finance setup."})
            actions.append({"code": "BUY_CREDITS", "label": "Buy usage credits", "tab": "usage-credits"})
        else:
            checks.append({"code": "INITIAL_CREDIT_PURCHASE", "label": "Starter credit package purchased",
                           "state": "complete", "detail": "Credit purchase on record"})

        # 3. Usable credit balance
        if _d(wallet["available_credits"]) <= 0:
            checks.append({"code": "USAGE_CREDIT_BALANCE", "label": "Usable credit balance",
                           "state": "blocked", "detail": "No usable credits — completed jobs cannot be charged"})
            blockers.append({"code": "USAGE_CREDITS_EXHAUSTED",
                             "message": "Your usable credit balance is zero.",
                             "resolution": "Top up usage credits to keep completing jobs."})
            actions.append({"code": "BUY_CREDITS", "label": "Buy usage credits", "tab": "usage-credits"})
        elif wallet["is_low_balance"]:
            checks.append({"code": "USAGE_CREDIT_BALANCE", "label": "Usable credit balance",
                           "state": "action_required",
                           "detail": f"₹{wallet['available_credits']} left (below ₹{wallet['low_balance_threshold']})"})
            warnings.append({"code": "USAGE_CREDITS_LOW",
                             "message": f"Usable credits (₹{wallet['available_credits']}) are below the "
                                        f"₹{wallet['low_balance_threshold']} low-balance threshold.",
                             "resolution": "Top up before your balance runs out."})
            actions.append({"code": "BUY_CREDITS", "label": "Buy usage credits", "tab": "usage-credits"})
        else:
            checks.append({"code": "USAGE_CREDIT_BALANCE", "label": "Usable credit balance",
                           "state": "complete", "detail": f"₹{wallet['available_credits']} available"})

        # 4. Credit floor — what replaced the security deposit
        # A deposit was collateral. Credit is spent, so instead of holding a
        # pot the policy sets a floor: below it, new bookings stop. That keeps
        # a balance available to deduct a penalty or settlement against.
        if policy is not None:
            _floor = _d(policy.credit_booking_floor)
            _warn = _d(policy.credit_warning_threshold)
            _avail = _d(wallet["available_credits"])
            if _avail < _floor:
                checks.append({"code": "CREDIT_FLOOR", "label": "Credit above booking floor",
                               "state": "blocked",
                               "detail": f"₹{_avail} available, floor is ₹{_floor}"})
                blockers.append({"code": "CREDIT_BELOW_FLOOR",
                                 "message": f"Credit balance ₹{_avail} is below the ₹{_floor} booking floor.",
                                 "resolution": "Buy a top-up plan to resume taking new bookings."})
                actions.append({"code": "BUY_TOPUP", "label": "Buy a top-up plan", "tab": "topups"})
            elif _avail < _warn:
                checks.append({"code": "CREDIT_FLOOR", "label": "Credit above booking floor",
                               "state": "action_required",
                               "detail": f"₹{_avail} available, warning at ₹{_warn}"})
                warnings.append({"code": "CREDIT_LOW",
                                 "message": f"Credit balance ₹{_avail} is approaching the ₹{_floor} booking floor.",
                                 "resolution": "Top up before new bookings are blocked."})
                actions.append({"code": "BUY_TOPUP", "label": "Buy a top-up plan", "tab": "topups"})
            else:
                checks.append({"code": "CREDIT_FLOOR", "label": "Credit above booking floor",
                               "state": "complete",
                               "detail": f"₹{_avail} available (floor ₹{_floor})"})

        # 5. Failed top-ups
        if wallet["failed_topups"]:
            checks.append({"code": "TOPUP_HEALTH", "label": "Credit top-up payments clean",
                           "state": "action_required",
                           "detail": f"{wallet['failed_topups']} failed top-up attempt(s)"})
            warnings.append({"code": "FAILED_TOPUPS",
                             "message": f"{wallet['failed_topups']} credit top-up payment(s) failed.",
                             "resolution": "Retry the failed payment from Top-ups & Transactions."})
            actions.append({"code": "REVIEW_TOPUPS", "label": "Review failed top-ups", "tab": "topups"})
        else:
            checks.append({"code": "TOPUP_HEALTH", "label": "Credit top-up payments clean",
                           "state": "complete", "detail": "No failed top-ups"})

        if blockers:
            status = "blocked"
        elif warnings:
            status = "action_required"
        else:
            status = "ready"

        return {
            "status": status,
            "status_label": {"ready": "Ready", "action_required": "Action required",
                             "blocked": "Blocked"}[status],
            "checks": checks,
            "blockers": blockers,
            "warnings": warnings,
            "available_actions": actions,
            "computed_at": utcnow().isoformat(),
            "server_computed": True,
        }

    # ── Action & reconciliation queue (section 15) ──────────────────────────

    async def get_action_queue(self) -> list[dict]:
        wallet = await self.get_usage_credits()
        reversals = (await self.db.execute(
            select(func.count(UsageCreditLedger.id)).where(
                UsageCreditLedger.tenant_id == self.tenant_id,
                UsageCreditLedger.event_type == EVENT_CREDIT_REVERSAL,
                UsageCreditLedger.created_at >= utcnow() - timedelta(days=30),
            )
        )).scalar() or 0

        # Ledger mismatch = the real integrity check: does the last ledger
        # row's balance_after match tenant_billing.credit_balance?
        mismatch = 0
        billing = await self._billing()
        last = (await self.db.execute(
            select(UsageCreditLedger).where(UsageCreditLedger.tenant_id == self.tenant_id)
            .order_by(UsageCreditLedger.created_at.desc()).limit(1)
        )).scalar_one_or_none()
        if billing and last and _d(last.balance_after) != _d(billing.credit_balance):
            mismatch = 1

        policy_unresolved = 1 if wallet["policy_error"] else 0

        return [
            {"code": "FAILED_TOPUPS", "label": "Failed top-ups", "count": wallet["failed_topups"],
             "tab": "topups", "filter": {"status": "failed"}, "severity": "danger"},
            {"code": "PENDING_TOPUPS", "label": "Pending gateway confirmation", "count": wallet["pending_topups"],
             "tab": "topups", "filter": {"status": "initiated"}, "severity": "warning"},
            {"code": "CREDIT_REVERSALS", "label": "Credit reversals (30d)", "count": reversals,
             "tab": "topups", "filter": {"ledger": LEDGER_ADJUSTMENT}, "severity": "info"},
            {"code": "POLICY_UNRESOLVED", "label": "Policy unresolved", "count": policy_unresolved,
             "tab": "policy", "filter": {}, "severity": "danger"},
            {"code": "LEDGER_MISMATCH", "label": "Ledger mismatch", "count": mismatch,
             "tab": "topups", "filter": {"ledger": LEDGER_USAGE_CREDITS}, "severity": "danger"},
        ]

    # ── Overview composition (section 4/5) ─────────────────────────────────

    async def get_overview(self) -> dict:
        wallet = await self.get_usage_credits()
        policy = await self.get_policy()
        readiness = await self.get_readiness()
        queue = await self.get_action_queue()
        recent = await self.get_transactions(page=1, page_size=8)
        try:
            direct = await self.get_direct_payments_summary()
        except Exception as exc:  # partial projection failure must not zero the page
            logger.warning("hs_finance.direct_payments_projection_failed", error=str(exc))
            direct = {"projection_failed": True, "error": str(exc),
                      "notice": "Customer pays the provider directly. Fuvay records confirmation only.",
                      "link": "/home-services/direct-payments"}

        action_items = sum(int(q["count"]) for q in queue)
        return {
            "tenant_id": str(self.tenant_id),
            "vertical": HOME_SERVICES_VERTICAL_KEY,
            "kpis": {
                "usable_credits": wallet["available_credits"],
                "credits_used_this_month": wallet["credits_used_this_month"],
                "entitled_seats": await self.get_entitled_seats(),
                "action_items": action_items,
                "finance_status": readiness["status"],
                "finance_status_label": readiness["status_label"],
            },
            "readiness": readiness,
            "recent_activity": recent,
            "usage_credits": wallet,
            "policy": policy,
            "direct_payments": direct,
            "action_queue": queue,
        }

    # ── Top-up flow (section 18) ───────────────────────────────────────────

    async def get_credit_packages(self) -> list[dict]:
        """Admin-approved credit packages. Derived from the published policy's
        base amount — the platform has exactly one approved package definition
        (the policy row); multiples of it are offered as quantities rather than
        inventing package tiers that no admin has approved."""
        policy = await self._policy_required()
        base = _d(policy.credit_package_base_amount)
        gst_pct = _d(policy.credit_package_gst_percent)
        out = []
        for qty in (1, 2, 5, 10):
            credits = (base * qty).quantize(Decimal("0.01"))
            gst = (credits * gst_pct / Decimal("100")).quantize(Decimal("0.01"))
            out.append({
                "package_key": f"policy_v{policy.version_number}_x{qty}",
                "quantity": qty,
                "label": f"₹{credits} usable credits",
                "base_credits": str(credits),
                "gst_percent": str(gst_pct),
                "gst_amount": str(gst),
                "total_payable": str((credits + gst).quantize(Decimal("0.01"))),
                "policy_version": policy.version_number,
            })
        return out

    async def create_topup(self, *, quantity: int, payment_method: str = "razorpay",
                            credit_package_id: uuid.UUID | None = None) -> dict:
        """Creates a gateway order ONLY. No credit is posted here — posting
        happens exclusively on server-verified payment confirmation.

        When `credit_package_id` is given, price/credits come from that
        admin-defined CreditPackage (platform_commerce.models) instead of
        the policy's flat per-unit price -- `quantity` is ignored in that
        case (a package is a fixed bundle, not a per-unit multiplier).
        Bonus credits are folded directly into `credits_purchased` (the one
        field the confirm-payment flow actually grants as usable credit) --
        `bonus_credits` is kept purely as a record of how much of that was
        bonus, not itself granted separately. Note the packaged path may
        make `gross - credits_purchased` (logged as "gst_amount" downstream)
        negative or zero when a bonus discount is applied -- that field is
        only a meaningful GST figure for the flat, non-package path.
        """
        policy_version = None
        if credit_package_id is not None:
            from app.engines.platform_commerce.models import CreditPackage
            pkg = (await self.db.execute(
                select(CreditPackage).where(CreditPackage.id == credit_package_id, CreditPackage.is_active == True)
            )).scalar_one_or_none()
            if not pkg:
                raise NotFoundException("CreditPackage", str(credit_package_id))
            bonus = (_d(pkg.credits_amount) * _d(pkg.bonus_pct) / Decimal("100")).quantize(Decimal("0.01"))
            base = (_d(pkg.credits_amount) + bonus).quantize(Decimal("0.01"))
            gross = _d(pkg.price_inr).quantize(Decimal("0.01"))
            audit_extra = {"credit_package_id": str(pkg.id), "package_name": pkg.name, "bonus_credits": str(bonus)}
        else:
            if quantity < 1 or quantity > 100:
                raise ServiceOSException("TOPUP_INVALID_QUANTITY",
                                         "quantity must be between 1 and 100.", status_code=422)
            policy = await self._policy_required()
            base = (_d(policy.credit_package_base_amount) * quantity).quantize(Decimal("0.01"))
            gst_pct = _d(policy.credit_package_gst_percent)
            gst = (base * gst_pct / Decimal("100")).quantize(Decimal("0.01"))
            gross = (base + gst).quantize(Decimal("0.01"))
            policy_version = policy.version_number
            bonus = Decimal("0")
            audit_extra = {"gst_amount": str(gst), "policy_version": policy_version}

        order_ref = f"HSTOP-{str(self.tenant_id)[:8]}-{uuid.uuid4().hex[:8]}".upper()
        gw = await razorpay_client.create_order(
            gross, receipt=order_ref,
            notes={"tenant_id": str(self.tenant_id), "purpose": "hs_usage_credit_topup",
                   "vertical_key": HOME_SERVICES_VERTICAL_KEY,
                   "policy_version": str(policy_version) if policy_version else "package",
                   **({"credit_package_id": str(credit_package_id)} if credit_package_id else {})},
            db=self.db,
        )

        rec = CreditTopupOrder(
            tenant_id=self.tenant_id, order_ref=order_ref,
            credit_package_id=credit_package_id,
            credits_purchased=base,          # usable credits (incl. bonus, for the package path)
            bonus_credits=bonus,
            amount_paid=gross,               # cash payable
            currency="INR", payment_method=payment_method,
            payment_status="initiated", wallet_credit_status="pending",
            gateway_order_id=gw["id"],
        )
        self.db.add(rec)
        await self.db.flush()
        await self._audit("hs_finance.topup_order_created", "credit_topup_order", str(rec.id),
                          after={"order_ref": order_ref, "base_credits": str(base),
                                 "total_payable": str(gross), **audit_extra})
        await self.db.commit()

        return {
            **rec.to_dict(),
            "quantity": quantity,
            "base_credits": str(base),
            "gst_percent": str(gst_pct),
            "gst_amount": str(gst),
            "total_payable": str(gross),
            "usable_credits_on_success": str(base),
            "policy_version": policy.version_number,
            "gateway": "razorpay",
            "gateway_order_id": gw["id"],
            "amount_paise": int(gross * 100),
            "key": await razorpay_client.get_key_id(self.db),
            "note": "No credits are posted until Fuvay verifies the payment signature server-side.",
        }

    async def confirm_topup_payment(self, *, gateway_order_id: str, gateway_payment_id: str,
                                    signature: str | None, status_: str = "captured",
                                    raw_payload: dict | None = None,
                                    signature_verified: bool = False) -> dict:
        """The ONLY path that posts usable credits.

        Idempotency is two-layered:
          1. CreditTopupOrder.payment_status == 'credited' short-circuits.
          2. UsageCreditService.grant_topup_credit's idempotency key
             `topup_credit_grant:{topup_order_id}:1` — a DB-level identity, so
             even two concurrent duplicate webhooks cannot double-credit.
        """
        order = (await self.db.execute(
            select(CreditTopupOrder).where(CreditTopupOrder.gateway_order_id == gateway_order_id)
        )).scalar_one_or_none()
        if not order:
            raise NotFoundException("CreditTopupOrder", gateway_order_id)
        # Tenant isolation: a caller can only ever confirm its OWN order.
        if order.tenant_id != self.tenant_id:
            raise NotFoundException("CreditTopupOrder", gateway_order_id)

        if not signature_verified:
            if not await razorpay_client.verify_payment_signature(gateway_order_id, gateway_payment_id, signature or "", db=self.db):
                order.payment_status = "failed"
                order.failure_reason = "Gateway signature verification failed"
                await self.db.commit()
                raise ServiceOSException("PAYMENT_VERIFICATION_FAILED",
                                         "Payment signature could not be verified. No credits were posted.",
                                         status_code=400)

        if order.payment_status == "credited":
            return {**order.to_dict(), "idempotent": True,
                    "message": "Already credited — duplicate confirmation safely ignored."}

        if status_ != "captured":
            order.payment_status = "failed"
            order.failure_reason = f"Gateway reported status '{status_}'"
            await self.db.commit()
            return {**order.to_dict(), "idempotent": False, "credited": False}

        order.gateway_payment_id = gateway_payment_id
        order.payment_status = "paid_pending_credit"
        await self.db.flush()

        grant = await self.credits.grant_topup_credit(
            tenant_id=self.tenant_id, topup_order_id=str(order.id),
            amount=_d(order.credits_purchased),
            reason=f"Home Services usage-credit top-up {order.order_ref}",
        )

        order.payment_status = "credited"
        order.wallet_credit_status = "credited"
        order.usage_credit_ledger_event_id = uuid.UUID(grant["ledger_id"])

        gross = _m(order.amount_paid)
        base = _m(order.credits_purchased)
        gst = (gross - base).quantize(Decimal("0.01"))
        # GST is platform tax revenue — its own financial event, NEVER wallet credit.
        self.db.add(FinancialEvent(
            record_type="credit_topup_order", record_id=order.id, tenant_id=self.tenant_id,
            actor_type="system", event_type="credit_topup.gst_collected",
            new_value={"gross_amount": str(gross), "usable_credits_posted": str(base),
                       "gst_amount": str(gst), "gateway_payment_id": gateway_payment_id},
        ))
        await self._audit("hs_finance.topup_credited", "credit_topup_order", str(order.id),
                          after={"usable_credits_posted": str(base), "gst_amount": str(gst),
                                 "gross_paid": str(gross), "ledger_id": grant["ledger_id"],
                                 "idempotent_grant": grant.get("idempotent")})
        await self.db.commit()

        return {
            **order.to_dict(), "idempotent": bool(grant.get("idempotent")), "credited": True,
            "usable_credits_posted": str(base), "gst_amount": str(gst), "gross_paid": str(gross),
            "ledger_event": grant,
            "receipt": await self.get_topup_receipt(order),
        }

    async def get_topup_receipt(self, order: CreditTopupOrder) -> dict:
        gross = _m(order.amount_paid)
        base = _m(order.credits_purchased)
        gst = (gross - base).quantize(Decimal("0.01"))
        policy, _ = await self._policy_or_none()
        return {
            "receipt_number": f"RCPT-{(order.order_ref or str(order.id))[-12:]}",
            "issued_at": (order.updated_at or order.created_at).isoformat()
                          if (order.updated_at or order.created_at) else None,
            "base_credit_value": str(base),
            "gst_amount": str(gst),
            "total_paid": str(gross),
            "usable_credit_posted": str(base),
            "transaction_reference": order.gateway_payment_id or order.gateway_order_id,
            "policy_version": policy.version_number if policy else None,
            "currency": order.currency,
        }

    async def get_topup(self, topup_id: uuid.UUID) -> dict:
        order = (await self.db.execute(
            select(CreditTopupOrder).where(
                CreditTopupOrder.id == topup_id,
                CreditTopupOrder.tenant_id == self.tenant_id,   # tenant isolation
            )
        )).scalar_one_or_none()
        if not order:
            raise NotFoundException("CreditTopupOrder", str(topup_id))
        gross = _m(order.amount_paid)
        base = _m(order.credits_purchased)
        return {
            **order.to_dict(),
            "base_credits": str(base),
            "gst_amount": str((gross - base).quantize(Decimal("0.01"))),
            "total_payable": str(gross),
            "receipt": await self.get_topup_receipt(order) if order.payment_status == "credited" else None,
        }

    async def cancel_topup(self, topup_id: uuid.UUID) -> dict:
        """Real gap fixed here: dismissing the Razorpay Checkout popup left
        the order permanently stuck at `payment_status='initiated'` --
        `cancelled` was already a documented valid status on this column
        (see the model's status-list comment) but nothing ever set it, so
        every abandoned checkout attempt sat in the tenant's own top-up
        table indefinitely, badge-colored the same "pending" yellow as a
        real in-flight payment. Only ever moves an order OUT of
        `initiated` -- a captured/credited/already-terminal order can never
        be cancelled from here."""
        order = (await self.db.execute(
            select(CreditTopupOrder).where(
                CreditTopupOrder.id == topup_id,
                CreditTopupOrder.tenant_id == self.tenant_id,
            )
        )).scalar_one_or_none()
        if not order:
            raise NotFoundException("CreditTopupOrder", str(topup_id))
        if order.payment_status != "initiated":
            return {**order.to_dict(), "already_terminal": True}

        order.payment_status = "cancelled"
        order.failure_reason = "Cancelled by tenant before completing payment"
        await self._audit("hs_finance.topup_cancelled", "credit_topup_order", str(order.id),
                          after={"order_ref": order.order_ref})
        await self.db.commit()
        return {**order.to_dict(), "already_terminal": False}

    async def list_topups(self, *, status: str | None = None, page: int = 1, page_size: int = 25) -> dict:
        clauses = [CreditTopupOrder.tenant_id == self.tenant_id]
        if status:
            clauses.append(CreditTopupOrder.payment_status == status)
        stmt = select(CreditTopupOrder).where(*clauses).order_by(CreditTopupOrder.created_at.desc())
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        rows = (await self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        items = []
        for r in rows:
            gross = _m(r.amount_paid); base = _m(r.credits_purchased)
            items.append({**r.to_dict(), "base_credits": str(base),
                          "gst_amount": str((gross - base).quantize(Decimal("0.01"))),
                          "total_payable": str(gross)})
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    # ── Deposit refund requests (section 12) ───────────────────────────────

    # The deposit refund request workflow (create/list/withdraw/respond/
    # admin_decide) was removed with the deposit in migration 317. A
    # top-up is spent down as commission, not held and returned, so there
    # is nothing to refund.

    async def export_transactions(self, *, date_from: str | None = None, date_to: str | None = None,
                                  ledger: str | None = None, status: str | None = None,
                                  type_: str | None = None) -> dict:
        data = await self.get_transactions(date_from=date_from, date_to=date_to,
                                          ledger=ledger, status=status, type_=type_,
                                          page=1, page_size=200)
        tenant = await self.db.get(Tenant, self.tenant_id)
        header = ["occurred_at", "reference", "ledger_label", "event_label", "description",
                  "debit", "credit", "usage_credit_balance_after", "status",
                  "related_job_id", "related_transaction_ref"]
        lines = [",".join(header)]
        for row in data["items"]:
            lines.append(",".join(
                '"' + str(row.get(k) if row.get(k) is not None else "—").replace('"', "'") + '"'
                for k in header
            ))
        await self._audit("hs_finance.statement_exported", "tenant_finance_statement", str(self.tenant_id),
                          after={"rows": len(data["items"]), "ledger": ledger, "type": type_,
                                 "date_from": date_from, "date_to": date_to})
        await self.db.commit()
        return {
            "filename": f"home-services-finance-{str(self.tenant_id)[:8]}.csv",
            "content_type": "text/csv",
            "row_count": len(data["items"]),
            "scope": {"tenant_id": str(self.tenant_id),
                      "tenant_name": tenant.business_name if tenant else None,
                      "vertical": HOME_SERVICES_VERTICAL_KEY,
                      "ledger": ledger or "all", "status": status or "all",
                      "type": type_ or "all",
                      "date_from": date_from, "date_to": date_to},
            "csv": "\n".join(lines),
        }

    # ── Audit trail (section 20 finance.view_audit) ─────────────────────────

    async def list_audit(self, page: int = 1, page_size: int = 25) -> dict:
        rows = (await self.db.execute(
            text("SELECT id, operation, entity_type, entity_id, actor_role, created_at "
                 "FROM platform_audit_logs WHERE tenant_id=:tid AND engine_id='finance_hub' "
                 "ORDER BY created_at DESC LIMIT :lim OFFSET :off"),
            {"tid": str(self.tenant_id), "lim": page_size, "off": (page - 1) * page_size},
        )).fetchall()
        total = (await self.db.execute(
            text("SELECT count(*) FROM platform_audit_logs WHERE tenant_id=:tid AND engine_id='finance_hub'"),
            {"tid": str(self.tenant_id)},
        )).scalar() or 0
        return {
            "items": [{"audit_id": str(r.id), "operation": r.operation,
                       "entity_type": r.entity_type, "entity_id": r.entity_id,
                       "actor_role": r.actor_role,
                       "created_at": r.created_at.isoformat() if r.created_at else None}
                      for r in rows],
            "total": total, "page": page, "page_size": page_size,
        }
