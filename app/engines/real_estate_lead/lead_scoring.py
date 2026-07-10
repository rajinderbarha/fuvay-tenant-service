"""Sprint 18 — Real Estate Lead Scoring Service.

Scores a lead draft based on completeness and intent signals.
Score is admin/provider-internal — customer sees safe label only.
"""
from __future__ import annotations
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.real_estate_lead.constants import (
    SCORE_COLD, SCORE_WARM, SCORE_HOT,
    SCORE_THRESHOLD_WARM, SCORE_THRESHOLD_HOT,
    ERR_LEAD_SCORE_FAILED,
)

logger = structlog.get_logger("real_estate.lead_scoring")


class RealEstateLeadScoringService:
    """
    Calculates a lead score from 0–100 based on field completeness.

    Scoring rules:
    +20  phone provided
    +10  email provided
    +20  budget/rent range provided
    +15  locality provided (more specific = better)
    +10  property_type provided
    +10  bedrooms or area provided
    +15  preferred_contact_time provided
    """

    SCORING_RULES = [
        ("customer_phone",         20, "Phone number provided"),
        ("customer_email",         10, "Email address provided"),
        ("budget_or_rent",         20, "Budget / rent range provided"),
        ("locality",               15, "Locality specified"),
        ("property_type",          10, "Property type provided"),
        ("bedrooms_or_area",       10, "Bedroom count or area provided"),
        ("preferred_contact_time", 15, "Preferred contact time provided"),
    ]

    def __init__(self, db: AsyncSession):
        self.db = db

    def calculate_from_draft(self, draft) -> dict:
        """
        Calculate score from a RealEstateLeadDraft object (in-memory, no DB write).
        Returns score dict with factors list.
        """
        score    = 0
        factors  = []

        # Phone
        if draft.customer_phone:
            score += 20
            factors.append({"field": "customer_phone", "points": 20, "reason": "Phone number provided"})

        # Email
        if draft.customer_email:
            score += 10
            factors.append({"field": "customer_email", "points": 10, "reason": "Email address provided"})

        # Budget / rent
        has_budget = (draft.budget_min is not None or draft.budget_max is not None)
        has_rent   = (draft.rent_min   is not None or draft.rent_max   is not None)
        if has_budget or has_rent:
            score += 20
            factors.append({"field": "budget_or_rent", "points": 20, "reason": "Budget / rent range provided"})

        # Locality (more specific than city)
        if draft.locality:
            score += 15
            factors.append({"field": "locality", "points": 15, "reason": "Locality specified"})

        # Property type
        if draft.property_type:
            score += 10
            factors.append({"field": "property_type", "points": 10, "reason": "Property type provided"})

        # Bedrooms or area
        has_rooms = draft.bedrooms is not None
        has_area  = (draft.area_sqft_min is not None or draft.area_sqft_max is not None)
        if has_rooms or has_area:
            score += 10
            factors.append({"field": "bedrooms_or_area", "points": 10, "reason": "Bedroom count or area provided"})

        # Preferred contact time
        if draft.preferred_contact_time:
            score += 15
            factors.append({"field": "preferred_contact_time", "points": 15, "reason": "Preferred contact time provided"})

        score = min(score, 100)
        label = self._score_to_label(score)

        return {
            "score":        score,
            "score_label":  label,
            "score_factors": factors,
            "max_score":    100,
        }

    def _score_to_label(self, score: int) -> str:
        if score >= SCORE_THRESHOLD_HOT:
            return SCORE_HOT
        if score >= SCORE_THRESHOLD_WARM:
            return SCORE_WARM
        return SCORE_COLD

    async def calculate_and_persist(self, draft, draft_id: uuid.UUID) -> dict:
        """Calculate score and upsert RealEstateLeadScore row."""
        try:
            from app.engines.real_estate_lead.models import RealEstateLeadScore
            from sqlalchemy import select

            score_dict = self.calculate_from_draft(draft)

            existing_q = select(RealEstateLeadScore).where(
                RealEstateLeadScore.draft_id == draft_id
            )
            existing = (await self.db.execute(existing_q)).scalars().first()

            if existing:
                existing.score         = score_dict["score"]
                existing.score_label   = score_dict["score_label"]
                existing.score_factors = score_dict["score_factors"]
                self.db.add(existing)
            else:
                row = RealEstateLeadScore(
                    draft_id     = draft_id,
                    score        = score_dict["score"],
                    score_label  = score_dict["score_label"],
                    score_factors= score_dict["score_factors"],
                )
                self.db.add(row)

            await self.db.flush()
            return score_dict

        except Exception as exc:
            logger.warning("real_estate.scoring.persist_failed", error=str(exc))
            return self.calculate_from_draft(draft)
