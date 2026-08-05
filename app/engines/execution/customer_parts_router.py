"""PARTS-APPROVAL phase -- customer-facing parts-request read/decide.

Mirrors the established `quote_checklist/customer_router.py` shape and
mount convention (`/v1/customer/...`). Backed by the existing `PartsRequest`
model and `HomeServiceExecutionService`'s new customer methods -- no
parallel parts engine.
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_customer
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.execution.home_service_service import HomeServiceJobExecutionService
from app.engines.execution.mobile_completion_proof_service import MobileCompletionProofService

router = APIRouter(prefix="/v1/customer/service-jobs", tags=["customer-parts"])
_svc = HomeServiceJobExecutionService()
_proof_svc = MobileCompletionProofService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/{job_id}/parts-requests")
async def customer_list_parts_requests(
    job_id: uuid.UUID, r: Request,
    user=Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    data = await _svc.customer_list_parts_requests(db, job_id, uuid.UUID(str(user.user_id)))
    return ok(data, _rid(r), "customer_list_parts_requests")


@router.post("/parts-requests/{parts_request_id}/approve")
async def customer_approve_parts_request(
    parts_request_id: uuid.UUID, r: Request,
    user=Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    data = await _svc.customer_decide_parts_request(
        db, parts_request_id, uuid.UUID(str(user.user_id)),
        decision="approve", reason=None, request_id=_rid(r),
    )
    await db.commit()
    return ok(data, _rid(r), "customer_approve_parts_request")


@router.post("/parts-requests/{parts_request_id}/decline")
async def customer_decline_parts_request(
    parts_request_id: uuid.UUID, body: dict, r: Request,
    user=Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    data = await _svc.customer_decide_parts_request(
        db, parts_request_id, uuid.UUID(str(user.user_id)),
        decision="decline", reason=body.get("reason"), request_id=_rid(r),
    )
    await db.commit()
    return ok(data, _rid(r), "customer_decline_parts_request")


@router.post("/{job_id}/acknowledge-handover")
async def customer_acknowledge_handover(
    job_id: uuid.UUID, r: Request,
    user=Depends(require_customer), db: AsyncSession = Depends(get_db),
):
    """Found genuinely missing during the Final Phase end-to-end pass: no
    customer-facing endpoint anywhere let the customer acknowledge job
    handover, which permanently blocked direct-payment closure for every
    real Home Services job."""
    data = await _proof_svc.acknowledge_handover(db, uuid.UUID(str(user.user_id)), job_id)
    return ok(data, _rid(r), "customer_acknowledge_handover")
