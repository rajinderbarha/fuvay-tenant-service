"""Phase 2A Slice 2F-12A — coaching appointment cancellation authority
and assignment closure.

Resolves the one question Slice 2F-12 left open: `cancel_appointment`
does not call `_assert_staff_owns_appt` (the per-appointment assignment
check) that the other 7 mutations use. Slice 2F-12 documented this as
"plausibly intentional business-wide cancellation" but marked it
UNVERIFIED.

This slice VERIFIES it via approved cross-module evidence, NOT assumption:

The sibling `home_service_service.cancel_job` -- the canonical
field-service execution module CLOSED and APPROVED in Slice 2F-3B --
uses the byte-for-byte identical pattern: whole-record cancellation
deliberately omits `_assert_staff_owns_job` while every other job
mutation enforces it. Slice 2F-3B explicitly documented and approved
`/v1/provider/service-jobs/{job_id}/cancel` as a "tenant-wide (business-
wide) provider action", `n/a` for assignment ownership. Same Sprint 21
author, same signature shape (`cancel_X(db, id, tenant_id, user_id,
reason, actor_role="provider")` -- no staff_member_id parameter at all,
unlike the assignment-checked methods), same `actor_role="provider"`
default.

Evidence class: EXPLICIT_PRODUCT_POLICY (2F-3B approved) +
TESTED_EXISTING_CONTRACT + ESTABLISHED_CROSS_MODULE_PATTERN. Business-wide
cancellation for tenant_owner AND canonical staff is the intentional,
approved, consistent design across BOTH execution modules -- not an
assignment gap. Coaching's cancel is in fact STRICTER than the approved
sibling (technician excluded here via require_owner_or_office_staff_mutation,
vs. cancel_job's require_staff_or_above_mutation which admits technician).

Final persona matrix (verified, no code change):
- tenant_owner: TENANT_OWNER_BUSINESS_WIDE_CANCEL
- canonical staff: STAFF_BUSINESS_WIDE_CANCEL
- super_admin: EXISTING_BEHAVIOR_PRESERVED (business-wide)
- technician: TECHNICIAN_CANCEL_DENIED
- customer: CUSTOMER_CANCEL_DENIED
- cross-tenant (any role): DENIED (tenant filter in _get_appt)
- read-only tenant scope: DENIED (require_owner_or_office_staff_mutation)
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.engines.execution.coaching_service import CoachingAppointmentExecutionService
from app.engines.execution.constants import (
    ERR_STAFF_NOT_ASSIGNED, ERR_RECORD_NOT_FOUND, ERR_INVALID_TRANSITION,
    ERR_REASON_REQUIRED,
)


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
CANCEL_PATH = f"/v1/provider/coaching-appointments/{APPT_ID}/cancel"


# ── Workstream 6: HTTP-level cancellation persona matrix ─────────────────────

@pytest.mark.asyncio
class TestCancellationRoleGate:
    async def test_unauthenticated_denied(self):
        _clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(CANCEL_PATH, json={"reason": "x"})
            assert resp.status_code in (401, 403)

    @pytest.mark.parametrize("role", ["technician", "customer", "guest", "totally_bogus_role"])
    async def test_denied_role_rejected(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(CANCEL_PATH, json={"reason": "x"})
                assert resp.status_code == 403, f"{role} -> {resp.status_code}"
        finally:
            _clear()

    async def test_readonly_tenant_owner_denied(self):
        _override(_user("tenant_owner", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(CANCEL_PATH, json={"reason": "x"})
                assert resp.status_code == 403
        finally:
            _clear()

    async def test_readonly_staff_denied(self):
        _override(_user("staff", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(CANCEL_PATH, json={"reason": "x"})
                assert resp.status_code == 403
        finally:
            _clear()

    @pytest.mark.parametrize("role", ["tenant_owner", "staff", "super_admin"])
    async def test_authorized_persona_clears_role_gate(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(CANCEL_PATH, json={"reason": "x"})
                body = resp.json()
                error_code = (body.get("error") or {}).get("code") or body.get("error_code")
                assert error_code != "PERMISSION_DENIED", (role, body)
        finally:
            _clear()


# ── Service-layer: business-wide authority + tenant ownership + state ────────

def _mock_appt(status="accepted", staff_member_id=None, tenant_id=None):
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


def _db_none():
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
class TestCancellationIsBusinessWide:
    """Directly proves cancel is NOT assignment-limited (business-wide) --
    the verified, intentional, cross-module-consistent behavior."""

    async def test_cancel_succeeds_when_actor_is_not_assigned_staff(self):
        """The acting user_id deliberately does NOT match the appointment's
        staff_member_id -- cancel still succeeds (no assignment check),
        unlike accept which would raise ERR_STAFF_NOT_ASSIGNED for the
        same mismatch."""
        svc = CoachingAppointmentExecutionService()
        assigned_staff = uuid.uuid4()
        acting_user = uuid.uuid4()  # different person (e.g. tenant owner / front desk)
        appt = _mock_appt(status="accepted", staff_member_id=assigned_staff)
        db = _db_returning(appt)
        result = await svc.cancel_appointment(db, appt.id, appt.tenant_id, acting_user, reason="closed")
        assert appt.status == "cancelled"
        assert result["status"] == "cancelled"

    async def test_accept_by_contrast_IS_assignment_limited(self):
        """Control: the same non-assigned actor IS blocked by accept --
        proving the cancel/accept asymmetry is real and deliberate."""
        svc = CoachingAppointmentExecutionService()
        assigned_staff = uuid.uuid4()
        non_assigned_staff = uuid.uuid4()  # a different staff member's id
        appt = _mock_appt(status="confirmed", staff_member_id=assigned_staff)
        db = _db_returning(appt)
        with pytest.raises(ValueError, match=ERR_STAFF_NOT_ASSIGNED):
            await svc.accept_appointment(db, appt.id, appt.tenant_id, non_assigned_staff, uuid.uuid4())


@pytest.mark.asyncio
class TestCancellationTenantOwnership:
    async def test_cross_tenant_cancel_not_found_no_mutation(self):
        svc = CoachingAppointmentExecutionService()
        db = _db_none()  # tenant filter excludes the appointment
        with pytest.raises(ValueError, match=ERR_RECORD_NOT_FOUND):
            await svc.cancel_appointment(db, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), reason="x")
        db.add.assert_not_called()
        db.flush.assert_not_called()
        db.commit.assert_not_called()


@pytest.mark.asyncio
class TestCancellationStateMatrix:
    """Workstream 7: cancel legality per state. cancelled is a legal
    target only from confirmed/accepted/scheduled (APPT_TRANSITIONS)."""

    @pytest.mark.parametrize("status", ["confirmed", "accepted", "scheduled"])
    async def test_legal_source_states_succeed(self, status):
        svc = CoachingAppointmentExecutionService()
        appt = _mock_appt(status=status)
        db = _db_returning(appt)
        await svc.cancel_appointment(db, appt.id, appt.tenant_id, uuid.uuid4(), reason="x")
        assert appt.status == "cancelled"

    @pytest.mark.parametrize("status", ["started", "completed", "no_show", "rejected", "cancelled"])
    async def test_illegal_source_states_rejected_no_mutation(self, status):
        svc = CoachingAppointmentExecutionService()
        appt = _mock_appt(status=status)
        db = _db_returning(appt)
        with pytest.raises(ValueError, match=ERR_INVALID_TRANSITION):
            await svc.cancel_appointment(db, appt.id, appt.tenant_id, uuid.uuid4(), reason="x")
        assert appt.status == status  # unchanged -- validated before mutation
        db.add.assert_not_called()
        db.flush.assert_not_called()

    async def test_repeated_cancel_rejected(self):
        """cancelled has an empty transition set -- a second cancel is
        STATE_TRANSITION_REJECTED, not idempotent."""
        svc = CoachingAppointmentExecutionService()
        appt = _mock_appt(status="cancelled")
        db = _db_returning(appt)
        with pytest.raises(ValueError, match=ERR_INVALID_TRANSITION):
            await svc.cancel_appointment(db, appt.id, appt.tenant_id, uuid.uuid4(), reason="x")
        db.add.assert_not_called()


@pytest.mark.asyncio
class TestCancellationReasonIntegrity:
    async def test_empty_reason_rejected_before_any_lookup(self):
        svc = CoachingAppointmentExecutionService()
        db = _db_returning(_mock_appt())
        with pytest.raises(ValueError, match=ERR_REASON_REQUIRED):
            await svc.cancel_appointment(db, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), reason="")
        db.execute.assert_not_called()  # fails before even fetching the appt
        db.add.assert_not_called()

    async def test_whitespace_reason_rejected(self):
        svc = CoachingAppointmentExecutionService()
        db = _db_returning(_mock_appt())
        with pytest.raises(ValueError, match=ERR_REASON_REQUIRED):
            await svc.cancel_appointment(db, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), reason="   ")
        db.add.assert_not_called()


class TestNoAssignmentCheckInCancelSource:
    """Direct source proof that cancel_appointment omits the assignment
    check -- and that this matches the approved sibling cancel_job."""

    def test_cancel_appointment_has_no_assignment_check(self):
        import inspect
        src = inspect.getsource(CoachingAppointmentExecutionService.cancel_appointment)
        assert "_assert_staff_owns_appt" not in src

    def test_accept_appointment_has_assignment_check(self):
        import inspect
        src = inspect.getsource(CoachingAppointmentExecutionService.accept_appointment)
        assert "_assert_staff_owns_appt" in src

    def test_sibling_cancel_job_also_omits_assignment_check(self):
        """Cross-module evidence: the approved (Slice 2F-3B) sibling
        cancel_job uses the identical no-assignment-check pattern."""
        import inspect
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService
        src = inspect.getsource(HomeServiceJobExecutionService.cancel_job)
        assert "_assert_staff_owns_job" not in src
