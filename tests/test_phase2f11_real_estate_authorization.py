"""Phase 2A Slice 2F-11 — complaints.execution.real_estate_router
authorization, ownership, and lifecycle closure.

Fresh runtime introspection (not assumed) found:
- `agent_router` (11 mounted mutation routes, `/v1/staff/real-estate-leads`)
  used `get_current_user` only -- no role check of any kind. Any
  authenticated user of any role (customer, guest, technician, a
  cross-tenant staff member) could call every lead-lifecycle mutation,
  gated only by the per-lead `agent_id` exact-match assignment check
  already correctly enforced inside `RealEstateLeadExecutionService`
  (`_assert_agent_owns_lead`) -- which blocks a *different* user from
  acting on someone else's assigned lead, but never verified the caller
  had an appropriate persona at all.
- `agent_router`'s GET `/timeline` and `provider_router`'s 2 GET routes
  (`/timeline`, `/notes`) were likewise `get_current_user`-only reads.
- `customer_router`'s GET `/tracking` was `get_current_user`-only,
  relying entirely on its own inline `customer_id` filter for privacy.
- `admin_router`'s 2 routes were already correctly
  `require_super_admin`-gated -- unmodified.

No technician caller was found anywhere (no mobile/staff-app reference
to any `real-estate-leads` endpoint) -- only `frontend/tenant-portal`
calls the agent mutation routes, and even there only 9 of the 11 backend
mutations have any frontend caller at all (`reject`/`disqualify` are
backend-only, unreferenced by any UI). This matches
`require_owner_or_office_staff_mutation`'s own documented rationale
(Slice 2F-6A: "no mobile/technician client has ever called the endpoint
and no product evidence proves technician was an intended actor") --
applied here instead of the broader `require_staff_or_above_mutation`,
which would have admitted technicians without evidence.

Fixed: all 11 agent mutation routes now use
`require_owner_or_office_staff_mutation` (role in {super_admin,
tenant_owner, staff}, access-scope-aware); `customer_tracking` now uses
`require_customer`. The existing, correct per-lead
`_assert_agent_owns_lead` assignment check is unchanged and remains the
authoritative object-ownership boundary this role gate sits in front of.

[CORRECTED IN SLICE 2F-11A]: `agent_timeline` and both `provider_router`
reads originally used `require_staff_or_above` (admits technician). Slice
2F-11A found this inconsistent with the mutation guard's own evidence
standard -- no technician/mobile caller exists for this module's reads
either -- and replaced it with `require_owner_or_office_staff_read`
(same persona set as the mutation guard, without the read-only-scope
deny). See `docs/workflow-rearchitecture/phase-02a-slice-02f11a/`.
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


LEAD_ID = "11111111-1111-1111-1111-111111111111"

AGENT_MUTATION_ROUTES = [
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/accept", None),
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/reject", {"reason": "out of area"}),
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/mark-contacted", {}),
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/schedule-follow-up", {}),
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/plan-site-visit", {}),
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/complete-site-visit", {}),
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/qualify", {}),
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/disqualify", {"reason": "not interested"}),
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/convert", {}),
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/close-lost", {"reason": "went with competitor"}),
    ("POST", f"/v1/staff/real-estate-leads/{LEAD_ID}/notes", {"note_text": "hello"}),
]

AGENT_READ_ROUTES = [
    ("GET", f"/v1/staff/real-estate-leads/{LEAD_ID}/timeline"),
]

PROVIDER_READ_ROUTES = [
    ("GET", f"/v1/provider/real-estate-leads/{LEAD_ID}/timeline"),
    ("GET", f"/v1/provider/real-estate-leads/{LEAD_ID}/notes"),
]

DENIED_ROLES_FOR_AGENT = ["technician", "customer", "guest", "totally_bogus_role"]


@pytest.mark.asyncio
class TestAgentMutationRoleGate:
    """Workstream 1/5/6/18: role gate for the 11 agent lead-lifecycle
    mutations. require_owner_or_office_staff_mutation admits
    super_admin/tenant_owner/staff only -- technician deliberately
    excluded (no evidence)."""

    async def test_unauthenticated_denied_on_every_mutation_route(self):
        _clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for method, path, body in AGENT_MUTATION_ROUTES:
                resp = await client.request(method, path, json=body)
                assert resp.status_code in (401, 403), f"{method} {path} -> {resp.status_code}"

    @pytest.mark.parametrize("role", DENIED_ROLES_FOR_AGENT)
    async def test_denied_role_rejected_on_every_mutation_route(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path, body in AGENT_MUTATION_ROUTES:
                    resp = await client.request(method, path, json=body)
                    assert resp.status_code == 403, f"{role} {method} {path} -> {resp.status_code}"
        finally:
            _clear()

    async def test_readonly_tenant_owner_denied_despite_role(self):
        _override(_user("tenant_owner", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/v1/staff/real-estate-leads/{LEAD_ID}/accept")
                assert resp.status_code == 403
        finally:
            _clear()

    async def test_readonly_staff_denied_despite_role(self):
        _override(_user("staff", access_scope="customer_support_limited"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/v1/staff/real-estate-leads/{LEAD_ID}/accept")
                assert resp.status_code == 403
        finally:
            _clear()

    async def test_tenant_owner_and_staff_clear_the_role_gate(self):
        """Role gate cleared -- ownership/not-found denial is a
        different, expected error, not PERMISSION_DENIED."""
        for role in ("tenant_owner", "staff", "super_admin"):
            _override(_user(role))
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(f"/v1/staff/real-estate-leads/{LEAD_ID}/accept")
                    body = resp.json()
                    error_code = (body.get("error") or {}).get("code") or body.get("error_code")
                    assert error_code != "PERMISSION_DENIED", (role, body)
            finally:
                _clear()


@pytest.mark.asyncio
class TestReadRouteRoleGate:
    async def test_agent_timeline_denied_for_customer_and_guest(self):
        for role in ("customer", "guest"):
            _override(_user(role))
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    for method, path in AGENT_READ_ROUTES:
                        resp = await client.request(method, path)
                        assert resp.status_code == 403, f"{role} {method} {path}"
            finally:
                _clear()

    async def test_provider_reads_denied_for_customer_and_guest(self):
        for role in ("customer", "guest"):
            _override(_user(role))
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    for method, path in PROVIDER_READ_ROUTES:
                        resp = await client.request(method, path)
                        assert resp.status_code == 403, f"{role} {method} {path}"
            finally:
                _clear()

    async def test_technician_denied_on_reads(self):
        """[CORRECTED IN SLICE 2F-11A] Reads now use
        require_owner_or_office_staff_read (technician excluded), matching
        the mutation guard's persona set -- no technician/mobile caller
        evidence exists anywhere for this module, and admitting technician
        via require_staff_or_above was implementation evidence only, not
        product-policy evidence. See phase-02a-slice-02f11a/."""
        _override(_user("technician"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for method, path in AGENT_READ_ROUTES + PROVIDER_READ_ROUTES:
                    resp = await client.request(method, path)
                    assert resp.status_code == 403, f"{method} {path} -> {resp.status_code}"
        finally:
            _clear()


@pytest.mark.asyncio
class TestCustomerTrackingRoleGate:
    async def test_unauthenticated_denied(self):
        _clear()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/v1/customer/real-estate-leads/{LEAD_ID}/tracking")
            assert resp.status_code in (401, 403)

    @pytest.mark.parametrize("role", ["tenant_owner", "staff", "technician", "guest"])
    async def test_non_customer_role_denied(self, role):
        _override(_user(role))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/v1/customer/real-estate-leads/{LEAD_ID}/tracking")
                assert resp.status_code == 403, f"{role} -> {resp.status_code}"
        finally:
            _clear()

    async def test_correct_customer_clears_role_gate(self):
        _override(_user("customer"))
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(f"/v1/customer/real-estate-leads/{LEAD_ID}/tracking")
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
                resp = await client.get(f"/v1/admin/real-estate-leads/{LEAD_ID}/execution-timeline")
                assert resp.status_code == 403
        finally:
            _clear()


# ── Service-layer assignment ownership (pre-existing, re-verified) ───────────
from app.engines.execution.real_estate_service import RealEstateLeadExecutionService
from app.engines.execution.constants import ERR_STAFF_NOT_ASSIGNED, ERR_RECORD_NOT_FOUND


def _mock_lead(status="new", agent_id=None, tenant_id=None):
    from app.engines.final_records.models import RealEstateLead
    lead = MagicMock(spec=RealEstateLead)
    lead.id = uuid.uuid4()
    lead.tenant_id = tenant_id or uuid.uuid4()
    lead.agent_id = agent_id or uuid.uuid4()
    lead.status = status
    lead.failure_reason = None
    lead.updated_at = None
    lead.to_dict = lambda: {"id": str(lead.id), "status": lead.status}
    return lead


def _db_returning(lead):
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = lead
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
class TestAssignmentOwnershipReVerified:
    """Re-verifies the pre-existing, correct per-lead assignment check
    this slice's role-gate fix sits in front of -- not modified."""

    async def test_wrong_agent_denied(self):
        svc = RealEstateLeadExecutionService()
        real_agent = uuid.uuid4()
        wrong_agent = uuid.uuid4()
        lead = _mock_lead(status="new", agent_id=real_agent)
        db = _db_returning(lead)
        with pytest.raises(ValueError, match=ERR_STAFF_NOT_ASSIGNED):
            await svc.accept_lead(db, lead.id, lead.tenant_id, wrong_agent, uuid.uuid4())
        assert lead.status == "new"  # unchanged

    async def test_foreign_tenant_lead_not_found(self):
        """Tenant filter in _get_lead means a foreign-tenant lead ID
        raises NOT_FOUND, not a leaked ownership-denied distinction."""
        svc = RealEstateLeadExecutionService()
        lead = _mock_lead(status="new")
        db = _mock_db_no_result = MagicMock()
        result = MagicMock()
        result.scalars.return_value.first.return_value = None  # tenant filter excludes it
        db.execute = AsyncMock(return_value=result)
        with pytest.raises(ValueError, match=ERR_RECORD_NOT_FOUND):
            await svc.accept_lead(db, lead.id, uuid.uuid4(), lead.agent_id, uuid.uuid4())

    async def test_assigned_agent_allowed(self):
        svc = RealEstateLeadExecutionService()
        agent_id = uuid.uuid4()
        lead = _mock_lead(status="new", agent_id=agent_id)
        db = _db_returning(lead)
        result = await svc.accept_lead(db, lead.id, lead.tenant_id, agent_id, uuid.uuid4())
        assert lead.status == "accepted"
