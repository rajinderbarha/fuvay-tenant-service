"""MODULE-L5-56 — two live defects found while walking real jobs to completion.

1. `usage_credit_ledger.deduction_source` was VARCHAR(50) while the commission
   path writes "category_commission:<uuid>" / "monetization_policy:<uuid>" (56
   chars). Every completion of a Home Services job under a published
   PERCENTAGE_COMMISSION policy died on StringDataRightTruncationError and
   returned HTTP 500 -- the job could not be completed at all. Migration 235
   widens the column; the test below is the invariant, not the symptom: the
   column must fit the longest label the code can emit.

2. The workflow checklist gate (`_assert_checklist_satisfied`) only accepted the
   SUPERSEDED quote_checklist generation, so on a job type with
   checklist_required=True a technician could complete every point of the real
   (checklist_catalog) checklist and start-service still answered 409, with
   nothing in any UI able to satisfy it.
"""
from __future__ import annotations

import asyncio
import os
import re
import uuid

import pytest

from app.engines.checklist_catalog import constants as cc
from app.engines.execution.home_service_service import HomeServiceJobExecutionService
from app.engines.finance_hub.home_services_finance_service import _policy_source
from app.engines.tenant_engine.models import UsageCreditLedger

ROOT = os.path.dirname(os.path.dirname(__file__))
DEDUCTION_SRC = os.path.join(ROOT, "app", "engines", "execution", "usage_credit_deduction.py")
MIGRATION_235 = os.path.join(ROOT, "alembic", "versions", "235_widen_deduction_source.py")

UUID_LEN = 36


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── 1. The column must fit every label the code can write ───────────────────

def test_deduction_source_column_fits_every_label_the_code_emits():
    """Reads the prefixes out of the source, so ADDING a longer prefix later
    fails here rather than in production at the moment of completion."""
    src = _read(DEDUCTION_SRC)
    prefixes = re.findall(r'f"([a-z_]+):\{', src)
    assert prefixes, "expected prefixed deduction_source labels to still exist"
    limit = UsageCreditLedger.__table__.c.deduction_source.type.length
    for prefix in prefixes:
        assert len(prefix) + 1 + UUID_LEN <= limit, (
            f'"{prefix}:<uuid>" does not fit deduction_source({limit})')


def test_migration_235_widens_the_column():
    assert os.path.exists(MIGRATION_235)
    src = _read(MIGRATION_235)
    assert 'revision = "235"' in src
    assert 'down_revision = "234"' in src
    assert "deduction_source" in src and "usage_credit_ledger" in src


# ── 2. Finance views must not mislabel a commission charge ───────────────────

def test_policy_source_distinguishes_the_three_shapes():
    assert _policy_source(None) == "unresolved_zero_charge"
    assert _policy_source(f"category_commission:{uuid.uuid4()}") == "category_commission"
    assert _policy_source(f"monetization_policy:{uuid.uuid4()}") == "monetization_policy"
    # A bare pricing-rule uuid is the legacy flat-credit shape.
    assert _policy_source(str(uuid.uuid4())) == "platform_pricing_rule"


# ── 3. The checklist gate accepts the checklist the technician actually fills ─

class _Result:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return list(self._values)

    def first(self):
        return self._values[0] if self._values else None


class _FakeDb:
    """Answers the two queries the gate makes, in the order it makes them:
    canonical instance states, then the legacy row."""

    def __init__(self, canonical_states, legacy_row=None):
        self._answers = [_Result(canonical_states), _Result([legacy_row] if legacy_row else [])]

    async def execute(self, _stmt):
        return self._answers.pop(0)


class _Workflow:
    checklist_required = True


def _gate(canonical_states, legacy_row=None):
    svc = HomeServiceJobExecutionService()

    async def _resolve(_db, _job):
        return _Workflow()

    svc._resolve_job_type_workflow = _resolve  # type: ignore[method-assign]
    job = type("Job", (), {"id": uuid.uuid4(), "status": "inspection_done"})()
    return svc._assert_checklist_satisfied(_FakeDb(canonical_states, legacy_row), job)


def test_completed_canonical_checklist_satisfies_the_gate():
    asyncio.run(_gate([cc.INSTANCE_COMPLETED]))


def test_waived_canonical_checklist_satisfies_the_gate():
    asyncio.run(_gate([cc.INSTANCE_WAIVED]))


def test_open_canonical_checklist_still_blocks_and_says_so():
    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException) as exc:
        asyncio.run(_gate([cc.INSTANCE_IN_PROGRESS]))
    # The technician is told the checklist ON THIS JOB is open, rather than the
    # dead-end "a checklist is required" with nothing to act on.
    assert "must be completed" in exc.value.detail


def test_legacy_checklist_row_still_satisfies_the_gate():
    asyncio.run(_gate([], legacy_row=uuid.uuid4()))


def test_no_checklist_at_all_still_fails_closed():
    from app.exceptions import ServiceOSException
    with pytest.raises(ServiceOSException):
        asyncio.run(_gate([]))
