"""HS3 — Admin Tier Pricing + Type-Dependent Brand Pricing certification.

Real gaps found and fixed this sprint in
`AdminCatalogService.create_pricing_rule` (app/engines/admin_catalog/service.py):

1. A brand override on a type-based service (pricing_model == "range")
   could previously be created with no service_type_id at all — the
   exact "global brand price across every type" bug this whole HS
   pricing-fix lineage exists to prevent. Fixed: raises
   SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING (422).
2. Duplicate service+type+brand+tier pricing rules were only guarded by
   a DB unique constraint (migration 120) that does NOT catch duplicates
   when tier_id is NULL (Postgres treats multiple NULLs as distinct) —
   the common case for "global, no tier" rules in this dev environment
   (no tiers seeded). Fixed: an explicit application-level duplicate
   check now runs before insert, raising DUPLICATE_TYPE_BRAND_PRICING_RULE
   (409) regardless of whether tier_id is set.

Both fixes were live-verified against the real running backend and the
real AC Repair / Window AC / Split AC / LG / Samsung seed data — see
HS3_TYPE_DEPENDENT_BRAND_PRICING_REPORT.md for the full transcript.

Mirrors the client-side check added to the admin pricing-rules page for
fast feedback (backend remains the source of truth).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/super-admin"

SERVICE_PY = (ROOT / "app/engines/admin_catalog/service.py").read_text(encoding="utf-8-sig")
PAGE = (FRONTEND / "app/admin/home-services/pricing-rules/page.tsx").read_text(encoding="utf-8-sig")


def _create_rule_fn() -> str:
    return SERVICE_PY.split("async def create_pricing_rule")[1].split("async def update_pricing_rule")[0]


# ── 1. Route / page structure ─────────────────────────────────────────────────
def test_route_exists():
    assert (FRONTEND / "app/admin/home-services/pricing-rules/page.tsx").exists()


def test_table_columns_type_before_brand():
    idx_type = PAGE.index('"Type"')
    idx_brand = PAGE.index('"Brand"')
    assert idx_type < idx_brand
    for col in ["Service", "Type", "Brand", "Zone/Tier", "Admin Min", "Admin Max",
                "Platform Fee", "Completed Job Deduction", "Status", "Actions"]:
        assert col in PAGE


# ── 2. Backend: brand override requires type for type-based service ──────────
def test_backend_brand_override_requires_type():
    fn = _create_rule_fn()
    assert "SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING" in fn
    assert 'data.get("brand_id") and model == "range" and not data.get("service_type_id")' in fn


def test_frontend_brand_override_requires_type():
    assert "Service type is required when adding brand pricing for a type-based service." in PAGE


# ── 3. Backend: duplicate service+type+brand+tier rejected ───────────────────
def test_backend_duplicate_rule_rejected():
    fn = _create_rule_fn()
    assert "DUPLICATE_TYPE_BRAND_PRICING_RULE" in fn
    assert "dup_stmt" in fn


def test_backend_duplicate_check_handles_null_tier():
    # The DB unique constraint alone doesn't catch NULL-tier duplicates
    # (Postgres NULL != NULL) — the application-level check must handle it.
    fn = _create_rule_fn()
    assert "ServicePricingRule.tier_id.is_(None)" in fn
    assert "ServicePricingRule.service_type_id.is_(None)" in fn
    assert "ServicePricingRule.brand_id.is_(None)" in fn


def test_backend_also_catches_db_level_duplicate_as_fallback():
    fn = _create_rule_fn()
    assert "IntegrityError" in fn
    assert "uq_spr_service_type_brand_tier" in fn


# ── 4. Admin range validation (pre-existing, re-confirmed) ────────────────────
def test_backend_min_max_validation():
    fn = _create_rule_fn()
    assert "INVALID_PRICE_RANGE" in fn
    assert "min_price > max_price" in fn


def test_backend_deduction_credits_validation():
    fn = _create_rule_fn()
    assert "INVALID_DEDUCTION_CREDITS" in fn
    assert "deduction_credits < 0" in fn


def test_frontend_admin_range_validation():
    assert "Admin Minimum Price must be greater than 0." in PAGE
    assert "Admin Maximum Price must be greater than or equal to Admin Minimum Price." in PAGE
    assert "Platform Fee must be greater than or equal to 0." in PAGE
    assert "Completed Job Deduction must be greater than or equal to 0." in PAGE


# ── 5. Customer price calculation (real function, unchanged this sprint) ─────
def test_symmetric_formula_matches_hs3_example():
    """Admin 300-500, provider 350-420, fee 10% -> Low 385, High 462 (ticket's own example)."""
    import sys
    sys.path.insert(0, str(ROOT))
    from app.engines.admin_catalog.bargain_engine import compute_symmetric_customer_price_tiers
    r = compute_symmetric_customer_price_tiers(350, 420, 10)
    assert r["low_price"] == 385.0
    assert r["high_price"] == 462.0
    assert r["payment_mode"] == "customer_pays_provider_directly"


def test_low_and_high_include_platform_fee():
    import sys
    sys.path.insert(0, str(ROOT))
    from app.engines.admin_catalog.bargain_engine import compute_symmetric_customer_price_tiers
    r = compute_symmetric_customer_price_tiers(350, 420, 10)
    assert r["low_price"] != 350.0  # low must not equal pre-fee provider min
    assert r["high_price"] != 420.0  # high must not equal pre-fee provider max


# ── 6. Provider boundary enforcement (tenant side — HS2 sprint) ──────────────
def test_provider_boundary_enforced_on_tenant_side():
    tenant_service_py = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")
    assert "TENANT_PRICE_BELOW_ADMIN_MIN" in tenant_service_py
    assert "TENANT_PRICE_ABOVE_ADMIN_MAX" in tenant_service_py


# ── 7. Forbidden labels ────────────────────────────────────────────────────────
FORBIDDEN = [
    "Manual Bargain Setup", "Bargain Rule Builder", "Bargain Settings",
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance", "Credit Wallet Health",
]


def test_no_forbidden_labels():
    for term in FORBIDDEN:
        assert term not in PAGE, f"forbidden label found: {term}"


def test_payment_mode_says_pays_provider_directly():
    bargain_engine = (ROOT / "app/engines/admin_catalog/bargain_engine.py").read_text(encoding="utf-8-sig")
    assert '"customer_pays_provider_directly"' in bargain_engine
    for bad in ["Platform Collected Payment", "Escrow", "Provider Payout", "Withdraw"]:
        assert bad not in bargain_engine
