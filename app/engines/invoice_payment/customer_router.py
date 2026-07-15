"""Sprint 23 — Customer invoice endpoints (customer-safe view only)."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
from app.engines.invoice_payment.payment_service import ServicePaymentService

inv_svc = ServiceInvoiceService()
pay_svc = ServicePaymentService()

customer_invoice_router = APIRouter(prefix="/v1/customer/service-invoices", tags=["customer-invoices"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _raise_4xx(exc: ValueError):
    """MODULE-L5-02 bug #22: the invoice/payment services raise bare ValueErrors
    for domain rejections (INVOICE_NOT_FOUND / INVOICE_ACCESS_DENIED / etc.).
    Every customer handler here called them without catching, so a customer
    viewing an invoice they don't own — or one that doesn't exist — got a 500
    instead of a clean 403/404. Map to the error code + a 4xx."""
    code = str(exc)
    status = 404 if "NOT_FOUND" in code else (403 if "ACCESS_DENIED" in code else 422)
    raise ServiceOSException(code, code.replace("_", " ").title(), status_code=status)


@customer_invoice_router.get("")
async def customer_list_invoices(
    r: Request = None,
    status: str | None = None,
    page: int = 1, limit: int = 50,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """The customer's own invoice history (customer-safe view)."""
    offset = max(0, (max(1, page) - 1) * limit)
    data = await inv_svc.list_customer_invoices(
        db, str(user.user_id), status=status, limit=limit, offset=offset)
    return ok({"invoices": data}, _rid(r), "customer_list_invoices")


@customer_invoice_router.get("/{invoice_id}")
async def customer_get_invoice(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    try:
        data = await inv_svc.get_invoice_for_customer(db, invoice_id, str(user.user_id))
    except ValueError as exc:
        _raise_4xx(exc)
    return ok(data, _rid(r), "customer_get_invoice")


@customer_invoice_router.get("/{invoice_id}/payment-status")
async def customer_payment_status(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    # MODULE-L5-02 bug #22: verify the customer actually owns the invoice before
    # returning its payment timeline (previously any customer could read any
    # invoice's payment status by id — an IDOR).
    try:
        await inv_svc.get_invoice_for_customer(db, invoice_id, str(user.user_id))
    except ValueError as exc:
        _raise_4xx(exc)
    # Returns only customer-safe payment info — no wallet/commission
    data = await pay_svc.get_payment_timeline(db, invoice_id)
    safe = [
        {
            "payment_mode":       p["payment_mode"],
            "payment_status":     p["payment_status"],
            "collected_amount":   p["collected_amount"],
            "customer_confirmed": p["customer_confirmed"],
            "created_at":         p["created_at"],
        }
        for p in data
    ]
    return ok(safe, _rid(r), "customer_payment_status")


@customer_invoice_router.post("/{invoice_id}/apply-credit")
async def customer_apply_credit(
    invoice_id: str, body: dict, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """MODULE-L5-28: apply the customer's service credit to this invoice,
    reducing what they owe. Applied once per invoice (double-apply rejected)."""
    import uuid
    from decimal import Decimal, InvalidOperation
    from app.engines.customer_credits.service import CustomerCreditService

    # Verify ownership up front for a clean 403/404 (the service also checks).
    try:
        await inv_svc.get_invoice_for_customer(db, invoice_id, str(user.user_id))
    except ValueError as exc:
        _raise_4xx(exc)
    try:
        amount = Decimal(str(body.get("credit_amount_to_apply", 0)))
    except (InvalidOperation, TypeError):
        raise ServiceOSException("VALIDATION_ERROR", "credit_amount_to_apply must be a number.",
                                 status_code=422)
    svc = CustomerCreditService(db, uuid.UUID(str(user.user_id)), request_id=_rid(r))
    data = await svc.apply_credit_to_invoice(
        uuid.UUID(str(user.user_id)), uuid.UUID(invoice_id), amount)
    return ok(data, _rid(r), "customer_apply_credit")


@customer_invoice_router.post("/{invoice_id}/confirm-payment")
async def customer_confirm_payment(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    try:
        data = await pay_svc.customer_confirm_payment(
            db, invoice_id, str(user.user_id), str(user.user_id), _rid(r),
        )
    except ValueError as exc:
        _raise_4xx(exc)
    return ok({"confirmed": data["customer_confirmed"]}, _rid(r), "customer_confirm_payment")


@customer_invoice_router.get("/{invoice_id}/receipt")
async def customer_get_receipt(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    # Returns same safe invoice view as a receipt
    try:
        data = await inv_svc.get_invoice_for_customer(db, invoice_id, str(user.user_id))
    except ValueError as exc:
        _raise_4xx(exc)
    data["receipt_type"] = "service_invoice"
    data["generated_at"] = data.get("paid_at") or data.get("issued_at")
    return ok(data, _rid(r), "customer_get_receipt")
