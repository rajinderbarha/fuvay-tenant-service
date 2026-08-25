"""Upload the approved Fuvay Home artwork and publish reusable demo content.

The script is idempotent: assets are reused by original filename and campaigns
are upserted by stable campaign key. It exercises the same Cloudinary/media and
customer-home models as the admin studio; it does not write localhost URLs.
"""
from __future__ import annotations

import asyncio
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from starlette.datastructures import Headers

from app.database import close_db, get_session_factory, init_db
from app.dependencies.auth import UserContext
from app.engines.auth.models import User
from app.engines.customer_home.merchandising import (
    HOME_COMPOSITION_SETTING_KEY,
    CustomerHomeMerchandisingService,
    HomeCompositionWrite,
    HomePlacementWrite,
    default_home_composition,
)
from app.engines.marketing_automation.constants import (
    AUDIENCE_CUSTOMERS,
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
from app.engines.media.asset_service import MediaAssetService
from app.engines.media.models import MediaAsset
from app.engines.settings_engine.models import PlatformSetting


ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "mobile" / "customer-app" / "assets" / "home-campaigns"

CONTENT = [
    {
        "key": "fuvay_home_ac_care_hero_v1",
        "file": "fuvay-ac-care-hero-v1.png",
        "title": "Comfort, handled beautifully",
        "subtitle": "Book trusted AC care from a service team available in your PIN code.",
        "placement": "home_hero",
        "variant": "cinematic",
        "theme_key": "ink",
        "badge": "Seasonal care",
        "offer_text": "Priority slots open",
        "action_label": "Book AC care",
        "service_group_slug": "ac_services",
        "priority": 400,
    },
    {
        "key": "fuvay_home_whole_home_banner_v1",
        "file": "fuvay-whole-home-care-v1.png",
        "title": "One home. Every essential appliance.",
        "subtitle": "Explore expert care for cooling, cleaning, water and kitchen appliances.",
        "placement": "home_banner",
        "variant": "editorial",
        "theme_key": "mint",
        "badge": "Whole-home care",
        "offer_text": None,
        "action_label": "Explore services",
        "service_group_slug": None,
        "priority": 260,
    },
    {
        "key": "fuvay_home_chimney_story_v1",
        "file": "fuvay-chimney-care-story-v1.png",
        "title": "A fresher kitchen starts above the hob",
        "subtitle": "Discover professional chimney care without the guesswork.",
        "placement": "home_story",
        "variant": "portrait",
        "theme_key": "coral",
        "badge": "Kitchen care",
        "offer_text": None,
        "action_label": "View chimney care",
        "service_group_slug": "chimney_services",
        "priority": 220,
    },
    {
        "key": "fuvay_home_digital_spotlight_v1",
        "file": "fuvay-digital-studio-v1.png",
        "title": "Build your next digital product with Fuvay",
        "subtitle": "Websites and mobile apps designed for ambitious businesses, available in every PIN code.",
        "placement": "home_spotlight",
        "variant": "feature",
        "theme_key": "violet",
        "badge": "Fuvay digital studio",
        "offer_text": None,
        "action_label": "Start a project",
        "action_url": "fuvay://global-services",
        "service_group_slug": None,
        "priority": 200,
    },
]


async def ensure_artwork(db, actor: UserContext, filename: str) -> str:
    existing = (await db.execute(
        select(MediaAsset).where(
            MediaAsset.media_context == "home_campaign_artwork",
            MediaAsset.file_name_original == filename,
            MediaAsset.status == "active",
            MediaAsset.is_public.is_(True),
        ).order_by(MediaAsset.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if existing and existing.public_url:
        return existing.public_url
    path = ART_DIR / filename
    upload = UploadFile(
        file=io.BytesIO(path.read_bytes()),
        filename=filename,
        headers=Headers({"content-type": "image/png"}),
    )
    result = await MediaAssetService(db, actor).upload(
        file=upload,
        media_context="home_campaign_artwork",
        owner_type="platform",
        owner_id=actor.user_id,
        is_public=True,
        description="Generated Fuvay customer Home campaign artwork",
        tags=["customer-home", "fuvay", "campaign"],
    )
    await db.commit()
    url = result.get("public_url") or result.get("preview_url")
    if not url or not str(url).startswith("https://"):
        raise RuntimeError(f"Cloudinary did not return a public HTTPS URL for {filename}.")
    return str(url)


async def upsert_campaign(db, actor: UserContext, spec: dict, image_url: str) -> None:
    body = HomePlacementWrite.model_validate({
        "title": spec["title"],
        "subtitle": spec["subtitle"],
        "placement": spec["placement"],
        "variant": spec["variant"],
        "theme_key": spec["theme_key"],
        "badge": spec["badge"],
        "offer_text": spec.get("offer_text"),
        "image_url": image_url,
        "action_label": spec["action_label"],
        "action_url": spec.get("action_url"),
        "category_slug": "home_services" if spec.get("service_group_slug") else None,
        "service_group_slug": spec.get("service_group_slug"),
        "priority": spec["priority"],
        "is_active": True,
    })
    campaign = (await db.execute(
        select(MarketingCampaign).where(MarketingCampaign.campaign_key == spec["key"])
    )).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if campaign is None:
        campaign = MarketingCampaign(
            campaign_key=spec["key"],
            campaign_name=body.title,
            campaign_type=CAMPAIGN_TYPE_ANNOUNCEMENT,
            status=CAMP_STATUS_RUNNING,
            target_audience=AUDIENCE_CUSTOMERS,
            vertical_key="home_services",
            channels_json=[CHANNEL_IN_APP],
            goal="customer_home_merchandising",
            created_by_user_id=uuid.UUID(actor.user_id),
            owner_user_id=uuid.UUID(actor.user_id),
        )
        db.add(campaign)
        await db.flush()
    campaign.campaign_name = body.title
    campaign.status = CAMP_STATUS_RUNNING
    campaign.updated_at = now
    message = (await db.execute(select(MarketingCampaignMessage).where(
        MarketingCampaignMessage.campaign_id == campaign.id,
        MarketingCampaignMessage.channel == CHANNEL_IN_APP,
    ))).scalar_one_or_none()
    if message is None:
        message = MarketingCampaignMessage(campaign_id=campaign.id, channel=CHANNEL_IN_APP)
        db.add(message)
    message.title = body.title
    message.body = body.subtitle
    message.action_label = body.action_label
    message.action_url = body.action_url
    message.is_active = True
    rule = (await db.execute(select(MarketingCampaignRule).where(
        MarketingCampaignRule.campaign_id == campaign.id,
        MarketingCampaignRule.rule_type == RULE_CHANNEL,
    ))).scalar_one_or_none()
    if rule is None:
        rule = MarketingCampaignRule(campaign_id=campaign.id, rule_type=RULE_CHANNEL)
        db.add(rule)
    rule.rule_config = {
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
    rule.is_active = True
    await db.commit()


async def main() -> None:
    await init_db()
    try:
        factory = get_session_factory()
        async with factory() as db:
            admin = (await db.execute(select(User).where(
                User.role == "super_admin", User.is_active.is_(True)
            ).order_by(User.created_at).limit(1))).scalar_one()
            actor = UserContext(
                user_id=str(admin.id), email=admin.email, role="super_admin",
                tenant_id=None, full_name=admin.full_name, is_verified=admin.is_verified,
            )
            composition_exists = (await db.execute(select(PlatformSetting.id).where(
                PlatformSetting.key == HOME_COMPOSITION_SETTING_KEY
            ))).scalar_one_or_none()
            if composition_exists is None:
                await CustomerHomeMerchandisingService().update_composition(
                    db,
                    body=HomeCompositionWrite(
                        sections=default_home_composition(),
                        reason="Publish the initial enterprise customer Home composition",
                    ),
                    actor_user_id=admin.id,
                    request_id="seed_generated_home_studio",
                )
            for spec in CONTENT:
                url = await ensure_artwork(db, actor, spec["file"])
                await upsert_campaign(db, actor, spec, url)
                print(f"{spec['key']}={url}")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
