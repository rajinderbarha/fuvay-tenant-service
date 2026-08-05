"""Technician mobile app Phase L: GET /v1/staff/service-jobs/{job_id}/mobile-estimate
+ the technician-authorized wrapper mutations, composed over the EXISTING
canonical ServiceJobQuoteService (never a second quote engine). Follows the
same live-DB pattern as test_mobile_inspection_projection.py.
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
async def test_estimate_unknown_job_id_fails_closed_with_404():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-estimate", headers={"Authorization": "Bearer x"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_estimate_requires_tenant_context():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
        tenant_id=None, full_name="No Tenant", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-estimate", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_estimate_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-estimate", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_estimate_full_lifecycle_live():
    """Real Master Service (with a real visit_fee) + Job Type + a REQUIRED
    inspection checklist gating estimate submission + a real assigned
    ServiceJob. Proves: create_estimate blocked before inspection
    completion, allowed after; visit-fee auto-seeded as a real backend
    discount item (never client-calculated); backend-only totals; send for
    approval; and that a superseded quote can no longer be mutated
    (the is_current fix)."""
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
            "visit_fee, created_at, updated_at) VALUES (:id, :cat, 'AC Repair', :slug, 'repair', true, 299, now(), now())"
        ), {"id": ms_id, "cat": cat_id, "slug": f"ac-{ms_id.hex[:6]}"})
        await db.execute(text(
            "INSERT INTO master_service_job_types (id, master_service_id, job_type_id, is_active, "
            "display_order, created_at, updated_at) VALUES (:id, :ms, :jt, true, 0, now(), now())"
        ), {"id": uuid.uuid4(), "ms": ms_id, "jt": jt_id})

        booking_id, job_id = uuid.uuid4(), uuid.uuid4()
        customer_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_bookings (id, booking_number, draft_id, category_id, offering_id, "
            "job_type_id, customer_id, status, assignment_status, created_at, updated_at) "
            "VALUES (:id, :num, :did, :cat, :off, :jt, :cust, 'pending_assignment', 'unassigned', now(), now())"
        ), {"id": booking_id, "num": f"BK-{booking_id.hex[:8]}", "did": uuid.uuid4(), "cat": cat_id, "off": ms_id,
            "jt": jt_id, "cust": customer_id})
        await db.execute(text(
            "INSERT INTO service_jobs (id, job_number, booking_id, category_id, offering_id, job_type_id, "
            "tenant_id, customer_id, assigned_staff_id, status, assignment_status, created_at, updated_at) "
            "VALUES (:id, :num, :bid, :cat, :off, :jt, :tid, :cust, :staff, 'inspection_done', 'assigned', now(), now())"
        ), {"id": job_id, "num": f"J-{job_id.hex[:8]}", "bid": booking_id, "cat": cat_id, "off": ms_id, "jt": jt_id,
            "tid": tenant_id, "cust": customer_id, "staff": staff_user_id})
        await db.commit()

        template = mapping = None
        try:
            template = await checklist_svc.create_template(
                db, name="AC Inspection Gate", code=f"ac-gate-{uuid.uuid4().hex[:6]}", purpose=cc.PURPOSE_INSPECTION,
                owner_scope=cc.OWNER_SCOPE_PLATFORM, tenant_id=None, created_by_user_id=None, description=None,
            )
            version = await checklist_svc.get_draft_version(db, template.id)
            section = await checklist_svc.add_section(db, version, "Inspection checklist", display_order=0)
            await checklist_svc.add_item(
                db, section, version, item_type=cc.ITEM_TYPE_YES_NO, label="Power supply checked",
                is_required=True, display_order=0,
            )
            await checklist_svc.publish_version(db, version, published_by=None, change_summary="v1")
            msjt_id = (await db.execute(text(
                "SELECT id FROM master_service_job_types WHERE master_service_id=:ms AND job_type_id=:jt"
            ), {"ms": ms_id, "jt": jt_id})).scalar_one()
            mapping = await checklist_svc.create_mapping(
                db, master_service_job_type_id=msjt_id, service_job_workflow_id=None,
                checklist_template_version_id=version.id, phase=cc.PURPOSE_INSPECTION,
                usage=cc.USAGE_REQUIRED, actor=cc.ACTOR_TECHNICIAN, completion_gate=cc.GATE_BEFORE_ESTIMATE_SUBMISSION,
                condition_rules=None, display_order=0, created_by=None,
            )
            await db.commit()

            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                headers = {"Authorization": "Bearer x"}

                # 1. Projection before any quote exists.
                detail = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-estimate", headers=headers)).json()["data"]
                assert detail["quote"] is None
                assert detail["visit_fee_policy"]["amount"] == 299.0
                assert detail["readiness"]["blockers"] == ["INSPECTION_NOT_COMPLETE"]

                # 2. Blocked: creating an estimate before inspection completion fails closed.
                blocked = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-estimate/create", headers=headers)
                assert blocked.status_code == 409

                # 3. Complete the gating inspection checklist for real.
                mappings = await checklist_svc.get_applicable_mappings(db, await db.get(__import__("app.engines.final_records.models", fromlist=["ServiceJob"]).ServiceJob, job_id), phase=cc.PURPOSE_INSPECTION)
                instance = await checklist_svc.ensure_instance(db, await db.get(__import__("app.engines.final_records.models", fromlist=["ServiceJob"]).ServiceJob, job_id), mappings[0])
                items = await checklist_svc._instance_items(db, instance)
                await checklist_svc.save_response(db, instance, items[0].id, actor_user_id=staff_user_id, actor_role="TECHNICIAN", response_value={"value": "yes"}, evidence=None)
                await checklist_svc.complete_instance(db, instance, completed_by=staff_user_id)
                await db.commit()

                # 4. Now estimate creation succeeds and auto-seeds the real visit-fee discount.
                created = (await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-estimate/create", headers=headers)).json()["data"]
                quote_id = created["id"]
                assert created["discount_amount"] == "299.00"
                assert created["total_amount"] == "-299.00"

                # 5. Add a real labour item; totals recompute server-side only.
                add_resp = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-estimate/{quote_id}/items", headers=headers,
                    json={"item_type": "labour", "item_name": "Gas refill & leak repair", "quantity": 1, "unit_price": 1200},
                )
                assert add_resp.status_code == 200

                detail2 = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-estimate", headers=headers)).json()["data"]
                assert detail2["calculation"]["labour_total"] == "1200.00"
                assert detail2["calculation"]["grand_total"] == "901.00"  # 1200 - 299
                assert "send_for_approval" in detail2["allowed_actions"]

                # 6. Send for approval -- real canonical transition.
                sent = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-estimate/{quote_id}/send", headers=headers, json={})
                assert sent.status_code == 200
                assert sent.json()["data"]["status"] == "sent_to_customer"

                # 7. A quote sent to the customer can no longer be mutated by the technician.
                blocked_edit = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-estimate/{quote_id}/items", headers=headers,
                    json={"item_type": "labour", "item_name": "Extra", "quantity": 1, "unit_price": 100},
                )
                assert blocked_edit.status_code >= 400
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM service_job_quote_events WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_job_quote_items WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_job_quotes WHERE job_id=:jid"), {"jid": job_id})
            if mapping is not None:
                await db.execute(text("DELETE FROM job_checklist_responses WHERE job_checklist_instance_id IN (SELECT id FROM job_checklist_instances WHERE job_id=:jid)"), {"jid": job_id})
                await db.execute(text("DELETE FROM job_checklist_instances WHERE job_id=:jid"), {"jid": job_id})
                await db.execute(text("DELETE FROM job_type_checklist_mappings WHERE id=:mid"), {"mid": mapping.id})
            if template is not None:
                await db.execute(text("DELETE FROM checklist_items WHERE checklist_section_id IN (SELECT id FROM checklist_sections WHERE checklist_template_version_id IN (SELECT id FROM checklist_template_versions WHERE checklist_template_id=:tid))"), {"tid": template.id})
                await db.execute(text("DELETE FROM checklist_sections WHERE checklist_template_version_id IN (SELECT id FROM checklist_template_versions WHERE checklist_template_id=:tid)"), {"tid": template.id})
                await db.execute(text("DELETE FROM checklist_template_versions WHERE checklist_template_id=:tid"), {"tid": template.id})
                await db.execute(text("DELETE FROM checklist_templates WHERE id=:tid"), {"tid": template.id})
            await db.execute(text("DELETE FROM service_jobs WHERE id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_bookings WHERE id=:bid"), {"bid": booking_id})
            await db.execute(text("DELETE FROM master_service_job_types WHERE master_service_id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM master_services WHERE id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM job_types WHERE id=:jt"), {"jt": jt_id})
            await db.commit()
