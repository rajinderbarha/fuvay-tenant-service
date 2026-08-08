"""Masked calling — number privacy and off-platform leakage prevention.

The invariant every test here defends: NO code path returns a real phone
number to either party, in any state. A number handed over once becomes a
permanent private channel and the next job goes off-platform, which is the
whole thing this engine exists to prevent.

Exercised against real live Guramrit data (no mocks) except for the telephony
provider itself, which is faked -- placing real phone calls in a test suite
would be both expensive and wrong.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text as sa_text

from app.engines.masked_calling import constants as c
from app.engines.masked_calling import provider as provider_module
from app.engines.masked_calling import service as svc
from app.engines.masked_calling.provider import BridgeResult, NullTelephonyProvider
from app.exceptions import ServiceOSException

GURAMRIT_TENANT_ID = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    return get_session_factory()()


class FakeProvider:
    """Stands in for a telephony vendor. Records what it was asked to dial so a
    test can prove the real numbers went to the provider and nowhere else."""

    name = "fake"

    def __init__(self, *, accept: bool = True, call_id: str | None = "fake-call-1"):
        self._accept = accept
        self._call_id = call_id
        self.calls: list[dict] = []

    @property
    def configured(self) -> bool:
        return True

    async def bridge(self, *, from_number, to_number, caller_id, reference):
        self.calls.append({
            "from": from_number, "to": to_number,
            "caller_id": caller_id, "reference": reference,
        })
        if not self._accept:
            return BridgeResult(None, False, "vendor_rejected")
        return BridgeResult(self._call_id, True, None)


async def _a_live_job(db):
    """A real, non-terminal job for this tenant, with its booking."""
    row = (await db.execute(sa_text(
        "SELECT id, booking_id, customer_id, status FROM service_jobs "
        "WHERE tenant_id=:t AND status NOT IN "
        "('completed','cancelled','failed','closed_estimate_declined') "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"t": str(GURAMRIT_TENANT_ID)})).fetchone()
    return row._mapping if row else None


# ── The core invariant ────────────────────────────────────────────────────

def test_the_session_row_never_persists_either_real_number():
    """Storing a number here would create a second surface a leak could come
    from, for no functional gain."""
    from app.engines.masked_calling.models import MaskedCallSession
    columns = set(MaskedCallSession.__table__.columns.keys())
    for forbidden in ("customer_phone", "staff_phone", "from_number", "to_number",
                      "customer_number", "phone", "phone_number"):
        assert forbidden not in columns, f"{forbidden} must not be stored on a call session"
    # The platform's own caller id IS safe to keep -- both sides see it anyway.
    assert "caller_id_used" in columns


@pytest.mark.asyncio
async def test_contact_payload_carries_no_phone_number_and_says_so():
    db = await _get_db()
    try:
        job = await _a_live_job(db)
        if not job:
            pytest.skip("no live job for this tenant to describe")
        data = await svc.describe_contact(db, job["id"], GURAMRIT_TENANT_ID)

        assert data["phone_number_visible"] is False
        assert data["customer_display"].startswith("Customer")
        # Nothing anywhere in the payload may look like a phone number.
        flat = repr(data)
        real = (await db.execute(sa_text(
            "SELECT customer_phone FROM service_bookings WHERE id=:b"
        ), {"b": str(job["booking_id"])})).scalar() if job["booking_id"] else None
        if real:
            assert str(real) not in flat, "the real customer number leaked into the contact payload"
    finally:
        await db.close()


# ── Not-configured must refuse, never fall back ───────────────────────────

def test_no_configured_vendor_resolves_to_the_refusing_provider():
    from app.config import get_settings
    settings = get_settings()
    original = settings.MASKED_CALLING_PROVIDER
    try:
        settings.MASKED_CALLING_PROVIDER = ""
        assert isinstance(provider_module.get_provider(), NullTelephonyProvider)
    finally:
        settings.MASKED_CALLING_PROVIDER = original


@pytest.mark.asyncio
async def test_the_null_provider_refuses_rather_than_returning_a_number():
    result = await NullTelephonyProvider().bridge(
        from_number="+911111111111", to_number="+912222222222",
        caller_id="+913333333333", reference="ref",
    )
    assert result.accepted is False
    assert result.provider_call_id is None
    assert result.failure_reason == c.ERR_CALLING_NOT_CONFIGURED


@pytest.mark.asyncio
async def test_placing_a_call_with_no_vendor_configured_raises_and_leaks_nothing():
    db = await _get_db()
    try:
        job = await _a_live_job(db)
        if not job:
            pytest.skip("no live job for this tenant")
        provider_module_get = provider_module.get_provider
        svc_get = svc.get_provider
        try:
            svc.get_provider = lambda: NullTelephonyProvider()
            with pytest.raises(ServiceOSException) as exc:
                await svc.place_call(
                    db, job_id=job["id"], tenant_id=GURAMRIT_TENANT_ID,
                    initiator_user_id=uuid.uuid4(),
                )
            assert exc.value.error_code == c.ERR_CALLING_NOT_CONFIGURED
        finally:
            svc.get_provider = svc_get
            provider_module.get_provider = provider_module_get
    finally:
        await db.rollback()
        await db.close()


# ── Webhook authenticity ──────────────────────────────────────────────────

def test_webhook_fails_closed_when_no_secret_is_configured():
    """An open status endpoint would let anyone forge a 'connected' call and tick
    off the technician's obligation to actually speak to the customer."""
    from app.config import get_settings
    settings = get_settings()
    original = settings.MASKED_CALLING_WEBHOOK_SECRET
    try:
        settings.MASKED_CALLING_WEBHOOK_SECRET = ""
        with pytest.raises(ServiceOSException) as exc:
            svc.assert_webhook_authorized("anything")
        assert exc.value.error_code == c.ERR_WEBHOOK_UNAUTHORIZED
        # ...and an empty supplied secret is refused too.
        settings.MASKED_CALLING_WEBHOOK_SECRET = "s3cret"
        with pytest.raises(ServiceOSException):
            svc.assert_webhook_authorized(None)
        with pytest.raises(ServiceOSException):
            svc.assert_webhook_authorized("wrong")
        svc.assert_webhook_authorized("s3cret")   # correct secret passes
    finally:
        settings.MASKED_CALLING_WEBHOOK_SECRET = original


# ── Only a real conversation counts ───────────────────────────────────────

def test_only_connected_statuses_count_as_having_reached_the_customer():
    """A ring-out or busy tone must not satisfy "call the customer first"."""
    assert c.STATUS_CONNECTED in c.CONNECTED_STATUSES
    assert c.STATUS_COMPLETED in c.CONNECTED_STATUSES
    for not_a_conversation in (c.STATUS_NO_ANSWER, c.STATUS_BUSY,
                               c.STATUS_FAILED, c.STATUS_RINGING,
                               c.STATUS_REQUESTED, c.STATUS_EXPIRED):
        assert not_a_conversation not in c.CONNECTED_STATUSES


def test_vendor_statuses_map_onto_our_vocabulary_and_unknowns_are_ignored():
    assert svc.normalize_provider_status("in-progress") == c.STATUS_CONNECTED
    assert svc.normalize_provider_status("ANSWERED") == c.STATUS_CONNECTED
    assert svc.normalize_provider_status("completed") == c.STATUS_COMPLETED
    assert svc.normalize_provider_status("no-answer") == c.STATUS_NO_ANSWER
    assert svc.normalize_provider_status("busy") == c.STATUS_BUSY
    # An unrecognised vendor status must not be guessed into a state change.
    assert svc.normalize_provider_status("something-new") is None
    assert svc.normalize_provider_status(None) is None


# ── Real bridge: numbers go to the vendor and nowhere else ────────────────

@pytest.mark.asyncio
async def test_a_bridged_call_sends_both_numbers_to_the_vendor_but_stores_neither():
    db = await _get_db()
    fake = FakeProvider()
    created_session_id = None
    try:
        job = await _a_live_job(db)
        if not job:
            pytest.skip("no live job for this tenant")
        booking_phone = (await db.execute(sa_text(
            "SELECT customer_phone FROM service_bookings WHERE id=:b"
        ), {"b": str(job["booking_id"])})).scalar() if job["booking_id"] else None
        if not booking_phone:
            pytest.skip("this job's booking has no customer number to dial")

        staff_user = (await db.execute(sa_text(
            "SELECT id FROM users WHERE phone IS NOT NULL LIMIT 1"))).scalar()
        if not staff_user:
            pytest.skip("no user with a phone number to act as the technician")

        from app.config import get_settings
        settings = get_settings()
        original_caller = settings.MASKED_CALLING_CALLER_ID
        svc_get = svc.get_provider
        try:
            settings.MASKED_CALLING_CALLER_ID = "+911140001000"
            svc.get_provider = lambda: fake
            session = await svc.place_call(
                db, job_id=job["id"], tenant_id=GURAMRIT_TENANT_ID,
                initiator_user_id=staff_user,
            )
            created_session_id = session.id

            assert len(fake.calls) == 1, "exactly one bridge request"
            sent = fake.calls[0]
            assert sent["to"] == str(booking_phone), "the customer's real number goes to the vendor"
            assert sent["caller_id"] == "+911140001000"
            assert sent["reference"] == str(session.id), "our own id is the webhook reference"

            assert session.status == c.STATUS_RINGING
            assert session.expires_at is not None, "a binding must be time-bound, not standing"

            # The row itself, and its API projection, contain no number.
            payload = repr(session.to_dict())
            assert str(booking_phone) not in payload
            assert sent["from"] not in payload
        finally:
            settings.MASKED_CALLING_CALLER_ID = original_caller
            svc.get_provider = svc_get
    finally:
        await db.rollback()
        if created_session_id:
            await db.execute(sa_text("DELETE FROM masked_call_sessions WHERE id=:i"),
                             {"i": str(created_session_id)})
            await db.commit()
        await db.close()


@pytest.mark.asyncio
async def test_a_closed_job_cannot_get_a_fresh_call_binding():
    db = await _get_db()
    try:
        # Any tenant's closed job proves the rule -- scoped to that job's own
        # tenant so this does not depend on one fixture tenant having one.
        row = (await db.execute(sa_text(
            "SELECT id, tenant_id FROM service_jobs "
            "WHERE status = ANY(:st) AND tenant_id IS NOT NULL LIMIT 1"
        ), {"st": list(c.NON_CALLABLE_JOB_STATUSES)})).fetchone()
        if not row:
            pytest.skip("no closed job anywhere to test the guard against")
        svc_get = svc.get_provider
        try:
            svc.get_provider = lambda: FakeProvider()
            with pytest.raises(ServiceOSException) as exc:
                await svc.place_call(
                    db, job_id=row._mapping["id"], tenant_id=row._mapping["tenant_id"],
                    initiator_user_id=uuid.uuid4(),
                )
            assert exc.value.error_code == c.ERR_JOB_NOT_CALLABLE
        finally:
            svc.get_provider = svc_get
    finally:
        await db.rollback()
        await db.close()


@pytest.mark.asyncio
async def test_a_forged_callback_cannot_target_a_job_it_does_not_own():
    """Sessions are matched on OUR reference (or the vendor's call id), never on
    a job id from the payload."""
    db = await _get_db()
    try:
        result = await svc.apply_provider_status(
            db, provider_call_id="does-not-exist",
            session_reference=str(uuid.uuid4()),
            raw_status="completed",
        )
        assert result is None, "an unmatched callback must change nothing"
    finally:
        await db.rollback()
        await db.close()


def test_dashboard_no_longer_returns_the_customers_raw_number():
    """Regression guard for the leak this engine closes: the provider dashboard's
    job detail used to return `customer_phone` straight from the users table."""
    import inspect
    from app.engines.execution import home_services_dashboard_service as mod
    src = inspect.getsource(mod)
    assert '"customer_phone": row.customer_phone' not in src
    assert '"customer_phone": None' in src
    assert "platform_masked_call" in src
