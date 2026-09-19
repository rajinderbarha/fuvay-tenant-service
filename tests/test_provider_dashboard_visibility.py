"""Provider dashboard shows live work, not cancelled operational history."""
from types import SimpleNamespace
import uuid

import pytest

from app.engines.execution.home_services_dashboard_service import (
    _job_pipeline, _todays_jobs,
)


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _DB:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    async def execute(self, statement, _params):
        self.statements.append(str(statement))
        return _Rows(self.rows)


@pytest.mark.asyncio
async def test_cancelled_group_is_not_returned_in_dashboard_pipeline():
    db = _DB([("assigned", 2), ("cancelled", 4), ("failed", 1)])

    pipeline = await _job_pipeline(db, uuid.uuid4())

    assert "cancelled" not in {item["key"] for item in pipeline}
    assert next(item for item in pipeline if item["key"] == "scheduled")["count"] == 2
    assert "NOT IN ('cancelled','failed','closed_estimate_declined')" in db.statements[0]


@pytest.mark.asyncio
async def test_cancelled_job_is_defensively_hidden_from_todays_dashboard():
    common = {
        "scheduled_date": None, "scheduled_time_window": "10:00-12:00",
        "city": "Bassi Pathana", "assigned_staff_id": None,
        "customer_name": "Customer", "service_name": "AC Repair",
        "technician_name": None,
    }
    db = _DB([
        SimpleNamespace(id=uuid.uuid4(), job_number="JOB-LIVE", status="assigned", **common),
        SimpleNamespace(id=uuid.uuid4(), job_number="JOB-CANCELLED", status="cancelled", **common),
    ])

    jobs = await _todays_jobs(db, uuid.uuid4())

    assert [job["job_number"] for job in jobs] == ["JOB-LIVE"]
    assert "NOT IN ('cancelled','failed','closed_estimate_declined')" in db.statements[0]
