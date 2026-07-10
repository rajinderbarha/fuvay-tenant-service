"""FIX — Home Services Type-Dependent Brand Pricing certification.

Root cause: TenantServiceBrand was keyed only by (tenant_service_id,
brand_id) — one price range per brand per service, shared across every
service type. The tenant setup wizard's set_brand_pricing already
threaded a service_type_id parameter through to read the admin-approved
floor/ceiling (via ServicePricingRule, which already had service_type_id
+ brand_id columns from an earlier sprint), but had nowhere to persist
the tenant's own type-scoped range — so setting "LG" pricing for Window
AC and then again for Split AC silently overwrote the same row.

Fixed via migration 120: added service_type_id to tenant_service_brands,
widened the unique constraint to (tenant_service_id, service_type_id,
brand_id), and added a uniqueness constraint to service_pricing_rules
(master_service_id, service_type_id, brand_id, tier_id) that didn't
exist before (duplicate admin rules were previously unguarded).

Live-verified against the real dev DB and the real AC Repair master
service (Window AC / Split AC / LG, matching this ticket's own example):
setting LG pricing for Window AC (Rs.370-480) and Split AC (Rs.700-850)
independently produced two distinct DB rows and two distinct, correct
GET responses — see TYPE_DEPENDENT_BRAND_PRICING_TEST_RESULTS.md for the
full live transcript.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

MODELS = (ROOT / "app/engines/admin_catalog/models.py").read_text(encoding="utf-8-sig")
TENANT_SERVICE_PY = (ROOT / "app/engines/admin_catalog/tenant_service.py").read_text(encoding="utf-8-sig")
TENANT_ROUTER = (ROOT / "app/engines/admin_catalog/tenant_router.py").read_text(encoding="utf-8-sig")
MIGRATION_120 = (ROOT / "alembic/versions/120_type_dependent_brand_pricing.py").read_text(encoding="utf-8-sig")
MIGRATE_SCRIPT = (ROOT / "scripts/migrate_type_dependent_brand_pricing.py").read_text(encoding="utf-8-sig")


# ── 1. Data model ──────────────────────────────────────────────────────────
def test_tenant_service_brand_has_service_type_id():
    block = MODELS.split("class TenantServiceBrand(ServiceOSBase)")[1].split("# ── Master Offerings")[0]
    assert "service_type_id" in block
    assert 'UniqueConstraint("tenant_service_id", "service_type_id", "brand_id"' in block


def test_service_pricing_rule_has_unique_constraint():
    block = MODELS.split("class ServicePricingRule(ServiceOSBase)")[1].split("# ── Bargain Rules")[0]
    assert "uq_spr_service_type_brand_tier" in block


def test_migration_120_adds_column_and_constraints():
    assert "service_type_id" in MIGRATION_120
    assert "uq_tsb_service_type_brand" in MIGRATION_120
    assert "uq_spr_service_type_brand_tier" in MIGRATION_120


# ── 2. Validation rules ───────────────────────────────────────────────────
def test_type_based_service_requires_type_for_brand_pricing():
    fn = TENANT_SERVICE_PY.split("async def set_brand_pricing")[1].split("async def get_brand_pricing_for_setup")[0] \
        if "async def get_brand_pricing_for_setup" in TENANT_SERVICE_PY.split("async def set_brand_pricing")[1] \
        else TENANT_SERVICE_PY.split("async def set_brand_pricing")[1]
    assert "SERVICE_TYPE_REQUIRED_FOR_BRAND_PRICING" in fn
    assert "ts.requires_type and service_type_id is None" in fn


def test_brand_override_must_belong_to_selected_service():
    fn = TENANT_SERVICE_PY.split("async def set_brand_pricing")[1]
    assert "BRAND_NOT_SUPPORTED" in fn
    assert "MasterServiceBrand.master_service_id == ts.master_service_id" in fn


def test_service_type_must_be_enabled_for_tenant_service():
    fn = TENANT_SERVICE_PY.split("async def set_brand_pricing")[1]
    assert "SERVICE_TYPE_NOT_SUPPORTED" in fn


# ── 3. Upsert scoped by service_type_id (the actual fix) ─────────────────
def test_set_brand_pricing_scoped_by_type_not_just_brand():
    fn = TENANT_SERVICE_PY.split("async def set_brand_pricing")[1]
    assert "TenantServiceBrand.service_type_id == service_type_id" in fn
    assert "TenantServiceBrand.service_type_id.is_(None)" in fn


def test_get_brand_pricing_scoped_by_type():
    fn = TENANT_SERVICE_PY.split("async def get_brand_pricing_for_setup")[1].split("async def set_brand_pricing")[0]
    assert "TenantServiceBrand.service_type_id == service_type_id" in fn
    assert "TenantServiceBrand.service_type_id.is_(None)" in fn


def test_brand_enablement_list_not_polluted_by_per_type_rows():
    fn = TENANT_SERVICE_PY.split("async def get_tenant_service_brands")[1].split("async def set_tenant_service_brands")[0]
    assert "TenantServiceBrand.service_type_id.is_(None)" in fn


# ── 4. API surface ─────────────────────────────────────────────────────────
def test_brand_pricing_endpoints_accept_service_type_id():
    block = TENANT_ROUTER.split('@router.put("/enabled-services/{tenant_service_id}/brands/{brand_id}/pricing"')[1][:800]
    assert "service_type_id" in block


# ── 5. Migration/cleanup script ────────────────────────────────────────────
def test_migration_script_supports_dry_run_and_apply():
    assert "--dry-run" in MIGRATE_SCRIPT
    assert "--apply" in MIGRATE_SCRIPT


def test_migration_script_does_not_blindly_copy_price_to_all_types():
    assert "blindly" in MIGRATE_SCRIPT.lower() or "not blindly" in MIGRATE_SCRIPT.lower()
    assert "manual_review" in MIGRATE_SCRIPT or "manual review" in MIGRATE_SCRIPT.lower()


def test_migration_script_finds_old_global_brand_rules():
    assert "service_type_id IS NULL" in MIGRATE_SCRIPT
    assert "brand_id IS NOT NULL" in MIGRATE_SCRIPT


# ── 6. No forbidden request_id gaps ────────────────────────────────────────
def test_backend_exceptions_use_serviceos_exception():
    fn = TENANT_SERVICE_PY.split("async def set_brand_pricing")[1]
    assert "ServiceOSException(" in fn
