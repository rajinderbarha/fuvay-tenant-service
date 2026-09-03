"""Platform complaint-policy configuration.

Customer and provider own complaint, rework, refund, and settlement cases.
Platform admins configure only the SLA windows and automatic tenant penalty.
"""

from decimal import Decimal
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.complaints.complaint_service import ComplaintService
from app.schemas.base import ok


admin_cpolicy_router = APIRouter(
    prefix="/v1/admin/complaint-policies",
    tags=["admin-complaint-policies"],
)

_complaint = ComplaintService()


def _rid(request: Request | None) -> str:
    return getattr(request.state, "request_id", "-") if request else "-"


class PolicyIn(BaseModel):
    policy_key: Optional[str] = None
    policy_name: Optional[str] = None
    tenant_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    complaint_window_hours: Optional[int] = None
    allow_duplicate_open_complaints: Optional[bool] = None
    allow_rework: Optional[bool] = None
    allow_refund_request: Optional[bool] = None
    require_provider_response: Optional[bool] = None
    default_provider_response_hours: Optional[int] = None
    default_resolution_hours: Optional[int] = None
    provider_sla_breach_penalty: Optional[Decimal] = None
    is_active: Optional[bool] = None

    @field_validator("provider_sla_breach_penalty")
    @classmethod
    def _penalty_range(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not (Decimal("0") <= value <= Decimal("100000")):
            raise ValueError(
                "provider_sla_breach_penalty must be between 0 and 100000"
            )
        return value


@admin_cpolicy_router.get("")
async def list_policies(
    request: Request = None,
    _user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    policies = await _complaint.list_policies(db)
    return ok(
        [policy.to_dict() for policy in policies],
        _rid(request),
        "admin.cpolicies.list",
    )


@admin_cpolicy_router.post("")
async def create_policy(
    body: PolicyIn,
    request: Request = None,
    _user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    policy = await _complaint.create_policy(db, body.model_dump(exclude_none=True))
    return ok(policy.to_dict(), _rid(request), "admin.cpolicy.created")


@admin_cpolicy_router.put("/{policy_id}")
async def update_policy(
    policy_id: uuid.UUID,
    body: PolicyIn,
    request: Request = None,
    _user: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    policy = await _complaint.update_policy(
        db,
        policy_id,
        body.model_dump(exclude_none=True),
    )
    return ok(policy.to_dict(), _rid(request), "admin.cpolicy.updated")
