"""Technician Mobile App Phase N — Completion Proof & Customer Handover routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_staff_or_technician_only, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.execution.mobile_completion_proof_service import MobileCompletionProofService

router = APIRouter(prefix="/v1/staff/service-jobs", tags=["Technician Mobile Completion Proof"])
_svc = MobileCompletionProofService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _require_tenant(user: UserContext) -> None:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No active tenant context.", status_code=403)


@router.get("/{job_id}/mobile-completion-proof")
async def get_mobile_completion_proof(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.get_detail(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    await db.commit()
    return ok(data, _rid(request), "execution")


@router.put("/{job_id}/mobile-completion-proof/draft")
async def save_mobile_completion_proof_draft(job_id: uuid.UUID, body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.save_draft(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, body.get("resolution_summary"), body.get("final_service_notes"))
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-completion-proof/evidence")
async def add_mobile_completion_evidence(job_id: uuid.UUID, body: dict, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.add_evidence(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, body["category"], body["file_id"])
    return ok(data, _rid(request), "execution")


@router.delete("/{job_id}/mobile-completion-proof/evidence/{category}/{file_id}")
async def remove_mobile_completion_evidence(job_id: uuid.UUID, category: str, file_id: str, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.remove_evidence(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id, category, file_id)
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-completion-proof/submit")
async def submit_mobile_completion_proof(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.submit(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-completion-proof/request-handover")
async def request_mobile_handover(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.request_handover(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-completion-proof/send-reminder")
async def send_mobile_handover_reminder(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.send_reminder(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    return ok(data, _rid(request), "execution")


@router.post("/{job_id}/mobile-completion-proof/customer-unavailable")
async def mark_mobile_customer_unavailable(job_id: uuid.UUID, request: Request, user: UserContext = Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    _require_tenant(user)
    data = await _svc.mark_customer_unavailable(db, uuid.UUID(user.user_id), uuid.UUID(user.tenant_id), job_id)
    return ok(data, _rid(request), "execution")
