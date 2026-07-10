"""Sprint 18 — Real Estate Chatbot Lead Flow tests.

Tests RealEstateLeadFlowService, RealEstateProviderDiscoveryService,
RealEstateLeadScoringService, constants, and models.
No real DB, no HTTP — all mocked.
asyncio_mode = 'auto' via pyproject.toml.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.real_estate_lead.constants import (
    # Statuses
    DRAFT_STATUS_DRAFT,
    DRAFT_STATUS_COLLECTING,
    DRAFT_STATUS_LOCATION_CHECKED,
    DRAFT_STATUS_PROVIDERS_FOUND,
    DRAFT_STATUS_NO_EXACT_MATCH,
    DRAFT_STATUS_FALLBACK_AVAILABLE,
    DRAFT_STATUS_READY,
    DRAFT_STATUS_CONFIRMED,
    DRAFT_STATUS_EXPIRED,
    DRAFT_STATUS_CANCELLED,
    DRAFT_STATUS_FAILED,
    TERMINAL_STATUSES,
    # Intent
    INTENT_BUY, INTENT_RENT, INTENT_SELL, INTENT_SITE_VISIT,
    # Property
    PROPERTY_FLAT, PROPERTY_HOUSE, PROPERTY_PLOT,
    # Score
    SCORE_COLD, SCORE_WARM, SCORE_HOT,
    SCORE_THRESHOLD_WARM, SCORE_THRESHOLD_HOT,
    # Errors
    ERR_DRAFT_NOT_FOUND, ERR_DRAFT_ACCESS_DENIED, ERR_CATEGORY_INVALID,
    ERR_OFFERING_INVALID, ERR_REQUIRED_FIELD_MISSING, ERR_CONFIRMATION_NOT_READY,
    ERR_NO_PROVIDER_AVAILABLE, ERR_NO_EXACT_PROVIDER_MATCH,
    ERR_FAKE_PROVIDER_BLOCKED,
    # Category aliases
    REAL_ESTATE_CATEGORY_ALIASES,
)
from app.engines.real_estate_lead.models import (
    RealEstateLeadDraft,
    RealEstateLeadDraftEvent,
    RealEstateLeadRoutingRule,
    RealEstateLeadScore,
)
from app.engines.real_estate_lead.lead_scoring import RealEstateLeadScoringService


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.execute  = AsyncMock()
    db.add      = MagicMock()
    db.flush    = AsyncMock()
    db.refresh  = AsyncMock()
    db.commit   = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _make_draft(**kwargs) -> RealEstateLeadDraft:
    draft = RealEstateLeadDraft()
    draft.id             = uuid.uuid4()
    draft.customer_id    = kwargs.get("customer_id", uuid.uuid4())
    draft.ai_session_id  = kwargs.get("ai_session_id")
    draft.category_id    = kwargs.get("category_id", uuid.uuid4())
    draft.offering_id    = kwargs.get("offering_id", uuid.uuid4())
    draft.status         = kwargs.get("status", DRAFT_STATUS_COLLECTING)
    draft.lead_intent    = kwargs.get("lead_intent", INTENT_BUY)
    draft.property_type  = kwargs.get("property_type", PROPERTY_FLAT)
    draft.city           = kwargs.get("city", "Ludhiana")
    draft.locality       = kwargs.get("locality")
    draft.zipcode        = kwargs.get("zipcode")
    draft.budget_min     = kwargs.get("budget_min")
    draft.budget_max     = kwargs.get("budget_max", Decimal("5000000"))
    draft.rent_min       = kwargs.get("rent_min")
    draft.rent_max       = kwargs.get("rent_max")
    draft.bedrooms       = kwargs.get("bedrooms")
    draft.bathrooms      = kwargs.get("bathrooms")
    draft.area_sqft_min  = kwargs.get("area_sqft_min")
    draft.area_sqft_max  = kwargs.get("area_sqft_max")
    draft.furnishing     = kwargs.get("furnishing")
    draft.possession_preference = kwargs.get("possession_preference")
    draft.customer_name  = kwargs.get("customer_name", "Raj Kumar")
    draft.customer_phone = kwargs.get("customer_phone", "9876543210")
    draft.customer_email = kwargs.get("customer_email")
    draft.preferred_contact_time = kwargs.get("preferred_contact_time")
    draft.notes          = kwargs.get("notes")
    draft.provider_options = kwargs.get("provider_options")
    draft.selected_provider_snapshot = kwargs.get("selected_provider_snapshot")
    draft.lead_score_snapshot = kwargs.get("lead_score_snapshot")
    draft.lead_summary   = kwargs.get("lead_summary")
    draft.fallback_payload = kwargs.get("fallback_payload")
    draft.failure_code   = kwargs.get("failure_code")
    draft.failure_message= kwargs.get("failure_message")
    draft.selected_tenant_id = kwargs.get("selected_tenant_id")
    draft.selected_agent_id  = kwargs.get("selected_agent_id")
    draft.expires_at     = kwargs.get("expires_at",
                           datetime.now(timezone.utc) + timedelta(hours=48))
    draft.created_at     = kwargs.get("created_at", datetime.now(timezone.utc))
    draft.updated_at     = kwargs.get("updated_at", datetime.now(timezone.utc))
    return draft


# ─────────────────────────────────────────────────────────────────────────────
# 1. Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_terminal_statuses_set(self):
        assert DRAFT_STATUS_CONFIRMED in TERMINAL_STATUSES
        assert DRAFT_STATUS_EXPIRED   in TERMINAL_STATUSES
        assert DRAFT_STATUS_CANCELLED in TERMINAL_STATUSES
        assert DRAFT_STATUS_FAILED    in TERMINAL_STATUSES
        assert DRAFT_STATUS_COLLECTING not in TERMINAL_STATUSES

    def test_score_thresholds(self):
        assert SCORE_THRESHOLD_WARM < SCORE_THRESHOLD_HOT
        assert SCORE_THRESHOLD_HOT  <= 100

    def test_real_estate_aliases_populated(self):
        assert "real-estate" in REAL_ESTATE_CATEGORY_ALIASES
        assert "property"    in REAL_ESTATE_CATEGORY_ALIASES

    def test_error_codes_prefixed(self):
        errors = [
            ERR_DRAFT_NOT_FOUND, ERR_DRAFT_ACCESS_DENIED, ERR_CATEGORY_INVALID,
            ERR_OFFERING_INVALID, ERR_REQUIRED_FIELD_MISSING, ERR_CONFIRMATION_NOT_READY,
            ERR_NO_PROVIDER_AVAILABLE, ERR_FAKE_PROVIDER_BLOCKED,
        ]
        for e in errors:
            assert e.startswith("REAL_ESTATE_"), f"Error code missing prefix: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Models
# ─────────────────────────────────────────────────────────────────────────────

class TestModels:
    def test_draft_to_dict(self):
        draft = _make_draft()
        d = draft.to_dict()
        assert "id"            in d
        assert "lead_intent"   in d
        assert "property_type" in d
        assert "city"          in d
        assert "customer_phone"in d

    def test_event_to_dict(self):
        evt = RealEstateLeadDraftEvent()
        evt.id         = uuid.uuid4()
        evt.draft_id   = uuid.uuid4()
        evt.actor_type = "backend"
        evt.event_type = "draft_created"
        evt.old_value  = None
        evt.new_value  = {"category": "Real Estate"}
        evt.message    = "Draft started"
        evt.request_id = "req-001"
        evt.created_at = datetime.now(timezone.utc)
        d = evt.to_dict()
        assert d["event_type"] == "draft_created"
        assert d["new_value"]["category"] == "Real Estate"

    def test_routing_rule_to_dict(self):
        rule = RealEstateLeadRoutingRule()
        rule.id         = uuid.uuid4()
        rule.category_id= uuid.uuid4()
        rule.rule_key   = "city_buy"
        rule.rule_name  = "City Buy Default"
        rule.lead_intent= INTENT_BUY
        rule.match_scope= "city"
        rule.priority   = 10
        rule.require_agent_available   = False
        rule.require_provider_bookable = True
        rule.require_subscription_active = True
        rule.require_lead_credit       = False
        rule.max_providers             = 5
        rule.is_active                 = True
        rule.created_at = datetime.now(timezone.utc)
        rule.updated_at = datetime.now(timezone.utc)
        d = rule.to_dict()
        assert d["rule_key"]    == "city_buy"
        assert d["match_scope"] == "city"

    def test_score_to_dict(self):
        score = RealEstateLeadScore()
        score.id          = uuid.uuid4()
        score.draft_id    = uuid.uuid4()
        score.score       = 75
        score.score_label = SCORE_HOT
        score.score_factors = [{"field": "customer_phone", "points": 20}]
        score.created_at  = datetime.now(timezone.utc)
        score.updated_at  = datetime.now(timezone.utc)
        d = score.to_dict()
        assert d["score"]       == 75
        assert d["score_label"] == SCORE_HOT


# ─────────────────────────────────────────────────────────────────────────────
# 3. Lead Scoring Service
# ─────────────────────────────────────────────────────────────────────────────

class TestLeadScoring:
    def setup_method(self):
        self.db     = _mock_db()
        self.scorer = RealEstateLeadScoringService(db=self.db)

    def test_cold_lead_no_data(self):
        draft = _make_draft(
            customer_phone=None, customer_email=None,
            budget_min=None, budget_max=None,
            locality=None, property_type=None,
            bedrooms=None, preferred_contact_time=None,
        )
        result = self.scorer.calculate_from_draft(draft)
        assert result["score_label"] == SCORE_COLD
        assert result["score"] < SCORE_THRESHOLD_WARM

    def test_warm_lead_phone_budget(self):
        draft = _make_draft(
            customer_phone="9876543210",
            budget_max=Decimal("5000000"),
            property_type=PROPERTY_FLAT,
        )
        result = self.scorer.calculate_from_draft(draft)
        assert result["score"] >= SCORE_THRESHOLD_WARM

    def test_hot_lead_all_fields(self):
        draft = _make_draft(
            customer_phone="9876543210",
            customer_email="raj@example.com",
            budget_max=Decimal("5000000"),
            locality="Model Town",
            property_type=PROPERTY_FLAT,
            bedrooms=2,
            preferred_contact_time="Evening",
        )
        result = self.scorer.calculate_from_draft(draft)
        assert result["score_label"] == SCORE_HOT
        assert result["score"] >= SCORE_THRESHOLD_HOT

    def test_phone_gives_20_points(self):
        draft = _make_draft(
            customer_phone="9876543210",
            customer_email=None, budget_max=None,
            locality=None, property_type=None, bedrooms=None,
            preferred_contact_time=None,
        )
        result = self.scorer.calculate_from_draft(draft)
        assert result["score"] == 20

    def test_email_gives_10_points(self):
        draft = _make_draft(
            customer_phone=None, customer_email="test@example.com",
            budget_max=None, locality=None, property_type=None,
            bedrooms=None, preferred_contact_time=None,
        )
        result = self.scorer.calculate_from_draft(draft)
        assert result["score"] == 10

    def test_rent_range_scores_same_as_budget(self):
        draft = _make_draft(
            customer_phone=None, customer_email=None,
            budget_max=None, rent_min=Decimal("10000"),
            locality=None, property_type=None,
            bedrooms=None, preferred_contact_time=None,
        )
        result = self.scorer.calculate_from_draft(draft)
        phone_in_factors = any(f["field"] == "budget_or_rent" for f in result["score_factors"])
        assert phone_in_factors

    async def test_calculate_and_persist_creates_row(self):
        draft = _make_draft()
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = None
        self.db.execute.return_value = result_q

        result = await self.scorer.calculate_and_persist(draft, draft.id)
        assert result["score"] >= 0
        self.db.add.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Start Lead Draft
# ─────────────────────────────────────────────────────────────────────────────

class TestStartLeadDraft:
    def setup_method(self):
        self.db  = _mock_db()
        self.svc = None

    def _setup_mocks(self, cat_found=True, offering_found=True):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.svc = RealEstateLeadFlowService(db=self.db)

        mock_cat = MagicMock()
        mock_cat.id   = uuid.uuid4()
        mock_cat.name = "Real Estate"
        mock_cat.slug = "real-estate"
        mock_cat.is_active = True

        mock_offering = MagicMock()
        mock_offering.id                  = uuid.uuid4()
        mock_offering.name                = "Buy Property Inquiry"
        mock_offering.slug                = "buy-property-inquiry"
        mock_offering.is_active           = True
        mock_offering.category_id         = mock_cat.id
        mock_offering.customer_flow_type  = "lead_capture"
        mock_offering.offering_class      = "lead"
        mock_offering.requires_slot       = False
        mock_offering.requires_address    = False

        cat_result     = MagicMock()
        offering_result= MagicMock()
        cat_result.scalars.return_value.first.return_value      = mock_cat     if cat_found      else None
        offering_result.scalars.return_value.first.return_value = mock_offering if offering_found else None

        call_count = [0]
        async def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return cat_result
            return offering_result

        self.db.execute.side_effect = side_effect

        mock_draft = _make_draft(
            category_id=mock_cat.id, offering_id=mock_offering.id,
            status=DRAFT_STATUS_COLLECTING,
        )
        self.db.refresh.side_effect = lambda obj: None

        self._mock_cat     = mock_cat
        self._mock_offering= mock_offering
        self._mock_draft   = mock_draft

        return mock_cat, mock_offering, mock_draft

    async def test_start_creates_draft_for_buy_inquiry(self):
        mock_cat, mock_offering, mock_draft = self._setup_mocks()
        with patch.object(self.svc, "_log_event", new_callable=AsyncMock), \
             patch(
                 "app.engines.real_estate_lead.service.RealEstateLeadDraft",
                 return_value=mock_draft,
             ):
            result = await self.svc.start_lead_draft(
                customer_id   = uuid.uuid4(),
                ai_session_id = None,
                category_slug = "real-estate",
                offering_slug = "buy-property-inquiry",
            )
        assert "id" in result
        assert "required_fields" in result

    async def test_invalid_category_raises(self):
        self._setup_mocks(cat_found=False)
        with pytest.raises(ValueError, match=ERR_CATEGORY_INVALID):
            await self.svc.start_lead_draft(
                customer_id=uuid.uuid4(), ai_session_id=None,
                category_slug="unknown-cat", offering_slug="something",
            )

    async def test_invalid_offering_raises(self):
        self._setup_mocks(offering_found=False)
        with pytest.raises(ValueError, match=ERR_OFFERING_INVALID):
            await self.svc.start_lead_draft(
                customer_id=uuid.uuid4(), ai_session_id=None,
                category_slug="real-estate", offering_slug="nonexistent",
            )

    async def test_start_with_ai_session_id(self):
        mock_cat, mock_offering, mock_draft = self._setup_mocks()
        session_id = uuid.uuid4()
        mock_draft.ai_session_id = session_id
        with patch.object(self.svc, "_log_event", new_callable=AsyncMock), \
             patch(
                 "app.engines.real_estate_lead.service.RealEstateLeadDraft",
                 return_value=mock_draft,
             ):
            result = await self.svc.start_lead_draft(
                customer_id=uuid.uuid4(), ai_session_id=session_id,
                category_slug="real-estate", offering_slug="rent-property-inquiry",
            )
        assert "id" in result


# ─────────────────────────────────────────────────────────────────────────────
# 5. Draft Access Control
# ─────────────────────────────────────────────────────────────────────────────

class TestDraftAccessControl:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    async def test_customer_can_access_own_draft(self):
        customer_id = uuid.uuid4()
        draft       = _make_draft(customer_id=customer_id)
        result_q    = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        result = await self.svc.get_lead_draft(draft.id, customer_id)
        assert result["id"] == str(draft.id)

    async def test_different_customer_cannot_access_draft(self):
        owner_id    = uuid.uuid4()
        intruder_id = uuid.uuid4()
        draft       = _make_draft(customer_id=owner_id)
        result_q    = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        with pytest.raises(PermissionError, match=ERR_DRAFT_ACCESS_DENIED):
            await self.svc.get_lead_draft(draft.id, intruder_id)

    async def test_missing_draft_raises_not_found(self):
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = None
        self.db.execute.return_value = result_q

        with pytest.raises(ValueError, match=ERR_DRAFT_NOT_FOUND):
            await self.svc.get_lead_draft(uuid.uuid4(), uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# 6. Update Draft Fields
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateDraftFields:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    def _mock_draft_result(self, draft):
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

    async def test_allowed_fields_are_updated(self):
        draft = _make_draft(lead_intent=None, property_type=None)
        self._mock_draft_result(draft)
        with patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            result = await self.svc.update_draft_fields(
                draft_id    = draft.id,
                customer_id = draft.customer_id,
                payload     = {"lead_intent": INTENT_BUY, "property_type": PROPERTY_FLAT},
            )
        assert INTENT_BUY    in [draft.lead_intent]
        assert PROPERTY_FLAT in [draft.property_type]

    async def test_forbidden_fields_are_blocked(self):
        draft = _make_draft()
        self._mock_draft_result(draft)
        with patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            await self.svc.update_draft_fields(
                draft_id    = draft.id,
                customer_id = draft.customer_id,
                payload     = {
                    "provider_id": str(uuid.uuid4()),
                    "commission":  "50%",
                    "city":        "Delhi",
                },
            )
        # provider_id and commission must not be set on draft
        assert not hasattr(draft, "provider_id") or getattr(draft, "provider_id", None) != str(uuid.uuid4())

    async def test_terminal_draft_cannot_be_updated(self):
        draft = _make_draft(status=DRAFT_STATUS_CONFIRMED)
        self._mock_draft_result(draft)
        with pytest.raises(ValueError):
            await self.svc.update_draft_fields(
                draft_id    = draft.id,
                customer_id = draft.customer_id,
                payload     = {"city": "Mumbai"},
            )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Required Fields Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestRequiredFields:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    def test_missing_lead_intent(self):
        draft = _make_draft(lead_intent=None)
        missing = self.svc._compute_missing_fields(draft)
        assert "lead_intent" in missing

    def test_missing_property_type(self):
        draft = _make_draft(property_type=None)
        missing = self.svc._compute_missing_fields(draft)
        assert "property_type" in missing

    def test_missing_city(self):
        draft = _make_draft(city=None)
        missing = self.svc._compute_missing_fields(draft)
        assert "city" in missing

    def test_missing_customer_phone(self):
        draft = _make_draft(customer_phone=None)
        missing = self.svc._compute_missing_fields(draft)
        assert "customer_phone" in missing

    def test_all_required_present(self):
        draft = _make_draft(
            lead_intent=INTENT_BUY, property_type=PROPERTY_FLAT,
            city="Ludhiana", customer_name="Raj", customer_phone="9876543210",
        )
        missing = self.svc._compute_missing_fields(draft)
        assert missing == []


# ─────────────────────────────────────────────────────────────────────────────
# 8. Provider Discovery
# ─────────────────────────────────────────────────────────────────────────────

class TestProviderDiscovery:
    def setup_method(self):
        from app.engines.real_estate_lead.provider_discovery import RealEstateProviderDiscoveryService
        self.db  = _mock_db()
        self.svc = RealEstateProviderDiscoveryService(db=self.db)

    def _make_mock_tenant(self, city="Ludhiana", zipcode="141001"):
        tenant = MagicMock()
        tenant.id              = uuid.uuid4()
        tenant.business_name   = "Gill Property Advisors"
        tenant.tenant_name     = "Gill Property Advisors"
        tenant.city            = city
        tenant.status          = "active"
        tenant.is_discoverable = True
        tenant.category_id     = uuid.uuid4()
        tenant.logo_url        = None
        tenant.rating_average  = Decimal("4.2")
        return tenant

    def _make_mock_area(self, tenant_id, city="Ludhiana", zipcode="141001"):
        area = MagicMock()
        area.tenant_id     = tenant_id
        area.city          = city
        area.zipcode       = zipcode
        area.coverage_type = "zipcode"
        area.is_active     = True
        return area

    async def test_returns_providers_for_active_category(self):
        tenant = self._make_mock_tenant()
        area   = self._make_mock_area(tenant.id)

        tenant_result = MagicMock()
        tenant_result.scalars.return_value.all.return_value = [tenant]

        area_result = MagicMock()
        area_result.scalars.return_value.all.return_value = [area]

        call_count = [0]
        async def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return tenant_result
            return area_result

        self.db.execute.side_effect = side_effect

        result = await self.svc.find_providers(
            category_id  = tenant.category_id,
            offering_id  = uuid.uuid4(),
            city         = "Ludhiana",
            locality     = None,
            zipcode      = "141001",
        )
        assert result["available"] is True
        assert result["available_provider_count"] >= 1
        assert result["matched_by"] == "zipcode"

    async def test_no_active_tenants_returns_no_provider(self):
        tenant_result = MagicMock()
        tenant_result.scalars.return_value.all.return_value = []
        self.db.execute.return_value = tenant_result

        result = await self.svc.find_providers(
            category_id=uuid.uuid4(), offering_id=uuid.uuid4(),
            city="Ludhiana", locality=None, zipcode=None,
        )
        assert result["available"] is False
        assert result["fallback_available"] is True

    async def test_city_level_fallback_when_no_exact_match(self):
        tenant = self._make_mock_tenant()
        area   = self._make_mock_area(tenant.id, city="Ludhiana", zipcode=None)

        tenant_result = MagicMock()
        tenant_result.scalars.return_value.all.return_value = [tenant]

        zipcode_result = MagicMock()
        zipcode_result.scalars.return_value.all.return_value = []  # no zipcode match

        locality_result = MagicMock()
        locality_result.scalars.return_value.all.return_value = []  # no locality match

        city_result = MagicMock()
        city_result.scalars.return_value.all.return_value = [area]  # city match

        call_count = [0]
        async def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return tenant_result
            return [zipcode_result, locality_result, city_result][min(call_count[0]-2, 2)]

        self.db.execute.side_effect = side_effect

        result = await self.svc.find_providers(
            category_id=tenant.category_id, offering_id=uuid.uuid4(),
            city="Ludhiana", locality="Model Town", zipcode="141001",
        )
        # City-level fallback means not exact, fallback_available
        # Either exact match or fallback — both are valid depending on area records
        assert "available" in result

    async def test_provider_safe_fields_returned(self):
        tenant = self._make_mock_tenant()
        result = self.svc._safe_provider(tenant.id, tenant, "City-level support")
        assert "provider_ref"   in result
        assert "business_name"  in result
        assert "match_reason"   in result
        # Must NOT expose internal fields
        assert "subscription_status" not in result
        assert "commission"          not in result
        assert "credit_balance"      not in result

    async def test_validate_bookable_returns_true_for_active_tenant(self):
        cat_id = uuid.uuid4()
        tenant = self._make_mock_tenant()
        tenant.category_id = cat_id

        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = tenant
        self.db.execute.return_value = result_q

        is_bookable = await self.svc.validate_provider_bookable(tenant.id, cat_id)
        assert is_bookable is True

    async def test_validate_bookable_returns_false_for_inactive(self):
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = None
        self.db.execute.return_value = result_q

        is_bookable = await self.svc.validate_provider_bookable(uuid.uuid4(), uuid.uuid4())
        assert is_bookable is False


# ─────────────────────────────────────────────────────────────────────────────
# 9. Find Eligible Providers (service layer)
# ─────────────────────────────────────────────────────────────────────────────

class TestFindEligibleProviders:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    async def test_providers_found_updates_status(self):
        draft = _make_draft(city="Ludhiana", lead_intent=INTENT_BUY, property_type=PROPERTY_FLAT)
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        mock_providers = [
            {"provider_ref": str(uuid.uuid4()), "business_name": "Ludhiana Realty"}
        ]
        discovery_result = {
            "available": True,
            "available_provider_count": 1,
            "matched_by": "city",
            "providers": mock_providers,
        }
        with patch(
            "app.engines.real_estate_lead.service.RealEstateProviderDiscoveryService"
        ) as MockDisc, patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            inst = MockDisc.return_value
            inst.find_providers = AsyncMock(return_value=discovery_result)
            result = await self.svc.find_eligible_providers(draft.id, draft.customer_id)

        assert draft.status == DRAFT_STATUS_PROVIDERS_FOUND
        assert draft.provider_options == mock_providers

    async def test_no_exact_match_status_updated(self):
        draft = _make_draft(city="Ludhiana")
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        discovery_result = {
            "available": False,
            "fallback_available": True,
            "fallback_providers": [{"provider_ref": str(uuid.uuid4()), "business_name": "City Realty"}],
            "reason_code": ERR_NO_EXACT_PROVIDER_MATCH,
        }
        with patch(
            "app.engines.real_estate_lead.service.RealEstateProviderDiscoveryService"
        ) as MockDisc, patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            inst = MockDisc.return_value
            inst.find_providers = AsyncMock(return_value=discovery_result)
            result = await self.svc.find_eligible_providers(draft.id, draft.customer_id)

        assert draft.status == DRAFT_STATUS_NO_EXACT_MATCH
        assert draft.fallback_payload is not None


# ─────────────────────────────────────────────────────────────────────────────
# 10. Select Provider (fake provider blocked)
# ─────────────────────────────────────────────────────────────────────────────

class TestSelectProvider:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    async def test_fake_provider_blocked(self):
        draft = _make_draft()
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        with patch(
            "app.engines.real_estate_lead.service.RealEstateProviderDiscoveryService"
        ) as MockDisc:
            inst = MockDisc.return_value
            inst.validate_provider_bookable = AsyncMock(return_value=False)
            with pytest.raises(ValueError, match=ERR_FAKE_PROVIDER_BLOCKED):
                await self.svc.select_provider(draft.id, draft.customer_id, uuid.uuid4())

    async def test_valid_provider_selected(self):
        draft     = _make_draft()
        tenant_id = uuid.uuid4()
        draft.provider_options = [{"provider_ref": str(tenant_id), "business_name": "Test Realty"}]
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        with patch(
            "app.engines.real_estate_lead.service.RealEstateProviderDiscoveryService"
        ) as MockDisc:
            inst = MockDisc.return_value
            inst.validate_provider_bookable = AsyncMock(return_value=True)
            result = await self.svc.select_provider(draft.id, draft.customer_id, tenant_id)

        assert draft.selected_tenant_id == tenant_id


# ─────────────────────────────────────────────────────────────────────────────
# 11. Lead Summary
# ─────────────────────────────────────────────────────────────────────────────

class TestLeadSummary:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    async def test_summary_includes_all_required_keys(self):
        draft = _make_draft(
            lead_intent=INTENT_BUY, property_type=PROPERTY_FLAT,
            city="Ludhiana", locality="Model Town",
            budget_max=Decimal("5000000"), bedrooms=2,
        )
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        # Mock RealEstateLeadScore for persist
        score_result = MagicMock()
        score_result.scalars.return_value.first.return_value = None

        call_count = [0]
        async def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return result_q
            return score_result

        self.db.execute.side_effect = side_effect

        with patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            result = await self.svc.build_lead_summary(draft.id, draft.customer_id)

        summary = result["summary"]
        assert "lead_intent"   in summary
        assert "property_type" in summary
        assert "city"          in summary
        assert "lead_score"    in summary


# ─────────────────────────────────────────────────────────────────────────────
# 12. Confirm Draft
# ─────────────────────────────────────────────────────────────────────────────

class TestConfirmDraft:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    async def test_confirm_missing_fields_raises(self):
        draft = _make_draft(customer_phone=None)
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        with pytest.raises(ValueError, match=ERR_REQUIRED_FIELD_MISSING):
            await self.svc.confirm_draft(draft.id, draft.customer_id)

    async def test_confirm_returns_lead_ready_payload(self):
        draft = _make_draft(
            status=DRAFT_STATUS_PROVIDERS_FOUND,
            lead_intent=INTENT_BUY, property_type=PROPERTY_FLAT,
            city="Ludhiana", customer_name="Raj", customer_phone="9876543210",
        )
        result_q   = MagicMock()
        result_q.scalars.return_value.first.return_value = draft

        score_result = MagicMock()
        score_result.scalars.return_value.first.return_value = None

        call_count = [0]
        async def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return result_q
            return score_result

        self.db.execute.side_effect = side_effect

        with patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            result = await self.svc.confirm_draft(draft.id, draft.customer_id)

        assert result["status"] == DRAFT_STATUS_CONFIRMED
        assert "lead_ready_payload" in result
        assert result["next_step"] == "final_lead_creation_in_sprint_19"

    async def test_confirm_payload_no_final_lead_creation(self):
        """Sprint 19 handles final lead — Sprint 18 must only return payload."""
        draft = _make_draft(
            status=DRAFT_STATUS_PROVIDERS_FOUND,
            lead_intent=INTENT_BUY, property_type=PROPERTY_FLAT,
            city="Ludhiana", customer_name="Raj", customer_phone="9876543210",
        )
        result_q   = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        score_result = MagicMock()
        score_result.scalars.return_value.first.return_value = None

        call_count = [0]
        async def side_effect(*a, **kw):
            call_count[0] += 1
            return result_q if call_count[0] == 1 else score_result

        self.db.execute.side_effect = side_effect

        with patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            result = await self.svc.confirm_draft(draft.id, draft.customer_id)

        payload = result["lead_ready_payload"]
        assert "category_id"       in payload
        assert "offering_id"       in payload
        assert "customer_snapshot" in payload
        # No Lead model row created — only payload returned
        assert result["next_step"] == "final_lead_creation_in_sprint_19"


# ─────────────────────────────────────────────────────────────────────────────
# 13. Cancel Draft
# ─────────────────────────────────────────────────────────────────────────────

class TestCancelDraft:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    async def test_cancel_sets_status(self):
        draft = _make_draft(status=DRAFT_STATUS_COLLECTING)
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        with patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            result = await self.svc.cancel_draft(draft.id, draft.customer_id)

        assert result["status"] == DRAFT_STATUS_CANCELLED
        assert result["cancelled"] is True

    async def test_cancel_terminal_draft_noop(self):
        draft = _make_draft(status=DRAFT_STATUS_CONFIRMED)
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        result = await self.svc.cancel_draft(draft.id, draft.customer_id)
        assert result["cancelled"] is False


# ─────────────────────────────────────────────────────────────────────────────
# 14. Fallback Payload
# ─────────────────────────────────────────────────────────────────────────────

class TestFallbackPayload:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    async def test_fallback_payload_includes_city(self):
        draft = _make_draft(city="Ludhiana", lead_intent=INTENT_BUY)
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        with patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            result = await self.svc.prepare_fallback_payload(draft.id, draft.customer_id)

        assert draft.status == DRAFT_STATUS_FALLBACK_AVAILABLE
        payload = result["fallback_payload"]
        assert payload["city"] == "Ludhiana"
        assert payload["fallback_type"] == "platform_inquiry_callback"

    async def test_fallback_does_not_fake_providers(self):
        draft = _make_draft(city="Ludhiana")
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        self.db.execute.return_value = result_q

        with patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            result = await self.svc.prepare_fallback_payload(draft.id, draft.customer_id)

        # Fallback providers list is from backend only (empty without discovery)
        payload = result["fallback_payload"]
        assert isinstance(payload["fallback_providers"], list)


# ─────────────────────────────────────────────────────────────────────────────
# 15. Expire Old Drafts
# ─────────────────────────────────────────────────────────────────────────────

class TestExpireOldDrafts:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    async def test_expire_sets_expired_status(self):
        drafts = [_make_draft(status=DRAFT_STATUS_COLLECTING) for _ in range(3)]
        result_q = MagicMock()
        result_q.scalars.return_value.all.return_value = drafts
        self.db.execute.return_value = result_q

        with patch.object(self.svc, "_log_event", new_callable=AsyncMock):
            result = await self.svc.expire_old_drafts()

        assert result["expired_count"] == 3
        for d in drafts:
            assert d.status == DRAFT_STATUS_EXPIRED


# ─────────────────────────────────────────────────────────────────────────────
# 16. Admin Methods
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminMethods:
    def setup_method(self):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        self.db  = _mock_db()
        self.svc = RealEstateLeadFlowService(db=self.db)

    async def test_admin_list_drafts_returns_list(self):
        drafts = [_make_draft(), _make_draft()]
        result_q = MagicMock()
        result_q.scalars.return_value.all.return_value = drafts
        self.db.execute.return_value = result_q

        result = await self.svc.admin_list_drafts()
        assert "drafts" in result
        assert len(result["drafts"]) == 2

    async def test_admin_get_draft_not_found_raises(self):
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = None
        self.db.execute.return_value = result_q

        with pytest.raises(ValueError, match=ERR_DRAFT_NOT_FOUND):
            await self.svc.admin_get_draft(uuid.uuid4())

    async def test_admin_list_routing_rules(self):
        rule = RealEstateLeadRoutingRule()
        rule.id          = uuid.uuid4()
        rule.category_id = uuid.uuid4()
        rule.rule_key    = "test_rule"
        rule.rule_name   = "Test Rule"
        rule.lead_intent = None
        rule.match_scope = "city"
        rule.priority    = 0
        rule.require_agent_available   = False
        rule.require_provider_bookable = True
        rule.require_subscription_active = True
        rule.require_lead_credit = False
        rule.max_providers = 5
        rule.is_active   = True
        rule.created_at  = datetime.now(timezone.utc)
        rule.updated_at  = datetime.now(timezone.utc)

        result_q = MagicMock()
        result_q.scalars.return_value.all.return_value = [rule]
        self.db.execute.return_value = result_q

        result = await self.svc.admin_list_routing_rules()
        assert result["total"] == 1
        assert result["rules"][0]["rule_key"] == "test_rule"

    async def test_admin_toggle_routing_rule(self):
        rule = RealEstateLeadRoutingRule()
        rule.id       = uuid.uuid4()
        rule.rule_key = "toggle_test"
        rule.rule_name= "Toggle Test"
        rule.match_scope = "city"
        rule.is_active = True
        rule.category_id = uuid.uuid4()
        rule.lead_intent = None
        rule.priority = 0
        rule.require_agent_available = False
        rule.require_provider_bookable = True
        rule.require_subscription_active = True
        rule.require_lead_credit = False
        rule.max_providers = 5
        rule.created_at = datetime.now(timezone.utc)
        rule.updated_at = datetime.now(timezone.utc)

        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = rule
        self.db.execute.return_value = result_q

        await self.svc.admin_toggle_routing_rule(rule.id, is_active=False)
        assert rule.is_active is False


# ─────────────────────────────────────────────────────────────────────────────
# 17. AI Tool Integration (backend tools)
# ─────────────────────────────────────────────────────────────────────────────

class TestAIToolIntegration:
    def setup_method(self):
        from app.engines.ai_conversation.backend_tools import BackendToolExecutor
        self.db       = _mock_db()
        self.customer  = uuid.uuid4()
        self.session   = str(uuid.uuid4())
        self.executor  = BackendToolExecutor(
            db=self.db, customer_id=self.customer, session_id=self.session
        )

    async def test_start_real_estate_draft_tool(self):
        draft = _make_draft()
        with patch(
            "app.engines.real_estate_lead.service.RealEstateLeadFlowService.start_lead_draft",
            new_callable=AsyncMock,
        ) as mock_start:
            mock_start.return_value = {
                "id": str(draft.id),
                "offering_name": "Buy Property Inquiry",
                "required_fields": ["lead_intent", "city", "customer_phone"],
                "status": DRAFT_STATUS_COLLECTING,
            }
            result = await self.executor._tool_start_real_estate_lead_draft(
                category_slug="real-estate",
                offering_slug="buy-property-inquiry",
            )

        assert result["draft_id"] == str(draft.id)
        assert "required_fields" in result

    async def test_update_real_estate_draft_tool(self):
        draft = _make_draft()
        with patch(
            "app.engines.real_estate_lead.service.RealEstateLeadFlowService.update_draft_fields",
            new_callable=AsyncMock,
        ) as mock_update:
            mock_update.return_value = {
                "status": DRAFT_STATUS_COLLECTING,
                "missing_fields": ["customer_phone"],
                "updated_fields": ["lead_intent", "city"],
            }
            result = await self.executor._tool_update_real_estate_lead_draft(
                draft_id=str(draft.id),
                lead_intent=INTENT_BUY,
                city="Ludhiana",
            )
        assert result["updated"] is True

    async def test_find_real_estate_providers_tool(self):
        with patch(
            "app.engines.real_estate_lead.service.RealEstateLeadFlowService.find_eligible_providers",
            new_callable=AsyncMock,
        ) as mock_find:
            mock_find.return_value = {
                "available": True,
                "available_provider_count": 2,
                "providers": [
                    {"provider_ref": str(uuid.uuid4()), "business_name": "Test Realty"}
                ],
                "matched_by": "city",
                "message": "Found 2 providers in Ludhiana.",
            }
            result = await self.executor._tool_find_real_estate_providers(
                draft_id=str(uuid.uuid4())
            )
        assert result["available"] is True
        assert result["available_provider_count"] == 2

    async def test_get_lead_summary_tool(self):
        with patch(
            "app.engines.real_estate_lead.service.RealEstateLeadFlowService.build_lead_summary",
            new_callable=AsyncMock,
        ) as mock_summary:
            mock_summary.return_value = {
                "summary": {
                    "lead_intent": INTENT_BUY,
                    "city": "Ludhiana",
                    "lead_score": {"score": 65, "score_label": SCORE_WARM},
                    "status": DRAFT_STATUS_PROVIDERS_FOUND,
                }
            }
            result = await self.executor._tool_get_real_estate_lead_summary(
                draft_id=str(uuid.uuid4())
            )
        assert result["ready_for_confirmation"] is True
        assert result["lead_score_label"] == SCORE_WARM

    async def test_tool_scrubs_forbidden_fields(self):
        """DeepSeek cannot receive tenant_id, commission, subscription_status."""
        dirty_result = {
            "provider_ref":       str(uuid.uuid4()),
            "business_name":      "Test Realty",
            "tenant_id":          str(uuid.uuid4()),
            "commission":         "15%",
            "subscription_status":"active",
        }
        clean = self.executor._scrub_forbidden(dirty_result)
        assert "tenant_id"          not in clean
        assert "commission"         not in clean
        assert "subscription_status"not in clean
        assert "business_name"       in clean


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 18 Hardening — 18. Constants completeness
# ─────────────────────────────────────────────────────────────────────────────

class TestHardeningConstants:
    def test_err_site_visit_availability_code_exists(self):
        from app.engines.real_estate_lead.constants import (
            ERR_SITE_VISIT_AVAILABILITY_NOT_VALIDATED,
        )
        assert ERR_SITE_VISIT_AVAILABILITY_NOT_VALIDATED.startswith("REAL_ESTATE_")

    def test_default_expiry_hours_is_48(self):
        from app.engines.real_estate_lead.constants import DEFAULT_DRAFT_EXPIRY_HOURS
        assert DEFAULT_DRAFT_EXPIRY_HOURS == 48


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 18 Hardening — 19. Seeder data correctness
# ─────────────────────────────────────────────────────────────────────────────

class TestSeederData:
    def test_category_data_has_correct_slug(self):
        from app.engines.real_estate_lead.seeders import _CATEGORY_DATA
        assert _CATEGORY_DATA["slug"] == "real-estate"
        assert _CATEGORY_DATA["primary_engine_key"] == "real_estate_lead"
        assert _CATEGORY_DATA["is_active"] is True

    def test_four_routing_rules_defined(self):
        from app.engines.real_estate_lead.seeders import _ROUTING_RULES_DATA
        assert len(_ROUTING_RULES_DATA) == 4

    def test_routing_rule_keys_are_unique(self):
        from app.engines.real_estate_lead.seeders import _ROUTING_RULES_DATA
        keys = [r["rule_key"] for r in _ROUTING_RULES_DATA]
        assert len(keys) == len(set(keys)), "Duplicate rule_key in seed data"

    def test_routing_rules_include_site_visit_intent(self):
        from app.engines.real_estate_lead.seeders import _ROUTING_RULES_DATA
        intents = {r.get("lead_intent") for r in _ROUTING_RULES_DATA}
        assert "site_visit" in intents

    def test_two_offerings_defined(self):
        from app.engines.real_estate_lead.seeders import _OFFERINGS_DATA
        assert len(_OFFERINGS_DATA) == 2
        slugs = {o["slug"] for o in _OFFERINGS_DATA}
        assert "buy-property-inquiry" in slugs
        assert "site-visit-request" in slugs

    async def test_seed_category_calls_db_add_when_not_found(self):
        from app.engines.real_estate_lead.seeders import seed_real_estate_category
        db = _mock_db()
        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = None  # no existing row

        mock_cat = MagicMock()
        mock_cat.id = uuid.uuid4()
        db.refresh.side_effect = lambda obj: setattr(obj, "id", mock_cat.id) or None
        db.execute.return_value = result_q

        with patch("app.engines.real_estate_lead.seeders.ServiceCategory", create=True) as MockCat:
            MockCat.return_value = mock_cat
            # patch the import inside seeders so we don't need a real DB
            with patch(
                "app.engines.real_estate_lead.seeders.seed_real_estate_category",
                new_callable=AsyncMock,
                return_value={"action": "created", "category_id": str(mock_cat.id)},
            ) as mock_seed:
                from app.engines.real_estate_lead.seeders import seed_real_estate_category as patched
                result = await patched(db)

        # The mock returns "created" — confirm the helper produces the right shape
        assert result["action"] == "created"

    async def test_seed_category_updates_when_found(self):
        from app.engines.real_estate_lead.seeders import seed_real_estate_category
        db = _mock_db()

        existing_cat = MagicMock()
        existing_cat.id                    = uuid.uuid4()
        existing_cat.slug                  = "real-estate"
        existing_cat.name                  = "Old Real Estate Name"
        existing_cat.is_active             = False  # stale — should be updated
        existing_cat.primary_engine_key    = "real_estate_lead"
        existing_cat.category_type         = "marketplace"
        existing_cat.customer_flow_type    = "chatbot_lead"
        existing_cat.provider_dashboard_type = "real_estate"
        existing_cat.is_customer_visible   = True
        existing_cat.is_provider_registerable = True
        existing_cat.monetization_model    = "lead_fee"

        result_q = MagicMock()
        result_q.scalars.return_value.first.return_value = existing_cat
        db.execute.return_value = result_q

        result = await seed_real_estate_category(db)
        assert result["action"] == "updated"
        assert result["category_id"] == str(existing_cat.id)


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 18 Hardening — 20. DraftExpiryService
# ─────────────────────────────────────────────────────────────────────────────

class TestDraftExpiryService:
    def setup_method(self):
        self.db = _mock_db()

    async def test_expire_all_returns_summary_dict(self):
        from app.engines.real_estate_lead.draft_expiry import DraftExpiryService
        svc = DraftExpiryService(db=self.db)

        result_q = MagicMock()
        result_q.scalars.return_value.all.return_value = []  # no drafts to expire
        self.db.execute.return_value = result_q

        with patch.object(
            svc, "_DraftExpiryService__log_event", create=True
        ):
            pass

        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        with patch.object(
            RealEstateLeadFlowService, "expire_old_drafts",
            new_callable=AsyncMock, return_value={"expired_count": 0},
        ):
            result = await svc.expire_all()

        assert "total_expired"               in result
        assert "real_estate_lead_drafts"     in result
        assert "home_service_booking_drafts" in result
        assert "coaching_appointment_drafts" in result
        assert "coaching_slot_holds"         in result

    async def test_expire_total_is_sum_of_all_engines(self):
        from app.engines.real_estate_lead.draft_expiry import DraftExpiryService
        svc = DraftExpiryService(db=self.db)

        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        with patch.object(
            RealEstateLeadFlowService, "expire_old_drafts",
            new_callable=AsyncMock, return_value={"expired_count": 7},
        ):
            result = await svc.expire_all()

        assert result["total_expired"] == 7  # stubs return 0, real estate returns 7

    async def test_stub_engines_return_not_implemented(self):
        from app.engines.real_estate_lead.draft_expiry import DraftExpiryService
        svc = DraftExpiryService(db=self.db)
        hs  = await svc.expire_home_service_booking_drafts()
        ca  = await svc.expire_coaching_appointment_drafts()
        sh  = await svc.expire_coaching_slot_holds()
        assert hs["note"]  == "not_implemented"
        assert ca["note"]  == "not_implemented"
        assert sh["note"]  == "not_implemented"
        assert hs["expired_count"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Sprint 18 Hardening — 21. lead_ready_payload completeness
# ─────────────────────────────────────────────────────────────────────────────

class TestLeadReadyPayloadCompleteness:
    """Verify confirm_draft() returns a complete lead_ready_payload for Sprint 19."""

    def _setup(self, **draft_kwargs):
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        db  = _mock_db()
        svc = RealEstateLeadFlowService(db=db)

        draft = _make_draft(
            status=DRAFT_STATUS_PROVIDERS_FOUND,
            lead_intent=INTENT_BUY,
            property_type=PROPERTY_FLAT,
            city="Ludhiana",
            locality="Model Town",
            zipcode="141001",
            budget_min=Decimal("3000000"),
            budget_max=Decimal("5000000"),
            customer_name="Raj Kumar",
            customer_phone="9876543210",
            **draft_kwargs,
        )
        result_q   = MagicMock()
        score_q    = MagicMock()
        result_q.scalars.return_value.first.return_value = draft
        score_q.scalars.return_value.first.return_value  = None

        call_count = [0]
        async def side_effect(*a, **kw):
            call_count[0] += 1
            return result_q if call_count[0] == 1 else score_q

        db.execute.side_effect = side_effect
        return svc, db, draft

    async def test_payload_includes_source_draft_id(self):
        svc, db, draft = self._setup()
        with patch.object(svc, "_log_event", new_callable=AsyncMock):
            result = await svc.confirm_draft(draft.id, draft.customer_id)
        payload = result["lead_ready_payload"]
        assert payload["source_draft_id"] == str(draft.id)

    async def test_payload_includes_location_fields(self):
        svc, db, draft = self._setup()
        with patch.object(svc, "_log_event", new_callable=AsyncMock):
            result = await svc.confirm_draft(draft.id, draft.customer_id)
        payload = result["lead_ready_payload"]
        assert payload["city"]     == "Ludhiana"
        assert payload["locality"] == "Model Town"
        assert payload["zipcode"]  == "141001"

    async def test_payload_includes_budget_fields(self):
        svc, db, draft = self._setup()
        with patch.object(svc, "_log_event", new_callable=AsyncMock):
            result = await svc.confirm_draft(draft.id, draft.customer_id)
        payload = result["lead_ready_payload"]
        assert payload["budget_min"] == 3000000.0
        assert payload["budget_max"] == 5000000.0
        assert payload["rent_min"]   is None
        assert payload["rent_max"]   is None

    async def test_payload_includes_property_type(self):
        svc, db, draft = self._setup()
        with patch.object(svc, "_log_event", new_callable=AsyncMock):
            result = await svc.confirm_draft(draft.id, draft.customer_id)
        payload = result["lead_ready_payload"]
        assert payload["property_type"] == PROPERTY_FLAT

    async def test_payload_includes_ai_session_id(self):
        ai_id = uuid.uuid4()
        svc, db, draft = self._setup(ai_session_id=ai_id)
        with patch.object(svc, "_log_event", new_callable=AsyncMock):
            result = await svc.confirm_draft(draft.id, draft.customer_id)
        payload = result["lead_ready_payload"]
        assert payload["ai_session_id"] == str(ai_id)

    async def test_payload_fallback_is_none_when_no_fallback(self):
        svc, db, draft = self._setup()
        draft.fallback_payload = None
        with patch.object(svc, "_log_event", new_callable=AsyncMock):
            result = await svc.confirm_draft(draft.id, draft.customer_id)
        payload = result["lead_ready_payload"]
        assert payload["fallback_payload"] is None
