"""Payment Engine — Router (14 endpoints). Zero inline imports."""
import uuid
from decimal import Decimal
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission, require_tenant_mutation_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.payment.service import PaymentService
from app.exceptions import ServiceOSException
from app.integrations import razorpay_client
from app.schemas.base import ApiResponse, ok
logger = structlog.get_logger("payment.router")
router = APIRouter(prefix="/v1/payments", tags=["Payment Engine"])
ENGINE_ID = "payment"
def _svc(r: Request, db: AsyncSession=Depends(get_db), u: UserContext=Depends(get_current_user)):
    return PaymentService(db=db, request_id=getattr(r.state,"request_id","—"),
                           actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
                           actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)
def _rid(r): return getattr(r.state,"request_id","—")
@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name":"Payment Engine","version":"10.0.0",
            "endpoint_count": 14,"status":"active",
            "capabilities":["webhook_idempotency","sequential_invoice_numbers",
                            "immutable_payment_records","refund_audit_trail",
                            "payout_management","settlement_breakdown"]}
@router.post("/orders", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def create_order(r: Request, u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_BILLING_MANAGE)),
                        s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_payment_order(uuid.UUID(body["tenant_id"]),
              body.get("booking_id"), uuid.UUID(body["customer_id"]) if body.get("customer_id") else None,
              Decimal(str(body["amount"])), body.get("payment_type","customer_payment"),
              body.get("gateway","razorpay")), _rid(r), ENGINE_ID)
@router.post("/webhook", summary="Proven idempotent on gateway_payment_id", response_model=ApiResponse[dict])
async def payment_webhook(r: Request, s: PaymentService=Depends(lambda r, db=Depends(get_db): PaymentService(db=db))) -> ApiResponse[dict]:
    raw_body = await r.body()
    sig = r.headers.get("x-razorpay-signature", "")
    if not razorpay_client.verify_webhook_signature(raw_body, sig):
        raise ServiceOSException("WEBHOOK_VERIFICATION_FAILED", "Invalid Razorpay webhook signature.")
    body = await r.json()
    return ok(await s.process_payment_webhook(
        uuid.UUID(body["tenant_id"]), body.get("gateway","razorpay"),
        body["gateway_payment_id"], body.get("gateway_order_id"),
        Decimal(str(body["amount"])), body.get("status","captured"),
        body.get("booking_id"), uuid.UUID(body["customer_id"]) if body.get("customer_id") else None,
        body.get("payment_type","customer_payment"), body), _rid(r), ENGINE_ID)
@router.get("/{payment_id}", response_model=ApiResponse[dict])
async def get_payment(payment_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                       s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_payment(payment_id), _rid(r), ENGINE_ID)
@router.get("", summary="List payments by tenant", response_model=ApiResponse[dict])
async def list_payments(r: Request, tenant_id: uuid.UUID=Query(...),
                         limit: int=Query(50,ge=1,le=200), cursor: str|None=Query(None),
                         u: UserContext=Depends(get_current_user), s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_payments(tenant_id, limit, cursor), _rid(r), ENGINE_ID)
@router.post("/{payment_id}/refund", response_model=ApiResponse[dict])
async def create_refund(payment_id: uuid.UUID, r: Request, u: UserContext=Depends(require_super_admin),
                         s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.create_refund(payment_id, Decimal(str(body["amount"])), body["reason"]), _rid(r), ENGINE_ID)
@router.get("/refunds/{refund_id}", response_model=ApiResponse[dict])
async def get_refund(refund_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                      s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_refund(refund_id), _rid(r), ENGINE_ID)
@router.get("/tenants/{tenant_id}/refunds", response_model=ApiResponse[dict])
async def list_refunds(tenant_id: uuid.UUID, r: Request, limit: int=Query(50,ge=1,le=200),
                        cursor: str|None=Query(None), u: UserContext=Depends(get_current_user),
                        s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_refunds(tenant_id, limit, cursor), _rid(r), ENGINE_ID)
@router.post("/invoices", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def generate_invoice(r: Request, u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_BILLING_MANAGE)),
                            s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.generate_invoice(uuid.UUID(body["tenant_id"]),
              uuid.UUID(body["payment_id"]) if body.get("payment_id") else None,
              body.get("booking_id"), Decimal(str(body["amount"])),
              Decimal(str(body.get("tax_amount","0"))), body.get("line_items",[]),
              body.get("invoice_type","service")), _rid(r), ENGINE_ID)
@router.get("/invoices/{invoice_id}", response_model=ApiResponse[dict])
async def get_invoice(invoice_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                       s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_invoice(invoice_id), _rid(r), ENGINE_ID)
@router.get("/tenants/{tenant_id}/invoices", response_model=ApiResponse[dict])
async def list_invoices(tenant_id: uuid.UUID, r: Request, limit: int=Query(50,ge=1,le=200),
                         cursor: str|None=Query(None), u: UserContext=Depends(get_current_user),
                         s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_invoices(tenant_id, limit, cursor), _rid(r), ENGINE_ID)
@router.post("/tenants/{tenant_id}/payout", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def request_payout(tenant_id: uuid.UUID, r: Request, u: UserContext=Depends(require_tenant_mutation_permission(P.TENANT_BILLING_MANAGE)),
                          s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.request_payout(tenant_id, Decimal(str(body["amount"])), body.get("bank_account",{})), _rid(r), ENGINE_ID)
@router.get("/payouts/{payout_id}", response_model=ApiResponse[dict])
async def get_payout(payout_id: uuid.UUID, r: Request, u: UserContext=Depends(get_current_user),
                      s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_payout_status(payout_id), _rid(r), ENGINE_ID)
@router.get("/tenants/{tenant_id}/payouts", response_model=ApiResponse[dict])
async def list_payouts(tenant_id: uuid.UUID, r: Request, limit: int=Query(50,ge=1,le=200),
                        cursor: str|None=Query(None), u: UserContext=Depends(get_current_user),
                        s: PaymentService=Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_payouts(tenant_id, limit, cursor), _rid(r), ENGINE_ID)
