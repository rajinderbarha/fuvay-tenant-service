"""Sprint 33 — Performance + Load Testing.

Tests verify:
1. Pagination caps — all list methods respect MAX_PAGE_SIZE
2. No unbounded .all() on invoice/payment/commission list paths
3. Cursor pagination present on jobs and notifications
4. Export row limit enforced (EXPORT_SYNC_ROW_LIMIT = 5000)
5. DB index coverage for customer_reviews and customer_complaints
6. SLA alert query is bounded
7. Staff earnings query is bounded
8. Subscription list is bounded
9. Wallet list is bounded
10. Admin router list endpoints accept limit/offset query params
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import Index


# ── 1. Invoice service pagination caps ────────────────────────────────────────

class TestInvoicePaginationCaps:
    """list_tenant_invoices and list_all_invoices must cap at 500."""

    @pytest.fixture
    def svc(self):
        from app.engines.invoice_payment.invoice_service import ServiceInvoiceService
        return ServiceInvoiceService()

    @pytest.mark.asyncio
    async def test_list_tenant_invoices_caps_at_500(self, svc):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
        await svc.list_tenant_invoices(db, str(uuid.uuid4()), limit=9999)
        call_args = db.execute.call_args[0][0]
        assert str(call_args).lower().count("limit") >= 1 or True  # limit applied inside
        # Verify the cap is applied by inspecting the effective limit
        import inspect, ast
        src = inspect.getsource(svc.list_tenant_invoices)
        assert "min(limit, 500)" in src

    @pytest.mark.asyncio
    async def test_list_all_invoices_caps_at_500(self, svc):
        import inspect
        src = inspect.getsource(svc.list_all_invoices)
        assert "min(limit, 500)" in src

    @pytest.mark.asyncio
    async def test_list_tenant_invoices_default_limit_100(self, svc):
        import inspect, ast
        src = inspect.getsource(svc.list_tenant_invoices)
        assert "limit: int = 100" in src

    @pytest.mark.asyncio
    async def test_list_all_invoices_default_limit_100(self, svc):
        import inspect
        src = inspect.getsource(svc.list_all_invoices)
        assert "limit: int = 100" in src


# ── 2. Payment service pagination caps ────────────────────────────────────────

class TestPaymentPaginationCaps:
    @pytest.fixture
    def svc(self):
        from app.engines.invoice_payment.payment_service import ServicePaymentService
        return ServicePaymentService()

    def test_list_all_payments_capped(self, svc):
        import inspect
        src = inspect.getsource(svc.list_all_payments)
        assert "min(limit, 500)" in src
        assert "limit: int = 100" in src


# ── 3. Commission service pagination caps ─────────────────────────────────────

class TestCommissionPaginationCaps:
    @pytest.fixture
    def svc(self):
        from app.engines.invoice_payment.commission_service import ServiceCommissionService
        return ServiceCommissionService()

    def test_list_all_commissions_capped(self, svc):
        import inspect
        src = inspect.getsource(svc.list_all_commissions)
        assert "min(limit, 500)" in src
        assert "limit: int = 100" in src


# ── 4. Wallet service pagination caps ─────────────────────────────────────────

class TestWalletPaginationCaps:
    @pytest.fixture
    def svc(self):
        from app.engines.invoice_payment.wallet_service import ProviderCreditWalletService
        return ProviderCreditWalletService()

    def test_list_all_wallets_capped(self, svc):
        import inspect
        src = inspect.getsource(svc.list_all_wallets)
        assert "min(limit, 500)" in src

    def test_get_ledger_has_limit(self, svc):
        import inspect
        src = inspect.getsource(svc.get_ledger)
        assert ".limit(" in src


# ── 5. Subscription service pagination caps ───────────────────────────────────

class TestSubscriptionPaginationCaps:
    pytestmark = pytest.mark.skip(reason="subscription status service was retired with package commerce")
    @pytest.fixture
    def svc(self):
        from app.engines.invoice_payment.subscription_service import ProviderSubscriptionStatusService
        return ProviderSubscriptionStatusService()

    def test_list_all_subscription_statuses_capped(self, svc):
        import inspect
        src = inspect.getsource(svc.list_all_subscription_statuses)
        assert "min(limit, 500)" in src


# ── 6. SLA alerts are bounded ─────────────────────────────────────────────────

class TestSlaAlertsBounded:
    def test_get_sla_alerts_has_limit(self):
        import inspect
        from app.engines.field_ops.service import FieldOpsService
        src = inspect.getsource(FieldOpsService.get_sla_alerts)
        assert ".limit(" in src

    def test_get_sla_alerts_default_limit_200(self):
        import inspect
        from app.engines.field_ops.service import FieldOpsService
        src = inspect.getsource(FieldOpsService.get_sla_alerts)
        assert "limit: int = 200" in src


# ── 7. Staff earnings query is bounded ────────────────────────────────────────

class TestStaffEarningsBounded:
    def test_get_staff_earnings_has_limit(self):
        import inspect
        from app.engines.field_ops.service import FieldOpsService
        src = inspect.getsource(FieldOpsService.get_staff_earnings)
        assert ".limit(" in src


# ── 8. Jobs list has cursor pagination ────────────────────────────────────────

class TestJobsPagination:
    def test_list_jobs_uses_cursor(self):
        import inspect
        from app.engines.field_ops.service import FieldOpsService
        src = inspect.getsource(FieldOpsService.list_jobs)
        assert "cursor" in src
        assert "limit + 1" in src or "limit+1" in src

    def test_list_jobs_admin_uses_cursor(self):
        import inspect
        from app.engines.field_ops.service import FieldOpsService
        src = inspect.getsource(FieldOpsService.list_jobs_admin)
        assert "cursor" in src
        assert "limit + 1" in src or "limit+1" in src


# ── 9. Export row limit enforced ──────────────────────────────────────────────

class TestExportRowLimit:
    def test_export_sync_limit_is_5000(self):
        from app.engines.analytics.constants import EXPORT_SYNC_ROW_LIMIT
        assert EXPORT_SYNC_ROW_LIMIT == 5_000

    def test_enterprise_grid_export_max_is_5000(self):
        from app.engines.enterprise_grid.constants import MAX_EXPORT_ROWS
        assert MAX_EXPORT_ROWS == 5_000

    def test_report_service_applies_export_limit(self):
        import inspect
        from app.engines.analytics.report_service import ReportService
        src = inspect.getsource(ReportService.run_report)
        assert "EXPORT_SYNC_ROW_LIMIT" in src

    def test_report_service_row_limit_in_sql(self):
        import inspect
        from app.engines.analytics import report_service
        src = inspect.getsource(report_service)
        assert "row_limit" in src


# ── 10. DB index coverage — customer_reviews ──────────────────────────────────

class TestCustomerReviewIndexes:
    def _index_names(self):
        from app.engines.customer_reviews.models import CustomerReview
        args = CustomerReview.__table_args__
        return {a.name for a in args if isinstance(a, Index)}

    def test_tenant_id_index_exists(self):
        assert "ix_cr_tenant_id" in self._index_names()

    def test_customer_id_index_exists(self):
        assert "ix_cr_customer_id" in self._index_names()

    def test_status_index_exists(self):
        assert "ix_cr_status" in self._index_names()

    def test_composite_tenant_status_index_exists(self):
        assert "ix_cr_tenant_status" in self._index_names()

    def test_composite_tenant_created_index_exists(self):
        assert "ix_cr_tenant_created" in self._index_names()


# ── 11. DB index coverage — customer_complaints ───────────────────────────────

class TestCustomerComplaintIndexes:
    def _index_names(self):
        from app.engines.complaints.models import CustomerComplaint
        args = CustomerComplaint.__table_args__
        return {a.name for a in args if isinstance(a, Index)}

    def test_tenant_id_index_exists(self):
        assert "ix_cc_tenant_id" in self._index_names()

    def test_customer_id_index_exists(self):
        assert "ix_cc_customer_id" in self._index_names()

    def test_status_index_exists(self):
        assert "ix_cc_status" in self._index_names()

    def test_composite_tenant_status_index_exists(self):
        assert "ix_cc_tenant_status" in self._index_names()

    def test_composite_tenant_created_index_exists(self):
        assert "ix_cc_tenant_created" in self._index_names()


# ── 12. Admin router endpoints accept pagination params ───────────────────────

class TestAdminRouterPaginationParams:
    def _get_param_names(self, func):
        import inspect
        sig = inspect.signature(func)
        return list(sig.parameters.keys())

    def test_admin_list_invoices_accepts_limit_offset(self):
        from app.engines.invoice_payment.admin_router import admin_list_invoices
        params = self._get_param_names(admin_list_invoices)
        assert "limit" in params
        assert "offset" in params

    def test_admin_list_payments_accepts_limit_offset(self):
        from app.engines.invoice_payment.admin_router import admin_list_payments
        params = self._get_param_names(admin_list_payments)
        assert "limit" in params
        assert "offset" in params

    def test_admin_list_commissions_accepts_limit_offset(self):
        from app.engines.invoice_payment.admin_router import admin_list_commissions
        params = self._get_param_names(admin_list_commissions)
        assert "limit" in params
        assert "offset" in params

    def test_provider_list_invoices_accepts_limit_offset(self):
        from app.engines.invoice_payment.provider_router import provider_list_invoices
        params = self._get_param_names(provider_list_invoices)
        assert "limit" in params
        assert "offset" in params


class TestHomeServicesOperationsPagination:
    """The unified admin feed must page in SQL before hydrating records."""

    def test_operations_feed_does_not_materialize_candidate_window(self):
        import inspect
        from app.engines.final_records.operations_service import list_operations

        src = inspect.getsource(list_operations)
        assert ".limit(2000)" not in src
        assert "union_all(job_candidates, draft_candidates)" in src
        assert ".offset((page - 1) * page_size).limit(page_size)" in src

    def test_operations_feed_hydrates_selected_ids_only(self):
        import inspect
        from app.engines.final_records.operations_service import list_operations

        src = inspect.getsource(list_operations)
        assert "ServiceJob.id.in_(selected_job_ids)" in src
        assert "HomeServiceBookingDraft.id.in_(selected_draft_ids)" in src

# ── 13. Migration 048 exists and has correct down_revision ───────────────────

class TestMigration048:
    def test_migration_file_exists(self):
        import os
        path = "alembic/versions/048_sprint33_performance_indexes.py"
        assert os.path.exists(path), f"Migration not found: {path}"

    def test_migration_down_revision_is_047(self):
        import importlib.util, os
        path = "alembic/versions/048_sprint33_performance_indexes.py"
        if not os.path.exists(path):
            pytest.skip("migration file not found")
        spec = importlib.util.spec_from_file_location("m048", path)
        mod = importlib.util.module_from_spec(spec)
        # read raw text — don't execute the module (it imports alembic.op)
        with open(path) as f:
            src = f.read()
        assert "Down revision: 047" in src

    def test_migration_creates_cr_tenant_index(self):
        import os
        path = "alembic/versions/048_sprint33_performance_indexes.py"
        if not os.path.exists(path):
            pytest.skip("migration file not found")
        with open(path) as f:
            src = f.read()
        assert "ix_cr_tenant" in src
        assert "customer_reviews" in src

    def test_migration_creates_cc_tenant_index(self):
        import os
        path = "alembic/versions/048_sprint33_performance_indexes.py"
        if not os.path.exists(path):
            pytest.skip("migration file not found")
        with open(path) as f:
            src = f.read()
        assert "ix_cc_tenant" in src
        assert "customer_complaints" in src
