"""Tenant-facing Finance Readiness onboarding step (Home Services, step 7 of 8).

Canonical model: for Home Services the customer pays the tenant's business
directly — Fuvay never collects, holds or settles that job payment
(app.engines.invoice_payment.commission_service.ServiceCommissionService
debits the tenant's platform wallet for commission on the invoice value, it
never routes the customer's payment through Fuvay). This router only
lets the tenant declare HOW it accepts that direct payment and its invoice
preferences (`TenantFinanceReadiness`), and surfaces the already-resolved,
read-only Home Services finance policy from the published vertical
monetization policy. Technician seats and usage credit are purchased only in
the Technician Seat Plan step and are deliberately absent from this endpoint.
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
from app.engines.tenant_engine.models import TenantFinanceReadiness
from app.engines.vertical_catalog.home_services_setup_service import HOME_SERVICES_VERTICAL_KEY
from app.engines.invoice_payment.commission_service import resolve_provider_commission_rate

from app.dependencies.setup_sequence import enforce_setup_sequence

router = APIRouter(dependencies=[Depends(enforce_setup_sequence)], prefix="/v1/tenant/home-services/setup/finance", tags=["Tenant Finance Readiness"])


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
            "accepts_card_at_service_location": False, "accepts_bank_transfer": False,
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

    commission_rate = str(await resolve_provider_commission_rate(db, tenant_row.category_id))

    readiness_row = await _row(db, tid)
    methods_selected = readiness_row is not None and any([
        readiness_row.accepts_cash, readiness_row.accepts_upi,
    ])
    invoice_name = (readiness_row.invoice_business_name if readiness_row and readiness_row.invoice_business_name
                    else (profile_row.trade_name if profile_row else None) or tenant_row.business_name)
    invoice_details_complete = bool(invoice_name) and bool(readiness_row and readiness_row.invoice_prefix)

    checks = {
        "direct_methods_selected": methods_selected,
        "confirmation_configured": readiness_row is not None,
        "invoice_details_complete": invoice_details_complete,
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
            "job_settlement": "Outside Fuvay",
            "pricing_ownership": "Tenant business",
            "provider_commission_pct": commission_rate,
            "policy_version": "HS_VERTICAL_MONETIZATION_LIVE",
        },
        "notice": "Customers pay your business directly. Fuvay records the payment but does not hold or settle job funds.",
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
    accepts_bank_transfer: bool = False
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

    row.accepts_cash = body.accepts_cash
    row.accepts_upi = body.accepts_upi
    row.accepts_card_at_service_location = False
    row.accepts_bank_transfer = False
    row.payment_confirmation_required = body.payment_confirmation_required
    row.invoice_business_name = body.invoice_business_name
    row.invoice_prefix = body.invoice_prefix
    row.issue_customer_receipt = body.issue_customer_receipt
    row.updated_at = datetime.now(timezone.utc)

    await db.commit()
    manifest = await _build_manifest(db, tid)
    return ok(manifest, request_id=rid)
