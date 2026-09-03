"""Marketing Automation Command Center — service layer.

Business rule enforced throughout: DALL-E/AI generation cost is charged to
the PLATFORM AI budget (marketing_ai_budget / marketing_ai_budget_ledger)
only. This service never reads or writes tenant_wallets or
customer_service_credits — there is no code path by which a tenant's usage
credit balance can be affected by marketing content generation.

External calls (OpenAI DALL-E image generation, Meta Graph API publishing)
are simulated here, consistent with the existing app/engines/marketing
Sprint-15 engine's stub pattern (no real `openai`/Graph API credentials are
configured in this environment) — every simulated call still writes a real,
persisted budget-ledger row, post record, and audit log entry so the
governance/audit trail is genuine even though the external side-effect isn't.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException
from app.engines.marketing_command_center.models import (
    MarketingPost, MarketingPostAsset, MarketingAIBudget, MarketingAIBudgetLedger,
    MarketingContentTemplateV2, MarketingPublishAttempt, MarketingAuditLog,
)
from app.engines.marketing_automation.models import MarketingCampaign
from app.engines.marketing.models import SocialAccount

utcnow = lambda: datetime.now(timezone.utc)

VALID_POST_STATUSES = [
    "draft", "generated", "pending_approval", "approved", "scheduled",
    "publishing", "published", "failed", "cancelled", "archived",
]
FAILURE_REASONS = [
    "token_expired", "permission_missing", "media_upload_failed",
    "rate_limited", "invalid_caption", "network_error", "unknown_error",
]

_DALLE_COST_PER_IMAGE = Decimal("8.00")
_CAPTION_COST = Decimal("0.50")
_HASHTAG_COST = Decimal("0.10")


class MarketingCommandCenterService:
    def __init__(self, db: AsyncSession, actor_id: uuid.UUID | None = None,
                 actor_role: str | None = None, request_id: str | None = None):
        self.db = db
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.request_id = request_id

    # ── Audit ────────────────────────────────────────────────────────────────

    async def _audit(self, action_type: str, target_type: str, target_id: str | None,
                      old_value: dict | None = None, new_value: dict | None = None,
                      reason: str | None = None) -> None:
        self.db.add(MarketingAuditLog(
            actor_user_id=self.actor_id, action_type=action_type, target_type=target_type,
            target_id=target_id, old_value_json=old_value, new_value_json=new_value,
            reason=reason, request_id=self.request_id,
        ))
        await self.db.flush()

    # ── Summary (Part B) ─────────────────────────────────────────────────────

    async def get_summary(self) -> dict[str, Any]:
        async def _count(status: str | None = None) -> int:
            q = select(func.count()).select_from(MarketingPost)
            if status:
                q = q.where(MarketingPost.status == status)
            return (await self.db.execute(q)).scalar() or 0

        published = await _count("published")
        scheduled = await _count("scheduled")
        pending = await _count("pending_approval")
        failed = await _count("failed")

        images_row = await self.db.execute(
            select(func.count(), func.coalesce(func.sum(MarketingAIBudgetLedger.cost_amount), 0))
            .where(MarketingAIBudgetLedger.generation_type == "image"))
        images_generated, images_cost = images_row.one()

        spend_row = await self.db.execute(
            select(func.coalesce(func.sum(MarketingAIBudgetLedger.cost_amount), 0))
            .where(func.date(MarketingAIBudgetLedger.created_at) == func.current_date()))
        daily_spend = spend_row.scalar() or 0

        budget = await self._get_or_create_budget()

        accounts_row = await self.db.execute(select(func.count()).select_from(SocialAccount))
        connected_channels = accounts_row.scalar() or 0

        campaigns_row = await self.db.execute(
            select(func.count()).select_from(MarketingCampaign).where(MarketingCampaign.status == "active"))
        active_campaigns = campaigns_row.scalar() or 0

        return {
            "posts_published": published,
            "scheduled_posts": scheduled,
            "pending_approval": pending,
            "failed_posts": failed,
            "images_generated": int(images_generated or 0),
            "images_generated_cost": float(images_cost or 0),
            "platform_ai_spend_today": float(daily_spend),
            "platform_ai_daily_budget": float(budget.daily_budget),
            "connected_channels": connected_channels,
            "active_campaigns": active_campaigns,
        }

    # ── AI Budget (Part F) ───────────────────────────────────────────────────

    async def _get_or_create_budget(self) -> MarketingAIBudget:
        row = await self.db.execute(select(MarketingAIBudget).where(MarketingAIBudget.scope == "platform"))
        budget = row.scalar_one_or_none()
        if not budget:
            budget = MarketingAIBudget(scope="platform")
            self.db.add(budget)
            await self.db.flush()
        return budget

    async def get_ai_budget(self) -> dict[str, Any]:
        budget = await self._get_or_create_budget()
        today_spend = (await self.db.execute(
            select(func.coalesce(func.sum(MarketingAIBudgetLedger.cost_amount), 0))
            .where(func.date(MarketingAIBudgetLedger.created_at) == func.current_date())
        )).scalar() or 0
        month_spend = (await self.db.execute(
            select(func.coalesce(func.sum(MarketingAIBudgetLedger.cost_amount), 0))
            .where(func.date_trunc("month", MarketingAIBudgetLedger.created_at) == func.date_trunc("month", func.now()))
        )).scalar() or 0
        images_count = (await self.db.execute(
            select(func.count()).where(MarketingAIBudgetLedger.generation_type == "image")
        )).scalar() or 0
        total_image_cost = (await self.db.execute(
            select(func.coalesce(func.sum(MarketingAIBudgetLedger.cost_amount), 0))
            .where(MarketingAIBudgetLedger.generation_type == "image")
        )).scalar() or 0
        avg_cost = float(total_image_cost) / images_count if images_count else 0.0

        d = budget.to_dict()
        d.update({
            "daily_used": float(today_spend),
            "daily_remaining": max(0.0, float(budget.daily_budget) - float(today_spend)),
            "monthly_used": float(month_spend),
            "monthly_remaining": max(0.0, float(budget.monthly_budget) - float(month_spend)),
            "images_generated": images_count,
            "average_cost_per_image": round(avg_cost, 2),
            "platform_pays_note": "Platform pays AI generation costs. Tenant usage credits are never deducted for marketing generation.",
        })
        return d

    async def update_ai_budget(self, data: dict[str, Any]) -> dict[str, Any]:
        budget = await self._get_or_create_budget()
        old = budget.to_dict()
        for field in ("daily_budget", "monthly_budget", "cost_alert_threshold_pct",
                      "auto_disable_on_exceed", "require_approval_above_cost"):
            if field in data and data[field] is not None:
                setattr(budget, field, data[field])
        budget.updated_by_user_id = self.actor_id
        budget.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.ai_budget.updated", "ai_budget", str(budget.id), old, budget.to_dict())
        return budget.to_dict()

    async def get_ai_budget_ledger(self, limit: int = 50) -> dict[str, Any]:
        rows = (await self.db.execute(
            select(MarketingAIBudgetLedger).order_by(desc(MarketingAIBudgetLedger.created_at)).limit(limit)
        )).scalars().all()
        return {"items": [r.to_dict() for r in rows]}

    async def _check_and_charge_budget(self, generation_type: str, model: str | None,
                                        cost: Decimal, post_id: uuid.UUID | None,
                                        campaign_id: uuid.UUID | None) -> None:
        budget = await self._get_or_create_budget()
        today_spend = (await self.db.execute(
            select(func.coalesce(func.sum(MarketingAIBudgetLedger.cost_amount), 0))
            .where(func.date(MarketingAIBudgetLedger.created_at) == func.current_date())
        )).scalar() or 0
        if budget.auto_disable_on_exceed and (Decimal(str(today_spend)) + cost) > budget.daily_budget:
            raise ServiceOSException(
                "AI_BUDGET_EXCEEDED",
                "Platform AI daily budget exceeded. Generation blocked until budget resets or is increased.",
                status_code=402,
                context={"daily_budget": float(budget.daily_budget), "today_spend": float(today_spend)},
            )
        self.db.add(MarketingAIBudgetLedger(
            generation_type=generation_type, model=model, cost_amount=cost,
            post_id=post_id, campaign_id=campaign_id, created_by_user_id=self.actor_id,
        ))
        await self.db.flush()

    # ── AI Generation (Part H step 5) ────────────────────────────────────────

    async def generate_caption(self, data: dict[str, Any]) -> dict[str, Any]:
        await self._check_and_charge_budget("caption", "gpt-content-v1", _CAPTION_COST, data.get("post_id"), data.get("campaign_id"))
        goal = data.get("goal", "brand awareness")
        tone = data.get("tone", "friendly")
        message = data.get("main_message", "")
        caption = f"{message}\n\nWe're here to help — {goal.replace('_', ' ')}, {tone} tone applied."
        await self._audit("marketing.post.generated", "post", str(data.get("post_id") or ""), None, {"caption": caption})
        return {"caption": caption, "short_caption": caption[:120], "estimated_cost": float(_CAPTION_COST)}

    async def generate_hashtags(self, data: dict[str, Any]) -> dict[str, Any]:
        await self._check_and_charge_budget("hashtags", "gpt-content-v1", _HASHTAG_COST, data.get("post_id"), data.get("campaign_id"))
        vertical = (data.get("vertical") or "home_services").replace("_", "")
        base = [f"#{vertical}", "#Fuvay", "#BookNow"]
        return {"hashtags": base, "estimated_cost": float(_HASHTAG_COST)}

    async def generate_image(self, data: dict[str, Any]) -> dict[str, Any]:
        await self._check_and_charge_budget("image", "dall-e-3", _DALLE_COST_PER_IMAGE, data.get("post_id"), data.get("campaign_id"))
        prompt = data.get("prompt", "")
        prompt_hash = uuid.uuid5(uuid.NAMESPACE_URL, prompt or str(uuid.uuid4())).hex
        image_url = f"https://dalle-placeholder.serviceos.local/{prompt_hash}.png"
        if data.get("post_id"):
            self.db.add(MarketingPostAsset(
                post_id=data["post_id"], asset_type="image", url=image_url,
                generated_by_ai=True, ai_model="dall-e-3", ai_prompt=prompt,
                alt_text=data.get("alt_text"), cost_amount=_DALLE_COST_PER_IMAGE, status="ready",
            ))
            await self.db.flush()
        await self._audit("marketing.post.image_generated", "post", str(data.get("post_id") or ""), None, {"image_url": image_url})
        return {"image_url": image_url, "alt_text": data.get("alt_text"), "estimated_cost": float(_DALLE_COST_PER_IMAGE),
                "compliance_warnings": []}

    async def generate_variations(self, data: dict[str, Any]) -> dict[str, Any]:
        count = int(data.get("count", 3))
        cost = _CAPTION_COST * count
        await self._check_and_charge_budget("variations", "gpt-content-v1", cost, data.get("post_id"), data.get("campaign_id"))
        base = data.get("main_message", "")
        variations = [f"{base} (variation {i+1})" for i in range(count)]
        return {"variations": variations, "estimated_cost": float(cost)}

    # ── Posts (Part D, N) ────────────────────────────────────────────────────

    def _job_dict_extra(self, p: MarketingPost) -> dict[str, Any]:
        d = p.to_dict()
        d["amount_collected"] = None  # never applicable — marketing posts carry no customer payment
        return d

    async def list_posts(self, status: str | None = None, campaign_id: uuid.UUID | None = None,
                          limit: int = 50) -> dict[str, Any]:
        q = select(MarketingPost)
        if status and status != "all":
            q = q.where(MarketingPost.status == status)
        if campaign_id:
            q = q.where(MarketingPost.campaign_id == campaign_id)
        q = q.order_by(desc(MarketingPost.created_at)).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return {"items": [r.to_dict() for r in rows], "total": len(rows)}

    async def get_post(self, post_id: uuid.UUID) -> dict[str, Any]:
        post = await self._get_post_or_404(post_id)
        assets = (await self.db.execute(
            select(MarketingPostAsset).where(MarketingPostAsset.post_id == post_id))).scalars().all()
        d = post.to_dict()
        d["assets"] = [a.to_dict() for a in assets]
        return d

    async def _get_post_or_404(self, post_id: uuid.UUID) -> MarketingPost:
        row = await self.db.execute(select(MarketingPost).where(MarketingPost.id == post_id))
        post = row.scalar_one_or_none()
        if not post:
            raise ServiceOSException("POST_NOT_FOUND", "Marketing post not found.", status_code=404)
        return post

    async def create_post(self, data: dict[str, Any]) -> dict[str, Any]:
        post = MarketingPost(
            post_code=f"MPOST-{uuid.uuid4().hex[:8].upper()}",
            campaign_id=data.get("campaign_id"), title=data["title"], caption=data.get("caption"),
            short_caption=data.get("short_caption"), hashtags_json=data.get("hashtags"),
            vertical_key=data.get("vertical_key"), category_id=data.get("category_id"),
            service_id=data.get("service_id"), tenant_id=data.get("tenant_id"),
            target_locations_json=data.get("target_locations"), language=data.get("language", "english"),
            tone=data.get("tone"), post_type=data.get("post_type", "image_post"), goal=data.get("goal"),
            cta=data.get("cta"), channels_json=data.get("channels"), status="draft",
            approval_status="not_required", created_by_user_id=self.actor_id,
        )
        self.db.add(post)
        await self.db.flush()
        await self._audit("marketing.post.created", "post", str(post.id), None, post.to_dict())
        return post.to_dict()

    async def update_post(self, post_id: uuid.UUID, data: dict[str, Any]) -> dict[str, Any]:
        post = await self._get_post_or_404(post_id)
        old = post.to_dict()
        for field in ("title", "caption", "short_caption", "hashtags_json", "cta", "tone",
                      "channels_json", "goal", "post_type"):
            key = field.replace("_json", "")
            if key in data:
                setattr(post, field, data[key])
        post.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.post.updated", "post", str(post.id), old, post.to_dict())
        return post.to_dict()

    async def submit_for_approval(self, post_id: uuid.UUID) -> dict[str, Any]:
        post = await self._get_post_or_404(post_id)
        post.status = "pending_approval"
        post.approval_status = "pending"
        post.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.post.submitted_for_approval", "post", str(post.id))
        return post.to_dict()

    async def approve_post(self, post_id: uuid.UUID, reason: str | None = None) -> dict[str, Any]:
        post = await self._get_post_or_404(post_id)
        post.status = "approved"
        post.approval_status = "approved"
        post.approved_by_user_id = self.actor_id
        post.approved_at = utcnow()
        post.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.post.approved", "post", str(post.id), reason=reason)
        return post.to_dict()

    async def reject_post(self, post_id: uuid.UUID, reason: str) -> dict[str, Any]:
        post = await self._get_post_or_404(post_id)
        post.status = "draft"
        post.approval_status = "rejected"
        post.rejection_reason = reason
        post.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.post.rejected", "post", str(post.id), reason=reason)
        return post.to_dict()

    async def schedule_post(self, post_id: uuid.UUID, scheduled_at: datetime, channels: list[str]) -> dict[str, Any]:
        post = await self._get_post_or_404(post_id)
        if scheduled_at <= utcnow():
            raise ServiceOSException("SCHEDULE_IN_PAST", "Cannot schedule a post in the past.", status_code=422)
        if post.approval_status == "pending":
            raise ServiceOSException("APPROVAL_PENDING", "Cannot schedule a post while approval is pending.", status_code=422)
        for channel in channels:
            acc_row = await self.db.execute(select(SocialAccount).where(SocialAccount.platform == channel))
            acc = acc_row.scalar_one_or_none()
            if not acc or acc.status != "active":
                raise ServiceOSException("CHANNEL_DISCONNECTED",
                    f"Cannot schedule to disconnected channel: {channel}.", status_code=422)
        post.status = "scheduled"
        post.scheduled_at = scheduled_at
        post.channels_json = channels
        post.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.post.scheduled", "post", str(post.id), new_value={"scheduled_at": scheduled_at.isoformat()})
        return post.to_dict()

    async def reschedule_post(self, post_id: uuid.UUID, scheduled_at: datetime) -> dict[str, Any]:
        post = await self._get_post_or_404(post_id)
        if scheduled_at <= utcnow():
            raise ServiceOSException("SCHEDULE_IN_PAST", "Cannot reschedule a post to the past.", status_code=422)
        old_time = post.scheduled_at.isoformat() if post.scheduled_at else None
        post.scheduled_at = scheduled_at
        post.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.post.rescheduled", "post", str(post.id),
                           {"scheduled_at": old_time}, {"scheduled_at": scheduled_at.isoformat()})
        return post.to_dict()

    async def publish_now(self, post_id: uuid.UUID) -> dict[str, Any]:
        post = await self._get_post_or_404(post_id)
        if post.approval_status == "pending":
            raise ServiceOSException("APPROVAL_PENDING", "Cannot publish a post while approval is pending.", status_code=422)
        channels = post.channels_json or []
        if not channels:
            raise ServiceOSException("NO_CHANNELS", "Post has no channels selected.", status_code=422)
        for i, channel in enumerate(channels):
            acc_row = await self.db.execute(select(SocialAccount).where(SocialAccount.platform == channel))
            acc = acc_row.scalar_one_or_none()
            if not acc or acc.status != "active":
                raise ServiceOSException("CHANNEL_DISCONNECTED",
                    f"Cannot publish to disconnected channel: {channel}.", status_code=422)
            self.db.add(MarketingPublishAttempt(
                post_id=post.id, channel=channel, social_account_id=acc.id,
                status="published", attempt_number=1, external_post_id=f"sim_{uuid.uuid4().hex[:10]}",
            ))
        post.status = "published"
        post.published_at = utcnow()
        post.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.post.published", "post", str(post.id))
        return post.to_dict()

    async def retry_post(self, post_id: uuid.UUID) -> dict[str, Any]:
        post = await self._get_post_or_404(post_id)
        last_attempt_row = await self.db.execute(
            select(MarketingPublishAttempt).where(MarketingPublishAttempt.post_id == post_id)
            .order_by(desc(MarketingPublishAttempt.attempt_number)).limit(1))
        last_attempt = last_attempt_row.scalar_one_or_none()
        next_num = (last_attempt.attempt_number + 1) if last_attempt else 1
        channel = last_attempt.channel if last_attempt else (post.channels_json or ["facebook"])[0]
        acc_row = await self.db.execute(select(SocialAccount).where(SocialAccount.platform == channel))
        acc = acc_row.scalar_one_or_none()
        attempt = MarketingPublishAttempt(
            post_id=post.id, channel=channel, social_account_id=acc.id if acc else None,
            status="published" if acc and acc.status == "active" else "failed",
            attempt_number=next_num,
            error_code=None if acc and acc.status == "active" else "token_expired",
            external_post_id=f"sim_{uuid.uuid4().hex[:10]}" if acc and acc.status == "active" else None,
        )
        self.db.add(attempt)
        post.status = "published" if acc and acc.status == "active" else "failed"
        if post.status == "published":
            post.published_at = utcnow()
        post.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.post.retry", "post", str(post.id))
        return {"post": post.to_dict(), "attempt": attempt.to_dict()}

    async def cancel_post(self, post_id: uuid.UUID, reason: str | None = None) -> dict[str, Any]:
        post = await self._get_post_or_404(post_id)
        post.status = "cancelled"
        post.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.post.cancelled", "post", str(post.id), reason=reason)
        return post.to_dict()

    # ── Calendar (Part G) ────────────────────────────────────────────────────

    async def get_calendar(self, date_from: datetime | None = None, date_to: datetime | None = None) -> dict[str, Any]:
        q = select(MarketingPost).where(MarketingPost.scheduled_at.is_not(None))
        if date_from:
            q = q.where(MarketingPost.scheduled_at >= date_from)
        if date_to:
            q = q.where(MarketingPost.scheduled_at <= date_to)
        q = q.order_by(MarketingPost.scheduled_at)
        rows = (await self.db.execute(q)).scalars().all()
        return {"items": [r.to_dict() for r in rows]}

    # ── Social accounts (Part E) ─────────────────────────────────────────────

    async def list_social_accounts(self) -> dict[str, Any]:
        rows = (await self.db.execute(select(SocialAccount))).scalars().all()
        items = []
        for a in rows:
            token_status = "expired" if a.token_expires_at and a.token_expires_at < utcnow() else "valid"
            items.append({
                "id": str(a.id), "platform": a.platform, "account_name": a.page_name,
                "connection_status": getattr(a, "connection_status", "connected"),
                "token_status": token_status,
                "publishing_enabled": getattr(a, "publishing_enabled", True),
                "daily_post_limit": getattr(a, "daily_post_limit", 10),
                "last_sync_at": a.last_refreshed_at.isoformat() if a.last_refreshed_at else None,
                "status": a.status,
            })
        return {"items": items, "total": len(items)}

    async def connect_social_account(self, data: dict[str, Any]) -> dict[str, Any]:
        acc = SocialAccount(
            platform=data["platform"], page_id=data.get("page_id", uuid.uuid4().hex[:12]),
            page_name=data.get("account_name", data["platform"].title()),
            access_token=data.get("access_token", "sim_token"),
            token_expires_at=data.get("token_expires_at") or (utcnow().replace(year=utcnow().year + 1)),
            status="active",
        )
        self.db.add(acc)
        await self.db.flush()
        await self._audit("marketing.social_account.connected", "social_account", str(acc.id))
        return {"id": str(acc.id), "platform": acc.platform, "account_name": acc.page_name, "status": acc.status}

    async def test_social_account(self, account_id: uuid.UUID) -> dict[str, Any]:
        row = await self.db.execute(select(SocialAccount).where(SocialAccount.id == account_id))
        acc = row.scalar_one_or_none()
        if not acc:
            raise ServiceOSException("ACCOUNT_NOT_FOUND", "Social account not found.", status_code=404)
        expired = bool(acc.token_expires_at and acc.token_expires_at < utcnow())
        return {"account_id": str(acc.id), "connection_ok": not expired,
                "token_status": "expired" if expired else "valid"}

    async def sync_social_account(self, account_id: uuid.UUID) -> dict[str, Any]:
        row = await self.db.execute(select(SocialAccount).where(SocialAccount.id == account_id))
        acc = row.scalar_one_or_none()
        if not acc:
            raise ServiceOSException("ACCOUNT_NOT_FOUND", "Social account not found.", status_code=404)
        acc.last_refreshed_at = utcnow()
        await self.db.flush()
        return {"account_id": str(acc.id), "synced_at": acc.last_refreshed_at.isoformat()}

    async def disconnect_social_account(self, account_id: uuid.UUID) -> dict[str, Any]:
        row = await self.db.execute(select(SocialAccount).where(SocialAccount.id == account_id))
        acc = row.scalar_one_or_none()
        if not acc:
            raise ServiceOSException("ACCOUNT_NOT_FOUND", "Social account not found.", status_code=404)
        acc.status = "disconnected"
        await self.db.flush()
        await self._audit("marketing.social_account.disconnected", "social_account", str(acc.id))
        return {"account_id": str(acc.id), "status": acc.status}

    # ── Content templates (Part J) ───────────────────────────────────────────

    async def list_templates(self) -> dict[str, Any]:
        rows = (await self.db.execute(select(MarketingContentTemplateV2)
            .order_by(desc(MarketingContentTemplateV2.created_at)))).scalars().all()
        return {"items": [r.to_dict() for r in rows]}

    async def create_template(self, data: dict[str, Any]) -> dict[str, Any]:
        tpl = MarketingContentTemplateV2(
            template_name=data["template_name"], vertical_key=data.get("vertical_key"),
            post_type=data.get("post_type", "image_post"), language=data.get("language", "english"),
            prompt_template=data.get("prompt_template"), caption_structure=data.get("caption_structure"),
            hashtag_set_json=data.get("hashtag_set"), cta=data.get("cta"),
            created_by_user_id=self.actor_id,
        )
        self.db.add(tpl)
        await self.db.flush()
        await self._audit("marketing.template.created", "template", str(tpl.id))
        return tpl.to_dict()

    async def update_template(self, template_id: uuid.UUID, data: dict[str, Any]) -> dict[str, Any]:
        row = await self.db.execute(select(MarketingContentTemplateV2).where(MarketingContentTemplateV2.id == template_id))
        tpl = row.scalar_one_or_none()
        if not tpl:
            raise ServiceOSException("TEMPLATE_NOT_FOUND", "Content template not found.", status_code=404)
        old = tpl.to_dict()
        for field in ("template_name", "prompt_template", "caption_structure", "cta", "status"):
            if field in data:
                setattr(tpl, field, data[field])
        if "hashtag_set" in data:
            tpl.hashtag_set_json = data["hashtag_set"]
        tpl.updated_at = utcnow()
        await self.db.flush()
        await self._audit("marketing.template.updated", "template", str(tpl.id), old, tpl.to_dict())
        return tpl.to_dict()

    # ── Publish failures (Part K) ────────────────────────────────────────────

    async def list_publish_failures(self, limit: int = 50) -> dict[str, Any]:
        rows = (await self.db.execute(
            select(MarketingPublishAttempt).where(MarketingPublishAttempt.status == "failed")
            .order_by(desc(MarketingPublishAttempt.created_at)).limit(limit))).scalars().all()
        return {"items": [r.to_dict() for r in rows]}

    # ── Analytics (Part L) ───────────────────────────────────────────────────

    async def get_analytics_summary(self) -> dict[str, Any]:
        published_row = await self.db.execute(
            select(func.count()).select_from(MarketingPost).where(MarketingPost.status == "published"))
        published = published_row.scalar() or 0
        if published == 0:
            return {"available": False,
                    "message": "Analytics not available yet. Connect accounts with insights permissions to view performance data."}
        return {
            "available": True, "impressions": 0, "reach": 0, "engagement": 0, "clicks": 0,
            "leads_generated": 0, "bookings_generated": 0, "cost_per_post": 0, "cost_per_lead": 0,
            "best_channel": None, "best_campaign": None, "best_vertical": None,
        }

    async def get_top_posts(self) -> dict[str, Any]:
        return {"items": [], "available": False}

    async def get_campaign_performance(self) -> dict[str, Any]:
        return {"items": [], "available": False}

    async def get_channel_performance(self) -> dict[str, Any]:
        return {"items": [], "available": False}

    # ── Audit logs ───────────────────────────────────────────────────────────

    async def list_audit_logs(self, limit: int = 50) -> dict[str, Any]:
        rows = (await self.db.execute(
            select(MarketingAuditLog).order_by(desc(MarketingAuditLog.created_at)).limit(limit))).scalars().all()
        return {"items": [r.to_dict() for r in rows]}
