"""LEVEL-5 REMEDIATION (2026-08-01, Phase 11) — CustomerCampaignService."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.customer_campaigns.constants import (
    ALLOWED_DEEPLINK_PREFIXES,
    CAMPAIGN_PLACEMENTS,
    CAMPAIGN_STYLES,
    ERR_INVALID_PLACEMENT,
    ERR_INVALID_STYLE,
    ERR_CAMPAIGN_NOT_FOUND,
    ERR_INVALID_DEEPLINK,
    ERR_INVALID_DATE_WINDOW,
    MAX_ACTIVE_CAMPAIGNS_RETURNED,
)
from app.engines.customer_campaigns.models import CustomerCampaign
from app.exceptions import ServiceOSException

utcnow = lambda: datetime.now(timezone.utc)


class CampaignService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Customer read (server-side targeting enforcement) ──────────────────

    async def list_active_for_customer(
        self,
        zipcode: str | None = None,
        vertical_key: str | None = None,
        category_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Returns customer-safe campaign dicts, enabled + within the active
        date window + matching ZIP/vertical/category targeting (empty
        targeting arrays mean "no restriction on that axis" — a campaign
        with no target_zipcodes at all is shown everywhere; one with a
        non-empty list is shown ONLY to matching ZIPs). All filtering is
        server-side — a client cannot request campaigns outside its own
        ZIP/category context by passing different values, since this method
        is the only read path and always re-checks here.
        """
        now = utcnow()
        q = select(CustomerCampaign).where(
            CustomerCampaign.is_enabled == True,  # noqa: E712
            or_(CustomerCampaign.starts_at.is_(None), CustomerCampaign.starts_at <= now),
            or_(CustomerCampaign.ends_at.is_(None), CustomerCampaign.ends_at >= now),
        ).order_by(CustomerCampaign.priority.asc())
        rows = (await self.db.execute(q)).scalars().all()

        def _matches(c: CustomerCampaign) -> bool:
            if c.target_zipcodes and zipcode and zipcode not in c.target_zipcodes:
                return False
            if c.target_zipcodes and not zipcode:
                return False
            if c.eligible_vertical_keys and vertical_key and vertical_key not in c.eligible_vertical_keys:
                return False
            if c.eligible_category_ids and category_id and str(category_id) not in c.eligible_category_ids:
                return False
            return True

        matched = [c for c in rows if _matches(c)]
        return [c.to_customer_dict() for c in matched[:MAX_ACTIVE_CAMPAIGNS_RETURNED]]

    # ── Admin CRUD ───────────────────────────────────────────────────────────

    def _validate_deeplink(self, deeplink: str | None) -> None:
        if deeplink is None:
            return
        if not any(deeplink.startswith(p) for p in ALLOWED_DEEPLINK_PREFIXES):
            raise ServiceOSException(
                ERR_INVALID_DEEPLINK,
                f"cta_deeplink must start with one of: {', '.join(ALLOWED_DEEPLINK_PREFIXES)}",
                status_code=422,
            )

    def _parse_dt(self, value, field: str):
        """ISO string -> aware datetime.

        Real bug fixed here: the admin router takes a raw dict body and these
        two fields went to a DateTime column as STRINGS, so asyncpg raised
        `invalid input for query argument ... expected a datetime` and every
        scheduled campaign returned HTTP 500. A campaign with a start/end window
        -- which is what a festival or limited-time run IS -- could not be
        created or updated through the API at all.

        A naive timestamp is read as UTC rather than rejected: admin tooling
        commonly omits the offset, and the alternative is refusing a value whose
        meaning is unambiguous in this system.
        """
        if value is None or isinstance(value, datetime):
            return value
        if not isinstance(value, str) or not value.strip():
            raise ServiceOSException(
                ERR_INVALID_DATE_WINDOW,
                f"{field} must be an ISO 8601 timestamp.", status_code=422,
            )
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            raise ServiceOSException(
                ERR_INVALID_DATE_WINDOW,
                f"{field} is not a valid ISO 8601 timestamp: {value!r}", status_code=422,
            ) from None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def _validate_presentation(self, style, placement) -> None:
        """A style the app has no renderer for, or a slot it has no position
        for, would save fine and then render as nothing -- so both are checked
        against the shipped vocabulary rather than accepted as free text."""
        if style is not None and style not in CAMPAIGN_STYLES:
            raise ServiceOSException(
                ERR_INVALID_STYLE,
                f"display_style must be one of: {', '.join(CAMPAIGN_STYLES)}",
                status_code=422,
            )
        if placement is not None and placement not in CAMPAIGN_PLACEMENTS:
            raise ServiceOSException(
                ERR_INVALID_PLACEMENT,
                f"placement must be one of: {', '.join(CAMPAIGN_PLACEMENTS)}",
                status_code=422,
            )

    def _validate_date_window(self, starts_at, ends_at) -> None:
        if starts_at and ends_at and starts_at > ends_at:
            raise ServiceOSException(
                ERR_INVALID_DATE_WINDOW, "starts_at must be before ends_at.", status_code=422,
            )

    async def create_campaign(self, data: dict, actor_id: uuid.UUID | None = None) -> dict:
        self._validate_deeplink(data.get("cta_deeplink"))
        starts_at = self._parse_dt(data.get("starts_at"), "starts_at")
        ends_at = self._parse_dt(data.get("ends_at"), "ends_at")
        self._validate_date_window(starts_at, ends_at)
        self._validate_presentation(data.get("display_style"), data.get("placement"))
        c = CustomerCampaign(
            id=uuid.uuid4(),
            internal_name=data["internal_name"],
            eyebrow=data.get("eyebrow"),
            title=data["title"],
            description=data.get("description"),
            artwork_url_light=data.get("artwork_url_light"),
            artwork_url_dark=data.get("artwork_url_dark"),
            cta_label=data.get("cta_label"),
            cta_deeplink=data.get("cta_deeplink"),
            display_style=data.get("display_style") or "hero",
            placement=data.get("placement") or "campaign_top",
            accent_color=data.get("accent_color"),
            badge_text=data.get("badge_text"),
            is_enabled=data.get("is_enabled", True),
            priority=data.get("priority", 100),
            starts_at=starts_at,
            ends_at=ends_at,
            eligible_vertical_keys=data.get("eligible_vertical_keys") or [],
            eligible_category_ids=data.get("eligible_category_ids") or [],
            target_zipcodes=data.get("target_zipcodes") or [],
            target_zones=data.get("target_zones") or [],
            target_cities=data.get("target_cities") or [],
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.db.add(c)
        await self.db.flush()
        await self.db.commit()
        return c.to_admin_dict()

    async def _require_campaign(self, campaign_id: uuid.UUID) -> CustomerCampaign:
        c = await self.db.get(CustomerCampaign, campaign_id)
        if not c:
            raise ServiceOSException(ERR_CAMPAIGN_NOT_FOUND, "Campaign not found.", status_code=404)
        return c

    async def update_campaign(self, campaign_id: uuid.UUID, data: dict, actor_id: uuid.UUID | None = None) -> dict:
        c = await self._require_campaign(campaign_id)
        if "cta_deeplink" in data:
            self._validate_deeplink(data["cta_deeplink"])
        self._validate_presentation(data.get("display_style"), data.get("placement"))
        data = dict(data)
        for field in ("starts_at", "ends_at"):
            if field in data:
                data[field] = self._parse_dt(data[field], field)
        self._validate_date_window(
            data.get("starts_at", c.starts_at), data.get("ends_at", c.ends_at),
        )
        for field in (
            "internal_name", "eyebrow", "title", "description",
            "artwork_url_light", "artwork_url_dark", "cta_label", "cta_deeplink",
            "display_style", "placement", "accent_color", "badge_text",
            "is_enabled", "priority", "starts_at", "ends_at",
            "eligible_vertical_keys", "eligible_category_ids",
            "target_zipcodes", "target_zones", "target_cities",
        ):
            if field in data:
                setattr(c, field, data[field])
        c.updated_by = actor_id
        await self.db.flush()
        await self.db.commit()
        return c.to_admin_dict()

    async def list_all_admin(self) -> list[dict]:
        rows = (await self.db.execute(
            select(CustomerCampaign).order_by(CustomerCampaign.priority.asc())
        )).scalars().all()
        return [c.to_admin_dict() for c in rows]

    async def delete_campaign(self, campaign_id: uuid.UUID) -> None:
        c = await self._require_campaign(campaign_id)
        await self.db.delete(c)
        await self.db.commit()
