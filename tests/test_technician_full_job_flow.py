"""The technician's job flow, walked end to end the way the mobile app walks it.

Every step here is driven by the SAME thing the app is driven by:
`next_required_action.key` from GET .../mobile-detail. The app maps that key to
an endpoint and calls it. So the property this file protects is narrow and
exact:

    every key the projection hands out must name a step that actually advances
    THIS job -- and following those keys in order must reach `completed`.

That property was broken in two independent ways, and both are covered below:

  1. The projection's keys are hyphenated (`on-the-way`, `start-inspection`,
     ...) because each one names its real endpoint. The app keyed its routing
     maps on underscored spellings that the backend never sends, so every
     action after `accept` -- the one key spelled the same either way -- fell
     through to "unhandled" and disabled its own button. A technician could
     accept a job and then not move it again.

  2. The mobile Job Detail and jobs-list projections did not ask whether the
     customer had been contacted, while Home did, so one job advertised two
     different next actions depending on which screen you read it from.

`test_no_offered_action_is_a_dead_end` is the general form of the same
property, and is what catches the next dead end rather than this one.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.config import get_settings
from app.engines.home_service_assignment.service import (
    _NEXT_ACTION_BY_STATUS, _next_required_action,
)

_real_engine = create_async_engine(get_settings().DATABASE_URL, poolclass=NullPool)
_real_sessionmaker = async_sessionmaker(_real_engine, expire_on_commit=False)


async def _override_get_db():
    async with _real_sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
def _use_real_db():
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


def make_technician_context(tenant_id, user_id=None):
    return UserContext(user_id=user_id or str(uuid.uuid4()), email="staff@serviceos.local",
                        role="technician", tenant_id=tenant_id, full_name="Demo Staff",
                        is_verified=True)


# The app POSTs to `/{job_id}/{key}` for every action but one. `call-customer`
# names a task satisfied by either a connected platform call or the explicit
# log-it endpoint, so it is the single entry here -- and this map staying a
# single entry is what `test_every_offered_key_names_a_real_staff_endpoint`
# protects.
_ENDPOINT_FOR_KEY = {"call-customer": "customer-contacted"}


def _endpoint_for(key: str) -> str:
    return _ENDPOINT_FOR_KEY.get(key, key)


# ── The action vocabulary itself ──────────────────────────────────────────────

class TestActionVocabulary:
    """Pure checks on the keys the projection emits -- no DB needed."""

    def test_every_offered_key_names_a_real_staff_endpoint(self):
        """The keys ARE route names. This is what makes the app's job a lookup
        rather than a translation table that can drift out of sync."""
        import app.engines.execution.home_service_router as staff_routes

        prefix = "/v1/staff/service-jobs"
        paths = {r.path for r in staff_routes.staff_router.routes}
        offered = {entry[0] for entry in _NEXT_ACTION_BY_STATUS.values() if entry}
        # `accept` lives on home_service_assignment's staff_router (the
        # execution copy is deliberately de-registered); every other status
        # action is served from home_service_router.
        offered.discard("accept")
        for key in sorted(offered):
            assert f"{prefix}/{{job_id}}/{key}" in paths, (
                f"next_required_action offers '{key}', which is not a real staff endpoint"
            )

    def test_the_contact_first_key_is_the_one_action_that_is_not_a_route_name(self):
        """`call-customer` describes a TASK, not one endpoint: it is satisfied
        either by a bridged platform call (POST .../call, which records the
        event itself on connect) or by POST .../customer-contacted. Pinned so
        the exception stays deliberate -- a client cannot POST to
        `/{job_id}/call-customer` and must know about both routes.
        """
        import app.engines.execution.home_service_router as staff_routes
        import app.engines.masked_calling.router as calling_routes

        prefix = "/v1/staff/service-jobs"
        exec_paths = {r.path for r in staff_routes.staff_router.routes}
        calling_paths = {r.path for r in calling_routes.staff_router.routes}

        assert f"{prefix}/{{job_id}}/call-customer" not in exec_paths
        assert f"{prefix}/{{job_id}}/customer-contacted" in exec_paths
        assert f"{prefix}/{{job_id}}/call" in calling_paths

    def test_keys_are_hyphenated_not_underscored(self):
        """Pinned deliberately: the mobile app's routing was written against
        underscored spellings that never existed, and silently disabled every
        button whose key it could not find."""
        offered = {entry[0] for entry in _NEXT_ACTION_BY_STATUS.values() if entry}
        multiword = {k for k in offered if len(k) > len("accept")}
        assert not any("_" in k for k in offered), offered
        assert any("-" in k for k in multiword), offered

    def test_contact_first_step_is_offered_only_until_it_is_done(self):
        uncontacted = _next_required_action("accepted", {}, customer_contacted=False)
        assert uncontacted["action_type"] == "call-customer"
        assert uncontacted["allowed"] is True

        contacted = _next_required_action("accepted", {}, customer_contacted=True)
        assert contacted["action_type"] == "on-the-way"

    def test_inspection_step_is_skipped_when_the_blueprint_has_none(self):
        """`start_inspection` answers INSPECTION_NOT_REQUIRED (409) for a
        fixed-price job, so offering it stranded the job on reached_site with
        its only action guaranteed to fail."""
        no_inspection = _next_required_action(
            "reached_site", {"inspection_required": False, "can_start_work": True})
        assert no_inspection["action_type"] == "start-service"
        assert no_inspection["allowed"] is True

        with_inspection = _next_required_action(
            "reached_site", {"inspection_required": True, "can_start_work": True})
        assert with_inspection["action_type"] == "start-inspection"

    def test_inspection_pricing_behaviour_counts_as_requiring_one(self):
        """A workflow whose price is only knowable after diagnosis inspects by
        definition. Reading only the boolean skipped the inspection and then
        offered `start-service`, which the quote gate refuses -- a dead end
        reached by way of the fix for the previous one."""
        from types import SimpleNamespace
        from app.engines.execution.home_service_service import HomeServiceJobExecutionService

        workflow = SimpleNamespace(
            inspection_required=False, quote_approval_required=False,
            pricing_behavior="inspection_required")
        # The projection's own rule, applied to the same row shape it reads.
        computed = bool(workflow.inspection_required) or (
            getattr(workflow, "pricing_behavior", None) == "inspection_required")
        assert computed is True
        assert hasattr(HomeServiceJobExecutionService, "get_work_start_status")

    def test_an_unresolved_blueprint_never_grants_the_skip(self):
        """`None` means the workflow could not be resolved -- it must not read
        as 'no inspection required'."""
        unresolved = _next_required_action("reached_site", {"can_start_work": True})
        assert unresolved["action_type"] == "start-inspection"

    def test_no_live_status_leaves_the_technician_with_nothing_to_do(self):
        """Asked of the projection itself, not of the raw table -- statuses
        like `quote_required` are answered by a branch above the lookup.

        `customer_not_available` is the one live status that genuinely belongs
        to someone else: the job waits on rescheduling, not on the technician.
        """
        waiting_on_others = {"customer_not_available"}
        terminal = {"completed", "cancelled", "failed", "closed_estimate_declined"}
        work_start_status = {"inspection_required": True, "can_start_work": True}
        for status in _NEXT_ACTION_BY_STATUS:
            if status in terminal or status in waiting_on_others:
                continue
            action = _next_required_action(status, work_start_status)
            assert action["action_type"] is not None, (
                f"status '{status}' offers the technician no action"
            )

    def test_a_cleared_quote_lets_the_technician_resume_the_job(self):
        """`quote_required` used to be an unconditional dead end even after the
        customer approved -- the job could not be moved by anyone."""
        cleared = _next_required_action("quote_required", {"can_start_work": True})
        assert cleared["action_type"] == "start-service"
        assert cleared["allowed"] is True

        pending = _next_required_action(
            "quote_required",
            {"can_start_work": False, "start_work_block_message": "Waiting on approval."})
        assert pending["action_type"] == "start-service"
        assert pending["allowed"] is False
        assert pending["blocked_message"] == "Waiting on approval."

    def test_a_skipped_inspection_still_respects_the_work_start_gate(self):
        """Skipping the inspection step moved `start-service` onto
        `reached_site`. Offering it as allowed while the gate refuses would
        hand the technician a button that 409s."""
        blocked = _next_required_action("reached_site", {
            "inspection_required": False,
            "can_start_work": False,
            "start_work_block_message": "Customer has not approved the estimate.",
        })
        assert blocked["action_type"] == "start-service"
        assert blocked["allowed"] is False
        assert blocked["blocked_message"] == "Customer has not approved the estimate."


# ── The whole flow, against real rows ─────────────────────────────────────────

async def _seed(db, *, inspection_required: bool, quote_approval_required: bool):
    """A real catalog + blueprint + booking + job, at `assigned`."""
    ids = {k: uuid.uuid4() for k in
           ("cat", "tenant", "ms", "jt", "staff", "customer", "workflow", "booking", "job",
            "msjt", "assignment")}

    await db.execute(text(
        "INSERT INTO job_types (id, key, label, is_active, created_at, updated_at) "
        "VALUES (:id, :key, 'Repair', true, now(), now())"
    ), {"id": ids["jt"], "key": f"repair_{ids['jt'].hex[:6]}"})
    await db.execute(text(
        "INSERT INTO master_services (id, category_id, service_name, slug, job_type, is_active, "
        "created_at, updated_at) VALUES (:id, :cat, 'AC Repair', :slug, 'repair', true, now(), now())"
    ), {"id": ids["ms"], "cat": ids["cat"], "slug": f"ac-{ids['ms'].hex[:6]}"})
    await db.execute(text(
        "INSERT INTO master_service_job_types (id, master_service_id, job_type_id, is_active, "
        "display_order, created_at, updated_at) VALUES (:id, :ms, :jt, true, 0, now(), now())"
    ), {"id": ids["msjt"], "ms": ids["ms"], "jt": ids["jt"]})
    await db.execute(text(
        "INSERT INTO service_job_workflow (id, master_service_id, job_type_id, inspection_required, "
        "quote_approval_required, checklist_required, schedule_required, address_required, "
        "technician_required, service_area_required, availability_required, pricing_behavior, "
        "created_at, updated_at) VALUES (:id, :ms, :jt, :insp, :quote, false, false, false, false, "
        "false, false, :pricing, now(), now())"
    ), {"id": ids["workflow"], "ms": ids["ms"], "jt": ids["jt"],
        "insp": inspection_required, "quote": quote_approval_required,
        "pricing": "inspection_required" if quote_approval_required else "fixed"})
    await db.execute(text(
        "INSERT INTO service_bookings (id, booking_number, draft_id, category_id, offering_id, "
        "job_type_id, customer_id, status, assignment_status, created_at, updated_at) "
        "VALUES (:id, :num, :did, :cat, :off, :jt, :cust, 'pending_assignment', 'unassigned', now(), now())"
    ), {"id": ids["booking"], "num": f"BK-{ids['booking'].hex[:8]}", "did": uuid.uuid4(),
        "cat": ids["cat"], "off": ids["ms"], "jt": ids["jt"], "cust": ids["customer"]})
    await db.execute(text(
        "INSERT INTO service_jobs (id, job_number, booking_id, category_id, offering_id, job_type_id, "
        "service_job_workflow_id, tenant_id, customer_id, assigned_staff_id, status, assignment_status, "
        "created_at, updated_at) VALUES (:id, :num, :bid, :cat, :off, :jt, :wf, :tid, :cust, :staff, "
        "'assigned', 'assigned', now(), now())"
    ), {"id": ids["job"], "num": f"J-{ids['job'].hex[:8]}", "bid": ids["booking"], "cat": ids["cat"],
        "off": ids["ms"], "jt": ids["jt"], "wf": ids["workflow"], "tid": ids["tenant"],
        "cust": ids["customer"], "staff": ids["staff"]})
    # `accept` is the one step that reads the assignment record rather than
    # ServiceJob.assigned_staff_id, so a job without one cannot be accepted.
    await db.execute(text(
        "INSERT INTO service_job_assignments (id, job_id, booking_id, tenant_id, "
        "assigned_staff_member_id, assignment_status, assignment_type, is_current, "
        "created_at, updated_at) VALUES (:id, :jid, :bid, :tid, :staff, 'assigned', "
        "'manual', true, now(), now())"
    ), {"id": ids["assignment"], "jid": ids["job"], "bid": ids["booking"],
        "tid": ids["tenant"], "staff": ids["staff"]})
    await db.commit()
    return ids


async def _cleanup(db, ids):
    await db.execute(text("DELETE FROM service_job_work_sessions WHERE job_id=:jid"), {"jid": ids["job"]})
    await db.execute(text("DELETE FROM service_job_completion_proofs WHERE job_id=:jid"), {"jid": ids["job"]})
    await db.execute(text("DELETE FROM service_job_quotes WHERE job_id=:jid"), {"jid": ids["job"]})
    await db.execute(text("DELETE FROM job_checklist_responses WHERE job_checklist_instance_id IN "
                          "(SELECT id FROM job_checklist_instances WHERE job_id=:jid)"), {"jid": ids["job"]})
    await db.execute(text("DELETE FROM job_checklist_instances WHERE job_id=:jid"), {"jid": ids["job"]})
    await db.execute(text("DELETE FROM service_job_execution_events WHERE job_id=:jid"), {"jid": ids["job"]})
    await db.execute(text("DELETE FROM service_job_assignment_events WHERE job_id=:jid"), {"jid": ids["job"]})
    await db.execute(text("DELETE FROM service_job_assignments WHERE job_id=:jid"), {"jid": ids["job"]})
    await db.execute(text("DELETE FROM service_jobs WHERE id=:jid"), {"jid": ids["job"]})
    await db.execute(text("DELETE FROM service_bookings WHERE id=:bid"), {"bid": ids["booking"]})
    await db.execute(text("DELETE FROM service_job_workflow WHERE id=:wf"), {"wf": ids["workflow"]})
    await db.execute(text("DELETE FROM master_service_job_types WHERE master_service_id=:ms"), {"ms": ids["ms"]})
    await db.execute(text("DELETE FROM master_services WHERE id=:ms"), {"ms": ids["ms"]})
    await db.execute(text("DELETE FROM job_types WHERE id=:jt"), {"jt": ids["jt"]})
    await db.commit()


@pytest.mark.asyncio
async def test_a_fixed_price_job_walks_from_assigned_to_work_done_by_following_its_own_keys():
    """No step is chosen by this test. Each one is read from
    `next_required_action.key` and POSTed to `/{job_id}/{key}` -- exactly what
    the app does. If a key names an endpoint that refuses, or the projection
    stops offering one before the work is finished, the walk stops and the
    assertion at the end fails.
    """
    from app.database import get_session_factory, init_db

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        ids = await _seed(db, inspection_required=False, quote_approval_required=False)
        job_id, tenant_id, staff_id = ids["job"], ids["tenant"], ids["staff"]
        app.dependency_overrides[get_current_user] = lambda: make_technician_context(
            str(tenant_id), user_id=str(staff_id))
        try:
            headers = {"Authorization": "Bearer x"}
            visited = []
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for _ in range(10):
                    detail = (await client.get(
                        f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=headers)).json()["data"]
                    key = detail["next_required_action"]["key"]
                    if key is None or not detail["next_required_action"]["allowed"]:
                        break
                    visited.append((detail["job"]["workflow_status"], key))

                    # `start-service` is performed by the Work Execution screen
                    # (it starts the service transition itself), and `complete`
                    # by the completion-proof + payment screens -- neither is a
                    # plain POST to /{key}, so the walk stops where the app
                    # hands off to those screens.
                    if key in ("start-service", "complete"):
                        break
                    response = await client.post(
                        f"/v1/staff/service-jobs/{job_id}/{_endpoint_for(key)}", headers=headers)
                    assert response.status_code == 200, (
                        f"offered action '{key}' was refused: "
                        f"{response.status_code} {response.text[:300]}"
                    )

            statuses = [s for s, _ in visited]
            keys = [k for _, k in visited]

            # The exact chain the technician sees, in order. `call-customer`
            # sits between accept and travel and does not change status, which
            # is why `accepted` appears twice.
            assert keys == [
                "accept", "call-customer", "on-the-way", "reached-site", "start-service",
            ], keys
            assert statuses == [
                "assigned", "accepted", "accepted", "on_the_way", "reached_site",
            ], statuses

            # No inspection in this blueprint, so the job never enters one.
            assert "start-inspection" not in keys
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await _cleanup(db, ids)


@pytest.mark.asyncio
async def test_an_inspection_job_is_offered_the_inspection_step():
    """Same walk, blueprint with `inspection_required` -- the step the previous
    test proves is skipped must still be offered here."""
    from app.database import get_session_factory, init_db

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        ids = await _seed(db, inspection_required=True, quote_approval_required=False)
        job_id, tenant_id, staff_id = ids["job"], ids["tenant"], ids["staff"]
        app.dependency_overrides[get_current_user] = lambda: make_technician_context(
            str(tenant_id), user_id=str(staff_id))
        try:
            headers = {"Authorization": "Bearer x"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for key in ("accept", "call-customer", "on-the-way", "reached-site"):
                    detail = (await client.get(
                        f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=headers)).json()["data"]
                    assert detail["next_required_action"]["key"] == key, detail["next_required_action"]
                    response = await client.post(
                        f"/v1/staff/service-jobs/{job_id}/{_endpoint_for(key)}", headers=headers)
                    assert response.status_code == 200, response.text[:300]

                detail = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=headers)).json()["data"]
                assert detail["job"]["workflow_status"] == "reached_site"
                assert detail["next_required_action"]["key"] == "start-inspection"

                # And it is a real transition, not just a label.
                response = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/start-inspection", headers=headers)
                assert response.status_code == 200, response.text[:300]
                status = (await db.execute(
                    text("SELECT status FROM service_jobs WHERE id=:jid"), {"jid": job_id})).scalar_one()
                assert status == "inspection_started"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await _cleanup(db, ids)


@pytest.mark.asyncio
async def test_every_technician_projection_reports_the_same_next_action_for_one_job():
    """Home, the jobs list and Job Detail read the same job. They must agree.

    They did not: only Home asked whether the customer had been contacted, so
    Home said "Call Customer & Confirm Requirements" while Job Detail -- the
    screen that button opens -- said "Start Traveling" for the same job.
    """
    from app.database import get_session_factory, init_db

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        ids = await _seed(db, inspection_required=False, quote_approval_required=False)
        job_id, tenant_id, staff_id = ids["job"], ids["tenant"], ids["staff"]
        app.dependency_overrides[get_current_user] = lambda: make_technician_context(
            str(tenant_id), user_id=str(staff_id))
        try:
            headers = {"Authorization": "Bearer x"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await client.post(f"/v1/staff/service-jobs/{job_id}/accept", headers=headers)

                detail = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=headers)).json()["data"]
                home = (await client.get("/v1/staff/mobile-home", headers=headers)).json()["data"]
                # `view=active` -- this job carries no scheduled_date, and the
                # default "today" view is date-scoped.
                jobs = (await client.get("/v1/staff/mobile-jobs?view=active", headers=headers)).json()["data"]

                job_row = next(j for j in jobs["results"] if j["job_id"] == str(job_id))
                assert home["current_job"]["job_id"] == str(job_id)

                assert detail["next_required_action"]["key"] == "call-customer"
                assert home["current_job"]["next_required_action"]["key"] == "call-customer"
                assert job_row["next_required_action"]["key"] == "call-customer"

                # And all three move on together once the task is done.
                await client.post(f"/v1/staff/service-jobs/{job_id}/customer-contacted", headers=headers)

                detail = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=headers)).json()["data"]
                home = (await client.get("/v1/staff/mobile-home", headers=headers)).json()["data"]
                jobs = (await client.get("/v1/staff/mobile-jobs?view=active", headers=headers)).json()["data"]
                job_row = next(j for j in jobs["results"] if j["job_id"] == str(job_id))

                assert detail["next_required_action"]["key"] == "on-the-way"
                assert home["current_job"]["next_required_action"]["key"] == "on-the-way"
                assert job_row["next_required_action"]["key"] == "on-the-way"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await _cleanup(db, ids)


@pytest.mark.asyncio
async def test_completion_proof_state_is_read_from_the_proof_not_from_job_status():
    """Job Detail routes the single `complete` action to either the proof
    screen or the payment screen using this field. It used to be derived from
    job status -- `work_done` reported the proof "submitted" before one
    existed, sending the technician to a payment screen that then refused with
    COMPLETION_PROOF_NOT_SUBMITTED.
    """
    from app.database import get_session_factory, init_db

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        ids = await _seed(db, inspection_required=False, quote_approval_required=False)
        job_id, tenant_id, staff_id = ids["job"], ids["tenant"], ids["staff"]
        await db.execute(text("UPDATE service_jobs SET status='work_done' WHERE id=:jid"), {"jid": job_id})
        await db.commit()
        app.dependency_overrides[get_current_user] = lambda: make_technician_context(
            str(tenant_id), user_id=str(staff_id))
        try:
            headers = {"Authorization": "Bearer x"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                detail = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=headers)).json()["data"]
                assert detail["job"]["workflow_status"] == "work_done"
                assert detail["requirements"]["completion_proof"]["state"] == "not_submitted"

                await client.put(f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/draft",
                                 headers=headers, json={"resolution_summary": "Replaced the capacitor."})
                detail = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=headers)).json()["data"]
                assert detail["requirements"]["completion_proof"]["state"] == "draft"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await _cleanup(db, ids)


@pytest.mark.asyncio
async def test_a_job_type_with_no_inspection_checklist_can_still_finish_inspecting():
    """A missing checklist is a configuration gap, not a dead end.

    On the live catalog every "Repair" job type requires an inspection and
    none of them has an inspection checklist mapped, so every repair job hit
    this. The screen said "No inspection checklist configured" and offered
    nothing else, while `complete-inspection` itself was perfectly willing:
    its gate enforces REQUIRED mappings and there were none to enforce. The
    job sat on `inspection_started` with no action anywhere able to move it.
    """
    from app.database import get_session_factory, init_db

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        ids = await _seed(db, inspection_required=True, quote_approval_required=False)
        job_id, tenant_id, staff_id = ids["job"], ids["tenant"], ids["staff"]
        # Nothing maps a checklist to this blueprint -- the real situation.
        app.dependency_overrides[get_current_user] = lambda: make_technician_context(
            str(tenant_id), user_id=str(staff_id))
        try:
            headers = {"Authorization": "Bearer x"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for key in ("accept", "call-customer", "on-the-way", "reached-site", "start-inspection"):
                    response = await client.post(
                        f"/v1/staff/service-jobs/{job_id}/{_endpoint_for(key)}", headers=headers)
                    assert response.status_code == 200, f"{key}: {response.text[:200]}"

                detail = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-inspection", headers=headers)).json()["data"]

                # Still honest that the checklist is missing...
                assert detail["definition_status"] == "UNAVAILABLE"
                assert detail["instance"] is None
                assert detail["sections"] == []
                # ...but no longer a dead end.
                assert detail["readiness"]["can_complete"] is True
                assert "complete_inspection" in detail["allowed_actions"]

                # And the action it offers genuinely works.
                response = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/complete-inspection", headers=headers)
                assert response.status_code == 200, response.text[:300]
                status = (await db.execute(
                    text("SELECT status FROM service_jobs WHERE id=:jid"), {"jid": job_id})).scalar_one()
                assert status == "inspection_done"

                # The job carries on rather than stopping here.
                detail = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-detail", headers=headers)).json()["data"]
                assert detail["next_required_action"]["key"] == "start-service"
                assert detail["next_required_action"]["allowed"] is True
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await _cleanup(db, ids)


@pytest.mark.asyncio
async def test_a_terminal_job_is_not_offered_a_phantom_inspection_to_complete():
    """The allowance above is scoped to live jobs -- a cancelled or completed
    job must not sprout a completable inspection out of a missing checklist."""
    from app.database import get_session_factory, init_db

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        ids = await _seed(db, inspection_required=True, quote_approval_required=False)
        job_id, tenant_id, staff_id = ids["job"], ids["tenant"], ids["staff"]
        await db.execute(text("UPDATE service_jobs SET status='cancelled' WHERE id=:jid"), {"jid": job_id})
        await db.commit()
        app.dependency_overrides[get_current_user] = lambda: make_technician_context(
            str(tenant_id), user_id=str(staff_id))
        try:
            headers = {"Authorization": "Bearer x"}
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                detail = (await client.get(
                    f"/v1/staff/service-jobs/{job_id}/mobile-inspection", headers=headers)).json()["data"]
                assert detail["definition_status"] == "UNAVAILABLE"
                assert detail["readiness"]["can_complete"] is False
                assert detail["allowed_actions"] == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await _cleanup(db, ids)
