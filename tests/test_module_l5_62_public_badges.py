"""MODULE-L5-62 — customer-visible provider badges: one claim, one badge.

A badge is a claim the platform makes on a provider's behalf, on the screen where a
customer decides whether to let a stranger into their home. Two things must hold:

* The same claim appears once. `list_earned_badges` dedupes by badge KEY, which is
  right for an admin view -- two definitions are two records. To a customer they are
  one claim, and the same word five times is not five reasons to trust someone.
* The list stays short enough to mean something.

Live case this was found on: Guramrit held five separately-keyed, customer-visible
definitions all named "L5 Cfg Badge" (repeated test fixtures). The booking card
printed that label five times and, keyed on the name, React errored with "two
children with the same key" -- which makes it reuse the wrong node.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.home_service_booking.matching_engine import (
    MAX_PUBLIC_BADGES, _public_badges,
)


def _earned(*badges: dict) -> MagicMock:
    """A TrustQualityService whose read side returns exactly these badges."""
    service = MagicMock()
    service.list_earned_badges = AsyncMock(return_value=list(badges))
    return service


def _badge(name: str, icon: str | None = None, color: str | None = None) -> dict:
    return {"name": name, "icon": icon, "color": color}


class TestCollapsing:
    @pytest.mark.asyncio
    async def test_repeated_names_collapse_to_one(self):
        with patch("app.engines.trust_quality.service.TrustQualityService",
                   return_value=_earned(
                       _badge("L5 Cfg Badge"), _badge("L5 Cfg Badge"), _badge("L5 Cfg Badge"),
                       _badge("L5 Cfg Badge"), _badge("L5 Cfg Badge"),
                       _badge("AC Specialist", "snow"), _badge("Verified Business", "shield-check"),
                   )):
            badges = await _public_badges(AsyncMock(), "t-1", None, None)

        assert [b["name"] for b in badges] == [
            "L5 Cfg Badge", "AC Specialist", "Verified Business",
        ]

    @pytest.mark.asyncio
    async def test_keeps_the_first_occurrences_icon_and_colour(self):
        # list_earned_badges returns newest first, so the first is the most recently
        # earned -- the one whose styling the admin most recently set.
        with patch("app.engines.trust_quality.service.TrustQualityService",
                   return_value=_earned(
                       _badge("Verified", "shield-check", "#3b82f6"),
                       _badge("Verified", "stale-icon", "#000000"),
                   )):
            badges = await _public_badges(AsyncMock(), "t-1", None, None)

        assert len(badges) == 1
        assert badges[0]["icon"] == "shield-check"
        assert badges[0]["color"] == "#3b82f6"

    @pytest.mark.asyncio
    async def test_never_returns_more_than_the_cap(self):
        with patch("app.engines.trust_quality.service.TrustQualityService",
                   return_value=_earned(*[_badge(f"Badge {i}") for i in range(10)])):
            badges = await _public_badges(AsyncMock(), "t-1", None, None)

        assert len(badges) == MAX_PUBLIC_BADGES

    @pytest.mark.asyncio
    async def test_ignores_an_unnamed_badge(self):
        # An empty name renders as a blank pill, which tells a customer nothing and
        # looks like a rendering fault.
        with patch("app.engines.trust_quality.service.TrustQualityService",
                   return_value=_earned(_badge(""), _badge("   "), _badge("Verified"))):
            badges = await _public_badges(AsyncMock(), "t-1", None, None)

        assert [b["name"] for b in badges] == ["Verified"]


class TestFallbackIsNotFabrication:
    @pytest.mark.asyncio
    async def test_a_badge_lookup_failure_does_not_break_matching(self):
        # Provider matching decides whether a customer can book at all. It must never
        # fail because a decorative read failed.
        failing = MagicMock()
        failing.list_earned_badges = AsyncMock(side_effect=RuntimeError("boom"))
        with patch("app.engines.trust_quality.service.TrustQualityService", return_value=failing), \
             patch("app.engines.home_service_booking.matching_engine._earned_fallback_badges",
                   new=AsyncMock(return_value=[])) as fallback:
            badges = await _public_badges(AsyncMock(), "t-1", None, None)

        assert badges == []
        fallback.assert_awaited()

    @pytest.mark.asyncio
    async def test_no_configured_badges_falls_back_to_earned_facts(self):
        with patch("app.engines.trust_quality.service.TrustQualityService",
                   return_value=_earned()), \
             patch("app.engines.home_service_booking.matching_engine._earned_fallback_badges",
                   new=AsyncMock(return_value=[_badge("Verified", "shield-check")])) as fallback:
            badges = await _public_badges(AsyncMock(), "t-1", None, None)

        assert [b["name"] for b in badges] == ["Verified"]
        fallback.assert_awaited()

    @pytest.mark.asyncio
    async def test_badges_that_are_all_unnamed_fall_back_rather_than_showing_nothing(self):
        with patch("app.engines.trust_quality.service.TrustQualityService",
                   return_value=_earned(_badge(""))), \
             patch("app.engines.home_service_booking.matching_engine._earned_fallback_badges",
                   new=AsyncMock(return_value=[_badge("Verified")])):
            badges = await _public_badges(AsyncMock(), "t-1", None, None)

        assert [b["name"] for b in badges] == ["Verified"]
