from types import SimpleNamespace
import uuid

import pytest
from fastapi import HTTPException

from app.engines.customer_home.router import (
    CampaignEventBatchBody,
    CampaignEventBatchItem,
    record_campaign_events_batch,
)


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class _FakeDb:
    def __init__(self, eligible_ids):
        self.eligible_ids = eligible_ids
        self.added = []
        self.committed = False

    async def execute(self, _statement):
        return _ScalarResult(self.eligible_ids)

    def add_all(self, rows):
        self.added.extend(rows)

    async def commit(self):
        self.committed = True


def _event(campaign_id: uuid.UUID, placement: str = "home_hero"):
    return CampaignEventBatchItem(
        campaign_id=campaign_id,
        event_type="delivered",
        placement=placement,
    )


@pytest.mark.asyncio
async def test_campaign_delivery_batch_is_one_atomic_write():
    first, second = uuid.uuid4(), uuid.uuid4()
    db = _FakeDb([first, second])
    response = await record_campaign_events_batch(
        CampaignEventBatchBody(events=[_event(first), _event(second, "home_banner")]),
        SimpleNamespace(state=SimpleNamespace(request_id="req_batch")),
        SimpleNamespace(user_id=str(uuid.uuid4())),
        db,
    )

    assert response.data == {"recorded": 2}
    assert len(db.added) == 2
    assert db.committed is True


@pytest.mark.asyncio
async def test_campaign_delivery_batch_rejects_duplicate_campaigns():
    campaign_id = uuid.uuid4()
    db = _FakeDb([campaign_id])

    with pytest.raises(HTTPException) as exc:
        await record_campaign_events_batch(
            CampaignEventBatchBody(events=[_event(campaign_id), _event(campaign_id)]),
            SimpleNamespace(state=SimpleNamespace(request_id="req_batch")),
            SimpleNamespace(user_id=str(uuid.uuid4())),
            db,
        )

    assert exc.value.status_code == 422
    assert db.added == []
    assert db.committed is False
