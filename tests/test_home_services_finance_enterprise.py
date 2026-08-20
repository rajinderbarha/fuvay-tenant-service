"""Regression coverage for the consolidated Home Services finance workspace."""
from __future__ import annotations

import inspect
from pathlib import Path


def test_workspace_client_uses_only_scoped_list_contracts():
    src = Path("frontend/super-admin/lib/api-hs-finance.ts").read_text(encoding="utf-8")
    for path in (
        "provider-charges", "topups", "deposits", "warranty-claims",
        "invoices", "refunds", "financial-events", "audit",
    ):
        assert f"/v1/admin/finance/home-services/{path}" in src
    assert "/v1/admin/commission-records${_q(params)}" not in src
    assert "/v1/admin/financial-events${_q(params)}" not in src


def test_provider_charges_are_paginated_in_sql_not_memory():
    from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
    src = inspect.getsource(HomeServicesFinanceService.list_provider_charges)
    assert "union_all" in src
    assert ".offset((page - 1) * page_size).limit(page_size)" in src
    assert "page_size=5000" not in src
    assert "items[start:start + page_size]" not in src


def test_large_summary_cards_use_aggregates_not_full_table_loads():
    from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
    for name in (
        "get_credits_workspace_summary", "get_hs_deposits_summary",
        "get_hs_warranty_claims_summary", "get_invoices_summary",
        "get_hs_refunds_summary",
    ):
        src = inspect.getsource(getattr(HomeServicesFinanceService, name))
        assert "func.count" in src
        assert ".scalars().all()" not in src


def test_retired_duplicate_pages_are_server_redirects_and_unlinked():
    completed = Path("frontend/super-admin/app/admin/home-services/completed-job-deduction/page.tsx").read_text(encoding="utf-8")
    wallets = Path("frontend/super-admin/app/admin/provider-wallets/page.tsx").read_text(encoding="utf-8")
    layout = Path("frontend/super-admin/components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
    assert 'redirect("/admin/home-services/finance?tab=provider-charges")' in completed
    assert "credits_tab=accounts" in wallets and "redirect(" in wallets
    assert 'href: "/admin/home-services/completed-job-deduction"' not in layout


def test_browser_never_requests_five_thousand_finance_rows():
    src = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
    assert "pageSize: 5000" not in src
    assert "pageSize: 1000" not in src
    assert "Quick CSV · 200 max" in src
    assert "alert(" not in src
    assert '/^[=+\\-@]/' in src


def test_finance_filters_and_pagination_are_reactive():
    """useApi deliberately ignores callback identity unless its dependency
    list is supplied. Every stateful Finance list must therefore pass the
    filter/page state twice: to useCallback and to useApi."""
    src = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
    dependency_sets = (
        "[query, chargeModel, status, page]), [query, chargeModel, status, page]",
        "[query, lowOnly, page, pageSize]), [query, lowOnly, page, pageSize]",
        "[query, status, dateFrom, dateTo, page, pageSize]), [query, status, dateFrom, dateTo, page, pageSize]",
        "[query, status, page]), [query, status, page]",
        "[query, status, paymentStatus, page]), [query, status, paymentStatus, page]",
        "[query, status, refundTypeQuery, page]), [query, status, refundTypeQuery, page]",
        "[query, status, claimTypeQuery, page]), [query, status, claimTypeQuery, page]",
        "[query, eventType, recordType, page]), [query, eventType, recordType, page]",
    )
    for dependency_set in dependency_sets:
        assert dependency_set in src
    assert src.count("<QueryError message=") >= 10


def test_finance_routes_have_base_permission_and_bounded_pages():
    from app.engines.finance_hub import admin_hs_finance_router
    src = inspect.getsource(admin_hs_finance_router)
    assert "Depends(require_permission(P.FINANCE_READ))" in src
    assert "page_size: int = Query(50, ge=1, le=200)" in src


def test_shared_invoice_commission_and_event_reads_are_vertical_scoped():
    from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
    for name in (
        "list_provider_charges", "get_provider_charge_detail",
        "list_invoices", "get_invoice_detail", "get_invoices_summary",
        "list_financial_events", "get_financial_event_detail", "get_financial_events_summary",
    ):
        src = inspect.getsource(getattr(HomeServicesFinanceService, name))
        assert "HOME_SERVICES_VERTICAL" in src


def test_refund_record_client_matches_backend_contract_and_avoids_prompts():
    client = Path("frontend/super-admin/lib/api-hs-finance.ts").read_text(encoding="utf-8")
    page = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
    assert "recorded_amount: amount" in client
    assert "prompt(" not in page


def test_invoice_summary_uses_the_statuses_written_by_invoice_engine():
    from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
    src = inspect.getsource(HomeServicesFinanceService.get_invoices_summary)
    for status in ("collected", "verified", "pending", "failed"):
        assert f'payment_status == "{status}"' in src
    assert 'payment_status == "paid"' not in src
    assert 'payment_status == "overdue"' not in src


def test_warranty_workflow_and_audit_pagination_are_reachable_from_workspace():
    client = Path("frontend/super-admin/lib/api-hs-finance.ts").read_text(encoding="utf-8")
    page = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
    for action in ("assign", "request-documents", "approve", "reject", "settle"):
        assert f"/${{id}}/{action}`" in client
    assert "listAudit(page, pageSize)" in page
    assert "<Pagination page={page} total={audit.data?.total ?? 0}" in page


def test_dead_direct_payment_workspace_client_was_removed():
    client = Path("frontend/super-admin/lib/api-hs-finance.ts").read_text(encoding="utf-8")
    page = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
    for name in (
        "DirectPaymentsTab", "DirectPaymentDetail", "ChargeLedgerCard",
        "listDirectPayments", "getDirectPaymentsSummary", "openDirectPaymentDispute",
    ):
        assert name not in client
        assert name not in page


def test_sensitive_finance_actions_have_dedicated_permissions():
    from app.engines.finance_hub import admin_hs_finance_router
    from app.engines.vertical_monetization import home_services_finance_router
    src = inspect.getsource(admin_hs_finance_router)
    monetization_src = inspect.getsource(home_services_finance_router)
    assert "P.DIRECT_PAYMENTS_REMIND_CUSTOMER" in src
    assert "P.DIRECT_PAYMENTS_OPEN_DISPUTE" in src
    assert "P.FINANCE_AUDIT_READ" in src
    assert 'home_services:finance_monetization:{action}' in monetization_src
    assert '_require_hs_action("draft")' in monetization_src
    assert '_require_hs_action("publish")' in monetization_src
    assert "P.FINANCE_HOME_SERVICES_TOPUPS_RECONCILE" in src


def test_adjustment_client_serializes_the_fastapi_contract():
    client = Path("frontend/super-admin/lib/api-hs-finance.ts").read_text(encoding="utf-8")
    for field in ("tenant_id", "credit_units", "reason_code", "detailed_reason", "supporting_reference"):
        assert f"{field}: payload." in client
    page = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
    assert "Reserved Credits" not in page
    assert "Pending Recoveries" not in page


def test_home_services_overview_aggregates_are_vertically_scoped():
    from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
    src = inspect.getsource(HomeServicesFinanceService.get_overview)
    assert src.count("Tenant.vertical == HOME_SERVICES_VERTICAL") >= 4
    assert 'warranty.get("open_exposure"' in src
    assert '"total_credit_units": charges["credits_deducted"]' in src
    assert "SvcCommissionRecord.status" not in src


def test_home_services_has_one_live_provider_charge_writer():
    from app.engines.invoice_payment.commission_service import ServiceCommissionService
    commission = inspect.getsource(ServiceCommissionService.calculate_commission)
    deduction = Path("app/engines/execution/usage_credit_deduction.py").read_text(encoding="utf-8")
    assert "uses_completion_ledger" in commission
    assert "COM_NOT_REQUIRED if uses_completion_ledger" in commission
    assert 'provider_model == "COMPLETION_CREDITS"' in deduction
    assert 'provider_model == "PERCENTAGE_COMMISSION"' in deduction
    assert 'provider_model == "FIXED_COMPLETION_CHARGE"' in deduction


def test_completion_finance_uses_invoice_snapshot_without_fee_on_fee():
    from app.engines.execution import home_service_service
    from app.engines.vertical_monetization import customer_charge_recovery
    completion = inspect.getsource(home_service_service.HomeServiceJobExecutionService.complete_job)
    recovery = inspect.getsource(customer_charge_recovery.deduct_customer_platform_charge_recovery)
    assert "invoice.total_amount" in completion
    assert "invoice.platform_fee_amount" in completion
    assert "job_price=service_charge_basis" in completion
    assert "snapshotted_fee_amount=platform_fee_snapshot" in completion
    assert "if snapshotted_fee_amount is None" in recovery
    assert "recovery_amount = Decimal(str(snapshotted_fee_amount))" in recovery


def test_home_services_policy_blocks_unimplemented_models_from_publish():
    from app.engines.vertical_monetization import home_services_finance_router
    src = inspect.getsource(home_services_finance_router)
    assert "_HS_LIVE_PROVIDER_MODELS" in src
    assert '"SUBSCRIPTION"' not in inspect.getsource(home_services_finance_router._validate_hs_runtime)
    assert "_validate_hs_runtime(draft)" in src


def test_overview_payment_summary_aggregates_in_postgres():
    from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
    src = inspect.getsource(HomeServicesFinanceService.get_direct_payments_summary)
    assert "func.count" in src and "func.sum" in src
    assert ".all()" not in src


def test_home_services_finance_page_has_no_category_charge_editor():
    client = Path("frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
    page = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
    assert "vertical_type=${encodeURIComponent(verticalType)}" in client
    assert 'listCategoryCommissionRates("home_services")' not in page
    assert "CategoryCommissionSection" not in page
    assert "Category Commission Overrides" not in page


def test_category_override_changes_are_audited():
    from app.engines.admin_catalog import admin_router
    src = inspect.getsource(admin_router.set_category_commission_rate)
    assert "VerticalAuditLog" in src
    assert 'action_type="monetization.category_override.update"' in src
    assert "before_state=" in src and "after_state=" in src
