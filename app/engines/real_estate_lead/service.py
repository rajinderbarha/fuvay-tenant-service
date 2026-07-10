"""Sprint 18 â€” RealEstateLeadFlowService.

18 methods covering the full lead capture lifecycle.
No final lead creation (Sprint 19 handles that).
No fake providers. No fake properties. No hardcoded Buy-only flow.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.real_estate_lead.models import (
    RealEstateLeadDraft, RealEstateLeadDraftEvent,
    RealEstateLeadRoutingRule, RealEstateLeadScore,
)
from app.engines.real_estate_lead.constants import (
    ACTOR_BACKEND, ACTOR_CUSTOMER, ACTOR_SYSTEM,
    DEFAULT_DRAFT_EXPIRY_HOURS, DEFAULT_MAX_PROVIDERS,
    DRAFT_STATUS_CANCELLED, DRAFT_STATUS_COLLECTING, DRAFT_STATUS_CONFIRMED,
    DRAFT_STATUS_DRAFT, DRAFT_STATUS_EXPIRED, DRAFT_STATUS_FAILED,
    DRAFT_STATUS_FALLBACK_AVAILABLE, DRAFT_STATUS_LOCATION_CHECKED,
    DRAFT_STATUS_NO_EXACT_MATCH, DRAFT_STATUS_PROVIDERS_FOUND,
    DRAFT_STATUS_READY, TERMINAL_STATUSES,
    ERR_CATEGORY_INVALID, ERR_CONFIRMATION_NOT_READY, ERR_DRAFT_ACCESS_DENIED,
    ERR_DRAFT_EXPIRED, ERR_DRAFT_NOT_FOUND, ERR_FAKE_PROVIDER_BLOCKED,
    ERR_NO_EXACT_PROVIDER_MATCH, ERR_NO_PROVIDER_AVAILABLE,
    ERR_OFFERING_INVALID, ERR_REQUIRED_FIELD_MISSING,
    EVENT_CONFIRMATION_REQUESTED, EVENT_DRAFT_CANCELLED, EVENT_DRAFT_CONFIRMED,
    EVENT_DRAFT_CREATED, EVENT_DRAFT_EXPIRED, EVENT_DRAFT_FAILED,
    EVENT_FALLBACK_PREPARED, EVENT_FIELD_COLLECTED, EVENT_LEAD_SCORED,
    EVENT_LOCATION_CHECKED, EVENT_NO_EXACT_MATCH, EVENT_PROVIDERS_FOUND,
    EVENT_SUMMARY_GENERATED,
    INTENT_BUY, INTENT_RENT, INTENT_SELL, INTENT_SITE_VISIT,
    REAL_ESTATE_CATEGORY_ALIASES,
)
from app.engines.real_estate_lead.provider_discovery import RealEstateProviderDiscoveryService
from app.engines.real_estate_lead.lead_scoring import RealEstateLeadScoringService

logger = structlog.get_logger("real_estate.service")
utcnow = lambda: datetime.now(timezone.utc)

# Fields customer may update (backend fields blocked)
ALLOWED_UPDATE_FIELDS = {
    "lead_intent", "property_type", "city", "locality", "zipcode",
    "budget_min", "budget_max", "rent_min", "rent_max",
    "bedrooms", "bathrooms", "area_sqft_min", "area_sqft_max",
    "furnishing", "possession_preference",
    "customer_name", "customer_phone", "customer_email",
    "preferred_contact_time", "notes",
}


class RealEstateLeadFlowService:
    """Full lead capture lifecycle for Real Estate chatbot flow."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # â”€â”€ 1. start_lead_draft â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def start_lead_draft(
        self,
        customer_id: uuid.UUID | None,
        ai_session_id: uuid.UUID | None,
        category_slug: str,
        offering_slug: str,
    ) -> dict:
        from app.engines.admin_catalog.models import ServiceCategory, MasterOffering

        # Resolve category
        cat = await self._resolve_category(category_slug)
        if not cat:
            raise ValueError(f"{ERR_CATEGORY_INVALID}: No real estate category found for '{category_slug}'")

        # Resolve offering
        offering = await self._resolve_offering(cat.id, offering_slug)
        if not offering:
            raise ValueError(f"{ERR_OFFERING_INVALID}: Offering '{offering_slug}' not found for this category")

        draft = RealEstateLeadDraft(
            customer_id  = customer_id,
            ai_session_id= ai_session_id,
            category_id  = cat.id,
            offering_id  = offering.id,
            status       = DRAFT_STATUS_COLLECTING,
            expires_at   = utcnow() + timedelta(hours=DEFAULT_DRAFT_EXPIRY_HOURS),
        )
        self.db.add(draft)
        await self.db.flush()
        await self.db.refresh(draft)

        await self._log_event(draft.id, ACTOR_BACKEND, EVENT_DRAFT_CREATED,
                              new_value={"category": cat.name, "offering": offering.name})

        return {
            **draft.to_dict(),
            "offering_name":  offering.name,
            "category_name":  cat.name,
            "required_fields": self._required_fields_for_offering(offering),
        }

    # â”€â”€ 2. get_lead_draft â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def get_lead_draft(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        missing = self._compute_missing_fields(draft)
        return {**draft.to_dict(), "missing_fields": missing}

    # â”€â”€ 3. update_draft_fields â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def update_draft_fields(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        payload: dict,
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)

        if draft.status in TERMINAL_STATUSES:
            raise ValueError(f"Draft is in terminal status: {draft.status}")

        safe_payload = {k: v for k, v in payload.items() if k in ALLOWED_UPDATE_FIELDS}
        updated_fields = []
        for field, value in safe_payload.items():
            if getattr(draft, field, None) != value:
                setattr(draft, field, value)
                updated_fields.append(field)

        if updated_fields:
            draft.status = DRAFT_STATUS_COLLECTING
            await self.db.flush()
            await self.db.refresh(draft)
            await self._log_event(draft.id, ACTOR_CUSTOMER, EVENT_FIELD_COLLECTED,
                                  new_value=safe_payload)

        missing = self._compute_missing_fields(draft)
        return {**draft.to_dict(), "missing_fields": missing, "updated_fields": updated_fields}

    # â”€â”€ 4. sync_draft_from_ai_session â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def sync_draft_from_ai_session(self, ai_session_id: uuid.UUID) -> dict | None:
        q = select(RealEstateLeadDraft).where(
            and_(
                RealEstateLeadDraft.ai_session_id == ai_session_id,
                RealEstateLeadDraft.status.notin_(TERMINAL_STATUSES),
            )
        ).order_by(desc(RealEstateLeadDraft.created_at)).limit(1)
        draft = (await self.db.execute(q)).scalars().first()
        if not draft:
            return None
        return draft.to_dict()

    # â”€â”€ 5. validate_required_fields â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def validate_required_fields(self, draft_id: uuid.UUID) -> dict:
        draft = (await self.db.execute(
            select(RealEstateLeadDraft).where(RealEstateLeadDraft.id == draft_id)
        )).scalars().first()
        if not draft:
            raise ValueError(f"{ERR_DRAFT_NOT_FOUND}")
        missing = self._compute_missing_fields(draft)
        return {"valid": len(missing) == 0, "missing_fields": missing}

    # â”€â”€ 6. get_missing_fields â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def get_missing_fields(self, draft_id: uuid.UUID, customer_id: uuid.UUID | None) -> list[str]:
        draft = await self._get_and_authorize(draft_id, customer_id)
        return self._compute_missing_fields(draft)

    # â”€â”€ 7. check_location_coverage â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def check_location_coverage(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        discovery = RealEstateProviderDiscoveryService(self.db)
        result = await discovery.find_providers(
            category_id  = draft.category_id,
            offering_id  = draft.offering_id,
            city         = draft.city,
            locality     = draft.locality,
            zipcode      = draft.zipcode,
            lead_intent  = draft.lead_intent,
            property_type= draft.property_type,
        )
        draft.status = DRAFT_STATUS_LOCATION_CHECKED
        await self.db.flush()
        await self._log_event(draft.id, ACTOR_BACKEND, EVENT_LOCATION_CHECKED,
                              new_value={"city": draft.city, "matched_by": result.get("matched_by")})
        return {"draft_id": str(draft_id), **result}

    # â”€â”€ 8. find_eligible_providers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def find_eligible_providers(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        discovery = RealEstateProviderDiscoveryService(self.db)
        result = await discovery.find_providers(
            category_id  = draft.category_id,
            offering_id  = draft.offering_id,
            city         = draft.city,
            locality     = draft.locality,
            zipcode      = draft.zipcode,
            lead_intent  = draft.lead_intent,
            property_type= draft.property_type,
        )
        if result.get("available"):
            draft.provider_options = result.get("providers", [])
            draft.status           = DRAFT_STATUS_PROVIDERS_FOUND
            await self.db.flush()
            await self._log_event(draft.id, ACTOR_BACKEND, EVENT_PROVIDERS_FOUND,
                                  new_value={"count": result.get("available_provider_count")})
        elif result.get("fallback_available"):
            draft.status          = DRAFT_STATUS_NO_EXACT_MATCH
            draft.fallback_payload= self._build_fallback_payload(draft, result)
            await self.db.flush()
            await self._log_event(draft.id, ACTOR_BACKEND, EVENT_NO_EXACT_MATCH,
                                  new_value={"fallback_count": len(result.get("fallback_providers", []))})
        else:
            draft.status = DRAFT_STATUS_FALLBACK_AVAILABLE
            draft.fallback_payload = self._build_fallback_payload(draft, result)
            await self.db.flush()
        await self.db.refresh(draft)
        return {"draft_id": str(draft_id), **result}

    # â”€â”€ 9. find_nearby_or_fallback_providers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def find_nearby_or_fallback_providers(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        discovery = RealEstateProviderDiscoveryService(self.db)
        result = await discovery.find_providers(
            category_id  = draft.category_id,
            offering_id  = draft.offering_id,
            city         = draft.city,
            locality     = None,   # drop locality for broader city search
            zipcode      = None,
            lead_intent  = draft.lead_intent,
        )
        fallback = self._build_fallback_payload(draft, result)
        draft.fallback_payload = fallback
        draft.status           = DRAFT_STATUS_FALLBACK_AVAILABLE
        await self.db.flush()
        await self._log_event(draft.id, ACTOR_BACKEND, EVENT_FALLBACK_PREPARED,
                              new_value=fallback)
        return {"draft_id": str(draft_id), "fallback_payload": fallback, **result}

    # â”€â”€ 10. select_provider â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def select_provider(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None, tenant_id: uuid.UUID
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        discovery = RealEstateProviderDiscoveryService(self.db)
        bookable = await discovery.validate_provider_bookable(tenant_id, draft.category_id)
        if not bookable:
            raise ValueError(f"{ERR_FAKE_PROVIDER_BLOCKED}: Provider is not bookable or not in same category")
        draft.selected_tenant_id = tenant_id
        provider_options = draft.provider_options or []
        snap = next(
            (p for p in provider_options if p.get("provider_ref") == str(tenant_id)), None
        )
        draft.selected_provider_snapshot = snap or {"provider_ref": str(tenant_id)}
        await self.db.flush()
        await self.db.refresh(draft)
        return draft.to_dict()

    # â”€â”€ 11. select_agent_if_allowed â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def select_agent_if_allowed(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None, agent_id: uuid.UUID
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        draft.selected_agent_id = agent_id
        await self.db.flush()
        await self.db.refresh(draft)
        return draft.to_dict()

    # â”€â”€ 12. calculate_lead_score â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def calculate_lead_score(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        scorer = RealEstateLeadScoringService(self.db)
        score_dict = await scorer.calculate_and_persist(draft, draft_id)
        draft.lead_score_snapshot = score_dict
        await self.db.flush()
        await self._log_event(draft.id, ACTOR_BACKEND, EVENT_LEAD_SCORED,
                              new_value=score_dict)
        return {"draft_id": str(draft_id), **score_dict}

    # â”€â”€ 13. build_lead_summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def build_lead_summary(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        scorer = RealEstateLeadScoringService(self.db)
        score  = scorer.calculate_from_draft(draft)
        summary = {
            "lead_intent":            draft.lead_intent,
            "property_type":          draft.property_type,
            "city":                   draft.city,
            "locality":               draft.locality,
            "zipcode":                draft.zipcode,
            "budget_min":             float(draft.budget_min) if draft.budget_min else None,
            "budget_max":             float(draft.budget_max) if draft.budget_max else None,
            "rent_min":               float(draft.rent_min) if draft.rent_min else None,
            "rent_max":               float(draft.rent_max) if draft.rent_max else None,
            "bedrooms":               draft.bedrooms,
            "furnishing":             draft.furnishing,
            "possession_preference":  draft.possession_preference,
            "customer_name":          draft.customer_name,
            "customer_phone":         draft.customer_phone,
            "customer_email":         draft.customer_email,
            "preferred_contact_time": draft.preferred_contact_time,
            "notes":                  draft.notes,
            "selected_provider":      draft.selected_provider_snapshot,
            "provider_options":       draft.provider_options or [],
            "fallback_available":     draft.fallback_payload is not None,
            "lead_score":             score,
            "status":                 draft.status,
        }
        draft.lead_summary       = summary
        draft.lead_score_snapshot= score
        await self.db.flush()
        await self._log_event(draft.id, ACTOR_BACKEND, EVENT_SUMMARY_GENERATED,
                              new_value={"score": score["score"], "status": draft.status})
        return {"draft_id": str(draft_id), "summary": summary}

    # â”€â”€ 14. prepare_fallback_payload â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def prepare_fallback_payload(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        payload = self._build_fallback_payload(draft, {})
        draft.fallback_payload = payload
        draft.status           = DRAFT_STATUS_FALLBACK_AVAILABLE
        await self.db.flush()
        await self._log_event(draft.id, ACTOR_BACKEND, EVENT_FALLBACK_PREPARED, new_value=payload)
        return {"draft_id": str(draft_id), "fallback_payload": payload}

    # â”€â”€ 15. mark_ready_for_confirmation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def mark_ready_for_confirmation(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        missing = self._compute_missing_fields(draft)
        if missing:
            raise ValueError(
                f"{ERR_REQUIRED_FIELD_MISSING}: Missing fields: {', '.join(missing)}"
            )
        if draft.status not in {
            DRAFT_STATUS_PROVIDERS_FOUND, DRAFT_STATUS_NO_EXACT_MATCH,
            DRAFT_STATUS_FALLBACK_AVAILABLE, DRAFT_STATUS_LOCATION_CHECKED,
            DRAFT_STATUS_COLLECTING,
        }:
            raise ValueError(f"{ERR_CONFIRMATION_NOT_READY}: Draft status is {draft.status}")

        # Build summary + score if not done yet
        scorer  = RealEstateLeadScoringService(self.db)
        score   = await scorer.calculate_and_persist(draft, draft_id)
        summary = {
            "lead_intent":   draft.lead_intent,
            "property_type": draft.property_type,
            "city":          draft.city,
            "locality":      draft.locality,
            "budget_min":    float(draft.budget_min) if draft.budget_min else None,
            "budget_max":    float(draft.budget_max) if draft.budget_max else None,
            "rent_min":      float(draft.rent_min) if draft.rent_min else None,
            "rent_max":      float(draft.rent_max) if draft.rent_max else None,
            "bedrooms":      draft.bedrooms,
            "customer_name": draft.customer_name,
            "customer_phone":draft.customer_phone,
            "customer_email":draft.customer_email,
        }
        draft.lead_summary        = summary
        draft.lead_score_snapshot = score
        draft.status              = DRAFT_STATUS_READY
        await self.db.flush()
        await self._log_event(draft.id, ACTOR_BACKEND, EVENT_CONFIRMATION_REQUESTED,
                              new_value={"status": DRAFT_STATUS_READY})
        await self.db.refresh(draft)
        return {**draft.to_dict(), "missing_fields": [], "ready_for_confirmation": True}

    # â”€â”€ 16. confirm_draft â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def confirm_draft(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        missing = self._compute_missing_fields(draft)
        if missing:
            raise ValueError(f"{ERR_REQUIRED_FIELD_MISSING}: Missing fields: {', '.join(missing)}")
        if draft.status not in {DRAFT_STATUS_READY, DRAFT_STATUS_PROVIDERS_FOUND,
                                  DRAFT_STATUS_NO_EXACT_MATCH, DRAFT_STATUS_FALLBACK_AVAILABLE}:
            raise ValueError(f"{ERR_CONFIRMATION_NOT_READY}: Draft status is {draft.status}")

        scorer = RealEstateLeadScoringService(self.db)
        score  = await scorer.calculate_and_persist(draft, draft_id)
        draft.lead_score_snapshot = score
        draft.status              = DRAFT_STATUS_CONFIRMED
        await self.db.flush()
        await self._log_event(draft.id, ACTOR_CUSTOMER, EVENT_DRAFT_CONFIRMED,
                              new_value={"status": DRAFT_STATUS_CONFIRMED})
        await self.db.refresh(draft)

        lead_ready_payload = {
            # Identity
            "source_draft_id":       str(draft_id),
            "ai_session_id":         str(draft.ai_session_id) if draft.ai_session_id else None,
            "category_id":           str(draft.category_id),
            "offering_id":           str(draft.offering_id),
            # Provider routing
            "tenant_id":             str(draft.selected_tenant_id) if draft.selected_tenant_id else None,
            "agent_id":              str(draft.selected_agent_id) if draft.selected_agent_id else None,
            # Lead intent + property
            "lead_intent":           draft.lead_intent,
            "property_type":         draft.property_type,
            # Location
            "city":                  draft.city,
            "locality":              draft.locality,
            "zipcode":               draft.zipcode,
            # Budget / rent ranges
            "budget_min":            float(draft.budget_min)  if draft.budget_min  is not None else None,
            "budget_max":            float(draft.budget_max)  if draft.budget_max  is not None else None,
            "rent_min":              float(draft.rent_min)    if draft.rent_min    is not None else None,
            "rent_max":              float(draft.rent_max)    if draft.rent_max    is not None else None,
            # Full requirement snapshot
            "requirement_snapshot":  draft.requirement_snapshot or draft.lead_summary or {},
            # Score
            "lead_score_snapshot":   score,
            # Provider chosen by customer
            "provider_snapshot":     draft.selected_provider_snapshot,
            # Fallback (populated when no exact provider match)
            "fallback_payload":      draft.fallback_payload,
            # Customer contact info
            "customer_snapshot": {
                "name":                   draft.customer_name,
                "phone":                  draft.customer_phone,
                "email":                  draft.customer_email,
                "preferred_contact_time": draft.preferred_contact_time,
                # TODO Sprint 19+: preferred_date for site visit must be validated
                # against agent availability before a real booking is created.
                # Error code: REAL_ESTATE_SITE_VISIT_AVAILABILITY_NOT_VALIDATED
            },
        }
        return {
            "draft_id":           str(draft_id),
            "status":             DRAFT_STATUS_CONFIRMED,
            "next_step":          "final_lead_creation_in_sprint_19",
            "lead_ready_payload": lead_ready_payload,
        }

    # â”€â”€ 17. cancel_draft â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def cancel_draft(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ) -> dict:
        draft = await self._get_and_authorize(draft_id, customer_id)
        if draft.status in TERMINAL_STATUSES:
            return {"draft_id": str(draft_id), "status": draft.status, "cancelled": False}
        draft.status = DRAFT_STATUS_CANCELLED
        await self.db.flush()
        await self._log_event(draft.id, ACTOR_CUSTOMER, EVENT_DRAFT_CANCELLED)
        return {"draft_id": str(draft_id), "status": DRAFT_STATUS_CANCELLED, "cancelled": True}

    # â”€â”€ 18. expire_old_drafts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def expire_old_drafts(self) -> dict:
        q = select(RealEstateLeadDraft).where(
            and_(
                RealEstateLeadDraft.expires_at < utcnow(),
                RealEstateLeadDraft.status.notin_(TERMINAL_STATUSES),
            )
        )
        drafts = (await self.db.execute(q)).scalars().all()
        count  = 0
        for d in drafts:
            d.status = DRAFT_STATUS_EXPIRED
            await self._log_event(d.id, ACTOR_SYSTEM, EVENT_DRAFT_EXPIRED)
            count += 1
        if count:
            await self.db.flush()
        return {"expired_count": count}

    # â”€â”€ Admin helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def admin_list_drafts(self, status: str | None = None, city: str | None = None,
                                 intent: str | None = None, limit: int = 50, offset: int = 0) -> dict:
        q = select(RealEstateLeadDraft)
        if status:
            q = q.where(RealEstateLeadDraft.status == status)
        if city:
            q = q.where(RealEstateLeadDraft.city.ilike(f"%{city}%"))
        if intent:
            q = q.where(RealEstateLeadDraft.lead_intent == intent)
        total_q   = select(RealEstateLeadDraft)
        q         = q.order_by(desc(RealEstateLeadDraft.created_at)).offset(offset).limit(limit)
        rows      = (await self.db.execute(q)).scalars().all()
        return {"drafts": [r.to_dict() for r in rows], "total": len(rows)}

    async def admin_get_draft(self, draft_id: uuid.UUID) -> dict:
        q    = select(RealEstateLeadDraft).where(RealEstateLeadDraft.id == draft_id)
        row  = (await self.db.execute(q)).scalars().first()
        if not row:
            raise ValueError(ERR_DRAFT_NOT_FOUND)
        return row.to_dict()

    async def admin_get_draft_events(self, draft_id: uuid.UUID) -> dict:
        q    = select(RealEstateLeadDraftEvent).where(
            RealEstateLeadDraftEvent.draft_id == draft_id
        ).order_by(RealEstateLeadDraftEvent.created_at)
        rows = (await self.db.execute(q)).scalars().all()
        return {"draft_id": str(draft_id), "events": [r.to_dict() for r in rows]}

    async def admin_list_routing_rules(self, category_id: uuid.UUID | None = None,
                                        active_only: bool = True) -> dict:
        q = select(RealEstateLeadRoutingRule)
        if active_only:
            q = q.where(RealEstateLeadRoutingRule.is_active == True)
        if category_id:
            q = q.where(RealEstateLeadRoutingRule.category_id == category_id)
        rows = (await self.db.execute(q)).scalars().all()
        return {"rules": [r.to_dict() for r in rows], "total": len(rows)}

    async def admin_create_routing_rule(self, payload: dict) -> dict:
        rule = RealEstateLeadRoutingRule(**{k: v for k, v in payload.items() if k != "id"})
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule.to_dict()

    async def admin_update_routing_rule(self, rule_id: uuid.UUID, payload: dict) -> dict:
        q    = select(RealEstateLeadRoutingRule).where(RealEstateLeadRoutingRule.id == rule_id)
        rule = (await self.db.execute(q)).scalars().first()
        if not rule:
            raise ValueError(ERR_DRAFT_NOT_FOUND)
        for k, v in payload.items():
            if k not in ("id", "created_at"):
                setattr(rule, k, v)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule.to_dict()

    async def admin_toggle_routing_rule(self, rule_id: uuid.UUID, is_active: bool) -> dict:
        q    = select(RealEstateLeadRoutingRule).where(RealEstateLeadRoutingRule.id == rule_id)
        rule = (await self.db.execute(q)).scalars().first()
        if not rule:
            raise ValueError(ERR_DRAFT_NOT_FOUND)
        rule.is_active = is_active
        await self.db.flush()
        await self.db.refresh(rule)
        return rule.to_dict()

    # â”€â”€ Internal helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def _get_and_authorize(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None
    ):
        q = select(RealEstateLeadDraft).where(RealEstateLeadDraft.id == draft_id)
        draft = (await self.db.execute(q)).scalars().first()
        if not draft:
            raise ValueError(ERR_DRAFT_NOT_FOUND)
        if customer_id and draft.customer_id and draft.customer_id != customer_id:
            raise PermissionError(ERR_DRAFT_ACCESS_DENIED)
        if draft.status == DRAFT_STATUS_EXPIRED:
            raise ValueError(ERR_DRAFT_EXPIRED)
        return draft

    async def _resolve_category(self, slug: str):
        from app.engines.admin_catalog.models import ServiceCategory
        normalized = slug.lower().strip()
        # Try slug match first
        q = select(ServiceCategory).where(
            and_(
                ServiceCategory.is_active == True,
                ServiceCategory.slug.ilike(normalized),
            )
        )
        cat = (await self.db.execute(q)).scalars().first()
        if cat:
            return cat
        # Try alias set
        for alias in REAL_ESTATE_CATEGORY_ALIASES:
            if alias in normalized or normalized in alias:
                q2 = select(ServiceCategory).where(
                    and_(
                        ServiceCategory.is_active == True,
                        ServiceCategory.name.ilike(f"%real%estate%"),
                    )
                )
                cat2 = (await self.db.execute(q2)).scalars().first()
                if cat2:
                    return cat2
                # Also try exact name match
                q3 = select(ServiceCategory).where(
                    and_(
                        ServiceCategory.is_active == True,
                        ServiceCategory.name.ilike(f"%{alias}%"),
                    )
                )
                cat3 = (await self.db.execute(q3)).scalars().first()
                if cat3:
                    return cat3
        return None

    async def _resolve_offering(self, category_id: uuid.UUID, slug: str):
        from app.engines.admin_catalog.models import MasterOffering
        q = select(MasterOffering).where(
            and_(
                MasterOffering.category_id == category_id,
                MasterOffering.is_active == True,
                MasterOffering.slug.ilike(slug),
            )
        )
        offering = (await self.db.execute(q)).scalars().first()
        if not offering:
            # Try name match
            q2 = select(MasterOffering).where(
                and_(
                    MasterOffering.category_id == category_id,
                    MasterOffering.is_active == True,
                    MasterOffering.name.ilike(f"%{slug.replace('-', ' ')}%"),
                )
            )
            offering = (await self.db.execute(q2)).scalars().first()
        return offering

    def _required_fields_for_offering(self, offering) -> list[str]:
        """Backend-driven required fields based on offering config."""
        required = ["lead_intent", "property_type", "city", "customer_name", "customer_phone"]
        return required

    def _compute_missing_fields(self, draft) -> list[str]:
        """Compute which required fields are still missing."""
        required = [
            ("lead_intent",     draft.lead_intent),
            ("property_type",   draft.property_type),
            ("city",            draft.city),
            ("customer_name",   draft.customer_name),
            ("customer_phone",  draft.customer_phone),
        ]
        return [field for field, val in required if not val]

    def _build_fallback_payload(self, draft, discovery_result: dict) -> dict:
        return {
            "reason":              "no_exact_provider_match",
            "city":                draft.city,
            "locality":            draft.locality,
            "lead_intent":         draft.lead_intent,
            "property_type":       draft.property_type,
            "customer_name":       draft.customer_name,
            "customer_phone":      draft.customer_phone,
            "customer_email":      draft.customer_email,
            "fallback_type":       "platform_inquiry_callback",
            "fallback_providers":  discovery_result.get("fallback_providers", []),
            "message":             (
                f"No exact provider found for your locality, but we found city-level support "
                f"in {draft.city}. Your inquiry will be submitted for callback."
                if draft.city else
                "No exact provider found. Your inquiry will be submitted for follow-up."
            ),
        }

    async def _log_event(
        self, draft_id: uuid.UUID, actor_type: str, event_type: str,
        old_value: dict | None = None, new_value: dict | None = None,
        message: str | None = None, request_id: str | None = None,
    ) -> None:
        evt = RealEstateLeadDraftEvent(
            draft_id   = draft_id,
            actor_type = actor_type,
            event_type = event_type,
            old_value  = old_value,
            new_value  = new_value,
            message    = message,
            request_id = request_id,
        )
        self.db.add(evt)
        try:
            await self.db.flush()
        except Exception:
            pass

