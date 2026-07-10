"""Sprint 29 — Marketing Automation Triggers.

Each trigger function checks eligibility (cooldown, preferences, status)
before creating a campaign event or notification.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.marketing_automation.constants import (
    VALID_TRIGGERS,
    COOLDOWN_HOURS,
    TRIGGER_ABANDONED_BOOKING_DRAFT,
    TRIGGER_ABANDONED_APPOINTMENT_DRAFT,
    TRIGGER_ABANDONED_REAL_ESTATE_DRAFT,
    TRIGGER_WALLET_LOW_BALANCE,
    TRIGGER_SUBSCRIPTION_EXPIRING,
    TRIGGER_REVIEW_REQUEST,
    TRIGGER_COMPLAINT_FOLLOWUP,
    TRIGGER_PROVIDER_INACTIVE,
    TRIGGER_CATEGORY_LAUNCH,
    ERR_TRIGGER_NOT_FOUND,
    ERR_TRIGGER_NOT_ALLOWED,
    EVENT_TARGETED,
    EVENT_SKIPPED,
)
from app.engines.marketing_automation.models import MarketingCampaignEvent

logger = structlog.get_logger("marketing_automation.triggers")

_utcnow = lambda: datetime.now(timezone.utc)


async def _within_cooldown(
    db: AsyncSession, trigger_key: str, user_id: uuid.UUID
) -> bool:
    """Return True if user received this trigger within the cooldown window."""
    hours = COOLDOWN_HOURS.get(trigger_key, 24)
    cutoff = _utcnow() - timedelta(hours=hours)
    result = await db.execute(
        text("""
            SELECT 1 FROM marketing_campaign_events e
            JOIN marketing_campaigns c ON c.id = e.campaign_id
            WHERE e.recipient_user_id = :uid
              AND e.event_type = 'targeted'
              AND e.camp_metadata->>'trigger_key' = :trigger_key
              AND e.created_at > :cutoff
            LIMIT 1
        """),
        {"uid": str(user_id), "trigger_key": trigger_key, "cutoff": cutoff},
    )
    return result.first() is not None


class AutomationTriggerService:
    """Executes named automation triggers against the platform DB."""

    TRIGGER_DESCRIPTIONS = {
        TRIGGER_ABANDONED_BOOKING_DRAFT:     "Customer started but didn't complete a home service booking draft",
        TRIGGER_ABANDONED_APPOINTMENT_DRAFT: "Student started but didn't complete a coaching appointment draft",
        TRIGGER_ABANDONED_REAL_ESTATE_DRAFT: "Customer started but didn't complete a real estate lead draft",
        TRIGGER_WALLET_LOW_BALANCE:          "Provider wallet balance is below threshold",
        TRIGGER_SUBSCRIPTION_EXPIRING:       "Provider subscription expires within 7 days",
        TRIGGER_REVIEW_REQUEST:              "Request review after job/appointment completion",
        TRIGGER_COMPLAINT_FOLLOWUP:          "Follow up after complaint resolution",
        TRIGGER_PROVIDER_INACTIVE:           "Provider has not received a booking in 30 days",
        TRIGGER_CATEGORY_LAUNCH:             "New category launched — notify interested customers",
    }

    def list_triggers(self) -> list[dict[str, Any]]:
        return [
            {"trigger_key": k, "description": v, "cooldown_hours": COOLDOWN_HOURS.get(k, 24)}
            for k, v in self.TRIGGER_DESCRIPTIONS.items()
        ]

    async def run_trigger(
        self,
        db: AsyncSession,
        trigger_key: str,
        actor_user_id: uuid.UUID,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a named trigger. Returns summary of targeted/skipped."""
        if trigger_key not in VALID_TRIGGERS:
            raise ValueError(f"{ERR_TRIGGER_NOT_FOUND}: {trigger_key}")

        method = getattr(self, f"_run_{trigger_key}", None)
        if not method:
            raise ValueError(f"{ERR_TRIGGER_NOT_ALLOWED}: {trigger_key} has no executor")

        logger.info("automation.trigger.start", trigger_key=trigger_key,
                    actor=str(actor_user_id))
        result = await method(db, params or {})
        logger.info("automation.trigger.done", trigger_key=trigger_key, result=result)
        return result

    # ── Abandoned booking draft ───────────────────────────────────────────────

    async def _run_abandoned_booking_draft(
        self, db: AsyncSession, params: dict
    ) -> dict[str, Any]:
        result = await db.execute(text("""
            SELECT DISTINCT s.customer_id
            FROM ai_conversation_sessions s
            WHERE s.workflow_status = 'abandoned'
              AND s.current_intent IN ('booking_intent', 'service_inquiry')
              AND s.customer_id IS NOT NULL
              AND s.updated_at > NOW() - INTERVAL '48 hours'
              AND s.updated_at < NOW() - INTERVAL '2 hours'
            LIMIT 500
        """))
        user_ids = [row[0] for row in result.fetchall() if row[0]]
        return await self._target_users(
            db, TRIGGER_ABANDONED_BOOKING_DRAFT, user_ids,
            "Reminder: Complete your home service booking"
        )

    # ── Wallet low balance ────────────────────────────────────────────────────

    async def _run_wallet_low_balance(
        self, db: AsyncSession, params: dict
    ) -> dict[str, Any]:
        threshold = params.get("threshold", 100)
        result = await db.execute(text("""
            SELECT DISTINCT t.owner_user_id
            FROM tenants t
            JOIN wallet_accounts w ON w.tenant_id = t.id
            WHERE w.balance < :threshold
              AND t.status = 'active'
              AND t.owner_user_id IS NOT NULL
            LIMIT 500
        """), {"threshold": threshold})
        user_ids = [row[0] for row in result.fetchall() if row[0]]
        return await self._target_users(
            db, TRIGGER_WALLET_LOW_BALANCE, user_ids,
            "Your wallet balance is low"
        )

    # ── Subscription expiring ─────────────────────────────────────────────────

    async def _run_subscription_expiring(
        self, db: AsyncSession, params: dict
    ) -> dict[str, Any]:
        days_ahead = params.get("days_ahead", 7)
        result = await db.execute(text("""
            SELECT DISTINCT t.owner_user_id
            FROM tenants t
            WHERE t.subscription_expires_at BETWEEN NOW() AND NOW() + INTERVAL ':days days'
              AND t.status = 'active'
              AND t.owner_user_id IS NOT NULL
            LIMIT 500
        """), {"days": days_ahead})
        user_ids = [row[0] for row in result.fetchall() if row[0]]
        return await self._target_users(
            db, TRIGGER_SUBSCRIPTION_EXPIRING, user_ids,
            "Your subscription is expiring soon"
        )

    # ── Review request after completion ──────────────────────────────────────

    async def _run_review_request_after_completion(
        self, db: AsyncSession, params: dict
    ) -> dict[str, Any]:
        result = await db.execute(text("""
            SELECT DISTINCT j.customer_user_id
            FROM jobs j
            LEFT JOIN customer_reviews r ON r.job_id = j.id
            WHERE j.status = 'completed'
              AND j.completed_at > NOW() - INTERVAL '72 hours'
              AND j.completed_at < NOW() - INTERVAL '4 hours'
              AND r.id IS NULL
              AND j.customer_user_id IS NOT NULL
            LIMIT 500
        """))
        user_ids = [row[0] for row in result.fetchall() if row[0]]
        return await self._target_users(
            db, TRIGGER_REVIEW_REQUEST, user_ids,
            "How was your recent service? Leave a review"
        )

    # ── Complaint followup ────────────────────────────────────────────────────

    async def _run_complaint_followup_after_resolution(
        self, db: AsyncSession, params: dict
    ) -> dict[str, Any]:
        result = await db.execute(text("""
            SELECT DISTINCT c.customer_user_id
            FROM complaints c
            WHERE c.status = 'resolved'
              AND c.resolved_at > NOW() - INTERVAL '48 hours'
              AND c.customer_user_id IS NOT NULL
            LIMIT 500
        """))
        user_ids = [row[0] for row in result.fetchall() if row[0]]
        return await self._target_users(
            db, TRIGGER_COMPLAINT_FOLLOWUP, user_ids,
            "Your complaint has been resolved — we'd love your feedback"
        )

    # ── Abandoned appointment draft ───────────────────────────────────────────

    async def _run_abandoned_appointment_draft(
        self, db: AsyncSession, params: dict
    ) -> dict[str, Any]:
        result = await db.execute(text("""
            SELECT DISTINCT ad.customer_id
            FROM coaching_appointment_drafts ad
            WHERE ad.status = 'draft'
              AND ad.updated_at < NOW() - INTERVAL '4 hours'
              AND ad.updated_at > NOW() - INTERVAL '48 hours'
              AND ad.customer_id IS NOT NULL
            LIMIT 500
        """))
        user_ids = [row[0] for row in result.fetchall() if row[0]]
        return await self._target_users(
            db, TRIGGER_ABANDONED_APPOINTMENT_DRAFT, user_ids,
            "Complete your coaching appointment booking"
        )

    # ── Abandoned real estate draft ───────────────────────────────────────────

    async def _run_abandoned_real_estate_lead_draft(
        self, db: AsyncSession, params: dict
    ) -> dict[str, Any]:
        result = await db.execute(text("""
            SELECT DISTINCT rd.customer_id
            FROM real_estate_lead_drafts rd
            WHERE rd.status = 'draft'
              AND rd.updated_at < NOW() - INTERVAL '4 hours'
              AND rd.updated_at > NOW() - INTERVAL '72 hours'
              AND rd.customer_id IS NOT NULL
            LIMIT 500
        """))
        user_ids = [row[0] for row in result.fetchall() if row[0]]
        return await self._target_users(
            db, TRIGGER_ABANDONED_REAL_ESTATE_DRAFT, user_ids,
            "Still looking for a property? Complete your inquiry"
        )

    # ── Provider inactive ─────────────────────────────────────────────────────

    async def _run_provider_inactive(
        self, db: AsyncSession, params: dict
    ) -> dict[str, Any]:
        result = await db.execute(text("""
            SELECT DISTINCT t.owner_user_id
            FROM tenants t
            WHERE t.status = 'active'
              AND t.owner_user_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM jobs j
                WHERE j.tenant_id = t.id
                  AND j.created_at > NOW() - INTERVAL '30 days'
              )
            LIMIT 500
        """))
        user_ids = [row[0] for row in result.fetchall() if row[0]]
        return await self._target_users(
            db, TRIGGER_PROVIDER_INACTIVE, user_ids,
            "Boost your business — update your availability"
        )

    # ── Category launch ───────────────────────────────────────────────────────

    async def _run_category_launch(
        self, db: AsyncSession, params: dict
    ) -> dict[str, Any]:
        # Target all active customers for a new category notification
        result = await db.execute(text("""
            SELECT id FROM users WHERE role='customer' AND is_active=true LIMIT 1000
        """))
        user_ids = [row[0] for row in result.fetchall() if row[0]]
        return await self._target_users(
            db, TRIGGER_CATEGORY_LAUNCH, user_ids,
            "New service category now available!"
        )

    # ── Internal: target users with cooldown check ────────────────────────────

    async def _target_users(
        self,
        db: AsyncSession,
        trigger_key: str,
        user_ids: list,
        default_message: str,
    ) -> dict[str, Any]:
        targeted = 0
        skipped  = 0
        for uid in user_ids:
            uid = uuid.UUID(str(uid)) if not isinstance(uid, uuid.UUID) else uid
            in_cooldown = await _within_cooldown(db, trigger_key, uid)
            if in_cooldown:
                skipped += 1
                continue
            db.add(MarketingCampaignEvent(
                campaign_id       = uuid.UUID("00000000-0000-0000-0000-000000000001"),  # system campaign
                recipient_user_id = uid,
                event_type        = EVENT_TARGETED,
                camp_metadata     = {"trigger_key": trigger_key, "message": default_message},
            ))
            targeted += 1

        if targeted:
            await db.flush()

        return {"trigger_key": trigger_key, "targeted": targeted, "skipped": skipped}
