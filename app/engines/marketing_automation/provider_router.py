"""Sprint 29 — Provider Marketing Visibility Router.

Provider sees only own campaign impact, own visibility status, campaigns, and assets.
tenant_id always from token — never from query params.
"""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, and_, desc, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.core.permissions import require_mutation_access_scope
from app.engines.marketing_automation.models import MarketingCampaignEvent
from app.schemas.base import ok

provider_marketing_router = APIRouter(
    prefix="/v1/provider/marketing",
    tags=["Provider Marketing Visibility"],
)


def _tid(u: UserContext) -> uuid.UUID:
    if not u.tenant_id:
        raise ValueError("MARKETING_ACCESS_DENIED: no tenant_id in token")
    return uuid.UUID(u.tenant_id)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@provider_marketing_router.get(
    "/visibility-status",
    summary="Provider marketing visibility status (own tenant only)",
)
async def provider_visibility_status(
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    result = await db.execute(text("""
        SELECT
          t.id                  AS tenant_id,
          t.is_bookable,
          t.is_visible,
          t.subscription_status,
          t.verification_status,
          t.status              AS tenant_status,
          t.city
        FROM tenants t
        WHERE t.id = :tenant_id
        LIMIT 1
    """), {"tenant_id": str(tenant_id)})
    row = result.mappings().first()
    data = dict(row) if row else {}
    # Convert UUID to str for JSON
    if "tenant_id" in data and data["tenant_id"]:
        data["tenant_id"] = str(data["tenant_id"])
    return ok(data, _rid(r), "provider.marketing.visibility")


@provider_marketing_router.get(
    "/campaign-impact",
    summary="Campaigns that targeted this provider (own tenant only)",
)
async def provider_campaign_impact(
    r: Request,
    limit:  int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _tid(u)
    result = await db.execute(
        select(MarketingCampaignEvent)
        .where(and_(
            MarketingCampaignEvent.tenant_id == tid,
            MarketingCampaignEvent.recipient_user_id == uuid.UUID(u.user_id),
        ))
        .order_by(desc(MarketingCampaignEvent.created_at))
        .limit(limit)
        .offset(offset)
    )
    events = [e.to_dict() for e in result.scalars().all()]
    return ok(events, _rid(r), "provider.marketing.campaign_impact")


@provider_marketing_router.get(
    "/leads-attributed",
    summary="Leads or bookings attributed to marketing campaigns (own tenant only)",
)
async def provider_leads_attributed(
    r: Request,
    limit:  int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _tid(u)
    result = await db.execute(
        select(MarketingCampaignEvent)
        .where(and_(
            MarketingCampaignEvent.tenant_id   == tid,
            MarketingCampaignEvent.event_type  == "converted",
        ))
        .order_by(desc(MarketingCampaignEvent.created_at))
        .limit(limit)
        .offset(offset)
    )
    events = [e.to_dict() for e in result.scalars().all()]
    return ok(events, _rid(r), "provider.marketing.leads_attributed")


# ── Sprint 13 Provider Marketing Campaign + Asset endpoints ───────────────────

@provider_marketing_router.get("/status", summary="Provider marketing readiness status")
async def provider_marketing_status(
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _tid(u)
    active = await db.execute(text("""
        SELECT id, status, admin_review_status, created_at
        FROM provider_marketing_campaigns
        WHERE tenant_id = :tid
        ORDER BY created_at DESC LIMIT 1
    """), {"tid": str(tid)})
    row = active.mappings().first()
    active_campaign = None
    if row:
        active_campaign = {
            "id": str(row["id"]),
            "status": row["status"],
            "admin_review_status": row["admin_review_status"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
    marketing_ready = bool(row and row["status"] in ("published", "manually_published", "approved"))
    blockers = []
    if not marketing_ready:
        if not row:
            blockers.append({"code": "NO_CAMPAIGN", "message": "No marketing campaign started yet.", "route": None})
        elif row["status"] in ("pending_admin_review",):
            blockers.append({"code": "PENDING_REVIEW", "message": "Campaign is under admin review.", "route": None})
        elif row["status"] in ("rejected",):
            blockers.append({"code": "REJECTED", "message": "Campaign was rejected. Please revise and resubmit.", "route": None})
    return ok({
        "marketing_ready": marketing_ready,
        "status": row["status"] if row else "not_started",
        "blockers": blockers,
        "active_campaign": active_campaign,
    }, _rid(r), "provider.marketing.status")


@provider_marketing_router.get("/campaigns", summary="List provider marketing campaigns (own tenant)")
async def list_provider_campaigns(
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _tid(u)
    result = await db.execute(text("""
        SELECT id, campaign_name, campaign_type, status, marketing_ready,
               provider_review_status, admin_review_status, rejection_reason,
               requested_changes, approved_at, published_at, created_at
        FROM provider_marketing_campaigns
        WHERE tenant_id = :tid
        ORDER BY created_at DESC LIMIT 50
    """), {"tid": str(tid)})
    rows = result.mappings().all()
    campaigns = []
    for row in rows:
        campaigns.append({
            "id": str(row["id"]),
            "campaign_name": row["campaign_name"],
            "campaign_type": row["campaign_type"],
            "status": row["status"],
            "marketing_ready": bool(row["marketing_ready"]),
            "provider_review_status": row["provider_review_status"],
            "admin_review_status": row["admin_review_status"],
            "rejection_reason": row["rejection_reason"],
            "requested_changes": row["requested_changes"],
            "approved_at": row["approved_at"].isoformat() if row["approved_at"] else None,
            "published_at": row["published_at"].isoformat() if row["published_at"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })
    return ok({"campaigns": campaigns, "count": len(campaigns)}, _rid(r), "provider.marketing.campaigns")


@provider_marketing_router.get("/campaigns/{campaign_id}", summary="Get single provider campaign")
async def get_provider_campaign(
    campaign_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _tid(u)
    result = await db.execute(text("""
        SELECT id, campaign_name, campaign_type, status, marketing_ready,
               provider_review_status, admin_review_status, rejection_reason,
               requested_changes, approved_at, published_at, created_at
        FROM provider_marketing_campaigns
        WHERE id = :cid AND tenant_id = :tid LIMIT 1
    """), {"cid": str(campaign_id), "tid": str(tid)})
    row = result.mappings().first()
    if not row:
        return ok({"campaign": None}, _rid(r), "provider.marketing.campaign")
    campaign = {
        "id": str(row["id"]),
        "campaign_name": row["campaign_name"],
        "campaign_type": row["campaign_type"],
        "status": row["status"],
        "marketing_ready": bool(row["marketing_ready"]),
        "provider_review_status": row["provider_review_status"],
        "admin_review_status": row["admin_review_status"],
        "rejection_reason": row["rejection_reason"],
        "requested_changes": row["requested_changes"],
        "approved_at": row["approved_at"].isoformat() if row["approved_at"] else None,
        "published_at": row["published_at"].isoformat() if row["published_at"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }
    return ok({"campaign": campaign}, _rid(r), "provider.marketing.campaign")


@provider_marketing_router.post("/campaigns/generate-launch", summary="Generate a launch marketing campaign")
async def generate_launch_campaign(
    r: Request,
    u: UserContext = Depends(require_mutation_access_scope),
    db: AsyncSession = Depends(get_db),
):
    tid = _tid(u)
    campaign_id = uuid.uuid4()
    await db.execute(text("""
        INSERT INTO provider_marketing_campaigns
          (id, tenant_id, campaign_key, campaign_name, campaign_type, status, marketing_ready)
        VALUES
          (:id, :tid, :key, :name, 'launch', 'draft', false)
        ON CONFLICT DO NOTHING
    """), {
        "id": str(campaign_id),
        "tid": str(tid),
        "key": f"launch_{str(tid)[:8]}",
        "name": "Launch Campaign",
    })
    await db.commit()
    campaign = {
        "id": str(campaign_id),
        "campaign_name": "Launch Campaign",
        "campaign_type": "launch",
        "status": "draft",
        "marketing_ready": False,
        "provider_review_status": None,
        "admin_review_status": None,
        "rejection_reason": None,
        "requested_changes": None,
        "approved_at": None,
        "published_at": None,
        "created_at": None,
    }
    return ok({"success": True, "message": "Launch campaign created.", "campaign": campaign,
               "marketing_ready": False, "blockers": []}, _rid(r), "provider.marketing")


@provider_marketing_router.post("/campaigns/{campaign_id}/submit-review", summary="Submit campaign for admin review")
async def submit_campaign_review(
    campaign_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_mutation_access_scope),
    db: AsyncSession = Depends(get_db),
):
    tid = _tid(u)
    await db.execute(text("""
        UPDATE provider_marketing_campaigns
        SET status='pending_admin_review', provider_review_status='submitted', updated_at=now()
        WHERE id=:cid AND tenant_id=:tid
    """), {"cid": str(campaign_id), "tid": str(tid)})
    await db.commit()
    return ok({"success": True, "campaign": {"id": str(campaign_id), "status": "pending_admin_review"}},
              _rid(r), "provider.marketing")


@provider_marketing_router.get("/assets", summary="List provider marketing assets (own tenant)")
async def list_provider_assets(
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tid = _tid(u)
    result = await db.execute(text("""
        SELECT id, campaign_id, asset_type, channel, language, title, body,
               image_url, generation_source, status, provider_notes,
               admin_notes, rejection_reason, publish_url, published_at, created_at
        FROM provider_marketing_assets
        WHERE tenant_id = :tid
        ORDER BY created_at DESC LIMIT 100
    """), {"tid": str(tid)})
    rows = result.mappings().all()
    assets = []
    for row in rows:
        assets.append({
            "id": str(row["id"]),
            "campaign_id": str(row["campaign_id"]) if row["campaign_id"] else None,
            "asset_type": row["asset_type"],
            "channel": row["channel"],
            "language": row["language"] or "en",
            "title": row["title"],
            "body": row["body"],
            "image_url": row["image_url"],
            "generation_source": row["generation_source"] or "template",
            "status": row["status"],
            "provider_notes": row["provider_notes"],
            "admin_notes": row["admin_notes"],
            "rejection_reason": row["rejection_reason"],
            "publish_url": row["publish_url"],
            "published_at": row["published_at"].isoformat() if row["published_at"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": None,
        })
    return ok({"assets": assets, "count": len(assets)}, _rid(r), "provider.marketing.assets")


@provider_marketing_router.put("/assets/{asset_id}/provider-notes", summary="Update provider notes on asset")
async def update_asset_provider_notes(
    asset_id: uuid.UUID,
    r: Request,
    u: UserContext = Depends(require_mutation_access_scope),
    db: AsyncSession = Depends(get_db),
):
    tid = _tid(u)
    body = await r.json()
    notes = body.get("notes", "")
    await db.execute(text("""
        UPDATE provider_marketing_assets
        SET provider_notes=:notes, updated_at=now()
        WHERE id=:aid AND tenant_id=:tid
    """), {"aid": str(asset_id), "tid": str(tid), "notes": notes})
    await db.commit()
    return ok({"success": True, "asset": {"id": str(asset_id), "provider_notes": notes}},
              _rid(r), "provider.marketing")
