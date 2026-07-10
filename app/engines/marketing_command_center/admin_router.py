"""Marketing Automation Command Center — Admin Router.

Every mutating endpoint is gated by a marketing.* permission constant (Part O)
and writes a MarketingAuditLog row via the service layer (Part P).
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.core.permissions import P, require_permission
from app.schemas.base import ok
from app.engines.marketing_command_center.service import MarketingCommandCenterService

router = APIRouter(prefix="/v1/admin/marketing", tags=["Marketing Command Center"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.MARKETING_AUTOMATION_READ))) -> MarketingCommandCenterService:
    return MarketingCommandCenterService(
        db=db, actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role, request_id=_rid(r))


# ── Summary ──────────────────────────────────────────────────────────────────

@router.get("/automation/summary", summary="Marketing automation KPI summary")
async def get_summary(r: Request, s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.get_summary(), _rid(r), "marketing_command_center")


# ── Posts ────────────────────────────────────────────────────────────────────

@router.get("/posts", summary="List marketing posts")
async def list_posts(r: Request, status: Optional[str] = Query(None),
                      campaign_id: Optional[uuid.UUID] = Query(None), limit: int = Query(50, le=200),
                      s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.list_posts(status, campaign_id, limit), _rid(r), "marketing_command_center")


@router.get("/posts/{post_id}", summary="Get a marketing post")
async def get_post(post_id: uuid.UUID, r: Request, s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.get_post(post_id), _rid(r), "marketing_command_center")


@router.post("/posts", summary="Create a marketing post draft")
async def create_post(r: Request, db: AsyncSession = Depends(get_db),
                       u: UserContext = Depends(require_permission(P.MARKETING_POSTS_CREATE))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.create_post(body), _rid(r), "marketing_command_center")


@router.put("/posts/{post_id}", summary="Update a marketing post")
async def update_post(post_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                       u: UserContext = Depends(require_permission(P.MARKETING_POSTS_UPDATE))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.update_post(post_id, body), _rid(r), "marketing_command_center")


@router.post("/posts/{post_id}/submit-approval", summary="Submit post for approval")
async def submit_approval(post_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                           u: UserContext = Depends(require_permission(P.MARKETING_POSTS_UPDATE))):
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.submit_for_approval(post_id), _rid(r), "marketing_command_center")


@router.post("/posts/{post_id}/approve", summary="Approve a post")
async def approve_post(post_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                        u: UserContext = Depends(require_permission(P.MARKETING_POSTS_APPROVE))):
    body = await r.json() if r.headers.get("content-length") not in (None, "0") else {}
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.approve_post(post_id, body.get("reason")), _rid(r), "marketing_command_center")


@router.post("/posts/{post_id}/reject", summary="Reject a post")
async def reject_post(post_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                       u: UserContext = Depends(require_permission(P.MARKETING_POSTS_APPROVE))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.reject_post(post_id, body.get("reason", "")), _rid(r), "marketing_command_center")


@router.post("/posts/{post_id}/schedule", summary="Schedule a post")
async def schedule_post(post_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                         u: UserContext = Depends(require_permission(P.MARKETING_POSTS_SCHEDULE))):
    body = await r.json()
    scheduled_at = datetime.fromisoformat(body["scheduled_at"])
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.schedule_post(post_id, scheduled_at, body.get("channels", [])), _rid(r), "marketing_command_center")


@router.post("/posts/{post_id}/reschedule", summary="Reschedule a post")
async def reschedule_post(post_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                           u: UserContext = Depends(require_permission(P.MARKETING_POSTS_SCHEDULE))):
    body = await r.json()
    scheduled_at = datetime.fromisoformat(body["scheduled_at"])
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.reschedule_post(post_id, scheduled_at), _rid(r), "marketing_command_center")


@router.post("/posts/{post_id}/publish-now", summary="Publish a post immediately")
async def publish_now(post_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                       u: UserContext = Depends(require_permission(P.MARKETING_POSTS_PUBLISH))):
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.publish_now(post_id), _rid(r), "marketing_command_center")


@router.post("/posts/{post_id}/retry", summary="Retry a failed post")
async def retry_post(post_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                      u: UserContext = Depends(require_permission(P.MARKETING_POSTS_RETRY))):
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.retry_post(post_id), _rid(r), "marketing_command_center")


@router.post("/posts/{post_id}/cancel", summary="Cancel a post")
async def cancel_post(post_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                       u: UserContext = Depends(require_permission(P.MARKETING_POSTS_CANCEL))):
    body = await r.json() if r.headers.get("content-length") not in (None, "0") else {}
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.cancel_post(post_id, body.get("reason")), _rid(r), "marketing_command_center")


# ── AI generation ────────────────────────────────────────────────────────────

@router.post("/ai/generate-caption", summary="Generate AI caption")
async def generate_caption(r: Request, db: AsyncSession = Depends(get_db),
                            u: UserContext = Depends(require_permission(P.MARKETING_AI_GENERATE_CAPTION))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.generate_caption(body), _rid(r), "marketing_command_center")


@router.post("/ai/generate-image", summary="Generate AI image (charged to platform AI budget)")
async def generate_image(r: Request, db: AsyncSession = Depends(get_db),
                          u: UserContext = Depends(require_permission(P.MARKETING_AI_GENERATE_IMAGE))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.generate_image(body), _rid(r), "marketing_command_center")


@router.post("/ai/generate-hashtags", summary="Generate AI hashtags")
async def generate_hashtags(r: Request, db: AsyncSession = Depends(get_db),
                             u: UserContext = Depends(require_permission(P.MARKETING_AI_GENERATE_CAPTION))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.generate_hashtags(body), _rid(r), "marketing_command_center")


@router.post("/ai/generate-variations", summary="Generate AI caption variations")
async def generate_variations(r: Request, db: AsyncSession = Depends(get_db),
                               u: UserContext = Depends(require_permission(P.MARKETING_AI_GENERATE_CAPTION))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.generate_variations(body), _rid(r), "marketing_command_center")


# ── Calendar ─────────────────────────────────────────────────────────────────

@router.get("/calendar", summary="Content calendar")
async def get_calendar(r: Request, date_from: Optional[datetime] = Query(None),
                        date_to: Optional[datetime] = Query(None),
                        s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.get_calendar(date_from, date_to), _rid(r), "marketing_command_center")


# ── Social accounts ──────────────────────────────────────────────────────────

@router.get("/social-accounts", summary="List connected social accounts")
async def list_social_accounts(r: Request, s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.list_social_accounts(), _rid(r), "marketing_command_center")


@router.post("/social-accounts/connect", summary="Connect a social account")
async def connect_social_account(r: Request, db: AsyncSession = Depends(get_db),
                                  u: UserContext = Depends(require_permission(P.MARKETING_SOCIAL_ACCOUNTS_CONNECT))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.connect_social_account(body), _rid(r), "marketing_command_center")


@router.post("/social-accounts/{account_id}/test", summary="Test social account connection")
async def test_social_account(account_id: uuid.UUID, r: Request, s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.test_social_account(account_id), _rid(r), "marketing_command_center")


@router.post("/social-accounts/{account_id}/sync", summary="Sync a social account")
async def sync_social_account(account_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                               u: UserContext = Depends(require_permission(P.MARKETING_SOCIAL_ACCOUNTS_READ))):
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.sync_social_account(account_id), _rid(r), "marketing_command_center")


@router.post("/social-accounts/{account_id}/disconnect", summary="Disconnect a social account")
async def disconnect_social_account(account_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                                     u: UserContext = Depends(require_permission(P.MARKETING_SOCIAL_ACCOUNTS_DISCONNECT))):
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.disconnect_social_account(account_id), _rid(r), "marketing_command_center")


# ── Content templates ────────────────────────────────────────────────────────

@router.get("/content-templates", summary="List content templates")
async def list_templates(r: Request, s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.list_templates(), _rid(r), "marketing_command_center")


@router.post("/content-templates", summary="Create a content template")
async def create_template(r: Request, db: AsyncSession = Depends(get_db),
                           u: UserContext = Depends(require_permission(P.MARKETING_TEMPLATES_CREATE))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.create_template(body), _rid(r), "marketing_command_center")


@router.put("/content-templates/{template_id}", summary="Update a content template")
async def update_template(template_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
                           u: UserContext = Depends(require_permission(P.MARKETING_TEMPLATES_UPDATE))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.update_template(template_id, body), _rid(r), "marketing_command_center")


# ── AI Budget ────────────────────────────────────────────────────────────────

@router.get("/ai-budget", summary="Get platform AI budget")
async def get_ai_budget(r: Request, s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.get_ai_budget(), _rid(r), "marketing_command_center")


@router.put("/ai-budget", summary="Update platform AI budget")
async def update_ai_budget(r: Request, db: AsyncSession = Depends(get_db),
                            u: UserContext = Depends(require_permission(P.MARKETING_AI_MANAGE_BUDGET))):
    body = await r.json()
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.update_ai_budget(body), _rid(r), "marketing_command_center")


@router.get("/ai-budget/ledger", summary="Platform AI budget ledger")
async def get_ai_budget_ledger(r: Request, limit: int = Query(50, le=500),
                                s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.get_ai_budget_ledger(limit), _rid(r), "marketing_command_center")


# ── Publish failures ─────────────────────────────────────────────────────────

@router.get("/publish-failures", summary="Failed publish attempts / retry queue")
async def list_publish_failures(r: Request, limit: int = Query(50, le=500),
                                 s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.list_publish_failures(limit), _rid(r), "marketing_command_center")


# ── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics/summary", summary="Marketing analytics summary")
async def analytics_summary(r: Request, s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.get_analytics_summary(), _rid(r), "marketing_command_center")


@router.get("/analytics/posts", summary="Top performing posts")
async def analytics_posts(r: Request, s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.get_top_posts(), _rid(r), "marketing_command_center")


@router.get("/analytics/campaigns", summary="Campaign performance")
async def analytics_campaigns(r: Request, s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.get_campaign_performance(), _rid(r), "marketing_command_center")


@router.get("/analytics/channels", summary="Channel performance")
async def analytics_channels(r: Request, s: MarketingCommandCenterService = Depends(_svc)):
    return ok(await s.get_channel_performance(), _rid(r), "marketing_command_center")


# ── Audit ────────────────────────────────────────────────────────────────────

@router.get("/audit-logs", summary="Marketing audit logs")
async def audit_logs(r: Request, limit: int = Query(50, le=500),
                      u: UserContext = Depends(require_permission(P.MARKETING_AUDIT_READ)),
                      db: AsyncSession = Depends(get_db)):
    svc = MarketingCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.list_audit_logs(limit), _rid(r), "marketing_command_center")
