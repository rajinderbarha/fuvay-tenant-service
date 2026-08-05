"""Technician Mobile App Phase L — Estimate Builder routes.

Thin technician-authorized wrapper over the canonical
`ServiceJobQuoteService` -- see mobile_estimate_service.py docstring for why
this exists instead of reusing quote_checklist's own staff_router directly
(that router's mutations use `require_owner_or_office_staff_mutation`,
which explicitly excludes technicians).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.execution.mobile_estimate_service import MobileEstimateService

router = APIRouter(prefix="/v1/staff/service-jobs", tags=["Technician Mobile Estimate"])
_svc = MobileEstimateService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _require_tenant(user: UserContext) -> None:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No active tenant context.", status_code=403)


@router.get("/{job_id}/mobile-estimate")
async def get_mobile_estimate(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.get_detail(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    await db.commit()
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-estimate/create")
async def create_mobile_estimate(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.create_estimate(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, _rid(request))
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-estimate/{quote_id}/revise")
async def revise_mobile_estimate(job_id: uuid.UUID, quote_id: str, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.create_revision(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, quote_id, _rid(request))
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-estimate/{quote_id}/items")
async def add_mobile_estimate_item(job_id: uuid.UUID, quote_id: str, body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.add_item(
        db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, quote_id,
        item_type=body["item_type"], item_name=body["item_name"], item_description=body.get("item_description"),
        quantity=float(body.get("quantity", 1)), unit_price=float(body.get("unit_price", 0)),
        is_customer_visible=bool(body.get("is_customer_visible", True)), request_id=_rid(request),
    )
    return ok(data, _rid(request), "execution")


@router.put("/{job_id}/mobile-estimate/{quote_id}/items/{item_id}")
async def update_mobile_estimate_item(job_id: uuid.UUID, quote_id: str, item_id: str, body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.update_item(
        db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, quote_id, item_id,
        item_name=body.get("item_name"), item_description=body.get("item_description"),
        quantity=body.get("quantity"), unit_price=body.get("unit_price"),
        is_customer_visible=body.get("is_customer_visible"), request_id=_rid(request),
    )
    return ok(data, _rid(request), "execution")


@router.delete("/{job_id}/mobile-estimate/{quote_id}/items/{item_id}")
async def remove_mobile_estimate_item(job_id: uuid.UUID, quote_id: str, item_id: str, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.remove_item(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, quote_id, item_id, _rid(request))
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-estimate/{quote_id}/send")
async def send_mobile_estimate(job_id: uuid.UUID, quote_id: str, body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.send_for_approval(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, quote_id, body.get("customer_notes"), _rid(request))
    return ok(data, _rid(request), "execution")
