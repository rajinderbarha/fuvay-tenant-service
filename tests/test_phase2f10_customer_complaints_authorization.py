"""Phase 2A Slice 2F-10 — complaints.customer_router authorization,
ownership, state-integrity and IDOR closure.

Runtime introspection confirmed 15 mounted routes (8 mutation + 7 read),
ALL of which previously used `get_current_user` only -- no role check of
any kind -- meaning a tenant_owner, staff member, technician, or another
customer could call every customer complaint endpoint. Ownership was
partially, but not completely, enforced at the service layer:

1. **Router-level role gap (fixed)**: all 15 routes now require
   `Depends(require_customer)` -- the pre-existing, already-used-elsewhere
   canonical customer-role dependency (`app/dependencies/auth.py`) --
   instead of `get_current_user`. Reuses existing infrastructure, grants
   nothing new.

2. **`create_complaint` had ZERO record-ownership check (fixed)**: any
   customer (or, pre-fix, any authenticated user) could file a complaint
   against ANY booking/job/invoice/appointment/lead/review by ID, for any
   other customer's record. Fixed by wiring in
   `ComplaintEligibilityService._fetch_record`/`_customer_owns_record`
   (already correct, already used by the separate advisory
   `check-eligible` endpoint, but never connected to actual creation).

3. **`create_refund_request_from_complaint` had ZERO complaint-ownership
   check (fixed)**: unlike every other customer_router route, this one
   called a bare `get_complaint` (fetch-by-id, no owner check) instead of
   `get_customer_complaint`. Any authenticated user could create a refund
   request against any complaint_id for any customer/tenant. Fixed to use
   `get_customer_complaint` when `actor_type == ACTOR_CUSTOMER`.

4. **`_get_resolution` had no complaint cross-check (fixed)**: mirrors the
   identical Slice 2F-9 `_get_settlement_proposal` bypass -- a customer
   who had proven ownership of complaint A could still accept/reject a
   `resolution_id` belonging to complaint B (any other customer/tenant).
   Fixed with the same pattern: optional `complaint_id` cross-check,
   fails the same way a genuinely missing resolution would (no existence
   leakage).

5. **Ordering defect (fixed)**: `customer_accept_resolution`/
   `customer_reject_resolution` mutated `resolution.status` (and, for a
   rework resolution, created AND COMMITTED a real `ServiceReworkRequest`)
   *before* validating the complaint's state-transition legality.
   Reordered to pre-validate via `ALLOWED_TRANSITIONS_EXT` before any
   mutation or side effect.

Settlement proposal cross-checking (`_get_settlement_proposal`) was
**already fixed** by Slice 2F-9 as a shared service-layer method used by
both provider and customer paths -- re-verified here, not re-fixed.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext


def _user(role: str, user_id: str | None = None, tenant_id: str | None = None) -> UserContext:
    return UserContext(
        user_id=user_id or str(uuid.uuid4()), email=f"{role}@test.local", role=role,
        tenant_id=tenant_id or str(uuid.uuid4()), full_name=role.title(), is_verified=True,
    )


def _override(u):
    app.dependency_overrides[get_current_user] = lambda: u


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


COMPLAINT_ID  = "11111111-1111-1111-1111-111111111111"
RESOLUTION_ID = "22222222-2222-2222-2222-222222222222"
PROPOSAL_ID   = "33333333-3333-3333-3333-333333333333"

MUTATION_ROUTES = [
    ("POST", "/v1/customer/complaints",
     {"record_type": "service_booking", "record_id": str(uuid.uuid4()),
      "complaint_type": "service_quality", "description": "not done"}),
    ("POST", f"/v1/customer/complaints/{COMPLAINT_ID}/messages", {"message_text": "hello"}),
    ("POST", f"/v1/customer/complaints/{COMPLAINT_ID}/ai-session/answers", {"answers": ["a"]}),
    ("POST", f"/v1/customer/complaints/{COMPLAINT_ID}/cancel", {"reason": "changed my mind"}),
    ("POST", f"/v1/customer/complaints/{COMPLAINT_ID}/resolutions/{RESOLUTION_ID}/accept", None),
    ("POST", f"/v1/customer/complaints/{COMPLAINT_ID}/resolutions/{RESOLUTION_ID}/reject", {"reason": "no"}),
    ("POST", f"/v1/customer/complaints/{COMPLAINT_ID}/refund",
     {"refund_type": "partial", "reason": "overcharged"}),
    ("POST", f"/v1/customer/complaints/{COMPLAINT_ID}/settlement-proposals/{PROPOSAL_ID}/respond",
     {"response": "accept"}),
]

READ_ROUTES = [
    ("GET", f"/v1/customer/complaints/check-eligible?record_type=service_booking&record_id={uuid.uuid4()}"),
    ("GET", "/v1/customer/complaints"),
    ("GET", f"/v1/customer/complaints/{COMPLAINT_ID}"),
    ("GET", f"/v1/customer/complaints/{COMPLAINT_ID}/messages"),
    ("GET", f"/v1/customer/complaints/{COMPLAINT_ID}/resolutions"),
    ("GET", f"/v1/customer/complaints/{COMPLAINT_ID}/ai-session"),
    ("GET", f"/v1/customer/complaints/{COMPLAINT_ID}/settlement-proposals"),
]

DENIED_ROLES = ["tenant_owner", "staff", "technician", "guest", "totally_bogus_role"]


@pytest.mark.asyncio
class TestCustomerRoleGate:
    """Workstream 5/18: every route must require the canonical `customer`
    role; every non-customer role must be denied before reaching any
    business logic."""

    async def test_unauthenticated_denied_on_every_mutation_route(self):
        _clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for method, path, body in MUTATION_ROUTES:
                resp = await client.request(method, path, json=body)
                assert resp.status_code in (401, 403), f"{method} {path} -> {resp.status_code}"

    @pytest.mark.parametrize("role", DENIED_ROLES)
    async def test_non_customer_role_denied_on_every_mutation_route(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path, body in MUTATION_ROUTES:
                    resp = await client.request(method, path, json=body)
                    assert resp.status_code == 403, f"{role} {method} {path} -> {resp.status_code}"
        finally:
            _clear()

    @pytest.mark.parametrize("role", DENIED_ROLES)
    async def test_non_customer_role_denied_on_every_read_route(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path in READ_ROUTES:
                    resp = await client.request(method, path)
                    assert resp.status_code == 403, f"{role} {method} {path} -> {resp.status_code}"
        finally:
            _clear()

    async def test_super_admin_not_wildcarded_through_customer_route(self):
        """Platform admins must use the separate admin router, not the
        customer route, even though require_customer's own semantics
        (unlike require_tenant_owner) grant no super_admin override at
        all -- confirmed directly, not assumed."""
        _override(_user("super_admin"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/v1/customer/complaints/{COMPLAINT_ID}")
                assert resp.status_code == 403
        finally:
            _clear()

    async def test_correct_customer_clears_role_gate(self):
        """A genuine customer clears the router-level role check (may
        still 404/deny at the ownership layer for a nonexistent complaint
        ID -- this test only proves the role gate itself passes)."""
        _override(_user("customer"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/v1/customer/complaints/{COMPLAINT_ID}")
                # Role gate cleared -- ownership denial (COMPLAINT_ACCESS_DENIED)
                # is a different, expected 403 for a nonexistent complaint;
                # the role gate's own error_code (PERMISSION_DENIED) must not
                # be the one returned.
                body = resp.json()
                error_code = (body.get("error") or {}).get("code") or body.get("error_code")
                assert error_code != "PERMISSION_DENIED", body
        finally:
            _clear()


# ── Service-layer ownership / IDOR tests ──────────────────────────────────────
from app.engines.complaints.complaint_service import ComplaintService
from app.engines.complaints.refund_service import RefundRequestService
from app.engines.complaints.constants import (
    STATUS_OPEN, STATUS_AWAITING_PROVIDER, STATUS_RESOLVED, STATUS_REWORK_APPROVED,
    STATUS_UNDER_ADMIN_REVIEW, STATUS_CLOSED, RECORD_SERVICE_BOOKING,
    ACTOR_CUSTOMER, ERR_COMPLAINT_ACCESS_DENIED, ERR_COMPLAINT_RECORD_NOT_FOUND,
    ERR_RESOLUTION_NOT_FOUND, ERR_COMPLAINT_INVALID_TRANSITION,
)


def _mock_db():
    # A session is an object with async methods, not an awaitable itself.
    # Using AsyncMock for the whole session manufactures coroutine-valued
    # attributes during MagicMock introspection and can emit false unawaited
    # coroutine warnings even when the production await contract is correct.
    db = MagicMock()
    db.execute = AsyncMock()
    db.scalar  = AsyncMock(return_value=None)
    db.get     = AsyncMock(return_value=None)
    db.flush  = AsyncMock()
    db.commit = AsyncMock()
    db.add    = MagicMock()
    return db


@pytest.mark.asyncio
class TestComplaintCreationOwnership:
    async def test_create_complaint_rejects_unowned_record(self):
        """Slice 2F-10A: create_complaint now delegates the whole
        eligibility contract (ownership included) to check_eligible."""
        svc = ComplaintService()
        db = _mock_db()
        svc._eligibility.check_eligible = AsyncMock(return_value={
            "eligible": False, "reason": "Not the customer for this record.",
            "reason_code": ERR_COMPLAINT_ACCESS_DENIED,
        })
        with pytest.raises(ValueError, match=ERR_COMPLAINT_ACCESS_DENIED):
            await svc.create_complaint(
                db, uuid.uuid4(), category_id=uuid.uuid4(),
                record_type=RECORD_SERVICE_BOOKING, record_id=uuid.uuid4(),
                complaint_type="service_quality", description="x",
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()

    async def test_create_complaint_rejects_missing_record(self):
        svc = ComplaintService()
        db = _mock_db()
        svc._eligibility._fetch_record = AsyncMock(return_value=None)
        with pytest.raises(ValueError, match=ERR_COMPLAINT_RECORD_NOT_FOUND):
            await svc.create_complaint(
                db, uuid.uuid4(), category_id=uuid.uuid4(),
                record_type=RECORD_SERVICE_BOOKING, record_id=uuid.uuid4(),
                complaint_type="service_quality", description="x",
            )
        db.add.assert_not_called()

    async def test_create_complaint_allowed_for_owned_record(self):
        svc = ComplaintService()
        db = _mock_db()
        cid = uuid.uuid4()
        svc._eligibility.check_eligible = AsyncMock(return_value={
            "eligible": True, "reason": None, "reason_code": None, "policy": None,
        })
        svc._log_event = AsyncMock()
        svc._link_service_job = AsyncMock()
        with patch(
            "app.engines.complaints.notifications.notify_provider_complaint",
            new_callable=AsyncMock,
        ):
            c = await svc.create_complaint(
                db, cid, category_id=uuid.uuid4(),
                record_type=RECORD_SERVICE_BOOKING, record_id=uuid.uuid4(),
                complaint_type="service_quality", description="x",
            )
        assert str(c.customer_id) == str(cid)
        db.add.assert_called_once()
        db.commit.assert_awaited_once()


@pytest.mark.asyncio
class TestRefundRequestOwnership:
    async def test_customer_cannot_request_refund_on_foreign_complaint(self):
        svc = RefundRequestService()
        db = _mock_db()
        other_customer = uuid.uuid4()
        foreign_complaint = MagicMock(customer_id=other_customer, tenant_id=uuid.uuid4())
        svc._complaint_svc.get_customer_complaint = AsyncMock(
            side_effect=ValueError(ERR_COMPLAINT_ACCESS_DENIED))
        with pytest.raises(ValueError, match=ERR_COMPLAINT_ACCESS_DENIED):
            await svc.create_refund_request_from_complaint(
                db, uuid.uuid4(), uuid.uuid4(), ACTOR_CUSTOMER, "partial", "reason",
            )
        db.add.assert_not_called()

    async def test_customer_refund_allowed_for_own_complaint(self):
        svc = RefundRequestService()
        db = _mock_db()
        cid = uuid.uuid4()
        own_complaint = MagicMock(customer_id=cid, tenant_id=uuid.uuid4(), status=STATUS_OPEN,
                                   invoice_id=None, booking_id=None, job_id=None,
                                   appointment_id=None, lead_id=None)
        svc._complaint_svc.get_customer_complaint = AsyncMock(return_value=own_complaint)
        svc._log_event = AsyncMock()
        refund = await svc.create_refund_request_from_complaint(
            db, uuid.uuid4(), cid, ACTOR_CUSTOMER, "partial", "reason",
        )
        assert str(refund.customer_id) == str(cid)
        db.add.assert_called_once()
        db.commit.assert_awaited_once()


@pytest.mark.asyncio
class TestResolutionCrossComplaintIDOR:
    async def test_accept_resolution_rejects_foreign_resolution_id(self):
        """Complaint A belongs to the customer; resolution_id belongs to
        complaint B (any other customer/tenant). Must be rejected as if
        the resolution didn't exist -- no existence leakage."""
        svc = ComplaintService()
        db = _mock_db()
        cid = uuid.uuid4()
        complaint_a_id = uuid.uuid4()
        complaint_a = MagicMock(id=complaint_a_id, customer_id=cid, status=STATUS_AWAITING_PROVIDER,
                                 tenant_id=uuid.uuid4())
        foreign_resolution = MagicMock(complaint_id=uuid.uuid4(), resolution_type="apology")
        svc.get_customer_complaint = AsyncMock(return_value=complaint_a)
        svc._get_resolution_query = None
        from unittest.mock import patch
        with patch.object(svc, "_get_resolution", wraps=svc._get_resolution) as spy:
            async def fake_get_resolution(db, resolution_id, complaint_id=None):
                if complaint_id is not None and str(foreign_resolution.complaint_id) != str(complaint_id):
                    raise ValueError(ERR_RESOLUTION_NOT_FOUND)
                return foreign_resolution
            spy.side_effect = fake_get_resolution
            with pytest.raises(ValueError, match=ERR_RESOLUTION_NOT_FOUND):
                await svc.customer_accept_resolution(db, cid, complaint_a_id, uuid.uuid4())
        db.add.assert_not_called()
        db.commit.assert_not_called()

    async def test_get_resolution_cross_check_directly(self):
        """Direct unit test of the fixed _get_resolution helper itself."""
        svc = ComplaintService()
        db = _mock_db()
        complaint_id = uuid.uuid4()
        resolution = MagicMock(complaint_id=uuid.uuid4())  # different complaint
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = resolution
        db.execute = AsyncMock(return_value=result_mock)
        with pytest.raises(ValueError, match=ERR_RESOLUTION_NOT_FOUND):
            await svc._get_resolution(db, uuid.uuid4(), complaint_id=complaint_id)

    async def test_get_resolution_matching_complaint_succeeds(self):
        svc = ComplaintService()
        db = _mock_db()
        complaint_id = uuid.uuid4()
        resolution = MagicMock(complaint_id=complaint_id)
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = resolution
        db.execute = AsyncMock(return_value=result_mock)
        result = await svc._get_resolution(db, uuid.uuid4(), complaint_id=complaint_id)
        assert result is resolution

    async def test_get_resolution_no_complaint_id_supplied_is_unchanged(self):
        """Callers that don't supply complaint_id (none currently exist,
        but the parameter is optional) retain the original behavior."""
        svc = ComplaintService()
        db = _mock_db()
        resolution = MagicMock(complaint_id=uuid.uuid4())
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = resolution
        db.execute = AsyncMock(return_value=result_mock)
        result = await svc._get_resolution(db, uuid.uuid4())
        assert result is resolution


@pytest.mark.asyncio
class TestResolutionOrderingDefectFix:
    """Workstream 16 example: persistence occurring before transition
    validation. Previously resolution.status (and, for rework, a real
    ServiceReworkRequest) was mutated/committed before the complaint's
    state-transition legality was checked."""

    async def test_accept_resolution_illegal_state_creates_no_mutation(self):
        svc = ComplaintService()
        db = _mock_db()
        cid = uuid.uuid4()
        complaint_id = uuid.uuid4()
        complaint = MagicMock(id=complaint_id, customer_id=cid, status=STATUS_CLOSED,
                               tenant_id=uuid.uuid4())
        resolution = MagicMock(complaint_id=complaint_id, resolution_type="apology")
        svc.get_customer_complaint = AsyncMock(return_value=complaint)
        svc._get_resolution = AsyncMock(return_value=resolution)
        with pytest.raises(ValueError, match=ERR_COMPLAINT_INVALID_TRANSITION):
            await svc.customer_accept_resolution(db, cid, complaint_id, uuid.uuid4())
        # No mutation of any kind should have occurred.
        db.flush.assert_not_called()
        db.commit.assert_not_called()
        assert resolution.status != "customer_accepted"

    async def test_reject_resolution_illegal_state_creates_no_mutation(self):
        svc = ComplaintService()
        db = _mock_db()
        cid = uuid.uuid4()
        complaint_id = uuid.uuid4()
        complaint = MagicMock(id=complaint_id, customer_id=cid, status=STATUS_CLOSED,
                               tenant_id=uuid.uuid4())
        resolution = MagicMock(complaint_id=complaint_id, resolution_type="apology")
        svc.get_customer_complaint = AsyncMock(return_value=complaint)
        svc._get_resolution = AsyncMock(return_value=resolution)
        with pytest.raises(ValueError, match=ERR_COMPLAINT_INVALID_TRANSITION):
            await svc.customer_reject_resolution(db, cid, complaint_id, uuid.uuid4(), "reason")
        db.flush.assert_not_called()
        db.commit.assert_not_called()

    async def test_accept_rework_resolution_illegal_state_does_not_create_rework(self):
        """The most severe pre-fix case: a rework resolution's
        ServiceReworkRequest creation (which commits internally) must not
        happen at all when the complaint's state doesn't legally allow
        the resulting transition."""
        svc = ComplaintService()
        db = _mock_db()
        cid = uuid.uuid4()
        complaint_id = uuid.uuid4()
        complaint = MagicMock(id=complaint_id, customer_id=cid, status=STATUS_CLOSED,
                               tenant_id=uuid.uuid4())
        resolution = MagicMock(complaint_id=complaint_id, resolution_type="rework")
        svc.get_customer_complaint = AsyncMock(return_value=complaint)
        svc._get_resolution = AsyncMock(return_value=resolution)
        from unittest.mock import patch
        with patch("app.engines.complaints.rework_service.ServiceReworkService") as MockRework:
            with pytest.raises(ValueError, match=ERR_COMPLAINT_INVALID_TRANSITION):
                await svc.customer_accept_resolution(db, cid, complaint_id, uuid.uuid4())
            MockRework.assert_not_called()
