"""LEVEL-5 REMEDIATION (2026-08-01, Phase 11) — Customer-facing campaign read."""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.customer_campaigns.service import CampaignService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/customer/campaigns", tags=["Customer Campaigns"])
ENGINE_ID = "customer_campaigns"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("", response_model=ApiResponse[dict], summary="List active campaigns/banners for the customer")
async def list_active_campaigns(
    r: Request,
    zipcode: str | None = Query(None),
    vertical_key: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CampaignService(db=db)
    items = await svc.list_active_for_customer(
        zipcode=zipcode, vertical_key=vertical_key, category_id=category_id,
    )
    return ok({"items": items, "total": len(items)}, _rid(r), ENGINE_ID)
