"""LEVEL-5 REMEDIATION (2026-08-01, Phase 10) — Customer Home aggregation endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.customer_home.service import CustomerHomeService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/customer/home", tags=["Customer Home"])
ENGINE_ID = "customer_home"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("", response_model=ApiResponse[dict], summary="Get the composed customer Home screen payload")
async def get_home(
    r: Request,
    zipcode: str | None = Query(None, description="Overrides the customer's default address ZIP for this request"),
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Composes existing engines' own read paths into a single Home payload —
    does not duplicate serviceability/catalog/booking business logic (see
    CustomerHomeService docstring). Requires authentication since it returns
    customer-specific data (address, active booking, notification count).
    """
    import uuid as _uuid
    svc = CustomerHomeService(db=db, request_id=_rid(r))
    data = await svc.get_home(customer_id=_uuid.UUID(u.user_id), zipcode=zipcode)
    return ok(data, _rid(r), ENGINE_ID)
