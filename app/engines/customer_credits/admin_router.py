"""Admin Dispute Settlement + Customer Credits router — /v1/admin/finance/settlements and credits."""
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user
from app.engines.customer_credits.service import (
    DisputeSettlementService, CustomerCreditService)
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/finance", tags=["admin-finance-settlements"])
ENGINE_ID = "customer_credits"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(db, u, req_id=""):
    return DisputeSettlementService(db, u.user_id, u.role, req_id)


def _csvc(db, u, req_id=""):
    return CustomerCreditService(db, u.user_id, u.role, req_id)


# ── Settlement endpoints ───────────────────────────────────────────────────────

@router.get("/settlements/summary")
async def get_settlement_summary(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_SETTLEMENTS_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).get_settlement_summary(), _rid(r), ENGINE_ID)


@router.get("/settlements")
async def list_settlements(
    r: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    tenant_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_SETTLEMENTS_READ)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u).list_settlements(
        page=page, limit=limit, status=status,
        tenant_id=tenant_id, customer_id=customer_id), _rid(r), ENGINE_ID)


@router.get("/settlements/{settlement_id}")
async def get_settlement(
    r: Request,
    settlement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_SETTLEMENTS_READ)),
) -> ApiResponse[dict]:
    s = await _svc(db, u)._get_settlement(settlement_id)
    return ok(s.to_dict(), _rid(r), ENGINE_ID)


@router.post("/disputes/{dispute_id}/settlements", status_code=201)
async def create_settlement(
    r: Request,
    dispute_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_SETTLEMENTS_CREATE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u, _rid(r)).create_settlement(dispute_id, body), _rid(r), ENGINE_ID)


@router.post("/disputes/{dispute_id}/settlements/preview")
async def preview_deduction(
    r: Request,
    dispute_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_SETTLEMENTS_READ)),
) -> ApiResponse[dict]:
    tenant_id = uuid.UUID(str(body["tenant_id"]))
    amount = Decimal(str(body.get("settlement_amount", 0)))
    strategy = body.get("deduction_strategy", "tenant_wallet_then_security_deposit")
    return ok(await _svc(db, u).preview_deduction(tenant_id, amount, strategy), _rid(r), ENGINE_ID)


@router.post("/settlements/{settlement_id}/approve")
async def approve_settlement(
    r: Request,
    settlement_id: uuid.UUID,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_SETTLEMENTS_APPROVE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u, _rid(r)).approve_settlement(settlement_id), _rid(r), ENGINE_ID)


@router.post("/settlements/{settlement_id}/execute")
async def execute_settlement(
    r: Request,
    settlement_id: uuid.UUID,
    body: dict = {},
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_SETTLEMENTS_EXECUTE)),
) -> ApiResponse[dict]:
    return ok(await _svc(db, u, _rid(r)).execute_settlement(settlement_id), _rid(r), ENGINE_ID)


@router.post("/settlements/{settlement_id}/cancel")
async def cancel_settlement(
    r: Request,
    settlement_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_SETTLEMENTS_CANCEL)),
) -> ApiResponse[dict]:
    reason = body.get("reason", "Cancelled by admin")
    return ok(await _svc(db, u, _rid(r)).cancel_settlement(settlement_id, reason), _rid(r), ENGINE_ID)


# ── Customer Credit endpoints ──────────────────────────────────────────────────

@router.get("/credits/summary")
async def get_credit_summary(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_CREDITS_READ)),
) -> ApiResponse[dict]:
    return ok(await _csvc(db, u).get_credit_summary(), _rid(r), ENGINE_ID)


@router.get("/credits")
async def list_credits(
    r: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_CREDITS_READ)),
) -> ApiResponse[dict]:
    return ok(await _csvc(db, u).list_credits(
        customer_id=customer_id, status=status, page=page, limit=limit), _rid(r), ENGINE_ID)


@router.get("/credits/{credit_id}")
async def get_credit(
    r: Request,
    credit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_CREDITS_READ)),
) -> ApiResponse[dict]:
    return ok(await _csvc(db, u).get_credit(credit_id), _rid(r), ENGINE_ID)


@router.post("/customers/{customer_id}/credits", status_code=201)
async def issue_manual_credit(
    r: Request,
    customer_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_CREDITS_CREATE)),
) -> ApiResponse[dict]:
    return ok(await _csvc(db, u, _rid(r)).issue_credit_manual(customer_id, body), _rid(r), ENGINE_ID)


@router.post("/credits/{credit_id}/cancel")
async def cancel_credit(
    r: Request,
    credit_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_CREDITS_CANCEL)),
) -> ApiResponse[dict]:
    return ok(await _csvc(db, u, _rid(r)).cancel_credit(
        credit_id, body.get("reason", "Cancelled by admin")), _rid(r), ENGINE_ID)


@router.post("/credits/{credit_id}/extend")
async def extend_credit(
    r: Request,
    credit_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_CREDITS_EXTEND)),
) -> ApiResponse[dict]:
    new_expiry = datetime.fromisoformat(body["new_expiry"])
    return ok(await _csvc(db, u, _rid(r)).extend_credit_expiry(credit_id, new_expiry), _rid(r), ENGINE_ID)


# ── Tenant Penalty endpoints ───────────────────────────────────────────────────

@router.get("/penalties/summary")
async def get_penalty_summary(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_PENALTIES_READ)),
) -> ApiResponse[dict]:
    return ok(await _csvc(db, u).get_penalty_summary(), _rid(r), ENGINE_ID)


@router.get("/penalties")
async def list_penalties(
    r: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_PENALTIES_READ)),
) -> ApiResponse[dict]:
    return ok(await _csvc(db, u).list_penalties(
        tenant_id=tenant_id, status=status, page=page, limit=limit), _rid(r), ENGINE_ID)


# ── Finance Vertical Config ────────────────────────────────────────────────────

@router.get("/vertical-config/{vertical_type}")
async def get_vertical_config(
    r: Request,
    vertical_type: str,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_permission(P.FINANCE_READ)),
) -> ApiResponse[dict]:
    return ok(await _csvc(db, u).get_vertical_config(vertical_type), _rid(r), ENGINE_ID)
