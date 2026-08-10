"""MODULE-L5-67 — a provider cannot offer more concurrent visits than it has people.

Per-slot capacity is typed into the availability rule by hand, and nothing bounded it. A
provider with two technicians could set five bookings per slot and the engine would offer
all five: the fifth customer gets a confirmed slot that no human can attend, and nobody
finds out until the day.

Live proof this was real: the demo provider has exactly 2 assignable technicians in
`provider_team_members`, and its availability rules were free to claim any number.

The fallback direction matters as much as the cap. An unreadable team must NOT close a
provider's calendar -- refusing every booking is a worse failure than the one being
prevented -- while a provider with genuinely nobody assignable has no capacity, and that
is reported rather than rounded up to one.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.home_service_booking.provider_slot_service import (
    FALLBACK_MAX_PER_SLOT, _effective_cap, assignable_technician_count,
)

TENANT = uuid.uuid4()


class TestTheCap:
    def test_a_rule_claiming_more_than_the_team_is_cut_to_the_team(self):
        assert _effective_cap({"max_bookings_per_slot": 5}, 2) == 2

    def test_a_rule_within_the_team_is_left_alone(self):
        # The cap is a ceiling, not a target: a provider who wants one visit at a time
        # with four technicians gets one.
        assert _effective_cap({"max_bookings_per_slot": 1}, 4) == 1

    def test_an_unset_rule_uses_the_stated_fallback_still_capped(self):
        assert _effective_cap({}, 5) == FALLBACK_MAX_PER_SLOT
        assert _effective_cap({}, 0) == 0

    def test_no_assignable_technicians_means_no_capacity(self):
        # Not rounded up to one. A booking nobody can attend is the thing being prevented,
        # and offering a slot with an empty team is exactly that booking.
        assert _effective_cap({"max_bookings_per_slot": 3}, 0) == 0

    def test_an_unreadable_team_leaves_the_rule_standing(self):
        # -1 is "could not read". Closing the whole calendar on a failed query would be a
        # bigger outage than the overbooking it guards against.
        assert _effective_cap({"max_bookings_per_slot": 5}, -1) == 5


class TestCountingTheTeam:
    @staticmethod
    def _db(count):
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=(count,))))
        return db

    @pytest.mark.asyncio
    async def test_counts_what_the_query_returns(self):
        assert await assignable_technician_count(self._db(3), TENANT) == 3

    @pytest.mark.asyncio
    async def test_a_failed_read_reports_minus_one_not_zero(self):
        # Zero would mean "no capacity" and would close the calendar; -1 means "unknown"
        # and leaves the rule in charge. Conflating the two is how a query error becomes
        # an outage.
        db = MagicMock()
        db.execute = AsyncMock(side_effect=RuntimeError("relation does not exist"))
        assert await assignable_technician_count(db, TENANT) == -1

    @pytest.mark.asyncio
    async def test_an_empty_result_is_zero(self):
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        assert await assignable_technician_count(db, TENANT) == 0

    @pytest.mark.asyncio
    async def test_queries_the_real_table_and_columns(self):
        # This guard exists because the first version of this query used `staff_members`
        # with `can_receive_assignments` -- neither of which exists. It threw, the fallback
        # swallowed it, and the cap silently did nothing. The live schema is
        # `provider_team_members`, `can_receive_assignment` (singular), and `status`.
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=(2,))))
        await assignable_technician_count(db, TENANT)

        sql = str(db.execute.await_args.args[0])
        assert "provider_team_members" in sql
        assert "can_receive_assignment " in sql or "can_receive_assignment," in sql or "can_receive_assignment)" in sql
        assert "staff_members" not in sql
