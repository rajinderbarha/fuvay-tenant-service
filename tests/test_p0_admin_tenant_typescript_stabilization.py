"""P0 Admin Frontend TypeScript Stabilization Sprint — static-inspection
regression tests. This repo's frontend has no test runner (no jest/vitest,
no *.test.* files, no eslint config — `next lint` is a scaffold leftover and
Next.js 16 removed the `next lint` subcommand entirely, confirmed by
`npx next lint` erroring with "Invalid project directory"). Following this
session's established convention, these tests are Python source-inspection
tests run via pytest rather than a real frontend test runner."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TENANT_DETAIL = ROOT / "frontend/super-admin/app/admin/tenants/[id]/page.tsx"
SERVICE_SETUP = ROOT / "frontend/super-admin/app/admin/service-setup/page.tsx"
API_TS = ROOT / "frontend/super-admin/lib/api.ts"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ── Tenant Detail page compiles (proxy: required symbols present, no stray
#    references to symbols that don't exist in the API client) ────────────

def test_tenant_detail_uses_symbols_that_exist_in_api_client():
    api_src = _read(API_TS)
    tenant_src = _read(TENANT_DETAIL)
    assert "requestChanges:" in api_src and "adminTenantsApi.requestChanges" in tenant_src
    assert "sendNotification:" in api_src and "adminTenantsApi.sendNotification" in tenant_src
    assert "owner_name" in api_src
    assert "verification_status" in api_src
    assert "settlement_status" in api_src


def test_tenant_detail_defines_menu_item_style_used_by_dropdown():
    src = _read(TENANT_DETAIL)
    assert "const menuItemStyle" in src
    assert src.count("menuItemStyle") > 1  # defined AND used


# ── Tenant Detail payment fields render safely (nullable-safe fallbacks) ───

def test_tenant_detail_bookings_table_has_credit_and_payable_columns():
    src = _read(TENANT_DETAIL)
    assert "ServiceOS Credit Applied" in src
    assert "Payable To Provider" in src
    assert "bk.credit_applied" in src
    assert "bk.payable_amount ?? bk.quoted_price" in src


def test_tenant_detail_jobs_table_has_payable_and_deduction_columns():
    # FINAL-L5-05E: the Jobs tab was migrated off legacy jobsApi onto the
    # canonical service_jobs list (finalRecordsAdminApi.listForTenant), which
    # returns real collected_amount + completed_job_deduction_credits fields
    # (batch-joined from usage_credit_ledger, not the old payable_to_provider/
    # quoted_price legacy-jobs-table fields).
    src = _read(TENANT_DETAIL)
    assert "Completed Job Deduction" in src
    assert "j.completed_job_deduction_credits" in src


def test_tenant_detail_payment_fields_use_nullable_safe_access():
    src = _read(TENANT_DETAIL)
    # every new payment-breakdown read in the tables added this sprint must
    # be guarded (?? fallback or != null check), never a bare property access
    # that would throw/NaN-render on a missing field.
    assert "bk.credit_applied != null" in src
    assert "(bk.payable_amount ?? bk.quoted_price) != null" in src
    assert "j.collected_amount != null" in src
    assert "j.completed_job_deduction_credits != null" in src


def test_booking_type_has_credit_and_payable_fields():
    src = _read(API_TS)
    assert "credit_applied?: number; payable_amount?: number;" in src


def test_shared_payment_breakdown_types_exist():
    src = _read(API_TS)
    assert "export type BookingPaymentBreakdown" in src
    assert "export type JobPaymentBreakdown" in src
    assert '"customer_pays_provider_directly"' in src


# ── Tenant Detail does not show payout/wallet language ──────────────────────

def test_tenant_detail_has_no_forbidden_payout_language():
    src = _read(TENANT_DETAIL)
    forbidden = ["Cash Wallet", "Payout", "Withdrawable Balance", "Escrow"]
    for term in forbidden:
        assert term not in src, f"tenant detail page must not contain '{term}'"


def test_tenant_detail_uses_correct_terminology():
    src = _read(TENANT_DETAIL)
    assert "Usage Credit Balance" in src
    assert "Usage Credit Ledger" in src
    assert "Security Deposit" in src
    assert "Add Usage Credits" in src


# ── Service Setup hub renders / module links correct ────────────────────────

def test_service_setup_hub_has_kpi_summary_cards():
    src = _read(SERVICE_SETUP)
    for label in ["Total Templates", "Published Templates", "Draft Templates",
                  "Active Wizard Drafts", "Total Bulk Runs", "Failed Runs"]:
        assert label in src


def test_service_setup_hub_links_to_all_nine_modules():
    src = _read(SERVICE_SETUP)
    for href in [
        "/admin/service-setup/templates", "/admin/service-setup/bulk-wizard",
        "/admin/service-setup/bulk-runs", "/admin/service-setup/brands",
        "/admin/service-setup/brand-requests", "/admin/service-setup/brand-templates",
        "/admin/service-setup/option-groups", "/admin/service-setup/service-options",
        "/admin/service-setup/issue-types",
    ]:
        assert href in src


def test_service_setup_module_subroutes_exist_on_disk():
    base = ROOT / "frontend/super-admin/app/admin/service-setup"
    for d in ["templates", "bulk-wizard", "bulk-runs", "brands", "brand-requests",
              "brand-templates", "option-groups", "service-options", "issue-types"]:
        assert (base / d / "page.tsx").exists(), f"missing page.tsx for {d}"


# ── adminTenantsApi double-wrap bug (found live this sprint, in tenants/page.tsx) ──

def test_admin_tenants_api_does_not_double_wrap_apifetch_generic():
    src = _read(API_TS)
    assert "apiFetch<TenantsSummary>" in src
    assert "apiFetch<TenantsInsights>" in src
    assert "apiFetch<{ data: TenantsSummary }>" not in src
    assert "apiFetch<{ data: TenantsInsights }>" not in src


# ── ServiceSetupTemplate table collision + bulk-setup-runs schema drift ─────
# (both found live this sprint, both blocked /admin/service-setup entirely) ──

def test_legacy_service_setup_template_model_renamed_to_avoid_collision():
    src = _read(ROOT / "app/engines/admin_catalog/models.py")
    assert 'service_setup_templates_legacy_34f' in src
    assert 'service_setup_template_items_legacy_34f' in src


def test_migration_099_adds_bulk_setup_runs_updated_at():
    src = _read(ROOT / "alembic/versions/099_admin_bulk_setup_runs_updated_at.py")
    assert 'down_revision = "098"' in src
    assert '"admin_bulk_setup_runs"' in src
    assert '"service_setup_bulk_runs"' in src
    assert '"updated_at"' in src


def test_service_setup_hub_uses_bulk_wizard_api_not_stale_bulk_setup_api():
    src = _read(SERVICE_SETUP)
    assert "bulkWizardApi" in src
    assert "bulkSetupApi" not in src


def test_template_detail_page_uses_current_service_setup_templates_api():
    src = _read(ROOT / "frontend/super-admin/app/admin/service-setup/templates/[templateId]/page.tsx")
    assert "serviceSetupTemplatesApi" in src
    assert "setupTemplateApi" not in src
    assert "serviceSetupTemplatesApi.get(" in src


# ── service-setup/templates wrong-hooks-import bug (found live this sprint) ──

def test_service_setup_templates_page_imports_hooks_from_correct_path():
    src = _read(ROOT / "frontend/super-admin/app/admin/service-setup/templates/page.tsx")
    assert 'from "../../../../hooks/useApi"' in src
    assert '"../../../../lib/hooks"' not in src


def test_service_setup_hub_has_error_and_empty_states():
    src = _read(SERVICE_SETUP)
    assert "Could not load some setup data" in src
    assert "Request ID" in src
    assert "No templates yet." in src
    assert "No runs yet." in src
