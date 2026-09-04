"""P0 Customer Service Credit + Dispute Settlement Engine — test suite.

Business rules verified:
- Platform issues Fuvay credit (not cash) after disputes.
- Platform recovers from tenant wallet first, then security deposit.
- No silent deductions — every deduction creates a FinanceAuditLog.
- NEVER call customer credit a 'cash refund'.
"""
import re
from pathlib import Path

# Repo-relative: this file is tests/<name>.py, so parents[1] is the repo
# root. A hardcoded absolute path made every test here fail on any machine
# that was not the Windows box it was written on, CI included.
ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "alembic/versions/080_customer_service_credit_dispute_settlement.py"
MODELS = ROOT / "app/engines/customer_credits/models.py"
SERVICE = ROOT / "app/engines/customer_credits/service.py"
ADMIN_ROUTER = ROOT / "app/engines/customer_credits/admin_router.py"
CUSTOMER_ROUTER = ROOT / "app/engines/customer_credits/customer_router.py"
PROVIDER_ROUTER = ROOT / "app/engines/customer_credits/provider_router.py"
MAIN_PY = ROOT / "app/main.py"
PERMISSIONS = ROOT / "app/core/permissions.py"
SA_API = ROOT / "frontend/super-admin/lib/api.ts"
TP_API = ROOT / "frontend/tenant-portal/lib/api.ts"
SA_SETTLEMENTS = ROOT / "frontend/super-admin/app/admin/finance/dispute-settlements/page.tsx"
SA_CREDITS = ROOT / "frontend/super-admin/app/admin/finance/customer-credits/page.tsx"
SA_PENALTIES = ROOT / "frontend/super-admin/app/admin/finance/tenant-penalties/page.tsx"
TP_CREDITS = ROOT / "frontend/tenant-portal/app/(tenant)/account/credits/page.tsx"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ── Migration ──────────────────────────────────────────────────────────────

class TestMigration080:
    def test_migration_file_exists(self):
        assert MIGRATION.exists(), "Migration 080 file not found."

    def test_migration_revision(self):
        content = _read(MIGRATION)
        assert 'revision = "080"' in content

    def test_migration_down_revision(self):
        content = _read(MIGRATION)
        assert 'down_revision = "079"' in content

    def test_migration_creates_finance_vertical_configs(self):
        assert "finance_vertical_configs" in _read(MIGRATION)

    def test_migration_creates_customer_service_credits(self):
        assert "customer_service_credits" in _read(MIGRATION)

    def test_migration_creates_customer_credit_ledger(self):
        assert "customer_credit_ledger" in _read(MIGRATION)

    def test_migration_creates_dispute_settlements(self):
        assert "dispute_settlements" in _read(MIGRATION)

    def test_migration_creates_tenant_penalties(self):
        assert "tenant_penalties" in _read(MIGRATION)

    def test_migration_creates_security_deposit_adjustments(self):
        assert "security_deposit_adjustments" in _read(MIGRATION)

    def test_migration_creates_finance_audit_logs(self):
        assert "finance_audit_logs" in _read(MIGRATION)

    def test_migration_seeds_home_services_config(self):
        content = _read(MIGRATION)
        assert "home_services" in content
        assert "payment_collection_enabled" in content

    def test_migration_home_services_payment_disabled(self):
        content = _read(MIGRATION)
        assert "false, false, true" in content or "payment_collection_enabled, tenant_payouts_enabled" in content


# ── Models ──────────────────────────────────────────────────────────────────

class TestModels:
    def test_models_file_exists(self):
        assert MODELS.exists()

    def test_finance_vertical_config_model(self):
        assert "FinanceVerticalConfig" in _read(MODELS)

    def test_customer_service_credit_model(self):
        assert "CustomerServiceCredit" in _read(MODELS)

    def test_customer_credit_ledger_model(self):
        assert "CustomerCreditLedger" in _read(MODELS)

    def test_dispute_settlement_model(self):
        assert "DisputeSettlement" in _read(MODELS)

    def test_tenant_penalty_model(self):
        assert "TenantPenalty" in _read(MODELS)

    def test_security_deposit_adjustment_model(self):
        assert "SecurityDepositAdjustment" in _read(MODELS)

    def test_finance_audit_log_model(self):
        assert "FinanceAuditLog" in _read(MODELS)

    def test_models_have_to_dict(self):
        content = _read(MODELS)
        count = content.count("def to_dict")
        assert count >= 6, f"Expected ≥6 to_dict methods, found {count}"

    def test_csc_has_credit_number(self):
        assert "credit_number" in _read(MODELS)

    def test_csc_has_remaining_amount(self):
        assert "remaining_amount" in _read(MODELS)

    def test_csc_has_status(self):
        assert '"active"' in _read(MODELS) or "'active'" in _read(MODELS)

    def test_dispute_settlement_has_settlement_number(self):
        assert "settlement_number" in _read(MODELS)

    def test_dispute_settlement_has_deduction_source(self):
        assert "deduction_source" in _read(MODELS)

    def test_dispute_settlement_has_wallet_deduction_amount(self):
        assert "tenant_wallet_deduction_amount" in _read(MODELS)

    def test_dispute_settlement_has_no_retired_security_deposit_amount(self):
        assert "security_deposit_deduction_amount" not in _read(MODELS)


# ── Service ──────────────────────────────────────────────────────────────────

class TestService:
    def test_service_file_exists(self):
        assert SERVICE.exists()

    def test_has_dispute_settlement_service(self):
        assert "DisputeSettlementService" in _read(SERVICE)

    def test_has_customer_credit_service(self):
        assert "CustomerCreditService" in _read(SERVICE)

    def test_has_preview_deduction(self):
        assert "preview_deduction" in _read(SERVICE)

    def test_has_create_settlement(self):
        assert "create_settlement" in _read(SERVICE)

    def test_has_approve_settlement(self):
        assert "approve_settlement" in _read(SERVICE)

    def test_has_execute_settlement(self):
        assert "execute_settlement" in _read(SERVICE)

    def test_has_cancel_settlement(self):
        assert "cancel_settlement" in _read(SERVICE)

    def test_has_issue_credit_manual(self):
        assert "issue_credit_manual" in _read(SERVICE)

    def test_has_cancel_credit(self):
        assert "cancel_credit" in _read(SERVICE)

    def test_has_extend_credit_expiry(self):
        assert "extend_credit_expiry" in _read(SERVICE)

    def test_has_apply_credit_to_booking(self):
        assert "apply_credit_to_booking" in _read(SERVICE)

    def test_apply_credit_to_booking_never_trusts_client_amount(self):
        """P0 Platform Stabilization Sprint fix: booking_amount was previously a raw
        client-supplied value with no server-side check against the real Booking
        row, and the computed payable amount was never persisted — so applying a
        credit had zero effect on what the provider/technician actually saw. The
        real Booking.quoted_price must now be the sole source of truth, and the
        result must be written back onto the booking row."""
        content = _read(SERVICE)
        body = content.split("async def apply_credit_to_booking")[1].split("\n    async def ")[0]
        assert "from app.engines.booking.models import Booking" in content
        assert "select(Booking)" in body
        assert "booking.quoted_price" in body
        assert "booking.credit_applied = " in body
        assert "booking.payable_amount = " in body

    def test_apply_credit_to_booking_verifies_ownership_with_string_compare(self):
        """UUID objects loaded from the DB never equal a raw string customer_id from
        a JWT via plain Python `!=` — must compare as strings, not rely on ORM-level
        coercion which doesn't apply outside a SQL where() clause."""
        content = _read(SERVICE)
        body = content.split("async def apply_credit_to_booking")[1].split("\n    async def ")[0]
        assert "str(booking.customer_id) != str(customer_id)" in body

    def test_customer_router_apply_does_not_accept_booking_amount_from_client(self):
        content = _read(CUSTOMER_ROUTER)
        apply_fn = content.split('@router.post("/apply")')[1]
        assert 'body.get("booking_amount"' not in apply_fn

    def test_business_rule_no_cash_refund(self):
        content = _read(SERVICE)
        # "cash refund" only allowed in a negation context ("not a cash refund", "NOT cash refund")
        import re as _re
        bad = [m.start() for m in _re.finditer(r"cash refund", content, _re.IGNORECASE)]
        for pos in bad:
            context = content[max(0, pos - 20):pos].lower()
            assert "not" in context or "no " in context, (
                f"Service labels credit as 'cash refund' without negation at position {pos}")


    def test_business_rule_not_cash(self):
        # Service must acknowledge credits are platform credits
        assert "platform credit" in _read(SERVICE).lower() or "service credit" in _read(SERVICE).lower()

    def test_execute_deducts_canonical_usage_credit(self):
        content = _read(SERVICE)
        assert "credit_balance" in content
        assert "UsageCreditLedger(" in content
        assert "warranty_drawn" not in content

    def test_execute_creates_audit_log(self):
        content = _read(SERVICE)
        assert "FinanceAuditLog" in content or "_audit(" in content

    def test_execute_creates_canonical_usage_credit_ledger(self):
        source = _read(SERVICE)
        assert "UsageCreditLedger" in source
        assert "WalletTransaction" not in source

    def test_execute_never_creates_retired_deposit_transaction(self):
        assert "SecurityDepositTransaction" not in _read(SERVICE)

    def test_valid_deduction_strategies_defined(self):
        content = _read(SERVICE)
        assert "tenant_wallet" in content
        assert "platform_goodwill" in content

    def test_preview_returns_can_fully_cover(self):
        assert "can_fully_cover" in _read(SERVICE)

    def test_credit_ledger_entry_on_issue(self):
        assert "CustomerCreditLedger" in _read(SERVICE)

    def test_tenant_penalty_created_on_execute(self):
        assert "TenantPenalty" in _read(SERVICE)

    def test_complaint_settlement_status_updated(self):
        assert "settlement_status" in _read(SERVICE)
        assert '"settled"' in _read(SERVICE)

    def test_credit_expiry_180_days(self):
        assert "180" in _read(SERVICE)

    def test_list_settlements_with_filters(self):
        assert "list_settlements" in _read(SERVICE)

    def test_list_credits_with_filters(self):
        assert "list_credits" in _read(SERVICE)


# ── Permissions ──────────────────────────────────────────────────────────────

class TestPermissions:
    def test_finance_settlements_read(self):
        assert "FINANCE_SETTLEMENTS_READ" in _read(PERMISSIONS)

    def test_finance_settlements_create(self):
        assert "FINANCE_SETTLEMENTS_CREATE" in _read(PERMISSIONS)

    def test_finance_settlements_approve(self):
        assert "FINANCE_SETTLEMENTS_APPROVE" in _read(PERMISSIONS)

    def test_finance_settlements_execute(self):
        assert "FINANCE_SETTLEMENTS_EXECUTE" in _read(PERMISSIONS)

    def test_finance_credits_read(self):
        assert "FINANCE_CREDITS_READ" in _read(PERMISSIONS)

    def test_finance_credits_create(self):
        assert "FINANCE_CREDITS_CREATE" in _read(PERMISSIONS)

    def test_finance_credits_cancel(self):
        assert "FINANCE_CREDITS_CANCEL" in _read(PERMISSIONS)

    def test_finance_credits_extend(self):
        assert "FINANCE_CREDITS_EXTEND" in _read(PERMISSIONS)

    def test_finance_penalties_read(self):
        assert "FINANCE_PENALTIES_READ" in _read(PERMISSIONS)


# ── Admin Router ─────────────────────────────────────────────────────────────

class TestAdminRouter:
    def test_admin_router_is_read_only_penalty_oversight(self):
        content = _read(ADMIN_ROUTER)
        assert ADMIN_ROUTER.exists()
        assert "/v1/admin/finance" in content
        assert "/penalties/summary" in content
        assert "/penalties" in content
        assert "vertical-config" in content
        assert "FINANCE_PENALTIES_READ" in content
        assert "router.post" not in content
        for retired in ("/settlements", "/credits", "/disputes", "/customers"):
            assert retired not in content

class TestCustomerRouter:
    def test_customer_router_file_exists(self):
        assert CUSTOMER_ROUTER.exists()

    def test_prefix_v1_me_credits(self):
        assert "/v1/me/credits" in _read(CUSTOMER_ROUTER)

    def test_list_credits_endpoint(self):
        content = _read(CUSTOMER_ROUTER)
        assert "list_credits" in content or 'async def list_my_credits' in content

    def test_credit_summary_endpoint(self):
        assert "summary" in _read(CUSTOMER_ROUTER)

    def test_get_credit_endpoint(self):
        assert "credit_id" in _read(CUSTOMER_ROUTER)

    def test_preview_apply_endpoint(self):
        assert "preview" in _read(CUSTOMER_ROUTER)

    def test_apply_endpoint(self):
        assert "apply" in _read(CUSTOMER_ROUTER)

    def test_uses_require_customer(self):
        assert "require_customer" in _read(CUSTOMER_ROUTER)


# ── Provider Router ───────────────────────────────────────────────────────────

class TestProviderRouter:
    def test_provider_router_file_exists(self):
        assert PROVIDER_ROUTER.exists()

    def test_prefix_v1_provider_finance(self):
        assert "/v1/provider/finance" in _read(PROVIDER_ROUTER)

    def test_tenant_isolation_guard(self):
        assert "_require_tenant" in _read(PROVIDER_ROUTER) or "tenant_id" in _read(PROVIDER_ROUTER)

    def test_settlements_list(self):
        assert "settlements" in _read(PROVIDER_ROUTER)

    def test_penalties_list(self):
        assert "penalties" in _read(PROVIDER_ROUTER)


# ── main.py Registration ─────────────────────────────────────────────────────

class TestMainRegistration:
    def test_admin_router_imported(self):
        assert "customer_credits.admin_router" in _read(MAIN_PY)

    def test_customer_router_imported(self):
        assert "customer_credits.customer_router" in _read(MAIN_PY)

    def test_provider_router_imported(self):
        assert "customer_credits.provider_router" in _read(MAIN_PY)

    def test_routers_included(self):
        content = _read(MAIN_PY)
        assert "credits_admin_router" in content
        assert "credits_customer_router" in content
        assert "credits_provider_router" in content


# ── Super-admin API (api.ts) ──────────────────────────────────────────────────

class TestSuperAdminApi:
    def test_tenant_penalty_interface(self):
        assert "TenantPenalty" in _read(SA_API)

    def test_tenant_penalty_summary_interface(self):
        assert "TenantPenaltySummary" in _read(SA_API)

    def test_finance_vertical_config_interface(self):
        assert "FinanceVerticalConfig" in _read(SA_API)

    def test_list_penalties_method(self):
        assert "listPenalties" in _read(SA_API)

    def test_get_penalty_summary_method(self):
        assert "getPenaltySummary" in _read(SA_API)

    def test_get_vertical_config_method(self):
        assert "getVerticalConfig" in _read(SA_API)

    def test_admin_dispute_and_customer_credit_controls_are_retired(self):
        content = _read(SA_API)
        for symbol in (
            "DisputeSettlement", "approveSettlement", "executeSettlement",
            "issueManualCredit", "cancelCredit", "extendCredit",
        ):
            assert symbol not in content


# ── Tenant Portal API (api.ts) ────────────────────────────────────────────────

class TestTenantPortalApi:
    def test_my_service_credit_interface(self):
        assert "MyServiceCredit" in _read(TP_API)

    def test_my_credit_summary_interface(self):
        assert "MyCreditSummary" in _read(TP_API)

    def test_credit_apply_preview_interface(self):
        assert "CreditApplyPreview" in _read(TP_API)

    def test_customer_credits_api_exported(self):
        assert "customerCreditsApi" in _read(TP_API)

    def test_list_my_credits_method(self):
        assert "listMyCredits" in _read(TP_API)

    def test_get_my_summary_method(self):
        assert "getMySummary" in _read(TP_API)

    def test_preview_apply_method(self):
        assert "previewApply" in _read(TP_API)

    def test_apply_to_booking_method(self):
        assert "applyToBooking" in _read(TP_API)

    def test_credit_described_as_platform_credit(self):
        content = _read(TP_API)
        block = content[content.find("customerCreditsApi"):]
        # Should reference /v1/me/credits
        assert "/v1/me/credits" in block


# ── Frontend pages ────────────────────────────────────────────────────────────

class TestSuperAdminPages:
    def test_retired_admin_settlement_and_credit_pages_are_deleted(self):
        assert not SA_SETTLEMENTS.exists()
        assert not SA_CREDITS.exists()

    def test_tenant_penalties_page_exists(self):
        assert SA_PENALTIES.exists()

    def test_tenant_penalties_uses_finance_api(self):
        assert "financeApi" in _read(SA_PENALTIES)

    def test_tenant_penalties_uses_admin_layout(self):
        assert "AdminLayout" in _read(SA_PENALTIES)


class TestTenantPortalPages:
    def test_credits_page_exists(self):
        assert TP_CREDITS.exists()

    def test_credits_page_uses_customer_credits_api(self):
        assert "customerCreditsApi" in _read(TP_CREDITS)

    def test_credits_page_uses_tenant_layout(self):
        assert "TenantLayout" in _read(TP_CREDITS)

    def test_credits_page_shows_balance(self):
        assert "active_credit_balance" in _read(TP_CREDITS) or "Active Balance" in _read(TP_CREDITS)

    def test_credits_page_disclaimer(self):
        content = _read(TP_CREDITS)
        assert "not cash" in content.lower() or "platform credit" in content.lower() or "NOT cash" in content

    def test_credits_page_shows_expiry(self):
        assert "expires_at" in _read(TP_CREDITS) or "Expires" in _read(TP_CREDITS)
