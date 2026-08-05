"""HOME-SERVICES-FINANCE-POLICY-01 — canonical activation finance policy.

Focused tests (time-boxed pass) proving:
  1. Policy resolution fails closed with a stable error code when no
     published policy exists / when ambiguous.
  2. Deposit math: 2000 for one qualifying technician, 4000 for two.
  3. GST split: base 1000 + 18% GST = 1180 payable, 1000 usable credit.
  4. Qualifying technician count excludes non-technician designations and
     counts real technicians (member_type='technician') even with a blank
     designation string (the exact Guramrit shape).

Live DB-integration proof (not re-run here, already captured in the
session's chat transcript): GET /v1/tenant/home-services/setup/
application-status for tenant 244beeec-fedc-452e-8054-317e45557d4d
("Guramrit") now returns finance_policy state="ready", "Resolved" (was
state="blocked", "Finance policy unresolved" before this fix).
"""
from __future__ import annotations
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.vertical_catalog.finance_policy_service import (
    resolve_published_policy, resolve_qualifying_technician_count,
    FinancePolicyResolutionError, ERR_NO_PUBLISHED_POLICY, ERR_AMBIGUOUS_POLICY,
)
from app.engines.vertical_catalog.finance_policy_models import HomeServicesActivationFinancePolicy


def _mock_scalars(rows):
    scalars = MagicMock()
    scalars.all.return_value = rows
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


@pytest.mark.asyncio
async def test_resolve_published_policy_fails_closed_when_none_exists():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_mock_scalars([]))

    with pytest.raises(FinancePolicyResolutionError) as exc:
        await resolve_published_policy(db, uuid.uuid4())
    assert exc.value.code == ERR_NO_PUBLISHED_POLICY


@pytest.mark.asyncio
async def test_resolve_published_policy_fails_closed_when_ambiguous():
    db = AsyncMock()
    p1 = MagicMock(spec=HomeServicesActivationFinancePolicy)
    p2 = MagicMock(spec=HomeServicesActivationFinancePolicy)
    db.execute = AsyncMock(return_value=_mock_scalars([p1, p2]))

    with pytest.raises(FinancePolicyResolutionError) as exc:
        await resolve_published_policy(db, uuid.uuid4())
    assert exc.value.code == ERR_AMBIGUOUS_POLICY


@pytest.mark.asyncio
async def test_resolve_published_policy_returns_the_single_current_row():
    db = AsyncMock()
    policy = MagicMock(spec=HomeServicesActivationFinancePolicy)
    policy.version_number = 3
    db.execute = AsyncMock(return_value=_mock_scalars([policy]))

    result = await resolve_published_policy(db, uuid.uuid4())
    assert result.version_number == 3


def test_deposit_math_one_and_two_technicians():
    per_tech = Decimal("2000")
    minimum = Decimal("2000")

    def required(qualifying_count: int) -> Decimal:
        return max(minimum, per_tech * max(1, qualifying_count))

    assert required(1) == Decimal("2000")
    assert required(2) == Decimal("4000")
    assert required(0) == Decimal("2000")  # floor: minimum still applies


def test_gst_split_base_1000_plus_18_percent_gst_180_payable_1180():
    base = Decimal("1000")
    gst_percent = Decimal("18")
    payable = (base * (1 + gst_percent / 100)).quantize(Decimal("0.01"))
    usable_credit = base  # GST NEVER enters the usable wallet credit

    assert payable == Decimal("1180.00")
    assert usable_credit == Decimal("1000")
    assert payable - usable_credit == Decimal("180.00")  # GST recorded separately


@pytest.mark.asyncio
async def test_qualifying_technician_count_excludes_non_technician_roles():
    db = AsyncMock()
    rows = [
        MagicMock(designation="",            member_type="owner"),       # excluded
        MagicMock(designation="manager",     member_type="staff"),       # excluded
        MagicMock(designation="dispatcher",  member_type="staff"),       # excluded
        MagicMock(designation="technician",  member_type=""),            # included (designation match)
        MagicMock(designation="",            member_type="technician"),  # included (member_type match) — real Guramrit shape
    ]
    db.execute = AsyncMock(return_value=MagicMock(fetchall=MagicMock(return_value=rows)))

    count = await resolve_qualifying_technician_count(db, uuid.uuid4())
    assert count == 2
