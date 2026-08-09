"""MODULE-L5-57 — backend control over how Home presents itself.

Covers the new vocabulary (banner styles, placements, section keys) and one real
defect found while seeding the first festival campaign:

`customer_campaigns` admin create/update take a raw dict body and passed
`starts_at`/`ends_at` STRAIGHT into a DateTime column, so asyncpg raised
"invalid input for query argument ... expected a datetime, got 'str'" and every
scheduled campaign returned HTTP 500. A campaign with a start/end window -- which
is exactly what a festival or limited-time run is -- could not be created or
updated through the API at all.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.customer_campaigns import constants as cc
from app.engines.customer_campaigns.service import CampaignService
from app.engines.customer_home.constants import HOME_SECTION_KEYS
from app.exceptions import ServiceOSException


def _svc() -> CampaignService:
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return CampaignService(db=db)


# ── Date parsing: the 500 ────────────────────────────────────────────────────

def test_iso_window_is_parsed_to_a_real_datetime():
    """The regression guard. A str reaching the DateTime column is the bug."""
    svc = _svc()
    parsed = svc._parse_dt("2026-11-05T18:29:59+00:00", "ends_at")
    assert isinstance(parsed, datetime)
    assert parsed.tzinfo is not None


def test_trailing_z_is_accepted():
    parsed = _svc()._parse_dt("2026-08-01T00:00:00Z", "starts_at")
    assert parsed == datetime(2026, 8, 1, tzinfo=timezone.utc)


def test_naive_timestamp_is_read_as_utc_rather_than_refused():
    parsed = _svc()._parse_dt("2026-08-01T00:00:00", "starts_at")
    assert parsed.tzinfo == timezone.utc


def test_unparseable_window_is_a_422_not_a_500():
    with pytest.raises(ServiceOSException) as exc:
        _svc()._parse_dt("next diwali", "ends_at")
    assert exc.value.status_code == 422
    assert exc.value.error_code == cc.ERR_INVALID_DATE_WINDOW


def test_create_stores_a_datetime_for_the_window():
    svc = _svc()
    captured = {}
    svc.db.add = MagicMock(side_effect=lambda row: captured.update(row=row))
    asyncio.run(svc.create_campaign({
        "internal_name": "festive", "title": "Festive offer",
        "starts_at": "2026-08-01T00:00:00Z", "ends_at": "2026-11-05T18:29:59+00:00",
    }))
    row = captured["row"]
    assert isinstance(row.starts_at, datetime) and isinstance(row.ends_at, datetime)


# ── Presentation vocabulary ──────────────────────────────────────────────────

def test_every_shipped_style_is_accepted():
    for style in cc.CAMPAIGN_STYLES:
        _svc()._validate_presentation(style, None)


def test_every_shipped_placement_is_accepted():
    for placement in cc.CAMPAIGN_PLACEMENTS:
        _svc()._validate_presentation(None, placement)


def test_a_style_the_app_cannot_draw_is_refused():
    # Accepting it would save a campaign that renders as nothing -- which reads
    # to admin as a broken feature rather than a rejected input.
    with pytest.raises(ServiceOSException) as exc:
        _svc()._validate_presentation("sparkly", None)
    assert exc.value.status_code == 422
    assert exc.value.error_code == cc.ERR_INVALID_STYLE


def test_a_placement_with_no_slot_is_refused():
    with pytest.raises(ServiceOSException) as exc:
        _svc()._validate_presentation(None, "nowhere")
    assert exc.value.status_code == 422
    assert exc.value.error_code == cc.ERR_INVALID_PLACEMENT


def test_default_style_and_placement_are_part_of_the_vocabulary():
    # The model defaults and the migration's server_default must both be values
    # the validator would accept, or existing rows become unrenderable.
    assert "hero" in cc.CAMPAIGN_STYLES
    assert "campaign_top" in cc.CAMPAIGN_PLACEMENTS


def test_every_campaign_placement_is_also_a_home_section():
    """A banner slot the layout cannot switch off would be a section admin has
    no control over -- the whole point of the section settings."""
    for placement in cc.CAMPAIGN_PLACEMENTS:
        assert placement in HOME_SECTION_KEYS


def test_customer_projection_carries_the_presentation_fields():
    from app.engines.customer_campaigns.models import CustomerCampaign
    row = CustomerCampaign(
        internal_name="x", title="t", display_style="festival", placement="campaign_mid",
        accent_color="#f59e0b", badge_text="Diwali Special", priority=10,
        ends_at=datetime(2026, 11, 5, tzinfo=timezone.utc),
    )
    row.id = uuid.uuid4()
    projection = row.to_customer_dict()
    assert projection["display_style"] == "festival"
    assert projection["placement"] == "campaign_mid"
    assert projection["accent_color"] == "#f59e0b"
    assert projection["badge_text"] == "Diwali Special"
    assert projection["ends_at"].startswith("2026-11-05")
    # Still customer-safe: no internal fields leak into the app payload.
    assert "internal_name" not in projection
    assert "created_by" not in projection


# ── Section vocabulary ───────────────────────────────────────────────────────

def test_migration_seeds_exactly_the_known_section_keys():
    import os
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "alembic", "versions", "236_home_presentation_control.py",
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert 'revision = "236"' in src and 'down_revision = "235"' in src
    # Every seeded key must be one the app can render, or admin gets rows that
    # do nothing; every renderable key must be seeded, or it is invisible to
    # admin until someone edits the database.
    for key in HOME_SECTION_KEYS:
        assert f'"{key}"' in src, f"section {key} is not seeded by migration 236"


def test_unknown_section_key_is_refused_by_the_service():
    from app.engines.customer_home.section_service import HomeSectionService
    db = AsyncMock()
    with pytest.raises(ServiceOSException) as exc:
        asyncio.run(HomeSectionService(db).update("marketing_carousel", {"is_enabled": False}))
    assert exc.value.status_code == 422


def test_reorder_validates_every_key_before_writing_any():
    """A typo halfway down a drag-sorted list must not leave the layout
    half-reordered."""
    from app.engines.customer_home.section_service import HomeSectionService
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    svc = HomeSectionService(db)
    with pytest.raises(ServiceOSException):
        asyncio.run(svc.reorder(["active_booking", "not_a_section"]))
    db.add.assert_not_called()
    db.commit.assert_not_called()
