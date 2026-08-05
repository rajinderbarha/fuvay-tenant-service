"""LEVEL-5 REMEDIATION (2026-08-01, Phase 11) — Admin campaign/banner CRUD."""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, require_super_admin, UserContext
from app.dependencies.db import get_db
from app.engines.customer_campaigns.service import CampaignService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/customer-campaigns", tags=["Customer Campaigns (Admin)"])
ENGINE_ID = "customer_campaigns"


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("", response_model=ApiResponse[dict], summary="List all campaigns (admin)")
async def list_campaigns(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = CampaignService(db=db)
    items = await svc.list_all_admin()
    return ok({"items": items, "total": len(items)}, _rid(r), ENGINE_ID)


@router.post("", response_model=ApiResponse[dict], summary="Create a campaign")
async def create_campaign(
    body: dict,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = CampaignService(db=db)
    data = await svc.create_campaign(body, actor_id=uuid.UUID(u.user_id))
    return ok(data, _rid(r), ENGINE_ID)


@router.put("/{campaign_id}", response_model=ApiResponse[dict], summary="Update a campaign")
async def update_campaign(
    campaign_id: uuid.UUID,
    body: dict,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = CampaignService(db=db)
    data = await svc.update_campaign(campaign_id, body, actor_id=uuid.UUID(u.user_id))
    return ok(data, _rid(r), ENGINE_ID)


@router.delete("/{campaign_id}", response_model=ApiResponse[dict], summary="Delete a campaign")
async def delete_campaign(
    campaign_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    svc = CampaignService(db=db)
    await svc.delete_campaign(campaign_id)
    return ok({"deleted": True, "campaign_id": str(campaign_id)}, _rid(r), ENGINE_ID)
