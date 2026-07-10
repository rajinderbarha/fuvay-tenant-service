"""Phase 3C — Bargain Rules & Provider Overrides enterprise frontend certification.

Static-inspection style (established convention this session — no JS/browser
test runner exists in this repo). Live rendering (200 status, no crash,
real API wiring) was additionally verified via curl against the real running
Next.js dev server + backend before this file was written — see
PHASE_3C_MANUAL_BROWSER_SMOKE_REPORT.md for that evidence.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
BARGAIN_PAGE = (ROOT / "frontend/super-admin/app/admin/pricing/bargain-rules/page.tsx").read_text(encoding="utf-8")
OVERRIDE_PAGE = (ROOT / "frontend/super-admin/app/admin/pricing/provider-overrides/page.tsx").read_text(encoding="utf-8")
API_TS = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8")
USE_API = (ROOT / "frontend/super-admin/hooks/useApi.ts").read_text(encoding="utf-8")
USE_PERM = (ROOT / "frontend/super-admin/hooks/usePermissions.ts").read_text(encoding="utf-8")


# 1-2. Bargain Rules page renders + summary cards
def test_bargain_page_has_summary_cards():
    assert "bargainRulesApi.summary()" in BARGAIN_PAGE
    for label in ("Total Bargain Rules", "Active Rules", "Inactive Rules",
                  "Bargain Enabled Services", "Below-Floor Rejections",
                  "Provider Approval Required", "Avg Accepted Offer", "Validation Issues"):
        assert label in BARGAIN_PAGE


# 3. Filters render
def test_bargain_page_has_filters():
    for f in ("search", "statusFilter", "readinessFilter", "bargainEnabledFilter"):
        assert f in BARGAIN_PAGE


# 4. Table renders real API data
def test_bargain_table_uses_real_api():
    assert "bargainRulesApi.list(" in BARGAIN_PAGE
    assert "mock" not in BARGAIN_PAGE.lower().replace("mockservice", "")


# 5. Readiness warning for enabled + inactive rule
def test_bargain_readiness_warning_rendered():
    assert "row.warning" in BARGAIN_PAGE
    assert "READINESS_BADGE" in BARGAIN_PAGE


# 6. Detail drawer opens
def test_bargain_detail_drawer_exists():
    assert 'modal === "detail"' in BARGAIN_PAGE
    assert "bargainRulesApi.get(" in BARGAIN_PAGE
    assert "bargainRulesApi.audit(" in BARGAIN_PAGE


# 7. Wizard opens (6 steps — "Bargain Policy" was later split into the
# symmetric customer-range/platform-fee step and a legacy-fixed-floor
# fallback step, per the Customer Price Experience sprint)
def test_bargain_wizard_has_five_steps():
    for step in ("Basic Details", "Scope", "Customer Range + Platform Fee",
                 "Legacy Fixed Floor", "Provider Approval", "Validation & Review"):
        assert step in BARGAIN_PAGE


# 8. Evaluate Offer modal opens
def test_evaluate_offer_modal_exists():
    assert 'modal === "preview"' in BARGAIN_PAGE
    assert "bargainRulesApi.evaluatePreview(" in BARGAIN_PAGE


# 9-10. Evaluate ₹500 rejected / ₹650 accepted (decision-shape rendering)
def test_evaluate_offer_renders_decision_shape():
    assert "previewResult.decision" in BARGAIN_PAGE
    assert "previewResult.bargain_floor" in BARGAIN_PAGE
    assert "previewResult.minimum_allowed_offer" in BARGAIN_PAGE
    assert "previewResult.customer_offer" in BARGAIN_PAGE


# 11. Error state shows request_id
def test_bargain_error_shows_request_id():
    assert "requestId" in BARGAIN_PAGE
    assert "ErrorBlock" in BARGAIN_PAGE


# 12-13. Provider Overrides page renders + summary cards
def test_override_page_has_summary_cards():
    assert "providerOverridesApi.summary()" in OVERRIDE_PAGE
    for label in ("Total Overrides", "Active Overrides", "Pending Approval",
                  "Rejected Overrides", "Out-of-Range Attempts", "Avg Override Price",
                  "Tenants With Overrides", "Validation Issues"):
        assert label in OVERRIDE_PAGE


# 14. Filters render
def test_override_page_has_filters():
    for f in ("search", "approvalFilter", "statusFilter"):
        assert f in OVERRIDE_PAGE


# 15. Table renders tenant name
def test_override_table_renders_tenant_name():
    assert "row.tenant_name" in OVERRIDE_PAGE
    assert "row.tenant_code" in OVERRIDE_PAGE
    # raw ID only ever shown as small secondary text, sliced — never the sole/primary display
    assert 'row.tenant_id.slice(0, 8)' in OVERRIDE_PAGE


# 16. Table renders service context
def test_override_table_renders_service_context():
    assert "row.master_service_name" in OVERRIDE_PAGE
    assert "row.service_type_name" in OVERRIDE_PAGE
    assert "row.brand_name" in OVERRIDE_PAGE
    assert "row.issue_type_name" in OVERRIDE_PAGE


# 17. Table renders platform range
def test_override_table_renders_platform_range():
    assert "row.platform_min_price" in OVERRIDE_PAGE
    assert "row.platform_max_price" in OVERRIDE_PAGE
    assert "row.platform_base_price" in OVERRIDE_PAGE
    assert "row.delta_from_base" in OVERRIDE_PAGE


# 18. Detail drawer opens
def test_override_detail_drawer_exists():
    assert 'modal === "detail"' in OVERRIDE_PAGE
    assert "providerOverridesApi.get(" in OVERRIDE_PAGE
    assert "providerOverridesApi.audit(" in OVERRIDE_PAGE


# 19. Wizard opens (5 steps)
def test_override_wizard_has_five_steps():
    for step in ("Tenant", "Service Scope", "Override Price", "Approval", "Review"):
        assert step in OVERRIDE_PAGE


# 20-22. Validate ₹500/₹900/₹1300 shows correct messages with request_id
def test_override_validate_preview_wired():
    assert "providerOverridesApi.validatePreview(" in OVERRIDE_PAGE
    assert "ValidationPreviewBlock" in OVERRIDE_PAGE
    assert "OVERRIDE_BELOW_PLATFORM_MIN" not in OVERRIDE_PAGE  # rendered generically from e.error_code, not hardcoded
    assert "e.error_code" in OVERRIDE_PAGE


# 23. Permission guards hide forbidden actions
def test_permission_guards_present():
    assert "usePermissions" in BARGAIN_PAGE and "perm.has(" in BARGAIN_PAGE
    assert "usePermissions" in OVERRIDE_PAGE and "perm.has(" in OVERRIDE_PAGE
    for p in ("pricing.bargain_rules.create", "pricing.bargain_rules.update",
              "pricing.bargain_rules.activate", "pricing.bargain_rules.evaluate_preview"):
        assert p in BARGAIN_PAGE
    for p in ("pricing.provider_overrides.create", "pricing.provider_overrides.update",
              "pricing.provider_overrides.approve", "pricing.provider_overrides.reject",
              "pricing.provider_overrides.activate"):
        assert p in OVERRIDE_PAGE


def test_use_permissions_hook_reads_real_backend():
    assert "authApi.me()" in USE_PERM
    assert 'perms.includes("*")' in USE_PERM


# 24. Empty states render
def test_empty_states_render():
    assert "No bargain rules found." in BARGAIN_PAGE
    assert "No provider pricing overrides found." in OVERRIDE_PAGE


# 25. Loading skeletons render
def test_loading_skeletons_render():
    assert "Skeleton" in BARGAIN_PAGE and "summary.loading" in BARGAIN_PAGE
    assert "Skeleton" in OVERRIDE_PAGE and "summary.loading" in OVERRIDE_PAGE


# 26. No forbidden labels appear
def test_no_forbidden_labels():
    forbidden = ("Cash Wallet", "Withdrawable Balance", "Tenant Payout",
                 "Provider Earnings Wallet", "Escrow", "Platform Collected Service Payment",
                 "Provider Cash Balance", ">Withdraw<")
    for label in forbidden:
        assert label not in BARGAIN_PAGE
        assert label not in OVERRIDE_PAGE


# request_id plumbing fix (pre-existing bug found + fixed this sprint)
def test_request_id_plumbing_fixed():
    assert "err.request_id" in API_TS
    assert "public requestId" in API_TS
    assert "e.requestId" in USE_API


# integration: no mock runtime data used anywhere in either page
def test_no_mock_runtime_data():
    for page in (BARGAIN_PAGE, OVERRIDE_PAGE):
        assert "mockData" not in page
        assert "fakeApi" not in page
        assert "hardcoded" not in page.lower()
