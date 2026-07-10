"""Customer-facing credit endpoints — /v1/me/credits."""
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.auth import require_customer
from app.engines.customer_credits.service import CustomerCreditService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/me/credits", tags=["customer-credits"])
ENGINE_ID = "customer_credits"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("")
async def list_my_credits(
    r: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    u=Depends(require_customer),
) -> ApiResponse[dict]:
    svc = CustomerCreditService(db, u.user_id, "customer")
    return ok(await svc.list_credits(customer_id=u.user_id, status=status,
                                      page=page, limit=limit), _rid(r), ENGINE_ID)


@router.get("/summary")
async def get_my_credit_summary(
    r: Request,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_customer),
) -> ApiResponse[dict]:
    svc = CustomerCreditService(db, u.user_id, "customer")
    return ok(await svc.get_credit_summary(customer_id=u.user_id), _rid(r), ENGINE_ID)


@router.get("/{credit_id}")
async def get_my_credit(
    r: Request,
    credit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_customer),
) -> ApiResponse[dict]:
    svc = CustomerCreditService(db, u.user_id, "customer")
    return ok(await svc.get_credit(credit_id, customer_id=u.user_id), _rid(r), ENGINE_ID)


@router.post("/preview-apply")
async def preview_apply_credit(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_customer),
) -> ApiResponse[dict]:
    svc = CustomerCreditService(db, u.user_id, "customer")
    booking_amount = Decimal(str(body.get("booking_amount", 0)))
    credit_apply = Decimal(str(body.get("credit_amount_to_apply", 0)))
    return ok(await svc.get_booking_credit_preview(u.user_id, booking_amount, credit_apply),
              _rid(r), ENGINE_ID)


@router.post("/apply")
async def apply_credit_to_booking(
    r: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    u=Depends(require_customer),
) -> ApiResponse[dict]:
    svc = CustomerCreditService(db, u.user_id, "customer")
    booking_id = uuid.UUID(str(body["booking_id"]))
    credit_apply = Decimal(str(body.get("credit_amount_to_apply", 0)))
    # booking_amount is intentionally NOT taken from the request body — the real
    # Booking.quoted_price is the sole source of truth (see service docstring).
    return ok(await svc.apply_credit_to_booking(u.user_id, booking_id, credit_apply),
              _rid(r), ENGINE_ID)
