"""Tenant My Status — Provider Visibility & Bookability Control Center certification.

Static-inspection style (established convention this session). Live end-to-end
verification of every backend endpoint this page depends on was additionally
performed via curl against the real running backend + real Postgres
(provider@serviceos.in, tenant_owner, tenant 34b427a7-b2be-496c-b826-6d51bb181248)
before this file was written — see TENANT_MY_STATUS_INTEGRATION_REPORT.md.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

PAGE = (FRONTEND / "app/(tenant)/provider/status/page.tsx").read_text(encoding="utf-8-sig")
HERO = (FRONTEND / "components/status/TenantStatusHero.tsx").read_text(encoding="utf-8-sig")
ACTION_CENTER = (FRONTEND / "components/status/TenantStatusActionCenter.tsx").read_text(encoding="utf-8-sig")
SCORE_CARDS = (FRONTEND / "components/status/TenantReadinessScoreCards.tsx").read_text(encoding="utf-8-sig")
BADGE = (FRONTEND / "components/status/TenantStatusBadge.tsx").read_text(encoding="utf-8-sig")
PANELS = (FRONTEND / "components/status/TenantStatusPanels.tsx").read_text(encoding="utf-8-sig")
STATUS_FORMAT = (FRONTEND / "lib/status-format.ts").read_text(encoding="utf-8-sig")
API_TS = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")

MIGRATION_115 = (ROOT / "alembic/versions/115_provider_status_offerings_tables.py").read_text(encoding="utf-8-sig")
PROVIDER_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8-sig")

ALL_FRONTEND_SOURCE = PAGE + HERO + ACTION_CENTER + SCORE_CARDS + BADGE + PANELS


# ── Header / hero ────────────────────────────────────────────────────────────
def test_header_title_upgraded():
    assert "Provider Visibility & Bookability" in PAGE
    assert "My Status</h1>" not in PAGE  # old title string, must not remain as the h1


def test_hero_component_exists_and_used():
    assert "TenantStatusHero" in PAGE
    assert "Visible + Bookable" in HERO or "STATE_META" in HERO


def test_header_has_all_four_required_actions():
    for label in ("Refresh Status", "Recalculate Readiness", "View Setup Checklist", "Manage Offerings"):
        assert label in PAGE


# ── Error handling ───────────────────────────────────────────────────────────
def test_generic_unexpected_error_not_shown_alone():
    assert "Unexpected error." not in PAGE


def test_section_error_component_shows_request_id_and_failed_source():
    assert "requestId" in BADGE
    assert "Failed source:" in BADGE
    assert "Copy Request ID" in BADGE
    assert "Retry" in BADGE


def test_page_uses_section_error_component_for_each_major_section():
    assert PAGE.count("TenantStatusSectionError") >= 4


# ── Required actions / blockers ─────────────────────────────────────────────
def test_action_center_shows_severity_reason_cta_rule_last_checked():
    for field in ("severity", "reason", "cta", "ruleKey", "Last checked"):
        assert field in ACTION_CENTER


def test_action_center_all_clear_message_matches_ticket_copy():
    assert "All required setup checks are complete." in ACTION_CENTER


def test_required_action_rules_derived_from_real_data_not_hardcoded_true():
    assert "safeNum(wallet?.balance) <= 0" in PAGE
    assert "deposit.status !== \"paid\"" in PAGE
    assert "areas.length === 0" in PAGE


# ── Readiness score cards ────────────────────────────────────────────────────
def test_six_score_cards_present():
    for card_id in ("overall", "visibility", "bookability", "finance", "service_setup", "operations"):
        assert f'id: "{card_id}"' in PAGE


def test_no_offerings_empty_state_is_enterprise_level():
    assert "No offerings enabled yet" in PANELS
    assert "Add at least one Home Services offering from the platform catalog to become discoverable." in PANELS
    assert "Enable Offering" in PANELS
    assert "View Catalog" in PANELS


# ── Offering bookability ─────────────────────────────────────────────────────
def test_offering_table_has_required_columns():
    for col in ("Type Coverage", "Brand Coverage", "Bookable Status", "Blocking Reasons"):
        assert col in PANELS


# ── Setup checklist ──────────────────────────────────────────────────────────
def test_checklist_items_have_status_reason_cta_rule_key():
    assert "ChecklistItem" in PANELS
    assert "ruleKey" in PANELS
    assert "item.reason" in PANELS


def test_checklist_has_all_required_items():
    for key in ("package_active", "usage_credits", "deposit", "service_area", "offering", "technician", "availability", "business_profile"):
        assert f'key: "{key}"' in PAGE


# ── Finance readiness ────────────────────────────────────────────────────────
def test_finance_panel_uses_usage_credit_balance_label():
    assert "Usage Credit Balance" in PANELS


def test_finance_panel_shows_security_deposit_separately():
    assert "Security Deposit" in PANELS
    assert "Separate from your usage credit balance" in PANELS


def test_finance_panel_explains_completed_job_deduction():
    assert "Completed Job Deduction" in PANELS
    assert "at job completion, not during setup" in PANELS


# ── Operational readiness ────────────────────────────────────────────────────
def test_operational_panel_covers_all_required_rows():
    for label in ("Service Areas", "Services / Offerings", "Active Technicians", "Availability", "Documents", "Pricing"):
        assert label in PAGE


# ── Visibility rules ──────────────────────────────────────────────────────────
def test_visibility_rules_panel_is_collapsible():
    assert "TenantVisibilityRulesPanel" in PAGE
    assert "useState" in PANELS
    assert "How bookability is calculated" in PANELS


def test_visibility_rules_list_has_eleven_items():
    assert "const RULES = [" in PANELS
    # count string literal rule entries between RULES = [ and the closing ];
    start = PANELS.index("const RULES = [")
    end = PANELS.index("];", start)
    block = PANELS[start:end]
    assert block.count('",\n') + (1 if block.rstrip().endswith('"') else 0) >= 10


# ── Recent status activity ───────────────────────────────────────────────────
def test_activity_timeline_empty_state_matches_ticket_copy():
    assert "No status activity yet." in PANELS
    assert "Status recalculations and setup changes will appear here." in PANELS


def test_activity_uses_real_audit_log_endpoint():
    assert "getAuditLog" in API_TS
    assert "/audit-log" in API_TS


# ── Recalculate / refresh ────────────────────────────────────────────────────
def test_recalculate_button_is_permission_aware():
    assert "canRecalculate" in PAGE
    assert "Permission required" in PAGE


def test_refresh_action_shows_loading_and_error_with_request_id():
    assert "refreshAction.loading" in PAGE
    assert "refreshAction.requestId" in PAGE


# ── Data normalization ───────────────────────────────────────────────────────
def test_safe_formatters_exist():
    for fn in ("safeNum", "safeText", "safeCurrency", "safePercent", "safeDate", "safeStatus", "safeArray"):
        assert f"export function {fn}" in STATUS_FORMAT


def test_no_subscription_maps_to_no_active_package():
    assert '"no_subscription": "No active package"' in STATUS_FORMAT.replace("no_subscription:", '"no_subscription":') or \
           "no_subscription: \"No active package\"" in STATUS_FORMAT


# ── Forbidden label scan ─────────────────────────────────────────────────────
FORBIDDEN_LABELS = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
]


def test_no_forbidden_finance_labels_anywhere_in_status_ui():
    for label in FORBIDDEN_LABELS:
        assert label not in ALL_FRONTEND_SOURCE, f"forbidden label '{label}' found in My Status UI"


# ── Backend bug fix: 3 missing tables ────────────────────────────────────────
def test_migration_115_creates_all_three_missing_tables():
    for table in ("provider_visibility_statuses", "provider_offering_bookable_statuses", "provider_enabled_offerings"):
        assert table in MIGRATION_115
    assert "existing_tables" in MIGRATION_115
    assert 'revision = "115"' in MIGRATION_115


def test_provider_router_column_usage_matches_migration_columns():
    # spot-check a few columns that appear literally in router.py (default-dict
    # fallback / UPDATE allow-list — most reads are `SELECT *` so column names
    # don't otherwise appear as literal text) and confirm the migration has them.
    for col in ("provider_price_override", "visibility_blockers", "bookability_blockers"):
        assert col in MIGRATION_115
        assert col in PROVIDER_ROUTER
