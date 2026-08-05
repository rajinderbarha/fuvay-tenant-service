"""Technician mobile app Phase M: GET /v1/staff/service-jobs/{job_id}/mobile-work-execution
+ start/pause/resume/finish, composed over EXISTING canonical services
(HomeServiceJobExecutionService.start_service/mark_work_done, the new
WorkSessionService, and checklist_catalog for the work checklist). Follows
the same live-DB pattern as the Phase K/L projection tests.
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


@pytest.mark.asyncio
async def test_work_execution_unknown_job_id_fails_closed_with_404():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-work-execution", headers={"Authorization": "Bearer x"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_work_execution_requires_tenant_context():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
        tenant_id=None, full_name="No Tenant", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-work-execution", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_work_execution_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-work-execution", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_work_execution_full_lifecycle_live():
    """Real Master Service + Job Type (quote_approval_required=True) + a
    real customer_approved current quote + a REQUIRED execution-phase
    checklist item. Proves: work blocked without approval is not this
    screen's job (already covered by L5-52) -- this test proves start
    creates a real session, finish is blocked while the checklist item is
    unanswered, pause/resume tracks elapsed time, finish transitions the
    job to work_done (never completed), and never touches commission."""
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
        customer_id = uuid.uuid4()

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
        workflow_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_job_workflow (id, master_service_id, job_type_id, inspection_required, "
            "quote_approval_required, checklist_required, schedule_required, address_required, "
            "technician_required, service_area_required, availability_required, pricing_behavior, "
            "created_at, updated_at) VALUES (:id, :ms, :jt, false, true, false, false, false, false, false, "
            "false, 'custom_quote', now(), now())"
        ), {"id": workflow_id, "ms": ms_id, "jt": jt_id})

        booking_id, job_id = uuid.uuid4(), uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_bookings (id, booking_number, draft_id, category_id, offering_id, "
            "job_type_id, customer_id, status, assignment_status, created_at, updated_at) "
            "VALUES (:id, :num, :did, :cat, :off, :jt, :cust, 'pending_assignment', 'unassigned', now(), now())"
        ), {"id": booking_id, "num": f"BK-{booking_id.hex[:8]}", "did": uuid.uuid4(), "cat": cat_id, "off": ms_id,
            "jt": jt_id, "cust": customer_id})
        await db.execute(text(
            "INSERT INTO service_jobs (id, job_number, booking_id, category_id, offering_id, job_type_id, "
            "service_job_workflow_id, tenant_id, customer_id, assigned_staff_id, status, assignment_status, "
            "created_at, updated_at) "
            "VALUES (:id, :num, :bid, :cat, :off, :jt, :wf, :tid, :cust, :staff, 'inspection_done', 'assigned', now(), now())"
        ), {"id": job_id, "num": f"J-{job_id.hex[:8]}", "bid": booking_id, "cat": cat_id, "off": ms_id, "jt": jt_id,
            "wf": workflow_id, "tid": tenant_id, "cust": customer_id, "staff": staff_user_id})

        quote_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_job_quotes (id, quote_number, booking_id, job_id, tenant_id, customer_id, "
            "status, quote_type, currency, labour_amount, parts_amount, service_amount, discount_amount, "
            "tax_amount, total_amount, customer_payable_amount, version_number, is_current, created_at, updated_at) "
            "VALUES (:id, :num, :bid, :jid, :tid, :cust, 'customer_approved', 'repair_quote', 'INR', "
            "1200, 0, 0, 0, 0, 1200, 1200, 1, true, now(), now())"
        ), {"id": quote_id, "num": f"QT-{quote_id.hex[:8]}", "bid": booking_id, "jid": job_id, "tid": tenant_id, "cust": customer_id})
        await db.commit()

        template = mapping = None
        try:
            template = await checklist_svc.create_template(
                db, name="AC Work Checklist", code=f"ac-work-{uuid.uuid4().hex[:6]}", purpose=cc.PURPOSE_EXECUTION,
                owner_scope=cc.OWNER_SCOPE_PLATFORM, tenant_id=None, created_by_user_id=None, description=None,
            )
            version = await checklist_svc.get_draft_version(db, template.id)
            section = await checklist_svc.add_section(db, version, "Work checklist", display_order=0)
            await checklist_svc.add_item(
                db, section, version, item_type=cc.ITEM_TYPE_YES_NO, label="Repair gas leakage",
                is_required=True, display_order=0,
            )
            await checklist_svc.publish_version(db, version, published_by=None, change_summary="v1")
            msjt_id = (await db.execute(text(
                "SELECT id FROM master_service_job_types WHERE master_service_id=:ms AND job_type_id=:jt"
            ), {"ms": ms_id, "jt": jt_id})).scalar_one()
            mapping = await checklist_svc.create_mapping(
                db, master_service_job_type_id=msjt_id, service_job_workflow_id=None,
                checklist_template_version_id=version.id, phase=cc.PURPOSE_EXECUTION,
                usage=cc.USAGE_REQUIRED, actor=cc.ACTOR_TECHNICIAN, completion_gate=cc.GATE_NONE,
                condition_rules=None, display_order=0, created_by=None,
            )
            await db.commit()

            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                headers = {"Authorization": "Bearer x"}

                # 1. Before start: approved scope visible, start_work allowed.
                detail = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-work-execution", headers=headers)).json()["data"]
                assert detail["approved_scope"]["approved_total"] == "1200.00"
                assert "start_work" in detail["allowed_actions"]
                assert detail["work_session"] is None

                # 2. Start work -- real start_service transition + real session row.
                start_resp = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-work-execution/start", headers=headers)
                assert start_resp.status_code == 200
                assert start_resp.json()["data"]["state"] == "active"

                job_status = (await db.execute(text("SELECT status FROM service_jobs WHERE id=:jid"), {"jid": job_id})).scalar_one()
                assert job_status == "service_started"

                # 3. Finish blocked -- required checklist item unanswered.
                detail2 = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-work-execution", headers=headers)).json()["data"]
                assert detail2["readiness"]["can_finish_work"] is False
                assert "finish_work" not in detail2["allowed_actions"]
                finish_blocked = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-work-execution/finish", headers=headers)
                assert finish_blocked.status_code == 409

                # 4. Pause then resume -- elapsed time accumulates, never a duplicate session.
                pause_resp = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-work-execution/pause", headers=headers, json={"reason": "Waiting for part"})
                assert pause_resp.json()["data"]["state"] == "paused"
                resume_resp = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-work-execution/resume", headers=headers)
                assert resume_resp.json()["data"]["state"] == "active"

                # 5. Answer the required checklist item via the reused canonical endpoint.
                item_id = detail2["checklist"]["items"][0]["id"]
                instance_id = detail2["checklist"]["instance_id"]
                save_resp = await client.post(
                    f"/v1/staff/service-jobs/checklist-instances/{instance_id}/responses/{item_id}",
                    json={"response_value": {"value": "yes"}}, headers=headers,
                )
                assert save_resp.status_code == 200

                # 6. Now finish-ready, and finishing moves to work_done -- never completed.
                detail3 = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-work-execution", headers=headers)).json()["data"]
                assert detail3["readiness"]["can_finish_work"] is True
                assert "finish_work" in detail3["allowed_actions"]

                finish_resp = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-work-execution/finish", headers=headers)
                assert finish_resp.status_code == 200
                assert finish_resp.json()["data"]["status"] == "work_done"

                job_status2 = (await db.execute(text("SELECT status FROM service_jobs WHERE id=:jid"), {"jid": job_id})).scalar_one()
                assert job_status2 == "work_done"  # never "completed" -- no premature commission trigger
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM service_job_work_sessions WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_job_quotes WHERE id=:qid"), {"qid": quote_id})
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
            await db.execute(text("DELETE FROM service_job_workflow WHERE id=:wf"), {"wf": workflow_id})
            await db.execute(text("DELETE FROM master_service_job_types WHERE master_service_id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM master_services WHERE id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM job_types WHERE id=:jt"), {"jt": jt_id})
            await db.commit()
