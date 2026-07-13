"""Sprint 23 — Admin financial endpoints.

MODULE-L5-01A: every handler in this file operates platform-wide (across
ALL tenants -- list-all/get-any/mutate-any, with tenant_id as an optional
admin filter, never the caller's own identity). It was previously gated
only by bare `get_current_user`, with zero permission or role check --
meaning any authenticated user of any role, including `customer`, could
list every tenant's invoices/payments/commissions, view or CREDIT any
tenant's wallet with an arbitrary amount, and read platform-wide financial
event logs. Fixed to `require_super_admin`, matching the identical pattern
already used for equivalent platform-wide wallet operations in the sibling
`field_ops/admin_finance_router.py`.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import require_super_admin
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
from app.engines.invoice_payment.payment_service import ServicePaymentService
from app.engines.invoice_payment.commission_service import ServiceCommissionService
from app.engines.invoice_payment.wallet_service import ProviderCreditWalletService
from app.engines.invoice_payment.subscription_service import ProviderSubscriptionStatusService
from app.engines.invoice_payment.models import FinancialEvent

inv_svc = ServiceInvoiceService()
pay_svc = ServicePaymentService()
com_svc = ServiceCommissionService()
wal_svc = ProviderCreditWalletService()
sub_svc = ProviderSubscriptionStatusService()

admin_invoice_router    = APIRouter(prefix="/v1/admin/service-invoices",     tags=["admin-invoices"])
admin_payment_router    = APIRouter(prefix="/v1/admin/payments",             tags=["admin-payments"])
admin_commission_router = APIRouter(prefix="/v1/admin/commission-records",   tags=["admin-commission"])
admin_wallet_router     = APIRouter(prefix="/v1/admin/provider-wallets",     tags=["admin-wallets"])
admin_sub_router        = APIRouter(prefix="/v1/admin/subscription-status",  tags=["admin-subscription"])
admin_fin_events_router = APIRouter(prefix="/v1/admin/financial-events",     tags=["admin-financial-events"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Admin: invoices ────────────────────────────────────────────────────────────

@admin_invoice_router.get("")
async def admin_list_invoices(
    tenant_id: str | None = None, status: str | None = None,
    limit: int = 100, offset: int = 0, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await inv_svc.list_all_invoices(db, tenant_id, status, limit=limit, offset=offset)
    return ok(data, _rid(r), "admin_list_invoices")


@admin_invoice_router.get("/{invoice_id}")
async def admin_get_invoice(
    invoice_id: str, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await inv_svc.get_invoice(db, invoice_id)
    return ok(data, _rid(r), "admin_get_invoice")


# ── Admin: payments ────────────────────────────────────────────────────────────

@admin_payment_router.get("")
async def admin_list_payments(
    tenant_id: str | None = None, limit: int = 100, offset: int = 0, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await pay_svc.list_all_payments(db, tenant_id, limit=limit, offset=offset)
    return ok(data, _rid(r), "admin_list_payments")


@admin_payment_router.post("/{payment_id}/verify")
async def admin_verify_payment(
    payment_id: str, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await pay_svc.admin_verify_payment(db, payment_id, str(user.user_id), _rid(r))
    return ok(data, _rid(r), "admin_verify_payment")


# ── Admin: commissions ─────────────────────────────────────────────────────────

@admin_commission_router.get("")
async def admin_list_commissions(
    tenant_id: str | None = None, status: str | None = None,
    limit: int = 100, offset: int = 0, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await com_svc.list_all_commissions(db, tenant_id, status, limit=limit, offset=offset)
    return ok(data, _rid(r), "admin_list_commissions")


@admin_commission_router.get("/{commission_id}")
async def admin_get_commission(
    commission_id: str, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    from app.engines.invoice_payment.models import SvcCommissionRecord
    import uuid
    res = await db.execute(
        select(SvcCommissionRecord).where(SvcCommissionRecord.id == uuid.UUID(commission_id))
    )
    cr = res.scalar_one_or_none()
    if not cr:
        raise ValueError("COMMISSION_RECORD_NOT_FOUND")
    return ok(cr.to_dict(), _rid(r), "admin_get_commission")


@admin_commission_router.post("/{commission_id}/retry")
async def admin_retry_commission(
    commission_id: str, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await com_svc.retry_commission_deduction(
        db, commission_id, str(user.user_id), _rid(r),
    )
    return ok(data, _rid(r), "admin_retry_commission")


@admin_commission_router.post("/{commission_id}/reverse")
async def admin_reverse_commission(
    commission_id: str, body: dict, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await com_svc.reverse_commission(
        db, commission_id, str(user.user_id),
        reason=body.get("reason", ""),
        request_id=_rid(r),
    )
    return ok(data, _rid(r), "admin_reverse_commission")


# ── Admin: wallets ─────────────────────────────────────────────────────────────

@admin_wallet_router.get("")
async def admin_list_wallets(
    limit: int = 200, offset: int = 0, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await wal_svc.list_all_wallets(db, limit=limit, offset=offset)
    return ok(data, _rid(r), "admin_list_wallets")


@admin_wallet_router.get("/{tenant_id}")
async def admin_get_wallet(
    tenant_id: str, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await wal_svc.get_wallet(db, tenant_id)
    return ok(data, _rid(r), "admin_get_wallet")


@admin_wallet_router.get("/{tenant_id}/ledger")
async def admin_wallet_ledger(
    tenant_id: str, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await wal_svc.get_ledger(db, tenant_id)
    return ok(data, _rid(r), "admin_wallet_ledger")


@admin_wallet_router.post("/{tenant_id}/credit")
async def admin_credit_wallet(
    tenant_id: str, body: dict, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await wal_svc.admin_credit(
        db, tenant_id,
        amount=float(body.get("amount", 0)),
        reason=body.get("reason", "Admin credit adjustment"),
        admin_user_id=str(user.user_id),
    )
    return ok(data, _rid(r), "admin_credit_wallet")


# ── Admin: subscription status ─────────────────────────────────────────────────

@admin_sub_router.get("")
async def admin_subscription_status(
    limit: int = 200, offset: int = 0, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    data = await sub_svc.list_all_subscription_statuses(db, limit=limit, offset=offset)
    return ok(data, _rid(r), "admin_subscription_status")


# ── Admin: financial events ────────────────────────────────────────────────────

@admin_fin_events_router.get("")
async def admin_financial_events(
    tenant_id: str | None = None, event_type: str | None = None, r: Request = None,
    user=Depends(require_super_admin), db: AsyncSession = Depends(get_db),
):
    import uuid
    q = select(FinancialEvent).order_by(FinancialEvent.created_at.desc()).limit(200)
    if tenant_id:
        q = q.where(FinancialEvent.tenant_id == uuid.UUID(tenant_id))
    if event_type:
        q = q.where(FinancialEvent.event_type == event_type)
    res = await db.execute(q)
    data = [ev.to_dict() for ev in res.scalars().all()]
    return ok(data, _rid(r), "admin_financial_events")
