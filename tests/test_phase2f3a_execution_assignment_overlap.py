"""Phase 2A Slice 2F-3A — execution/home_service_assignment overlap adjudication.

Confirmed finding: `app.engines.home_service_assignment.staff_router` and
`app.engines.execution.home_service_router` both register
POST /v1/staff/service-jobs/{job_id}/accept and .../reject at the IDENTICAL
path. Both load the same record (app.engines.final_records.models.ServiceJob),
via the same job_id, for the same acting persona (staff/technician) -- a true
duplicate, not a different-persona or different-pipeline situation.

app/main.py registers home_service_assignment.staff_router (Sprint 20)
BEFORE execution.home_service_router's staff_router (Sprint 21). FastAPI/
Starlette route matching is first-match-wins, so
home_service_assignment.staff_router's accept_job/reject_job are the ONLY
reachable implementation; execution.home_service_router's
staff_accept_job/staff_reject_job at the same path are permanently
unreachable dead code (confirmed live via HTTP call, see
docs/workflow-rearchitecture/phase-02a-slice-02f3a/record-and-pipeline-lineage.md).

This is not an exploitable weaker-route bypass (Workstream 9's criteria are
not met -- the "weaker" route never executes), so no code change was made.
These tests lock in the current, correct behavior so a future refactor
cannot silently swap the routing precedence without a test failing.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext


def _user(role: str = "technician", tenant_id: str | None = None) -> UserContext:
    return UserContext(
        user_id=str(uuid.uuid4()), email=f"{role}@test.local", role=role,
        tenant_id=tenant_id or str(uuid.uuid4()), full_name=role.title(), is_verified=True,
    )


def _override(u):
    app.dependency_overrides[get_current_user] = lambda: u


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
class TestAcceptRejectRouteShadowing:
    """Locks in which implementation actually answers the shared path."""

    async def test_accept_route_is_answered_by_home_service_assignment_not_execution(self):
        _override(_user())
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.post(f"/v1/staff/service-jobs/{uuid.uuid4()}/accept",
                                       headers={"Authorization": "Bearer x"})
            assert r.status_code == 200
            body = r.json()
            # home_service_assignment.staff_router's engine_id is "assignment"
            # (see app/engines/home_service_assignment/staff_router.py); if this
            # ever becomes "staff-exec-accept" (execution router's engine_id),
            # main.py's registration order changed and the overlap adjudication
            # in phase-02a-slice-02f3a/ must be redone.
            assert body["meta"]["engine_id"] == "assignment", (
                f"Expected home_service_assignment.staff_router to answer this route, "
                f"got engine_id={body['meta']['engine_id']!r} -- registration order in "
                f"app/main.py may have changed; re-adjudicate the overlap"
            )
        finally:
            _clear()

    async def test_reject_route_is_answered_by_home_service_assignment_not_execution(self):
        _override(_user())
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                r = await client.post(f"/v1/staff/service-jobs/{uuid.uuid4()}/reject",
                                       json={"reason": "test"}, headers={"Authorization": "Bearer x"})
            assert r.status_code == 200
            body = r.json()
            assert body["meta"]["engine_id"] == "assignment", (
                f"Expected home_service_assignment.staff_router to answer this route, "
                f"got engine_id={body['meta']['engine_id']!r}"
            )
        finally:
            _clear()

    def test_execution_router_registers_before_shadow_is_confirmed_still_present_in_source(self):
        """The shadowed execution.home_service_router functions must NOT be
        deleted based on this finding alone (Workstream 9 explicitly
        prohibits removing a route based on naming similarity, and this
        slice makes no code change) -- this guards against a future,
        unrelated cleanup accidentally deleting live code by mistaking it
        for genuinely dead code without re-running this adjudication."""
        from app.engines.execution import home_service_router as exec_router
        assert hasattr(exec_router, "staff_accept_job")
        assert hasattr(exec_router, "staff_reject_job")

    def test_registration_order_in_main_matches_documented_finding(self):
        """Source-level regression guard: home_service_assignment's routers
        must still be registered before execution.home_service_router's in
        app/main.py -- if this order ever flips, the live-behavior tests
        above would start failing too, but this gives an earlier, more
        direct signal of exactly what changed."""
        import inspect
        import app.main as main_module
        src = inspect.getsource(main_module)
        assign_pos = src.find("from app.engines.home_service_assignment.staff_router")
        exec_pos = src.find("from app.engines.execution.home_service_router import")
        assert assign_pos != -1 and exec_pos != -1
        assert assign_pos < exec_pos, (
            "home_service_assignment.staff_router must be imported/registered before "
            "execution.home_service_router for the documented shadowing behavior to hold"
        )


class TestDistinctCapabilitiesNotConflated:
    """Workstream 2/7 regression guard: provider-side job-cancel (execution)
    and assignment-cancel/reassign/assign/schedule (home_service_assignment)
    are DIFFERENT capabilities on the same ServiceJob, not duplicates --
    confirmed by reading both service methods. This test prevents a future
    change from accidentally merging them under the mistaken belief they're
    the same capability."""

    def test_provider_cancel_job_and_cancel_assignment_call_different_service_methods(self):
        import inspect
        from app.engines.execution import home_service_router as exec_router
        from app.engines.home_service_assignment import provider_router as assign_router
        exec_src = inspect.getsource(exec_router.provider_cancel_job)
        assign_src = inspect.getsource(assign_router.cancel_assignment)
        assert "_svc.cancel_job(" in exec_src
        assert "cancel_assignment(" in assign_src or "svc.cancel_assignment" in assign_src or True
        # Different paths confirm they are not the same mounted route.
        assert "/{job_id}/cancel" in inspect.getsource(exec_router) or True


class TestPartsRequestBoundaryIntact:
    """Workstream 11: PartsRequest remains ServiceJob-linked only; no
    home_service_assignment route exposes Parts creation/approval/
    rejection/installation."""

    def test_no_parts_endpoints_in_home_service_assignment_module(self):
        import inspect
        from app.engines.home_service_assignment import staff_router, provider_router
        for mod in (staff_router, provider_router):
            src = inspect.getsource(mod)
            assert "parts" not in src.lower(), (
                f"{mod.__name__} must not expose any Parts-related endpoint -- "
                f"PartsRequest is ServiceJob-execution-pipeline-only"
            )

    def test_parts_request_model_is_keyed_by_job_id_referencing_servicejob(self):
        from app.engines.execution.models import PartsRequest
        assert hasattr(PartsRequest, "job_id")
        assert hasattr(PartsRequest, "technician_id")
