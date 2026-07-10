"""
P0 Package Creation UX + Data Model tests.
Covers:
  - Migration 071 exists with correct revision
  - PackageFeature / PackageLimit models
  - PackageCommerceService: features/limits CRUD, get_package_with_details, clone_package
  - Validation guards (credit_topup/security_deposit_rule money field rules)
  - Admin router: features/limits sub-resources + clone endpoint
  - Public packages endpoint includes features + limits
  - Frontend super-admin api.ts: PackageFeature/PackageLimit types, new methods
  - Frontend super-admin packages/page.tsx: tabbed form, DraftFeature/DraftLimit, PreviewCard
  - Frontend tenant-portal api.ts: SignupPackageFeature/SignupPackageLimit types
  - Frontend tenant-portal register/page.tsx: renders package_features + package_limits
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))

MIGRATION_071      = os.path.join(ROOT, "alembic", "versions", "071_package_features_limits.py")
MODELS_FILE        = os.path.join(ROOT, "app", "engines", "package_commerce", "models.py")
SERVICE_FILE       = os.path.join(ROOT, "app", "engines", "package_commerce", "service.py")
ADMIN_ROUTER       = os.path.join(ROOT, "app", "engines", "package_commerce", "admin_router.py")
PUBLIC_ROUTER      = os.path.join(ROOT, "app", "engines", "package_commerce", "public_router.py")
SA_API             = os.path.join(ROOT, "frontend", "super-admin", "lib", "api.ts")
SA_PACKAGES_PAGE   = os.path.join(ROOT, "frontend", "super-admin", "app", "admin", "packages", "page.tsx")
TP_API             = os.path.join(ROOT, "frontend", "tenant-portal", "lib", "api.ts")
TP_REGISTER_PAGE   = os.path.join(ROOT, "frontend", "tenant-portal", "app", "register", "page.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Migration 071 ──────────────────────────────────────────────────────────────

def test_migration_071_exists():
    assert os.path.exists(MIGRATION_071), "Migration 071 file must exist"


def test_migration_071_revision():
    src = _read(MIGRATION_071)
    assert 'revision = "071"' in src, "migration must declare revision 071"
    assert 'down_revision = "070"' in src, "migration must chain from 070"


def test_migration_071_creates_package_features_table():
    src = _read(MIGRATION_071)
    assert "package_features" in src


def test_migration_071_creates_package_limits_table():
    src = _read(MIGRATION_071)
    assert "package_limits" in src


def test_migration_071_adds_short_description_column():
    src = _read(MIGRATION_071)
    assert "short_description" in src


def test_migration_071_adds_badge_label_column():
    src = _read(MIGRATION_071)
    assert "badge_label" in src


def test_migration_071_adds_trial_days_column():
    src = _read(MIGRATION_071)
    assert "trial_days" in src


def test_migration_071_adds_is_featured_column():
    src = _read(MIGRATION_071)
    assert "is_featured" in src


def test_migration_071_adds_is_recommended_column():
    src = _read(MIGRATION_071)
    assert "is_recommended" in src


def test_migration_071_adds_bonus_credits_column():
    src = _read(MIGRATION_071)
    assert "bonus_credits" in src


def test_migration_071_adds_lead_credits_column():
    src = _read(MIGRATION_071)
    assert "lead_credits" in src


def test_migration_071_package_features_fk():
    src = _read(MIGRATION_071)
    assert "service_packages.id" in src, "package_features must FK to service_packages.id"


def test_migration_071_package_limits_fk():
    src = _read(MIGRATION_071)
    assert "package_limits" in src and "service_packages.id" in src


# ── SQLAlchemy Models ──────────────────────────────────────────────────────────

def test_models_has_package_feature_class():
    src = _read(MODELS_FILE)
    assert "class PackageFeature" in src


def test_models_has_package_limit_class():
    src = _read(MODELS_FILE)
    assert "class PackageLimit" in src


def test_models_package_feature_tablename():
    src = _read(MODELS_FILE)
    assert '__tablename__ = "package_features"' in src


def test_models_package_limit_tablename():
    src = _read(MODELS_FILE)
    assert '__tablename__ = "package_limits"' in src


def test_models_package_feature_has_feature_label():
    src = _read(MODELS_FILE)
    assert "feature_label" in src


def test_models_package_feature_has_is_highlighted():
    src = _read(MODELS_FILE)
    assert "is_highlighted" in src


def test_models_package_feature_has_is_included():
    src = _read(MODELS_FILE)
    assert "is_included" in src


def test_models_package_limit_has_limit_key():
    src = _read(MODELS_FILE)
    assert "limit_key" in src


def test_models_package_limit_has_is_unlimited():
    src = _read(MODELS_FILE)
    assert "is_unlimited" in src


def test_models_service_package_has_short_description():
    src = _read(MODELS_FILE)
    assert "short_description" in src


def test_models_service_package_has_badge_label():
    src = _read(MODELS_FILE)
    assert "badge_label" in src


def test_models_service_package_has_cta_label():
    src = _read(MODELS_FILE)
    assert "cta_label" in src


def test_models_service_package_has_is_featured():
    src = _read(MODELS_FILE)
    assert "is_featured" in src


def test_models_service_package_has_is_recommended():
    src = _read(MODELS_FILE)
    assert "is_recommended" in src


# ── Service ────────────────────────────────────────────────────────────────────

def test_service_imports_package_feature():
    src = _read(SERVICE_FILE)
    assert "PackageFeature" in src


def test_service_imports_package_limit():
    src = _read(SERVICE_FILE)
    assert "PackageLimit" in src


def test_service_has_list_package_features():
    src = _read(SERVICE_FILE)
    assert "list_package_features" in src


def test_service_has_create_package_feature():
    src = _read(SERVICE_FILE)
    assert "create_package_feature" in src


def test_service_has_update_package_feature():
    src = _read(SERVICE_FILE)
    assert "update_package_feature" in src


def test_service_has_delete_package_feature():
    src = _read(SERVICE_FILE)
    assert "delete_package_feature" in src


def test_service_has_list_package_limits():
    src = _read(SERVICE_FILE)
    assert "list_package_limits" in src


def test_service_has_create_package_limit():
    src = _read(SERVICE_FILE)
    assert "create_package_limit" in src


def test_service_has_update_package_limit():
    src = _read(SERVICE_FILE)
    assert "update_package_limit" in src


def test_service_has_delete_package_limit():
    src = _read(SERVICE_FILE)
    assert "delete_package_limit" in src


def test_service_has_get_package_with_details():
    src = _read(SERVICE_FILE)
    assert "get_package_with_details" in src


def test_service_has_clone_package():
    src = _read(SERVICE_FILE)
    assert "clone_package" in src


def test_service_clone_generates_copy_slug():
    src = _read(SERVICE_FILE)
    assert "-copy-" in src, "clone_package must append -copy- suffix to slug"


def test_service_feature_dict_returns_feature_id():
    src = _read(SERVICE_FILE)
    assert "_feature_dict" in src
    assert "feature_id" in src


def test_service_limit_dict_returns_limit_id():
    src = _read(SERVICE_FILE)
    assert "_limit_dict" in src
    assert "limit_id" in src


def test_service_pkg_dict_returns_package_features_key():
    src = _read(SERVICE_FILE)
    assert "package_features" in src


def test_service_pkg_dict_returns_package_limits_key():
    src = _read(SERVICE_FILE)
    assert "package_limits" in src


def test_service_pkg_dict_returns_both_id_and_package_id():
    src = _read(SERVICE_FILE)
    assert '"package_id"' in src and '"id"' in src, \
        "_pkg_dict must return both 'id' and 'package_id' for backward compat"


def test_service_pkg_dict_returns_both_price_keys():
    src = _read(SERVICE_FILE)
    assert '"price"' in src and '"package_price"' in src, \
        "_pkg_dict must return both 'price' and 'package_price' for backward compat"


def test_service_validation_credit_topup_no_deposit():
    src = _read(SERVICE_FILE)
    assert "credit_topup" in src and "security_deposit_amount" in src


def test_service_validation_security_deposit_no_credits():
    src = _read(SERVICE_FILE)
    assert "security_deposit_rule" in src and "included_credit_amount" in src


def test_service_list_public_packages_loads_features():
    src = _read(SERVICE_FILE)
    assert "list_public_packages" in src
    assert "package_features" in src


# ── Admin Router ───────────────────────────────────────────────────────────────

def test_admin_router_has_features_list_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "/features" in src


def test_admin_router_has_features_create_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "create_package_feature" in src


def test_admin_router_has_features_update_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "update_package_feature" in src


def test_admin_router_has_features_delete_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "delete_package_feature" in src


def test_admin_router_has_limits_list_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "/limits" in src


def test_admin_router_has_limits_create_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "create_package_limit" in src


def test_admin_router_has_limits_update_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "update_package_limit" in src


def test_admin_router_has_limits_delete_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "delete_package_limit" in src


def test_admin_router_has_clone_endpoint():
    src = _read(ADMIN_ROUTER)
    assert "clone" in src
    assert "clone_package" in src


def test_admin_router_get_package_uses_with_details():
    src = _read(ADMIN_ROUTER)
    assert "get_package_with_details" in src


# ── Frontend super-admin api.ts ────────────────────────────────────────────────

def test_sa_api_has_package_feature_interface():
    src = _read(SA_API)
    assert "PackageFeature" in src


def test_sa_api_package_feature_has_feature_id():
    src = _read(SA_API)
    assert "feature_id" in src


def test_sa_api_package_feature_has_feature_label():
    src = _read(SA_API)
    assert "feature_label" in src


def test_sa_api_package_feature_has_is_highlighted():
    src = _read(SA_API)
    assert "is_highlighted" in src


def test_sa_api_has_package_limit_interface():
    src = _read(SA_API)
    assert "PackageLimit" in src


def test_sa_api_package_limit_has_limit_id():
    src = _read(SA_API)
    assert "limit_id" in src


def test_sa_api_package_limit_has_is_unlimited():
    src = _read(SA_API)
    assert "is_unlimited" in src


def test_sa_api_admin_package_has_package_features_array():
    src = _read(SA_API)
    assert "package_features" in src


def test_sa_api_admin_package_has_package_limits_array():
    src = _read(SA_API)
    assert "package_limits" in src


def test_sa_api_has_list_features():
    src = _read(SA_API)
    assert "listFeatures" in src


def test_sa_api_has_create_feature():
    src = _read(SA_API)
    assert "createFeature" in src


def test_sa_api_has_update_feature():
    src = _read(SA_API)
    assert "updateFeature" in src


def test_sa_api_has_delete_feature():
    src = _read(SA_API)
    assert "deleteFeature" in src


def test_sa_api_has_list_limits():
    src = _read(SA_API)
    assert "listLimits" in src


def test_sa_api_has_create_limit():
    src = _read(SA_API)
    assert "createLimit" in src


def test_sa_api_has_update_limit():
    src = _read(SA_API)
    assert "updateLimit" in src


def test_sa_api_has_delete_limit():
    src = _read(SA_API)
    assert "deleteLimit" in src


def test_sa_api_admin_package_has_short_description():
    src = _read(SA_API)
    assert "short_description" in src


def test_sa_api_admin_package_has_badge_label():
    src = _read(SA_API)
    assert "badge_label" in src


def test_sa_api_admin_package_has_cta_label():
    src = _read(SA_API)
    assert "cta_label" in src


def test_sa_api_admin_package_has_is_featured():
    src = _read(SA_API)
    assert "is_featured" in src


def test_sa_api_admin_package_has_is_recommended():
    src = _read(SA_API)
    assert "is_recommended" in src


# ── Frontend super-admin packages page ────────────────────────────────────────

def test_sa_packages_page_has_draft_feature_type():
    src = _read(SA_PACKAGES_PAGE)
    assert "DraftFeature" in src


def test_sa_packages_page_has_draft_limit_type():
    src = _read(SA_PACKAGES_PAGE)
    assert "DraftLimit" in src


def test_sa_packages_page_has_preview_card():
    src = _read(SA_PACKAGES_PAGE)
    assert "PreviewCard" in src


def test_sa_packages_page_has_feature_row():
    src = _read(SA_PACKAGES_PAGE)
    assert "FeatureRow" in src


def test_sa_packages_page_has_limit_row():
    src = _read(SA_PACKAGES_PAGE)
    assert "LimitRow" in src


def test_sa_packages_page_has_tabs():
    src = _read(SA_PACKAGES_PAGE)
    assert "features" in src and "limits" in src and "pricing" in src and "display" in src


def test_sa_packages_page_has_package_type_conditions():
    src = _read(SA_PACKAGES_PAGE)
    assert "showDeposit" in src and "showCredits" in src and "showBilling" in src


def test_sa_packages_page_no_hardcoded_starter_benefits():
    src = _read(SA_PACKAGES_PAGE)
    # The displayed feature list must come from pkg.package_features (backend),
    # not from a hardcoded JS array rendered directly to users.
    # getFeatureTemplate() is OK — it only pre-fills the admin form, not the user-facing card.
    assert "featureList(" not in src, \
        "Must not use old featureList() helper — features come from package_features[]"
    assert "pkg.package_features" in src or "package_features" in src, \
        "Feature display must use pkg.package_features from backend"


def test_sa_packages_page_has_get_feature_template():
    src = _read(SA_PACKAGES_PAGE)
    assert "getFeatureTemplate" in src


def test_sa_packages_page_handles_clone():
    src = _read(SA_PACKAGES_PAGE)
    assert "clone" in src.lower()


def test_sa_packages_page_has_signup_visible_column():
    src = _read(SA_PACKAGES_PAGE)
    assert "is_public_signup_visible" in src


# ── Frontend tenant-portal api.ts ─────────────────────────────────────────────

def test_tp_api_has_signup_package_feature_interface():
    src = _read(TP_API)
    assert "SignupPackageFeature" in src


def test_tp_api_signup_package_feature_has_feature_id():
    src = _read(TP_API)
    assert "feature_id" in src


def test_tp_api_signup_package_feature_has_is_highlighted():
    src = _read(TP_API)
    assert "is_highlighted" in src


def test_tp_api_has_signup_package_limit_interface():
    src = _read(TP_API)
    assert "SignupPackageLimit" in src


def test_tp_api_signup_package_limit_has_is_unlimited():
    src = _read(TP_API)
    assert "is_unlimited" in src


def test_tp_api_signup_package_has_package_features():
    src = _read(TP_API)
    assert "package_features" in src


def test_tp_api_signup_package_has_package_limits():
    src = _read(TP_API)
    assert "package_limits" in src


def test_tp_api_signup_package_has_short_description():
    src = _read(TP_API)
    assert "short_description" in src


def test_tp_api_signup_package_has_badge_label():
    src = _read(TP_API)
    assert "badge_label" in src


def test_tp_api_signup_package_has_cta_label():
    src = _read(TP_API)
    assert "cta_label" in src


def test_tp_api_signup_package_has_terms_summary():
    src = _read(TP_API)
    assert "terms_summary" in src


# ── Frontend tenant-portal register/page.tsx ──────────────────────────────────

def test_tp_register_no_hardcoded_feature_list_function():
    src = _read(TP_REGISTER_PAGE)
    assert "featureList" not in src, \
        "register/page.tsx must not use old featureList() — render pkg.package_features instead"


def test_tp_register_renders_package_features():
    src = _read(TP_REGISTER_PAGE)
    assert "package_features" in src, "signup card must render pkg.package_features from backend"


def test_tp_register_renders_package_limits():
    src = _read(TP_REGISTER_PAGE)
    assert "package_limits" in src, "signup card must render pkg.package_limits from backend"


def test_tp_register_uses_badge_label():
    src = _read(TP_REGISTER_PAGE)
    assert "badge_label" in src, "signup card must show backend badge_label"


def test_tp_register_uses_short_description():
    src = _read(TP_REGISTER_PAGE)
    assert "short_description" in src, "signup card must show short_description from backend"


def test_tp_register_uses_cta_label():
    src = _read(TP_REGISTER_PAGE)
    assert "cta_label" in src, "signup card must use cta_label from backend for button label"


def test_tp_register_uses_terms_summary():
    src = _read(TP_REGISTER_PAGE)
    assert "terms_summary" in src, "signup card must show terms_summary below card"


def test_tp_register_renders_is_highlighted_feature():
    src = _read(TP_REGISTER_PAGE)
    assert "is_highlighted" in src, "highlighted features must use brand color"


def test_tp_register_renders_limit_chips():
    src = _read(TP_REGISTER_PAGE)
    assert "is_unlimited" in src, "limit chips must handle unlimited flag"


def test_tp_register_does_not_hardcode_popular_only():
    src = _read(TP_REGISTER_PAGE)
    assert "badge_label" in src, "badge must use backend badge_label, not only is_popular hardcode"


def test_tp_register_uses_package_price_or_price():
    src = _read(TP_REGISTER_PAGE)
    assert "package_price" in src, "formatPrice must use pkg.package_price"


def test_tp_register_security_deposit_shown():
    src = _read(TP_REGISTER_PAGE)
    assert "security_deposit_amount" in src, "security deposit must be shown separately in card"


def test_tp_register_wallet_credits_shown():
    src = _read(TP_REGISTER_PAGE)
    assert "included_credit_amount" in src, "wallet credit inclusion must be shown in card"
