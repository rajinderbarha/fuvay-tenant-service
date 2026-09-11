"""VERTICAL-MONETIZATION: customer-facing fee disclosure + payment
collection. The customer never supplies an amount — every value here is
server-resolved from a real charge row created by the canonical booking/
quote-approval flow (see charge_service.py)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.vertical_monetization.charge_service import create_payment_order_for_charge
from app.engines.vertical_monetization.models import CustomerPlatformFeeCharge

router = APIRouter(prefix="/v1/customer/monetization", tags=["Platform Charges"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/charges/{charge_id}", response_model=ApiResponse)
async def get_charge(
    charge_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Full breakdown for the payment/receipt screen: service amount, who
    receives it, Fuvay fee, total, refundability, collection stage."""
    charge = await db.get(CustomerPlatformFeeCharge, charge_id)
    if not charge:
        from app.exceptions import NotFoundException
        raise NotFoundException("Charge", str(charge_id))
    if charge.customer_id and str(charge.customer_id) != user.user_id:
        from app.exceptions import ServiceOSException
        raise ServiceOSException("PERMISSION_DENIED", "This charge does not belong to you.", status_code=403)
    d = charge.to_dict()
    d["breakdown_display"] = {
        "service_amount_paid_to_provider": str(charge.service_subtotal_minor / 100),
        "serviceos_platform_fee_paid_to_serviceos": str(charge.fee_amount_minor / 100),
        "total_customer_obligation": str(charge.total_payable_minor / 100),
    }
    return ok(d, _rid(r), "vertical_monetization")


@router.post("/charges/{charge_id}/pay", response_model=ApiResponse)
async def pay_charge(
    charge_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    order = await create_payment_order_for_charge(db, charge_id=charge_id, customer_id=uuid.UUID(user.user_id))
    return ok(order, _rid(r), "vertical_monetization")
