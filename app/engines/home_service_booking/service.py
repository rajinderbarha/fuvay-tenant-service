"""Sprint 16 — HomeServiceChatbotBookingService.

15 public methods covering the full booking draft lifecycle.

Rules:
- Backend is source of truth (pricing, serviceability, providers)
- DeepSeek only collects field values — never decides anything
- No final job assignment in this sprint (Sprint 19)
- Required fields driven by MasterOffering flags, not hardcoded
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.home_service_booking.constants import (
    ACTOR_AI, ACTOR_BACKEND, ACTOR_CUSTOMER, ACTOR_SYSTEM,
    ALLOWED_PHOTO_TYPES, DRAFT_EXPIRY_HOURS, DRAFT_MAX_PHOTOS,
    DRAFT_STATUS_CANCELLED, DRAFT_STATUS_COLLECTING_DETAILS,
    DRAFT_STATUS_CONFIRMED, DRAFT_STATUS_DRAFT, DRAFT_STATUS_EXPIRED,
    DRAFT_STATUS_FAILED, DRAFT_STATUS_PRICE_ESTIMATED,
    DRAFT_STATUS_PROVIDER_MATCHED, DRAFT_STATUS_READY_FOR_CONFIRMATION,
    DRAFT_STATUS_SERVICEABILITY_CHECKED, EVENT_DRAFT_CANCELLED,
    EVENT_DRAFT_CONFIRMED, EVENT_DRAFT_CREATED, EVENT_DRAFT_FAILED,
    EVENT_FIELD_COLLECTED, EVENT_PHOTO_UPLOADED, EVENT_PRICE_ESTIMATED,
    EVENT_PROVIDER_MATCHED, EVENT_PROVIDER_SELECTED,
    EVENT_SERVICEABILITY_CHECKED, EVENT_SUMMARY_GENERATED,
    ERR_ADDRESS_REQUIRED, ERR_BRAND_REQUIRED, ERR_CATEGORY_INVALID,
    ERR_CONFIRMATION_NOT_READY, ERR_DRAFT_ACCESS_DENIED,
    ERR_DRAFT_NOT_FOUND, ERR_DRAFT_TERMINAL, ERR_NO_PROVIDER_AVAILABLE,
    ERR_PROVIDER_ENTITLEMENT_CHANGED,
    ERR_OFFERING_INVALID, ERR_PHOTO_UPLOAD_FAILED,
    ERR_PRICE_ESTIMATE_FAILED, ERR_PROVIDER_NOT_IN_AREA,
    ERR_REQUIRED_FIELD_MISSING, ERR_TYPE_REQUIRED, MAX_PHOTO_SIZE_BYTES,
    PRICE_STATUS_ESTIMATED, PRICE_STATUS_FAILED, PRICE_STATUS_PENDING,
    PRICING_MODEL_FIXED, PRICING_MODEL_VISIT_FEE,
    PROVIDER_MATCH_MATCHED, PROVIDER_MATCH_NO_PROVIDER,
    PROVIDER_MATCH_PENDING, SVCABILITY_NOT_SERVICEABLE,
    SVCABILITY_PENDING, SVCABILITY_SERVICEABLE, TERMINAL_STATUSES,
)
from app.engines.home_service_booking.models import (
    HomeServiceBookingDraft,
    HomeServiceBookingDraftEvent,
)
from app.engines.home_service_booking.serviceability_service import (
    HomeServiceServiceabilityService,
)
from app.engines.home_service_booking.provider_matching import (
    find_bookable_home_service_providers,
)
from app.exceptions import ServiceOSException

logger = structlog.get_logger("home_service.booking.service")
utcnow = lambda: datetime.now(timezone.utc)


class HomeServiceChatbotBookingService:
    """
    Manages the full booking draft lifecycle for Home Services.
    All business decisions (pricing, serviceability, provider selection)
    are made here. DeepSeek only supplies text/field values via the chat layer.
    """

    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db         = db
        self.request_id = request_id
        self._svc_svc   = HomeServiceServiceabilityService(db)

    # ══════════════════════════════════════════════════════════════════════════
    # 1. START DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def start_booking_draft(
        self,
        customer_id: uuid.UUID | None,
        ai_session_id: uuid.UUID | None,
        category_slug: str,
        offering_slug: str,
    ) -> dict:
        """Create a new booking draft for a Home Service offering."""
        from app.engines.admin_catalog.models import ServiceCategory, MasterService

        # Resolve category
        cat = (await self.db.execute(
            select(ServiceCategory).where(
                ServiceCategory.is_active.is_(True),
                ServiceCategory.slug == category_slug,
            )
        )).scalars().first()
        if not cat:
            raise ServiceOSException(
                ERR_CATEGORY_INVALID,
                f"Category '{category_slug}' is not available.",
                status_code=422,
            )

        # Resolve offering.
        #
        # HS7 fix: this previously queried `MasterOffering`, a legacy table
        # that is completely empty in the real database (confirmed via
        # direct query — 0 rows). Every customer catalog surface actually
        # in use (admin catalog, HS6/HS6B provider-first matching/pricing,
        # `/v1/catalog/master/services`) reads from `MasterService`, so
        # `start_booking_draft` — the very first step of the customer
        # booking flow — could never succeed for any real service. Fixed to
        # resolve against the real, populated `MasterService` table.
        offering = (await self.db.execute(
            select(MasterService).where(
                MasterService.is_active.is_(True),
                MasterService.category_id == cat.id,
                MasterService.slug == offering_slug,
            )
        )).scalars().first()
        if not offering:
            raise ServiceOSException(
                ERR_OFFERING_INVALID,
                f"Offering '{offering_slug}' is not available under '{category_slug}'.",
                status_code=422,
            )

        expires_at = utcnow() + timedelta(hours=DRAFT_EXPIRY_HOURS)
        draft = HomeServiceBookingDraft(
            id=uuid.uuid4(),
            customer_id=customer_id,
            ai_session_id=ai_session_id,
            category_id=cat.id,
            offering_id=offering.id,
            status=DRAFT_STATUS_DRAFT,
            serviceability_status=SVCABILITY_PENDING,
            price_status=PRICE_STATUS_PENDING,
            provider_match_status=PROVIDER_MATCH_PENDING,
            expires_at=expires_at,
        )
        self.db.add(draft)
        await self.db.flush()

        await self._emit_event(
            draft_id=draft.id,
            actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_DRAFT_CREATED,
            new_value={"category_slug": category_slug, "offering_slug": offering_slug},
            message=f"Draft created for {offering.service_name}",
        )
        await self.db.commit()
        await self.db.refresh(draft)

        result = draft.to_dict()
        result["offering_name"]          = offering.service_name
        result["offering_slug"]          = offering.slug
        result["category_name"]          = cat.name
        result["category_slug"]          = cat.slug
        result["required_fields"]        = self._get_required_field_list(offering)
        result["pricing_model"]          = offering.pricing_model
        result["default_visit_fee"]      = float(offering.visit_fee)
        result["default_base_price"]     = float(offering.base_price)
        return result

    # ══════════════════════════════════════════════════════════════════════════
    # 2. GET DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def get_booking_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Return a draft, enforcing customer ownership."""
        draft = await self._require_draft(draft_id, customer_id)
        return await self._enrich_draft(draft)

    # ══════════════════════════════════════════════════════════════════════════
    # 3. UPDATE DRAFT FIELDS
    # ══════════════════════════════════════════════════════════════════════════

    async def update_draft_fields(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        payload: dict,
    ) -> dict:
        """Merge customer-supplied fields into the draft. Backend re-validates."""
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        updatable = [
            "customer_name", "customer_phone",
            "city", "zipcode",
            "issue_summary", "issue_details",
            "preferred_date", "preferred_time_window",
        ]
        uuid_fields = ["offering_type_id", "brand_id", "address_id"]
        changes: dict = {}

        for field in updatable:
            if field in payload and payload[field] is not None:
                val = payload[field]
                # MODULE-L5-02: preferred_date is a DATE column; a raw string
                # ("2026-08-01") from the client crashed the UPDATE with an
                # asyncpg DataError ('str' has no attribute 'toordinal'). Parse
                # ISO date strings to a date object before persisting.
                if field == "preferred_date" and isinstance(val, str):
                    from datetime import date, datetime as _dt
                    try:
                        val = date.fromisoformat(val)
                    except ValueError:
                        val = _dt.fromisoformat(val).date()
                setattr(draft, field, val)
                changes[field] = payload[field]

        for field in uuid_fields:
            if field in payload and payload[field]:
                val = uuid.UUID(str(payload[field]))
                setattr(draft, field, val)
                changes[field] = str(val)

        # Resolve address if address_id provided
        if "address_id" in payload and payload["address_id"]:
            await self._resolve_address_snapshot(draft, uuid.UUID(str(payload["address_id"])))
            changes["address_snapshot"] = draft.address_snapshot

        draft.status = DRAFT_STATUS_COLLECTING_DETAILS
        draft.updated_at = utcnow()

        if changes:
            await self._emit_event(
                draft_id=draft.id,
                actor_type=ACTOR_CUSTOMER,
                event_type=EVENT_FIELD_COLLECTED,
                new_value=changes,
                message=f"Customer updated {len(changes)} field(s)",
            )

        await self.db.commit()
        await self.db.refresh(draft)
        return await self._enrich_draft(draft)

    # ══════════════════════════════════════════════════════════════════════════
    # 4. SYNC DRAFT FROM AI SESSION
    # ══════════════════════════════════════════════════════════════════════════

    async def sync_draft_from_ai_session(
        self,
        ai_session_id: uuid.UUID,
    ) -> dict | None:
        """Pull collected_fields from an AI session into the linked draft."""
        from app.engines.ai_conversation.models import AIConversationSession

        session = (await self.db.execute(
            select(AIConversationSession).where(
                AIConversationSession.id == ai_session_id,
                AIConversationSession.is_active.is_(True),
            )
        )).scalars().first()
        if not session:
            return None

        draft = (await self.db.execute(
            select(HomeServiceBookingDraft).where(
                HomeServiceBookingDraft.ai_session_id == ai_session_id,
                HomeServiceBookingDraft.status.not_in(list(TERMINAL_STATUSES)),
            )
        )).scalars().first()
        if not draft:
            return None

        fields = session.collected_fields or {}
        changed = False

        simple_map = {
            "city": "city", "zipcode": "zipcode",
            "issue_summary": "issue_summary",
            "customer_name": "customer_name", "customer_phone": "customer_phone",
            "preferred_date": "preferred_date",
            "preferred_time_window": "preferred_time_window",
        }
        for ai_key, draft_key in simple_map.items():
            if fields.get(ai_key) and not getattr(draft, draft_key):
                setattr(draft, draft_key, fields[ai_key])
                changed = True

        if changed:
            draft.status = DRAFT_STATUS_COLLECTING_DETAILS
            draft.updated_at = utcnow()
            await self._emit_event(
                draft_id=draft.id,
                actor_type=ACTOR_AI,
                event_type=EVENT_FIELD_COLLECTED,
                new_value=fields,
                message="Fields synced from AI session",
            )
            await self.db.commit()
            await self.db.refresh(draft)

        return await self._enrich_draft(draft)

    # ══════════════════════════════════════════════════════════════════════════
    # 5. VALIDATE REQUIRED FIELDS
    # ══════════════════════════════════════════════════════════════════════════

    async def validate_required_fields(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Return validation result with missing field names."""
        draft   = await self._require_draft(draft_id, customer_id)
        offering = await self._get_offering(draft.offering_id)
        missing = self._compute_missing_fields(draft, offering)
        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 6. GET MISSING FIELDS
    # ══════════════════════════════════════════════════════════════════════════

    async def get_missing_fields(
        self, draft_id: uuid.UUID, customer_id: uuid.UUID | None = None,
    ) -> list[str]:
        """Return a list of field names still needed to proceed."""
        draft    = await self._require_draft(draft_id, customer_id)
        offering = await self._get_offering(draft.offering_id)
        return self._compute_missing_fields(draft, offering)

    # ══════════════════════════════════════════════════════════════════════════
    # 7. CHECK SERVICEABILITY
    # ══════════════════════════════════════════════════════════════════════════

    async def check_serviceability(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Run real serviceability check and update draft."""
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        if not draft.city:
            raise ServiceOSException(
                ERR_ADDRESS_REQUIRED,
                "City is required for serviceability check.",
                status_code=422,
            )

        result = await self._svc_svc.check(
            category_id=draft.category_id,
            offering_id=draft.offering_id,
            city=draft.city,
            zipcode=draft.zipcode,
        )

        draft.serviceability_status = (
            SVCABILITY_SERVICEABLE if result["serviceable"] else SVCABILITY_NOT_SERVICEABLE
        )
        if result["serviceable"]:
            draft.status = DRAFT_STATUS_SERVICEABILITY_CHECKED
        else:
            draft.failure_code    = result.get("reason_code")
            draft.failure_message = result.get("message")

        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id,
            actor_type=ACTOR_BACKEND,
            event_type=EVENT_SERVICEABILITY_CHECKED,
            new_value=result,
            message=result["message"],
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {**result, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # 8. RESOLVE PRICE ESTIMATE
    # ══════════════════════════════════════════════════════════════════════════

    async def resolve_price_estimate(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Compute price estimate using offering defaults + city-tier floor.
        Backend is source of truth. Frontend price is NEVER trusted.
        """
        draft    = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)
        offering = await self._get_offering(draft.offering_id)

        try:
            snapshot = await self._compute_price_snapshot(draft, offering)
            draft.price_snapshot = snapshot
            draft.price_status   = PRICE_STATUS_ESTIMATED
            draft.status         = DRAFT_STATUS_PRICE_ESTIMATED
            draft.updated_at     = utcnow()

            await self._emit_event(
                draft_id=draft.id,
                actor_type=ACTOR_BACKEND,
                event_type=EVENT_PRICE_ESTIMATED,
                new_value=snapshot,
                message=f"Price estimated: {snapshot.get('display_price')}",
            )
            await self.db.commit()
            await self.db.refresh(draft)
            return {"price_snapshot": snapshot, "draft_status": draft.status}

        except Exception as exc:
            logger.warning("home_service.price_estimate_failed", error=str(exc))
            draft.price_status = PRICE_STATUS_FAILED
            draft.updated_at   = utcnow()
            await self.db.commit()
            raise ServiceOSException(
                ERR_PRICE_ESTIMATE_FAILED,
                "Unable to estimate price at this time. Please try again.",
                status_code=503,
            )

    # ══════════════════════════════════════════════════════════════════════════
    # 9. FIND BOOKABLE PROVIDERS
    # ══════════════════════════════════════════════════════════════════════════

    async def find_bookable_providers(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Find real bookable providers for the draft's city/zipcode."""
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        if not draft.city:
            raise ServiceOSException(
                ERR_ADDRESS_REQUIRED,
                "City is required before matching providers.",
                status_code=422,
            )

        providers = await find_bookable_home_service_providers(
            db=self.db,
            category_id=draft.category_id,
            offering_id=draft.offering_id,
            city=draft.city,
            zipcode=draft.zipcode,
            offering_type_id=draft.offering_type_id,
            brand_id=draft.brand_id,
        )

        if providers:
            draft.provider_options      = providers
            draft.provider_match_status = PROVIDER_MATCH_MATCHED
            draft.status                = DRAFT_STATUS_PROVIDER_MATCHED

            # Auto-select top provider
            if not draft.selected_tenant_id and providers:
                top = providers[0]
                draft.selected_tenant_id        = uuid.UUID(top["provider_ref"])
                draft.selected_provider_snapshot = top
        else:
            draft.provider_match_status = PROVIDER_MATCH_NO_PROVIDER

        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id,
            actor_type=ACTOR_BACKEND,
            event_type=EVENT_PROVIDER_MATCHED,
            new_value={"count": len(providers)},
            message=f"{len(providers)} provider(s) found",
        )
        await self.db.commit()
        await self.db.refresh(draft)

        if not providers:
            raise ServiceOSException(
                ERR_NO_PROVIDER_AVAILABLE,
                f"No providers available in {draft.city}. Try a nearby city.",
                status_code=422,
            )
        return {"providers": providers, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # 10. SELECT PROVIDER
    # ══════════════════════════════════════════════════════════════════════════

    async def select_provider(
        self,
        draft_id: uuid.UUID,
        provider_ref: str,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Customer selects a specific provider from the options list."""
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        options = draft.provider_options or []
        match   = next((p for p in options if p["provider_ref"] == provider_ref), None)
        if not match:
            raise ServiceOSException(
                ERR_PROVIDER_NOT_IN_AREA,
                "Selected provider is not available for this booking.",
                status_code=422,
            )

        draft.selected_tenant_id       = uuid.UUID(match["provider_ref"])
        draft.selected_provider_snapshot = match
        draft.updated_at               = utcnow()

        await self._emit_event(
            draft_id=draft.id,
            actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_PROVIDER_SELECTED,
            new_value=match,
            message=f"Customer selected: {match.get('business_name')}",
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {"selected_provider": match, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # 10B. PROVIDER-FIRST MATCHING + CUSTOMER PRICE CHOICE
    # ══════════════════════════════════════════════════════════════════════════
    # Corrects the list-based flow above (find_bookable_providers + select_provider,
    # which let the customer pick a provider manually from a list). The backend
    # now selects exactly one provider via full eligibility gating + scoring,
    # THEN computes that provider's Low/Mid/High price options. The customer
    # never sees or picks from a provider list in this flow.

    async def match_provider_and_price(
        self,
        *,
        category_id: uuid.UUID,
        master_service_id: uuid.UUID,
        city: str,
        zipcode: str | None,
        offering_type_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
        draft_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        reveal_internal_score: bool = False,
    ) -> dict:
        """Steps 3-8 of the corrected flow, atomically: find eligible providers,
        rank them, select the single best one, compute its price options, and
        compute a separate area comparison. Returns the ticket-required response
        shape. If draft_id is given, persists a snapshot onto the draft.

        Home Services scope guard: this entire flow — provider-first matching,
        Low/Mid/High bargain pricing, "customer pays provider directly" — is
        Home-Services-only. Raises VerticalFlowNotSupported for any other
        vertical (CA/professional services, IELTS/coaching, restaurants, real
        estate, education, listing/menu/subscription businesses)."""
        from app.engines.home_service_booking.matching_engine import (
            select_best_provider, get_area_market_comparison,
            build_customer_safe_provider, build_admin_provider, compute_price_tiers,
            assert_home_services_vertical,
        )
        from app.engines.admin_catalog.bargain_engine import BargainValidationError
        from app.engines.admin_catalog.models import BargainRule, ServicePricingRule, ServiceCategory

        category = await self.db.get(ServiceCategory, category_id)
        assert_home_services_vertical(category.vertical_type if category else None)

        # MODULE-L5-02: require a city before matching (a draft with no address
        # previously reached the matching engine and crashed with a NoneType
        # .strip() 500). Return the same clean error as serviceability-check.
        if not city:
            raise ServiceOSException(
                "HOME_BOOKING_ADDRESS_REQUIRED",
                "Please set your service address (city) before matching a provider.",
                status_code=422,
            )

        match = await select_best_provider(
            self.db, category_id=category_id, offering_id=master_service_id,
            city=city, zipcode=zipcode, offering_type_id=offering_type_id, brand_id=brand_id,
        )

        if not match or not match.get("signals"):
            raise ServiceOSException(
                ERR_NO_PROVIDER_AVAILABLE,
                f"No eligible providers available in {city}. Try a nearby city.",
                status_code=422,
            )

        signals, score = match["signals"], match["score"]
        selected_tenant_id = uuid.UUID(signals.tenant_id)

        # Resolve the selected provider's bargain rule (customer range + fee)
        # and its linked pricing rule (admin range) — real, tenant-scoped data.
        #
        # HS6 fix: previously matched ONLY on master_service_id, completely
        # ignoring offering_type_id/brand_id even though they were already
        # passed into select_best_provider() for eligibility filtering — the
        # exact "Window AC brand price used for Split AC" bug this whole
        # Home Services pricing lineage exists to prevent, except it was
        # still live in the actual matching/booking price-resolution path.
        # Fixed: join the linked ServicePricingRule and prefer the most
        # specific match — type+brand > type-only > service-only — mirroring
        # the hierarchy already used by _find_admin_pricing_rule elsewhere.
        bargain_candidates = (await self.db.execute(
            select(BargainRule, ServicePricingRule)
            .join(ServicePricingRule, ServicePricingRule.id == BargainRule.pricing_rule_id, isouter=True)
            .where(
                BargainRule.master_service_id == master_service_id,
                BargainRule.status == "active", BargainRule.deleted_at.is_(None),
            )
        )).all()

        def _specificity(row) -> int:
            spr = row[1]
            if spr is None:
                return 0
            has_type = offering_type_id is not None and spr.service_type_id == offering_type_id
            has_brand = brand_id is not None and spr.brand_id == brand_id
            if has_type and has_brand:
                return 3
            if has_type:
                return 2
            if spr.service_type_id is None and spr.brand_id is None:
                return 1
            return -1  # a type/brand-scoped rule that doesn't match this request — never usable here

        eligible_candidates = [row for row in bargain_candidates if _specificity(row) >= 0]
        eligible_candidates.sort(key=lambda row: (_specificity(row), row[0].created_at), reverse=True)
        bargain_rule = eligible_candidates[0][0] if eligible_candidates else None
        if not bargain_rule or bargain_rule.customer_min_price is None or bargain_rule.customer_max_price is None:
            raise ServiceOSException(
                "PRICE_OPTIONS_UNAVAILABLE",
                "Selected provider does not have a customer price range configured yet.",
                status_code=422,
            )
        pricing_rule = None
        if bargain_rule.pricing_rule_id:
            pricing_rule = await self.db.get(ServicePricingRule, bargain_rule.pricing_rule_id)

        try:
            price_options = compute_price_tiers(
                admin_min_price=pricing_rule.min_price if pricing_rule else None,
                admin_max_price=pricing_rule.max_price if pricing_rule else None,
                admin_base_price=pricing_rule.base_price if pricing_rule else None,
                customer_min_price=bargain_rule.customer_min_price,
                customer_max_price=bargain_rule.customer_max_price,
                platform_fee_percent=bargain_rule.platform_fee_percent or (pricing_rule.platform_fee_percent if pricing_rule else 0),
                platform_fee_fixed_amount=bargain_rule.platform_fee_fixed_amount,
            )
        except BargainValidationError as e:
            raise ServiceOSException(e.code, e.message, status_code=422) from e

        area_comparison = await get_area_market_comparison(
            self.db, category_id=category_id, offering_id=master_service_id,
            city=city, zipcode=zipcode, exclude_tenant_id=selected_tenant_id,
        )

        selected_provider_public = build_customer_safe_provider(signals, score)
        selected_provider_admin = build_admin_provider(signals, score) if reveal_internal_score else None

        result = {
            "selected_provider": selected_provider_public,
            "selected_provider_price_options": price_options,
            "area_market_comparison": area_comparison,
        }
        if reveal_internal_score:
            result["selected_provider_admin"] = selected_provider_admin

        if draft_id is not None:
            draft = await self._require_draft(draft_id, customer_id)
            self._assert_not_terminal(draft)
            draft.selected_tenant_id = selected_tenant_id
            # matching_score_snapshot is internal — stored on the draft (backend-
            # only field), never returned verbatim by the customer-facing API.
            draft.selected_provider_snapshot = {
                **selected_provider_public,
                "matching_score_snapshot": build_admin_provider(signals, score)["internal_score_breakdown"],
                "internal_score": float(score),
            }
            draft.price_snapshot = {**(draft.price_snapshot or {}), "price_options": price_options}
            draft.provider_match_status = PROVIDER_MATCH_MATCHED
            draft.status = DRAFT_STATUS_PROVIDER_MATCHED
            draft.updated_at = utcnow()
            await self._emit_event(
                draft_id=draft.id, actor_type=ACTOR_BACKEND, event_type=EVENT_PROVIDER_MATCHED,
                new_value={"selected_tenant_id": str(selected_tenant_id), "candidate_count": match["candidate_count"]},
                message=f"Backend selected provider: {signals.provider_name}",
            )
            await self.db.commit()
            await self.db.refresh(draft)
            result["draft_status"] = draft.status

        return result

    async def confirm_price_choice(
        self,
        draft_id: uuid.UUID,
        price_tier: str,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Customer chooses Low/Mid/High only — never a raw amount, never a
        provider. Re-validates the stored price options before storing the
        offer (hard gate 10: no assignment change without revalidation)."""
        from app.engines.home_service_booking.matching_engine import resolve_customer_offer_for_tier

        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        if price_tier not in ("low", "mid", "high"):
            raise ServiceOSException("INVALID_PRICE_TIER",
                "price_tier must be 'low', 'mid', or 'high'.", status_code=422)
        if not draft.selected_tenant_id or not draft.price_snapshot or "price_options" not in draft.price_snapshot:
            raise ServiceOSException(ERR_NO_PROVIDER_AVAILABLE,
                "No matched provider/price options found for this draft. Run provider matching first.",
                status_code=422)

        price_options = draft.price_snapshot["price_options"]
        customer_offer = resolve_customer_offer_for_tier(price_options, price_tier)

        # HS7 fix: matching_score_snapshot (internal per-signal scoring) was
        # being copied into booking_summary and returned verbatim to the
        # customer by this endpoint and by /summary — a direct violation of
        # the "never show internal provider scoring" hard gate. Removed;
        # internal scoring remains available to admin-only surfaces via
        # draft.selected_provider_snapshot, never via booking_summary.
        draft.booking_summary = {
            **(draft.booking_summary or {}),
            "selected_tenant_id": str(draft.selected_tenant_id),
            "selected_provider_name": (draft.selected_provider_snapshot or {}).get("provider_name"),
            "selected_zipcode": draft.zipcode,
            "selected_price_tier": price_tier,
            "customer_offer": float(customer_offer),
            "allowed_offer_min": price_options["allowed_offer_min"],
            "allowed_offer_max": price_options["allowed_offer_max"],
            "platform_fee_amount": price_options["platform_fee_amount"],
            "payment_mode": "customer_pays_provider_directly",
        }
        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_CUSTOMER, event_type=EVENT_PRICE_ESTIMATED,
            new_value={"price_tier": price_tier, "customer_offer": float(customer_offer)},
            message=f"Customer chose {price_tier} price: {customer_offer}",
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {"booking_summary": draft.booking_summary, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # 11. BUILD BOOKING SUMMARY
    # ══════════════════════════════════════════════════════════════════════════

    async def build_booking_summary(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Build the customer-facing booking summary card.

        HS7 fixes:
        1. This previously *overwrote* draft.booking_summary wholesale,
           destroying the selected_price_tier/customer_offer that
           confirm_price_choice had just written there — a real bug that
           would make the later /confirm call fail with
           INVALID_SELECTED_PRICE_OPTION even after the customer legitimately
           picked a tier, if the Review step (which calls this endpoint)
           runs after price selection as the ticket's flow requires. Fixed
           to merge on top of the existing summary instead of replacing it.
        2. `selected_provider` was the raw `selected_provider_snapshot`,
           which includes `internal_score` and `matching_score_snapshot` —
           a direct customer-safety leak of internal provider scoring
           (explicitly forbidden by the ticket). Fixed to strip those keys.
        """
        draft    = await self._require_draft(draft_id, customer_id)
        offering = await self._get_offering(draft.offering_id)

        customer_safe_provider = None
        if draft.selected_provider_snapshot:
            customer_safe_provider = {
                k: v for k, v in draft.selected_provider_snapshot.items()
                if k not in ("internal_score", "matching_score_snapshot")
            }

        existing = draft.booking_summary or {}
        summary = {
            **existing,
            "offering_name":    offering.service_name,
            "offering_slug":    offering.slug,
            "issue_summary":    draft.issue_summary,
            "address":          draft.address_snapshot,
            "city":             draft.city,
            "zipcode":          draft.zipcode,
            "preferred_date":   draft.preferred_date.isoformat() if draft.preferred_date else None,
            "preferred_time_window": draft.preferred_time_window,
            "price_estimate":   draft.price_snapshot,
            "selected_provider":customer_safe_provider,
            "serviceability":   {
                "serviceable": draft.serviceability_status == SVCABILITY_SERVICEABLE,
                "status":      draft.serviceability_status,
            },
            "ready_for_confirmation": (
                draft.serviceability_status == SVCABILITY_SERVICEABLE
                and bool(draft.selected_tenant_id)
                and existing.get("selected_price_tier") in ("low", "mid", "high")
            ),
        }

        draft.booking_summary = summary
        draft.updated_at      = utcnow()
        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_BACKEND,
            event_type=EVENT_SUMMARY_GENERATED,
            new_value={"ready_for_confirmation": summary["ready_for_confirmation"]},
            message="Booking summary generated",
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {"booking_summary": summary, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # 12. MARK READY FOR CONFIRMATION
    # ══════════════════════════════════════════════════════════════════════════

    async def mark_ready_for_confirmation(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """Advance draft to ready_for_confirmation if all checks pass.

        HS7 fix: this was previously dead code (never called from any
        router) and, when unwired, additionally checked the legacy flat
        `price_status`/`resolve_price_estimate` gate rather than the
        provider-first flow's own readiness signals (selected provider +
        confirmed price tier). Rewritten to require the real HS6/HS6B
        provider-first sequence — match-and-price then
        confirm-price-choice — and to re-validate the selected provider is
        still bookable right now (a booking must never be created against a
        provider that became non-bookable while the customer was reviewing).
        """
        draft    = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)
        offering = await self._get_offering(draft.offering_id)
        missing  = self._compute_missing_fields(draft, offering)

        if missing:
            raise ServiceOSException(
                ERR_REQUIRED_FIELD_MISSING,
                f"Missing required fields: {', '.join(missing)}",
                status_code=422,
            )

        if draft.serviceability_status != SVCABILITY_SERVICEABLE:
            raise ServiceOSException(
                "SERVICE_NOT_AVAILABLE_IN_AREA",
                "This service is not available in your area yet.",
                status_code=422,
            )

        if not draft.selected_tenant_id or not draft.price_snapshot or "price_options" not in draft.price_snapshot:
            raise ServiceOSException(
                ERR_NO_PROVIDER_AVAILABLE,
                "No matched provider/price options found for this draft. Run provider matching first.",
                status_code=422,
            )

        selected_tier = (draft.booking_summary or {}).get("selected_price_tier")
        if selected_tier not in ("low", "mid", "high"):
            raise ServiceOSException(
                "INVALID_SELECTED_PRICE_OPTION",
                "Selected price option is no longer valid.",
                status_code=422,
            )

        from sqlalchemy import text
        bookable_row = (await self.db.execute(
            text(
                "SELECT is_bookable FROM provider_visibility_statuses "
                "WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": str(draft.selected_tenant_id)},
        )).first()
        if not bookable_row or not bookable_row[0]:
            raise ServiceOSException(
                "SELECTED_PROVIDER_NOT_BOOKABLE",
                "Selected provider is no longer available. Please match again.",
                status_code=422,
            )

        draft.status     = DRAFT_STATUS_READY_FOR_CONFIRMATION
        draft.updated_at = utcnow()
        await self.db.commit()
        await self.db.refresh(draft)
        return {"draft_status": draft.status, "ready_for_confirmation": True}

    # ══════════════════════════════════════════════════════════════════════════
    # 13. CONFIRM DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def confirm_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Customer confirms booking intent. Returns booking-ready payload for Sprint 19.
        Does NOT create a final job or booking in this sprint.
        """
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        if draft.status != DRAFT_STATUS_READY_FOR_CONFIRMATION:
            raise ServiceOSException(
                ERR_CONFIRMATION_NOT_READY,
                f"Draft must be in 'ready_for_confirmation' status. Current: {draft.status}",
                status_code=422,
            )

        # FINAL-L5-04C — re-validate the selected provider's entitlement at
        # confirmation time, not just at match time (Part 6). Entitlement
        # could have been disabled by an admin in the window between the
        # customer being matched and confirming — a controlled 409, not a
        # stale confirmation or an unhandled 500.
        if draft.selected_tenant_id and draft.offering_id:
            from app.engines.admin_catalog.models import MasterService
            from app.engines.entitlement.service import entitlement_service
            svc_group_id = (await self.db.execute(
                select(MasterService.service_group_id).where(MasterService.id == draft.offering_id)
            )).scalar_one_or_none()
            if svc_group_id:
                still_entitled = await entitlement_service.has_category_entitlement(
                    self.db, draft.selected_tenant_id, svc_group_id
                )
                if not still_entitled:
                    raise ServiceOSException(
                        ERR_PROVIDER_ENTITLEMENT_CHANGED,
                        "The selected provider is no longer available for this category. Please search again.",
                        status_code=409,
                    )

        draft.status     = DRAFT_STATUS_CONFIRMED
        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_DRAFT_CONFIRMED,
            new_value={"status": DRAFT_STATUS_CONFIRMED},
            message="Customer confirmed booking intent",
        )
        await self.db.commit()
        await self.db.refresh(draft)

        booking_ready_payload = {
            "draft_id":         str(draft.id),
            "category_id":      str(draft.category_id),
            "offering_id":      str(draft.offering_id),
            "tenant_id":        str(draft.selected_tenant_id) if draft.selected_tenant_id else None,
            "price_snapshot":   draft.price_snapshot,
            "address_snapshot": draft.address_snapshot,
            "issue_details":    {
                "issue_summary":      draft.issue_summary,
                "offering_type_id":   str(draft.offering_type_id) if draft.offering_type_id else None,
                "brand_id":           str(draft.brand_id) if draft.brand_id else None,
                "preferred_date":     draft.preferred_date.isoformat() if draft.preferred_date else None,
                "preferred_time_window": draft.preferred_time_window,
                "photo_urls":         draft.photo_urls or [],
            },
        }

        return {
            "success": True,
            "data": {
                "draft_id":             str(draft.id),
                "status":               DRAFT_STATUS_CONFIRMED,
                "next_step":            "final_booking_creation_in_sprint_19",
                "booking_ready_payload": booking_ready_payload,
            },
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 14. CANCEL DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def cancel_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> dict:
        """Cancel a draft (customer-initiated)."""
        draft = await self._require_draft(draft_id, customer_id)
        if draft.status in TERMINAL_STATUSES:
            return {"draft_status": draft.status, "message": "Draft already closed."}

        draft.status     = DRAFT_STATUS_CANCELLED
        draft.updated_at = utcnow()
        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_DRAFT_CANCELLED,
            new_value={"reason": reason},
            message=reason or "Customer cancelled",
        )
        await self.db.commit()
        return {"draft_status": draft.status, "message": "Booking draft cancelled."}

    # ══════════════════════════════════════════════════════════════════════════
    # 15. EXPIRE OLD DRAFTS (system job)
    # ══════════════════════════════════════════════════════════════════════════

    async def expire_old_drafts(self) -> int:
        """Mark expired drafts. Intended to be called by a scheduler."""
        now = utcnow()
        rows = (await self.db.execute(
            select(HomeServiceBookingDraft).where(
                HomeServiceBookingDraft.expires_at <= now,
                HomeServiceBookingDraft.status.not_in(list(TERMINAL_STATUSES)),
            )
        )).scalars().all()

        count = 0
        for draft in rows:
            draft.status     = DRAFT_STATUS_EXPIRED
            draft.updated_at = now
            await self._emit_event(
                draft_id=draft.id, actor_type=ACTOR_SYSTEM,
                event_type=EVENT_DRAFT_FAILED,
                new_value={"reason": "expired"},
                message="Draft expired",
            )
            count += 1

        if count:
            await self.db.commit()
        return count

    # ══════════════════════════════════════════════════════════════════════════
    # ADMIN METHODS
    # ══════════════════════════════════════════════════════════════════════════

    async def admin_list_drafts(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        city: str | None = None,
        offering_id: str | None = None,
    ) -> dict:
        """Admin: list all drafts with optional filters."""
        q = select(HomeServiceBookingDraft).order_by(
            HomeServiceBookingDraft.created_at.desc()
        )
        if status:
            q = q.where(HomeServiceBookingDraft.status == status)
        if city:
            q = q.where(HomeServiceBookingDraft.city.ilike(f"%{city}%"))
        if offering_id:
            q = q.where(HomeServiceBookingDraft.offering_id == uuid.UUID(offering_id))

        offset = (page - 1) * page_size
        rows   = (await self.db.execute(q.offset(offset).limit(page_size))).scalars().all()
        return {
            "drafts": [d.to_dict() for d in rows],
            "page": page, "page_size": page_size,
        }

    async def admin_get_draft(self, draft_id: uuid.UUID) -> dict:
        """Admin: get any draft without ownership check."""
        draft = await self.db.get(HomeServiceBookingDraft, draft_id)
        if not draft:
            raise ServiceOSException(ERR_DRAFT_NOT_FOUND,
                f"Draft '{draft_id}' not found.", status_code=404)
        return await self._enrich_draft(draft)

    async def admin_get_draft_events(self, draft_id: uuid.UUID) -> list[dict]:
        """Admin: get all events for a draft."""
        rows = (await self.db.execute(
            select(HomeServiceBookingDraftEvent)
            .where(HomeServiceBookingDraftEvent.draft_id == draft_id)
            .order_by(HomeServiceBookingDraftEvent.created_at)
        )).scalars().all()
        return [e.to_dict() for e in rows]

    # ══════════════════════════════════════════════════════════════════════════
    # PHOTO UPLOAD
    # ══════════════════════════════════════════════════════════════════════════

    async def add_photo(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        photo_url: str,
        content_type: str = "image/jpeg",
    ) -> dict:
        """Add a photo URL to the draft (after media upload)."""
        draft = await self._require_draft(draft_id, customer_id)
        self._assert_not_terminal(draft)

        if content_type not in ALLOWED_PHOTO_TYPES:
            raise ServiceOSException(
                ERR_PHOTO_UPLOAD_FAILED,
                f"Invalid file type: {content_type}. Allowed: jpg, png, webp.",
                status_code=422,
            )

        existing = list(draft.photo_urls or [])
        if len(existing) >= DRAFT_MAX_PHOTOS:
            raise ServiceOSException(
                ERR_PHOTO_UPLOAD_FAILED,
                f"Maximum {DRAFT_MAX_PHOTOS} photos allowed per booking.",
                status_code=422,
            )

        existing.append(photo_url)
        draft.photo_urls = existing
        draft.updated_at = utcnow()

        await self._emit_event(
            draft_id=draft.id, actor_type=ACTOR_CUSTOMER,
            event_type=EVENT_PHOTO_UPLOADED,
            new_value={"url": photo_url},
            message="Photo added to draft",
        )
        await self.db.commit()
        await self.db.refresh(draft)
        return {"photo_urls": draft.photo_urls, "draft_status": draft.status}

    # ══════════════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    async def _require_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> HomeServiceBookingDraft:
        draft = await self.db.get(HomeServiceBookingDraft, draft_id)
        if not draft:
            raise ServiceOSException(ERR_DRAFT_NOT_FOUND,
                f"Booking draft '{draft_id}' not found.", status_code=404)
        if customer_id and draft.customer_id and draft.customer_id != customer_id:
            raise ServiceOSException(ERR_DRAFT_ACCESS_DENIED,
                "You do not have access to this booking draft.", status_code=403)
        return draft

    def _assert_not_terminal(self, draft: HomeServiceBookingDraft) -> None:
        if draft.status in TERMINAL_STATUSES:
            raise ServiceOSException(
                ERR_DRAFT_TERMINAL,
                f"Draft is in terminal status '{draft.status}' and cannot be modified.",
                status_code=422,
            )

    async def _get_offering(self, offering_id: uuid.UUID):
        from app.engines.admin_catalog.models import MasterService
        offering = await self.db.get(MasterService, offering_id)
        if not offering or not offering.is_active:
            raise ServiceOSException(ERR_OFFERING_INVALID,
                "Offering not found or inactive.", status_code=404)
        return offering

    def _get_required_field_list(self, offering) -> list[str]:
        """Return list of required field names based on offering config."""
        fields = ["issue_summary", "city"]
        if offering.is_type_required:
            fields.append("offering_type_id")
        if offering.is_brand_required:
            fields.append("brand_id")
        if offering.requires_schedule:
            fields.append("preferred_date")
        return fields

    def _compute_missing_fields(self, draft: HomeServiceBookingDraft, offering) -> list[str]:
        """Return names of required fields not yet filled."""
        missing = []
        if not draft.issue_summary:
            missing.append("issue_summary")
        if not draft.city:
            missing.append("city")
        if offering.is_type_required and not draft.offering_type_id:
            missing.append("offering_type_id")
        if offering.is_brand_required and not draft.brand_id:
            missing.append("brand_id")
        if offering.requires_schedule and not draft.preferred_date:
            missing.append("preferred_date")
        return missing

    async def _compute_price_snapshot(self, draft: HomeServiceBookingDraft, offering) -> dict:
        """
        Build price estimate from offering defaults + optional city floor check.
        Backend is source of truth. Frontend/DeepSeek price is NEVER used.
        """
        from app.engines.pricing.models import CityTierConfig
        from app.engines.admin_catalog.models import ServiceCategory

        cat = await self.db.get(ServiceCategory, draft.category_id)
        cat_name = cat.name if cat else "home_services"

        # Check city tier floor
        floor_row = (await self.db.execute(
            select(CityTierConfig).where(
                CityTierConfig.city_name.ilike(draft.city or ""),
                CityTierConfig.service_category.ilike(cat_name),
                CityTierConfig.is_active.is_(True),
            )
        )).scalars().first()

        floor_price  = float(floor_row.floor_price) if floor_row else 0.0
        pricing_model = offering.pricing_model or "visit_fee_plus_quote"

        if pricing_model == PRICING_MODEL_VISIT_FEE:
            base  = max(float(offering.visit_fee), floor_price)
            note  = "Visit/inspection fee. Final repair quote shared after technician check."
        elif pricing_model == PRICING_MODEL_FIXED:
            base  = max(float(offering.base_price), floor_price)
            note  = "Fixed price service."
        else:
            base  = max(float(offering.base_price), floor_price)
            note  = "Estimated price."

        min_price = float(offering.min_price) if offering.min_price else base
        max_price = float(offering.max_price) if offering.max_price else None

        return {
            "pricing_model":   pricing_model,
            "visit_fee":       base if pricing_model == PRICING_MODEL_VISIT_FEE else 0,
            "base_price":      base,
            "min_price":       min_price,
            "max_price":       max_price,
            "currency":        "INR",
            "city_tier":       floor_row.tier if floor_row else "tier_3",
            "note":            note,
            "display_price":   f"₹{int(base)}",
            "source":          "backend_catalog",
        }

    async def _resolve_address_snapshot(
        self, draft: HomeServiceBookingDraft, address_id: uuid.UUID,
    ) -> None:
        """Load address record and copy into draft snapshot."""
        from app.engines.serviceability.models import CustomerAddress
        addr = await self.db.get(CustomerAddress, address_id)
        if addr:
            draft.address_id = addr.id
            draft.city       = addr.city
            draft.zipcode    = addr.zipcode
            draft.address_snapshot = {
                "address_line_1": addr.address_line_1,
                "address_line_2": addr.address_line_2,
                "landmark":       addr.landmark,
                "city":           addr.city,
                "state":          addr.state,
                "zipcode":        addr.zipcode,
                "country":        addr.country,
                "name":           addr.name,
                "phone":          addr.phone,
            }

    async def _enrich_draft(self, draft: HomeServiceBookingDraft) -> dict:
        """Return draft dict with offering name/slug attached."""
        from app.engines.admin_catalog.models import MasterService, ServiceCategory
        result = draft.to_dict()
        offering = await self.db.get(MasterService, draft.offering_id)
        if offering:
            result["offering_name"]      = offering.service_name
            result["offering_slug"]      = offering.slug
            result["required_fields"]    = self._get_required_field_list(offering)
            result["pricing_model"]      = offering.pricing_model
        cat = await self.db.get(ServiceCategory, draft.category_id)
        if cat:
            result["category_name"] = cat.name
            result["category_slug"] = cat.slug
        return result

    async def _emit_event(
        self,
        draft_id: uuid.UUID,
        actor_type: str,
        event_type: str,
        old_value: dict | None = None,
        new_value: dict | None = None,
        message: str | None = None,
    ) -> None:
        try:
            event = HomeServiceBookingDraftEvent(
                id=uuid.uuid4(),
                draft_id=draft_id,
                actor_type=actor_type,
                event_type=event_type,
                old_value=old_value,
                new_value=new_value,
                message=message,
                request_id=self.request_id,
            )
            self.db.add(event)
            await self.db.flush()
        except Exception as exc:
            logger.warning("home_service.event_failed", error=str(exc))
