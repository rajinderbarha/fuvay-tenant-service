"""Create or update a development customer-Home campaign.

The script intentionally targets the existing marketing automation tables so
there is no second campaign system. Production operators configure the same
record through the admin campaign API; this utility only makes local/native QA
repeatable.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.database import close_db, get_session_factory, init_db
from app.engines.customer_home.merchandising import HOME_PLACEMENTS
from app.engines.marketing_automation.models import (
    MarketingCampaign,
    MarketingCampaignMessage,
    MarketingCampaignRule,
)


async def seed(
    *,
    campaign_key: str,
    title: str,
    body: str,
    image_url: str,
    category_slug: str,
    service_group_slug: str | None,
    placement: str,
    offer_text: str | None,
    action_label: str,
    action_url: str | None,
    priority: int,
    ends_at: datetime | None,
) -> None:
    placement_definition = HOME_PLACEMENTS.get(placement)
    if placement_definition is None:
        supported = ", ".join(sorted(HOME_PLACEMENTS))
        raise ValueError(f"Unsupported Home placement '{placement}'. Choose one of: {supported}")
    variant = str(placement_definition["variants"][0])
    await init_db()
    factory = get_session_factory()
    try:
        async with factory() as db:
            campaign = (await db.execute(
                select(MarketingCampaign).where(
                    MarketingCampaign.campaign_key == campaign_key
                )
            )).scalars().first()
            now = datetime.now(timezone.utc)
            if campaign is None:
                campaign = MarketingCampaign(
                    campaign_key=campaign_key,
                    campaign_name=title,
                    campaign_type="promotion",
                    status="running",
                    target_audience="customers",
                    vertical_key="home_services",
                    goal="Drive serviceable AC maintenance bookings",
                    channels_json=["in_app"],
                    starts_at=now,
                )
                db.add(campaign)
                await db.flush()
            else:
                campaign.campaign_name = title
                campaign.campaign_type = "promotion"
                campaign.status = "running"
                campaign.target_audience = "customers"
                campaign.vertical_key = "home_services"
                campaign.channels_json = ["in_app"]
                campaign.updated_at = now
            campaign.ends_at = ends_at

            await db.execute(delete(MarketingCampaignMessage).where(
                MarketingCampaignMessage.campaign_id == campaign.id
            ))
            await db.execute(delete(MarketingCampaignRule).where(
                MarketingCampaignRule.campaign_id == campaign.id
            ))
            db.add(MarketingCampaignMessage(
                campaign_id=campaign.id,
                channel="in_app",
                title=title,
                body=body,
                action_label=action_label,
                action_url=action_url or f"fuvay://assistant?category_slug={category_slug}",
                is_active=True,
            ))
            db.add(MarketingCampaignRule(
                campaign_id=campaign.id,
                rule_type="channel",
                rule_config={
                    "surface": "customer_home",
                    "placement": placement,
                    "priority": priority,
                    "variant": variant,
                    "sponsored": placement == "home_hero",
                    "badge": "Sponsored" if placement == "home_hero" else "For your home",
                    "offer_text": offer_text,
                    "image_url": image_url,
                    "category_slug": category_slug,
                    "service_group_slug": service_group_slug,
                    # Evergreen Home content must remain stable across refreshes.
                    # Operators can still configure a cap through the admin API,
                    # but the repeatable local seed should never make a hero
                    # silently disappear during native QA.
                    "frequency_cap_per_day": 0,
                },
                is_active=True,
            ))
            await db.commit()
            print(str(campaign.id))
    finally:
        await close_db()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-url", required=True)
    parser.add_argument("--campaign-key", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--category-slug", default="home_services")
    parser.add_argument("--service-group-slug")
    parser.add_argument("--placement", default="home_hero")
    parser.add_argument("--offer-text")
    parser.add_argument("--action-label", default="Explore")
    parser.add_argument("--action-url", help="Optional native deep link, for example fuvay://global-services")
    parser.add_argument("--priority", type=int, default=0)
    parser.add_argument(
        "--ends-at",
        help="Optional ISO-8601 end timestamp, for example 2026-08-31T23:59:59+05:30",
    )
    args = parser.parse_args()
    if not args.image_url.startswith("https://"):
        raise SystemExit("--image-url must be an HTTPS CDN URL")
    ends_at = datetime.fromisoformat(args.ends_at) if args.ends_at else None
    if ends_at is not None and ends_at.tzinfo is None:
        raise SystemExit("--ends-at must include a timezone offset")
    asyncio.run(seed(
        campaign_key=args.campaign_key,
        title=args.title,
        body=args.body,
        image_url=args.image_url,
        category_slug=args.category_slug,
        service_group_slug=args.service_group_slug,
        placement=args.placement,
        offer_text=args.offer_text,
        action_label=args.action_label,
        action_url=args.action_url,
        priority=args.priority,
        ends_at=ends_at,
    ))


if __name__ == "__main__":
    main()
