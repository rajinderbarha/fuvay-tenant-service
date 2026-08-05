"""TENANT-HS-DIRECT-PAYMENTS-01 — tenant + customer API surface.

Tenant routes are gated on BOTH the tenant's Home Services enrollment being
active (require_tenant_vertical_active) and the specific direct_payments.*
permission. There is deliberately NO payout, settlement, or
confirm-on-behalf-of-the-customer route here.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, permission_checker
from app.dependencies.auth import UserContext, get_current_user
from app.dependencies.db import get_db
from app.dependencies.vertical_guard import require_tenant_vertical_active
from app.engines.invoice_payment.direct_payments_constants import (
    BANNER_TEXT, FOOTER_DISCLAIMER, POLICY_BULLETS, SENSITIVE_EVIDENCE_WARNING,
)
from app.engines.invoice_payment.direct_payments_service import DirectPaymentsService
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/tenant/home-services", tags=["Home Services Direct Payments"])
customer_router = APIRouter(prefix="/v1/customer/direct-payments",
                            tags=["Home Services Direct Payments (Customer)"])

_RID = lambda r: getattr(r.state, "request_id", "—")

_HS_ACTIVE = require_tenant_vertical_active("home_services")


def _assert_perm(user: UserContext, permission: str) -> None:
    if not permission_checker.has(role=user.role, permission=permission,
                                  overrides=getattr(user, "permission_overrides", None)):
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Permission '{permission}' required.",
            status_code=403,
            resolution="Ask your tenant owner to grant this permission.",
            context={"required": permission, "role": user.role},
        )


def _svc(user: UserContext, db: AsyncSession, r: Request) -> DirectPaymentsService:
    return DirectPaymentsService(db, uuid.UUID(str(user.tenant_id)), _RID(r))


# ── Queue ────────────────────────────────────────────────────────────────────

@router.get("/direct-payments", response_model=ApiResponse,
            summary="Direct-payment confirmation queue + KPI summary")
async def list_direct_payments(
    r: Request,
    status: str | None = Query(None, description="needs_action|all|awaiting_provider|awaiting_customer|confirmed|mismatched|disputed"),
    method: str | None = Query(None),
    service_id: str | None = Query(None),
    job_type_id: str | None = Query(None),
    technician_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    user: UserContext = Depends(_HS_ACTIVE),
    db: AsyncSession = Depends(get_db),
):
    _assert_perm(user, P.DIRECT_PAYMENTS_READ)
    data = await _svc(user, db, r).list_queue(
        status=status, method=method, service_id=service_id, job_type_id=job_type_id,
        technician_id=technician_id, date_from=date_from, date_to=date_to,
        search=search, page=page, limit=limit,
    )
    data["policy"] = POLICY_BULLETS
    data["footer_disclaimer"] = FOOTER_DISCLAIMER
    data["banner"]["text"] = BANNER_TEXT
    return ok(data, _RID(r), "direct_payments")


@router.get("/direct-payments/export", response_model=ApiResponse,
            summary="Export the direct-payment queue (tenant-scoped, privacy-safe)")
async def export_direct_payments(
    r: Request,
    status: str | None = Query(None),
    method: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    search: str | None = Query(None),
    user: UserContext = Depends(_HS_ACTIVE),
    db: AsyncSession = Depends(get_db),
):
    _assert_perm(user, P.DIRECT_PAYMENTS_EXPORT)
    data = await _svc(user, db, r).export_rows(
        status=status, method=method, date_from=date_from, date_to=date_to, search=search,
    )
    return ok(data, _RID(r), "direct_payments")


@router.get("/direct-payments/{payment_id}", response_model=ApiResponse,
            summary="Direct-payment record detail + reconciliation workflow")
async def get_direct_payment(
    payment_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(_HS_ACTIVE),
    db: AsyncSession = Depends(get_db),
):
    _assert_perm(user, P.DIRECT_PAYMENTS_READ)
    data = await _svc(user, db, r).get_detail(payment_id)
    data["footer_disclaimer"] = FOOTER_DISCLAIMER
    data["banner_text"] = BANNER_TEXT
    return ok(data, _RID(r), "direct_payments")


# ── Provider declaration ─────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/direct-payment/preflight", response_model=ApiResponse,
            summary="Expected payable, approved estimate and visit-fee treatment before declaring")
async def declaration_preflight(
    job_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(_HS_ACTIVE),
    db: AsyncSession = Depends(get_db),
):
    _assert_perm(user, P.DIRECT_PAYMENTS_DECLARE)
    data = await _svc(user, db, r).declaration_preflight(job_id)
    data["sensitive_data_warning"] = SENSITIVE_EVIDENCE_WARNING
    return ok(data, _RID(r), "direct_payments")


@router.post("/jobs/{job_id}/direct-payment/declaration", response_model=ApiResponse,
             summary="Record the provider's declaration of a direct customer payment")
async def create_declaration(
    job_id: uuid.UUID,
    r: Request,
    payload: dict = Body(...),
    user: UserContext = Depends(_HS_ACTIVE),
    db: AsyncSession = Depends(get_db),
):
    _assert_perm(user, P.DIRECT_PAYMENTS_DECLARE)
    if payload.get("evidence_media_id"):
        _assert_perm(user, P.DIRECT_PAYMENTS_UPLOAD_EVIDENCE)
    received_at = payload.get("received_at")
    data = await _svc(user, db, r).declare(
        job_id=job_id,
        # The client may NOT supply expected_amount -- it is resolved
        # server-side and any such key is ignored on purpose.
        amount=payload.get("amount"),
        method=payload.get("method", ""),
        actor_user_id=user.user_id,
        received_at=datetime.fromisoformat(received_at) if received_at else None,
        reference_id=payload.get("reference_id"),
        note=payload.get("note"),
        evidence_media_id=payload.get("evidence_media_id"),
        evidence_type=payload.get("evidence_type"),
        difference_reason=payload.get("difference_reason"),
    )
    return ok(data, _RID(r), "direct_payments")


@router.patch("/direct-payments/{payment_id}/declaration", response_model=ApiResponse,
              summary="Correct a declaration before customer confirmation (versioned)")
async def correct_declaration(
    payment_id: uuid.UUID,
    r: Request,
    payload: dict = Body(...),
    user: UserContext = Depends(_HS_ACTIVE),
    db: AsyncSession = Depends(get_db),
):
    _assert_perm(user, P.DIRECT_PAYMENTS_CORRECT)
    if payload.get("evidence_media_id"):
        _assert_perm(user, P.DIRECT_PAYMENTS_UPLOAD_EVIDENCE)
    received_at = payload.get("received_at")
    data = await _svc(user, db, r).correct_declaration(
        payment_id=payment_id,
        actor_user_id=user.user_id,
        expected_version=payload.get("expected_version"),
        amount=payload.get("amount"),
        method=payload.get("method"),
        reference_id=payload.get("reference_id"),
        note=payload.get("note"),
        received_at=datetime.fromisoformat(received_at) if received_at else None,
        evidence_media_id=payload.get("evidence_media_id"),
        evidence_type=payload.get("evidence_type"),
        correction_reason=payload.get("correction_reason"),
        difference_reason=payload.get("difference_reason"),
    )
    return ok(data, _RID(r), "direct_payments")


# ── Reminder / dispute ───────────────────────────────────────────────────────

@router.post("/direct-payments/{payment_id}/remind-customer", response_model=ApiResponse,
             summary="Send a real confirmation reminder through ServiceOS notifications")
async def remind_customer(
    payment_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(_HS_ACTIVE),
    db: AsyncSession = Depends(get_db),
):
    _assert_perm(user, P.DIRECT_PAYMENTS_REMIND_CUSTOMER)
    data = await _svc(user, db, r).remind_customer(
        payment_id=payment_id, actor_user_id=user.user_id)
    return ok(data, _RID(r), "direct_payments")


@router.post("/direct-payments/{payment_id}/open-dispute", response_model=ApiResponse,
             summary="Open a payment dispute in the Complaints & Resolution Center")
async def open_dispute(
    payment_id: uuid.UUID,
    r: Request,
    payload: dict = Body(default={}),
    user: UserContext = Depends(_HS_ACTIVE),
    db: AsyncSession = Depends(get_db),
):
    _assert_perm(user, P.DIRECT_PAYMENTS_OPEN_DISPUTE)
    data = await _svc(user, db, r).open_dispute(
        payment_id=payment_id, actor_user_id=user.user_id,
        description=payload.get("description")
        or "The customer reports a different amount for this direct payment.",
    )
    return ok(data, _RID(r), "direct_payments")


# ── Customer side ────────────────────────────────────────────────────────────
# Authenticated + ownership-checked. No unsecured public-token confirmation
# path exists.

@customer_router.get("", response_model=ApiResponse,
                     summary="My direct payments awaiting confirmation")
async def customer_list(
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = DirectPaymentsService(db, uuid.UUID(int=0), _RID(r))
    data = await svc.customer_pending_list(user.user_id)
    return ok(data, _RID(r), "direct_payments")


@customer_router.post("/{payment_id}/confirm", response_model=ApiResponse,
                      summary="Confirm the direct payment I made to the provider")
async def customer_confirm(
    payment_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = DirectPaymentsService(db, uuid.UUID(int=0), _RID(r))
    data = await svc.customer_confirm(payment_id=payment_id, customer_id=user.user_id)
    return ok(data, _RID(r), "direct_payments")


@customer_router.post("/{payment_id}/report-mismatch", response_model=ApiResponse,
                      summary="Report a different amount / method / not paid")
async def customer_report_mismatch(
    payment_id: uuid.UUID,
    r: Request,
    payload: dict = Body(...),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = DirectPaymentsService(db, uuid.UUID(int=0), _RID(r))
    data = await svc.customer_report_mismatch(
        payment_id=payment_id, customer_id=user.user_id,
        action=payload.get("action", ""),
        reported_amount=payload.get("reported_amount"),
        reported_method=payload.get("reported_method"),
        note=payload.get("note"),
    )
    return ok(data, _RID(r), "direct_payments")


@customer_router.post("/{payment_id}/open-dispute", response_model=ApiResponse,
                      summary="Open a payment dispute (Complaints & Resolution Center)")
async def customer_open_dispute(
    payment_id: uuid.UUID,
    r: Request,
    payload: dict = Body(default={}),
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.invoice_payment.models import ServicePaymentRecord
    from sqlalchemy import select as _select
    pay = (await db.execute(_select(ServicePaymentRecord).where(
        ServicePaymentRecord.id == payment_id))).scalars().first()
    if pay is None or str(pay.customer_id) != str(user.user_id):
        raise ServiceOSException(
            error_code="DIRECT_PAYMENT_NOT_FOUND",
            detail="Direct payment record not found.", status_code=404)
    svc = DirectPaymentsService(db, pay.tenant_id, _RID(r))
    data = await svc.open_dispute(
        payment_id=payment_id, actor_user_id=user.user_id, actor_type="customer",
        description=payload.get("description")
        or "I did not pay the amount recorded by the provider.",
    )
    return ok(data, _RID(r), "direct_payments")
