"""Technician mobile app Phase O: GET /v1/staff/service-jobs/{job_id}/mobile-direct-payment
+ declare/remind/finalize, composed over the EXISTING canonical
DirectPaymentsService and HomeServiceJobExecutionService.complete_job.
Follows the same live-DB pattern as the Phase K/L/M/N projection tests.
Proves finalize (a) is blocked until completion proof + handover +
payment reconciliation all pass, (b) succeeds exactly once, (c) never
leaves the job anywhere but "completed", and (d) never calls the
finalization action a second time (idempotency guard already in complete_job).
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
async def test_direct_payment_unknown_job_id_fails_closed_with_404():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-direct-payment", headers={"Authorization": "Bearer x"})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_direct_payment_requires_tenant_context():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
        tenant_id=None, full_name="No Tenant", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-direct-payment", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_direct_payment_denies_customer_role():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()), email="customer@serviceos.local", role="customer",
        tenant_id=None, full_name="Demo Customer", is_verified=True,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/v1/staff/service-jobs/{uuid.uuid4()}/mobile-direct-payment", headers={"Authorization": "Bearer x"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_direct_payment_full_lifecycle_live():
    """Real job at work_done with a submitted CompletionProof, a real
    approved current quote, and no unresolved parts. Proves: blocked before
    handover acknowledgment/payment declaration, declare records a real
    ServicePaymentRecord with the backend-resolved expected amount, finalize
    is blocked until customer confirmation, and finalize succeeds exactly
    once -- transitioning the job to "completed" through the existing
    complete_job action (commission trigger untouched/reused, not re-tested
    here since it's already covered elsewhere)."""
    from app.database import get_session_factory, init_db

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
            "INSERT INTO tenants (id, tenant_name, business_name, slug, tenant_code, status, vertical, created_at, updated_at) "
            "VALUES (:id, 'Mobile Flow Tenant', 'Mobile Flow Co', :slug, :code, 'active', 'home_services', now(), now())"
        ), {"id": tenant_id, "slug": f"mobile-{tenant_id.hex[:8]}", "code": f"MF{tenant_id.hex[:6]}"})
        await db.execute(text(
            "INSERT INTO tenant_billing (id, tenant_id, billing_cycle, subscription_status, credit_balance, "
            "security_deposit_paid, security_deposit_amount, vertical_key, created_at, updated_at) "
            "VALUES (:id, :tid, 'monthly', 'active', 500, false, 0, 'home_services', now(), now())"
        ), {"id": uuid.uuid4(), "tid": tenant_id})

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
        pricing_rule_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_pricing_rules (id, master_service_id, category_id, job_type, job_type_id, "
            "pricing_model, base_price, visit_fee, platform_fee_percent, commission_percent, tax_percent, "
            "priority, is_active, source, completed_job_deduction_credits, created_at, updated_at) "
            "VALUES (:id, :ms, :cat, 'repair', :jt, 'fixed', 0, 0, 0, 0, 0, 100, true, 'test', 7, now(), now())"
        ), {"id": pricing_rule_id, "ms": ms_id, "cat": cat_id, "jt": jt_id})

        booking_id, job_id = uuid.uuid4(), uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_bookings (id, booking_number, draft_id, category_id, offering_id, "
            "job_type_id, customer_id, status, assignment_status, price_snapshot, created_at, updated_at) "
            "VALUES (:id, :num, :did, :cat, :off, :jt, :cust, 'pending_assignment', 'unassigned', '{}'::jsonb, now(), now())"
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
            "tax_amount, total_amount, customer_payable_amount, version_number, is_current, approved_at, created_at, updated_at) "
            "VALUES (:id, :num, :bid, :jid, :tid, :cust, 'customer_approved', 'repair_quote', 'INR', "
            "1200, 0, 0, 0, 0, 1200, 1200, 1, true, now(), now(), now())"
        ), {"id": quote_id, "num": f"QT-{quote_id.hex[:8]}", "bid": booking_id, "jid": job_id, "tid": tenant_id, "cust": customer_id})

        proof_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO service_job_completion_proofs (id, job_id, tenant_id, staff_member_id, status, "
            "resolution_summary, handover_status, created_at, updated_at) "
            "VALUES (:id, :jid, :tid, :staff, 'submitted', 'Gas leakage repaired.', 'not_requested', now(), now())"
        ), {"id": proof_id, "jid": job_id, "tid": tenant_id, "staff": staff_user_id})
        await db.commit()

        try:
            app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                headers = {"Authorization": "Bearer x"}

                # 1. Blocked: handover not acknowledged, payment not declared.
                detail = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment", headers=headers)).json()["data"]
                assert detail["amount"]["expected_amount"] == "1200.00"
                assert set(detail["closure_readiness"]["blockers"]) == {"CUSTOMER_HANDOVER_NOT_ACKNOWLEDGED", "PAYMENT_NOT_DECLARED"}
                finalize_blocked = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/finalize", headers=headers)
                assert finalize_blocked.status_code == 409

                # 2. Declare the direct payment -- real ServicePaymentRecord, backend-resolved amount.
                declare_resp = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/declare", headers=headers,
                    json={"amount": "1200.00", "method": "onsite_cash"},
                )
                assert declare_resp.status_code == 200
                assert declare_resp.json()["data"]["status"] == "awaiting_customer"

                # 3. The real native-app contract is now complete: staff requests
                #    handover, then the authenticated owning customer acknowledges
                #    it and confirms the provider's direct-payment declaration.
                handover_request = await client.post(
                    f"/v1/staff/service-jobs/{job_id}/mobile-completion-proof/request-handover",
                    headers=headers,
                )
                assert handover_request.status_code == 200

                app.dependency_overrides[get_current_user] = lambda: UserContext(
                    user_id=str(customer_id), email="customer@serviceos.local", role="customer",
                    tenant_id=None, full_name="Demo Customer", is_verified=True,
                )
                handover = await client.get(f"/v1/customer/service-jobs/{job_id}/handover", headers=headers)
                assert handover.status_code == 200
                assert handover.json()["data"]["can_acknowledge"] is True

                acknowledged = await client.post(f"/v1/customer/service-jobs/{job_id}/acknowledge-handover", headers=headers)
                assert acknowledged.status_code == 200
                assert acknowledged.json()["data"]["handover_status"] == "acknowledged"

                payments = await client.get("/v1/customer/direct-payments", headers=headers)
                payment = next(row for row in payments.json()["data"]["items"] if row["job_id"] == str(job_id))
                assert payment["booking_id"] == str(booking_id)
                assert payment["status"] == "awaiting_customer"
                assert payment["customer_action"] is None
                confirmed = await client.post(f"/v1/customer/direct-payments/{payment['payment_id']}/confirm", headers=headers)
                assert confirmed.status_code == 200
                assert confirmed.json()["data"]["status"] == "confirmed"

                # 4. Now finalize succeeds -- job transitions to completed exactly once.
                app.dependency_overrides[get_current_user] = lambda: make_technician_context(str(tenant_id), user_id=str(staff_user_id))
                detail2 = (await client.get(f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment", headers=headers)).json()["data"]
                assert detail2["closure_readiness"]["can_finalize"] is True

                finalize_resp = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/finalize", headers=headers)
                assert finalize_resp.status_code == 200
                assert finalize_resp.json()["data"]["status"] == "completed"

                ledger = (await db.execute(text(
                    "SELECT credit_delta, balance_before, balance_after FROM usage_credit_ledger "
                    "WHERE job_id=:jid AND event_type='completed_job_deduction'"
                ), {"jid": job_id})).mappings().all()
                assert len(ledger) == 1
                assert ledger[0]["credit_delta"] < 0
                assert ledger[0]["balance_before"] == 500
                assert ledger[0]["balance_after"] == 500 + ledger[0]["credit_delta"]
                wallet_balance = (await db.execute(text(
                    "SELECT credit_balance FROM tenant_billing WHERE tenant_id=:tid"
                ), {"tid": tenant_id})).scalar_one()
                assert wallet_balance == ledger[0]["balance_after"]

                # 5. A second finalize attempt is rejected, not double-fired.
                finalize_again = await client.post(f"/v1/staff/service-jobs/{job_id}/mobile-direct-payment/finalize", headers=headers)
                assert finalize_again.status_code >= 400
                ledger_count = (await db.execute(text(
                    "SELECT count(*) FROM usage_credit_ledger WHERE job_id=:jid AND event_type='completed_job_deduction'"
                ), {"jid": job_id})).scalar_one()
                assert ledger_count == 1
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            await db.execute(text("DELETE FROM service_job_completion_proofs WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM usage_credit_ledger WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_payment_records WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_job_quotes WHERE id=:qid"), {"qid": quote_id})
            await db.execute(text("DELETE FROM service_job_execution_events WHERE job_id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_jobs WHERE id=:jid"), {"jid": job_id})
            await db.execute(text("DELETE FROM service_bookings WHERE id=:bid"), {"bid": booking_id})
            await db.execute(text("DELETE FROM master_service_job_types WHERE master_service_id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM service_pricing_rules WHERE id=:id"), {"id": pricing_rule_id})
            await db.execute(text("DELETE FROM master_services WHERE id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM job_types WHERE id=:jt"), {"jt": jt_id})
            await db.execute(text("DELETE FROM tenant_billing WHERE tenant_id=:tid"), {"tid": tenant_id})
            await db.execute(text("DELETE FROM tenants WHERE id=:tid"), {"tid": tenant_id})
            await db.commit()
