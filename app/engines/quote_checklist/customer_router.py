"""Sprint 22 — Customer quote self-service endpoints."""
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, require_customer
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
from app.engines.quote_checklist.checklist_service import ServiceChecklistService
# Slice 2F-16: every route here previously used get_current_user only -- no
# explicit canonical-customer role check. Ownership (quote.customer_id ==
# caller's own server-derived user_id) already made cross-customer
# impersonation impractical, but a non-customer role (tenant_owner/staff)
# could still reach these routes at all, which is not the intended persona
# boundary. require_customer (existing dependency, no new role) makes the
# canonical customer persona explicit and denies every other role.

quote_svc = ServiceJobQuoteService()
checklist_svc = ServiceChecklistService()

customer_router = APIRouter(prefix="/customer/quotes", tags=["customer-quotes"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@customer_router.get("/jobs/{job_id}")
async def customer_list_quotes(
    job_id: str, r: Request,
    user=Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.list_customer_quotes(db, str(user.user_id), job_id)
    return ok(data, _rid(r), "customer_list_quotes")


@customer_router.get("/{quote_id}")
async def customer_get_quote(
    quote_id: str, r: Request,
    user=Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.get_quote(db, quote_id, customer_id=str(user.user_id))
    return ok(data, _rid(r), "customer_get_quote")


@customer_router.post("/{quote_id}/approve")
async def customer_approve_quote(
    quote_id: str, r: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user=Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.customer_approve(
        db, quote_id, str(user.user_id),
        idempotency_key=idempotency_key,
        user_id=str(user.user_id), request_id=_rid(r),
    )
    return ok(data, _rid(r), "customer_approve_quote")


@customer_router.post("/{quote_id}/reject")
async def customer_reject_quote(
    quote_id: str, body: dict, r: Request,
    user=Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.customer_reject(
        db, quote_id, str(user.user_id),
        reason=body.get("reason", ""),
        user_id=str(user.user_id), request_id=_rid(r),
    )
    return ok(data, _rid(r), "customer_reject_quote")


@customer_router.post("/{quote_id}/request-revision")
async def customer_request_revision(
    quote_id: str, body: dict, r: Request,
    user=Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.customer_request_revision(
        db, quote_id, str(user.user_id),
        reason=body.get("reason", ""),
        user_id=str(user.user_id), request_id=_rid(r),
    )
    return ok(data, _rid(r), "customer_request_revision")


@customer_router.get("/{quote_id}/events")
async def customer_quote_events(
    quote_id: str, r: Request,
    user=Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    data = await quote_svc.list_quote_events(db, quote_id, customer_id=str(user.user_id))
    return ok(data, _rid(r), "customer_quote_events")
