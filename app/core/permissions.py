"""
ServiceOS — Complete RBAC Permission System
Level 5: granular permissions, role hierarchy, tenant-scoped overrides,
Redis-cached resolution, staff-level custom grants.

Permission format: "engine:resource:action"
Examples: "field_ops:jobs:read", "auth:users:create", "tenant:billing:manage"
"""
from __future__ import annotations
from typing import Callable
import structlog

logger = structlog.get_logger("permissions")


# ── Permission Constants ───────────────────────────────────────────────────────
class P:
    """All platform permissions as typed constants."""

    # ── Super Admin only ──────────────────────────────────────────────────────
    PLATFORM_ADMIN          = "platform:admin"
    PLATFORM_IMPERSONATE    = "platform:impersonate"
    PLATFORM_ENGINES_MANAGE = "platform:engines:manage"
    ENGINES_READ              = "engines:read"
    ENGINES_CREATE            = "engines:create"
    ENGINES_UPDATE            = "engines:update"
    ENGINES_ENABLE            = "engines:enable"
    ENGINES_DISABLE           = "engines:disable"
    ENGINES_IMPACT_PREVIEW    = "engines:impact_preview"
    ENGINES_CATEGORY_READ     = "engines:category_matrix:read"
    ENGINES_CATEGORY_UPDATE   = "engines:category_matrix:update"
    ENGINES_DEPS_READ         = "engines:dependencies:read"
    ENGINES_DEPS_UPDATE       = "engines:dependencies:update"
    ENGINES_PKG_READ          = "engines:package_entitlements:read"
    ENGINES_PKG_UPDATE        = "engines:package_entitlements:update"
    ENGINES_OVERRIDE_READ     = "engines:tenant_overrides:read"
    ENGINES_OVERRIDE_CREATE   = "engines:tenant_overrides:create"
    ENGINES_OVERRIDE_REVOKE   = "engines:tenant_overrides:revoke"
    ENGINES_HEALTH_READ       = "engines:health:read"
    ENGINES_HEALTH_CHECK      = "engines:health:check"
    ENGINES_PERMS_READ        = "engines:permissions:read"
    ENGINES_PERMS_UPDATE      = "engines:permissions:update"
    ENGINES_AUDIT_READ        = "engines:audit:read"
    ENGINES_AUDIT_EXPORT      = "engines:audit:export"
    PLATFORM_PLANS_MANAGE   = "platform:plans:manage"
    PLATFORM_AUDIT_READ     = "platform:audit:read"

    # ── Tenant management ─────────────────────────────────────────────────────
    TENANT_CREATE           = "tenant:create"
    TENANT_READ             = "tenant:read"
    TENANT_UPDATE           = "tenant:update"
    TENANT_SUSPEND          = "tenant:suspend"
    TENANT_TERMINATE        = "tenant:terminate"
    TENANT_REINSTATE        = "tenant:reinstate"
    TENANT_PLAN_MANAGE      = "tenant:plan:manage"
    TENANT_ENGINES_MANAGE   = "tenant:engines:manage"
    TENANT_FLAGS_MANAGE     = "tenant:flags:manage"
    TENANT_BILLING_READ     = "tenant:billing:read"
    TENANT_BILLING_MANAGE   = "tenant:billing:manage"
    TENANT_DATA_EXPORT      = "tenant:data:export"
    TENANT_DATA_DELETE      = "tenant:data:delete"
    TENANT_HEALTH_READ      = "tenant:health:read"
    TENANT_360_READ         = "tenant:360:read"

    # ── Tenant Onboarding & Approval (Phase 5) ─────────────────────────────────
    TENANT_VERIFY              = "tenants.verify"
    TENANT_APPROVE             = "tenants.approve"
    TENANT_REJECT              = "tenants.reject"
    TENANT_REQUEST_MORE_INFO   = "tenants.request_more_info"
    TENANT_ONBOARDING_READ     = "tenants.onboarding.read"
    TENANT_ONBOARDING_AUDIT_READ = "tenants.onboarding.audit.read"

    # ── User / Auth management ────────────────────────────────────────────────
    AUTH_USERS_READ         = "auth:users:read"
    AUTH_USERS_CREATE       = "auth:users:create"
    AUTH_USERS_UPDATE       = "auth:users:update"
    AUTH_USERS_DEACTIVATE   = "auth:users:deactivate"
    AUTH_SESSIONS_MANAGE    = "auth:sessions:manage"
    AUTH_MFA_MANAGE         = "auth:mfa:manage"
    AUTH_PERMISSIONS_MANAGE = "auth:permissions:manage"
    AUTH_APIKEYS_MANAGE     = "auth:apikeys:manage"
    AUTH_STAFF_INVITE       = "auth:staff:invite"
    AUTH_STAFF_MANAGE       = "auth:staff:manage"
    AUTH_AUDIT_READ         = "auth:audit:read"

    # ── Field Ops ─────────────────────────────────────────────────────────────
    FIELD_OPS_JOBS_READ     = "field_ops:jobs:read"
    FIELD_OPS_JOBS_CREATE   = "field_ops:jobs:create"
    FIELD_OPS_JOBS_UPDATE   = "field_ops:jobs:update"
    FIELD_OPS_JOBS_ASSIGN   = "field_ops:jobs:assign"
    FIELD_OPS_JOBS_CLOSE    = "field_ops:jobs:close"
    FIELD_OPS_JOBS_EXPORT   = "field_ops:jobs:export"
    FIELD_OPS_PHOTOS_CREATE = "field_ops:photos:create"
    FIELD_OPS_QUOTES_MANAGE = "field_ops:quotes:manage"
    FIELD_OPS_PARTS_ADD     = "field_ops:parts:add"
    FIELD_OPS_INVOICE_GEN   = "field_ops:invoice:generate"
    FIELD_OPS_REPORTS_READ  = "field_ops:reports:read"
    FIELD_OPS_SLA_MANAGE    = "field_ops:sla:manage"
    FIELD_OPS_CHECKLIST_MANAGE = "field_ops:checklist:manage"

    # ── Booking ───────────────────────────────────────────────────────────────
    BOOKING_READ            = "booking:bookings:read"
    BOOKING_CREATE          = "booking:bookings:create"
    BOOKING_CANCEL          = "booking:bookings:cancel"
    BOOKING_RESCHEDULE      = "booking:bookings:reschedule"
    BOOKING_MANAGE          = "booking:bookings:manage"
    BOOKING_SLOTS_MANAGE    = "booking:slots:manage"

    # ── Payment ───────────────────────────────────────────────────────────────
    PAYMENT_READ            = "payment:transactions:read"
    PAYMENT_CREATE          = "payment:transactions:create"
    PAYMENT_REFUND          = "payment:refunds:create"
    PAYMENT_INVOICE_READ    = "payment:invoices:read"
    PAYMENT_REPORTS_READ    = "payment:reports:read"
    PAYMENT_GATEWAY_MANAGE  = "payment:gateway:manage"

    # ── Analytics ─────────────────────────────────────────────────────────────
    ANALYTICS_READ          = "analytics:dashboard:read"
    ANALYTICS_EXPORT        = "analytics:data:export"
    ANALYTICS_ADVANCED      = "analytics:advanced:read"

    # ── Staff & Customers ─────────────────────────────────────────────────────
    STAFF_READ              = "staff:read"
    STAFF_MANAGE            = "staff:manage"
    STAFF_PERFORMANCE_READ  = "staff:performance:read"
    CUSTOMERS_READ          = "customers:read"
    CUSTOMERS_MANAGE        = "customers:manage"
    # ── Customer Users Enterprise Upgrade ────────────────────────────────────
    CUSTOMERS_VIEW_DETAIL           = "customers:view_detail"
    CUSTOMERS_EXPORT                = "customers:export"
    # FINAL-L5-05R — Enterprise Export resource mapping completion. Two new
    # export-shaped permission keys covering the Operations and Catalog/
    # Pricing/System-Configuration domains, which had no existing export
    # permission to reuse (unlike Finance/Security/Jobs, which already had
    # FINANCE_EXPORT/SECURITY_AUDIT_EXPORT/FIELD_OPS_JOBS_EXPORT).
    OPERATIONS_EXPORT              = "operations:export"
    CATALOG_EXPORT                 = "catalog:export"
    CUSTOMERS_BLOCK                 = "customers:block"
    CUSTOMERS_SUSPEND               = "customers:suspend"
    CUSTOMERS_REACTIVATE            = "customers:reactivate"
    CUSTOMERS_SESSIONS_READ         = "customers:sessions:read"
    CUSTOMERS_SESSIONS_REVOKE       = "customers:sessions:revoke"
    CUSTOMERS_LOGIN_HISTORY_READ    = "customers:login_history:read"
    CUSTOMERS_ADDRESSES_READ        = "customers:addresses:read"
    CUSTOMERS_ADDRESSES_VIEW_FULL   = "customers:addresses:view_full"
    CUSTOMERS_SERVICE_CREDITS_READ  = "customers:service_credits:read"
    CUSTOMERS_SERVICE_CREDITS_CREATE= "customers:service_credits:create"
    CUSTOMERS_PRIVACY_READ          = "customers:privacy:read"
    CUSTOMERS_AUDIT_READ            = "customers:audit:read"

    # ── Inventory ─────────────────────────────────────────────────────────────
    INVENTORY_READ          = "inventory:items:read"
    INVENTORY_WRITE         = "inventory:items:write"
    INVENTORY_DEDUCT        = "inventory:items:deduct"

    # ── Notification ──────────────────────────────────────────────────────────
    NOTIFICATION_SEND       = "notification:send"
    NOTIFICATION_TEMPLATES  = "notification:templates:manage"
    NOTIFICATION_LOGS_READ  = "notification:logs:read"

    # ── Notification Template Center (P0 Enterprise Upgrade) ────────────────
    NOTIF_TEMPLATES_READ           = "notifications.templates.read"
    NOTIF_TEMPLATES_CREATE         = "notifications.templates.create"
    NOTIF_TEMPLATES_UPDATE         = "notifications.templates.update"
    NOTIF_TEMPLATES_ACTIVATE       = "notifications.templates.activate"
    NOTIF_TEMPLATES_ARCHIVE        = "notifications.templates.archive"
    NOTIF_TEMPLATES_DELETE         = "notifications.templates.delete"
    NOTIF_TEMPLATES_CLONE          = "notifications.templates.clone"
    NOTIF_TEMPLATES_OVERRIDE       = "notifications.templates.override"
    NOTIF_TEMPLATES_TEST_SEND      = "notifications.templates.test_send"
    NOTIF_TEMPLATES_PREVIEW        = "notifications.templates.preview"
    NOTIF_TEMPLATES_SEED_DEFAULTS  = "notifications.templates.seed_defaults"
    NOTIF_TEMPLATES_ANALYTICS_READ = "notifications.templates.analytics.read"
    NOTIF_TEMPLATES_AUDIT_READ     = "notifications.templates.audit.read"
    NOTIF_TEMPLATES_VERSION_ROLLBACK = "notifications.templates.version.rollback"

    # ── Chat ──────────────────────────────────────────────────────────────────
    CHAT_READ               = "chat:messages:read"
    CHAT_WRITE              = "chat:messages:write"
    CHAT_MANAGE             = "chat:conversations:manage"

    # ── Review ────────────────────────────────────────────────────────────────
    REVIEW_READ             = "review:read"
    REVIEW_CREATE           = "review:create"
    REVIEW_RESPOND          = "review:respond"
    REVIEW_MODERATE         = "review:moderate"

    # ── RAG / AI ──────────────────────────────────────────────────────────────
    RAG_QUERY               = "rag:query"
    RAG_KB_MANAGE           = "rag:kb:manage"

    # ── Tenant Help & Support (Phase Y) ─────────────────────────────────────
    # Found missing from this registry entirely during the "make it 100%
    # working" pass -- app/engines/support/tenant_router.py references all
    # 5 of these on every request, crashing every call with AttributeError.
    SUPPORT_REQUESTS_CREATE   = "support:requests:create"
    SUPPORT_REQUESTS_VIEW     = "support:requests:view"
    SUPPORT_REQUESTS_VIEW_ALL = "support:requests:view_all"
    SUPPORT_REQUESTS_REPLY    = "support:requests:reply"
    SUPPORT_REQUESTS_REOPEN   = "support:requests:reopen"
    SUPPORT_INCIDENT_REPORT   = "support:incident:report"
    # ── Platform Admin Support Queue ─────────────────────────────────────────
    # Also missing entirely -- app/engines/support/admin_router.py references
    # all 6 of these on every request.
    SUPPORT_ADMIN_QUEUE_VIEW      = "support:admin:queue_view"
    SUPPORT_ADMIN_TRIAGE          = "support:admin:triage"
    SUPPORT_ADMIN_REPLY           = "support:admin:reply"
    SUPPORT_ADMIN_RESOLVE         = "support:admin:resolve"
    SUPPORT_ADMIN_INTERNAL_NOTE   = "support:admin:internal_note"
    SUPPORT_ADMIN_INCIDENT_MANAGE = "support:admin:incident_manage"

    # ── Tenant AI Assistant ───────────────────────────────────────────────────
    # ASSISTANT_USE is the tenant-side gate; the two admin permissions gate the
    # configuration console, which is platform-side only.
    ASSISTANT_USE              = "assistant:use"
    ASSISTANT_ADMIN_VIEW       = "assistant:admin:view"
    ASSISTANT_ADMIN_CONFIGURE  = "assistant:admin:configure"

    # ── Settings ──────────────────────────────────────────────────────────────
    SETTINGS_READ           = "settings:read"
    SETTINGS_WRITE          = "settings:write"
    SETTINGS_BRANDING       = "settings:branding:manage"
    # ── Platform Settings Enterprise Upgrade ─────────────────────────────────
    SETTINGS_CREATE                = "settings:create"
    SETTINGS_UPDATE                = "settings:update"
    SETTINGS_DELETE                = "settings:delete"
    SETTINGS_ENABLE                = "settings:enable"
    SETTINGS_DISABLE               = "settings:disable"
    SETTINGS_IMPACT_PREVIEW        = "settings:impact_preview"
    SETTINGS_ROLLBACK              = "settings:rollback"
    SETTINGS_SEED_DEFAULTS         = "settings:seed_defaults"
    SETTINGS_IMPORT                = "settings:import"
    SETTINGS_EXPORT                = "settings:export"
    SETTINGS_PLAN_READ             = "settings:plan:read"
    SETTINGS_PLAN_UPDATE           = "settings:plan:update"
    SETTINGS_CATEGORY_READ         = "settings:category:read"
    SETTINGS_CATEGORY_UPDATE       = "settings:category:update"
    SETTINGS_TENANT_OVERRIDES_READ   = "settings:tenant_overrides:read"
    SETTINGS_TENANT_OVERRIDES_CREATE = "settings:tenant_overrides:create"
    SETTINGS_TENANT_OVERRIDES_REVOKE = "settings:tenant_overrides:revoke"
    SETTINGS_FEATURE_FLAGS_READ     = "settings:feature_flags:read"
    SETTINGS_FEATURE_FLAGS_UPDATE   = "settings:feature_flags:update"
    SETTINGS_AUDIT_READ             = "settings:audit:read"
    SETTINGS_HISTORY_READ           = "settings:history:read"

    # ── Customer Addresses (Serviceability) ──────────────────────────────────
    CUSTOMER_ADDRESS_READ_OWN   = "customer_address:read_own"
    CUSTOMER_ADDRESS_CREATE_OWN = "customer_address:create_own"
    CUSTOMER_ADDRESS_UPDATE_OWN = "customer_address:update_own"
    CUSTOMER_ADDRESS_DELETE_OWN = "customer_address:delete_own"
    CUSTOMER_ADDRESS_ADMIN_READ = "customer_address:admin_read"

    # ── Tenant Service Areas (Serviceability) ────────────────────────────────
    TENANT_SERVICE_AREA_READ    = "tenant_service_area:read"
    TENANT_SERVICE_AREA_CREATE  = "tenant_service_area:create"
    TENANT_SERVICE_AREA_UPDATE  = "tenant_service_area:update"
    TENANT_SERVICE_AREA_DELETE  = "tenant_service_area:delete"

    # ── Tenant Service Area Service Mappings (Serviceability) ────────────────
    TENANT_SERVICE_AREA_SERVICE_READ   = "tenant_service_area_service:read"
    TENANT_SERVICE_AREA_SERVICE_CREATE = "tenant_service_area_service:create"

    # ── Intelligence Command Center ───────────────────────────────────────────
    INTELLIGENCE_READ   = "intelligence:read"
    INTELLIGENCE_WRITE  = "intelligence:write"
    INTELLIGENCE_MANAGE = "intelligence:manage"
    TENANT_SERVICE_AREA_SERVICE_UPDATE = "tenant_service_area_service:update"
    TENANT_SERVICE_AREA_SERVICE_DELETE = "tenant_service_area_service:delete"

    # ── Serviceability Matching (Step 3) ──────────────────────────────────────
    SERVICEABILITY_CHECK              = "serviceability:check"
    SERVICEABILITY_MATCH              = "serviceability:matching_tenants:read"
    SERVICEABILITY_AVAILABLE_SERVICES = "serviceability:available_services:read"
    SERVICEABILITY_ADMIN_TEST         = "serviceability:admin_test"

    # ── Admin Catalog (Sprint 3) ──────────────────────────────────────────────
    CATALOG_CATEGORIES_READ   = "catalog:categories:read"
    CATALOG_CATEGORIES_WRITE  = "catalog:categories:write"
    CATALOG_SERVICES_READ     = "catalog:services:read"
    CATALOG_SERVICES_WRITE    = "catalog:services:write"
    CATALOG_TYPES_READ        = "catalog:types:read"
    CATALOG_TYPES_WRITE       = "catalog:types:write"
    CATALOG_BRANDS_READ       = "catalog:brands:read"
    CATALOG_BRANDS_WRITE      = "catalog:brands:write"
    CATALOG_TIERS_READ        = "catalog:tiers:read"
    CATALOG_TIERS_WRITE       = "catalog:tiers:write"
    CATALOG_PRICING_READ      = "catalog:pricing:read"
    CATALOG_PRICING_WRITE     = "catalog:pricing:write"
    CATALOG_TENANT_ENABLE     = "catalog:tenant:enable"
    CATALOG_TENANT_READ       = "catalog:tenant:read"

    # ── Pricing & Rules (Phase 3) ────────────────────────────────────────────────
    PRICING_READ                    = "pricing.read"
    PRICING_CREATE                  = "pricing.create"
    PRICING_UPDATE                  = "pricing.update"
    PRICING_ARCHIVE                 = "pricing.archive"
    PRICING_TIERS_READ              = "pricing.tiers.read"
    PRICING_TIERS_CREATE            = "pricing.tiers.create"
    PRICING_TIERS_UPDATE            = "pricing.tiers.update"
    PRICING_CITY_ZIP_READ           = "pricing.city_zip.read"
    PRICING_CITY_ZIP_CREATE         = "pricing.city_zip.create"
    PRICING_CITY_ZIP_UPDATE         = "pricing.city_zip.update"
    PRICING_RULES_READ              = "pricing.rules.read"
    PRICING_RULES_CREATE            = "pricing.rules.create"
    PRICING_RULES_UPDATE            = "pricing.rules.update"
    PRICING_RULES_ACTIVATE          = "pricing.rules.activate"
    PRICING_RULES_DEACTIVATE        = "pricing.rules.deactivate"
    PRICING_RESOLVE_PREVIEW         = "pricing.resolve_preview"
    PRICING_BARGAIN_RULES_READ      = "pricing.bargain_rules.read"
    PRICING_BARGAIN_RULES_CREATE    = "pricing.bargain_rules.create"
    PRICING_BARGAIN_RULES_UPDATE    = "pricing.bargain_rules.update"
    PRICING_BARGAIN_EVALUATE_PREVIEW= "pricing.bargain_rules.evaluate_preview"
    PRICING_BARGAIN_RULES_ACTIVATE  = "pricing.bargain_rules.activate"
    PRICING_BARGAIN_RULES_DEACTIVATE= "pricing.bargain_rules.deactivate"
    PRICING_BARGAIN_RULES_AUDIT_READ= "pricing.bargain_rules.audit.read"
    PRICING_PROVIDER_OVERRIDES_READ    = "pricing.provider_overrides.read"
    PRICING_PROVIDER_OVERRIDES_CREATE  = "pricing.provider_overrides.create"
    PRICING_PROVIDER_OVERRIDES_UPDATE  = "pricing.provider_overrides.update"
    PRICING_PROVIDER_OVERRIDES_APPROVE = "pricing.provider_overrides.approve"
    PRICING_PROVIDER_OVERRIDES_REJECT  = "pricing.provider_overrides.reject"
    PRICING_PROVIDER_OVERRIDES_VALIDATE_PREVIEW = "pricing.provider_overrides.validate_preview"
    PRICING_PROVIDER_OVERRIDES_ACTIVATE   = "pricing.provider_overrides.activate"
    PRICING_PROVIDER_OVERRIDES_DEACTIVATE = "pricing.provider_overrides.deactivate"
    PRICING_PROVIDER_OVERRIDES_AUDIT_READ = "pricing.provider_overrides.audit.read"

    # ── Multi-Vertical Catalog Architecture ───────────────────────────────────
    VERTICALS_READ            = "verticals:read"
    VERTICALS_CREATE          = "verticals:create"
    VERTICALS_UPDATE          = "verticals:update"
    VERTICALS_ENABLE          = "verticals:enable"
    VERTICALS_DISABLE         = "verticals:disable"
    CATALOG_HOME_SERVICES_READ         = "catalog:home_services:read"
    CATALOG_HOME_SERVICES_UPDATE       = "catalog:home_services:update"
    # Home Services customer/provider directories (tenant_engine hs_*_router).
    # Same defect as FINANCE_MONETIZATION_* above: referenced by the routers
    # but never declared, so those three engines could not import and never
    # mounted -- the entire Home Services directory + dashboard API 404'd.
    HOME_SERVICES_CUSTOMERS_VIEW       = "home_services:customers:view"
    HOME_SERVICES_PROVIDERS_VIEW       = "home_services:providers:view"
    HOME_SERVICES_PROVIDERS_EXPORT     = "home_services:providers:export"
    CATALOG_COACHING_READ              = "catalog:coaching:read"
    CATALOG_COACHING_UPDATE            = "catalog:coaching:update"
    CATALOG_REAL_ESTATE_READ           = "catalog:real_estate:read"
    CATALOG_REAL_ESTATE_UPDATE         = "catalog:real_estate:update"
    CATALOG_RESTAURANT_READ            = "catalog:restaurant:read"
    CATALOG_RESTAURANT_UPDATE          = "catalog:restaurant:update"
    CATALOG_PRODUCTS_READ              = "catalog:products:read"
    CATALOG_PRODUCTS_UPDATE            = "catalog:products:update"
    CATALOG_PROFESSIONAL_SERVICES_READ   = "catalog:professional_services:read"
    CATALOG_PROFESSIONAL_SERVICES_UPDATE = "catalog:professional_services:update"
    NAVIGATION_MENU_READ      = "navigation:menu:read"
    NAVIGATION_MENU_UPDATE    = "navigation:menu:update"

    # ── Service Setup Templates ───────────────────────────────────────────────
    SETUP_TEMPLATES_READ    = "setup_templates:read"
    SETUP_TEMPLATES_WRITE   = "setup_templates:write"
    SETUP_TEMPLATES_PUBLISH = "setup_templates:publish"

    # ── Service Setup Bulk Wizard ─────────────────────────────────────────────
    BULK_WIZARD_READ    = "bulk_wizard:read"
    BULK_WIZARD_WRITE   = "bulk_wizard:write"
    BULK_WIZARD_EXECUTE = "bulk_wizard:execute"

    # ── Finance Hub (P0 Enterprise Finance Upgrade) ───────────────────────────
    FINANCE_READ              = "finance:hub:read"
    FINANCE_EXPORT            = "finance:hub:export"
    FINANCE_DEPOSITS_READ     = "finance:deposits:read"
    FINANCE_DEPOSITS_UPDATE   = "finance:deposits:update"
    FINANCE_DEPOSITS_APPROVE  = "finance:deposits:approve"
    FINANCE_DEPOSITS_REFUND   = "finance:deposits:refund"
    FINANCE_TOPUPS_READ       = "finance:topups:read"
    FINANCE_TOPUPS_UPDATE     = "finance:topups:update"
    FINANCE_TOPUPS_REFUND     = "finance:topups:refund"
    FINANCE_CLAIMS_READ       = "finance:claims:read"
    FINANCE_CLAIMS_ASSIGN     = "finance:claims:assign"
    FINANCE_CLAIMS_APPROVE    = "finance:claims:approve"
    FINANCE_CLAIMS_REJECT     = "finance:claims:reject"
    FINANCE_CLAIMS_SETTLE     = "finance:claims:settle"
    FINANCE_PAYOUTS_READ      = "finance:payouts:read"
    FINANCE_PAYOUTS_APPROVE   = "finance:payouts:approve"
    FINANCE_PAYOUTS_REJECT    = "finance:payouts:reject"
    FINANCE_PAYOUTS_PROCESS   = "finance:payouts:process"
    FINANCE_PAYOUTS_COMPLETE  = "finance:payouts:complete"
    FINANCE_WALLETS_READ      = "finance:wallets:read"
    FINANCE_WALLETS_ADJUST    = "finance:wallets:adjust"
    FINANCE_AUDIT_READ        = "finance:audit:read"
    # Home Services usage-credit administration. These are intentionally
    # distinct from customer service credits and generic cash-wallet access.
    FINANCE_HOME_SERVICES_CREDITS_VIEW         = "finance.home_services.credits.view"
    FINANCE_HOME_SERVICES_CREDITS_EXPORT       = "finance.home_services.credits.export"
    FINANCE_HOME_SERVICES_CREDITS_AUDIT        = "finance.home_services.credits.audit"
    FINANCE_HOME_SERVICES_TOPUPS_VIEW          = "finance.home_services.topups.view"
    FINANCE_HOME_SERVICES_TOPUPS_RECONCILE     = "finance.home_services.topups.reconcile"
    FINANCE_HOME_SERVICES_ADJUSTMENTS_CREATE   = "finance.home_services.adjustments.create"
    FINANCE_HOME_SERVICES_ADJUSTMENTS_APPROVE  = "finance.home_services.adjustments.approve"
    FINANCE_HOME_SERVICES_LEDGER_VIEW          = "finance.home_services.ledger.view"
    # Vertical Monetization policy workspace (vertical_monetization engine).
    # These constants were referenced by the engine's admin_router but never
    # declared here, so importing that router raised AttributeError and the
    # WHOLE engine silently failed to mount -- every /v1/admin/monetization/
    # verticals route 404'd in production.
    FINANCE_MONETIZATION_READ    = "finance:monetization:read"
    FINANCE_MONETIZATION_DRAFT   = "finance:monetization:draft"
    FINANCE_MONETIZATION_PUBLISH = "finance:monetization:publish"

    # Platform Configuration workspace (settings_engine configuration_router).
    # Same never-declared defect: the router referenced these, could not
    # import, and the whole engine failed to mount -- /v1/admin/configuration
    # 404'd everywhere.
    CONFIGURATION_READ                  = "configuration:read"
    CONFIGURATION_CHANGE_REQUEST_CREATE = "configuration:change_request:create"
    CONFIGURATION_APPROVE               = "configuration:approve"
    CONFIGURATION_ACTIVATE              = "configuration:activate"
    CONFIGURATION_ROLLBACK              = "configuration:rollback"
    CONFIGURATION_AUDIT_READ            = "configuration:audit:read"

    # Direct (cash/UPI-to-provider) payments — invoice_payment
    # direct_payments_router. Never-declared, engine never mounted.
    DIRECT_PAYMENTS_READ            = "direct_payments:read"
    DIRECT_PAYMENTS_DECLARE         = "direct_payments:declare"
    DIRECT_PAYMENTS_CORRECT         = "direct_payments:correct"
    DIRECT_PAYMENTS_EXPORT          = "direct_payments:export"
    DIRECT_PAYMENTS_OPEN_DISPUTE    = "direct_payments:open_dispute"
    DIRECT_PAYMENTS_REMIND_CUSTOMER = "direct_payments:remind_customer"
    DIRECT_PAYMENTS_UPLOAD_EVIDENCE = "direct_payments:upload_evidence"

    # Tenant-facing Home Services finance hub — finance_hub
    # tenant_hs_finance_router. Never-declared, engine never mounted.
    TENANT_FINANCE_READ                   = "tenant_finance:read"
    TENANT_FINANCE_EXPORT                 = "tenant_finance:export"
    TENANT_FINANCE_POLICY_READ            = "tenant_finance:policy:read"
    TENANT_FINANCE_TRANSACTIONS_READ      = "tenant_finance:transactions:read"
    TENANT_FINANCE_RECEIPTS_DOWNLOAD      = "tenant_finance:receipts:download"
    TENANT_FINANCE_DEPOSIT_READ           = "tenant_finance:deposit:read"
    TENANT_FINANCE_DEPOSIT_REFUND_REQUEST = "tenant_finance:deposit:refund_request"
    TENANT_FINANCE_BUY_CREDITS            = "tenant_finance:buy_credits"
    # Customer Credits + Dispute Settlement (migration 080)
    FINANCE_SETTLEMENTS_READ    = "finance:settlements:read"
    FINANCE_SETTLEMENTS_CREATE  = "finance:settlements:create"
    FINANCE_SETTLEMENTS_APPROVE = "finance:settlements:approve"
    FINANCE_SETTLEMENTS_EXECUTE = "finance:settlements:execute"
    FINANCE_SETTLEMENTS_CANCEL  = "finance:settlements:cancel"
    FINANCE_CREDITS_READ        = "finance:credits:read"
    FINANCE_CREDITS_CREATE      = "finance:credits:create"
    FINANCE_CREDITS_CANCEL      = "finance:credits:cancel"
    FINANCE_CREDITS_EXTEND      = "finance:credits:extend"
    FINANCE_PENALTIES_READ      = "finance:penalties:read"

    # ── Packages / Plans (Phase 4) ────────────────────────────────────────────
    PACKAGES_READ        = "packages.read"
    PACKAGES_CREATE      = "packages.create"
    PACKAGES_UPDATE      = "packages.update"
    PACKAGES_ARCHIVE     = "packages.archive"
    PACKAGES_ACTIVATE    = "packages.activate"
    PACKAGES_DEACTIVATE  = "packages.deactivate"
    PACKAGES_CLONE       = "packages.clone"
    PACKAGES_AUDIT_READ  = "packages.audit.read"

    # ── Provider Usage Credits / Security Deposits (Phase 4) ──────────────────
    FINANCE_USAGE_CREDITS_READ         = "finance.usage_credits.read"
    FINANCE_USAGE_CREDITS_TOP_UP       = "finance.usage_credits.top_up"
    FINANCE_USAGE_CREDITS_ADJUST       = "finance.usage_credits.adjust"
    FINANCE_USAGE_CREDITS_LEDGER_READ  = "finance.usage_credits.ledger.read"
    FINANCE_COMPLETED_JOB_DEDUCTION_RULES_READ = "finance.completed_job_deduction_rules.read"
    # FINAL-L5-05U DEPRECATED (mission rule 27: no deprecated alias may grant
    # access after migration). This was a second, parallel Security Deposit
    # permission namespace, independent of the canonical `FINANCE_DEPOSITS_*`
    # family above -- a live audit found the frontend nav item, the page's
    # RequirePermission route guard, and the permission catalog all checked
    # THIS namespace's `.read` key while the page's own action menu and every
    # backend endpoint it calls checked the canonical `finance:deposits:*`
    # family instead, so no role could ever both see AND successfully use the
    # page without holding both namespaces simultaneously. The 4 endpoints
    # these keys used to gate (package_commerce.admin_router's
    # `/v1/admin/tenants/{tenant_id}/security-deposit*`) are now blocked
    # (410); CONFIG_UPDATE/CREATE/HOLD/AUDIT_READ were never wired to any
    # endpoint at all (confirmed via `git grep` -- zero non-permissions.py
    # references). The constants remain defined (never deleted -- Part 13
    # requires an explicit, not silent, disposition) but are no longer
    # assigned to any role bundle and are pinned by an automated guard so
    # they cannot silently re-authorize anything. See
    # docs/final-l5-05/FINAL_L5_05U_ADR_SECURITY_DEPOSIT_CANONICAL_PERMISSION.md.
    FINANCE_SECURITY_DEPOSITS_READ           = "finance.security_deposits.read"            # DEPRECATED — use FINANCE_DEPOSITS_READ
    FINANCE_SECURITY_DEPOSITS_CONFIG_UPDATE  = "finance.security_deposits.config.update"    # DEPRECATED — never wired to any endpoint
    FINANCE_SECURITY_DEPOSITS_CREATE         = "finance.security_deposits.create"           # DEPRECATED — never wired to any endpoint
    FINANCE_SECURITY_DEPOSITS_MARK_RECEIVED  = "finance.security_deposits.mark_received"    # DEPRECATED — use FINANCE_DEPOSITS_UPDATE
    FINANCE_SECURITY_DEPOSITS_HOLD           = "finance.security_deposits.hold"             # DEPRECATED — never wired to any endpoint
    FINANCE_SECURITY_DEPOSITS_RELEASE        = "finance.security_deposits.release"          # DEPRECATED — use FINANCE_DEPOSITS_REFUND
    FINANCE_SECURITY_DEPOSITS_ADJUST         = "finance.security_deposits.adjust"           # DEPRECATED — use FINANCE_DEPOSITS_UPDATE
    FINANCE_SECURITY_DEPOSITS_AUDIT_READ     = "finance.security_deposits.audit.read"       # DEPRECATED — never wired to any endpoint
    FINANCE_SETTINGS_READ    = "finance.settings.read"
    FINANCE_SETTINGS_UPDATE  = "finance.settings.update"

    # ── FINAL-L5-05L: canonical Admin-exec Jobs mutations (super-admin
    # service_jobs domain — distinct from the tenant-portal field_ops.* keys
    # above) and platform Roles/Permissions catalog reads ───────────────────
    ADMIN_JOBS_READ            = "admin:jobs:read"
    ADMIN_JOBS_REASSIGN        = "admin:jobs:reassign"
    ADMIN_JOBS_STATUS_OVERRIDE = "admin:jobs:status_override"
    ADMIN_JOBS_FORCE_CLOSE     = "admin:jobs:force_close"
    ADMIN_JOBS_VOID            = "admin:jobs:void"
    PLATFORM_ROLES_READ        = "platform:roles:read"
    PLATFORM_PERMISSIONS_READ  = "platform:permissions:read"

    # ── User Account Security (Phase 0E) ─────────────────────────────────────
    USERS_SECURITY_READ            = "users:security:read"
    USERS_SECURITY_LOCK            = "users:security:lock"
    USERS_SECURITY_UNLOCK          = "users:security:unlock"
    USERS_SECURITY_DEACTIVATE      = "users:security:deactivate"
    USERS_SECURITY_REACTIVATE      = "users:security:reactivate"
    USERS_SECURITY_REVOKE_SESSIONS = "users:security:revoke_sessions"
    USERS_SECURITY_VIEW_SESSIONS   = "users:security:view_sessions"
    USERS_SECURITY_VIEW_HISTORY    = "users:security:view_login_history"
    USERS_SECURITY_VIEW_AUDIT      = "users:security:view_audit"
    TENANT_STAFF_SECURITY_MANAGE   = "tenant_staff:security:manage"
    TENANT_STAFF_SECURITY_REVOKE   = "tenant_staff:security:revoke_sessions"
    TENANT_STAFF_SECURITY_HISTORY  = "tenant_staff:security:view_login_history"

    # ── Tenant Vertical Documents Workspace ──────────────────────────────────
    # Found missing entirely during the "make it 100% working" pass --
    # app/engines/vertical_catalog/tenant_documents_workspace_router.py
    # references both on every one of its endpoints.
    TENANT_DOCUMENTS_READ          = "tenant_documents:read"
    TENANT_DOCUMENTS_UPLOAD        = "tenant_documents:upload"

    # ── Security & Threats SOC (Security Enterprise Upgrade, migration 083) ──
    SECURITY_READ                  = "security:read"
    SECURITY_THREATS_READ          = "security:threats:read"
    SECURITY_THREATS_UPDATE        = "security:threats:update"
    SECURITY_THREATS_RESOLVE       = "security:threats:resolve"
    SECURITY_THREATS_BLOCK_IP      = "security:threats:block_ip"
    SECURITY_SESSIONS_READ         = "security:sessions:read"
    SECURITY_SESSIONS_REVOKE       = "security:sessions:revoke"
    SECURITY_IP_BLOCKLIST_READ     = "security:ip_blocklist:read"
    SECURITY_IP_BLOCKLIST_CREATE   = "security:ip_blocklist:create"
    SECURITY_IP_BLOCKLIST_UPDATE   = "security:ip_blocklist:update"
    SECURITY_IP_BLOCKLIST_REVOKE   = "security:ip_blocklist:revoke"
    SECURITY_API_KEYS_READ         = "security:api_keys:read"
    SECURITY_API_KEYS_CREATE       = "security:api_keys:create"
    SECURITY_API_KEYS_ROTATE       = "security:api_keys:rotate"
    SECURITY_API_KEYS_REVOKE       = "security:api_keys:revoke"
    SECURITY_AUDIT_READ            = "security:audit:read"
    SECURITY_AUDIT_EXPORT          = "security:audit:export"
    SECURITY_POLICIES_READ         = "security:policies:read"
    SECURITY_POLICIES_UPDATE       = "security:policies:update"

    # ── Trust & Quality Engine (Phase 1) ────────────────────────────────────────
    TRUST_QUALITY_READ             = "trust_quality:read"
    BADGE_RULES_READ               = "trust_quality:badge_rules:read"
    BADGE_RULES_WRITE               = "trust_quality:badge_rules:write"
    BADGE_MANAGEMENT_READ          = "trust_quality:badge_management:read"
    BADGE_MANAGEMENT_WRITE         = "trust_quality:badge_management:write"
    HEALTH_RULES_READ              = "trust_quality:health_rules:read"
    HEALTH_RULES_WRITE             = "trust_quality:health_rules:write"
    HEALTH_MANAGEMENT_READ         = "trust_quality:health_management:read"
    RISK_SCORING_READ              = "trust_quality:risk_scoring:read"
    RISK_SCORING_WRITE             = "trust_quality:risk_scoring:write"
    RECALCULATION_JOBS_READ        = "trust_quality:recalculation_jobs:read"
    RECALCULATION_JOBS_RUN         = "trust_quality:recalculation_jobs:run"

    # ── Marketing Automation Command Center ─────────────────────────────────────
    MARKETING_AUTOMATION_READ      = "marketing.automation.read"
    MARKETING_POSTS_CREATE         = "marketing.posts.create"
    MARKETING_POSTS_UPDATE         = "marketing.posts.update"
    MARKETING_POSTS_APPROVE        = "marketing.posts.approve"
    MARKETING_POSTS_SCHEDULE       = "marketing.posts.schedule"
    MARKETING_POSTS_PUBLISH        = "marketing.posts.publish"
    MARKETING_POSTS_RETRY          = "marketing.posts.retry"
    MARKETING_POSTS_CANCEL         = "marketing.posts.cancel"
    MARKETING_CAMPAIGNS_READ       = "marketing.campaigns.read"
    MARKETING_CAMPAIGNS_CREATE     = "marketing.campaigns.create"
    MARKETING_CAMPAIGNS_UPDATE     = "marketing.campaigns.update"
    MARKETING_CAMPAIGNS_PAUSE      = "marketing.campaigns.pause"
    MARKETING_AI_GENERATE_CAPTION  = "marketing.ai.generate_caption"
    MARKETING_AI_GENERATE_IMAGE    = "marketing.ai.generate_image"
    MARKETING_AI_MANAGE_BUDGET     = "marketing.ai.manage_budget"
    MARKETING_SOCIAL_ACCOUNTS_READ       = "marketing.social_accounts.read"
    MARKETING_SOCIAL_ACCOUNTS_CONNECT    = "marketing.social_accounts.connect"
    MARKETING_SOCIAL_ACCOUNTS_DISCONNECT = "marketing.social_accounts.disconnect"
    MARKETING_TEMPLATES_READ       = "marketing.templates.read"
    MARKETING_TEMPLATES_CREATE     = "marketing.templates.create"
    MARKETING_TEMPLATES_UPDATE     = "marketing.templates.update"
    MARKETING_ANALYTICS_READ       = "marketing.analytics.read"
    MARKETING_AUDIT_READ           = "marketing.audit.read"

    # ── Platform Command Center Dashboard ───────────────────────────────────────
    DASHBOARD_READ                 = "dashboard.read"
    DASHBOARD_FINANCE_READ         = "dashboard.finance.read"
    DASHBOARD_OPERATIONS_READ      = "dashboard.operations.read"
    DASHBOARD_SECURITY_READ        = "dashboard.security.read"
    DASHBOARD_COMPLIANCE_READ      = "dashboard.compliance.read"
    DASHBOARD_EXPORT               = "dashboard.export"
    DASHBOARD_ACTION_QUEUE_MANAGE  = "dashboard.action_queue.manage"
    DASHBOARD_ENGINE_HEALTH_READ   = "dashboard.engine_health.read"
    DASHBOARD_ACTIVITY_READ        = "dashboard.activity.read"

    # ── DPDP Compliance Command Center ──────────────────────────────────────────
    COMPLIANCE_DPDP_READ            = "compliance.dpdp.read"
    COMPLIANCE_DPDP_REQUESTS_CREATE = "compliance.dpdp.requests.create"
    COMPLIANCE_DPDP_REQUESTS_UPDATE = "compliance.dpdp.requests.update"
    COMPLIANCE_DPDP_REQUESTS_VERIFY = "compliance.dpdp.requests.verify"
    COMPLIANCE_DPDP_REQUESTS_APPROVE= "compliance.dpdp.requests.approve"
    COMPLIANCE_DPDP_REQUESTS_REJECT = "compliance.dpdp.requests.reject"
    COMPLIANCE_DPDP_EXPORTS_GENERATE= "compliance.dpdp.exports.generate"
    COMPLIANCE_DPDP_EXPORTS_DOWNLOAD= "compliance.dpdp.exports.download"
    COMPLIANCE_DPDP_ERASURE_VALIDATE= "compliance.dpdp.erasure.validate"
    COMPLIANCE_DPDP_ERASURE_RUN     = "compliance.dpdp.erasure.run"
    COMPLIANCE_DPDP_CONSENT_READ    = "compliance.dpdp.consent.read"
    COMPLIANCE_DPDP_CONSENT_WITHDRAW= "compliance.dpdp.consent.withdraw"
    COMPLIANCE_DPDP_RETENTION_MANAGE= "compliance.dpdp.retention.manage"
    COMPLIANCE_DPDP_LEGAL_HOLDS_MANAGE = "compliance.dpdp.legal_holds.manage"
    COMPLIANCE_DPDP_EVIDENCE_GENERATE  = "compliance.dpdp.evidence.generate"
    COMPLIANCE_DPDP_SETTINGS_MANAGE = "compliance.dpdp.settings.manage"
    COMPLIANCE_DPDP_AUDIT_READ      = "compliance.dpdp.audit.read"

    # ── Wildcard ──────────────────────────────────────────────────────────────
    ALL                     = "*"


# ── Role Default Permissions ──────────────────────────────────────────────────
ROLE_PERMISSIONS: dict[str, list[str]] = {

    "super_admin": [P.ALL],  # Full platform access

    "tenant_owner": [
        # Tenant self-management
        P.TENANT_READ, P.TENANT_UPDATE, P.TENANT_BILLING_READ, P.TENANT_BILLING_MANAGE,
        P.TENANT_DATA_EXPORT, P.TENANT_HEALTH_READ, P.TENANT_ENGINES_MANAGE, P.TENANT_FLAGS_MANAGE,
        # User management within their tenant
        P.AUTH_USERS_READ, P.AUTH_USERS_CREATE, P.AUTH_USERS_UPDATE, P.AUTH_USERS_DEACTIVATE,
        P.AUTH_SESSIONS_MANAGE, P.AUTH_PERMISSIONS_MANAGE, P.AUTH_APIKEYS_MANAGE,
        P.AUTH_STAFF_INVITE, P.AUTH_STAFF_MANAGE, P.AUTH_AUDIT_READ,
        # Operations
        P.FIELD_OPS_JOBS_READ, P.FIELD_OPS_JOBS_CREATE, P.FIELD_OPS_JOBS_ASSIGN,
        P.FIELD_OPS_JOBS_UPDATE, P.FIELD_OPS_JOBS_CLOSE, P.FIELD_OPS_JOBS_EXPORT, P.FIELD_OPS_REPORTS_READ,
        P.FIELD_OPS_SLA_MANAGE, P.FIELD_OPS_QUOTES_MANAGE, P.FIELD_OPS_INVOICE_GEN, P.FIELD_OPS_CHECKLIST_MANAGE,
        P.BOOKING_READ, P.BOOKING_CREATE, P.BOOKING_CANCEL, P.BOOKING_RESCHEDULE,
        P.BOOKING_MANAGE, P.BOOKING_SLOTS_MANAGE,
        P.PAYMENT_READ, P.PAYMENT_CREATE, P.PAYMENT_REFUND, P.PAYMENT_INVOICE_READ,
        P.PAYMENT_REPORTS_READ, P.PAYMENT_GATEWAY_MANAGE,
        P.ANALYTICS_READ, P.ANALYTICS_EXPORT, P.ANALYTICS_ADVANCED,
        P.STAFF_READ, P.STAFF_MANAGE, P.STAFF_PERFORMANCE_READ,
        P.CUSTOMERS_READ, P.CUSTOMERS_MANAGE,
        P.INVENTORY_READ, P.INVENTORY_WRITE, P.INVENTORY_DEDUCT,
        P.NOTIFICATION_SEND, P.NOTIFICATION_TEMPLATES, P.NOTIFICATION_LOGS_READ,
        P.CHAT_READ, P.CHAT_WRITE, P.CHAT_MANAGE,
        P.REVIEW_READ, P.REVIEW_RESPOND, P.REVIEW_MODERATE,
        P.RAG_QUERY, P.RAG_KB_MANAGE,
        P.SETTINGS_READ, P.SETTINGS_WRITE, P.SETTINGS_BRANDING,
        P.SUPPORT_REQUESTS_CREATE, P.SUPPORT_REQUESTS_VIEW, P.SUPPORT_REQUESTS_VIEW_ALL,
        P.SUPPORT_REQUESTS_REPLY, P.SUPPORT_REQUESTS_REOPEN, P.SUPPORT_INCIDENT_REPORT,
        P.ASSISTANT_USE,
        # Service areas — own tenant only (service enforces tenant scoping)
        P.TENANT_SERVICE_AREA_READ, P.TENANT_SERVICE_AREA_CREATE,
        P.TENANT_SERVICE_AREA_UPDATE, P.TENANT_SERVICE_AREA_DELETE,
        P.TENANT_SERVICE_AREA_SERVICE_READ, P.TENANT_SERVICE_AREA_SERVICE_CREATE,
        P.TENANT_SERVICE_AREA_SERVICE_UPDATE, P.TENANT_SERVICE_AREA_SERVICE_DELETE,
        # Limited read of addresses for customers connected via a booking/job
        P.CUSTOMER_ADDRESS_ADMIN_READ,
        # Serviceability matching (service layer filters to own tenant)
        P.SERVICEABILITY_CHECK,
        P.SERVICEABILITY_MATCH,
        # Staff security management — own tenant staff only (service enforces)
        P.TENANT_STAFF_SECURITY_MANAGE, P.TENANT_STAFF_SECURITY_REVOKE,
        P.TENANT_STAFF_SECURITY_HISTORY,
        P.USERS_SECURITY_READ, P.USERS_SECURITY_VIEW_SESSIONS,
        P.USERS_SECURITY_VIEW_HISTORY, P.USERS_SECURITY_LOCK,
        P.USERS_SECURITY_UNLOCK, P.USERS_SECURITY_DEACTIVATE,
        P.USERS_SECURITY_REACTIVATE, P.USERS_SECURITY_REVOKE_SESSIONS,
        P.TENANT_DOCUMENTS_READ, P.TENANT_DOCUMENTS_UPLOAD,
        # Real bug fixed here: DIRECT_PAYMENTS_* permissions were defined
        # but never assigned to any role, so every tenant_owner got a 403
        # on their own Home Services direct-payments workspace.
        P.DIRECT_PAYMENTS_READ, P.DIRECT_PAYMENTS_DECLARE, P.DIRECT_PAYMENTS_CORRECT,
        P.DIRECT_PAYMENTS_EXPORT, P.DIRECT_PAYMENTS_OPEN_DISPUTE,
        P.DIRECT_PAYMENTS_REMIND_CUSTOMER, P.DIRECT_PAYMENTS_UPLOAD_EVIDENCE,
        # Same bug, same fix: TENANT_FINANCE_* was defined but never
        # assigned to any role -- every tenant_owner got a 403 on their own
        # Home Services finance workspace (/v1/tenant/home-services/finance).
        P.TENANT_FINANCE_READ, P.TENANT_FINANCE_EXPORT, P.TENANT_FINANCE_POLICY_READ,
        P.TENANT_FINANCE_TRANSACTIONS_READ, P.TENANT_FINANCE_RECEIPTS_DOWNLOAD,
        P.TENANT_FINANCE_DEPOSIT_READ, P.TENANT_FINANCE_DEPOSIT_REFUND_REQUEST,
        P.TENANT_FINANCE_BUY_CREDITS,
    ],

    "staff": [
        # Default staff — field technician profile
        # Can be extended per staff member via StaffPermission table
        P.FIELD_OPS_JOBS_READ,     # Own assigned jobs only (service enforces)
        P.FIELD_OPS_JOBS_UPDATE,   # Status transitions on own jobs
        P.FIELD_OPS_JOBS_CLOSE,    # Record direct customer payment + close own jobs (Home Services model)
        P.FIELD_OPS_PHOTOS_CREATE, # Upload photos on own jobs
        P.FIELD_OPS_PARTS_ADD,     # Add parts to own jobs
        P.FIELD_OPS_QUOTES_MANAGE, # Create/update quotes on own jobs
        P.INVENTORY_READ,          # Browse parts catalog
        P.BOOKING_READ,            # View own schedule
        P.CHAT_READ, P.CHAT_WRITE, # Customer chat
        P.REVIEW_READ,             # View own ratings
        P.NOTIFICATION_LOGS_READ,  # Own notification history
        P.SETTINGS_READ,           # Business hours, service catalog
        P.TENANT_SERVICE_AREA_READ, # View (not edit) tenant's configured service areas
        P.RAG_QUERY,               # Query knowledge base mid-job
        P.SUPPORT_REQUESTS_CREATE, P.SUPPORT_REQUESTS_VIEW, P.SUPPORT_REQUESTS_REPLY, P.SUPPORT_REQUESTS_REOPEN,
        P.SUPPORT_INCIDENT_REPORT, P.ASSISTANT_USE,
    ],

    # "technician" is the role value actually seeded onto real staff/User rows
    # (see app/dependencies/auth.py::require_technician) — "staff" above was the
    # only key ever populated in this table, so every real technician account got
    # ZERO permissions from role defaults alone. Mirror "staff" exactly.
    "technician": [
        P.FIELD_OPS_JOBS_READ, P.FIELD_OPS_JOBS_UPDATE, P.FIELD_OPS_JOBS_CLOSE,
        P.FIELD_OPS_PHOTOS_CREATE, P.FIELD_OPS_PARTS_ADD, P.FIELD_OPS_QUOTES_MANAGE,
        P.INVENTORY_READ, P.BOOKING_READ, P.CHAT_READ, P.CHAT_WRITE, P.REVIEW_READ,
        P.NOTIFICATION_LOGS_READ, P.SETTINGS_READ, P.TENANT_SERVICE_AREA_READ, P.RAG_QUERY,
        P.SUPPORT_REQUESTS_CREATE, P.SUPPORT_REQUESTS_VIEW, P.SUPPORT_REQUESTS_REPLY, P.SUPPORT_REQUESTS_REOPEN,
        P.SUPPORT_INCIDENT_REPORT, P.ASSISTANT_USE,
    ],

    "customer": [
        P.BOOKING_CREATE,          # Make bookings
        P.BOOKING_READ,            # Own bookings only
        P.BOOKING_CANCEL,          # Cancel own bookings
        P.BOOKING_RESCHEDULE,      # Reschedule own bookings
        P.PAYMENT_INVOICE_READ,    # Own invoices
        P.REVIEW_CREATE,           # Post reviews
        P.REVIEW_READ,             # Read reviews
        P.CHAT_READ, P.CHAT_WRITE, # Support chat
        P.NOTIFICATION_LOGS_READ,  # Own notifications
        P.SETTINGS_READ,           # Business info
        # Own addresses only (service enforces ownership)
        P.CUSTOMER_ADDRESS_READ_OWN, P.CUSTOMER_ADDRESS_CREATE_OWN,
        P.CUSTOMER_ADDRESS_UPDATE_OWN, P.CUSTOMER_ADDRESS_DELETE_OWN,
        # Serviceability matching (service enforces address ownership)
        P.SERVICEABILITY_CHECK,
        P.SERVICEABILITY_MATCH,
        P.SERVICEABILITY_AVAILABLE_SERVICES,
    ],

    "guest": [
        P.BOOKING_READ,            # Public service catalog
        P.SETTINGS_READ,           # Business info for menu/booking
    ],

    # ── FINAL-L5-05L — canonical least-privilege platform Admin roles ──────────
    # None of these get P.ALL; super_admin remains the sole wildcard role.
    "admin_operations": [
        P.ASSISTANT_ADMIN_VIEW, P.ASSISTANT_ADMIN_CONFIGURE,
        P.ADMIN_JOBS_READ, P.ADMIN_JOBS_REASSIGN, P.ADMIN_JOBS_STATUS_OVERRIDE,
        P.ADMIN_JOBS_FORCE_CLOSE, P.ADMIN_JOBS_VOID,
        P.FIELD_OPS_JOBS_READ, P.FIELD_OPS_REPORTS_READ, P.FIELD_OPS_JOBS_EXPORT,
        P.TENANT_READ, P.TENANT_HEALTH_READ,
        # FINAL-L5-05P: Provider onboarding verify/reject/request-more-info
        # are real operational actions (Part 25's own expected policy lists
        # "Tenant verify"/"Provider verify" as ALLOW for Operations Admin).
        # These 4 real, distinct backend permissions existed but were
        # granted to zero non-super-admin roles before this sprint.
        P.TENANT_ONBOARDING_READ, P.TENANT_APPROVE, P.TENANT_REJECT, P.TENANT_REQUEST_MORE_INFO,
        P.STAFF_READ, P.STAFF_PERFORMANCE_READ,
        P.REVIEW_READ, P.REVIEW_MODERATE,
        P.NOTIFICATION_LOGS_READ, P.NOTIFICATION_SEND,
        P.ANALYTICS_READ,
        # FINAL-L5-05R: Operations Admin export of operational
        # customer-service content (Reviews/Complaints/Refund-Rework
        # Requests/Bookings/Coaching Appointments/Real Estate Leads) --
        # explicitly named as Operations-approved in this mission's own
        # Part 9 policy text ("Reviews... Complaints... operational
        # reports"), and Operations Admin already holds REVIEW_MODERATE
        # for this same domain.
        P.OPERATIONS_EXPORT,
        # FINAL-L5-05O: dashboard-widget read permissions, distinct from the
        # underlying domain read permissions above (Part 3/4's separation of
        # concerns) — Operations Admin sees the base + operations-domain
        # dashboard sections, engine health, and activity feed, plus the
        # action-queue quick-action permission (operational triage tool).
        P.DASHBOARD_READ, P.DASHBOARD_OPERATIONS_READ, P.DASHBOARD_ACTIVITY_READ,
        P.DASHBOARD_ENGINE_HEALTH_READ, P.DASHBOARD_ACTION_QUEUE_MANAGE,
        # Explicitly NOT granted: any FINANCE_*, ADMIN_JOBS is granted above
        # (operational, not financial) but Usage Credit / Top-up / Security
        # Deposit mutation and read permissions are deliberately absent —
        # Operations Admin has no financial domain access at all.
    ],

    "admin_finance": [
        P.FINANCE_READ, P.FINANCE_USAGE_CREDITS_READ, P.FINANCE_USAGE_CREDITS_TOP_UP,
        P.FINANCE_USAGE_CREDITS_ADJUST, P.FINANCE_USAGE_CREDITS_LEDGER_READ,
        P.FINANCE_HOME_SERVICES_CREDITS_VIEW, P.FINANCE_HOME_SERVICES_CREDITS_EXPORT,
        P.FINANCE_HOME_SERVICES_CREDITS_AUDIT, P.FINANCE_HOME_SERVICES_TOPUPS_VIEW,
        P.FINANCE_HOME_SERVICES_TOPUPS_RECONCILE,
        P.FINANCE_HOME_SERVICES_ADJUSTMENTS_CREATE,
        P.FINANCE_HOME_SERVICES_ADJUSTMENTS_APPROVE,
        P.FINANCE_HOME_SERVICES_LEDGER_VIEW,
        P.FINANCE_COMPLETED_JOB_DEDUCTION_RULES_READ,
        P.FINANCE_TOPUPS_READ, P.FINANCE_TOPUPS_UPDATE, P.FINANCE_TOPUPS_REFUND,
        # FINAL-L5-05U: the canonical Security Deposit permission family is
        # finance:deposits:* (backs the live /admin/finance/deposits page's
        # nav, route guard, and every action on it -- confirmed via a live
        # audit). FINAL-L5-05O's own bounded fix granted both this namespace
        # AND the now-deprecated FINANCE_SECURITY_DEPOSITS_* one; the
        # deprecated one is removed this sprint (it authorized nothing --
        # zero endpoints still check it -- see the P class definition for
        # the full removal rationale).
        P.FINANCE_DEPOSITS_READ, P.FINANCE_DEPOSITS_APPROVE, P.FINANCE_DEPOSITS_UPDATE,
        P.FINANCE_DEPOSITS_REFUND,
        P.FINANCE_SETTINGS_READ, P.FINANCE_AUDIT_READ, P.PACKAGES_AUDIT_READ, P.FINANCE_EXPORT,
        P.TENANT_READ, P.TENANT_BILLING_READ, P.TENANT_HEALTH_READ,
        # FINAL-L5-05O: base dashboard read (Finance Admin already had the
        # domain-specific DASHBOARD_FINANCE_READ below).
        P.DASHBOARD_READ, P.DASHBOARD_FINANCE_READ,
        # Explicitly NOT granted: ADMIN_JOBS_* (reassign/status-override/
        # force-close/void), STAFF mutation, PLATFORM_ROLES/PERMISSIONS,
        # SECURITY_* (sessions/devices/audit) — Finance Admin cannot perform
        # any operational job mutation or security administration. Also NOT
        # granted: FIELD_OPS_JOBS_EXPORT, SECURITY_AUDIT_EXPORT — Finance
        # Admin cannot export Operations or Security data (FINAL-L5-05O
        # rule 2/3).
    ],

    "admin_security": [
        P.SECURITY_READ, P.SECURITY_THREATS_READ, P.SECURITY_THREATS_UPDATE,
        P.SECURITY_THREATS_RESOLVE, P.SECURITY_THREATS_BLOCK_IP,
        P.SECURITY_SESSIONS_READ, P.SECURITY_SESSIONS_REVOKE,
        P.SECURITY_IP_BLOCKLIST_READ, P.SECURITY_IP_BLOCKLIST_CREATE,
        P.SECURITY_IP_BLOCKLIST_UPDATE, P.SECURITY_IP_BLOCKLIST_REVOKE,
        P.SECURITY_API_KEYS_READ, P.SECURITY_API_KEYS_CREATE,
        P.SECURITY_API_KEYS_ROTATE, P.SECURITY_API_KEYS_REVOKE,
        P.SECURITY_AUDIT_READ, P.SECURITY_AUDIT_EXPORT,
        P.SECURITY_POLICIES_READ,
        P.PLATFORM_ROLES_READ, P.PLATFORM_PERMISSIONS_READ,
        P.AUTH_USERS_READ, P.AUTH_AUDIT_READ,
        P.USERS_SECURITY_READ, P.USERS_SECURITY_VIEW_SESSIONS, P.USERS_SECURITY_VIEW_HISTORY,
        # FINAL-L5-05O: base + security-domain dashboard read.
        P.DASHBOARD_READ, P.DASHBOARD_SECURITY_READ,
        # Decision (Part 9): Security Admin gets read-only on the Roles/
        # Permissions catalog, not create/edit — the catalog is code-defined
        # RBAC (see roles_permissions/admin_router.py) with no real mutation
        # capability yet for ANY role including super_admin, so "manage" is
        # not a meaningful grant to withhold or extend at this time.
        # Explicitly NOT granted: any FINANCE_* key, ADMIN_JOBS_* key,
        # STAFF mutation — Security Admin cannot touch financial or
        # operational-job mutations.
    ],

    "admin_readonly": [
        P.ASSISTANT_ADMIN_VIEW,
        P.ADMIN_JOBS_READ, P.FIELD_OPS_JOBS_READ,
        P.TENANT_READ, P.TENANT_HEALTH_READ,
        P.STAFF_READ,
        P.FINANCE_READ,  # base gate required by finance_hub's shared _svc dependency
        P.FINANCE_USAGE_CREDITS_READ, P.FINANCE_USAGE_CREDITS_LEDGER_READ,
        P.FINANCE_HOME_SERVICES_CREDITS_VIEW,
        P.FINANCE_HOME_SERVICES_TOPUPS_VIEW,
        P.FINANCE_HOME_SERVICES_LEDGER_VIEW,
        # FINAL-L5-05U: was P.FINANCE_SECURITY_DEPOSITS_READ (deprecated
        # alias that authorized nothing -- zero live endpoints check it,
        # so Read Only held a "read" grant that couldn't actually read the
        # live /admin/finance/deposits page, which checks finance:deposits:read).
        # Migrated to the canonical key so this role's existing read-only
        # intent actually works end-to-end.
        P.FINANCE_TOPUPS_READ, P.FINANCE_DEPOSITS_READ,
        P.FINANCE_COMPLETED_JOB_DEDUCTION_RULES_READ, P.FINANCE_AUDIT_READ,
        P.SECURITY_READ, P.SECURITY_SESSIONS_READ, P.SECURITY_AUDIT_READ,
        P.PLATFORM_ROLES_READ, P.PLATFORM_PERMISSIONS_READ,
        P.AUTH_USERS_READ,
        P.ANALYTICS_READ,
        # FINAL-L5-05O: base dashboard read only -- deliberately NOT granted
        # any of DASHBOARD_FINANCE_READ / DASHBOARD_OPERATIONS_READ /
        # DASHBOARD_SECURITY_READ / DASHBOARD_ACTION_QUEUE_MANAGE / export,
        # consistent with the zero-mutation, minimal-exposure design of this
        # role even though it separately holds broad domain READ access.
        P.DASHBOARD_READ,
        # Zero mutation/adjust/approve/revoke/create/update/delete/export
        # permissions of any kind. Required invariant (Part 10): mutation
        # permission count == 0 for this role, enforced by an architecture
        # guard test.
    ],
}


# ── Permission Checker ────────────────────────────────────────────────────────
class PermissionChecker:
    """
    Checks if a user has a permission.
    Resolution order:
      1. Super admin → always YES
      2. Role wildcard → YES if role has P.ALL
      3. Exact match in role defaults → YES/NO
      4. Staff override in StaffPermission table → YES/NO (overrides role default)
      5. Engine wildcard (e.g., "field_ops:*") → YES if role has engine wildcard
    """

    def has(self, role: str, permission: str, overrides: dict[str, bool] | None = None) -> bool:
        """
        Check if role has permission, optionally with per-user overrides.
        overrides: {"field_ops:jobs:assign": True, "analytics:*": False}
        """
        if role == "super_admin":
            return True

        role_perms = ROLE_PERMISSIONS.get(role, [])

        # Role has ALL
        if P.ALL in role_perms:
            return True

        # Check explicit override first (most specific wins)
        if overrides:
            # Exact override
            if permission in overrides:
                return overrides[permission]
            # Engine-level wildcard override
            parts = permission.split(":")
            if len(parts) >= 2:
                engine_wildcard = f"{parts[0]}:*"
                if engine_wildcard in overrides:
                    return overrides[engine_wildcard]

        # Check role permissions
        if permission in role_perms:
            return True

        # Check engine-level wildcard in role
        parts = permission.split(":")
        if len(parts) >= 2:
            engine_wildcard = f"{parts[0]}:*"
            if engine_wildcard in role_perms:
                return True

        # Check resource-level wildcard
        if len(parts) >= 3:
            resource_wildcard = f"{parts[0]}:{parts[1]}:*"
            if resource_wildcard in role_perms:
                return True

        logger.debug("permission.denied", role=role, permission=permission)
        return False

    def all_permissions_for_role(self, role: str) -> list[str]:
        return ROLE_PERMISSIONS.get(role, [])


# Singleton
permission_checker = PermissionChecker()


# ── FastAPI Dependency Factory ────────────────────────────────────────────────
def require_permission(permission: str) -> Callable:
    """
    Factory returning a FastAPI dependency that checks a specific permission.

    Usage:
        @router.get("/jobs", dependencies=[Depends(require_permission(P.FIELD_OPS_JOBS_READ))])
        async def list_jobs(...): ...

    Or in handler:
        @router.post("/jobs/assign")
        async def assign_job(user: UserContext = Depends(require_permission(P.FIELD_OPS_JOBS_ASSIGN))): ...
    """
    async def _check(
        user: "UserContext" = __import__("fastapi", fromlist=["Depends"]).Depends(
            __import__("app.dependencies.auth", fromlist=["get_current_user"]).get_current_user
        )
    ) -> "UserContext":
        from app.exceptions import ServiceOSException
        has = permission_checker.has(
            role=user.role,
            permission=permission,
            overrides=getattr(user, "permission_overrides", None),
        )
        if not has:
            raise ServiceOSException(
                error_code="PERMISSION_DENIED",
                detail=f"Permission '{permission}' required. Your role '{user.role}' does not have this permission.",
                blocking_rule=f"required_permission: {permission}",
                resolution="Contact your administrator to grant this permission.",
                context={"required": permission, "role": user.role},
            )
        return user

    _check.__name__ = f"require_{permission.replace(':', '_')}"
    return _check


# ── Tenant read-only access_scope hardening ────────────────────────────────────
# Some tenant-side staff accounts carry role="tenant_owner" (for tenant-scoping
# purposes elsewhere in the codebase) but are restricted to a read-only
# access_scope (e.g. support agents). These scopes must NEVER be allowed to
# reach mutation endpoints, even though role-based ROLE_PERMISSIONS grants
# tenant_owner full TENANT_UPDATE etc. This check runs in the SAME dependency,
# BEFORE the endpoint body / request payload is parsed, so business validation
# (e.g. 422) can never be reached by a read-only-scoped caller.
TENANT_READONLY_ACCESS_SCOPES = {"customer_support_limited"}


def require_tenant_mutation_permission(permission: str) -> Callable:
    """
    Like require_permission(), but additionally denies (403) any tenant-side
    user whose access_scope marks them read-only — regardless of role-based
    permission grants. Use this (instead of require_permission) on every
    tenant mutation endpoint (service setup, coverage, pricing, publish, etc.)
    so read-only users are rejected at the authorization layer, before any
    business-rule validation runs.
    """
    role_check = require_permission(permission)

    async def _check(
        user: "UserContext" = __import__("fastapi", fromlist=["Depends"]).Depends(
            __import__("app.dependencies.auth", fromlist=["get_current_user"]).get_current_user
        )
    ) -> "UserContext":
        from app.exceptions import ServiceOSException
        # Role-based permission gate first (existing behavior preserved).
        user = await role_check(user)
        # Tenant read-only access_scope gate — super_admin is exempt.
        if user.role != "super_admin" and getattr(user, "access_scope", None) in TENANT_READONLY_ACCESS_SCOPES:
            raise ServiceOSException(
                error_code="PERMISSION_DENIED",
                detail=(
                    f"Your account has read-only access (access_scope='{user.access_scope}') "
                    "and cannot make changes. Contact an owner or manager to update this "
                    "information."
                ),
                blocking_rule=f"tenant_readonly_access_scope: {user.access_scope}",
                resolution="Contact your tenant owner or manager to request write access.",
                context={"required_permission": permission, "access_scope": user.access_scope},
            )
        return user

    _check.__name__ = f"require_tenant_mutation_{permission.replace(':', '_')}"
    return _check


async def require_tenant_owner_mutation(
    user: "UserContext" = __import__("fastapi", fromlist=["Depends"]).Depends(
        __import__("app.dependencies.auth", fromlist=["require_tenant_owner"]).require_tenant_owner
    )
) -> "UserContext":
    """
    Like require_tenant_owner(), but additionally denies (403) any tenant-side
    user whose access_scope marks them read-only -- the role-gated analogue of
    require_tenant_mutation_permission(), for routers (e.g. provider_portal)
    whose endpoints are gated by the require_tenant_owner ROLE dependency
    rather than a granular require_permission(P.X) permission. Use this in
    place of require_tenant_owner on any provider_portal-style mutation
    endpoint so a read-only-scoped tenant_owner is rejected before any
    business-rule validation runs, exactly like require_tenant_mutation_permission
    does for permission-gated endpoints.
    """
    from app.exceptions import ServiceOSException
    if user.role != "super_admin" and getattr(user, "access_scope", None) in TENANT_READONLY_ACCESS_SCOPES:
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=(
                f"Your account has read-only access (access_scope='{user.access_scope}') "
                "and cannot make changes. Contact an owner or manager to update this "
                "information."
            ),
            blocking_rule=f"tenant_readonly_access_scope: {user.access_scope}",
            resolution="Contact your tenant owner or manager to request write access.",
            context={"access_scope": user.access_scope},
        )
    return user


async def require_staff_or_above_mutation(
    user: "UserContext" = __import__("fastapi", fromlist=["Depends"]).Depends(
        __import__("app.dependencies.auth", fromlist=["require_staff_or_above"]).require_staff_or_above
    )
) -> "UserContext":
    """
    Like require_staff_or_above() (role in {super_admin, tenant_owner, staff,
    technician}), but additionally denies (403) any tenant-side user whose
    access_scope marks them read-only -- the access-scope-aware analogue for
    ServiceJob execution/assignment endpoints (Slice 2F-3B) where the acting
    persona is a technician/staff member operating on their OWN assigned
    ServiceJob (or a tenant_owner override), not a granular permission grant.
    Object/assignment ownership (which specific job the actor may act on) is
    NOT this dependency's job -- that remains enforced by the existing
    in-service-layer checks (_assert_staff_owns_job, ServiceJobAssignment
    matching), which this guard sits in front of, not in place of.
    """
    from app.exceptions import ServiceOSException
    if user.role != "super_admin" and getattr(user, "access_scope", None) in TENANT_READONLY_ACCESS_SCOPES:
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=(
                f"Your account has read-only access (access_scope='{user.access_scope}') "
                "and cannot make changes. Contact an owner or manager to update this "
                "information."
            ),
            blocking_rule=f"tenant_readonly_access_scope: {user.access_scope}",
            resolution="Contact your tenant owner or manager to request write access.",
            context={"access_scope": user.access_scope},
        )
    return user


async def require_mutation_access_scope(
    user: "UserContext" = __import__("fastapi", fromlist=["Depends"]).Depends(
        __import__("app.dependencies.auth", fromlist=["get_current_user"]).get_current_user
    )
) -> "UserContext":
    """
    Scope-only mutation guard (Slice 2F-31A / N01).

    Unlike require_staff_or_above_mutation and friends, this does NOT restrict
    the admitted role set at all -- it is for routes whose persona is
    intentionally mixed (e.g. a customer uploading their own media alongside
    tenant staff uploading business assets). It adds exactly one thing on top
    of get_current_user: rejection of a read-only mutation access_scope,
    using the SAME TENANT_READONLY_ACCESS_SCOPES check and the same
    before-body-parsing timing as every other *_mutation guard in this file.
    Object/tenant ownership remains the caller's responsibility (service layer
    or an explicit follow-up check), exactly as with the other *_mutation
    guards -- this is a fail-closed floor, not a full authorization decision.
    """
    from app.exceptions import ServiceOSException
    if user.role != "super_admin" and getattr(user, "access_scope", None) in TENANT_READONLY_ACCESS_SCOPES:
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=(
                f"Your account has read-only access (access_scope='{user.access_scope}') "
                "and cannot make changes. Contact an owner or manager to update this "
                "information."
            ),
            blocking_rule=f"tenant_readonly_access_scope: {user.access_scope}",
            resolution="Contact your tenant owner or manager to request write access.",
            context={"access_scope": user.access_scope},
        )
    return user


async def require_owner_or_office_staff_mutation(
    user: "UserContext" = __import__("fastapi", fromlist=["Depends"]).Depends(
        __import__("app.dependencies.auth", fromlist=["get_current_user"]).get_current_user
    )
) -> "UserContext":
    """
    Slice 2F-6A: role in {super_admin, tenant_owner, staff} -- deliberately
    EXCLUDES technician, unlike require_staff_or_above_mutation. Use this for
    back-office/web-only capabilities (e.g. invoice_payment.provider_router's
    record-payment/create-invoice/add-item) where no mobile/technician client
    has ever called the endpoint and no product evidence proves technician
    was an intended actor for this specific capability -- narrower than
    require_staff_or_above_mutation on purpose, per the "do not infer
    technician access merely because an existing guard happens to admit it"
    rule. Also denies (403) any tenant-side user whose access_scope marks
    them read-only, same as every other *_mutation guard in this module.
    """
    from app.exceptions import ServiceOSException
    from app.dependencies.auth import _check_force_password_change
    _check_force_password_change(user)
    if user.role not in ("super_admin", "tenant_owner", "staff"):
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Owner or office staff access required. Your role: '{user.role}'.",
            blocking_rule="required_role: tenant_owner | staff | super_admin",
        )
    if user.role != "super_admin" and getattr(user, "access_scope", None) in TENANT_READONLY_ACCESS_SCOPES:
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=(
                f"Your account has read-only access (access_scope='{user.access_scope}') "
                "and cannot make changes. Contact an owner or manager to update this "
                "information."
            ),
            blocking_rule=f"tenant_readonly_access_scope: {user.access_scope}",
            resolution="Contact your tenant owner or manager to request write access.",
            context={"access_scope": user.access_scope},
        )
    return user


def require_any_permission(*permissions: str) -> Callable:
    """Requires at least one of the listed permissions."""
    async def _check(
        user: "UserContext" = __import__("fastapi", fromlist=["Depends"]).Depends(
            __import__("app.dependencies.auth", fromlist=["get_current_user"]).get_current_user
        )
    ) -> "UserContext":
        from app.exceptions import ServiceOSException
        overrides = getattr(user, "permission_overrides", None)
        for perm in permissions:
            if permission_checker.has(user.role, perm, overrides):
                return user
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"One of these permissions required: {', '.join(permissions)}",
            blocking_rule=f"required_any: {' | '.join(permissions)}",
            resolution="Contact your administrator to grant the appropriate permission.",
        )

    _check.__name__ = f"require_any_{'_or_'.join(p.split(':')[-1] for p in permissions)}"
    return _check
