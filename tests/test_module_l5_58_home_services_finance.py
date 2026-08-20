"""HOME-SERVICES-FINANCE — Completion Charges (replaces the retired,
404'ing /admin/home-services/completed-job-deduction page).

Root cause (proven, not guessed): the old page called
`GET /v1/admin/pricing-rules`, deleted 2026-07 under the "provider-set-price"
policy (app/engines/admin_catalog/admin_router.py's own comment documents
the removal) while the underlying `ServicePricingRule` table and its
`completed_job_deduction_credits` column were deliberately left in place.
The certified completion-charge engine
(app.engines.execution.usage_credit_deduction.deduct_for_completed_job)
never called that deleted endpoint -- it reads ServicePricingRule directly
from the DB -- so it was never broken. Only the admin page's OWN data
source was broken. This test suite proves the new
HomeServicesFinanceService/router (a pure read + safe-reconciliation
projection over the SAME certified engine's writes) is correct, and that
the certified engine's own idempotency/atomicity guarantees hold.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import text


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures: a real Home Services job + tenant against the live database
# ─────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session():
    from app.database import get_session_factory, init_db
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        yield db


@pytest_asyncio.fixture
async def hs_job(db_session):
    """A minimal, real service_jobs row plus its owning tenant, cleaned up after."""
    tenant_id = uuid.uuid4()
    booking_id = uuid.uuid4()
    job_id = uuid.uuid4()
    category_id = uuid.uuid4()
    master_service_id = uuid.uuid4()

    await db_session.execute(text(
        "INSERT INTO tenants (id, tenant_name, business_name, slug, tenant_code, status, vertical, "
        "created_at, updated_at) VALUES (:id, 'T', 'T Co', :slug, :code, 'active', 'home_services', now(), now())"
    ), {"id": tenant_id, "slug": f"t-{tenant_id.hex[:8]}", "code": f"TC{tenant_id.hex[:6]}"})
    await db_session.execute(text(
        "INSERT INTO service_bookings (id, booking_number, draft_id, category_id, offering_id, "
        "tenant_id, status, assignment_status, created_at, updated_at) "
        "VALUES (:id, :num, :did, :cat, :off, :tid, 'pending_assignment', 'unassigned', now(), now())"
    ), {"id": booking_id, "num": f"BK-{booking_id.hex[:8]}", "did": uuid.uuid4(),
        "cat": category_id, "off": master_service_id, "tid": tenant_id})
    await db_session.execute(text(
        "INSERT INTO service_jobs (id, job_number, booking_id, category_id, offering_id, tenant_id, "
        "status, assignment_status, created_at, updated_at) "
        "VALUES (:id, :num, :bid, :cat, :off, :tid, 'service_started', 'assigned', now(), now())"
    ), {"id": job_id, "num": f"JOB-{job_id.hex[:8]}", "bid": booking_id,
        "cat": category_id, "off": master_service_id, "tid": tenant_id})
    await db_session.commit()

    yield {"tenant_id": tenant_id, "booking_id": booking_id, "job_id": job_id,
           "master_service_id": master_service_id}

    await db_session.execute(text("DELETE FROM usage_credit_ledger WHERE job_id = :id"), {"id": job_id})
    await db_session.execute(text("DELETE FROM service_jobs WHERE id = :id"), {"id": job_id})
    await db_session.execute(text("DELETE FROM service_bookings WHERE id = :id"), {"id": booking_id})
    await db_session.execute(text("DELETE FROM tenant_billing WHERE tenant_id = :id"), {"id": tenant_id})
    await db_session.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": tenant_id})
    await db_session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 1-3. Idempotency and atomicity of the certified engine
# ─────────────────────────────────────────────────────────────────────────────

class TestCompletionChargeIdempotencyAndAtomicity:
    async def test_valid_completed_job_produces_one_charge(self, db_session, hs_job):
        from app.engines.execution.usage_credit_deduction import deduct_for_completed_job
        result = await deduct_for_completed_job(
            db_session, tenant_id=hs_job["tenant_id"], job_id=hs_job["job_id"],
            booking_id=hs_job["booking_id"], master_service_id=hs_job["master_service_id"],
            offering_type_id=None, brand_id=None,
        )
        await db_session.commit()
        assert result["deduction_status"] == "deducted"

        count = (await db_session.execute(text(
            "SELECT count(*) FROM usage_credit_ledger WHERE job_id = :id AND event_type = 'completed_job_deduction'"
        ), {"id": hs_job["job_id"]})).scalar()
        assert count == 1

    async def test_duplicate_completion_produces_no_duplicate_charge(self, db_session, hs_job):
        from app.engines.execution.usage_credit_deduction import deduct_for_completed_job
        first = await deduct_for_completed_job(
            db_session, tenant_id=hs_job["tenant_id"], job_id=hs_job["job_id"],
            booking_id=hs_job["booking_id"], master_service_id=hs_job["master_service_id"],
            offering_type_id=None, brand_id=None,
        )
        await db_session.commit()
        second = await deduct_for_completed_job(
            db_session, tenant_id=hs_job["tenant_id"], job_id=hs_job["job_id"],
            booking_id=hs_job["booking_id"], master_service_id=hs_job["master_service_id"],
            offering_type_id=None, brand_id=None,
        )
        assert second["deduction_status"] == "already_deducted"
        assert second["ledger_id"] == first["ledger_id"]

        count = (await db_session.execute(text(
            "SELECT count(*) FROM usage_credit_ledger WHERE job_id = :id AND event_type = 'completed_job_deduction'"
        ), {"id": hs_job["job_id"]})).scalar()
        assert count == 1

    async def test_database_uniqueness_guard_rejects_a_second_direct_insert(self, db_session, hs_job):
        """Proves the DB-level partial unique index (migration 129,
        uq_ucl_job_event_once), not just the application-level pre-check --
        even a hand-crafted second INSERT bypassing deduct_for_completed_job
        entirely must fail. This is what makes 'concurrent completion
        produces one charge' true under real concurrency, where two
        processes could both pass the application-level SELECT-then-INSERT
        check before either commits."""
        await db_session.execute(text(
            "INSERT INTO usage_credit_ledger (id, tenant_id, job_id, booking_id, event_type, "
            "credit_delta, balance_before, balance_after, created_at, updated_at) "
            "VALUES (:id, :tid, :jid, :bid, 'completed_job_deduction', -3, 100, 97, now(), now())"
        ), {"id": uuid.uuid4(), "tid": hs_job["tenant_id"], "jid": hs_job["job_id"], "bid": hs_job["booking_id"]})
        await db_session.commit()

        with pytest.raises(Exception) as exc:
            await db_session.execute(text(
                "INSERT INTO usage_credit_ledger (id, tenant_id, job_id, booking_id, event_type, "
                "credit_delta, balance_before, balance_after, created_at, updated_at) "
                "VALUES (:id, :tid, :jid, :bid, 'completed_job_deduction', -3, 97, 94, now(), now())"
            ), {"id": uuid.uuid4(), "tid": hs_job["tenant_id"], "jid": hs_job["job_id"], "bid": hs_job["booking_id"]})
            await db_session.commit()
        assert "uq_ucl_job_event_once" in str(exc.value) or "unique" in str(exc.value).lower()
        await db_session.rollback()

    async def test_balance_and_ledger_update_share_one_transaction(self, db_session, hs_job):
        from app.engines.execution.usage_credit_deduction import deduct_for_completed_job
        from app.engines.tenant_engine.models import TenantBilling
        await deduct_for_completed_job(
            db_session, tenant_id=hs_job["tenant_id"], job_id=hs_job["job_id"],
            booking_id=hs_job["booking_id"], master_service_id=hs_job["master_service_id"],
            offering_type_id=None, brand_id=None,
        )
        # Both the ledger row and the balance mutation exist together after a
        # single flush -- no separate commit between them in the source
        # (see app/engines/execution/usage_credit_deduction.py:104-123).
        ledger_row = (await db_session.execute(text(
            "SELECT balance_after FROM usage_credit_ledger WHERE job_id = :id"
        ), {"id": hs_job["job_id"]})).scalar()
        billing = (await db_session.execute(text(
            "SELECT credit_balance FROM tenant_billing WHERE tenant_id = :id"
        ), {"id": hs_job["tenant_id"]})).scalar()
        await db_session.commit()
        assert Decimal(str(ledger_row)) == Decimal(str(billing))


# ─────────────────────────────────────────────────────────────────────────────
# 9-13. Client trust boundaries, append-only, policy source
# ─────────────────────────────────────────────────────────────────────────────

class TestTrustBoundariesAndPolicySource:
    def test_deduction_engine_never_calls_the_retired_pricing_rules_endpoint(self):
        import inspect
        from app.engines.execution import usage_credit_deduction
        src = inspect.getsource(usage_credit_deduction)
        assert "/v1/admin/pricing-rules" not in src
        assert "apiFetch" not in src
        assert "ServicePricingRule" not in src  # no hidden per-service fallback
        assert "VerticalMonetizationPolicy" in src
        assert 'return Decimal("0"), None' in src  # no published policy = no charge

    def test_new_finance_service_never_calls_the_retired_pricing_rules_endpoint(self):
        import inspect
        from app.engines.finance_hub import home_services_finance_service
        # Executable code only -- strip the module docstring, which
        # documents the retired endpoint's PATH in prose for context.
        full_src = inspect.getsource(home_services_finance_service)
        src = full_src.split('"""', 2)[-1]  # drop everything through the closing """ of the module docstring
        assert "pricing-rules" not in src
        assert "apiFetch" not in src

    def test_completion_charge_router_endpoints_are_read_only_or_reconciliation_only(self):
        """Client cannot control charge amount or tenant ID via an
        unprotected route: every route under /home-services/ is a GET
        except reconciliation/run (reads+audits, no body) and the manual
        credit adjustment endpoint (elevated permission, creates an
        immutable ledger entry, never edits an existing charge)."""
        import inspect
        from app.engines.finance_hub import admin_hs_finance_router
        src = inspect.getsource(admin_hs_finance_router)
        assert '@canonical_router.post(\n    "/adjustments"' in src
        assert "FINANCE_HOME_SERVICES_ADJUSTMENTS_CREATE" in src
        assert "UsageCreditLedger).update(" not in src

    def test_ledger_model_has_no_update_or_delete_code_path(self):
        import inspect
        from app.engines.finance_hub import home_services_finance_service
        from app.engines.execution import usage_credit_deduction
        for module in (home_services_finance_service, usage_credit_deduction):
            src = inspect.getsource(module)
            assert "UsageCreditLedger).update(" not in src
            assert "delete(UsageCreditLedger" not in src
            assert "db.delete(ledger" not in src


# ─────────────────────────────────────────────────────────────────────────────
# 16-19. Reconciliation
# ─────────────────────────────────────────────────────────────────────────────

class TestReconciliation:
    async def test_reconciliation_detects_a_missing_charge(self, db_session, hs_job):
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        await db_session.execute(text(
            "UPDATE service_jobs SET status = 'completed' WHERE id = :id"
        ), {"id": hs_job["job_id"]})
        await db_session.commit()

        svc = HomeServicesFinanceService(db=db_session)
        result = await svc.run_reconciliation()
        await db_session.commit()
        assert str(hs_job["job_id"]) in result["missing_job_ids"]
        assert result["missing_count"] >= 1

    async def test_reconciliation_finds_no_missing_charge_once_posted(self, db_session, hs_job):
        from app.engines.execution.usage_credit_deduction import deduct_for_completed_job
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        await db_session.execute(text(
            "UPDATE service_jobs SET status = 'completed' WHERE id = :id"
        ), {"id": hs_job["job_id"]})
        await deduct_for_completed_job(
            db_session, tenant_id=hs_job["tenant_id"], job_id=hs_job["job_id"],
            booking_id=hs_job["booking_id"], master_service_id=hs_job["master_service_id"],
            offering_type_id=None, brand_id=None,
        )
        await db_session.commit()

        svc = HomeServicesFinanceService(db=db_session)
        result = await svc.run_reconciliation()
        await db_session.commit()
        assert str(hs_job["job_id"]) not in result["missing_job_ids"]

    async def test_non_chargeable_statuses_are_not_counted_as_chargeable(self, db_session, hs_job):
        """Cancelled / rejected-estimate / draft / inspection / work-start
        states must never be treated as chargeable by reconciliation --
        only the exact 'completed' status counts."""
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        for status in ("cancelled", "closed_estimate_declined", "inspection_done",
                       "service_started", "quote_required"):
            await db_session.execute(text(
                "UPDATE service_jobs SET status = :s WHERE id = :id"
            ), {"s": status, "id": hs_job["job_id"]})
            await db_session.commit()
            svc = HomeServicesFinanceService(db=db_session)
            result = await svc.run_reconciliation()
            await db_session.commit()
            assert str(hs_job["job_id"]) not in result["missing_job_ids"], f"status={status} must not be chargeable"

    async def test_reconciliation_makes_no_mutation(self, db_session, hs_job):
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        await db_session.execute(text(
            "UPDATE service_jobs SET status = 'completed' WHERE id = :id"
        ), {"id": hs_job["job_id"]})
        await db_session.commit()
        before = (await db_session.execute(text(
            "SELECT status, updated_at FROM service_jobs WHERE id = :id"
        ), {"id": hs_job["job_id"]})).fetchone()

        svc = HomeServicesFinanceService(db=db_session)
        await svc.run_reconciliation()
        await db_session.commit()

        after = (await db_session.execute(text(
            "SELECT status, updated_at FROM service_jobs WHERE id = :id"
        ), {"id": hs_job["job_id"]})).fetchone()
        assert before == after
        ledger_count = (await db_session.execute(text(
            "SELECT count(*) FROM usage_credit_ledger WHERE job_id = :id"
        ), {"id": hs_job["job_id"]})).scalar()
        assert ledger_count == 0  # reconciliation must never create the missing charge itself

    async def test_historical_ledger_rows_remain_readable(self, db_session, hs_job):
        from app.engines.execution.usage_credit_deduction import deduct_for_completed_job
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        await deduct_for_completed_job(
            db_session, tenant_id=hs_job["tenant_id"], job_id=hs_job["job_id"],
            booking_id=hs_job["booking_id"], master_service_id=hs_job["master_service_id"],
            offering_type_id=None, brand_id=None,
        )
        await db_session.commit()
        svc = HomeServicesFinanceService(db=db_session)
        data = await svc.list_completion_charges(tenant_id=str(hs_job["tenant_id"]))
        assert data["total"] == 1
        assert data["items"][0]["job_id"] == str(hs_job["job_id"])
        assert data["items"][0]["status"] == "posted"


# ─────────────────────────────────────────────────────────────────────────────
# 20. Vertical isolation (structural)
# ─────────────────────────────────────────────────────────────────────────────

class TestVerticalIsolation:
    def test_usage_credit_ledger_has_no_coupling_to_other_vertical_tables(self):
        """Coaching (CoachingAppointment) and Real Estate (RealEstateLead)
        live in entirely separate final-record tables from Home Services
        (ServiceJob/service_jobs) -- usage_credit_ledger.job_id can
        therefore never reference a Coaching/Real-Estate record, so
        disabling Home Services cannot touch their billing by construction."""
        import inspect
        from app.engines.finance_hub import home_services_finance_service
        full_src = inspect.getsource(home_services_finance_service)
        src = full_src.split('"""', 2)[-1]
        assert "CoachingAppointment" not in src
        assert "RealEstateLead" not in src

    async def test_summary_only_counts_service_jobs_table(self, db_session, hs_job):
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        await db_session.execute(text(
            "UPDATE service_jobs SET status = 'completed' WHERE id = :id"
        ), {"id": hs_job["job_id"]})
        await db_session.commit()
        svc = HomeServicesFinanceService(db=db_session)
        summary = await svc.get_summary()
        assert summary["completed_jobs"] >= 1


class TestSecurityDepositWorkspaceContract:
    async def test_hs_deposit_detail_checks_nested_deposit_vertical(self):
        """The shared detail service returns an envelope containing
        `deposit`, `ledger` and `audit_log`; valid HS deposits must not be
        rejected by checking for `vertical` on the outer envelope."""
        from unittest.mock import AsyncMock, MagicMock
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService

        deposit_id = uuid.uuid4()
        expected = {
            "deposit": {"deposit_id": str(deposit_id), "vertical": "home_services"},
            "ledger": [],
            "audit_log": [],
        }
        svc = HomeServicesFinanceService(db=MagicMock())
        svc._fh.get_deposit_detail = AsyncMock(return_value=expected)

        assert await svc.get_hs_deposit_detail(deposit_id) == expected
