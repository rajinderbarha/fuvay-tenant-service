"""Sprint 29 — MarketingSegmentService.

Builds recipient lists from segment rules. Uses raw SQL against existing tables.
Does NOT target suspended users/providers unless admin explicitly sets allow_suspended=true.
"""
from __future__ import annotations
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.marketing_automation.constants import (
    SEGMENT_PREVIEW_MAX,
    ERR_SEGMENT_INVALID,
    ERR_SEGMENT_TOO_LARGE,
    AUDIENCE_CUSTOMERS,
    AUDIENCE_PROVIDERS,
)


# ── Supported filter keys per audience ────────────────────────────────────────
CUSTOMER_SEGMENT_FILTERS = {
    "city", "zone_id", "booking_count_min", "booking_count_max",
    "last_booking_days_ago", "has_abandoned_draft", "has_open_complaint",
    "has_submitted_review", "category_id",
}

PROVIDER_SEGMENT_FILTERS = {
    "city", "zone_id", "category_id", "verification_status",
    "wallet_balance_max", "subscription_status", "rating_min",
    "complaint_rate_max", "is_bookable", "is_visible",
    "allow_suspended",
}


class MarketingSegmentService:
    """Resolves segment rules into a list of user_ids."""

    # ── 1. Build customer segment ─────────────────────────────────────────────

    async def build_customer_segment(
        self, db: AsyncSession, rules: dict[str, Any]
    ) -> list[uuid.UUID]:
        """
        Returns list of user_ids matching customer segment rules.
        Rules come from campaign rule_config with rule_type='segment'.
        """
        params: dict[str, Any] = {}
        conditions = ["u.is_active = true", "u.role = 'customer'"]

        if rules.get("city"):
            conditions.append("u.city ILIKE :city")
            params["city"] = f"%{rules['city']}%"

        if rules.get("category_id"):
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM bookings b
                    WHERE b.customer_id = u.id
                      AND b.category_id = :category_id::uuid
                )
            """)
            params["category_id"] = str(rules["category_id"])

        if rules.get("has_abandoned_draft"):
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM ai_conversation_sessions s
                    WHERE s.customer_id = u.id
                      AND s.workflow_status = 'abandoned'
                      AND s.created_at > NOW() - INTERVAL '7 days'
                )
            """)

        sql = f"""
            SELECT u.id FROM users u
            WHERE {' AND '.join(conditions)}
            LIMIT 5000
        """
        result = await db.execute(text(sql), params)
        return [row[0] for row in result.fetchall()]

    # ── 2. Build provider segment ─────────────────────────────────────────────

    async def build_provider_segment(
        self, db: AsyncSession, rules: dict[str, Any]
    ) -> list[uuid.UUID]:
        """Returns list of tenant owner user_ids matching provider segment rules."""
        params: dict[str, Any] = {}
        conditions = ["t.status != 'suspended'"]

        if not rules.get("allow_suspended"):
            conditions.append("t.status != 'suspended'")

        if rules.get("city"):
            conditions.append("t.city ILIKE :city")
            params["city"] = f"%{rules['city']}%"

        if rules.get("category_id"):
            conditions.append("t.primary_category_id = :category_id::uuid")
            params["category_id"] = str(rules["category_id"])

        if rules.get("is_bookable") is not None:
            conditions.append("t.is_bookable = :is_bookable")
            params["is_bookable"] = bool(rules["is_bookable"])

        if rules.get("subscription_status"):
            conditions.append("t.subscription_status = :subscription_status")
            params["subscription_status"] = rules["subscription_status"]

        sql = f"""
            SELECT t.owner_user_id FROM tenants t
            WHERE {' AND '.join(conditions)}
              AND t.owner_user_id IS NOT NULL
            LIMIT 5000
        """
        result = await db.execute(text(sql), params)
        return [row[0] for row in result.fetchall()]

    # ── 3. Validate segment rules ─────────────────────────────────────────────

    def validate_segment_rules(self, rules: dict[str, Any], audience: str) -> list[str]:
        """Returns list of validation errors (empty = valid)."""
        errors: list[str] = []
        allowed = CUSTOMER_SEGMENT_FILTERS if audience == AUDIENCE_CUSTOMERS else PROVIDER_SEGMENT_FILTERS
        for key in rules:
            if key not in allowed:
                errors.append(f"Unsupported segment filter for {audience}: {key}")
        return errors

    # ── 4. Estimate segment size ──────────────────────────────────────────────

    async def estimate_segment_size(
        self, db: AsyncSession, rules: dict[str, Any], audience: str
    ) -> int:
        if audience == AUDIENCE_CUSTOMERS:
            ids = await self.build_customer_segment(db, rules)
        else:
            ids = await self.build_provider_segment(db, rules)
        return len(ids)

    # ── 5. Preview segment ────────────────────────────────────────────────────

    async def preview_segment(
        self, db: AsyncSession, rules: dict[str, Any], audience: str
    ) -> dict[str, Any]:
        """Returns capped preview + estimated total."""
        errors = self.validate_segment_rules(rules, audience)
        if errors:
            raise ValueError(f"{ERR_SEGMENT_INVALID}: {'; '.join(errors)}")

        if audience == AUDIENCE_CUSTOMERS:
            ids = await self.build_customer_segment(db, rules)
        else:
            ids = await self.build_provider_segment(db, rules)

        estimated = len(ids)
        preview   = [str(i) for i in ids[:SEGMENT_PREVIEW_MAX]]

        return {
            "audience":        audience,
            "estimated_total": estimated,
            "preview_count":   len(preview),
            "preview_ids":     preview,
            "rules_applied":   rules,
        }
