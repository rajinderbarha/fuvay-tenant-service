"""Slot capacity has one authority: active technicians on the roster.

Legacy availability rows may still carry ``max_bookings_per_slot``, but the
runtime deliberately ignores it. Capacity is HEADCOUNT -- one active technician
creates one place in a slot; a missing or unreadable team creates none.

Neither the requested service nor the weekday narrows that count any more.
They used to, which made slot capacity disagree with the seats a provider had
bought: a technician with no per-staff availability row sold no slots while
still consuming a seat. Availability is published by the PROVIDER and is what
the customer picks a slot from; skills stay advisory at assignment time.
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
    async def test_service_and_weekday_do_not_narrow_capacity(self):
        """The seats a provider buys must be the capacity they get.

        These two filters were the reason billing and capacity disagreed.
        The arguments are still accepted so existing callers keep working,
        but they must not reach the query.
        """
        db = self._db(2)
        service_id = uuid.uuid4()
        day = dt.date(2026, 8, 24)  # Monday
        count = await assignable_technician_count(
            db, TENANT, master_service_id=service_id, day=day,
        )
        assert count == 2
        sql = str(db.execute.await_args.args[0])
        params = db.execute.await_args.args[1]
        assert "tenant_services" not in sql
        assert "supported_offering_ids" not in sql
        assert "provider_availability_rules" not in sql
        assert "msid" not in params
        assert "dow" not in params

    @pytest.mark.asyncio
    async def test_same_count_with_or_without_service_and_day(self):
        bare = self._db(2)
        await assignable_technician_count(bare, TENANT)
        narrowed = self._db(2)
        await assignable_technician_count(
            narrowed, TENANT, master_service_id=uuid.uuid4(), day=dt.date(2026, 8, 24),
        )
        assert str(bare.execute.await_args.args[0]) == str(narrowed.execute.await_args.args[0])

    @pytest.mark.asyncio
    async def test_a_deactivated_login_creates_no_capacity(self):
        """A roster row can be active while the user account is revoked.

        Confirmed live on a real technician. They can never open the app, so
        counting them would sell a slot nobody can work.
        """
        db = self._db(1)
        await assignable_technician_count(db, TENANT)
        sql = str(db.execute.await_args.args[0])
        assert "is_active = false" in sql
        assert "NOT EXISTS" in sql


class TestSharedDefinition:
    """Billing and capacity must count the same people."""

    def test_multi_word_designations_are_eligible(self):
        from app.engines.home_service_assignment.eligibility import is_technician_role
        # Raw-lowercasing left these unmatched, so a real "Senior Technician"
        # was refused with role_not_allowed while a plain "Technician" passed.
        assert is_technician_role("Senior Technician", None)
        assert is_technician_role("Field Engineer", None)
        assert is_technician_role("field-engineer", None)

    def test_owner_technician_counts_but_plain_owner_does_not(self):
        from app.engines.home_service_assignment.eligibility import is_technician_role
        assert is_technician_role(None, "owner_technician")
        assert not is_technician_role("", "owner")
        assert not is_technician_role("Manager", "owner")

    def test_billing_and_capacity_share_one_predicate(self):
        import inspect
        from app.engines.vertical_catalog import finance_policy_service as fps
        from app.engines.home_service_booking import provider_slot_service as pss
        assert "active_technician_sql" in inspect.getsource(
            fps.resolve_qualifying_technician_count)
        assert "active_technician_sql" in inspect.getsource(
            pss.assignable_technician_count)
