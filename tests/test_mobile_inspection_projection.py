"""Technician mobile app Phase K: GET /v1/staff/service-jobs/{job_id}/mobile-inspection
+ the reused checklist_catalog staff mutation endpoints (save-response,
complete-instance) + the existing complete-inspection workflow transition,
composed together exactly as the mobile client will call them.

Follows the established live-DB pattern from
tests/test_module_l5_53_exact_job_type_resolution.py::test_repair_vs_installation_same_master_service_live
for full end-to-end proof, plus the NullPool router-override pattern from
tests/test_mobile_job_detail_projection.py for router-level auth tests.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.config import get_settings
from app.exceptions import ServiceOSException

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
    return UserContext(user_id=user_id or str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
                        tenant_id=tenant_id, full_name="Demo Staff", is_verified=True)


# ── Router-level auth failures (no checklist data required) ─────────────

@pytest.mark.asyncio
async def test_inspection_detail_unknown_job_id_fails_closed_with_404():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-inspection", headers={"Authorization": "Bearer x"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_inspection_detail_requires_tenant_context():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
        tenant_id=None, full_name="No Tenant", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-inspection", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_inspection_detail_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-inspection", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ── Full live end-to-end: real job-type-mapped checklist, real save/complete ──

@pytest.mark.asyncio
async def test_inspection_full_lifecycle_live():
    """Real Master Service + Job Type + published checklist template mapped
    to it (INSPECTION phase, REQUIRED, gate=REQUIRE_BEFORE_INSPECTION_COMPLETE)
    + a real assigned ServiceJob. Proves: exact job-type resolution (never
    category-based), readiness math, save-response via the real reused
    endpoint, completion blocked while incomplete, completion allowed once
    complete, and the existing complete-inspection workflow transition
    advancing the job status -- all through real (non-mocked) service code
    against the live database."""
    from app.database import get_session_factory, init_db
    from app.engines.checklist_catalog import service as checklist_svc
    from app.engines.checklist_catalog import constants as cc

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        cat_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        ms_id = uuid.uuid4()
        jt_id = uuid.uuid4()
        staff_user_id = uuid.uuid4()

        await db.execute(text(
            "INSERT INTO job_types (id, key, label, is_active, created_at, updated_at) "
            "VALUES (:id, :key, 'Repair', true, now(), now())"
        ), {"id": jt_id, "key": f"repair_{jt_id.hex[:6]}"})
        await db.execute(text(
            "INSERT INTO master_services (id, category_id, service_name, slug, job_type, is_active, "
            "created_at, updated_at) VALUES (:id, :cat, 'AC Repair', :slug, 'repair', true, now(), now())"
        ), {"id": ms_id, "cat": cat_id, "slug": f"ac-{ms_id.hex[:6]}"})
        await db.execute(text(
            "INSERT INTO master_service_job_types (id, master_service_id, job_type_id, is_active, "
            "display_order, created_at, updated_at) VALUES (:id, :ms, :jt, true, 0, now(), now())"
        ), {"id": uuid.uuid4(), "ms": ms_id, "jt": jt_id})

        booking_id, job_id = uuid.uuid4(), uuid.uuid4()
        customer_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_bookings (id, booking_number, draft_id, category_id, offering_id, "
            "job_type_id, customer_id, status, assignment_status, issue_summary, created_at, updated_at) "
            "VALUES (:id, :num, :did, :cat, :off, :jt, :cust, 'pending_assignment', 'unassigned', :issue, now(), now())"
        ), {"id": booking_id, "num": f"BK-{booking_id.hex[:8]}", "did": uuid.uuid4(), "cat": cat_id, "off": ms_id,
            "jt": jt_id, "cust": customer_id, "issue": "AC is running but not cooling"})
        await db.execute(text(
            "INSERT INTO service_jobs (id, job_number, booking_id, category_id, offering_id, job_type_id, "
            "tenant_id, customer_id, assigned_staff_id, status, assignment_status, created_at, updated_at) "
            "VALUES (:id, :num, :bid, :cat, :off, :jt, :tid, :cust, :staff, 'inspection_started', 'assigned', now(), now())"
        ), {"id": job_id, "num": f"J-{job_id.hex[:8]}", "bid": booking_id, "cat": cat_id, "off": ms_id, "jt": jt_id,
            "tid": tenant_id, "cust": customer_id, "staff": staff_user_id})
        await db.commit()

        template = mapping = None
        try:
            # Author a real checklist through the real admin service layer.
            template = await checklist_svc.create_template(
                db, name="AC Inspection", code=f"ac-insp-{uuid.uuid4().hex[:6]}", purpose=cc.PURPOSE_INSPECTION,
                owner_scope=cc.OWNER_SCOPE_PLATFORM, tenant_id=None, created_by_user_id=None, description=None,
            )
            version = await checklist_svc.get_draft_version(db, template.id)
            section = await checklist_svc.add_section(db, version, "Inspection checklist", display_order=0)
            item = await checklist_svc.add_item(
                db, section, version, item_type=cc.ITEM_TYPE_YES_NO, label="Power supply checked",
                is_required=True, display_order=0,
            )
            await checklist_svc.publish_version(db, version, published_by=None, change_summary="v1")
            mapping = await checklist_svc.create_mapping(
                db, master_service_job_type_id=(await db.execute(text(
                    "SELECT id FROM master_service_job_types WHERE master_service_id=:ms AND job_type_id=:jt"
                ), {"ms": ms_id, "jt": jt_id})).scalar_one(),
                service_job_workflow_id=None,
                checklist_template_version_id=version.id, phase=cc.PURPOSE_INSPECTION,
                usage=cc.USAGE_REQUIRED, actor=cc.ACTOR_TECHNICIAN, completion_gate=cc.GATE_BEFORE_INSPECTION_COMPLETE,
                condition_rules=None, display_order=0, created_by=None,
            )
            await db.commit()

            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                headers = {"Authorization": "Bearer x"}

                # 1. Projection resolves the exact job-type-mapped checklist.
                detail = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-inspection", headers=headers)).json()["data"]
                assert detail["job"]["service_label"] == "AC Repair"
                assert detail["customer_report"]["issue_label"] == "AC is running but not cooling"
                assert len(detail["sections"]) == 1
                assert detail["sections"][0]["title"] == "Inspection checklist"
                assert detail["readiness"]["total_required"] == 1
                assert detail["readiness"]["completed_required"] == 0
                assert detail["readiness"]["can_complete"] is False
                assert "complete_inspection" not in detail["allowed_actions"]
                instance_id = detail["instance"]["instance_id"]
                item_id = detail["sections"][0]["items"][0]["id"]

                # 2. Completion blocked while required item unanswered.
                complete_resp = await client.post(f"/v1/staff/service-jobs/checklist-instances/{instance_id}/complete", headers=headers)
                assert complete_resp.status_code == 422

                # 3. Save the required response through the real reused endpoint.
                save_resp = await client.post(
                    f"/v1/staff/service-jobs/checklist-instances/{instance_id}/responses/{item_id}",
                    json={"response_value": {"value": "yes"}}, headers=headers,
                )
                assert save_resp.status_code == 200

                # 4. Readiness now reflects completion-ready.
                detail2 = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-inspection", headers=headers)).json()["data"]
                assert detail2["readiness"]["completed_required"] == 1
                assert detail2["readiness"]["can_complete"] is True
                assert "complete_inspection" in detail2["allowed_actions"]

                # 5. Complete the checklist instance, then the real workflow transition.
                complete_resp2 = await client.post(f"/v1/staff/service-jobs/checklist-instances/{instance_id}/complete", headers=headers)
                assert complete_resp2.status_code == 200
                workflow_resp = await client.post(f"/v1/staff/service-jobs/{job_id}/complete-inspection", headers=headers)
                assert workflow_resp.status_code == 200
                assert workflow_resp.json()["data"]["status"] == "inspection_done"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            if mapping is not None:
                await db.execute(text("DELETE FROM job_checklist_responses WHERE job_checklist_instance_id IN (SELECT id FROM job_checklist_instances WHERE job_id=:jid)"), {"jid": job_id})
                await db.execute(text("DELETE FROM job_checklist_instances WHERE job_id=:jid"), {"jid": job_id})
                await db.execute(text("DELETE FROM job_type_checklist_mappings WHERE id=:mid"), {"mid": mapping.id})
            if template is not None:
                await db.execute(text("DELETE FROM checklist_items WHERE checklist_section_id IN (SELECT id FROM checklist_sections WHERE checklist_template_version_id IN (SELECT id FROM checklist_template_versions WHERE checklist_template_id=:tid))"), {"tid": template.id})
                await db.execute(text("DELETE FROM checklist_sections WHERE checklist_template_version_id IN (SELECT id FROM checklist_template_versions WHERE checklist_template_id=:tid)"), {"tid": template.id})
                await db.execute(text("DELETE FROM checklist_template_versions WHERE checklist_template_id=:tid"), {"tid": template.id})
                await db.execute(text("DELETE FROM checklist_templates WHERE id=:tid"), {"tid": template.id})
            await db.execute(text("DELETE FROM service_job_execution_events WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_jobs WHERE id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_bookings WHERE id=:bid"), {"bid": booking_id})
            await db.execute(text("DELETE FROM master_service_job_types WHERE master_service_id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM master_services WHERE id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM job_types WHERE id=:jt"), {"jt": jt_id})
            await db.commit()
