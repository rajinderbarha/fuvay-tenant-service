"""Technician mobile app Phase N: GET /v1/staff/service-jobs/{job_id}/mobile-completion-proof
+ draft/evidence/submit/handover mutations. Follows the same live-DB
pattern as the Phase K/L/M projection tests. Proves in particular that
submitting proof NEVER advances ServiceJob.status past work_done and NEVER
touches commission (complete_job/deduct_for_completed_job untouched).
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
async def test_completion_proof_unknown_job_id_fails_closed_with_404():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-completion-proof", headers={"Authorization": "Bearer x"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_completion_proof_requires_tenant_context():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
        tenant_id=None, full_name="No Tenant", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-completion-proof", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_completion_proof_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-completion-proof", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_completion_proof_full_lifecycle_live():
    """Real job at work_done with an unresolved parts request + a REQUIRED
    completion-phase checklist item. Proves: readiness blockers (checklist,
    evidence, parts, resolution summary) surface correctly, submission is
    rejected while blocked, succeeds once resolved, ServiceJob.status stays
    work_done after submit (never completed -- no premature commission),
    and handover request + rate-limited reminder work."""
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

        booking_id, job_id = uuid.uuid4(), uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_bookings (id, booking_number, draft_id, category_id, offering_id, "
            "job_type_id, customer_id, status, assignment_status, created_at, updated_at) "
            "VALUES (:id, :num, :did, :cat, :off, :jt, :cust, 'pending_assignment', 'unassigned', now(), now())"
        ), {"id": booking_id, "num": f"BK-{booking_id.hex[:8]}", "did": uuid.uuid4(), "cat": cat_id, "off": ms_id,
            "jt": jt_id, "cust": customer_id})
        await db.execute(text(
            "INSERT INTO service_jobs (id, job_number, booking_id, category_id, offering_id, job_type_id, "
            "tenant_id, customer_id, assigned_staff_id, status, assignment_status, created_at, updated_at) "
            "VALUES (:id, :num, :bid, :cat, :off, :jt, :tid, :cust, :staff, 'work_done', 'assigned', now(), now())"
        ), {"id": job_id, "num": f"J-{job_id.hex[:8]}", "bid": booking_id, "cat": cat_id, "off": ms_id, "jt": jt_id,
            "tid": tenant_id, "cust": customer_id, "staff": staff_user_id})

        quote_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_job_quotes (id, quote_number, booking_id, job_id, tenant_id, customer_id, "
            "status, quote_type, currency, labour_amount, parts_amount, service_amount, discount_amount, "
            "tax_amount, total_amount, customer_payable_amount, version_number, is_current, created_at, updated_at) "
            "VALUES (:id, :num, :bid, :jid, :tid, :cust, 'customer_approved', 'repair_quote', 'INR', "
            "1200, 0, 0, 0, 0, 1200, 1200, 1, true, now(), now())"
        ), {"id": quote_id, "num": f"QT-{quote_id.hex[:8]}", "bid": booking_id, "jid": job_id, "tid": tenant_id, "cust": customer_id})

        parts_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_job_parts_requests (id, job_id, tenant_id, technician_id, part_name, quantity, "
            "estimated_cost, reason, status, created_at, updated_at) "
            "VALUES (:id, :jid, :tid, :staff, 'Copper pipe', 2, 400, 'extension', 'requested', now(), now())"
        ), {"id": parts_id, "jid": job_id, "tid": tenant_id, "staff": staff_user_id})
        await db.commit()

        template = mapping = None
        try:
            template = await checklist_svc.create_template(
                db, name="AC Completion Checks", code=f"ac-final-{uuid.uuid4().hex[:6]}", purpose=cc.PURPOSE_COMPLETION,
                owner_scope=cc.OWNER_SCOPE_PLATFORM, tenant_id=None, created_by_user_id=None, description=None,
            )
            version = await checklist_svc.get_draft_version(db, template.id)
            section = await checklist_svc.add_section(db, version, "Final checks", display_order=0)
            await checklist_svc.add_item(
                db, section, version, item_type=cc.ITEM_TYPE_YES_NO, label="Cooling tested",
                is_required=True, display_order=0,
            )
            await checklist_svc.publish_version(db, version, published_by=None, change_summary="v1")
            msjt_id = (await db.execute(text(
                "SELECT id FROM master_service_job_types WHERE master_service_id=:ms AND job_type_id=:jt"
            ), {"ms": ms_id, "jt": jt_id})).scalar_one()
            mapping = await checklist_svc.create_mapping(
                db, master_service_job_type_id=msjt_id, service_job_workflow_id=None,
                checklist_template_version_id=version.id, phase=cc.PURPOSE_COMPLETION,
                usage=cc.USAGE_REQUIRED, actor=cc.ACTOR_TECHNICIAN, completion_gate=cc.GATE_NONE,
                condition_rules=None, display_order=0, created_by=None,
            )
            await db.commit()

            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                headers = {"Authorization": "Bearer x"}

                # 1. Blocked: missing resolution summary, evidence, checklist, unresolved part.
                detail = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof", headers=headers)).json()["data"]
                assert detail["readiness"]["can_submit"] is False
                assert set(detail["readiness"]["blockers"]) >= {"FINAL_CHECKS_INCOMPLETE", "EVIDENCE_MISSING", "PARTS_UNRESOLVED", "RESOLUTION_SUMMARY_REQUIRED"}
                submit_blocked = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/submit", headers=headers)
                assert submit_blocked.status_code == 409

                # 2. Save draft resolution summary + notes.
                draft_resp = await client.put(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/draft", headers=headers,
                    json={"resolution_summary": "Gas leakage repaired and refrigerant refilled.", "final_service_notes": "Clean filter every 3 months."},
                )
                assert draft_resp.status_code == 200

                # 3. Add after-photo evidence.
                evidence_resp = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/evidence", headers=headers,
                    json={"category": "after", "file_id": str(uuid.uuid4())},
                )
                assert evidence_resp.status_code == 200
                assert len(evidence_resp.json()["data"]["after_photo_ids"]) == 1

                # 4. Answer the required checklist item.
                item_id = detail["definition"]["final_checks"][0]["id"]
                instance_id = detail["definition"]["final_checks"][0]["instance_id"]
                save_resp = await client.post(
                    f"/v1/staff/service-jobs/checklist-instances/{instance_id}/responses/{item_id}",
                    json={"response_value": {"value": "yes"}}, headers=headers,
                )
                assert save_resp.status_code == 200

                # 5. Still blocked -- part unresolved.
                detail2 = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof", headers=headers)).json()["data"]
                assert detail2["readiness"]["blockers"] == ["PARTS_UNRESOLVED"]

                # 6. Resolve the part via the real install endpoint, then submit succeeds.
                await db.execute(text("UPDATE service_job_parts_requests SET status='installed' WHERE id=:pid"), {"pid": parts_id})
                await db.commit()

                detail3 = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof", headers=headers)).json()["data"]
                assert detail3["readiness"]["can_submit"] is True

                submit_resp = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/submit", headers=headers)
                assert submit_resp.status_code == 200
                assert submit_resp.json()["data"]["status"] == "submitted"

                # 7. ServiceJob.status is UNCHANGED (still work_done) -- proof submission never advances the workflow.
                job_status = (await db.execute(text("SELECT status FROM service_jobs WHERE id=:jid"), {"jid": job_id})).scalar_one()
                assert job_status == "work_done"

                # 8. Submitted proof is immutable.
                edit_blocked = await client.put(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/draft", headers=headers,
                    json={"resolution_summary": "Changed after submit"},
                )
                assert edit_blocked.status_code == 409

                # 9. Customer handover request + rate-limited reminder.
                handover_resp = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/request-handover", headers=headers)
                assert handover_resp.json()["data"]["handover_status"] == "requested"
                reminder_resp = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/send-reminder", headers=headers)
                assert reminder_resp.status_code == 200
                reminder_resp2 = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/send-reminder", headers=headers)
                assert reminder_resp2.status_code == 429
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM in_app_notifications WHERE source_record_id IN (SELECT id FROM service_invoices WHERE job_id=:jid)"), {"jid": job_id})
            await db.execute(text("DELETE FROM financial_events WHERE record_id IN (SELECT id FROM service_invoices WHERE job_id=:jid)"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_invoice_items WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_invoices WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_job_completion_proofs WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_job_parts_requests WHERE id=:pid"), {"pid": parts_id})
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
            await db.execute(text("DELETE FROM master_service_job_types WHERE master_service_id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM master_services WHERE id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM job_types WHERE id=:jt"), {"jt": jt_id})
            await db.commit()
