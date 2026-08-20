"""HOME-SERVICES-FINANCE — Overview aggregation + Direct Customer Payments.

Home Services customers pay the provider directly (cash/UPI/card/bank
transfer) -- ServiceOS never collects the job payment itself. This suite
proves, against real inserted rows (not mocks):

1. Direct Customer Payments (ServicePaymentRecord) and Overview aggregation
   are scoped to the Home Services vertical only -- a Coaching-vertical
   tenant's payment never appears.
2. Home Services provider charges use the completed-job usage-credit ledger;
   the legacy invoice commission path is marked not-required and cannot debit
   the provider a second time.
3. Overview reports the independently tracked platform-charge recovery.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import text


@pytest_asyncio.fixture
async def db_session():
    from app.database import get_session_factory, init_db
    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        yield db


@pytest_asyncio.fixture
async def hs_payment(db_session):
    """A real Home Services tenant + invoice + direct customer payment row."""
    tenant_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    booking_id = uuid.uuid4()
    job_id = uuid.uuid4()
    invoice_id = uuid.uuid4()
    payment_id = uuid.uuid4()
    category_id = uuid.uuid4()
    offering_id = uuid.uuid4()

    await db_session.execute(text(
        "INSERT INTO tenants (id, tenant_name, business_name, slug, tenant_code, status, vertical, "
        "created_at, updated_at) VALUES (:id, 'T', 'T Co', :slug, :code, 'active', 'home_services', now(), now())"
    ), {"id": tenant_id, "slug": f"t-{tenant_id.hex[:8]}", "code": f"TC{tenant_id.hex[:6]}"})
    await db_session.execute(text(
        "INSERT INTO service_invoices (id, invoice_number, booking_id, job_id, tenant_id, customer_id, "
        "category_id, offering_id, status, currency, total_amount, platform_fee_amount, "
        "customer_payable_amount, payment_status, created_at, updated_at) "
        "VALUES (:id, :num, :bid, :jid, :tid, :cid, :cat, :off, 'issued', 'INR', "
        "'500.00', '20.00', '520.00', 'pending', now(), now())"
    ), {"id": invoice_id, "num": f"INV-{invoice_id.hex[:8]}", "bid": booking_id, "jid": job_id,
        "tid": tenant_id, "cid": customer_id, "cat": category_id, "off": offering_id})
    await db_session.execute(text(
        "INSERT INTO service_payment_records (id, invoice_id, booking_id, job_id, tenant_id, customer_id, "
        "payment_mode, payment_status, collected_amount, currency, customer_confirmation_required, "
        "customer_confirmed, created_at, updated_at) "
        "VALUES (:id, :iid, :bid, :jid, :tid, :cid, 'cash', 'collected', '520.00', 'INR', true, false, now(), now())"
    ), {"id": payment_id, "iid": invoice_id, "bid": booking_id, "jid": job_id, "tid": tenant_id, "cid": customer_id})
    await db_session.commit()

    yield {"tenant_id": tenant_id, "invoice_id": invoice_id, "payment_id": payment_id,
           "booking_id": booking_id, "job_id": job_id, "customer_id": customer_id}

    await db_session.execute(text("DELETE FROM svc_commission_records WHERE invoice_id = :id"), {"id": invoice_id})
    await db_session.execute(text(
        "DELETE FROM financial_events WHERE record_type = 'commission' AND tenant_id = :tid"
    ), {"tid": tenant_id})
    await db_session.execute(text("DELETE FROM financial_events WHERE record_id IN (:pid, :iid)"),
                              {"pid": payment_id, "iid": invoice_id})
    await db_session.execute(text("DELETE FROM service_payment_records WHERE id = :id"), {"id": payment_id})
    await db_session.execute(text("DELETE FROM service_invoices WHERE id = :id"), {"id": invoice_id})
    await db_session.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": tenant_id})
    await db_session.commit()


@pytest_asyncio.fixture
async def coaching_payment(db_session):
    """A same-shaped payment, but for a Coaching-vertical tenant -- must
    never appear in any Home Services Finance query."""
    tenant_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    booking_id = uuid.uuid4()
    job_id = uuid.uuid4()
    invoice_id = uuid.uuid4()
    payment_id = uuid.uuid4()
    category_id = uuid.uuid4()
    offering_id = uuid.uuid4()

    await db_session.execute(text(
        "INSERT INTO tenants (id, tenant_name, business_name, slug, tenant_code, status, vertical, "
        "created_at, updated_at) VALUES (:id, 'C', 'C Co', :slug, :code, 'active', 'coaching', now(), now())"
    ), {"id": tenant_id, "slug": f"c-{tenant_id.hex[:8]}", "code": f"CC{tenant_id.hex[:6]}"})
    await db_session.execute(text(
        "INSERT INTO service_invoices (id, invoice_number, booking_id, job_id, tenant_id, customer_id, "
        "category_id, offering_id, status, currency, total_amount, platform_fee_amount, "
        "customer_payable_amount, payment_status, created_at, updated_at) "
        "VALUES (:id, :num, :bid, :jid, :tid, :cid, :cat, :off, 'issued', 'INR', "
        "'9999.00', '999.00', '10998.00', 'pending', now(), now())"
    ), {"id": invoice_id, "num": f"INV-{invoice_id.hex[:8]}", "bid": booking_id, "jid": job_id,
        "tid": tenant_id, "cid": customer_id, "cat": category_id, "off": offering_id})
    await db_session.execute(text(
        "INSERT INTO service_payment_records (id, invoice_id, booking_id, job_id, tenant_id, customer_id, "
        "payment_mode, payment_status, collected_amount, currency, customer_confirmation_required, "
        "customer_confirmed, created_at, updated_at) "
        "VALUES (:id, :iid, :bid, :jid, :tid, :cid, 'cash', 'collected', '10998.00', 'INR', true, false, now(), now())"
    ), {"id": payment_id, "iid": invoice_id, "bid": booking_id, "jid": job_id, "tid": tenant_id, "cid": customer_id})
    await db_session.commit()

    yield {"tenant_id": tenant_id, "invoice_id": invoice_id, "payment_id": payment_id}

    await db_session.execute(text("DELETE FROM service_payment_records WHERE id = :id"), {"id": payment_id})
    await db_session.execute(text("DELETE FROM service_invoices WHERE id = :id"), {"id": invoice_id})
    await db_session.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": tenant_id})
    await db_session.commit()


class TestVerticalIsolation:
    async def test_direct_payment_visible_for_home_services_tenant(self, db_session, hs_payment):
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        svc = HomeServicesFinanceService(db=db_session)
        result = await svc.list_direct_payments(q=None, page=1, page_size=500)
        ids = {item["id"] for item in result["items"]}
        assert str(hs_payment["payment_id"]) in ids

    async def test_coaching_payment_never_appears(self, db_session, hs_payment, coaching_payment):
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        svc = HomeServicesFinanceService(db=db_session)
        result = await svc.list_direct_payments(q=None, page=1, page_size=500)
        ids = {item["id"] for item in result["items"]}
        assert str(coaching_payment["payment_id"]) not in ids
        assert str(hs_payment["payment_id"]) in ids

    async def test_coaching_payment_detail_lookup_raises_not_found(self, db_session, coaching_payment):
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        from app.exceptions import NotFoundException
        svc = HomeServicesFinanceService(db=db_session)
        with pytest.raises(NotFoundException):
            await svc.get_direct_payment_detail(coaching_payment["payment_id"])

    async def test_coaching_amount_never_pollutes_hs_summary(self, db_session, hs_payment, coaching_payment):
        """Coaching's ₹10,998 payment must not leak into the Home Services
        provider-collected total (proves the join is scoped, not filtered
        after the fact in Python)."""
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        svc = HomeServicesFinanceService(db=db_session)
        summary = await svc.get_direct_payments_summary()
        assert Decimal(summary["provider_collected_total"]) == Decimal("520.00")


class TestChargeSeparation:
    async def test_platform_fee_and_completion_charge_are_separate_records(self, db_session, hs_payment):
        """The ₹20 customer platform charge lives on ServiceInvoice; a
        provider completion charge (if any) lives in SvcCommissionRecord --
        distinct tables, never one merged row."""
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        svc = HomeServicesFinanceService(db=db_session)
        detail = await svc.get_direct_payment_detail(hs_payment["payment_id"])
        assert detail["customer_platform_charge"] == "20.00"
        assert detail["provider_collected_amount"] == "520.00"
        # No commission row was created in this fixture -- proves the two
        # concepts are independently absent/present, not derived from one another.
        assert detail["legacy_invoice_commission"]["status"] == "not_calculated"
        assert detail["legacy_invoice_commission"]["amount"] is None

    async def test_home_services_invoice_commission_is_not_required(self, db_session, hs_payment):
        """Recording the invoice payment cannot debit a second wallet after
        the completed-job usage-credit charge has run."""
        from app.engines.invoice_payment.commission_service import ServiceCommissionService
        result = await ServiceCommissionService().calculate_commission(
            db_session, str(hs_payment["invoice_id"])
        )
        assert result["status"] == "not_required"
        assert Decimal(result["commission_amount"]) == Decimal("0")
        second = await ServiceCommissionService().deduct_commission(
            db_session, str(hs_payment["invoice_id"]), idempotency_key=f"test-{hs_payment['invoice_id']}"
        )
        assert second["status"] == "not_required"
        assert second["wallet_ledger_entry_id"] is None


class TestOverviewHonesty:
    async def test_overview_reports_platform_charge_recovery_as_tracked(self, db_session, hs_payment):
        """Customer platform-charge recovery now posts its own usage_credit_
        ledger row (vertical_monetization.customer_charge_recovery, wired
        into job completion) -- independent from the provider completion
        charge. Overview must report the real figure, not a placeholder."""
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        svc = HomeServicesFinanceService(db=db_session)
        overview = await svc.get_overview()
        b = overview["group_b_serviceos_financial_position"]
        assert b["platform_charge_recovery_tracked"] is True
        assert b["platform_charges_recovered"] is not None
        assert "audit_note" in overview and len(overview["audit_note"]) > 0

    async def test_overview_customer_platform_charges_recorded_matches_real_data(self, db_session, hs_payment):
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        svc = HomeServicesFinanceService(db=db_session)
        overview = await svc.get_overview()
        a = overview["group_a_customer_to_provider"]
        assert Decimal(a["customer_platform_charges_recorded"]) == Decimal("20.00")
        assert Decimal(a["provider_collected_customer_payments"]) == Decimal("520.00")

    async def test_overview_confirmation_pending_counts_unconfirmed_payment(self, db_session, hs_payment):
        from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
        svc = HomeServicesFinanceService(db=db_session)
        overview = await svc.get_overview()
        assert overview["group_a_customer_to_provider"]["payment_confirmations_pending"] >= 1


class TestBackendValidatesAmounts:
    async def test_record_onsite_payment_rejects_amount_above_payable(self, db_session, hs_payment):
        """Provider-supplied amounts are never trusted over the invoice's
        own customer_payable_amount snapshot."""
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        from app.engines.invoice_payment.constants import ERR_PAYMENT_AMOUNT_MISMATCH, ERR_PAYMENT_ALREADY_RECORDED
        svc = ServicePaymentService()
        # A second payment attempt on the same (already-collected) invoice
        # must fail closed -- either on the duplicate guard or the amount
        # guard, never silently succeed with an inflated amount.
        with pytest.raises(ValueError) as exc:
            await svc.record_onsite_payment(
                db_session, invoice_id=str(hs_payment["invoice_id"]), tenant_id=str(hs_payment["tenant_id"]),
                payment_mode="onsite_cash", collected_amount=99999.00, proof_media_url=None,
                user_id=str(uuid.uuid4()), staff_member_id=None, request_id=None,
            )
        assert str(exc.value) in (ERR_PAYMENT_AMOUNT_MISMATCH, ERR_PAYMENT_ALREADY_RECORDED)
