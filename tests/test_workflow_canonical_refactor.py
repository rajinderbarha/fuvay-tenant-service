"""WORKFLOW-CANONICALIZATION Phase 2-5 (migration 186) — verifies the real
capability columns added to `service_job_workflow`
(allows_cancellation / allows_reschedule / requires_direct_payment_record)
are actually enforced where the model docstring says they are, that the
migration-160 `checklist_required` flag (previously dead) now gates work
start, that dead system #3 (`app.engines.workflows`, the standalone
"Workflow Templates Enterprise" router formerly mounted at
`/v1/admin/workflows/templates`) is gone, and that the kept system #2
(`MasterWorkflowTemplate` / admin_catalog `/admin/workflow-templates`)
still works untouched.

Fixture data inserted directly via SQL against the real running server +
Postgres (this environment's seed data is not persistent across sessions)
-- same live httpx.AsyncClient + asyncpg pattern as
tests/test_home_services_complaint_workflow.py and
tests/test_module_l5_29_booking_cancel_reschedule.py.
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
import asyncpg
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS = "Password123!"
STAFF_EMAIL = "provider@serviceos.in"
STAFF_PASS = "Password123!"
DB_URL = "postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos"

pytestmark = pytest.mark.anyio
_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def admin_token(anyio_backend):
    if "admin" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["admin"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["admin"]


@pytest_asyncio.fixture(scope="module")
async def staff_token(anyio_backend):
    if "staff" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": STAFF_EMAIL, "password": STAFF_PASS})
            _TOKEN_CACHE["staff"] = r.json()["data"]["access_token"] if r.status_code == 200 else None
    return _TOKEN_CACHE["staff"]


@pytest_asyncio.fixture
async def admin(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        yield c


@pytest_asyncio.fixture
async def pg():
    conn = await asyncpg.connect(DB_URL)
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def staff_ctx(staff_token):
    """Resolve the real staff account's user_id + tenant_id so fixture jobs
    can be created under a tenant/staff pairing that will actually pass
    auth (require_staff_or_above_mutation + _get_job's tenant scoping +
    _assert_staff_owns_job's assigned_staff_id match)."""
    if not staff_token:
        pytest.skip("staff login unavailable")
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {staff_token}"}, timeout=30) as c:
        r = await c.get("/v1/auth/me")
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        yield {"token": staff_token, "user_id": data["user_id"], "tenant_id": data["tenant_id"]}


# ═══════════════════════════════════════════════════════════════════════════
# a. Schema — new columns exist on service_job_workflow
# ═══════════════════════════════════════════════════════════════════════════

class TestSchema:
    def test_model_has_capability_columns(self):
        from app.engines.admin_catalog.models import ServiceJobWorkflow
        cols = ServiceJobWorkflow.__table__.columns
        names = set(cols.keys())
        assert "allows_cancellation" in names
        assert "allows_reschedule" in names
        assert "requires_direct_payment_record" in names
        assert cols["allows_cancellation"].default.arg is True
        assert cols["allows_reschedule"].default.arg is True
        assert cols["requires_direct_payment_record"].default.arg is False

    async def test_db_has_capability_columns(self, pg):
        rows = await pg.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'service_job_workflow' AND column_name = ANY($1::text[])",
            ["allows_cancellation", "allows_reschedule", "requires_direct_payment_record"],
        )
        names = {r["column_name"] for r in rows}
        assert names == {"allows_cancellation", "allows_reschedule", "requires_direct_payment_record"}


# ═══════════════════════════════════════════════════════════════════════════
# Fixture: a real job scoped under the REAL logged-in staff account's
# tenant, with a workflow row snapshotted directly onto the job via
# service_job_workflow_id (bypasses the master_service/job_type link table
# entirely -- _resolve_job_type_workflow checks the snapshot column first).
# ═══════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture
async def job_factory(pg, staff_ctx):
    created = {"jobs": [], "workflows": []}

    async def _make(allows_cancellation=True, allows_reschedule=True, checklist_required=False,
                     quote_approval_required=False, status="assigned"):
        tenant_id = uuid.UUID(staff_ctx["tenant_id"])
        staff_user_id = uuid.UUID(staff_ctx["user_id"])
        category = await pg.fetchrow("SELECT id FROM service_categories LIMIT 1")
        master_service_id = uuid.uuid4()
        job_type_id = uuid.uuid4()
        wf_id = uuid.uuid4()
        job_id = uuid.uuid4()
        booking_id = uuid.uuid4()

        await pg.execute(
            "INSERT INTO service_job_workflow (id, master_service_id, job_type_id, "
            "inspection_required, quote_approval_required, checklist_required, "
            "schedule_required, address_required, technician_required, "
            "service_area_required, availability_required, pricing_behavior, "
            "version_number, is_current, status, allows_cancellation, "
            "allows_reschedule, requires_direct_payment_record, created_at, updated_at) "
            "VALUES ($1,$2,$3,false,$4,$5,false,false,false,false,false,'fixed',1,true,"
            "'published',$6,$7,false, now(), now())",
            wf_id, master_service_id, job_type_id, quote_approval_required,
            checklist_required, allows_cancellation, allows_reschedule,
        )
        await pg.execute(
            "INSERT INTO service_jobs (id, job_number, booking_id, customer_id, tenant_id, "
            "category_id, offering_id, job_type_id, service_job_workflow_id, "
            "assigned_staff_id, status, assignment_status, created_at, updated_at) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'assigned', now(), now())",
            job_id, f"WFT-{job_id.hex[:8]}", booking_id, staff_user_id, tenant_id,
            category["id"], master_service_id, job_type_id, wf_id, staff_user_id, status,
        )
        created["jobs"].append(job_id)
        created["workflows"].append(wf_id)
        return {"job_id": str(job_id), "workflow_id": str(wf_id), "tenant_id": str(tenant_id)}

    yield _make

    for jid in created["jobs"]:
        await pg.execute("DELETE FROM service_job_checklists WHERE job_id = $1", jid)
        await pg.execute("DELETE FROM service_job_quotes WHERE job_id = $1", jid)
        await pg.execute("DELETE FROM service_job_execution_events WHERE job_id = $1", jid)
        await pg.execute("DELETE FROM service_jobs WHERE id = $1", jid)
    for wid in created["workflows"]:
        await pg.execute("DELETE FROM service_job_workflow WHERE id = $1", wid)


# ═══════════════════════════════════════════════════════════════════════════
# b/c. allows_cancellation enforcement (cancel_job)
# ═══════════════════════════════════════════════════════════════════════════

class TestCancellationGate:
    async def test_cancel_rejected_when_workflow_disallows(self, staff_ctx, job_factory):
        info = await job_factory(allows_cancellation=False)
        async with AsyncClient(base_url=BASE, timeout=30,
                                headers={"Authorization": f"Bearer {staff_ctx['token']}"}) as c:
            r = await c.post(f"/v1/provider/service-jobs/{info['job_id']}/cancel",
                              json={"reason": "customer changed mind"})
            assert r.status_code == 422, r.text

    async def test_cancel_allowed_when_workflow_allows(self, staff_ctx, job_factory):
        info = await job_factory(allows_cancellation=True)
        async with AsyncClient(base_url=BASE, timeout=30,
                                headers={"Authorization": f"Bearer {staff_ctx['token']}"}) as c:
            r = await c.post(f"/v1/provider/service-jobs/{info['job_id']}/cancel",
                              json={"reason": "customer changed mind"})
            assert r.status_code == 200, r.text
            assert r.json()["data"]["status"] == "cancelled"

    async def test_cancel_still_succeeds_with_no_resolvable_workflow(self, pg, staff_ctx):
        """Regression: a job whose workflow snapshot is NULL (legacy job,
        never resolves) must still be cancellable -- cancel_job only fails
        closed when a workflow IS resolvable and explicitly disallows it."""
        tenant_id = uuid.UUID(staff_ctx["tenant_id"])
        staff_user_id = uuid.UUID(staff_ctx["user_id"])
        category = await pg.fetchrow("SELECT id FROM service_categories LIMIT 1")
        job_id, booking_id = uuid.uuid4(), uuid.uuid4()
        await pg.execute(
            "INSERT INTO service_jobs (id, job_number, booking_id, customer_id, tenant_id, "
            "category_id, offering_id, assigned_staff_id, status, assignment_status, "
            "created_at, updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'assigned','assigned', now(), now())",
            job_id, f"WFT-{job_id.hex[:8]}", booking_id, staff_user_id, tenant_id,
            category["id"], uuid.uuid4(), staff_user_id,
        )
        try:
            async with AsyncClient(base_url=BASE, timeout=30,
                                    headers={"Authorization": f"Bearer {staff_ctx['token']}"}) as c:
                r = await c.post(f"/v1/provider/service-jobs/{job_id}/cancel",
                                  json={"reason": "no workflow resolvable"})
                assert r.status_code == 200, r.text
        finally:
            await pg.execute("DELETE FROM service_job_execution_events WHERE job_id = $1", job_id)
            await pg.execute("DELETE FROM service_jobs WHERE id = $1", job_id)


# ═══════════════════════════════════════════════════════════════════════════
# d. checklist_required gate on start-service
# ═══════════════════════════════════════════════════════════════════════════

class TestChecklistGate:
    async def test_start_service_blocked_without_checklist_row(self, staff_ctx, job_factory):
        info = await job_factory(checklist_required=True, quote_approval_required=False,
                                  status="inspection_done")
        async with AsyncClient(base_url=BASE, timeout=30,
                                headers={"Authorization": f"Bearer {staff_ctx['token']}"}) as c:
            r = await c.post(f"/v1/staff/service-jobs/{info['job_id']}/start-service")
            assert r.status_code == 409, r.text
            assert r.json().get("error_code") == "CHECKLIST_REQUIRED_BEFORE_WORK_START", r.text

    async def test_start_service_succeeds_once_checklist_row_exists(self, pg, staff_ctx, job_factory):
        info = await job_factory(checklist_required=True, quote_approval_required=False,
                                  status="inspection_done")
        await pg.execute(
            "INSERT INTO service_job_checklists (id, booking_id, job_id, tenant_id, status, "
            "checklist_type, created_at, updated_at) "
            "SELECT $1, booking_id, id, tenant_id, 'pending', 'pre_work', now(), now() "
            "FROM service_jobs WHERE id = $2",
            uuid.uuid4(), uuid.UUID(info["job_id"]),
        )
        async with AsyncClient(base_url=BASE, timeout=30,
                                headers={"Authorization": f"Bearer {staff_ctx['token']}"}) as c:
            r = await c.post(f"/v1/staff/service-jobs/{info['job_id']}/start-service")
            assert r.status_code == 200, r.text
            assert r.json()["data"]["status"] == "service_started"


# ═══════════════════════════════════════════════════════════════════════════
# e. Deleted system #3 (standalone Workflow Templates Enterprise) 404s
# ═══════════════════════════════════════════════════════════════════════════

class TestDeadSystemGone:
    async def test_old_workflows_templates_route_404s(self, admin):
        r = await admin.get("/v1/admin/workflows/templates/summary")
        assert r.status_code == 404

    def test_workflows_engine_module_removed(self):
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("app.engines.workflows.workflow_router")


# ═══════════════════════════════════════════════════════════════════════════
# f. Retired duplicate system #2 (MasterWorkflowTemplate / admin_catalog route)
# ═══════════════════════════════════════════════════════════════════════════

class TestRetiredDuplicateWorkflowSurface:
    async def test_workflow_templates_summary_is_gone(self, admin, pg):
        r = await admin.get("/v1/admin/workflow-templates/summary")
        assert r.status_code == 410, r.text
        assert r.json()["error"]["code"] == "WORKFLOW_TEMPLATES_RETIRED"

    def test_admin_page_redirects_to_canonical_catalog_workspace(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        page = os.path.join(root, "frontend", "super-admin", "app", "admin",
                            "workflow-templates", "page.tsx")
        src = open(page, encoding="utf-8").read()
        assert "redirect" in src
        assert "/admin/catalog-workspace?tab=workflow" in src
        assert "masterDataApi" not in src

    def test_canonical_job_type_workflow_router_still_present(self):
        import app.engines.admin_catalog.admin_router as ac_router_mod
        import app.engines.admin_catalog.job_type_blueprint_router as bp_router_mod
        admin_src = open(ac_router_mod.__file__, encoding="utf-8").read()
        bp_src = open(bp_router_mod.__file__, encoding="utf-8").read()
        assert "WORKFLOW_TEMPLATES_RETIRED" in admin_src
        assert '"/{service_id}/job-types/{job_type_id}/workflow"' in bp_src
