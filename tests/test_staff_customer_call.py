"""Call customer, from the technician's own phone.

Tapping Call in the technician app asks POST .../customer-call for the number
the customer gave on the booking (the Instagram chat collects it), and the app
opens the phone dialer with it. Every tap is recorded with its time, so the
number is never handed out without a record, and the app shows when the
customer was last called.

Dialing does not prove the customer answered, so it must not tick off
"Call Customer & Confirm Requirements" -- the explicit confirmation still does.
"""
from __future__ import annotations

import json
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.main import app
from tests.test_technician_full_job_flow import (
    _cleanup, _override_get_db, _seed, make_technician_context,
)

PHONE = "+919812345678"
HEADERS = {"Authorization": "Bearer x"}


@pytest.fixture(autouse=True)
def _use_real_db():
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


async def _seed_job(db, *, phone: str | None = PHONE):
    ids = await _seed(db, inspection_required=False, quote_approval_required=False)
    await db.execute(text(
        "UPDATE service_bookings SET customer_phone=:phone WHERE id=:bid"
    ), {"phone": phone, "bid": ids["booking"]})
    await db.commit()
    return ids


def _act_as(ids, user_id=None):
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(
        str(ids["tenant"]), user_id=str(user_id or ids["staff"]))


async def _dial_events(db, job_id):
    return (await db.execute(text(
        "SELECT notes, metadata FROM service_job_execution_events "
        "WHERE job_id=:jid AND event_type='customer_call_dialed'"
    ), {"jid": job_id})).fetchall()


@pytest.mark.asyncio
async def test_each_call_tap_returns_the_booking_number_and_is_recorded_with_its_time():
    from app.database import get_session_factory, init_db

    await init_db()
    async with get_session_factory()() as db:
        ids = await _seed_job(db)
        job_id = ids["job"]
        _act_as(ids)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                accepted = await client.post(f"/v1/staff/service-jobs/{job_id}/accept", headers=HEADERS)
                assert accepted.status_code == 200, accepted.text

                first = await client.post(f"/v1/staff/service-jobs/{job_id}/customer-call", headers=HEADERS)
                assert first.status_code == 200, first.text
                second = await client.post(f"/v1/staff/service-jobs/{job_id}/customer-call", headers=HEADERS)
                assert second.status_code == 200, second.text
                first, second = first.json()["data"], second.json()["data"]

                assert first["customer_phone"] == PHONE
                assert first["call_count"] == 1 and second["call_count"] == 2
                assert second["recent_call_times"] == [second["called_at"], first["called_at"]]

                detail = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=HEADERS)).json()["data"]
                customer = detail["customer"]
                assert customer["phone_call_available"] is True
                assert customer["phone_call_reason"] is None
                assert customer["call_count"] == 2
                assert customer["last_called_at"] == second["called_at"]
                # The number is released only by the recorded tap.
                assert PHONE not in json.dumps(detail)
                assert PHONE[-10:] not in json.dumps(detail)

                # Dialing is not proof of a conversation.
                assert detail["next_required_action"]["key"] == "call-customer"

                timeline = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-timeline", headers=HEADERS)).json()["data"]
                assert [e["event_type"] for e in timeline["entries"]].count("customer_call_dialed") == 2

            events = await _dial_events(db, job_id)
            assert len(events) == 2
            assert PHONE[-10:] not in json.dumps([[e.notes, e.metadata] for e in events])
        finally:
            await _cleanup(db, ids)


@pytest.mark.asyncio
async def test_a_technician_not_on_the_job_gets_no_number_and_no_record():
    from app.database import get_session_factory, init_db

    await init_db()
    async with get_session_factory()() as db:
        ids = await _seed_job(db)
        _act_as(ids, user_id=uuid.uuid4())
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    f"/v1/staff/service-jobs/{ids['job']}/customer-call", headers=HEADERS)
            assert response.status_code == 403, response.text
            assert PHONE[-10:] not in response.text
            assert await _dial_events(db, ids["job"]) == []
        finally:
            await _cleanup(db, ids)


@pytest.mark.asyncio
async def test_completed_job_contact_remains_available_until_warranty_expiry():
    from app.database import get_session_factory, init_db

    await init_db()
    async with get_session_factory()() as db:
        ids = await _seed_job(db)
        job_id = ids["job"]
        _act_as(ids)
        try:
            await db.execute(text(
                "UPDATE service_jobs SET status='completed', "
                "warranty_expires_at=now() + interval '1 day' WHERE id=:jid"
            ), {"jid": job_id})
            await db.commit()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                detail = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=HEADERS
                )).json()["data"]
                assert detail["customer"]["phone_call_available"] is True

                response = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/customer-call", headers=HEADERS
                )
                assert response.status_code == 200, response.text
                assert response.json()["data"]["customer_phone"] == PHONE
        finally:
            await _cleanup(db, ids)


@pytest.mark.asyncio
async def test_missing_number_and_closed_job_refuse_without_recording_a_tap():
    from app.database import get_session_factory, init_db

    await init_db()
    async with get_session_factory()() as db:
        ids = await _seed_job(db, phone=None)
        job_id = ids["job"]
        _act_as(ids)
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                no_number = await client.post(f"/v1/staff/service-jobs/{job_id}/customer-call", headers=HEADERS)
                assert no_number.status_code == 422, no_number.text
                assert no_number.json()["error_code"] == "MASKED_CALLING_NO_CUSTOMER_NUMBER"
                customer = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=HEADERS)).json()["data"]["customer"]
                assert customer["phone_call_available"] is False
                assert customer["phone_call_reason"] == "MASKED_CALLING_NO_CUSTOMER_NUMBER"
                assert customer["last_called_at"] is None

                await db.execute(text(
                    "UPDATE service_bookings SET customer_phone=:phone WHERE id=:bid"
                ), {"phone": PHONE, "bid": ids["booking"]})
                await db.execute(text(
                    "UPDATE service_jobs SET status='completed', "
                    "warranty_expires_at=now() - interval '1 minute' WHERE id=:jid"
                ), {"jid": job_id})
                await db.commit()
                closed = await client.post(f"/v1/staff/service-jobs/{job_id}/customer-call", headers=HEADERS)
                assert closed.status_code == 409, closed.text
                assert closed.json()["error_code"] == "MASKED_CALLING_JOB_NOT_CALLABLE"
                assert PHONE[-10:] not in closed.text

                customer = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=HEADERS
                )).json()["data"]["customer"]
                assert customer["phone_call_available"] is False
                assert customer["phone_call_reason"] == "MASKED_CALLING_JOB_NOT_CALLABLE"

            assert await _dial_events(db, job_id) == []
        finally:
            await _cleanup(db, ids)
