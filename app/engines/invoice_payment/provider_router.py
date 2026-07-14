"""Sprint 23 — Provider / Staff invoice, wallet, subscription endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
from app.engines.invoice_payment.payment_service import ServicePaymentService
from app.engines.invoice_payment.commission_service import ServiceCommissionService
from app.engines.invoice_payment.wallet_service import ProviderCreditWalletService
from app.engines.invoice_payment.subscription_service import ProviderSubscriptionStatusService

inv_svc  = ServiceInvoiceService()
pay_svc  = ServicePaymentService()
com_svc  = ServiceCommissionService()
wal_svc  = ProviderCreditWalletService()
sub_svc  = ProviderSubscriptionStatusService()

provider_invoice_router = APIRouter(prefix="/v1/provider/service-invoices", tags=["provider-service-invoices"])
provider_wallet_router  = APIRouter(prefix="/v1/provider/wallet",           tags=["provider-wallet"])
provider_sub_router     = APIRouter(prefix="/v1/provider/subscription-status", tags=["provider-subscription"])
staff_invoice_router    = APIRouter(prefix="/v1/staff/service-invoices",    tags=["staff-service-invoices"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Provider: list own invoices ────────────────────────────────────────────────

@provider_invoice_router.get("")
async def provider_list_invoices(
    status: str | None = None, limit: int = 100, offset: int = 0, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await inv_svc.list_tenant_invoices(db, str(user.tenant_id), status, limit=limit, offset=offset)
    return ok(data, _rid(r), "provider_list_invoices")


@provider_invoice_router.get("/{invoice_id}")
async def provider_get_invoice(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await inv_svc.get_invoice_for_tenant(db, invoice_id, str(user.tenant_id))
    return ok(data, _rid(r), "provider_get_invoice")


@provider_invoice_router.post("/{invoice_id}/issue")
async def provider_issue_invoice(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await inv_svc.issue_invoice(db, invoice_id, str(user.tenant_id),
                                       str(user.user_id), _rid(r))
    return ok(data, _rid(r), "provider_issue_invoice")


@provider_invoice_router.post("/{invoice_id}/record-payment")
async def provider_record_payment(
    invoice_id: str, body: dict, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    try:
        data = await pay_svc.record_onsite_payment(
            db, invoice_id, str(user.tenant_id),
            payment_mode=body.get("payment_mode", "onsite_cash"),
            collected_amount=float(body.get("collected_amount", 0)),
            proof_media_url=body.get("proof_media_url"),
            user_id=str(user.user_id),
            # MODULE-L5-02 bug #17: UserContext has no `staff_member_id` attribute
            # at all, so this line raised AttributeError -> 500 on every payment
            # record, killing the whole post-completion settlement flow. The staff
            # identity in this system is keyed off users.id (see
            # home_service_assignment reconciliation), so fall back to user id.
            staff_member_id=str(getattr(user, "staff_member_id", None) or user.user_id),
            request_id=_rid(r),
        )
    except ValueError as exc:
        # MODULE-L5-02 bug #18: the service raises bare ValueErrors for domain
        # rejections (invalid mode / not found / access denied / already paid);
        # they were leaking as 500s. Map to the ticket's error code + a 4xx.
        code = str(exc)
        status = 404 if code in ("INVOICE_NOT_FOUND",) else (
            403 if code in ("INVOICE_ACCESS_DENIED",) else 422)
        raise ServiceOSException(code, code.replace("_", " ").title(), status_code=status)
    return ok(data, _rid(r), "provider_record_payment")


@provider_invoice_router.get("/{invoice_id}/financial-timeline")
async def provider_financial_timeline(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await pay_svc.get_payment_timeline(db, invoice_id, str(user.tenant_id))
    return ok(data, _rid(r), "provider_financial_timeline")


@provider_invoice_router.get("/{invoice_id}/commission-status")
async def provider_commission_status(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await com_svc.get_commission_status(db, invoice_id)
    return ok(data, _rid(r), "provider_commission_status")


# ── Staff: create invoice for job ──────────────────────────────────────────────

@staff_invoice_router.post("")
async def staff_create_invoice(
    body: dict, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await inv_svc.create_invoice(
        db,
        job_id=body["job_id"],
        tenant_id=str(user.tenant_id),
        source=body.get("source", "manual_final"),
        quote_id=body.get("quote_id"),
        notes=body.get("notes"),
        user_id=str(user.user_id),
        request_id=_rid(r),
    )
    return ok(data, _rid(r), "staff_create_invoice")


@staff_invoice_router.post("/{invoice_id}/items")
async def staff_add_invoice_item(
    invoice_id: str, body: dict, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await inv_svc.add_item(
        db, invoice_id, str(user.tenant_id),
        item_type=body.get("item_type", "service"),
        item_name=body["item_name"],
        item_description=body.get("item_description"),
        quantity=float(body.get("quantity", 1)),
        unit_price=float(body.get("unit_price", 0)),
        is_customer_visible=bool(body.get("is_customer_visible", True)),
        user_id=str(user.user_id),
        request_id=_rid(r),
    )
    return ok(data, _rid(r), "staff_add_invoice_item")


@staff_invoice_router.get("/jobs/{job_id}")
async def staff_job_invoice(
    job_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await inv_svc.get_job_invoice(db, job_id, str(user.tenant_id))
    return ok(data, _rid(r), "staff_job_invoice")


# ── Provider: wallet ───────────────────────────────────────────────────────────

@provider_wallet_router.get("")
async def provider_get_wallet(
    r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    # MODULE-L5-02: a tenant may not have a wallet provisioned yet. get_wallet
    # raises a bare ValueError -> 500 (breaking the provider wallet page). Return
    # a zero-balance default (same fix as the admin wallet handler).
    try:
        data = await wal_svc.get_wallet(db, str(user.tenant_id))
    except ValueError:
        data = {"tenant_id": str(user.tenant_id), "currency": "INR", "current_balance": "0",
                "reserved_balance": "0", "total_purchased": "0", "total_deducted": "0",
                "low_balance_threshold": None, "is_active": False,
                "last_transaction_at": None, "provisioned": False}
    return ok(data, _rid(r), "provider_get_wallet")


@provider_wallet_router.get("/ledger")
async def provider_wallet_ledger(
    r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await wal_svc.get_ledger(db, str(user.tenant_id))
    return ok(data, _rid(r), "provider_wallet_ledger")


@provider_wallet_router.get("/commission-records")
async def provider_commission_records(
    limit: int = 100, offset: int = 0, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await com_svc.list_all_commissions(db, str(user.tenant_id), limit=limit, offset=offset)
    return ok(data, _rid(r), "provider_commission_records")


# ── Provider: subscription status ─────────────────────────────────────────────

@provider_sub_router.get("")
async def provider_subscription_status(
    r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await sub_svc.get_provider_subscription_status(db, str(user.tenant_id))
    return ok(data, _rid(r), "provider_subscription_status")
