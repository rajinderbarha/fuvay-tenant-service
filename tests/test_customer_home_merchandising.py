from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.engines.customer_home.merchandising import (
    CustomerHomeMerchandisingService,
    HOME_PLACEMENTS,
    HomeSectionWrite,
    HomePlacementWrite,
    default_home_composition,
)
from app.engines.customer_home.service import CustomerHomeService
from app.engines.marketing_automation.models import (
    MarketingCampaignMessage,
    MarketingCampaignRule,
)


def valid_body(**overrides) -> HomePlacementWrite:
    data = {
        "title": "Monsoon Home Care",
        "subtitle": "Keep your home comfortable through the rains.",
        "placement": "home_hero",
        "variant": "cinematic",
        "theme_key": "coral",
        "image_url": "https://res.cloudinary.com/fuvay/image/upload/monsoon.jpg",
        "action_label": "Book now",
        "zipcodes": ["141001", "141002"],
    }
    data.update(overrides)
    return HomePlacementWrite(**data)


def test_home_placement_contract_rejects_unsafe_or_unrenderable_content() -> None:
    with pytest.raises(ValidationError, match="HTTPS CDN URL"):
        valid_body(image_url="http://localhost:8000/banner.png")
    with pytest.raises(ValidationError, match="not valid"):
        valid_body(variant="arbitrary_html")
    with pytest.raises(ValidationError, match="6 digits"):
        valid_body(zipcodes=["14100"])
    with pytest.raises(ValidationError, match="cannot advertise a provider price"):
        valid_body(offer_text="From ₹599")
    with pytest.raises(ValidationError, match="Unsupported Home placement"):
        valid_body(placement="home_unknown", variant="editorial")


def test_every_home_placement_has_bounded_native_variants() -> None:
    assert set(HOME_PLACEMENTS) == {
        "home_hero",
        "home_story",
        "home_spotlight",
        "home_banner",
        "home_mosaic",
        "home_collection",
        "home_notice",
        "home_trust",
        "home_global",
        "home_recommendation",
    }
    assert HOME_PLACEMENTS["home_trust"]["variants"] == ["promise"]
    assert HOME_PLACEMENTS["home_trust"]["max_active"] == 4
    for definition in HOME_PLACEMENTS.values():
        assert definition["variants"]
        assert 1 <= definition["max_active"] <= 8


def test_every_native_section_has_a_safe_backend_layout_contract() -> None:
    sections = default_home_composition()
    assert len(sections) >= 19
    assert {section["key"] for section in sections} >= {"hero", "spotlight", "master_services", "featured_problems", "trust_strip"}
    enabled = {section["key"] for section in sections if section["enabled"]}
    assert enabled == {
        "hero", "service_groups", "master_services", "nearby_services",
        "recent_bookings", "assistant", "trust_strip", "featured_problems",
        "spotlight", "featured_services", "global_services",
    }
    assert all(section["spacing"] in {"compact", "standard", "generous"} for section in sections)
    assert all(section["surface"] in {"canvas", "subtle", "raised", "brand_tint"} for section in sections)
    assert next(section for section in sections if section["key"] == "hero")["variant"] == "marketplace"
    assert next(section for section in sections if section["key"] == "service_groups")["variant"] == "compact_grid"
    assert next(section for section in sections if section["key"] == "master_services")["variant"] == "recommendation_cards"
    configured = HomeSectionWrite(
        key="hero", enabled=True, title=None, variant="edge_to_edge",
        max_items=4, spacing="generous", surface="brand_tint",
    )
    assert configured.spacing == "generous"
    assert configured.surface == "brand_tint"
    with pytest.raises(ValidationError):
        HomeSectionWrite(
            key="hero", enabled=True, variant="arbitrary_html", max_items=1,
            spacing="standard", surface="canvas",
        )


def test_spotlight_has_independent_future_ready_native_layouts() -> None:
    cinematic = HomeSectionWrite(
        key="spotlight", enabled=True, title="Seasonal spotlight",
        variant="cinematic_card", max_items=2,
    )
    split = cinematic.model_copy(update={"variant": "split_feature"})
    assert cinematic.variant == "cinematic_card"
    assert split.variant == "split_feature"


@pytest.mark.asyncio
async def test_admin_create_persists_one_marketing_source_of_truth() -> None:
    db = MagicMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    async def assign_campaign_id() -> None:
        campaign = db.add.call_args.args[0]
        campaign.id = uuid.uuid4()
        campaign.created_at = datetime.now(timezone.utc)
        campaign.updated_at = campaign.created_at

    db.flush = AsyncMock(side_effect=assign_campaign_id)
    body = valid_body(section_title="Monsoon essentials")

    result = await CustomerHomeMerchandisingService().create(
        db,
        body=body,
        actor_user_id=uuid.uuid4(),
    )

    message, rule = db.add_all.call_args.args[0]
    assert isinstance(message, MarketingCampaignMessage)
    assert isinstance(rule, MarketingCampaignRule)
    assert message.channel == "in_app"
    assert rule.rule_type == "channel"
    assert rule.rule_config["surface"] == "customer_home"
    assert rule.rule_config["placement"] == "home_hero"
    assert rule.rule_config["variant"] == "cinematic"
    assert result["section_title"] == "Monsoon essentials"
    assert result["is_active"] is False
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unserved_pin_is_not_marked_serviceable_and_has_no_campaigns() -> None:
    service = CustomerHomeService(db=MagicMock())
    service._get_default_address = AsyncMock(return_value={"zipcode": "141001", "city": "Ludhiana", "state": "Punjab"})
    service._get_enabled_verticals = AsyncMock(return_value=[])
    service._get_bookable_categories = AsyncMock(return_value=[])
    service._get_bookable_service_groups = AsyncMock(return_value=[])
    service._get_bookable_master_services = AsyncMock(return_value=[])
    service._get_active_booking_summaries = AsyncMock(return_value=[])
    service._count_active_bookings = AsyncMock(return_value=0)
    service._get_unread_notification_count = AsyncMock(return_value=0)
    service._get_home_campaigns = AsyncMock(return_value=[{"should": "not escape"}])
    service._get_quick_issues = AsyncMock(return_value=[])

    result = await service.get_home(customer_id=uuid.uuid4(), zipcode="999999")

    assert result["serviceability"] == {"zipcode": "999999", "checked": False}
    assert result["campaigns"] == []
    service._get_home_campaigns.assert_not_awaited()


@pytest.mark.asyncio
async def test_override_pin_does_not_inherit_default_city_campaign_targeting() -> None:
    service = CustomerHomeService(db=MagicMock())
    service._get_default_address = AsyncMock(return_value={"zipcode": "141001", "city": "Ludhiana", "state": "Punjab"})
    service._get_enabled_verticals = AsyncMock(return_value=[])
    service._get_bookable_categories = AsyncMock(return_value=[])
    service._get_bookable_service_groups = AsyncMock(return_value=[{"slug": "ac_services"}])
    service._get_bookable_master_services = AsyncMock(return_value=[])
    service._get_active_booking_summaries = AsyncMock(return_value=[])
    service._count_active_bookings = AsyncMock(return_value=0)
    service._get_unread_notification_count = AsyncMock(return_value=0)
    service._get_home_campaigns = AsyncMock(return_value=[])
    service._get_quick_issues = AsyncMock(return_value=[])

    result = await service.get_home(customer_id=uuid.uuid4(), zipcode="560001")

    assert result["serviceability"]["checked"] is True
    service._get_home_campaigns.assert_awaited_once_with(
        customer_id=ANY,
        city=None,
        zipcode="560001",
        allowed_service_group_slugs={"ac_services"},
    )


@pytest.mark.asyncio
async def test_home_keeps_service_groups_and_master_services_as_distinct_collections() -> None:
    """The Home discovery rail must not be reused as the recommendation grid."""
    service = CustomerHomeService(db=MagicMock())
    service._get_default_address = AsyncMock(return_value={"zipcode": "141001", "city": "Ludhiana", "state": "Punjab"})
    service._get_enabled_verticals = AsyncMock(return_value=[])
    service._get_bookable_categories = AsyncMock(return_value=[{"category_id": "category-1", "name": "Home Services"}])
    service._get_bookable_service_groups = AsyncMock(return_value=[{"service_group_id": "group-1", "slug": "ac", "name": "AC & HVAC"}])
    service._get_bookable_master_services = AsyncMock(return_value=[{"master_service_id": "service-1", "name": "AC Repair", "service_group_id": "group-1"}])
    service._get_active_booking_summaries = AsyncMock(return_value=[])
    service._count_active_bookings = AsyncMock(return_value=0)
    service._get_unread_notification_count = AsyncMock(return_value=0)
    service._get_home_campaigns = AsyncMock(return_value=[])
    service._get_quick_issues = AsyncMock(return_value=[{
        "issue_id": "issue-1", "label": "Not cooling", "category_id": "category-1",
        "category_slug": "home-services", "category_name": "Home Services", "intent": "repair",
    }])

    result = await service.get_home(customer_id=uuid.uuid4(), zipcode="141001")

    assert result["bookable_service_groups"][0]["name"] == "AC & HVAC"
    assert result["bookable_master_services"][0]["name"] == "AC Repair"
    assert result["bookable_service_groups"] != result["bookable_master_services"]
    assert "icon_url" not in result["quick_issues"][0]


def test_home_offer_projection_suppresses_provider_prices() -> None:
    assert CustomerHomeService._home_safe_offer_text("From ₹599") is None
    assert CustomerHomeService._home_safe_offer_text("Save 20% today") == "Save 20% today"
