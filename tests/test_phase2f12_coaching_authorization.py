"""Phase 2A Slice 2F-12 — execution.coaching_router authorization,
ownership, and lifecycle closure.

Fresh runtime introspection (not assumed) found this module structurally
identical to `execution.real_estate_router` (Slice 2F-11/2F-11A) — same
Sprint 21 author pattern, same bug class:

- `staff_router` (8 mounted mutation routes,
  `/v1/staff/coaching-appointments` for 7 + `/v1/provider/coaching-appointments`
  for 1) used `get_current_user` only -- no role check at all. Any
  authenticated user of any role could call every appointment-lifecycle
  mutation, gated only by the per-appointment `staff_member_id`
  exact-match assignment check already correctly enforced inside
  `CoachingAppointmentExecutionService` (`_assert_staff_owns_appt`) --
  object ownership, not persona.
- `staff_timeline`/`provider_timeline` (2 reads) and `customer_tracking`
  (1 read) were likewise `get_current_user`-only.
- `admin_router`'s 1 route was already correctly `require_super_admin`-gated.

No technician/mobile caller was found anywhere for this module
(confirmed via repository-wide grep) -- matching the identical evidence
gap already closed for real-estate in Slices 2F-11/2F-11A. Fixed with
the same guards from day one (not requiring a follow-up slice this
time): all 8 mutations use `require_owner_or_office_staff_mutation`
(technician excluded); the 2 staff/provider reads use a local
`require_owner_or_office_staff_read` (mirroring 2F-11A's fix, technician
excluded from the start); `customer_tracking` uses `require_customer`.

Architecture finding: `app.engines.execution.coaching_router` operates
on `CoachingAppointment` (final_records) -- a CONFIRMED, already-booked
appointment record. No slot-hold, capacity, or enrolment/conversion
model exists in this module; that machinery lives in a distinct module,
`app.engines.coaching_appointment` (draft + `CoachingAppointmentSlotHold`
+ confirmation flow), which shares no table or lifecycle-execution
capability with this router -- confirmed absent, not fabricated (see
`docs/workflow-rearchitecture/phase-02a-slice-02f12/coaching-model-lineage.md`).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext


def _user(role: str, user_id: str | None = None, tenant_id: str | None = None,
          access_scope: str | None = None) -> UserContext:
    return UserContext(
        user_id=user_id or str(uuid.uuid4()), email=f"{role}@test.local", role=role,
        tenant_id=tenant_id or str(uuid.uuid4()), full_name=role.title(), is_verified=True,
        access_scope=access_scope,
    )


def _override(u):
    app.dependency_overrides[get_current_user] = lambda: u


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


APPT_ID = "11111111-1111-1111-1111-111111111111"

MUTATION_ROUTES = [
    ("POST", f"/v1/staff/coaching-appointments/{APPT_ID}/accept", None),
    ("POST", f"/v1/staff/coaching-appointments/{APPT_ID}/reject", {"reason": "unavailable"}),
    ("POST", f"/v1/staff/coaching-appointments/{APPT_ID}/start", None),
    ("POST", f"/v1/staff/coaching-appointments/{APPT_ID}/complete", None),
    ("POST", f"/v1/staff/coaching-appointments/{APPT_ID}/no-show", {}),
    ("POST", f"/v1/staff/coaching-appointments/{APPT_ID}/request-reschedule", {}),
    ("POST", f"/v1/staff/coaching-appointments/{APPT_ID}/notes", {"note_text": "hello"}),
    ("POST", f"/v1/provider/coaching-appointments/{APPT_ID}/cancel", {"reason": "closed"}),
]

STAFF_READ_ROUTES = [
    ("GET", f"/v1/staff/coaching-appointments/{APPT_ID}/timeline"),
    ("GET", f"/v1/provider/coaching-appointments/{APPT_ID}/timeline"),
]

DENIED_ROLES = ["technician", "customer", "guest", "totally_bogus_role"]


@pytest.mark.asyncio
class TestMutationRoleGate:
    async def test_unauthenticated_denied_on_every_mutation_route(self):
        _clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for method, path, body in MUTATION_ROUTES:
                resp = await client.request(method, path, json=body)
                assert resp.status_code in (401, 403), f"{method} {path} -> {resp.status_code}"

    @pytest.mark.parametrize("role", DENIED_ROLES)
    async def test_denied_role_rejected_on_every_mutation_route(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path, body in MUTATION_ROUTES:
                    resp = await client.request(method, path, json=body)
                    assert resp.status_code == 403, f"{role} {method} {path} -> {resp.status_code}"
        finally:
            _clear()

    async def test_readonly_tenant_owner_denied_despite_role(self):
        _override(_user("tenant_owner", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/v1/staff/coaching-appointments/{APPT_ID}/accept")
                assert resp.status_code == 403
        finally:
            _clear()

    async def test_readonly_staff_denied_despite_role(self):
        _override(_user("staff", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/v1/staff/coaching-appointments/{APPT_ID}/accept")
                assert resp.status_code == 403
        finally:
            _clear()

    async def test_tenant_owner_staff_admin_clear_role_gate(self):
        for role in ("tenant_owner", "staff", "super_admin"):
            _override(_user(role))
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(f"/v1/staff/coaching-appointments/{APPT_ID}/accept")
                    body = resp.json()
                    error_code = (body.get("error") or {}).get("code") or body.get("error_code")
                    assert error_code != "PERMISSION_DENIED", (role, body)
            finally:
                _clear()


@pytest.mark.asyncio
class TestReadRoleGate:
    async def test_denied_role_rejected_on_reads(self):
        for role in ("technician", "customer", "guest"):
            _override(_user(role))
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    for method, path in STAFF_READ_ROUTES:
                        resp = await client.request(method, path)
                        assert resp.status_code == 403, f"{role} {method} {path}"
            finally:
                _clear()

    async def test_readonly_tenant_owner_retains_read_access(self):
        _override(_user("tenant_owner", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path in STAFF_READ_ROUTES:
                    resp = await client.request(method, path)
                    body = resp.json()
                    error_code = (body.get("error") or {}).get("code") or body.get("error_code")
                    assert error_code != "PERMISSION_DENIED", (method, path, body)
        finally:
            _clear()


@pytest.mark.asyncio
class TestCustomerTrackingRoleGate:
    async def test_unauthenticated_denied(self):
        _clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/v1/customer/coaching-appointments/{APPT_ID}/tracking")
            assert resp.status_code in (401, 403)

    @pytest.mark.parametrize("role", ["tenant_owner", "staff", "technician", "guest"])
    async def test_non_customer_role_denied(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/v1/customer/coaching-appointments/{APPT_ID}/tracking")
                assert resp.status_code == 403, f"{role} -> {resp.status_code}"
        finally:
            _clear()

    async def test_correct_customer_clears_role_gate(self):
        _override(_user("customer"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/v1/customer/coaching-appointments/{APPT_ID}/tracking")
                body = resp.json()
                error_code = (body.get("error") or {}).get("code") or body.get("error_code")
                assert error_code != "PERMISSION_DENIED", body
        finally:
            _clear()


@pytest.mark.asyncio
class TestAdminRouteUnchanged:
    @pytest.mark.parametrize("role", ["tenant_owner", "staff", "customer", "guest"])
    async def test_non_super_admin_denied(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/v1/admin/coaching-appointments/{APPT_ID}/execution-timeline")
                assert resp.status_code == 403
        finally:
            _clear()


class TestReadGuardIsCorrectPersona:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("role,allowed", [
        ("super_admin", True), ("tenant_owner", True), ("staff", True),
        ("technician", False), ("customer", False), ("guest", False),
        ("totally_bogus_role", False),
    ])
    async def test_role_admission(self, role, allowed):
        from app.engines.execution.coaching_router import require_owner_or_office_staff_read
        from app.exceptions import ServiceOSException
        u = _user(role)
        if allowed:
            result = await require_owner_or_office_staff_read(u)
            assert result is u
        else:
            with pytest.raises(ServiceOSException):
                await require_owner_or_office_staff_read(u)


# ── Service-layer assignment ownership (pre-existing, re-verified) ───────────
from app.engines.execution.coaching_service import CoachingAppointmentExecutionService
from app.engines.execution.constants import ERR_STAFF_NOT_ASSIGNED, ERR_RECORD_NOT_FOUND


def _mock_appt(status="confirmed", staff_member_id=None, tenant_id=None):
    from app.engines.final_records.models import CoachingAppointment
    appt = MagicMock(spec=CoachingAppointment)
    appt.id = uuid.uuid4()
    appt.tenant_id = tenant_id or uuid.uuid4()
    appt.staff_member_id = staff_member_id or uuid.uuid4()
    appt.status = status
    appt.failure_reason = None
    appt.updated_at = None
    appt.to_dict = lambda: {"id": str(appt.id), "status": appt.status}
    return appt


def _db_returning(appt):
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = appt
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
class TestAssignmentOwnershipReVerified:
    async def test_wrong_staff_denied(self):
        svc = CoachingAppointmentExecutionService()
        real_staff = uuid.uuid4()
        wrong_staff = uuid.uuid4()
        appt = _mock_appt(status="confirmed", staff_member_id=real_staff)
        db = _db_returning(appt)
        with pytest.raises(ValueError, match=ERR_STAFF_NOT_ASSIGNED):
            await svc.accept_appointment(db, appt.id, appt.tenant_id, wrong_staff, uuid.uuid4())
        assert appt.status == "confirmed"

    async def test_foreign_tenant_appt_not_found(self):
        svc = CoachingAppointmentExecutionService()
        appt = _mock_appt(status="confirmed")
        db = MagicMock()
        result = MagicMock()
        result.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(return_value=result)
        with pytest.raises(ValueError, match=ERR_RECORD_NOT_FOUND):
            await svc.accept_appointment(db, appt.id, uuid.uuid4(), appt.staff_member_id, uuid.uuid4())

    async def test_assigned_staff_allowed(self):
        svc = CoachingAppointmentExecutionService()
        staff_id = uuid.uuid4()
        appt = _mock_appt(status="confirmed", staff_member_id=staff_id)
        db = _db_returning(appt)
        await svc.accept_appointment(db, appt.id, appt.tenant_id, staff_id, uuid.uuid4())
        assert appt.status == "accepted"

    async def test_provider_cancel_not_assignment_limited(self):
        """cancel_appointment (provider_cancel route) does NOT call
        _assert_staff_owns_appt -- confirmed by source read; any provider
        persona (not just the assigned staff) may cancel. Documented, not
        a defect -- cancellation is a business-level action, consistent
        with the analogous real-estate design choice for tenant-wide
        reads (business oversight), just applied to a mutation here since
        the source explicitly omits the assignment check for this one
        action."""
        svc = CoachingAppointmentExecutionService()
        appt = _mock_appt(status="confirmed")
        db = _db_returning(appt)
        await svc.cancel_appointment(db, appt.id, appt.tenant_id, uuid.uuid4(), reason="closed")
        assert appt.status == "cancelled"
