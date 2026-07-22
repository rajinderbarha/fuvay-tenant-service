"""Phase 2A Slice 2F-6A — invoice/on-site payment integrity and persona
closure for invoice_payment.provider_router.

Covers the 3 remaining questions from Slice 2F-6's conditional approval:
1. On-site payment amount integrity (negative/zero/overpayment/state).
2. Invoice item integrity (negative/zero quantity+price -- no discount
   mechanism exists, so negative values are rejected outright).
3. Technician persona: narrowed from require_staff_or_above_mutation to
   require_owner_or_office_staff_mutation (excludes technician) for
   provider_record_payment/staff_create_invoice/staff_add_invoice_item,
   since no mobile/staff-app caller was found for any of the 3.

Also directly proves cross-tenant rejection on all 4 routes via
service-level fixtures with a real mismatched tenant_id (not just source
inspection).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

TENANT_ID    = uuid.uuid4()
OTHER_TENANT = uuid.uuid4()
USER_ID      = uuid.uuid4()
CUSTOMER_ID  = uuid.uuid4()
JOB_ID       = uuid.uuid4()
BOOKING_ID   = uuid.uuid4()
INVOICE_ID   = uuid.uuid4()


def _mock_invoice(status="issued", tenant_id=None, payable="1000.00"):
    from app.engines.invoice_payment.models import ServiceInvoice
    inv = MagicMock(spec=ServiceInvoice)
    inv.id = INVOICE_ID
    inv.tenant_id = tenant_id or TENANT_ID
    inv.customer_id = CUSTOMER_ID
    inv.job_id = JOB_ID
    inv.booking_id = BOOKING_ID
    inv.status = status
    inv.customer_payable_amount = Decimal(payable)
    inv.total_amount = Decimal(payable)
    inv.platform_fee_amount = Decimal("0")
    inv.currency = "INR"
    inv.category_id = None
    return inv


def _scalars_result(items):
    r = MagicMock()
    r.scalars.return_value.all.return_value = items
    r.scalar_one_or_none.return_value = items[0] if items else None
    return r


def _mock_db(*execute_results):
    db = MagicMock()
    db.execute = AsyncMock(side_effect=list(execute_results))
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


# ─────────────────────────────────────────────────────────────────────────────
# On-site payment amount integrity
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestOnsitePaymentAmountIntegrity:
    async def test_negative_amount_rejected(self):
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        from app.engines.invoice_payment.constants import ERR_PAYMENT_AMOUNT_MISMATCH
        svc = ServicePaymentService()
        inv = _mock_invoice()
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.record_onsite_payment(
                db, str(INVOICE_ID), str(TENANT_ID), "onsite_cash", -100.0,
                None, str(USER_ID), None, None,
            )
        assert ERR_PAYMENT_AMOUNT_MISMATCH in str(exc.value)
        db.add.assert_not_called()

    async def test_zero_amount_rejected(self):
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        from app.engines.invoice_payment.constants import ERR_PAYMENT_AMOUNT_MISMATCH
        svc = ServicePaymentService()
        inv = _mock_invoice()
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.record_onsite_payment(
                db, str(INVOICE_ID), str(TENANT_ID), "onsite_cash", 0.0,
                None, str(USER_ID), None, None,
            )
        assert ERR_PAYMENT_AMOUNT_MISMATCH in str(exc.value)
        db.add.assert_not_called()

    async def test_overpayment_rejected(self):
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        from app.engines.invoice_payment.constants import ERR_PAYMENT_AMOUNT_MISMATCH
        svc = ServicePaymentService()
        inv = _mock_invoice(payable="1000.00")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.record_onsite_payment(
                db, str(INVOICE_ID), str(TENANT_ID), "onsite_cash", 1500.0,
                None, str(USER_ID), None, None,
            )
        assert ERR_PAYMENT_AMOUNT_MISMATCH in str(exc.value)
        db.add.assert_not_called()

    async def test_exact_remaining_balance_succeeds(self):
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        svc = ServicePaymentService()
        inv = _mock_invoice(payable="1000.00")
        db = _mock_db(_scalars_result([inv]), _scalars_result([]))
        with __import__("unittest.mock", fromlist=["patch"]).patch.object(
            svc._inv_svc, "update_payment_status", AsyncMock()
        ), __import__("unittest.mock", fromlist=["patch"]).patch.object(
            svc, "_log_event", AsyncMock()
        ), __import__("unittest.mock", fromlist=["patch"]).patch.object(
            svc, "_best_effort_commission", AsyncMock()
        ):
            result = await svc.record_onsite_payment(
                db, str(INVOICE_ID), str(TENANT_ID), "onsite_cash", 1000.0,
                None, str(USER_ID), None, None,
            )
        assert result is not None
        db.add.assert_called()

    async def test_valid_partial_payment_within_balance_succeeds(self):
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        svc = ServicePaymentService()
        inv = _mock_invoice(payable="1000.00")
        db = _mock_db(_scalars_result([inv]), _scalars_result([]))
        with __import__("unittest.mock", fromlist=["patch"]).patch.object(
            svc._inv_svc, "update_payment_status", AsyncMock()
        ), __import__("unittest.mock", fromlist=["patch"]).patch.object(
            svc, "_log_event", AsyncMock()
        ), __import__("unittest.mock", fromlist=["patch"]).patch.object(
            svc, "_best_effort_commission", AsyncMock()
        ):
            result = await svc.record_onsite_payment(
                db, str(INVOICE_ID), str(TENANT_ID), "onsite_cash", 400.0,
                None, str(USER_ID), None, None,
            )
        assert result is not None

    async def test_payment_against_draft_invoice_rejected(self):
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        from app.engines.invoice_payment.constants import ERR_INVOICE_INVALID_STATUS
        svc = ServicePaymentService()
        inv = _mock_invoice(status="draft")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.record_onsite_payment(
                db, str(INVOICE_ID), str(TENANT_ID), "onsite_cash", 500.0,
                None, str(USER_ID), None, None,
            )
        assert ERR_INVOICE_INVALID_STATUS in str(exc.value)
        db.add.assert_not_called()

    async def test_payment_against_cancelled_invoice_rejected(self):
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        from app.engines.invoice_payment.constants import ERR_INVOICE_INVALID_STATUS
        svc = ServicePaymentService()
        inv = _mock_invoice(status="cancelled")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.record_onsite_payment(
                db, str(INVOICE_ID), str(TENANT_ID), "onsite_cash", 500.0,
                None, str(USER_ID), None, None,
            )
        assert ERR_INVOICE_INVALID_STATUS in str(exc.value)

    async def test_payment_against_fully_collected_invoice_rejected(self):
        """Already-collected invoice: status moved to payment_collected AND
        an existing COLLECTED payment record exists -- both the new
        state check and the pre-existing duplicate-payment check reject."""
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        from app.engines.invoice_payment.constants import ERR_INVOICE_INVALID_STATUS
        svc = ServicePaymentService()
        inv = _mock_invoice(status="payment_collected")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.record_onsite_payment(
                db, str(INVOICE_ID), str(TENANT_ID), "onsite_cash", 500.0,
                None, str(USER_ID), None, None,
            )
        assert ERR_INVOICE_INVALID_STATUS in str(exc.value)

    async def test_repeated_identical_payment_rejected(self):
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        from app.engines.invoice_payment.constants import ERR_PAYMENT_ALREADY_RECORDED
        svc = ServicePaymentService()
        inv = _mock_invoice(status="issued")
        existing = MagicMock()
        db = _mock_db(_scalars_result([inv]), _scalars_result([existing]))
        with pytest.raises(ValueError) as exc:
            await svc.record_onsite_payment(
                db, str(INVOICE_ID), str(TENANT_ID), "onsite_cash", 1000.0,
                None, str(USER_ID), None, None,
            )
        assert ERR_PAYMENT_ALREADY_RECORDED in str(exc.value)

    async def test_cross_tenant_payment_rejected_no_mutation(self):
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ACCESS_DENIED
        svc = ServicePaymentService()
        inv = _mock_invoice(tenant_id=OTHER_TENANT)
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.record_onsite_payment(
                db, str(INVOICE_ID), str(TENANT_ID), "onsite_cash", 500.0,
                None, str(USER_ID), None, None,
            )
        assert ERR_INVOICE_ACCESS_DENIED in str(exc.value)
        db.add.assert_not_called()
        db.commit.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Invoice item integrity
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestInvoiceItemIntegrity:
    async def test_negative_quantity_rejected(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ITEM_INVALID
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="draft")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.add_item(
                db, str(INVOICE_ID), str(TENANT_ID), "part", "Widget", None,
                -1, 10.0, True, str(USER_ID), None,
            )
        assert ERR_INVOICE_ITEM_INVALID in str(exc.value)
        db.add.assert_not_called()

    async def test_zero_quantity_rejected(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ITEM_INVALID
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="draft")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.add_item(
                db, str(INVOICE_ID), str(TENANT_ID), "part", "Widget", None,
                0, 10.0, True, str(USER_ID), None,
            )
        assert ERR_INVOICE_ITEM_INVALID in str(exc.value)

    async def test_negative_unit_price_rejected(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ITEM_INVALID
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="draft")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.add_item(
                db, str(INVOICE_ID), str(TENANT_ID), "part", "Widget", None,
                1, -10.0, True, str(USER_ID), None,
            )
        assert ERR_INVOICE_ITEM_INVALID in str(exc.value)

    async def test_zero_unit_price_allowed(self):
        """A free/no-charge line item (e.g. warranty part) is legitimate."""
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="draft")
        db = _mock_db(_scalars_result([inv]), _scalars_result([]), MagicMock())
        result = await svc.add_item(
            db, str(INVOICE_ID), str(TENANT_ID), "part", "Warranty part", None,
            1, 0.0, True, str(USER_ID), None,
        )
        assert result is not None

    async def test_negative_quantity_negative_price_double_negative_rejected(self):
        """A double-negative (qty=-1, price=-10) would produce a positive
        line_total (+10) if unchecked -- must still be rejected on the
        quantity check alone, not accidentally allowed through."""
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ITEM_INVALID
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="draft")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.add_item(
                db, str(INVOICE_ID), str(TENANT_ID), "part", "Widget", None,
                -1, -10.0, True, str(USER_ID), None,
            )
        assert ERR_INVOICE_ITEM_INVALID in str(exc.value)

    async def test_item_added_after_issue_rejected(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ALREADY_ISSUED
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="issued")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.add_item(
                db, str(INVOICE_ID), str(TENANT_ID), "part", "Widget", None,
                1, 10.0, True, str(USER_ID), None,
            )
        assert ERR_INVOICE_ALREADY_ISSUED in str(exc.value)

    async def test_item_added_after_full_payment_rejected(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ALREADY_ISSUED
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="payment_collected")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.add_item(
                db, str(INVOICE_ID), str(TENANT_ID), "part", "Widget", None,
                1, 10.0, True, str(USER_ID), None,
            )
        assert ERR_INVOICE_ALREADY_ISSUED in str(exc.value)

    async def test_item_added_after_cancellation_rejected(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ALREADY_ISSUED
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="cancelled")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.add_item(
                db, str(INVOICE_ID), str(TENANT_ID), "part", "Widget", None,
                1, 10.0, True, str(USER_ID), None,
            )
        assert ERR_INVOICE_ALREADY_ISSUED in str(exc.value)

    async def test_valid_item_addition_succeeds(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="draft")
        db = _mock_db(_scalars_result([inv]), _scalars_result([]), MagicMock())
        result = await svc.add_item(
            db, str(INVOICE_ID), str(TENANT_ID), "part", "Widget", None,
            2, 50.0, True, str(USER_ID), None,
        )
        assert result is not None
        db.add.assert_called()

    async def test_cross_tenant_item_add_rejected_no_mutation(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ACCESS_DENIED
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="draft", tenant_id=OTHER_TENANT)
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.add_item(
                db, str(INVOICE_ID), str(TENANT_ID), "part", "Widget", None,
                1, 10.0, True, str(USER_ID), None,
            )
        assert ERR_INVOICE_ACCESS_DENIED in str(exc.value)
        db.add.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Invoice state machine (issue / create) cross-tenant + repeated-issue proof
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestInvoiceStateMachineDirect:
    async def test_repeated_issue_rejected(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ALREADY_ISSUED
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="issued")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.issue_invoice(db, str(INVOICE_ID), str(TENANT_ID), str(USER_ID), None)
        assert ERR_INVOICE_ALREADY_ISSUED in str(exc.value)

    async def test_issue_cross_tenant_rejected_no_mutation(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ACCESS_DENIED
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="draft", tenant_id=OTHER_TENANT)
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.issue_invoice(db, str(INVOICE_ID), str(TENANT_ID), str(USER_ID), None)
        assert ERR_INVOICE_ACCESS_DENIED in str(exc.value)
        db.commit.assert_not_called()

    async def test_issue_cancelled_invoice_rejected(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_INVALID_STATUS
        svc = ServiceInvoiceService()
        inv = _mock_invoice(status="cancelled")
        db = _mock_db(_scalars_result([inv]))
        with pytest.raises(ValueError) as exc:
            await svc.issue_invoice(db, str(INVOICE_ID), str(TENANT_ID), str(USER_ID), None)
        assert ERR_INVOICE_INVALID_STATUS in str(exc.value)

    async def test_create_invoice_cross_tenant_rejected_no_mutation(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        from app.engines.invoice_payment.constants import ERR_INVOICE_ACCESS_DENIED
        from app.engines.final_records.models import ServiceJob
        svc = ServiceInvoiceService()
        job = MagicMock(spec=ServiceJob)
        job.id = JOB_ID
        job.tenant_id = OTHER_TENANT
        job.booking_id = BOOKING_ID
        job.customer_id = CUSTOMER_ID
        job.category_id = None
        job.offering_id = None
        db = _mock_db(_scalars_result([job]))
        with pytest.raises(ValueError) as exc:
            await svc.create_invoice(
                db, str(JOB_ID), str(TENANT_ID), "manual_final", None, None,
                str(USER_ID), None,
            )
        assert ERR_INVOICE_ACCESS_DENIED in str(exc.value)
        db.add.assert_not_called()
        db.commit.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Technician persona narrowing (HTTP-level, via the router's new guard)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestTechnicianPersonaNarrowed:
    """Slice 2F-6A: technician is denied on all 3 require_owner_or_office_staff_mutation
    routes (provider_record_payment/staff_create_invoice/staff_add_invoice_item),
    and remains denied on provider_issue_invoice (unchanged, owner-only)."""

    @staticmethod
    def _user(role):
        from app.dependencies.auth import UserContext
        return UserContext(
            user_id=str(uuid.uuid4()), email=f"{role}@test.local", role=role,
            tenant_id=str(uuid.uuid4()), full_name=role.title(), is_verified=True,
        )

    async def _call(self, method, path, body):
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            return await ac.request(method, path, json=body)

    @pytest.fixture(autouse=True)
    def _mock_database(self):
        from app.main import app
        from app.dependencies.db import get_db
        mock_database = MagicMock()
        mock_database.execute = AsyncMock(return_value=MagicMock())
        mock_database.commit = AsyncMock()
        mock_database.flush = AsyncMock()
        mock_database.add = MagicMock()

        async def _fake_get_db():
            yield mock_database

        app.dependency_overrides[get_db] = _fake_get_db
        yield mock_database
        app.dependency_overrides.pop(get_db, None)

    @pytest.mark.parametrize("path,body", [
        ("/v1/provider/service-invoices/{}/record-payment".format(str(INVOICE_ID)),
         {"payment_mode": "onsite_cash", "collected_amount": "100"}),
        ("/v1/staff/service-invoices", {"job_id": "job-1"}),
        ("/v1/staff/service-invoices/{}/items".format(str(INVOICE_ID)),
         {"item_name": "part", "unit_price": "10"}),
    ])
    async def test_technician_denied(self, path, body):
        from app.main import app
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: self._user("technician")
        try:
            resp = await self._call("POST", path, body)
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_technician_denied_on_issue(self):
        from app.main import app
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: self._user("technician")
        try:
            resp = await self._call(
                "POST", f"/v1/provider/service-invoices/{INVOICE_ID}/issue", None
            )
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestModuleVerificationExitsCleanAfterNarrowing:
    def test_invoice_payment_provider_router_zero_unverified(self):
        import importlib.util
        from pathlib import Path
        from app.main import app

        spec = importlib.util.spec_from_file_location(
            "inventory_mutation_routes",
            Path(__file__).parent.parent / "scripts" / "workflow_rearchitecture" / "inventory_mutation_routes.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        routes = [r for r in mod.walk(app.router if hasattr(app, "router") else app)
                  if r["module"] == "app.engines.invoice_payment.provider_router"]
        assert len(routes) == 4
        exempt = mod.CONFIRMED_FALSE_POSITIVE_ROUTES | mod.CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES
        unverified = [
            r for r in routes
            if r["guard_status"] not in mod.ACCEPTED_GUARD_STATUSES
            and (r["module"], r["endpoint_name"]) not in exempt
        ]
        assert unverified == [], f"unverified routes remain: {unverified}"
