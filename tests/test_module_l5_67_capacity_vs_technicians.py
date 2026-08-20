"""Slot capacity has one authority: ready technicians.

Legacy availability rows may still carry ``max_bookings_per_slot``, but the
runtime deliberately ignores it. One ready, service-assigned technician creates
one place in a slot; a missing or unreadable team creates none.
"""
from __future__ import annotations

import datetime as dt
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.home_service_booking.provider_slot_service import (
    _effective_cap,
    assignable_technician_count,
)

TENANT = uuid.uuid4()


class TestAutomaticCapacity:
    def test_legacy_rule_cannot_raise_capacity_above_the_team(self):
        assert _effective_cap({"max_bookings_per_slot": 5}, 2) == 2

    def test_legacy_rule_cannot_reduce_real_team_capacity(self):
        assert _effective_cap({"max_bookings_per_slot": 1}, 4) == 4

    def test_unset_rule_uses_the_ready_team_count(self):
        assert _effective_cap({}, 5) == 5

    def test_no_assignable_technicians_means_no_capacity(self):
        assert _effective_cap({}, 0) == 0

    def test_unreadable_team_fails_closed(self):
        assert _effective_cap({"max_bookings_per_slot": 5}, -1) == 0


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
    async def test_failed_read_reports_minus_one(self):
        db = MagicMock()
        db.execute = AsyncMock(side_effect=RuntimeError("relation does not exist"))
        assert await assignable_technician_count(db, TENANT) == -1

    @pytest.mark.asyncio
    async def test_empty_result_is_zero(self):
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        assert await assignable_technician_count(db, TENANT) == 0

    @pytest.mark.asyncio
    async def test_queries_the_real_table_and_columns(self):
        db = self._db(2)
        await assignable_technician_count(db, TENANT)
        sql = str(db.execute.await_args.args[0])
        assert "provider_team_members" in sql
        assert "can_receive_assignment" in sql
        assert "staff_members" not in sql

    @pytest.mark.asyncio
    async def test_service_and_weekday_are_part_of_capacity(self):
        db = self._db(2)
        service_id = uuid.uuid4()
        day = dt.date(2026, 8, 24)  # Monday
        await assignable_technician_count(
            db, TENANT, master_service_id=service_id, day=day,
        )
        sql = str(db.execute.await_args.args[0])
        params = db.execute.await_args.args[1]
        assert "tenant_services" in sql
        assert "supported_offering_ids" in sql
        assert "provider_availability_rules" in sql
        assert params["msid"] == str(service_id)
        assert params["dow"] == 1
