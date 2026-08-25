"""LEVEL-5 REMEDIATION (2026-08-01, Phase 10) — Customer Home aggregation endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.customer_home.service import CustomerHomeService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/customer/home", tags=["Customer Home"])
ENGINE_ID = "customer_home"


class CampaignEventBody(BaseModel):
    event_type: str = Field(pattern="^(delivered|opened|clicked)$")
    placement: str | None = Field(default=None, max_length=80)
    session_id: str | None = Field(default=None, max_length=120)


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


@router.post(
    "/campaigns/{campaign_id}/events",
    response_model=ApiResponse[dict],
    summary="Record a customer Home campaign delivery or interaction",
)
async def record_campaign_event(
    campaign_id: str,
    body: CampaignEventBody,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Records only customer-safe delivery/open/click events.

    The campaign must still be a customer in-app campaign. This endpoint does
    not accept arbitrary conversion records; conversions remain tied to the
    existing booking/payment attribution workflow.
    """
    import uuid as _uuid
    from sqlalchemy import select
    from app.engines.marketing_automation.constants import (
        AUDIENCE_CUSTOMERS,
        CHANNEL_IN_APP,
    )
    from app.engines.marketing_automation.models import (
        MarketingCampaign,
        MarketingCampaignEvent,
        MarketingCampaignMessage,
    )

    cid = _uuid.UUID(campaign_id)
    eligible = (await db.execute(
        select(MarketingCampaign.id)
        .join(
            MarketingCampaignMessage,
            MarketingCampaignMessage.campaign_id == MarketingCampaign.id,
        )
        .where(
            MarketingCampaign.id == cid,
            MarketingCampaign.target_audience == AUDIENCE_CUSTOMERS,
            MarketingCampaignMessage.channel == CHANNEL_IN_APP,
            MarketingCampaignMessage.is_active.is_(True),
        )
        .limit(1)
    )).scalar_one_or_none()
    if eligible is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Campaign is not available.")

    db.add(MarketingCampaignEvent(
        campaign_id=cid,
        recipient_user_id=_uuid.UUID(u.user_id),
        event_type=body.event_type,
        camp_metadata={
            "surface": "customer_home",
            "placement": body.placement,
            "session_id": body.session_id,
        },
    ))
    await db.commit()
    return ok({"recorded": True}, _rid(r), ENGINE_ID)
