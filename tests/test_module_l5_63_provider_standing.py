"""MODULE-L5-63 — provider standing: one earned level, or nothing.

The ladder replaces a row of independent badges with a single claim, and the whole
value of that claim rests on it being unearnable by default. So the tests that matter
most here are the refusals: no level for a provider with no record, no level from
volume alone, and no level for an unverified business however much work it has done.

Supersession needs no revocation logic and is asserted as such: the level is computed
from current facts, so holding two at once is not representable.
"""
from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.trust_quality.provider_standing import (
    LADDER, StandingFacts, resolve_level, resolve_standing_badge, satisfies,
)


def facts(**overrides) -> StandingFacts:
    base = dict(
        completed_jobs=0, approved_reviews=0, average_rating=None,
        verified=True, days_active=0,
    )
    base.update(overrides)
    return StandingFacts(**base)


def _level(name: str):
    return next(l for l in LADDER if l.name == name)


class TestNothingIsEarnedByDefault:
    def test_a_brand_new_provider_has_no_level(self):
        # The fallback for "we cannot vouch for them yet" is silence. A starter badge
        # nobody earned devalues the ones that were earned.
        assert resolve_level(facts()) is None

    def test_an_unverified_provider_earns_nothing_however_much_work_they_have_done(self):
        assert resolve_level(facts(
            verified=False, completed_jobs=5000, approved_reviews=900,
            average_rating=5.0, days_active=4000,
        )) is None

    def test_volume_alone_does_not_reach_a_level_that_requires_quality(self):
        # 300 finished jobs at 3.9 is not Gold. The level is a claim about quality as
        # well as volume.
        reached = resolve_level(facts(
            completed_jobs=300, approved_reviews=200, average_rating=3.9, days_active=800,
        ))
        assert reached is not None
        assert reached.name == "Bronze Partner"

    def test_a_missing_rating_fails_a_rung_that_requires_one(self):
        # Absence is not a pass.
        assert satisfies(_level("Silver Partner"), facts(
            completed_jobs=100, approved_reviews=50, average_rating=None, days_active=500,
        )) is False


class TestTheLadder:
    def test_bronze_needs_verification_and_real_finished_work(self):
        assert resolve_level(facts(completed_jobs=4)) is None
        assert resolve_level(facts(completed_jobs=5)).name == "Bronze Partner"

    def test_higher_levels_need_time_as_well_as_numbers(self):
        # A good month is not a sustained record.
        young = facts(completed_jobs=40, approved_reviews=20, average_rating=4.6, days_active=10)
        assert resolve_level(young).name == "Bronze Partner"
        assert resolve_level(
            facts(completed_jobs=40, approved_reviews=20, average_rating=4.6, days_active=120)
        ).name == "Silver Partner"

    def test_the_highest_reached_rung_wins(self):
        elite = facts(
            completed_jobs=400, approved_reviews=150, average_rating=4.9, days_active=800,
        )
        assert resolve_level(elite).name == "Elite Partner"

    def test_a_level_is_a_single_value_so_two_cannot_be_held_at_once(self):
        # Supersession is structural: reaching Silver IS no longer being Bronze, which
        # is why there is no award to revoke and no way to accumulate rungs.
        reached = resolve_level(facts(
            completed_jobs=40, approved_reviews=20, average_rating=4.6, days_active=120,
        ))
        assert reached in LADDER
        assert isinstance(reached.level, int)

    def test_the_ladder_is_ordered_and_gets_strictly_harder_on_volume(self):
        rungs = sorted(LADDER, key=lambda l: l.level)
        assert [r.level for r in rungs] == list(range(1, len(rungs) + 1))
        jobs = [r.min_completed_jobs for r in rungs]
        assert jobs == sorted(jobs)
        assert len(set(r.badge_key for r in rungs)) == len(rungs)


class TestPresentation:
    @pytest.mark.asyncio
    async def test_uses_the_admin_configured_name_icon_and_colour_when_there_is_one(self):
        # Trust & Quality stays the place these are named and styled; the code-level
        # defaults are a fallback, never an override.
        db = MagicMock()
        with patch("app.engines.trust_quality.provider_standing.load_facts",
                   new=AsyncMock(return_value=facts(completed_jobs=10))), \
             patch("app.engines.trust_quality.provider_standing._admin_presentation",
                   new=AsyncMock(return_value={
                       "name": "Fuvay Certified", "icon": "star", "color": "#123456"})):
            badge = await resolve_standing_badge(db, "t-1")

        assert badge == {"name": "Fuvay Certified", "icon": "star",
                         "color": "#123456", "level": 1}

    @pytest.mark.asyncio
    async def test_falls_back_to_the_built_in_presentation(self):
        db = MagicMock()
        with patch("app.engines.trust_quality.provider_standing.load_facts",
                   new=AsyncMock(return_value=facts(completed_jobs=10))), \
             patch("app.engines.trust_quality.provider_standing._admin_presentation",
                   new=AsyncMock(return_value=None)):
            badge = await resolve_standing_badge(db, "t-1")

        assert badge["name"] == "Bronze Partner"
        # The icon is what the compact card shows, so it must always be present.
        assert badge["icon"]
        assert badge["color"]

    @pytest.mark.asyncio
    async def test_no_badge_for_a_provider_who_has_earned_no_level(self):
        db = MagicMock()
        with patch("app.engines.trust_quality.provider_standing.load_facts",
                   new=AsyncMock(return_value=facts())):
            assert await resolve_standing_badge(db, "t-1") is None

    @pytest.mark.asyncio
    async def test_a_failed_read_yields_no_badge_rather_than_a_guess(self):
        # A decorative read must never break a booking card, and must never invent a
        # standing it could not confirm.
        db = MagicMock()
        with patch("app.engines.trust_quality.provider_standing.load_facts",
                   new=AsyncMock(side_effect=RuntimeError("db gone"))):
            assert await resolve_standing_badge(db, "t-1") is None

    @pytest.mark.asyncio
    async def test_an_unknown_tenant_has_no_standing(self):
        db = MagicMock()
        with patch("app.engines.trust_quality.provider_standing.load_facts",
                   new=AsyncMock(return_value=None)):
            assert await resolve_standing_badge(db, "t-1") is None


class TestStandingLeadsTheCustomerBadgeList:
    @pytest.mark.asyncio
    async def test_standing_comes_first_so_the_cap_never_drops_it(self):
        from app.engines.home_service_booking import matching_engine

        earned = MagicMock()
        earned.list_earned_badges = AsyncMock(return_value=[
            {"name": "AC Specialist", "icon": "snow", "color": None},
            {"name": "Verified Business", "icon": "shield-check", "color": None},
            {"name": "Something Else", "icon": None, "color": None},
        ])
        with patch("app.engines.trust_quality.service.TrustQualityService", return_value=earned), \
             patch("app.engines.trust_quality.provider_standing.resolve_standing_badge",
                   new=AsyncMock(return_value={
                       "name": "Gold Partner", "icon": "trophy",
                       "color": "#f59e0b", "level": 3})):
            badges = await matching_engine._public_badges(AsyncMock(), "t-1", None, None)

        assert badges[0]["name"] == "Gold Partner"
        assert badges[0]["level"] == 3
        assert len(badges) == matching_engine.MAX_PUBLIC_BADGES

    @pytest.mark.asyncio
    async def test_a_provider_with_standing_but_no_other_badges_still_shows_it(self):
        from app.engines.home_service_booking import matching_engine

        empty = MagicMock()
        empty.list_earned_badges = AsyncMock(return_value=[])
        with patch("app.engines.trust_quality.service.TrustQualityService", return_value=empty), \
             patch("app.engines.trust_quality.provider_standing.resolve_standing_badge",
                   new=AsyncMock(return_value={
                       "name": "Bronze Partner", "icon": "medal",
                       "color": "#b45309", "level": 1})):
            badges = await matching_engine._public_badges(AsyncMock(), "t-1", None, None)

        assert [b["name"] for b in badges] == ["Bronze Partner"]
