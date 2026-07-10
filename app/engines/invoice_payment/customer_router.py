"""Sprint 23 — Customer invoice endpoints (customer-safe view only)."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
from app.engines.invoice_payment.payment_service import ServicePaymentService

inv_svc = ServiceInvoiceService()
pay_svc = ServicePaymentService()

customer_invoice_router = APIRouter(prefix="/v1/customer/service-invoices", tags=["customer-invoices"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@customer_invoice_router.get("/{invoice_id}")
async def customer_get_invoice(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await inv_svc.get_invoice_for_customer(db, invoice_id, str(user.user_id))
    return ok(data, _rid(r), "customer_get_invoice")


@customer_invoice_router.get("/{invoice_id}/payment-status")
async def customer_payment_status(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
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


@customer_invoice_router.post("/{invoice_id}/confirm-payment")
async def customer_confirm_payment(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = await pay_svc.customer_confirm_payment(
        db, invoice_id, str(user.user_id), str(user.user_id), _rid(r),
    )
    return ok({"confirmed": data["customer_confirmed"]}, _rid(r), "customer_confirm_payment")


@customer_invoice_router.get("/{invoice_id}/receipt")
async def customer_get_receipt(
    invoice_id: str, r: Request = None,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    # Returns same safe invoice view as a receipt
    data = await inv_svc.get_invoice_for_customer(db, invoice_id, str(user.user_id))
    data["receipt_type"] = "service_invoice"
    data["generated_at"] = data.get("paid_at") or data.get("issued_at")
    return ok(data, _rid(r), "customer_get_receipt")
