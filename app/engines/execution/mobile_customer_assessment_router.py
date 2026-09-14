"""Assigned-technician-only private customer behavior feedback."""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, require_staff_or_technician_only
from app.dependencies.db import get_db
from app.engines.execution.mobile_customer_assessment_service import MobileCustomerAssessmentService
from app.exceptions import ServiceOSException
from app.schemas.base import ok


router = APIRouter(prefix="/v1/staff/service-jobs", tags=["Technician Mobile Customer Assessment"])
_service = MobileCustomerAssessmentService()


class CustomerAssessmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    behavior_code: Literal["respectful", "neutral", "difficult", "unsafe"]
    reason_code: Literal["rude_language", "access_denied", "safety_concern", "other"] | None = None
    note: str | None = Field(default=None, max_length=500)


def _identity(user: UserContext) -> tuple[uuid.UUID, uuid.UUID]:
    if not user.tenant_id:
        raise ServiceOSException("TENANT_CONTEXT_MISSING", "No active tenant context.", status_code=403)
    return uuid.UUID(user.user_id), uuid.UUID(user.tenant_id)


@router.get("/{job_id}/customer-assessment")
async def get_customer_assessment(
    job_id: uuid.UUID, request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    user_id, tenant_id = _identity(user)
    data = await _service.get_status(db, user_id, tenant_id, job_id)
    return ok(data, getattr(request.state, "request_id", "-"), "execution")


@router.post("/{job_id}/customer-assessment")
async def submit_customer_assessment(
    job_id: uuid.UUID, body: CustomerAssessmentBody, request: Request,
    user: UserContext = Depends(require_staff_or_technician_only),
    db: AsyncSession = Depends(get_db),
):
    user_id, tenant_id = _identity(user)
    data = await _service.submit(
        db, user_id, tenant_id, job_id, body.behavior_code,
        body.reason_code, body.note.strip() if body.note else None,
    )
    return ok(data, getattr(request.state, "request_id", "-"), "execution")
