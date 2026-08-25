"""Admin-managed, native-safe merchandising for the customer Home screen.

The native app owns layout and interaction. Administrators own content,
targeting, schedule, ordering and the approved presentation variant.  Keeping
the finite placement catalogue here prevents arbitrary HTML/JSON layouts from
becoming a remote-code or accessibility problem while still allowing the Home
screen to be operated without an app release.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.marketing_automation.constants import (
    AUDIENCE_CUSTOMERS,
    CAMP_STATUS_CANCELLED,
    CAMP_STATUS_DRAFT,
    CAMP_STATUS_RUNNING,
    CAMPAIGN_TYPE_ANNOUNCEMENT,
    CHANNEL_IN_APP,
    RULE_CHANNEL,
)
from app.engines.marketing_automation.models import (
    MarketingCampaign,
    MarketingCampaignMessage,
    MarketingCampaignRule,
)
from app.engines.settings_engine.models import PlatformSetting, SettingAuditLog

HOME_PLACEMENTS: dict[str, dict[str, Any]] = {
    "home_hero": {
        "label": "Hero slider",
        "description": "Large swipeable campaign at the top of Home.",
        "variants": ["cinematic", "split", "offer"],
        "max_active": 5,
    },
    "home_story": {
        "label": "Story rail",
        "description": "Scrollable visual stories and seasonal ideas.",
        "variants": ["landscape", "portrait"],
        "max_active": 8,
    },
    "home_spotlight": {
        "label": "Spotlight",
        "description": "A focused editorial feature with a strong call to action.",
        "variants": ["feature"],
        "max_active": 2,
    },
    "home_banner": {
        "label": "Editorial banner",
        "description": "Full-width promotion placed lower on Home.",
        "variants": ["editorial", "ribbon"],
        "max_active": 4,
    },
    "home_mosaic": {
        "label": "Creative mosaic",
        "description": "Asymmetric image-led collection for festivals or launches.",
        "variants": ["mosaic"],
        "max_active": 3,
    },
    "home_collection": {
        "label": "Curated collection",
        "description": "Scrollable themed cards for a reusable campaign collection.",
        "variants": ["collection"],
        "max_active": 8,
    },
    "home_notice": {
        "label": "Announcement strip",
        "description": "Compact operational or promotional notice.",
        "variants": ["notice"],
        "max_active": 2,
    },
    "home_trust": {
        "label": "Customer assurance item",
        "description": "A verified customer promise displayed in the Home assurance strip.",
        "variants": ["promise"],
        "max_active": 4,
    },
}

HOME_THEME_KEYS = {"ink", "citrus", "coral", "mint", "violet", "sky", "sand"}
HOME_SECTION_SPACING = {"compact", "standard", "generous"}
HOME_SECTION_SURFACES = {"canvas", "subtle", "raised", "brand_tint"}

HOME_COMPOSITION_SETTING_KEY = "customer_home.section_composition.v1"

# A finite component registry gives administrators real control over Home
# without allowing arbitrary remote UI code. Every section is native-rendered,
# accessibility-tested and backed by an existing bounded API collection.
HOME_SECTION_DEFINITIONS: dict[str, dict[str, Any]] = {
    "hero": {"label": "Hero slider", "title": None, "variants": ["marketplace", "cinematic", "edge_to_edge"], "max_items": 5},
    "service_groups": {"label": "Service groups", "title": "Popular services", "variants": ["compact_grid", "visual_rail", "two_row"], "max_items": 12},
    "live_booking": {"label": "Live booking", "title": "Your live booking", "variants": ["timeline"], "max_items": 1},
    "recent_bookings": {"label": "Recent bookings", "title": "Recent bookings", "variants": ["compact_rail", "stack"], "max_items": 3},
    "featured_services": {"label": "Featured services", "title": "Featured services", "variants": ["compact_cards", "feature_rail"], "max_items": 6},
    "master_services": {"label": "Master services", "title": "Recommended for you", "variants": ["recommendation_cards", "image_rail", "editorial_grid"], "max_items": 12},
    "trust_strip": {"label": "Customer assurance", "title": None, "variants": ["icon_row", "compact_cards"], "max_items": 4},
    "stories": {"label": "Stories and offers", "title": "Ideas and offers", "variants": ["landscape", "portrait"], "max_items": 8},
    "spotlight": {"label": "Editorial spotlight", "title": "In the spotlight", "variants": ["cinematic_card", "split_feature"], "max_items": 2},
    "mosaic": {"label": "Campaign mosaic", "title": "Fresh ways to care for home", "variants": ["asymmetric"], "max_items": 3},
    "global_services": {"label": "Fuvay digital services", "title": "Web & mobile development", "variants": ["compact_services", "studio_rail"], "max_items": 6},
    "collection": {"label": "Curated collection", "title": "Offers for you", "variants": ["editorial_cards"], "max_items": 8},
    "banners": {"label": "Editorial banners", "title": None, "variants": ["full_bleed", "contained"], "max_items": 4},
    "assistant": {"label": "Ask Fuvay", "title": None, "variants": ["command_strip"], "max_items": 1},
    "featured_problems": {"label": "Featured problems", "title": "What needs fixing?", "variants": ["editorial_list", "compact_grid"], "max_items": 8},
    "active_bookings": {"label": "More active bookings", "title": "More active bookings", "variants": ["stack"], "max_items": 3},
    "repair_problems": {"label": "Repair problems", "title": "Repairs you can book now", "variants": ["editorial_rail"], "max_items": 12},
    "consultation_problems": {"label": "Consultation problems", "title": "Get an expert opinion", "variants": ["editorial_list"], "max_items": 8},
    "more_problems": {"label": "More problems", "title": "More ways we can help", "variants": ["compact_grid"], "max_items": 12},
    "notices": {"label": "Notices", "title": None, "variants": ["strips"], "max_items": 2},
    "support_actions": {"label": "Location and support", "title": None, "variants": ["utility_rows"], "max_items": 2},
}

DEFAULT_HOME_SECTION_ORDER = [
    "hero", "service_groups", "recent_bookings", "featured_services", "master_services",
    "banners", "collection", "spotlight", "global_services", "trust_strip", "live_booking", "stories",
    "mosaic", "assistant",
    "featured_problems", "active_bookings", "repair_problems",
    "consultation_problems", "more_problems", "notices", "support_actions",
]

DEFAULT_ENABLED_HOME_SECTIONS = {
    "hero", "service_groups", "recent_bookings", "featured_services", "master_services",
    "banners", "collection", "spotlight", "global_services", "trust_strip",
}

DEFAULT_HOME_PRESENTATION: dict[str, dict[str, str]] = {
    "hero": {"spacing": "compact", "surface": "canvas"},
    "live_booking": {"spacing": "compact", "surface": "canvas"},
    "service_groups": {"spacing": "compact", "surface": "canvas"},
    "recent_bookings": {"spacing": "compact", "surface": "canvas"},
    "featured_services": {"spacing": "compact", "surface": "canvas"},
    "master_services": {"spacing": "compact", "surface": "canvas"},
    "banners": {"spacing": "standard", "surface": "canvas"},
    "collection": {"spacing": "compact", "surface": "canvas"},
    "spotlight": {"spacing": "compact", "surface": "canvas"},
    "global_services": {"spacing": "compact", "surface": "canvas"},
    "trust_strip": {"spacing": "compact", "surface": "subtle"},
}


class HomeSectionWrite(BaseModel):
    key: str
    enabled: bool = True
    title: str | None = Field(default=None, max_length=80)
    variant: str
    max_items: int = Field(ge=1, le=24)
    spacing: Literal["compact", "standard", "generous"] = "standard"
    surface: Literal["canvas", "subtle", "raised", "brand_tint"] = "canvas"

    @model_validator(mode="after")
    def validate_section(self):
        definition = HOME_SECTION_DEFINITIONS.get(self.key)
        if not definition:
            raise ValueError(f"Unsupported Home section '{self.key}'.")
        if self.variant not in definition["variants"]:
            raise ValueError(f"Variant '{self.variant}' is not valid for {self.key}.")
        if self.max_items > int(definition["max_items"]):
            raise ValueError(
                f"{definition['label']} supports at most {definition['max_items']} items."
            )
        return self


class HomeCompositionWrite(BaseModel):
    sections: list[HomeSectionWrite] = Field(min_length=1, max_length=len(HOME_SECTION_DEFINITIONS))
    reason: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def unique_sections(self):
        keys = [section.key for section in self.sections]
        if len(keys) != len(set(keys)):
            raise ValueError("A Home section can appear only once.")
        return self


def default_home_composition() -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "enabled": key in DEFAULT_ENABLED_HOME_SECTIONS,
            "title": HOME_SECTION_DEFINITIONS[key]["title"],
            "variant": HOME_SECTION_DEFINITIONS[key]["variants"][0],
            "max_items": HOME_SECTION_DEFINITIONS[key]["max_items"],
            "spacing": DEFAULT_HOME_PRESENTATION.get(key, {}).get("spacing", "standard"),
            "surface": DEFAULT_HOME_PRESENTATION.get(key, {}).get("surface", "canvas"),
        }
        for key in DEFAULT_HOME_SECTION_ORDER
    ]


def normalize_home_composition(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return default_home_composition()
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        try:
            validated = HomeSectionWrite.model_validate(item)
        except Exception:
            continue
        if validated.key in seen:
            continue
        seen.add(validated.key)
        normalized.append(validated.model_dump())
    for default in default_home_composition():
        if default["key"] not in seen:
            normalized.append(default)
    return normalized or default_home_composition()


class HomePlacementWrite(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    subtitle: str = Field(min_length=2, max_length=300)
    placement: str
    variant: str
    theme_key: str = "ink"
    section_title: str | None = Field(default=None, max_length=80)
    badge: str = Field(default="Featured", max_length=40)
    offer_text: str | None = Field(default=None, max_length=80)
    image_url: str = Field(max_length=1000)
    action_label: str = Field(default="Explore", min_length=1, max_length=40)
    action_url: str | None = Field(default=None, max_length=500)
    category_slug: str | None = Field(default=None, max_length=160)
    service_group_slug: str | None = Field(default=None, max_length=160)
    sponsored: bool = False
    priority: int = Field(default=0, ge=-1000, le=1000)
    city: str | None = Field(default=None, max_length=100)
    zipcodes: list[str] = Field(default_factory=list, max_length=100)
    # Zero means evergreen. Customer Home content should not silently disappear
    # after a few app refreshes; operators can still opt into a bounded daily cap.
    frequency_cap_per_day: int = Field(default=0, ge=0, le=100)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool = False

    @field_validator("image_url")
    @classmethod
    def secure_image_url(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("https://"):
            raise ValueError("Artwork must use an HTTPS CDN URL (Cloudinary is supported).")
        return value

    @field_validator("zipcodes")
    @classmethod
    def normalize_zipcodes(cls, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            pin = str(value).strip()
            if not (pin.isdigit() and len(pin) == 6):
                raise ValueError("Every PIN code must contain exactly 6 digits.")
            if pin not in normalized:
                normalized.append(pin)
        return normalized

    @field_validator("offer_text")
    @classmethod
    def prevent_speculative_price(cls, value: str | None) -> str | None:
        text = (value or "").strip()
        if not text:
            return None
        lowered = text.lower()
        if any(token in lowered for token in ("₹", "rs.", "rs ", "inr", "starting at", "from rupee")):
            raise ValueError("Home content cannot advertise a provider price before matching.")
        return text

    @model_validator(mode="after")
    def validate_presentation(self):
        placement = HOME_PLACEMENTS.get(self.placement)
        if not placement:
            raise ValueError("Unsupported Home placement.")
        if self.variant not in placement["variants"]:
            raise ValueError(f"Variant '{self.variant}' is not valid for {self.placement}.")
        if self.theme_key not in HOME_THEME_KEYS:
            raise ValueError("Unsupported Home theme.")
        if self.ends_at and self.starts_at and self.ends_at <= self.starts_at:
            raise ValueError("End date must be after the start date.")
        return self


class HomePlacementPatch(HomePlacementWrite):
    pass


class CustomerHomeMerchandisingService:
    async def get_composition(self, db: AsyncSession) -> dict[str, Any]:
        setting = (await db.execute(
            select(PlatformSetting).where(PlatformSetting.key == HOME_COMPOSITION_SETTING_KEY)
        )).scalar_one_or_none()
        stored = (setting.value or {}).get("v") if setting else None
        return {
            "sections": normalize_home_composition(stored),
            "definitions": [
                {"key": key, **definition}
                for key, definition in HOME_SECTION_DEFINITIONS.items()
            ],
            "layout_options": {
                "spacing": sorted(HOME_SECTION_SPACING),
                "surfaces": sorted(HOME_SECTION_SURFACES),
            },
            "updated_at": setting.updated_at.isoformat() if setting and setting.updated_at else None,
        }

    async def update_composition(
        self,
        db: AsyncSession,
        *,
        body: HomeCompositionWrite,
        actor_user_id: uuid.UUID,
        request_id: str,
    ) -> dict[str, Any]:
        setting = (await db.execute(
            select(PlatformSetting).where(PlatformSetting.key == HOME_COMPOSITION_SETTING_KEY)
        )).scalar_one_or_none()
        old_value = (setting.value or {}).get("v") if setting else None
        sections = normalize_home_composition([section.model_dump() for section in body.sections])
        if setting is None:
            setting = PlatformSetting(
                key=HOME_COMPOSITION_SETTING_KEY,
                value={"v": sections},
                setting_type="json",
                description="Ordered native section composition for the customer Home screen.",
                label="Customer Home composition",
                category="customer_experience",
                is_public=True,
                set_by=actor_user_id,
                risk_level="medium",
                requires_approval=False,
                requires_restart=False,
                is_runtime_editable=True,
                owner_module="customer_home",
                status="active",
            )
            db.add(setting)
        else:
            setting.value = {"v": sections}
            setting.set_by = actor_user_id
            setting.updated_at = datetime.now(timezone.utc)
        db.add(SettingAuditLog(
            tier="platform",
            key=HOME_COMPOSITION_SETTING_KEY,
            old_value={"v": old_value} if old_value is not None else None,
            new_value={"v": sections},
            changed_by=actor_user_id,
            reason=body.reason,
            request_id=request_id,
            risk_level="medium",
            action_type="updated" if old_value is not None else "created",
        ))
        await db.commit()
        await db.refresh(setting)
        return await self.get_composition(db)

    async def list(self, db: AsyncSession) -> dict[str, Any]:
        from app.engines.admin_catalog.models import ServiceGroup

        rows = (await db.execute(
            select(MarketingCampaign, MarketingCampaignMessage, MarketingCampaignRule)
            .join(
                MarketingCampaignMessage,
                and_(
                    MarketingCampaignMessage.campaign_id == MarketingCampaign.id,
                    MarketingCampaignMessage.channel == CHANNEL_IN_APP,
                    MarketingCampaignMessage.is_active.is_(True),
                ),
            )
            .join(
                MarketingCampaignRule,
                and_(
                    MarketingCampaignRule.campaign_id == MarketingCampaign.id,
                    MarketingCampaignRule.rule_type == RULE_CHANNEL,
                    MarketingCampaignRule.is_active.is_(True),
                ),
            )
            .where(MarketingCampaign.target_audience == AUDIENCE_CUSTOMERS)
            .order_by(desc(MarketingCampaign.updated_at), desc(MarketingCampaign.created_at))
        )).all()
        items: list[dict[str, Any]] = []
        seen: set[uuid.UUID] = set()
        for campaign, message, rule in rows:
            config = rule.rule_config if isinstance(rule.rule_config, dict) else {}
            if campaign.id in seen or config.get("surface") != "customer_home":
                continue
            seen.add(campaign.id)
            items.append(self._serialize(campaign, message, config))
        service_groups = (await db.execute(
            select(ServiceGroup.slug, ServiceGroup.name)
            .where(ServiceGroup.status == "active", ServiceGroup.deleted_at.is_(None))
            .order_by(ServiceGroup.display_order, ServiceGroup.name)
        )).all()
        composition = await self.get_composition(db)
        return {
            "items": items,
            "count": len(items),
            "placements": [
                {"key": key, **value} for key, value in HOME_PLACEMENTS.items()
            ],
            "themes": sorted(HOME_THEME_KEYS),
            "service_groups": [
                {"slug": row.slug, "label": row.name} for row in service_groups
            ],
            "composition": composition,
        }

    async def create(
        self,
        db: AsyncSession,
        *,
        body: HomePlacementWrite,
        actor_user_id: uuid.UUID,
    ) -> dict[str, Any]:
        await self._ensure_capacity(db, body.placement, body.is_active)
        campaign = MarketingCampaign(
            campaign_key=f"customer_home_{secrets.token_hex(8)}",
            campaign_name=body.title,
            campaign_type=CAMPAIGN_TYPE_ANNOUNCEMENT,
            status=CAMP_STATUS_RUNNING if body.is_active else CAMP_STATUS_DRAFT,
            target_audience=AUDIENCE_CUSTOMERS,
            city=body.city.strip() if body.city else None,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
            created_by_user_id=actor_user_id,
            owner_user_id=actor_user_id,
            vertical_key="home_services",
            channels_json=[CHANNEL_IN_APP],
            goal="customer_home_merchandising",
        )
        db.add(campaign)
        await db.flush()
        message = MarketingCampaignMessage(
            campaign_id=campaign.id,
            channel=CHANNEL_IN_APP,
            title=body.title,
            body=body.subtitle,
            action_label=body.action_label,
            action_url=body.action_url,
        )
        rule = MarketingCampaignRule(
            campaign_id=campaign.id,
            rule_type=RULE_CHANNEL,
            rule_config=self._config(body),
        )
        db.add_all([message, rule])
        await db.commit()
        await db.refresh(campaign)
        return self._serialize(campaign, message, rule.rule_config)

    async def update(
        self,
        db: AsyncSession,
        *,
        campaign_id: uuid.UUID,
        body: HomePlacementPatch,
    ) -> dict[str, Any]:
        campaign, message, rule = await self._get(db, campaign_id)
        was_active = campaign.status == CAMP_STATUS_RUNNING
        if body.is_active and (not was_active or (rule.rule_config or {}).get("placement") != body.placement):
            await self._ensure_capacity(db, body.placement, True, excluding=campaign.id)
        campaign.campaign_name = body.title
        campaign.city = body.city.strip() if body.city else None
        campaign.starts_at = body.starts_at
        campaign.ends_at = body.ends_at
        campaign.status = CAMP_STATUS_RUNNING if body.is_active else CAMP_STATUS_DRAFT
        campaign.updated_at = datetime.now(timezone.utc)
        message.title = body.title
        message.body = body.subtitle
        message.action_label = body.action_label
        message.action_url = body.action_url
        message.updated_at = datetime.now(timezone.utc)
        rule.rule_config = self._config(body)
        rule.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(campaign)
        return self._serialize(campaign, message, rule.rule_config)

    async def archive(self, db: AsyncSession, campaign_id: uuid.UUID) -> dict[str, Any]:
        campaign, message, rule = await self._get(db, campaign_id)
        campaign.status = CAMP_STATUS_CANCELLED
        campaign.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return {"campaign_id": str(campaign.id), "archived": True}

    async def _get(self, db: AsyncSession, campaign_id: uuid.UUID):
        row = (await db.execute(
            select(MarketingCampaign, MarketingCampaignMessage, MarketingCampaignRule)
            .join(MarketingCampaignMessage, MarketingCampaignMessage.campaign_id == MarketingCampaign.id)
            .join(MarketingCampaignRule, MarketingCampaignRule.campaign_id == MarketingCampaign.id)
            .where(
                MarketingCampaign.id == campaign_id,
                MarketingCampaignMessage.channel == CHANNEL_IN_APP,
                MarketingCampaignRule.rule_type == RULE_CHANNEL,
            )
            .limit(1)
        )).first()
        if not row or (row[2].rule_config or {}).get("surface") != "customer_home":
            raise ValueError("Customer Home placement not found.")
        return row

    async def _ensure_capacity(
        self,
        db: AsyncSession,
        placement: str,
        is_active: bool,
        *,
        excluding: uuid.UUID | None = None,
    ) -> None:
        if not is_active:
            return
        max_active = int(HOME_PLACEMENTS[placement]["max_active"])
        stmt = (
            select(func.count(func.distinct(MarketingCampaign.id)))
            .select_from(MarketingCampaign)
            .join(MarketingCampaignRule, MarketingCampaignRule.campaign_id == MarketingCampaign.id)
            .where(
                MarketingCampaign.status == CAMP_STATUS_RUNNING,
                MarketingCampaign.target_audience == AUDIENCE_CUSTOMERS,
                MarketingCampaignRule.rule_type == RULE_CHANNEL,
                MarketingCampaignRule.rule_config["surface"].astext == "customer_home",
                MarketingCampaignRule.rule_config["placement"].astext == placement,
            )
        )
        if excluding:
            stmt = stmt.where(MarketingCampaign.id != excluding)
        current = int((await db.execute(stmt)).scalar_one() or 0)
        if current >= max_active:
            raise ValueError(
                f"{HOME_PLACEMENTS[placement]['label']} already has its {max_active} active item limit."
            )

    @staticmethod
    def _config(body: HomePlacementWrite) -> dict[str, Any]:
        return {
            "surface": "customer_home",
            "placement": body.placement,
            "variant": body.variant,
            "theme_key": body.theme_key,
            "section_title": body.section_title,
            "badge": body.badge,
            "offer_text": body.offer_text,
            "image_url": body.image_url,
            "category_slug": body.category_slug,
            "service_group_slug": body.service_group_slug,
            "sponsored": body.sponsored,
            "priority": body.priority,
            "zipcodes": body.zipcodes,
            "frequency_cap_per_day": body.frequency_cap_per_day,
        }

    @staticmethod
    def _serialize(
        campaign: MarketingCampaign,
        message: MarketingCampaignMessage,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "campaign_id": str(campaign.id),
            "title": message.title,
            "subtitle": message.body,
            "placement": config.get("placement", "home_hero"),
            "variant": config.get("variant", "cinematic"),
            "theme_key": config.get("theme_key", "ink"),
            "section_title": config.get("section_title"),
            "badge": config.get("badge", "Featured"),
            "offer_text": config.get("offer_text"),
            "image_url": config.get("image_url"),
            "action_label": message.action_label or "Explore",
            "action_url": message.action_url,
            "category_slug": config.get("category_slug"),
            "service_group_slug": config.get("service_group_slug"),
            "sponsored": bool(config.get("sponsored", False)),
            "priority": int(config.get("priority") or 0),
            "city": campaign.city,
            "zipcodes": config.get("zipcodes") or [],
            "frequency_cap_per_day": int(config.get("frequency_cap_per_day") or 0),
            "starts_at": campaign.starts_at.isoformat() if campaign.starts_at else None,
            "ends_at": campaign.ends_at.isoformat() if campaign.ends_at else None,
            "is_active": campaign.status == CAMP_STATUS_RUNNING,
            "status": campaign.status,
            "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
        }
