from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


class _Scalar:
    def __init__(self, value: int):
        self.value = value

    def scalar_one(self):
        return self.value


@pytest.mark.asyncio
async def test_provider_allowance_counts_only_approved_provider_changes():
    from app.engines.home_service_assignment import provider_reschedule_service as service

    db = SimpleNamespace(execute=AsyncMock(return_value=_Scalar(2)))
    assert await service._approved_provider_reschedule_count(db, uuid.uuid4()) == 2

    statement = db.execute.await_args.args[0]
    params = set(statement.compile().params.values())
    assert "provider" in params
    assert "approved" in params


@pytest.mark.asyncio
async def test_customer_allowance_counts_only_customer_reschedule_events():
    from app.engines.home_service_assignment.constants import EVENT_CUSTOMER_RESCHEDULED
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    db = SimpleNamespace(execute=AsyncMock(return_value=_Scalar(1)))
    service = HomeServiceJobAssignmentService(db)
    assert await service._customer_reschedule_count(uuid.uuid4()) == 1

    statement = db.execute.await_args.args[0]
    assert EVENT_CUSTOMER_RESCHEDULED in set(statement.compile().params.values())
