"""FINAL-L5-05J — Canonical Usage Credit admin router.

POST /v1/admin/usage-credits/{tenant_id}/adjustments is the one canonical
mutation endpoint for manual Usage Credit adjustments. Every other
Admin wallet-adjustment implementation found in FINAL-L5-05I is either
deprecated (410) or retained as a thin read-only/adapter surface — see
docs/final-l5-05/FINAL_L5_05J_ADMIN_ADJUSTMENT_MIGRATION.md.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import P, require_permission
from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.engines.tenant_engine.models import Tenant
from app.engines.usage_credits.service import UsageCreditService, VALID_REASON_CODES
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, Meta, ok

router = APIRouter(prefix="/v1/admin/usage-credits", tags=["Usage Credits"])
ENGINE_ID = "usage_credits"


def _meta(r: Request) -> Meta:
    return Meta(request_id=getattr(r.state, "request_id", "—"), engine_id=ENGINE_ID)


async def _require_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    exists = (await db.execute(select(Tenant.id).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if not exists:
        raise ServiceOSException("TENANT_NOT_FOUND", f"Tenant {tenant_id} not found.", status_code=404)


class UsageCreditAdjustmentRequest(BaseModel):
    direction: str = Field(..., description="'credit' or 'debit'")
    amount: Decimal = Field(..., gt=0)
    reason_code: str
    reason: str
    idempotency_key: str


@router.get("/{tenant_id}/balance", summary="Canonical Usage Credit balance", response_model=ApiResponse[dict])
async def get_balance(tenant_id: uuid.UUID, r: Request,
                       db: AsyncSession = Depends(get_db),
                       u: UserContext = Depends(require_permission(P.FINANCE_USAGE_CREDITS_READ))
                       ) -> ApiResponse[dict]:
    await _require_tenant(db, tenant_id)
    svc = UsageCreditService(db, actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
    return ok(await svc.get_balance(tenant_id), _meta(r).request_id, ENGINE_ID)


@router.get("/{tenant_id}/ledger", summary="Canonical Usage Credit Ledger", response_model=ApiResponse[dict])
async def get_ledger(tenant_id: uuid.UUID, r: Request,
                      limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                      db: AsyncSession = Depends(get_db),
                      u: UserContext = Depends(require_permission(P.FINANCE_USAGE_CREDITS_LEDGER_READ))
                      ) -> ApiResponse[dict]:
    await _require_tenant(db, tenant_id)
    svc = UsageCreditService(db, actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
    return ok(await svc.get_ledger(tenant_id, limit, offset), _meta(r).request_id, ENGINE_ID)


@router.get("/{tenant_id}/threshold", summary="Usage Credit threshold check", response_model=ApiResponse[dict])
async def get_threshold(tenant_id: uuid.UUID, r: Request,
                         db: AsyncSession = Depends(get_db),
                         u: UserContext = Depends(require_permission(P.FINANCE_USAGE_CREDITS_READ))
                         ) -> ApiResponse[dict]:
    await _require_tenant(db, tenant_id)
    svc = UsageCreditService(db, actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
    return ok(await svc.check_threshold(tenant_id), _meta(r).request_id, ENGINE_ID)


@router.get("/reason-codes", summary="Allowed Usage Credit adjustment reason codes", response_model=ApiResponse[dict])
async def get_reason_codes(r: Request,
                            u: UserContext = Depends(require_permission(P.FINANCE_USAGE_CREDITS_READ))
                            ) -> ApiResponse[dict]:
    return ok({"reason_codes": sorted(VALID_REASON_CODES)}, _meta(r).request_id, ENGINE_ID)


@router.post("/{tenant_id}/adjustments", summary="Canonical Usage Credit adjustment", response_model=ApiResponse[dict])
async def create_adjustment(tenant_id: uuid.UUID, body: UsageCreditAdjustmentRequest, r: Request,
                             db: AsyncSession = Depends(get_db),
                             u: UserContext = Depends(require_permission(P.FINANCE_USAGE_CREDITS_ADJUST))
                             ) -> ApiResponse[dict]:
    await _require_tenant(db, tenant_id)
    svc = UsageCreditService(
        db, actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role,
        request_id=_meta(r).request_id, actor_ip=r.client.host if r.client else None,
    )
    result = await svc.adjust_credit(
        tenant_id=tenant_id, direction=body.direction, amount=body.amount,
        reason_code=body.reason_code, reason=body.reason, idempotency_key=body.idempotency_key,
    )
    await db.commit()
    return ok(result, _meta(r).request_id, ENGINE_ID)
