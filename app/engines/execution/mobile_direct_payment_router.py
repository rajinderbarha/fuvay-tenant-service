"""Technician Mobile App Phase O — Direct Payment Confirmation routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.execution.mobile_direct_payment_service import MobileDirectPaymentService

router = APIRouter(prefix="/v1/staff/service-jobs", tags=["Technician Mobile Direct Payment"])
_svc = MobileDirectPaymentService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _require_tenant(user: UserContext) -> None:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No active tenant context.", status_code=403)


@router.get("/{job_id}/mobile-direct-payment")
async def get_mobile_direct_payment(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.get_detail(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    await db.commit()
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-direct-payment/declare")
async def declare_mobile_direct_payment(job_id: uuid.UUID, body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.declare_payment(
        db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id,
        amount=body["amount"], method=body["method"], reference_id=body.get("reference_id"),
        note=body.get("note"), evidence_media_id=body.get("evidence_media_id"), request_id=_rid(request),
    )
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-direct-payment/remind")
async def remind_mobile_direct_payment(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.remind_customer(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, _rid(request))
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-direct-payment/finalize")
async def finalize_mobile_direct_payment(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.finalize_job(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, _rid(request))
    return ok(data, _rid(request), "execution")
