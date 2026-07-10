"""Sprint 29 — Admin Marketing Automation Router (14 endpoints)."""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.marketing_automation.campaign_service import MarketingCampaignService
from app.engines.marketing_automation.segment_service import MarketingSegmentService
from app.engines.marketing_automation.triggers import AutomationTriggerService
from app.engines.marketing_automation.models import MarketingCampaignEvent
from app.schemas.base import ok
from sqlalchemy import select, desc

_svc  = MarketingCampaignService()
_seg  = MarketingSegmentService()
_trig = AutomationTriggerService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


admin_marketing_router = APIRouter(
    prefix="/v1/admin/marketing",
    tags=["Admin Marketing Campaigns"],
    dependencies=[Depends(require_super_admin)],
)


# ── Campaign CRUD ──────────────────────────────────────────────────────────────

@admin_marketing_router.get("/campaigns", summary="List all marketing campaigns")
async def list_campaigns(
    r: Request,
    status:        Optional[str] = Query(None),
    campaign_type: Optional[str] = Query(None),
    limit:         int           = Query(20, ge=1, le=100),
    offset:        int           = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.list_campaigns(db, status=status, campaign_type=campaign_type,
                                     limit=limit, offset=offset)
    return ok(data, _rid(r), "admin.marketing.campaigns.list")


@admin_marketing_router.post("/campaigns", summary="Create a marketing campaign")
async def create_campaign(
    body: dict,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.create_campaign(db, actor_user_id=uuid.UUID(u.user_id), payload=body)
    return ok(data, _rid(r), "admin.marketing.campaigns.create")


@admin_marketing_router.get("/campaigns/{campaign_id}", summary="Get campaign detail")
async def get_campaign(
    campaign_id: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_campaign(db, uuid.UUID(campaign_id))
    return ok(data, _rid(r), "admin.marketing.campaigns.get")


@admin_marketing_router.put("/campaigns/{campaign_id}", summary="Update campaign")
async def update_campaign(
    campaign_id: str,
    body: dict,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.update_campaign(db, uuid.UUID(campaign_id), body)
    return ok(data, _rid(r), "admin.marketing.campaigns.update")


# ── Campaign lifecycle ─────────────────────────────────────────────────────────

@admin_marketing_router.post("/campaigns/{campaign_id}/schedule", summary="Schedule campaign")
async def schedule_campaign(
    campaign_id: str, r: Request, db: AsyncSession = Depends(get_db),
):
    data = await _svc.schedule_campaign(db, uuid.UUID(campaign_id))
    return ok(data, _rid(r), "admin.marketing.campaigns.schedule")


@admin_marketing_router.post("/campaigns/{campaign_id}/pause", summary="Pause campaign")
async def pause_campaign(
    campaign_id: str, r: Request, db: AsyncSession = Depends(get_db),
):
    data = await _svc.pause_campaign(db, uuid.UUID(campaign_id))
    return ok(data, _rid(r), "admin.marketing.campaigns.pause")


@admin_marketing_router.post("/campaigns/{campaign_id}/resume", summary="Resume campaign")
async def resume_campaign(
    campaign_id: str, r: Request, db: AsyncSession = Depends(get_db),
):
    data = await _svc.resume_campaign(db, uuid.UUID(campaign_id))
    return ok(data, _rid(r), "admin.marketing.campaigns.resume")


@admin_marketing_router.post("/campaigns/{campaign_id}/cancel", summary="Cancel campaign")
async def cancel_campaign(
    campaign_id: str, r: Request, db: AsyncSession = Depends(get_db),
):
    data = await _svc.cancel_campaign(db, uuid.UUID(campaign_id))
    return ok(data, _rid(r), "admin.marketing.campaigns.cancel")


@admin_marketing_router.post("/campaigns/{campaign_id}/run-now", summary="Run campaign immediately")
async def run_campaign_now(
    campaign_id: str, r: Request, db: AsyncSession = Depends(get_db),
):
    data = await _svc.run_campaign(db, uuid.UUID(campaign_id))
    return ok(data, _rid(r), "admin.marketing.campaigns.run")


@admin_marketing_router.get("/campaigns/{campaign_id}/performance", summary="Campaign performance metrics")
async def campaign_performance(
    campaign_id: str, r: Request, db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_campaign_performance(db, uuid.UUID(campaign_id))
    return ok(data, _rid(r), "admin.marketing.campaigns.performance")


# ── Segment preview ────────────────────────────────────────────────────────────

@admin_marketing_router.post("/segments/preview", summary="Preview audience segment")
async def preview_segment(
    body: dict,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    audience = body.get("audience", "customers")
    rules    = body.get("rules", {})
    data     = await _seg.preview_segment(db, rules, audience)
    return ok(data, _rid(r), "admin.marketing.segments.preview")


# ── Campaign events ────────────────────────────────────────────────────────────

@admin_marketing_router.get("/events", summary="List campaign events")
async def list_campaign_events(
    r: Request,
    campaign_id: Optional[str] = Query(None),
    event_type:  Optional[str] = Query(None),
    limit:       int           = Query(50, ge=1, le=200),
    offset:      int           = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import and_
    filters = []
    if campaign_id:
        filters.append(MarketingCampaignEvent.campaign_id == uuid.UUID(campaign_id))
    if event_type:
        filters.append(MarketingCampaignEvent.event_type == event_type)

    stmt = (select(MarketingCampaignEvent)
            .order_by(desc(MarketingCampaignEvent.created_at))
            .limit(limit).offset(offset))
    if filters:
        from sqlalchemy import and_
        stmt = stmt.where(and_(*filters))

    result = await db.execute(stmt)
    return ok([e.to_dict() for e in result.scalars().all()], _rid(r), "admin.marketing.events.list")


# ── Automation triggers ────────────────────────────────────────────────────────

@admin_marketing_router.get("/automation-triggers", summary="List automation triggers")
async def list_triggers(r: Request):
    return ok(_trig.list_triggers(), r.state.__dict__.get("request_id", "—"),
              "admin.marketing.triggers.list")


@admin_marketing_router.post(
    "/automation-triggers/{trigger_key}/run",
    summary="Execute an automation trigger",
)
async def run_trigger(
    trigger_key: str,
    body: dict,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await _trig.run_trigger(
        db, trigger_key=trigger_key,
        actor_user_id=uuid.UUID(u.user_id),
        params=body,
    )
    return ok(data, _rid(r), "admin.marketing.triggers.run")
