"""Tenant-facing Finance Readiness onboarding step (Home Services, step 7 of 8).

Canonical model: for Home Services the customer pays the tenant's business
directly — ServiceOS never collects, holds or settles that job payment
(app.engines.invoice_payment.commission_service.ServiceCommissionService
debits the tenant's platform wallet for commission on the invoice value, it
never routes the customer's payment through ServiceOS). This router only
lets the tenant declare HOW it accepts that direct payment and its invoice
preferences (`TenantFinanceReadiness`), and surfaces the already-resolved,
read-only Home Services finance policy: category commission rate
(ServiceCategory.commission_pct, the live authority — NOT the frozen
package_commerce commission path), usage-credit balance (tenant_billing),
and security deposit (tenant_billing.security_deposit_amount/paid — the
real, live deposit fields; collected only after admin approval, never here).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_vertical_not_active
from app.core.permissions import require_tenant_owner_mutation
from app.schemas.base import ok
from app.exceptions import NotFoundException
from app.engines.tenant_engine.models import TenantFinanceReadiness, TenantBilling
from app.engines.vertical_catalog.home_services_setup_service import HOME_SERVICES_VERTICAL_KEY
from app.engines.invoice_payment.commission_service import resolve_provider_commission_rate
from app.engines.vertical_catalog.service import VerticalCatalogService
from app.engines.vertical_catalog.finance_policy_service import (
    resolve_published_policy, resolve_qualifying_technician_count, FinancePolicyResolutionError,
)

router = APIRouter(prefix="/v1/tenant/home-services/setup/finance", tags=["Tenant Finance Readiness"])


def _tid(user: UserContext) -> uuid.UUID:
    if not user.tenant_id:
        from fastapi import HTTPException
        raise HTTPException(403, "No tenant context")
    return uuid.UUID(user.tenant_id)


async def _row(db: AsyncSession, tid: uuid.UUID) -> TenantFinanceReadiness | None:
    return (await db.execute(
        select(TenantFinanceReadiness).where(TenantFinanceReadiness.tenant_id == tid)
    )).scalar_one_or_none()


def _row_dict(r: TenantFinanceReadiness | None) -> dict:
    if not r:
        return {
            "accepts_cash": True, "accepts_upi": True,
            "accepts_card_at_service_location": False, "accepts_bank_transfer": True,
            "payment_confirmation_required": True,
            "invoice_business_name": None, "invoice_prefix": None,
            "issue_customer_receipt": True,
        }
    return {
        "accepts_cash": r.accepts_cash, "accepts_upi": r.accepts_upi,
        "accepts_card_at_service_location": r.accepts_card_at_service_location,
        "accepts_bank_transfer": r.accepts_bank_transfer,
        "payment_confirmation_required": r.payment_confirmation_required,
        "invoice_business_name": r.invoice_business_name, "invoice_prefix": r.invoice_prefix,
        "issue_customer_receipt": r.issue_customer_receipt,
    }


async def _build_manifest(db: AsyncSession, tid: uuid.UUID) -> dict:
    tenant_row = (await db.execute(
        text("SELECT business_name, category_id FROM tenants WHERE id=:tid"), {"tid": str(tid)},
    )).fetchone()
    if not tenant_row:
        raise NotFoundException("Tenant", str(tid))

    profile_row = (await db.execute(
        text("SELECT trade_name, gstin, gstin_verified FROM tenant_business_profiles WHERE tenant_id=:tid"),
        {"tid": str(tid)},
    )).fetchone()

    billing_row = (await db.execute(
        text("SELECT credit_balance, security_deposit_amount, security_deposit_paid "
             "FROM tenant_billing WHERE tenant_id=:tid"),
        {"tid": str(tid)},
    )).fetchone()

    commission_rate = str(await resolve_provider_commission_rate(db, tenant_row.category_id))

    deposit_amount = float(billing_row.security_deposit_amount) if billing_row and billing_row.security_deposit_amount else 0.0
    deposit_paid = bool(billing_row and billing_row.security_deposit_paid)
    credit_balance = float(billing_row.credit_balance) if billing_row else 0.0

    # Real fix: `tenant_billing.security_deposit_amount` is only ever
    # populated AFTER a deposit is captured (see
    # activation_payment_service.confirm_activation_payment_webhook), so
    # before payment this manifest previously reported "not_required" for
    # every tenant who simply hadn't paid yet -- indistinguishable from a
    # tenant whose policy genuinely requires nothing. The required amount
    # must be resolved from the published finance policy, the same source
    # activation_payment_service already uses to size the Razorpay order.
    required_deposit_amount = 0.0
    required_credit_amount = 0.0
    policy_resolved = False
    try:
        v = await VerticalCatalogService()._by_key(db, HOME_SERVICES_VERTICAL_KEY)
        policy = await resolve_published_policy(db, v.id)
        qualifying = await resolve_qualifying_technician_count(db, tid)
        required_deposit_amount = max(
            float(policy.minimum_deposit),
            float(policy.deposit_amount_per_technician) * max(1, qualifying),
        )
        required_credit_amount = float(policy.credit_package_base_amount)
        policy_resolved = True
    except FinancePolicyResolutionError:
        # No published policy yet -- nothing to pay, nothing to gate on.
        pass

    readiness_row = await _row(db, tid)
    methods_selected = readiness_row is not None and any([
        readiness_row.accepts_cash, readiness_row.accepts_upi,
        readiness_row.accepts_card_at_service_location, readiness_row.accepts_bank_transfer,
    ])
    invoice_name = (readiness_row.invoice_business_name if readiness_row and readiness_row.invoice_business_name
                    else (profile_row.trade_name if profile_row else None) or tenant_row.business_name)
    invoice_details_complete = bool(invoice_name) and bool(readiness_row and readiness_row.invoice_prefix)

    activation_requirements_pending = (deposit_amount > 0 and not deposit_paid)

    checks = {
        "direct_methods_selected": methods_selected,
        "confirmation_configured": readiness_row is not None,
        "invoice_details_complete": invoice_details_complete,
        "activation_requirements_pending": activation_requirements_pending,
    }
    setup_complete = methods_selected and checks["confirmation_configured"] and invoice_details_complete
    complete_count = sum(1 for k in ("direct_methods_selected", "confirmation_configured", "invoice_details_complete") if checks[k])
    percentage = round((complete_count / 3) * 100)

    return {
        "readiness_percentage": percentage,
        "setup_complete": setup_complete,
        "checks": checks,
        "direct_payment": _row_dict(readiness_row),
        "invoice_defaults": {
            "business_name": invoice_name,
            "gstin": profile_row.gstin if profile_row else None,
            "gstin_verified": bool(profile_row and profile_row.gstin_verified),
        },
        "policy": {
            "vertical": HOME_SERVICES_VERTICAL_KEY,
            "revenue_model": "Provider commission on completed jobs",
            "customer_pays": "Provider directly",
            "job_settlement": "Outside ServiceOS",
            "pricing_ownership": "Tenant business",
            "provider_commission_pct": commission_rate,
            "policy_version": "HS_COMMISSION_LIVE",
        },
        "activation_requirements": {
            "security_deposit": {
                "amount": deposit_amount,
                "required_amount": required_deposit_amount,
                "status": "paid" if deposit_paid else (
                    "not_required" if not policy_resolved or required_deposit_amount <= 0 else "required_after_approval"
                ),
                "can_pay": policy_resolved and required_deposit_amount > 0 and not deposit_paid,
            },
            "usage_credit_wallet": {
                "balance": credit_balance,
                "required_amount": required_credit_amount,
                "status": "active" if (billing_row and credit_balance >= required_credit_amount and required_credit_amount > 0) else "not_active",
                "can_pay": policy_resolved and required_credit_amount > 0 and credit_balance < required_credit_amount,
            },
        },
        "notice": "Customers pay your business directly. ServiceOS records the payment but does not hold or settle job funds.",
    }


@router.get("")
async def get_finance_readiness(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_vertical_not_active(HOME_SERVICES_VERTICAL_KEY)),
):
    tid = _tid(user)
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")
    manifest = await _build_manifest(db, tid)
    return ok(manifest, request_id=rid)


class SaveFinanceReadinessRequest(BaseModel):
    accepts_cash: bool = True
    accepts_upi: bool = True
    accepts_card_at_service_location: bool = False
    accepts_bank_transfer: bool = True
    payment_confirmation_required: bool = True
    invoice_business_name: str | None = Field(default=None, max_length=255)
    invoice_prefix: str | None = Field(default=None, max_length=20)
    issue_customer_receipt: bool = True


@router.put("")
async def save_finance_readiness(
    body: SaveFinanceReadinessRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_tenant_owner_mutation),
    _guard: UserContext = Depends(require_vertical_not_active(HOME_SERVICES_VERTICAL_KEY)),
):
    tid = _tid(user)
    rid = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID", "—")

    row = await _row(db, tid)
    if not row:
        row = TenantFinanceReadiness(tenant_id=tid)
        db.add(row)

    # Saving Finance Readiness is what makes finance genuinely "configured"
    # for onboarding purposes -- the readiness aggregator
    # (home_services_setup_service.get_setup_overview) gates the
    # FINANCE_READINESS section purely on a tenant_billing row existing.
    # Nothing else in the onboarding flow ever created that row for a new
    # tenant, so without this the section stayed permanently incomplete no
    # matter how completely the tenant filled out this step.
    billing_row = (await db.execute(
        select(TenantBilling).where(TenantBilling.tenant_id == tid)
    )).scalar_one_or_none()
    if not billing_row:
        db.add(TenantBilling(tenant_id=tid, vertical_key=HOME_SERVICES_VERTICAL_KEY))

    row.accepts_cash = body.accepts_cash
    row.accepts_upi = body.accepts_upi
    row.accepts_card_at_service_location = body.accepts_card_at_service_location
    row.accepts_bank_transfer = body.accepts_bank_transfer
    row.payment_confirmation_required = body.payment_confirmation_required
    row.invoice_business_name = body.invoice_business_name
    row.invoice_prefix = body.invoice_prefix
    row.issue_customer_receipt = body.issue_customer_receipt
    row.updated_at = datetime.now(timezone.utc)

    await db.commit()
    manifest = await _build_manifest(db, tid)
    return ok(manifest, request_id=rid)
