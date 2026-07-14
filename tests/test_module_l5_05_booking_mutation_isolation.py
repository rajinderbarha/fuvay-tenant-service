"""MODULE-L5-05 — booking MUTATION cross-tenant isolation.

request/accept/reject_reschedule, add_note, and void_booking previously loaded a
booking by id and mutated it with NO tenant/customer scope check (a tenant_owner
could mutate another tenant's booking; add_note was auth-only so ANY user could).
All now route through _assert_can_access_booking. Also enforced by
e2e/cross_tenant_isolation_guard.py's booking-mutation-coverage check.
"""
import uuid
from unittest.mock import MagicMock

import pytest

from app.engines.booking.service import BookingService
from app.exceptions import NotFoundException
import e2e.cross_tenant_isolation_guard as guard


def _staff_at(tenant_id):
    svc = BookingService(db=MagicMock(), actor_id=uuid.uuid4(), actor_role="staff",
                         actor_tenant_id=tenant_id)
    return svc


def test_add_note_blocks_cross_tenant():
    """add_note (endpoint is auth-only) must still confine to the booking's tenant."""
    svc = _staff_at(uuid.uuid4())
    b = MagicMock(id=uuid.uuid4(), customer_id=uuid.uuid4(), tenant_id=uuid.uuid4())  # different tenant
    with pytest.raises(NotFoundException):
        svc._assert_can_access_booking(b)


def test_add_note_allows_own_tenant():
    tid = uuid.uuid4()
    svc = _staff_at(tid)
    b = MagicMock(id=uuid.uuid4(), customer_id=uuid.uuid4(), tenant_id=tid)
    svc._assert_can_access_booking(b)  # no raise


def test_tenant_owner_cannot_mutate_other_tenant_booking():
    a, b_tenant = uuid.uuid4(), uuid.uuid4()
    svc = BookingService(db=MagicMock(), actor_id=uuid.uuid4(), actor_role="tenant_owner",
                         actor_tenant_id=a)
    booking = MagicMock(id=uuid.uuid4(), customer_id=uuid.uuid4(), tenant_id=b_tenant)
    with pytest.raises(NotFoundException):
        svc._assert_can_access_booking(booking)


def test_guard_enforces_booking_mutation_coverage():
    assert guard.check() == []


def test_staff_me_jobs_does_not_require_tenant_id_query():
    """MODULE-L5-02 bug #14: /v1/staff/me/jobs is a staff/technician *self*
    endpoint — its tenant is derived from the JWT inside list_jobs, which always
    overrides the passed tenant_id with actor_tenant_id for staff/technician.
    The router previously declared tenant_id as a REQUIRED query param, so every
    call from the staff app returned 422 (and, worse, invited the client to
    supply its own tenant_id on a /me/ endpoint). The param must be optional."""
    import inspect
    from app.engines.field_ops import staff_router
    sig = inspect.signature(staff_router.my_jobs)
    default = sig.parameters["tenant_id"].default
    # FastAPI Query(...) marker for a required param exposes default is Ellipsis;
    # an optional Query(None) exposes default None.
    assert getattr(default, "default", default) is None, (
        "tenant_id must be optional on the staff self /me/jobs endpoint")


def test_staff_id_resolvers_fall_back_to_user_id_not_empty_team_table():
    """MODULE-L5-02 bug #15: the service layer keys staff off users.id
    (service_jobs.assigned_staff_id = users.id) because provider_team_members is
    unpopulated, but both staff-facing routers translated the login through that
    empty table — so a real technician got an empty job list, a 500 on accept,
    and 403s on every execution transition. The resolvers must fall back to the
    raw auth user id instead of raising when no team-member row exists."""
    import inspect
    from app.engines.home_service_assignment import staff_router as asn
    from app.engines.execution import home_service_router as ex
    for fn in (asn._resolve_staff_member_id, ex._staff_member_id):
        src = inspect.getsource(fn)
        assert "user.user_id" in src and "return uuid.UUID(str(user.user_id))" in src, \
            f"{fn.__qualname__} must fall back to the auth user id"
        # must NOT raise/deny on the missing-team-member path anymore
        assert "raise ValueError(ERR_JOB_NOT_FOUND)" not in src
        assert 'raise ServiceOSException("STAFF_MEMBER_NOT_FOUND"' not in src
