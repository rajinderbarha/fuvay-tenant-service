"""Field Ops Engine — Customer Job Tracking Router (Step 6).
Read-only: customer can view progress but can never update job status."""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import require_customer, UserContext
from app.dependencies.db import get_db
from app.engines.field_ops.service import FieldOpsService
from app.engines.field_ops.billing_service import BillingService
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/customer/jobs", tags=["Customer Job Tracking"])
ENGINE_ID = "field_ops"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_customer)) -> FieldOpsService:
    if u.role != "customer":
        raise ServiceOSException("CUSTOMER_JOB_ACCESS_DENIED",
            "This endpoint is for customer accounts only.", status_code=403)
    return FieldOpsService(db=db, request_id=getattr(r.state, "request_id", "—"),
                            actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                            actor_role=u.role)


def _billing_svc(r: Request, db: AsyncSession = Depends(get_db),
                  u: UserContext = Depends(require_customer)) -> BillingService:
    if u.role != "customer":
        raise ServiceOSException("CUSTOMER_JOB_ACCESS_DENIED",
            "This endpoint is for customer accounts only.", status_code=403)
    return BillingService(db=db, request_id=getattr(r.state, "request_id", "—"),
                           actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)


def _rid(r): return getattr(r.state, "request_id", "—")


@router.get("", summary="Step 6: My jobs", response_model=ApiResponse[dict])
async def my_jobs(r: Request,
                   limit: int = Query(50, ge=1, le=200),
                   cursor: str | None = Query(None),
                   u: UserContext = Depends(require_customer),
                   s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_customer_jobs(s.actor_id, limit, cursor), _rid(r), ENGINE_ID)


@router.get("/{job_id}", summary="Step 6: My job detail", response_model=ApiResponse[dict])
async def my_job_detail(job_id: uuid.UUID, r: Request,
                         s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_customer_job(job_id, s.actor_id), _rid(r), ENGINE_ID)


@router.get("/{job_id}/progress", summary="Step 6: My job progress", response_model=ApiResponse[dict])
async def my_job_progress(job_id: uuid.UUID, r: Request,
                           s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_customer_job_progress(job_id, s.actor_id), _rid(r), ENGINE_ID)


@router.get("/{job_id}/checklist", tags=["Job Checklist"],
            summary="Step 8: Completed checklist summary for my job (read-only)",
            response_model=ApiResponse[dict])
async def my_job_checklist_summary(job_id: uuid.UUID, r: Request,
                                    s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_customer_checklist_summary(job_id, s.actor_id), _rid(r), ENGINE_ID)


@router.get("/{job_id}/invoice", tags=["Invoices"],
            summary="Step 9: My job's invoice (own jobs only)",
            response_model=ApiResponse[dict])
async def my_job_invoice(job_id: uuid.UUID, r: Request,
                          s: BillingService = Depends(_billing_svc)) -> ApiResponse[dict]:
    return ok(await s.get_customer_job_invoice(s.actor_id, job_id), _rid(r), ENGINE_ID)


# ── Step 9: Customer Invoices ─────────────────────────────────────────────────
invoice_router = APIRouter(prefix="/v1/customer/invoices", tags=["Invoices"])


@invoice_router.get("", summary="Step 9: My invoices", response_model=ApiResponse[dict])
async def my_invoices(r: Request,
                       limit: int = Query(50, ge=1, le=200),
                       cursor: str | None = Query(None),
                       s: BillingService = Depends(_billing_svc)) -> ApiResponse[dict]:
    return ok(await s.get_customer_invoices(s.actor_id, limit, cursor), _rid(r), ENGINE_ID)


@invoice_router.get("/{invoice_id}", summary="Step 9: My invoice detail", response_model=ApiResponse[dict])
async def my_invoice_detail(invoice_id: uuid.UUID, r: Request,
                             s: BillingService = Depends(_billing_svc)) -> ApiResponse[dict]:
    return ok(await s.get_customer_invoice_detail(s.actor_id, invoice_id), _rid(r), ENGINE_ID)


# ── Step 8: Customer Quotes ───────────────────────────────────────────────────
quote_router = APIRouter(prefix="/v1/customer/quotes", tags=["Customer Quotes"])


@quote_router.get("", summary="Step 8: My quotes (filterable)", response_model=ApiResponse[dict])
async def my_quotes(r: Request,
                     status_filter: str | None = Query(None, alias="status"),
                     job_id: uuid.UUID | None = Query(None),
                     quote_type: str | None = Query(None),
                     created_from: str | None = Query(None),
                     created_to: str | None = Query(None),
                     s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_customer_quotes(s.actor_id, status_filter, job_id, quote_type,
                                            created_from, created_to), _rid(r), ENGINE_ID)


@quote_router.get("/{quote_id}", summary="Step 8: My quote detail with price breakdown",
                   response_model=ApiResponse[dict])
async def my_quote_detail(quote_id: uuid.UUID, r: Request,
                           s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_customer_quote_detail(s.actor_id, quote_id), _rid(r), ENGINE_ID)


@quote_router.post("/{quote_id}/approve", summary="Step 8: Approve my own quote",
                    response_model=ApiResponse[dict])
async def approve_my_quote(quote_id: uuid.UUID, r: Request,
                            s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.approve_customer_quote(quote_id, s.actor_id, body.get("customer_note")),
              _rid(r), ENGINE_ID)


@quote_router.post("/{quote_id}/reject", summary="Step 8: Reject my own quote — reason required",
                    response_model=ApiResponse[dict])
async def reject_my_quote(quote_id: uuid.UUID, r: Request,
                           s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.reject_customer_quote(quote_id, s.actor_id, body.get("reason")),
              _rid(r), ENGINE_ID)
