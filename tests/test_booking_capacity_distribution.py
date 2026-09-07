import datetime as dt
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.home_service_booking import provider_slot_service as slots


@pytest.mark.parametrize('limit,expected', [(4, [1, 1, 1, 1]), (6, [2, 2, 1, 1]), (12, [3, 3, 3, 3]), (99, [3, 3, 3, 3])])
def test_balanced_daily_capacity(limit, expected):
    rule = {'start_time': '09:00', 'end_time': '18:00', 'max_jobs_per_day': limit}
    assert list(slots._slot_allocation([rule], 3).values()) == expected


@pytest.mark.asyncio
async def test_preview_decrements_places_after_booking():
    rule = {'start_time': '09:00', 'end_time': '18:00'}
    with patch.object(slots, '_is_closed', AsyncMock(return_value=False)), \
         patch.object(slots, '_provider_rules_for_day', AsyncMock(return_value=[rule])), \
         patch.object(slots, 'assignable_technician_count', AsyncMock(return_value=3)), \
         patch.object(slots, '_booked_counts', AsyncMock(side_effect=[{}, {'09:00-11:00': 1}])):
        before = await slots.daily_slot_preview(MagicMock(), uuid.uuid4(), dt.date(2026, 9, 8))
        after = await slots.daily_slot_preview(MagicMock(), uuid.uuid4(), dt.date(2026, 9, 8))
    assert before['slots'][0]['available_slots'] == 3
    assert after['slots'][0]['available_slots'] == 2
    assert after['daily_remaining'] == 11


@pytest.mark.asyncio
async def test_holiday_has_no_slots():
    with patch.object(slots, '_is_closed', AsyncMock(return_value=True)):
        preview = await slots.daily_slot_preview(MagicMock(), uuid.uuid4(), dt.date(2026, 9, 8))
    assert preview['closed'] and preview['slots'] == []
    assert preview['daily_remaining'] == 0


@pytest.mark.asyncio
async def test_daily_limit_rejects_more_than_purchased_team_can_deliver():
    from app.engines.provider_portal.router import _validate_daily_job_capacity, _validate_designation
    from app.exceptions import ServiceOSException
    assert _validate_designation('technician', None) is None
    rule = {'start_time': '09:00', 'end_time': '18:00', 'max_jobs_per_day': 12}
    with patch('app.engines.vertical_catalog.seat_enforcement.get_seat_usage', AsyncMock(return_value={'entitled_seats': 3, 'used_seats': 3})):
        await _validate_daily_job_capacity(MagicMock(), uuid.uuid4(), rule)
        with pytest.raises(ServiceOSException):
            await _validate_daily_job_capacity(MagicMock(), uuid.uuid4(), {**rule, 'max_jobs_per_day': 13})


@pytest.mark.asyncio
async def test_technician_hours_follow_business_edits_without_copying():
    from app.engines.home_service_assignment import availability_resolver as resolver
    with patch.object(resolver, '_fetch_business_hours', AsyncMock(side_effect=[
        [{'start_time': '09:00', 'end_time': '18:00', 'max_jobs_per_day': 12}],
        [{'start_time': '10:00', 'end_time': '16:00', 'max_jobs_per_day': 9}],
    ])):
        before = await resolver._fetch_staff_pattern(MagicMock(), uuid.uuid4(), uuid.uuid4(), 1)
        after = await resolver._fetch_staff_pattern(MagicMock(), uuid.uuid4(), uuid.uuid4(), 1)
    assert (before['start_time'], before['end_time'], before['max_jobs_per_day']) == ('09:00', '18:00', 4)
    assert (after['start_time'], after['end_time'], after['max_jobs_per_day']) == ('10:00', '16:00', 3)
