"""FIX — Tenant Type-Specific Brand Price Inputs certification.

Root cause: the tenant Service Setup wizard's `/tenant/setup/services`
page had a real, type-blind brand pricing UI — `BrandPricingState` had
no `typeId` field at all, `getBrandPricing(tenantServiceId)` fetched a
single flat brand list with no type context, and
`setBrandPricing(tenantServiceId, brandId, min, max)` never passed
`service_type_id`. The Review & Publish matrix rendered the SAME flat
brand list under every type row, so a single LG override literally
displayed identical prices under both Window AC and Split AC — the
exact bug this ticket describes.

The backend (fixed in an earlier "Type-Dependent Brand Pricing" sprint
this session — migration 120, tenant_service.py) already fully supports
type-scoped brand pricing, including the SERVICE_TYPE_REQUIRED_FOR_
BRAND_PRICING validation and a service_type_id-aware unique constraint.
The API client (lib/api.ts) already accepted an optional serviceTypeId
parameter on both getBrandPricing/setBrandPricing. The bug was entirely
in this one page never using that parameter.

Fixed by: adding typeId/typeName to BrandPricingState, fetching brand
pricing per selected type (one call per type, tagged with typeId),
passing typeId through on every save, and restructuring both the Step 4
UI and the Review matrix to group/filter by type instead of showing one
flat brand list everywhere.

Live-verified this sprint against the real running backend and real DB:
saved Window AC + LG (₹400-480) and Split AC + LG (₹700-850)
independently, confirmed 2 distinct DB rows, confirmed updating one
never affects the other, and confirmed publish preserves both.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

PAGE = (FRONTEND / "app/(tenant)/tenant/setup/services/page.tsx").read_text(encoding="utf-8-sig")
API_TS = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")
TENANT_SERVICE_PY = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")


# ── 1. Data model: BrandPricingState is now type-scoped ──────────────────────
def test_brand_pricing_state_has_type_fields():
    interface_block = PAGE.split("interface BrandPricingState")[1].split("}")[0]
    assert "typeId: string" in interface_block
    assert "typeName: string" in interface_block


# ── 2. Fetching is per-type ────────────────────────────────────────────────────
def test_brand_pricing_fetched_per_type():
    assert "fetchBrandPricingForTypes" in PAGE
    fn = PAGE.split("fetchBrandPricingForTypes = useCallback")[1].split("}, []);")[0]
    assert "getBrandPricing(tsid, typeId)" in fn


def test_brand_pricing_no_longer_fetched_type_agnostically():
    # The old single, type-agnostic fetch (no serviceTypeId argument) must
    # be gone — every getBrandPricing call in this page must pass a type.
    assert "getBrandPricing(tenantServiceId)" not in PAGE.replace(
        "getBrandPricing(tenantServiceId ?? \"__none__\")", "")  # brands-list call (different method) excluded


# ── 3. Saving passes service_type_id ──────────────────────────────────────────
def test_save_brand_pricing_passes_type_id():
    fn = PAGE.split("const saveBrandPricingAction = useAction")[1].split("}, [tenantServiceId, brandMode, brandPricingState]));")[0]
    assert "setBrandPricing(tenantServiceId, bp.brandId, min, max, bp.typeId)" in fn


def test_api_client_supports_service_type_id_param():
    fn = API_TS.split("setBrandPricing: (tenantServiceId: string")[1][:400]
    assert "serviceTypeId?: string" in fn
    assert "service_type_id=" in fn


# ── 4. UI groups brand overrides by type ──────────────────────────────────────
def test_brands_step_renders_one_section_per_type():
    step_block = PAGE.split('{step === "brands" && (')[1].split('{step === "review" && (')[0]
    assert "typePricingState.map(tp =>" in step_block
    assert "rowsForType = brandPricingState.filter(b => b.typeId === tp.typeId" in step_block


def test_brand_change_handlers_scoped_by_type_and_brand():
    step_block = PAGE.split('{step === "brands" && (')[1].split('{step === "review" && (')[0]
    assert "b.typeId === bp.typeId && b.brandId === bp.brandId" in step_block


# ── 5. Review matrix scopes brand rows to their own type only ────────────────
def test_review_matrix_filters_brand_rows_by_type():
    review_block = PAGE.split('{step === "review" && (')[1].split("Price resolution")[0]
    assert "brandPricingState" in review_block
    assert ".filter(b => b.typeId === tp.typeId && b.canOverride)" in review_block
    # The old, type-blind filter (only checking enabled+canOverride, no
    # typeId comparison) must be gone.
    assert ".filter(b => b.enabled && b.canOverride)" not in review_block


def test_review_matrix_shows_no_override_cta():
    review_block = PAGE.split('{step === "review" && (')[1].split("Price resolution")[0]
    assert "No brand override" in review_block
    assert "using type price" in review_block
    assert "Add override" in review_block


# ── 6. Price resolution copy updated ──────────────────────────────────────────
def test_price_resolution_copy_updated():
    assert "type-specific brand price → type price → service base price." in PAGE
    assert "Window AC + LG can be different from Split AC + LG." in PAGE
    assert "brand price → type price → base price." not in PAGE  # old copy gone


# ── 7. Backend already enforces type-scoping (from an earlier sprint) ────────
def test_backend_requires_type_for_brand_pricing():
    assert "SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING" in TENANT_SERVICE_PY


def test_backend_set_brand_pricing_scoped_by_type():
    fn = TENANT_SERVICE_PY.split("async def set_brand_pricing")[1]
    assert "TenantServiceBrand.service_type_id == service_type_id" in fn


# ── 8. Forbidden labels ────────────────────────────────────────────────────────
FORBIDDEN = [
    "Manual Bargain Setup", "Bargain Rule Builder", "Bargain Settings",
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance", "Credit Wallet Health",
]


def test_no_forbidden_labels():
    for term in FORBIDDEN:
        assert term not in PAGE, f"forbidden label found: {term}"
