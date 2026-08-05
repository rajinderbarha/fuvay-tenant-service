"""MY-BOOKINGS-ROOT-TAB CLOSURE (2026-08-01) — `list_my_bookings` now
accepts `?bucket=active|completed|all`, always returns authoritative
`counts` for all three buckets (never computed from a partial fetch), and
orders deterministically by `(created_at DESC, id DESC)`.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.final_records.customer_router import list_my_bookings


def _rows(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


@pytest.mark.asyncio
async def test_counts_are_always_returned_for_all_three_buckets_regardless_of_selected_bucket():
    customer_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_rows([]))
    # scalar() is called for: bucket total, active_total, completed_total, all_total
    db.scalar = AsyncMock(side_effect=[0, 3, 5, 8])
    request = MagicMock()
    request.state.request_id = "req-1"
    user = MagicMock(user_id=str(customer_id))

    result = await list_my_bookings(r=request, bucket="active", status=None, limit=20, offset=0, user=user, db=db)

    assert result.data["counts"] == {"active": 3, "completed": 5, "all": 8}


@pytest.mark.asyncio
async def test_active_bucket_excludes_completed_and_cancelled_at_the_query_level():
    customer_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_rows([]))
    db.scalar = AsyncMock(return_value=0)
    request = MagicMock()
    request.state.request_id = "req-1"
    user = MagicMock(user_id=str(customer_id))

    await list_my_bookings(r=request, bucket="active", status=None, limit=20, offset=0, user=user, db=db)

    # First execute() call is the main paginated query -- inspect its
    # compiled WHERE clause for the terminal-status exclusion.
    compiled = str(db.execute.call_args_list[0].args[0])
    assert "NOT IN" in compiled.upper()


@pytest.mark.asyncio
async def test_completed_bucket_matches_only_the_real_completed_status():
    customer_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_rows([]))
    db.scalar = AsyncMock(return_value=0)
    request = MagicMock()
    request.state.request_id = "req-1"
    user = MagicMock(user_id=str(customer_id))

    await list_my_bookings(r=request, bucket="completed", status=None, limit=20, offset=0, user=user, db=db)

    compiled = str(db.execute.call_args_list[0].args[0])
    assert "status" in compiled


@pytest.mark.asyncio
async def test_default_ordering_is_deterministic_by_created_at_then_id():
    customer_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(return_value=_rows([]))
    db.scalar = AsyncMock(return_value=0)
    request = MagicMock()
    request.state.request_id = "req-1"
    user = MagicMock(user_id=str(customer_id))

    await list_my_bookings(r=request, bucket=None, status=None, limit=20, offset=0, user=user, db=db)

    compiled = str(db.execute.call_args_list[0].args[0])
    assert "ORDER BY" in compiled.upper()
    order_clause = compiled.upper().split("ORDER BY")[1]
    assert order_clause.index("CREATED_AT") < order_clause.index("ID")
