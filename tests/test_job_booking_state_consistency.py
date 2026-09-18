"""The job row and the customer-facing booking row must not drift apart.

Every bug covered here was found by reading live staging data on 2026-09-18,
not by reasoning about the code:

  * `service_bookings.status` held four values the customer app could not
    name, because it mirrors the JOB status verbatim.
  * BK-20260912-000005 had booking `inspection_done` against job
    `closed_estimate_declined` -- the quote engine moved the job and never
    touched the booking.
  * `force_closed` / `voided` were private to one admin module, so no
    terminal check anywhere else knew about them.
  * The fair-share ledger query failed on EVERY match with `column
    "new_value" does not exist`, silently disabling provider rotation.
"""
from __future__ import annotations

import inspect
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── the fair-share ledger query ──────────────────────────────────────────────

def test_fair_share_ledger_scopes_its_order_by_to_its_own_subquery():
    """A trailing ORDER BY after UNION ALL binds to the whole union.

    The union's only output column is `provider_id`, so `new_value` and
    `created_at` were out of scope and Postgres rejected the entire
    statement. The except branch around the call is fail-open, so this never
    surfaced as an error -- allocation counts just came back empty every
    time, flattening fair share to a constant and disabling both the
    round-robin and the anti-stampede hold.
    """
    from app.engines.home_service_booking.matching_engine import (
        _recent_allocation_counts,
    )

    sql = inspect.getsource(_recent_allocation_counts)
    union_at = sql.index("UNION ALL")
    distinct_at = sql.index("SELECT DISTINCT ON")
    order_at = sql.index("ORDER BY COALESCE")
    close_at = sql.index("AS recent_matches")

    # The DISTINCT ON branch and its ORDER BY must both sit inside the
    # wrapper subquery that closes with `AS recent_matches`.
    assert union_at < distinct_at < order_at < close_at, (
        "the DISTINCT ON branch and its ORDER BY must stay inside their own "
        "subquery, or the ORDER BY re-binds to the union"
    )


# ── one canonical terminal set ───────────────────────────────────────────────

def test_admin_terminal_statuses_are_part_of_the_shared_vocabulary():
    from app.engines.execution.constants import (
        JS_FORCE_CLOSED, JS_VOIDED, TERMINAL_JOB_STATUSES,
    )

    for status in (JS_FORCE_CLOSED, JS_VOIDED, "completed", "cancelled",
                   "failed", "closed_estimate_declined"):
        assert status in TERMINAL_JOB_STATUSES


def test_admin_job_actions_uses_the_shared_terminal_names():
    """They used to be string literals private to this module, which is how
    they stayed invisible to every other terminal check."""
    from app.engines.execution import admin_job_actions
    from app.engines.execution.constants import JS_FORCE_CLOSED, JS_VOIDED

    assert admin_job_actions.JS_FORCE_CLOSED is JS_FORCE_CLOSED
    assert admin_job_actions.JS_VOIDED is JS_VOIDED


def test_customer_active_bucket_excludes_every_terminal_status():
    """A force-closed, voided, failed or estimate-declined booking used to
    sit in the customer's Active tab for good, and inflate its count."""
    from app.engines.final_records.customer_router import _TERMINAL_BOOKING_STATUSES

    for status in ("completed", "cancelled", "failed",
                   "closed_estimate_declined", "force_closed", "voided"):
        assert status in _TERMINAL_BOOKING_STATUSES


# ── the booking mirror ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_booking_of_job_issues_exactly_one_statement():
    """Resolved through a correlated subquery, not a SELECT then an UPDATE."""
    from app.engines.final_records.booking_job_sync import sync_booking_of_job

    db = MagicMock()
    db.execute = AsyncMock()
    await sync_booking_of_job(db, uuid.uuid4(), "closed_estimate_declined")

    assert db.execute.await_count == 1
    statement = str(db.execute.await_args[0][0])
    assert statement.lower().startswith("update service_bookings")
    assert "service_jobs" in statement, "booking must be located via its job"


@pytest.mark.asyncio
async def test_sync_is_a_no_op_without_an_id_or_a_status():
    from app.engines.final_records.booking_job_sync import (
        sync_booking_of_job, sync_booking_to_job_status,
    )

    db = MagicMock()
    db.execute = AsyncMock()
    await sync_booking_of_job(db, None, "completed")
    await sync_booking_of_job(db, uuid.uuid4(), "")
    await sync_booking_to_job_status(db, None, "completed")
    await sync_booking_to_job_status(db, uuid.uuid4(), "")
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_quote_engine_mirrors_its_job_status_onto_the_booking():
    """Confirmed live: declining an estimate left the booking reading
    `inspection_done` while the job read `closed_estimate_declined`."""
    from app.engines.execution.constants import (
        JS_QUOTE_REQUIRED, JS_CLOSED_ESTIMATE_DECLINED,
    )
    from app.engines.quote_checklist.quote_service import ServiceJobQuoteService

    job_id = uuid.uuid4()
    statements: list[str] = []

    db = MagicMock()

    async def execute(stmt, *_a, **_kw):
        statements.append(str(stmt))
        result = MagicMock()
        result.scalar_one_or_none.return_value = JS_QUOTE_REQUIRED
        return result

    db.execute = AsyncMock(side_effect=execute)
    db.scalar = AsyncMock(return_value=JS_QUOTE_REQUIRED)

    service = ServiceJobQuoteService()
    await service._sync_job_status(db, job_id, JS_CLOSED_ESTIMATE_DECLINED)

    updated = [s.lower() for s in statements if s.lower().startswith("update")]
    assert any("service_jobs" in s for s in updated), "the job must be written"
    assert any("service_bookings" in s for s in updated), (
        "the booking must be written in the same call, or the customer keeps "
        "a booking that outlived its job"
    )


# ── concurrent transitions ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_transition_on_a_stale_read_is_rejected_not_double_applied():
    """Two taps, or a mobile retry after a socket timeout, both used to read
    the same status, both pass the transition guard, and both write."""
    from app.exceptions import ServiceOSException
    from app.engines.execution.home_service_service import HomeServiceJobExecutionService

    job = SimpleNamespace(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), status="on_the_way",
        tenant_id=uuid.uuid4(),
    )
    db = MagicMock()
    # The row really holds `reached_site`: the winning request already
    # committed while this one was in flight.
    db.scalar = AsyncMock(return_value="reached_site")
    db.execute = AsyncMock()

    service = HomeServiceJobExecutionService()
    with pytest.raises(ServiceOSException) as excinfo:
        await service._set_status(
            db, job, "reached_site", "technician_reached_site",
            actor_user_id=None, actor_role="staff",
        )

    assert excinfo.value.status_code == 409
    assert "reached_site" in str(excinfo.value)


@pytest.mark.asyncio
async def test_re_applying_the_same_status_does_nothing():
    """A retry of a request that actually succeeded must not log a second
    event or fire the side effects again."""
    from app.engines.execution.home_service_service import HomeServiceJobExecutionService

    job = SimpleNamespace(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), status="reached_site",
        tenant_id=uuid.uuid4(),
    )
    db = MagicMock()
    db.scalar = AsyncMock(return_value="reached_site")
    db.execute = AsyncMock()
    db.add = MagicMock()

    service = HomeServiceJobExecutionService()
    await service._set_status(
        db, job, "reached_site", "technician_reached_site",
        actor_user_id=None, actor_role="staff",
    )

    db.add.assert_not_called()
    assert job.status == "reached_site"
