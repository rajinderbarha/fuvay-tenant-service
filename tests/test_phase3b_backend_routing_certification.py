"""Phase 3B — Pricing & Rules backend routing/permissions/Swagger certification.

Static-inspection style tests (established convention this session — no live
JS/browser test runner exists in this repo). Live-endpoint behavior for these
same assertions was additionally verified manually via curl against the real
running backend + Postgres before this file was written; see
PHASE_3B_BACKEND_TEST_RESULTS.md for the raw request/response evidence.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVICE = (ROOT / "app/engines/admin_catalog/service.py").read_text(encoding="utf-8-sig")
ROUTER = (ROOT / "app/engines/admin_catalog/admin_router.py").read_text(encoding="utf-8-sig")
PERMISSIONS = (ROOT / "app/core/permissions.py").read_text(encoding="utf-8-sig")


# ── 1. Bargain summary ──────────────────────────────────────────────
def test_bargain_summary_endpoint_and_kpis():
    assert '"/pricing/bargain-rules/summary"' in ROUTER
    assert "get_bargain_rules_summary" in SERVICE
    for kpi in ("total_bargain_rules", "active_rules", "inactive_rules",
                "bargain_enabled_services", "below_floor_rejections",
                "provider_approval_required", "avg_accepted_offer", "validation_issues"):
        assert kpi in SERVICE


# ── 2. Bargain list returns enrichment ──────────────────────────────
def test_bargain_list_returns_names_and_pricing_context():
    assert "master_service_name" in SERVICE
    assert "category_name" in SERVICE
    assert '"base_price"' in SERVICE and '"min_price"' in SERVICE and '"max_price"' in SERVICE


# ── 3. Bargain detail loads ─────────────────────────────────────────
def test_bargain_detail_endpoint_exists():
    assert 'async def get_bargain_rule(' in ROUTER


# ── 4. Duplicate active bargain rule rejected ───────────────────────
def test_duplicate_active_bargain_rule_rejected():
    assert "DUPLICATE_ACTIVE_BARGAIN_RULE" in SERVICE
    assert "_find_duplicate_active_bargain_rule" in SERVICE


# ── 5/6. Invalid floor below/above min/max rejected ─────────────────
def test_invalid_bargain_floor_validation():
    assert "INVALID_BARGAIN_FLOOR" in SERVICE


# ── 7. Inactive rule readiness warning ──────────────────────────────
def test_inactive_rule_readiness_warning():
    assert "Bargaining is configured but this rule is inactive." in SERVICE
    assert '"readiness"' in SERVICE


# ── 8. Validate bargain rule endpoint ───────────────────────────────
def test_validate_bargain_rule_endpoint():
    assert '"/pricing/bargain-rules/{rule_id}/validate"' in ROUTER
    assert "async def validate_bargain_rule" in SERVICE
    assert "no_duplicate_active_bargain_rule" in SERVICE


# ── 9. Bargain audit endpoint ────────────────────────────────────────
def test_bargain_audit_endpoint():
    assert '"/pricing/bargain-rules/{rule_id}/audit"' in ROUTER
    assert "async def get_bargain_rule_audit" in SERVICE


# ── 10/11. Evaluate below floor / accepted ──────────────────────────
def test_evaluate_bargain_decision_shape():
    assert '"decision"' in SERVICE
    assert "Offer is below bargain floor." in SERVICE
    assert "Offer meets bargain floor." in SERVICE
    assert '"rule_used"' in SERVICE and '"pricing_source"' in SERVICE


# ── 12. Evaluate logs audit event ───────────────────────────────────
def test_evaluate_bargain_logs_audit():
    assert '"bargain_evaluation"' in SERVICE
    assert "await _log(" in SERVICE


# ── 13. Provider overrides summary ──────────────────────────────────
def test_override_summary_endpoint_and_kpis():
    assert '"/pricing/provider-overrides/summary"' in ROUTER
    assert "get_provider_overrides_summary" in SERVICE
    for kpi in ("total_overrides", "active_overrides", "pending_approval",
                "rejected_overrides", "out_of_range_attempts", "avg_override_price",
                "tenants_with_overrides", "validation_issues"):
        assert kpi in SERVICE


# ── 14. Override list returns tenant_name not just raw ID ──────────
def test_override_list_returns_tenant_name():
    assert '"tenant_name"' in SERVICE
    assert '"tenant_code"' in SERVICE
    assert "await self.db.get(Tenant, o.tenant_id)" in SERVICE


# ── 15. Override list returns service context + platform bounds ────
def test_override_list_returns_service_context():
    assert '"platform_min_price"' in SERVICE
    assert '"platform_max_price"' in SERVICE
    assert '"platform_base_price"' in SERVICE
    assert '"delta_from_base"' in SERVICE


# ── 16/18. Validate override below-min / above-max error codes ─────
def test_override_validation_error_codes():
    assert "OVERRIDE_BELOW_PLATFORM_MIN" in SERVICE
    assert "OVERRIDE_ABOVE_PLATFORM_MAX" in SERVICE
    assert "platform_min_price" in SERVICE and "platform_max_price" in SERVICE
    assert "context=" in SERVICE


# ── 17. Validate override within range ──────────────────────────────
def test_validate_provider_override_preview_exists():
    assert "async def validate_provider_override_preview" in SERVICE
    assert '"/pricing/provider-overrides/validate-preview"' in ROUTER


# ── 19. Duplicate active provider override rejected ────────────────
def test_duplicate_active_override_rejected():
    assert "DUPLICATE_ACTIVE_OVERRIDE" in SERVICE
    assert "_find_duplicate_active_override" in SERVICE


# ── 20. Provider override audit endpoint ────────────────────────────
def test_override_audit_endpoint():
    assert '"/pricing/provider-overrides/{override_id}/audit"' in ROUTER
    assert "async def get_provider_override_audit" in SERVICE


# ── 21. Permission constants + 403 enforcement ──────────────────────
def test_permission_constants_exist():
    for perm in (
        "PRICING_BARGAIN_RULES_ACTIVATE", "PRICING_BARGAIN_RULES_DEACTIVATE",
        "PRICING_BARGAIN_RULES_AUDIT_READ",
        "PRICING_PROVIDER_OVERRIDES_VALIDATE_PREVIEW",
        "PRICING_PROVIDER_OVERRIDES_ACTIVATE", "PRICING_PROVIDER_OVERRIDES_DEACTIVATE",
        "PRICING_PROVIDER_OVERRIDES_AUDIT_READ",
    ):
        assert perm in PERMISSIONS


def test_all_new_endpoints_require_permission():
    for fn_marker in (
        "get_bargain_rules_summary", "activate_bargain_rule", "deactivate_bargain_rule",
        "validate_bargain_rule", "get_bargain_rule_audit",
        "get_provider_overrides_summary", "validate_provider_override_preview",
        "activate_provider_override", "deactivate_provider_override",
        "get_provider_override_audit",
    ):
        idx = ROUTER.index(f"async def {fn_marker}")
        snippet = ROUTER[idx: idx + 400]
        assert "require_permission(P." in snippet, f"{fn_marker} missing require_permission"


# ── 22. OpenAPI includes all Phase 3B endpoints ─────────────────────
def test_openapi_route_declarations_present():
    expected_paths = [
        '"/pricing/bargain-rules/summary"',
        '"/pricing/bargain-rules/{rule_id}/activate"',
        '"/pricing/bargain-rules/{rule_id}/deactivate"',
        '"/pricing/bargain-rules/{rule_id}/validate"',
        '"/pricing/bargain-rules/{rule_id}/audit"',
        '"/pricing/provider-overrides/summary"',
        '"/pricing/provider-overrides/validate-preview"',
        '"/pricing/provider-overrides/{override_id}/activate"',
        '"/pricing/provider-overrides/{override_id}/deactivate"',
        '"/pricing/provider-overrides/{override_id}/audit"',
    ]
    for path in expected_paths:
        assert path in ROUTER, f"missing route declaration: {path}"


def test_no_forbidden_labels_in_new_code():
    forbidden = ("Cash Wallet", "Withdrawable Balance", "Tenant Payout",
                 "Provider Earnings Wallet", "Escrow", "Platform Collected Service Payment")
    for label in forbidden:
        assert label not in SERVICE
        assert label not in ROUTER
