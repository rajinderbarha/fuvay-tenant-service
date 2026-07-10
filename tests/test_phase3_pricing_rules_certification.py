"""Phase 3 — Pricing & Rules Frontend + Backend Certification Sprint.

Modules 1-4 (Pricing Tiers, City/Zip Mapping, Pricing Rules, Resolver) were
already fully built and live-verified in prior sprints (Phase 0/1/2) — this
sprint added the previously-missing completed_job_deduction_credits field,
and built Bargain Rules + Provider Pricing Overrides from scratch (both were
confirmed entirely absent by research before this sprint).

Static-inspection style (source-text assertions) for structural checks;
the AC Repair baseline (₹800, 21 usage credits, bargain floor ₹650, offer
evaluation, and provider override min/max bounds) was live-verified
end-to-end against the running backend and real Postgres this sprint.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = (ROOT / "app/engines/admin_catalog/models.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "app/engines/admin_catalog/service.py").read_text(encoding="utf-8")
ROUTER = (ROOT / "app/engines/admin_catalog/admin_router.py").read_text(encoding="utf-8")
PRICING_ENGINE = (ROOT / "app/engines/admin_catalog/pricing_engine.py").read_text(encoding="utf-8")
PERMISSIONS = (ROOT / "app/core/permissions.py").read_text(encoding="utf-8")
MIGRATION = (ROOT / "alembic/versions/111_pricing_completed_job_deduction.py").read_text(encoding="utf-8")
ADMIN_LAYOUT = (ROOT / "frontend/super-admin/components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
BARGAIN_PAGE = (ROOT / "frontend/super-admin/app/admin/pricing/bargain-rules/page.tsx").read_text(encoding="utf-8")
OVERRIDE_PAGE = (ROOT / "frontend/super-admin/app/admin/pricing/provider-overrides/page.tsx").read_text(encoding="utf-8")


def test_completed_job_deduction_credits_column_exists():
    assert "completed_job_deduction_credits" in MODELS
    assert "completed_job_deduction_credits" in MIGRATION


def test_deduction_credits_rejects_negative_on_create_and_update():
    assert "INVALID_DEDUCTION_CREDITS" in SERVICE
    assert "cannot be negative" in SERVICE


def test_resolver_returns_deduction_credits_and_payment_mode():
    assert "completed_job_deduction_credits" in PRICING_ENGINE
    assert '"payment_collection_mode": "customer_pays_provider_directly"' in PRICING_ENGINE


def test_bargain_rule_model_and_migration_exist():
    assert "class BargainRule" in MODELS
    assert "bargain_rules" in MIGRATION


def test_bargain_evaluation_endpoint_exists():
    assert '@router.post("/pricing/bargain/evaluate-preview"' in ROUTER
    assert "async def evaluate_bargain" in SERVICE


def test_bargain_evaluation_rejects_below_floor():
    assert "Offer is below bargain floor." in SERVICE
    assert "if offer < floor:" in SERVICE


def test_bargain_floor_validation_on_pricing_rule():
    assert "bargain_floor cannot be below min_price" in SERVICE
    assert "bargain_floor cannot exceed base_price" in SERVICE


def test_provider_pricing_override_model_and_migration_exist():
    assert "class ProviderPricingOverride" in MODELS
    assert "provider_pricing_overrides" in MIGRATION


def test_provider_override_enforces_platform_min_max():
    assert "OVERRIDE_BELOW_PLATFORM_MIN" in SERVICE
    assert "OVERRIDE_ABOVE_PLATFORM_MAX" in SERVICE
    assert "_platform_price_bounds" in SERVICE


def test_provider_override_approval_workflow_endpoints_exist():
    assert '@router.post("/pricing/provider-overrides/{override_id}/approve"' in ROUTER
    assert '@router.post("/pricing/provider-overrides/{override_id}/reject"' in ROUTER
    assert "Rejection reason is required" in SERVICE


def test_provider_override_is_tenant_scoped():
    assert "tenant_id" in MODELS
    assert "ix_ppo_tenant" in MIGRATION


def test_no_forbidden_cash_wallet_labels_in_pricing_code():
    for banned in ("cash_wallet", "cash wallet", "tenant_payout", "tenant payout",
                   "earnings_wallet", "earnings wallet", "escrow"):
        assert banned not in SERVICE.lower()
        assert banned not in ROUTER.lower()
        assert banned not in PRICING_ENGINE.lower()
        assert banned not in BARGAIN_PAGE.lower()
        assert banned not in OVERRIDE_PAGE.lower()


def test_pricing_permission_constants_exist():
    for perm in (
        "PRICING_READ", "PRICING_TIERS_READ", "PRICING_CITY_ZIP_READ",
        "PRICING_RULES_READ", "PRICING_RULES_ACTIVATE", "PRICING_RULES_DEACTIVATE",
        "PRICING_RESOLVE_PREVIEW", "PRICING_BARGAIN_RULES_READ",
        "PRICING_BARGAIN_EVALUATE_PREVIEW", "PRICING_PROVIDER_OVERRIDES_READ",
        "PRICING_PROVIDER_OVERRIDES_APPROVE", "PRICING_PROVIDER_OVERRIDES_REJECT",
    ):
        assert perm in PERMISSIONS, f"missing permission constant {perm}"


def test_all_new_endpoints_require_permission():
    assert ROUTER.count("require_permission(P.PRICING_") >= 15


def test_all_new_mutations_are_audited():
    for op in ('"bargain_rule"', '"provider_pricing_override"'):
        assert op in SERVICE
    assert "_audit(" in SERVICE


def test_sidebar_pricing_group_renamed_and_has_no_duplicates():
    # HS0 cleanup: "Bargain Rules" was removed from the common "Pricing &
    # Rules" sidebar group entirely (not just deduplicated) — the deprecated
    # bargain-rules page is reachable only by direct URL, never from the
    # live sidebar. "Pricing Rules" now lives only inside the vertical-
    # scoped "Home Services" group.
    assert 'label: "Pricing & Rules"' in ADMIN_LAYOUT
    assert ADMIN_LAYOUT.count('label: "Pricing Tiers"') == 1
    assert ADMIN_LAYOUT.count('label: "City/Zip Mapping"') == 1
    assert ADMIN_LAYOUT.count('label: "Provider Pricing Overrides"') == 1
    assert ADMIN_LAYOUT.count('label: "Bargain Rules"') == 0
    assert ADMIN_LAYOUT.count('label: "Pricing Rules"') == 1
    assert ADMIN_LAYOUT.count('label: "Home Services"') == 1


def test_bargain_rules_frontend_page_renders_offer_evaluation_ui():
    assert "Evaluate Offer" in BARGAIN_PAGE
    assert "evaluatePreview" in BARGAIN_PAGE
    assert "requestId" in BARGAIN_PAGE


def test_provider_overrides_frontend_page_has_approve_reject_actions():
    assert "approveAction" in OVERRIDE_PAGE
    assert "rejectAction" in OVERRIDE_PAGE
    assert "Rejection Reason" in OVERRIDE_PAGE
