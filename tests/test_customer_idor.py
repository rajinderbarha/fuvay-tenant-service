"""
Phase 4 readiness fix: booking + review engines let any authenticated
customer read/spoof ANOTHER customer's data by ID (no ownership check).
This verifies the fix: customers are scoped to their own customer_id,
tenant staff/owner/admin access is untouched, and creation can no longer
be spoofed via the request body.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import NotFoundException


def make_db_returning(obj):
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    return db


# ── Booking ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_cannot_get_another_customers_booking():
    from app.engines.booking.service import BookingService
    owner_id = uuid.uuid4()
    other_customer_id = uuid.uuid4()
    fake_booking = MagicMock(id=uuid.uuid4(), customer_id=owner_id)
    db = make_db_returning(fake_booking)
    svc = BookingService(db=db, actor_id=other_customer_id, actor_role="customer")

    with pytest.raises(NotFoundException):
        await svc.get_booking(fake_booking.id)


@pytest.mark.asyncio
async def test_customer_can_get_own_booking():
    from app.engines.booking.service import BookingService
    owner_id = uuid.uuid4()
    fake_booking = MagicMock(id=uuid.uuid4(), customer_id=owner_id, tenant_id=uuid.uuid4(),
                              status="confirmed", booking_number="BK-1")
    db = make_db_returning(fake_booking)
    svc = BookingService(db=db, actor_id=owner_id, actor_role="customer")
    svc._booking_dict = lambda b: {"booking_id": str(b.id), "customer_id": str(b.customer_id)}

    result = await svc.get_booking(fake_booking.id)
    assert result["customer_id"] == str(owner_id)


@pytest.mark.asyncio
async def test_staff_can_view_booking_in_their_tenant():
    """MODULE-L5-04: staff may view a booking IN THEIR OWN TENANT (tenant_id
    match), and only that. (The prior version of this test created a staff with
    NO actor_tenant_id and asserted it could view ANY booking — encoding the
    cross-tenant IDOR that MODULE-L5-04 fixed. Corrected to the secure behavior.)"""
    from app.engines.booking.service import BookingService
    tid = uuid.uuid4()
    fake_booking = MagicMock(id=uuid.uuid4(), customer_id=uuid.uuid4(), tenant_id=tid)
    db = make_db_returning(fake_booking)
    svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="staff", actor_tenant_id=tid)
    svc._booking_dict = lambda b: {"booking_id": str(b.id)}

    result = await svc.get_booking(fake_booking.id)
    assert result["booking_id"] == str(fake_booking.id)


@pytest.mark.asyncio
async def test_staff_cannot_view_booking_in_another_tenant():
    """MODULE-L5-04 regression: staff holds booking:bookings:read but must NOT be
    able to read a booking belonging to a different tenant."""
    from app.engines.booking.service import BookingService
    fake_booking = MagicMock(id=uuid.uuid4(), customer_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    db = make_db_returning(fake_booking)
    svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="staff", actor_tenant_id=uuid.uuid4())
    with pytest.raises(NotFoundException):
        await svc.get_booking(fake_booking.id)


@pytest.mark.asyncio
async def test_customer_cannot_list_another_customers_bookings():
    from app.engines.booking.service import BookingService
    db = MagicMock()
    svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="customer")

    with pytest.raises(NotFoundException):
        await svc.list_by_customer(uuid.uuid4(), None, 50, None)


@pytest.mark.asyncio
async def test_create_booking_router_ignores_spoofed_customer_id():
    """A customer POSTing someone else's customer_id in the body gets overridden
    with their own token's user_id — they cannot book on another customer's behalf."""
    import app.engines.booking.router as booking_router
    from app.dependencies.auth import UserContext

    own_id = str(uuid.uuid4())
    other_id = str(uuid.uuid4())
    # Do NOT include tenant_id — the router correctly rejects it with FRONTEND_TENANT_ID_NOT_ALLOWED.
    # This test verifies that customer_id from the body is ignored; JWT customer is used instead.
    spoofed_body = {"customer_id": other_id, "service_type_id": "ac_repair"}

    captured = {}
    async def fake_create_booking(**kwargs):
        captured.update(kwargs)
        return {"booking_id": str(uuid.uuid4())}

    class FakeState:
        request_id = "req_test"

    class FakeRequest:
        state = FakeState()
        async def json(self): return spoofed_body

    fake_svc = MagicMock()
    fake_svc.create_booking = fake_create_booking
    user = UserContext(user_id=own_id, email="c@x.io", role="customer", tenant_id=None,
                        full_name="Cust", is_verified=True)

    await booking_router.create_booking(FakeRequest(), u=user, s=fake_svc)
    assert str(captured["customer_id"]) == own_id
    assert str(captured["customer_id"]) != other_id


# ── Review ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_customer_cannot_get_another_customers_review():
    from app.engines.review.service import ReviewService
    owner_id = uuid.uuid4()
    fake_review = MagicMock(id=uuid.uuid4(), customer_id=owner_id)
    db = make_db_returning(fake_review)
    svc = ReviewService(db=db, actor_id=uuid.uuid4(), actor_role="customer")

    with pytest.raises(NotFoundException):
        await svc.get_review(fake_review.id)


@pytest.mark.asyncio
async def test_legacy_review_create_endpoint_is_blocked():
    """Phase 2A Slice 2: POST /v1/reviews (legacy review engine) is now a
    hard 410 — customer_reviews is the sole canonical write path (see
    docs/workflow-rearchitecture/phase-01a/review-canonical-decision.md).
    This supersedes the old spoofed-customer-id IDOR test above: since the
    endpoint no longer creates anything at all, the spoofing concern this
    test used to guard against no longer applies — there is nothing left to
    spoof into."""
    import app.engines.review.router as review_router
    from app.dependencies.auth import UserContext
    from fastapi import HTTPException

    class FakeState:
        request_id = "req_test"

    class FakeRequest:
        state = FakeState()
        async def json(self): return {}

    user = UserContext(user_id=str(uuid.uuid4()), email="c@x.io", role="customer",
                        tenant_id=None, full_name="Cust", is_verified=True)

    with pytest.raises(HTTPException) as exc_info:
        await review_router.create_review(FakeRequest(), u=user)
    assert exc_info.value.status_code == 410
