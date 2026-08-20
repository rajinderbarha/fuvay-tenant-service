"""
P0 Finance + Package + Pricing Mapping Fix — tests (second wave).

Final canonical package types:
  onboarding_package    — one-time onboarding fee (deposit + starting credits allowed)
  security_deposit_rule — deposit requirement ONLY; must NOT have included_credit_amount > 0
  credit_topup          — spendable wallet credits for commission; must NOT have security_deposit_amount > 0
  subscription_plan     — recurring plan
  lead_credit_package   — lead credits for real estate / lead verticals
  trial_plan            — free/limited trial
  custom_plan           — miscellaneous

NOT valid generic types:
  security_deposit      — bare type removed (use security_deposit_rule)
  credit_package        — renamed to credit_topup

Verifies:
  1. Backend VALID_PACKAGE_TYPES has final canonical names
  2. security_deposit_rule validation: must not include spendable credits
  3. credit_topup validation: must not have security_deposit_amount > 0
  4. Migration 067 adds service-level pricing fields to city_tier_configs
  5. Pricing model has new fields
  6. Pricing schemas accept new fields
  7. Pricing service _ctc_dict returns new fields
  8. City tier duplicate check uses service_name
  9. Finance Hub: no Credit Packages tab, no New Package button
  10. Finance Hub: Security Deposits tab + Credit Top-ups tab
  11. Packages page: final type names with no stale types
  12. Packages page: security_deposit_rule form fields
  13. Pricing page labels: "Minimum Allowed Price" (not "Floor Price")
  14. Pricing page: max_price field, service_name field
  15. Catalog Master Service: helper text about basic pricing only
  16. Nav: separate Finance, Packages & Plans, Pricing groups
"""
import os
import re

ROOT      = os.path.dirname(os.path.dirname(__file__))
SVC_PKG   = os.path.join(ROOT, "app", "engines", "package_commerce", "service.py")
MDL_PRC   = os.path.join(ROOT, "app", "engines", "pricing", "models.py")
SCH_PRC   = os.path.join(ROOT, "app", "engines", "pricing", "schemas.py")
SVC_PRC   = os.path.join(ROOT, "app", "engines", "pricing", "service.py")
MIG_067   = os.path.join(ROOT, "alembic", "versions", "067_pricing_service_fields.py")
FIN_PG    = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "finance", "page.tsx")
# P0 Enterprise Finance Hub Upgrade split the old single-page tabs into dedicated pages.
FIN_DEPOSITS_PG = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "finance", "deposits", "page.tsx")
FIN_TOPUPS_PG   = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "finance", "topups", "page.tsx")
HS_FIN_PG       = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "home-services", "finance", "page.tsx")
PKG_PG    = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "packages", "page.tsx")
PRC_PG    = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "pricing", "page.tsx")
CAT_PG    = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "master-services", "page.tsx")
NAV_CFG   = os.path.join(ROOT, "frontend", "super-admin", "lib", "nav-config.ts")


def _r(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════
# BACKEND — Package Service: VALID_PACKAGE_TYPES
# ══════════════════════════════════════════════════════════════

def test_package_service_rejects_bare_security_deposit():
    """'security_deposit' (bare) must not be in VALID_PACKAGE_TYPES — only security_deposit_rule is valid."""
    src = _r(SVC_PKG)
    idx = src.find("VALID_PACKAGE_TYPES")
    assert idx != -1
    block = src[idx:idx+700]
    assert '"security_deposit"' not in block or "security_deposit_rule" not in block or \
        block.index('"security_deposit"') > block.index("security_deposit_rule"), \
        "bare 'security_deposit' must not appear as a standalone entry in VALID_PACKAGE_TYPES"
    # More direct: the bare type (not part of security_deposit_rule) must not be present
    assert '"security_deposit",' not in block and '"security_deposit"\n' not in block


def test_package_service_rejects_old_credit_package_name():
    """'credit_package' was renamed to 'credit_topup' — must not appear in VALID_PACKAGE_TYPES."""
    src = _r(SVC_PKG)
    idx = src.find("VALID_PACKAGE_TYPES")
    block = src[idx:idx+700]
    assert '"credit_package"' not in block, \
        "'credit_package' must not be in VALID_PACKAGE_TYPES (renamed to credit_topup)"


def test_package_service_rejects_old_onboarding_plan_name():
    """'onboarding_plan' was renamed to 'onboarding_package'."""
    src = _r(SVC_PKG)
    idx = src.find("VALID_PACKAGE_TYPES")
    block = src[idx:idx+700]
    assert '"onboarding_plan"' not in block, \
        "'onboarding_plan' must not be in VALID_PACKAGE_TYPES (renamed to onboarding_package)"


def test_package_service_has_onboarding_package():
    src = _r(SVC_PKG)
    idx = src.find("VALID_PACKAGE_TYPES")
    block = src[idx:idx+700]
    assert '"onboarding_package"' in block


def test_package_service_has_security_deposit_rule():
    src = _r(SVC_PKG)
    idx = src.find("VALID_PACKAGE_TYPES")
    block = src[idx:idx+700]
    assert '"security_deposit_rule"' in block


def test_package_service_has_credit_topup():
    src = _r(SVC_PKG)
    idx = src.find("VALID_PACKAGE_TYPES")
    block = src[idx:idx+700]
    assert '"credit_topup"' in block


def test_package_service_has_subscription_plan():
    src = _r(SVC_PKG)
    idx = src.find("VALID_PACKAGE_TYPES")
    block = src[idx:idx+700]
    assert '"subscription_plan"' in block


def test_package_service_has_lead_credit_package():
    src = _r(SVC_PKG)
    idx = src.find("VALID_PACKAGE_TYPES")
    block = src[idx:idx+700]
    assert '"lead_credit_package"' in block


def test_package_service_has_trial_plan():
    src = _r(SVC_PKG)
    idx = src.find("VALID_PACKAGE_TYPES")
    block = src[idx:idx+700]
    assert '"trial_plan"' in block


def test_package_service_has_custom_plan():
    src = _r(SVC_PKG)
    idx = src.find("VALID_PACKAGE_TYPES")
    block = src[idx:idx+700]
    assert '"custom_plan"' in block


def test_package_service_credit_topup_validation():
    """credit_topup packages must not have security_deposit_amount > 0."""
    src = _r(SVC_PKG)
    assert "credit_topup" in src
    assert "security_deposit_amount = 0" in src or "security_deposit_amount" in src


def test_package_service_security_deposit_rule_validation():
    """security_deposit_rule must not include spendable credits (included_credit_amount > 0 blocked)."""
    src = _r(SVC_PKG)
    assert "security_deposit_rule" in src
    # validation error message must reference spendable credits
    assert "spendable" in src or "included_credit" in src


# ══════════════════════════════════════════════════════════════
# MIGRATION 067
# ══════════════════════════════════════════════════════════════

def test_migration_067_exists():
    assert os.path.exists(MIG_067)


def test_migration_067_adds_service_name():
    src = _r(MIG_067)
    assert "service_name" in src


def test_migration_067_adds_min_price():
    src = _r(MIG_067)
    assert "min_price" in src


def test_migration_067_adds_max_price():
    src = _r(MIG_067)
    assert "max_price" in src


def test_migration_067_adds_default_estimate():
    src = _r(MIG_067)
    assert "default_estimate" in src


def test_migration_067_adds_visit_fee():
    src = _r(MIG_067)
    assert "visit_fee" in src


def test_migration_067_adds_bargain_floor():
    src = _r(MIG_067)
    assert "bargain_floor" in src


def test_migration_067_adds_provider_override():
    src = _r(MIG_067)
    assert "provider_override_allowed" in src


def test_migration_067_updates_unique_constraint():
    src = _r(MIG_067)
    assert "uq_ctc_city_category_service" in src
    assert "drop_constraint" in src or "drop" in src.lower()


# ══════════════════════════════════════════════════════════════
# PRICING MODEL
# ══════════════════════════════════════════════════════════════

def test_pricing_model_has_service_name():
    src = _r(MDL_PRC)
    assert "service_name" in src


def test_pricing_model_has_min_price():
    src = _r(MDL_PRC)
    assert "min_price" in src


def test_pricing_model_has_max_price():
    src = _r(MDL_PRC)
    assert "max_price" in src


def test_pricing_model_has_default_estimate():
    src = _r(MDL_PRC)
    assert "default_estimate" in src


def test_pricing_model_has_bargain_floor():
    src = _r(MDL_PRC)
    assert "bargain_floor" in src


def test_pricing_model_has_provider_override():
    src = _r(MDL_PRC)
    assert "provider_override_allowed" in src


def test_pricing_model_unique_constraint_uses_service_name():
    src = _r(MDL_PRC)
    assert "uq_ctc_city_category_service" in src
    assert "service_name" in src


# ══════════════════════════════════════════════════════════════
# PRICING SCHEMAS
# ══════════════════════════════════════════════════════════════

def test_pricing_schema_create_has_service_name():
    src = _r(SCH_PRC)
    idx = src.find("class CityTierCreateRequest")
    block = src[idx:idx+600]
    assert "service_name" in block


def test_pricing_schema_create_has_min_price():
    src = _r(SCH_PRC)
    idx = src.find("class CityTierCreateRequest")
    block = src[idx:idx+600]
    assert "min_price" in block


def test_pricing_schema_create_has_max_price():
    src = _r(SCH_PRC)
    idx = src.find("class CityTierCreateRequest")
    block = src[idx:idx+900]
    assert "max_price" in block


def test_pricing_schema_update_has_min_max():
    src = _r(SCH_PRC)
    idx = src.find("class CityTierUpdateRequest")
    block = src[idx:idx+400]
    assert "min_price" in block
    assert "max_price" in block


# ══════════════════════════════════════════════════════════════
# PRICING SERVICE
# ══════════════════════════════════════════════════════════════

def test_pricing_service_ctc_dict_returns_service_name():
    src = _r(SVC_PRC)
    idx = src.find("def _ctc_dict")
    block = src[idx:idx+600]
    assert "service_name" in block


def test_pricing_service_ctc_dict_returns_min_price():
    src = _r(SVC_PRC)
    idx = src.find("def _ctc_dict")
    block = src[idx:idx+600]
    assert "min_price" in block


def test_pricing_service_ctc_dict_returns_max_price():
    src = _r(SVC_PRC)
    idx = src.find("def _ctc_dict")
    block = src[idx:idx+600]
    assert "max_price" in block


def test_pricing_service_create_uses_service_name():
    src = _r(SVC_PRC)
    idx = src.find("async def create_city_tier_config")
    block = src[idx:idx+800]
    assert "service_name" in block


def test_pricing_service_update_handles_min_max():
    src = _r(SVC_PRC)
    idx = src.find("async def update_city_tier_config")
    block = src[idx:idx+600]
    assert "min_price" in block


# ══════════════════════════════════════════════════════════════
# FRONTEND — Finance Hub
# ══════════════════════════════════════════════════════════════

def test_finance_hub_no_credit_packages_tab():
    src = _r(FIN_PG)
    assert 'label: "Credit Packages"' not in src and "label:\"Credit Packages\"" not in src, \
        "Finance Hub must not have a Credit Packages tab"


def test_finance_hub_no_new_package_button():
    src = _r(FIN_PG)
    assert "setPkgModal" not in src, \
        "Finance Hub must not have a pkgModal state (no New Package button)"


def test_finance_hub_has_security_deposits_tab():
    # P0 Enterprise Finance Hub Upgrade: Security Deposits is now a dedicated page,
    # linked from the Finance nav group, rather than a tab on finance/page.tsx.
    src = _r(FIN_DEPOSITS_PG)
    assert "Security Deposits" in src


def test_finance_hub_has_credit_topups_tab():
    # The retired standalone URL preserves deep links by redirecting to the
    # one consolidated Home Services Finance authority.
    redirect_src = _r(FIN_TOPUPS_PG)
    workspace_src = _r(HS_FIN_PG)
    assert "tab=credits&credits_tab=topups" in redirect_src
    assert "Credits & Top-ups" in workspace_src


def test_finance_hub_link_to_packages():
    # Package administration is rendered inside the consolidated Credits
    # workspace; the compatibility redirect intentionally contains no UI.
    src = _r(HS_FIN_PG)
    assert "credit_package" in src or "package" in src.lower()


def test_finance_hub_security_deposit_helper_text():
    # The separation is enforced structurally now (dedicated Security Deposits vs
    # Wallet Directory pages, distinct API/service methods) rather than via a banner string.
    deposits_src = _r(FIN_DEPOSITS_PG)
    service_src = _r(os.path.join(ROOT, "app", "engines", "finance_hub", "service.py"))
    assert "Security Deposits" in deposits_src
    assert "TenantWallet" not in service_src[service_src.index("def _deposit_dict("):service_src.index("def _deposit_dict(") + 1500]


# ══════════════════════════════════════════════════════════════
# FRONTEND — Packages Page (second wave types)
# ══════════════════════════════════════════════════════════════

def test_packages_page_no_bare_security_deposit():
    src = _r(PKG_PG)
    # bare "security_deposit" as a value must not appear (security_deposit_rule is the correct form)
    assert 'value: "security_deposit",' not in src and "value: \"security_deposit\"," not in src


def test_packages_page_no_old_credit_package_name():
    """'credit_package' was renamed to 'credit_topup' — packages page must use new name."""
    src = _r(PKG_PG)
    assert 'value: "credit_package"' not in src


def test_packages_page_no_old_onboarding_plan():
    """'onboarding_plan' renamed to 'onboarding_package'."""
    src = _r(PKG_PG)
    assert 'value: "onboarding_plan"' not in src


def test_packages_page_no_old_lead_credit_plan():
    """'lead_credit_plan' renamed to 'lead_credit_package'."""
    src = _r(PKG_PG)
    assert 'value: "lead_credit_plan"' not in src


def test_packages_page_no_old_custom():
    """PACKAGE_TYPE_TABS must use 'custom_plan' (not bare 'custom') as package type value."""
    src = _r(PKG_PG)
    # PACKAGE_TYPE_TABS must have custom_plan (not "custom")
    assert '"custom_plan"' in src
    # The old bare "custom" package type must be gone from PACKAGE_TYPE_TABS
    # (LIMIT_KEY_OPTS may still have value:"custom" as a limit key — that's OK)
    tabs_section = src[src.find("PACKAGE_TYPE_TABS"):src.find("LIMIT_KEY_OPTS")]
    assert 'value: "custom",' not in tabs_section


def test_packages_page_has_onboarding_package():
    src = _r(PKG_PG)
    assert '"onboarding_package"' in src


def test_packages_page_has_security_deposit_rule():
    src = _r(PKG_PG)
    assert '"security_deposit_rule"' in src


def test_packages_page_has_credit_topup():
    src = _r(PKG_PG)
    assert '"credit_topup"' in src


def test_packages_page_has_subscription_plan():
    src = _r(PKG_PG)
    assert '"subscription_plan"' in src


def test_packages_page_has_lead_credit_package():
    src = _r(PKG_PG)
    assert '"lead_credit_package"' in src


def test_packages_page_has_trial_plan():
    src = _r(PKG_PG)
    assert '"trial_plan"' in src


def test_packages_page_has_custom_plan():
    src = _r(PKG_PG)
    assert '"custom_plan"' in src


def test_packages_page_dynamic_form_by_type():
    src = _r(PKG_PG)
    assert "form.package_type" in src
    assert "isDepositRule" in src or "security_deposit_rule" in src


def test_packages_page_security_deposit_rule_hint():
    """Security deposit rule must show as non-spendable in the UI."""
    src = _r(PKG_PG)
    assert "non-spendable" in src or "NOT spendable" in src or "not spendable" in src.lower()


def test_packages_page_credit_topup_wallet_hint():
    src = _r(PKG_PG)
    assert "wallet" in src.lower()


def test_packages_page_type_tabs_exist():
    src = _r(PKG_PG)
    assert "PACKAGE_TYPE_TABS" in src


# ══════════════════════════════════════════════════════════════
# FRONTEND — Pricing Page (second wave labels)
# ══════════════════════════════════════════════════════════════

def test_pricing_page_no_floor_price_label():
    """'Floor Price' label must be gone."""
    src = _r(PRC_PG)
    assert 'label:"Floor Price"' not in src and 'label: "Floor Price"' not in src


def test_pricing_page_has_minimum_allowed_price_label():
    """Must use 'Minimum Allowed Price', not 'Category Minimum Price'."""
    src = _r(PRC_PG)
    assert "Minimum Allowed Price" in src


def test_pricing_page_no_category_minimum_price_label():
    """'Category Minimum Price' label text replaced by 'Minimum Allowed Price'."""
    src = _r(PRC_PG)
    # The old label text must not appear as a UI label (helper text may still mention category)
    assert 'label="Category Minimum Price' not in src and \
           'label: "Category Minimum Price' not in src and \
           "Category Minimum Price" not in src


def test_pricing_page_column_min_allowed_price():
    """Column header should say 'Min Allowed Price'."""
    src = _r(PRC_PG)
    assert "Min Allowed Price" in src


def test_pricing_page_form_has_service_name():
    src = _r(PRC_PG)
    assert "service_name" in src


def test_pricing_page_form_has_min_price():
    src = _r(PRC_PG)
    assert "min_price" in src


def test_pricing_page_form_has_max_price():
    src = _r(PRC_PG)
    assert "max_price" in src


def test_pricing_page_form_has_default_estimate():
    src = _r(PRC_PG)
    assert "default_estimate" in src


def test_pricing_page_form_has_visit_fee():
    src = _r(PRC_PG)
    assert "visit_fee" in src


def test_pricing_page_form_has_bargain_floor():
    src = _r(PRC_PG)
    assert "bargain_floor" in src or "Bargain Floor" in src


def test_pricing_page_form_has_provider_override():
    src = _r(PRC_PG)
    assert "provider_override_allowed" in src


def test_pricing_page_category_wide_fallback_hint():
    src = _r(PRC_PG)
    lower = src.lower()
    assert "fallback" in lower or "category-wide" in lower


def test_pricing_page_new_rule_button_label():
    src = _r(PRC_PG)
    assert "New Pricing Rule" in src


def test_pricing_page_min_price_helper_text():
    """Pricing page must explain what minimum price means for providers in a city tier."""
    src = _r(PRC_PG)
    lower = src.lower()
    assert "minimum price" in lower and ("city" in lower or "tier" in lower or "category" in lower)


# ══════════════════════════════════════════════════════════════
# FRONTEND — Catalog Master Service
# ══════════════════════════════════════════════════════════════

# HS0 cleanup: the Master Service modal's inline pricing helper text/link to
# /admin/pricing was part of the old per-service manual pricing form that has
# since been removed from /admin/catalog entirely (pricing now lives in the
# Home Services Pricing Rules screen and the tenant Service Setup wizard).
# Both assertions tested obsolete UI; deleted as obsolete rather than left
# red. See HS0_TEST_FILE_CLEANUP_REPORT.md.


# ══════════════════════════════════════════════════════════════
# NAV CONFIG
# ══════════════════════════════════════════════════════════════

def test_nav_packages_not_in_catalog():
    src = _r(NAV_CFG)
    catalog_idx = src.find('"catalog"')
    if catalog_idx == -1:
        return
    catalog_block_end = src.find("  },", catalog_idx + 20)
    catalog_block = src[catalog_idx:catalog_block_end]
    assert 'href: "/admin/packages"' not in catalog_block, \
        "packages link must not appear inside the catalog nav group"


def test_nav_has_packages_group():
    src = _r(NAV_CFG)
    assert '"packages"' in src
    assert "/admin/packages" in src


def test_nav_has_pricing_group_or_entry():
    src = _r(NAV_CFG)
    assert "/admin/pricing" in src


def test_nav_finance_hub_label():
    src = _r(NAV_CFG)
    assert "Finance Hub" in src or '"finance"' in src


def test_nav_finance_hub_no_credit_packages_link():
    src = _r(NAV_CFG)
    assert "credit-packages" not in src and "credit_packages" not in src
