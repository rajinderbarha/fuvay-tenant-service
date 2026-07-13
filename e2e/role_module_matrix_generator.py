"""
MODULE-L5-00A: role-to-module applicability matrix generator.

Produces a full 17-module x 10-role matrix (170 cells) with a reasoned,
evidence-based default per cell -- derived from the real permission-bundle
scoping already verified across the FINAL-L5-05 chain for the 5 admin_*
roles, and from documented business-role purpose for the other 5 roles
(tenant_owner, staff, technician, customer, guest), which is real domain
knowledge, not a naive guess: e.g. a customer cannot be DENIED from the
Booking module (a customer's core self-service purpose) and staff cannot
be granted Finance/Commission mutation rights (never true anywhere in
this codebase's permission registry).

This is a FIRST-PASS matrix appropriate for an L00A foundation gate --
each cell states its reasoning source; cells not yet independently
runtime-verified are marked accordingly, not silently claimed proven.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROLES = [
    "super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly",
    "tenant_owner", "staff", "technician", "customer", "guest",
]

MODULES = [
    "identity_access", "tenant_onboarding", "geography_serviceability", "catalog_offerings",
    "pricing_bargain", "provider_staff_availability", "packages_credits_deposits",
    "booking_matching_scheduling", "job_lifecycle", "finance_ledger_commission",
    "notifications_audit_workers", "reviews_rewards_disputes", "compliance_security_ops",
    "media_storage_exports", "system_configuration", "marketing_leads", "vertical_extensions",
]

# Per-module role defaults. Each entry: role -> (cell, reason, cert_status).
# cert_status reflects REAL prior verification depth, not aspiration:
#   "RUNTIME_VERIFIED" = directly proven in a prior FINAL-L5-05 sprint (admin roles only)
#   "SOURCE_INFERRED"  = derived from permission bundle / code inspection, not runtime-tested
#   "BUSINESS_DEFAULT"  = derived from documented business role purpose, not yet verified in code
RULES = {
    "identity_access": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("DENIED", "no AUTH_USERS_* write perms in bundle", "SOURCE_INFERRED"),
        "admin_finance": ("DENIED", "no AUTH_USERS_* write perms in bundle", "SOURCE_INFERRED"),
        "admin_security": ("SECONDARY_OPERATOR", "AUTH_USERS_READ, session/device revoke perms", "RUNTIME_VERIFIED"),
        "admin_readonly": ("READ_ONLY", "AUTH_USERS_READ only, 0 mutation perms (guarded invariant)", "RUNTIME_VERIFIED"),
        "tenant_owner": ("SELF_SERVICE", "manages own tenant's staff accounts", "BUSINESS_DEFAULT"),
        "staff": ("SELF_SERVICE", "own profile/session only", "BUSINESS_DEFAULT"),
        "technician": ("SELF_SERVICE", "own profile/session only", "BUSINESS_DEFAULT"),
        "customer": ("SELF_SERVICE", "own account/session only", "BUSINESS_DEFAULT"),
        "guest": ("SYSTEM_TRIGGER_ONLY", "registration/login entry point only", "BUSINESS_DEFAULT"),
    },
    "tenant_onboarding": {
        "super_admin": ("APPROVER", "tenant approve/reject/request-more-info endpoints", "RUNTIME_VERIFIED"),
        "admin_operations": ("APPROVER", "tenants.approve/reject granted per FINAL-L5-05P", "RUNTIME_VERIFIED"),
        "admin_finance": ("DENIED", "no tenant-approval perms in bundle", "SOURCE_INFERRED"),
        "admin_security": ("DENIED", "no tenant-approval perms in bundle", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "TENANT_READ granted, 0 mutation", "RUNTIME_VERIFIED"),
        "tenant_owner": ("PRIMARY_OPERATOR", "submits own onboarding application/documents", "BUSINESS_DEFAULT"),
        "staff": ("DENIED", "no onboarding ownership", "BUSINESS_DEFAULT"),
        "technician": ("DENIED", "no onboarding ownership", "BUSINESS_DEFAULT"),
        "customer": ("NOT_APPLICABLE", "tenant onboarding is a provider/business concern", "BUSINESS_DEFAULT"),
        "guest": ("SYSTEM_TRIGGER_ONLY", "initiates registration as a prospective tenant", "BUSINESS_DEFAULT"),
    },
    "geography_serviceability": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("PRIMARY_OPERATOR", "Service Area/Operations scope", "SOURCE_INFERRED"),
        "admin_finance": ("DENIED", "outside Finance domain", "SOURCE_INFERRED"),
        "admin_security": ("DENIED", "outside Security domain", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("PRIMARY_OPERATOR", "configures own Service Areas", "BUSINESS_DEFAULT"),
        "staff": ("READ_ONLY", "views assigned coverage area", "BUSINESS_DEFAULT"),
        "technician": ("READ_ONLY", "views assigned coverage area", "BUSINESS_DEFAULT"),
        "customer": ("SELF_SERVICE", "serviceability check for own address", "BUSINESS_DEFAULT"),
        "guest": ("SELF_SERVICE", "pre-registration serviceability check", "BUSINESS_DEFAULT"),
    },
    "catalog_offerings": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("PRIMARY_OPERATOR", "Operations scope per canonical role intent", "SOURCE_INFERRED"),
        "admin_finance": ("DENIED", "outside Finance domain", "SOURCE_INFERRED"),
        "admin_security": ("DENIED", "outside Security domain", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("SECONDARY_OPERATOR", "enables/configures offerings within admin-defined catalog", "BUSINESS_DEFAULT"),
        "staff": ("DENIED", "no catalog ownership", "BUSINESS_DEFAULT"),
        "technician": ("DENIED", "no catalog ownership", "BUSINESS_DEFAULT"),
        "customer": ("READ_ONLY", "browses catalog to book", "BUSINESS_DEFAULT"),
        "guest": ("READ_ONLY", "browses catalog pre-registration", "BUSINESS_DEFAULT"),
    },
    "pricing_bargain": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("DENIED", "Finance-adjacent, not Operations per canonical intent", "SOURCE_INFERRED"),
        "admin_finance": ("PRIMARY_OPERATOR", "Finance domain per canonical role intent", "SOURCE_INFERRED"),
        "admin_security": ("DENIED", "outside Security domain", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("SECONDARY_OPERATOR", "provider-level overrides within admin-set floors", "BUSINESS_DEFAULT"),
        "staff": ("DENIED", "no pricing ownership", "BUSINESS_DEFAULT"),
        "technician": ("DENIED", "no pricing ownership", "BUSINESS_DEFAULT"),
        "customer": ("SELF_SERVICE", "views price, participates in bargaining flow where enabled", "BUSINESS_DEFAULT"),
        "guest": ("READ_ONLY", "views indicative pricing pre-registration", "BUSINESS_DEFAULT"),
    },
    "provider_staff_availability": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("PRIMARY_OPERATOR", "Operations scope per canonical role intent", "SOURCE_INFERRED"),
        "admin_finance": ("DENIED", "outside Finance domain", "SOURCE_INFERRED"),
        "admin_security": ("DENIED", "outside Security domain", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("PRIMARY_OPERATOR", "manages own staff/technician roster and availability", "BUSINESS_DEFAULT"),
        "staff": ("SELF_SERVICE", "manages own availability", "BUSINESS_DEFAULT"),
        "technician": ("SELF_SERVICE", "manages own availability", "BUSINESS_DEFAULT"),
        "customer": ("NOT_APPLICABLE", "no direct customer interaction with provider roster admin", "BUSINESS_DEFAULT"),
        "guest": ("NOT_APPLICABLE", "no direct interaction", "BUSINESS_DEFAULT"),
    },
    "packages_credits_deposits": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("DENIED", "Finance domain, not Operations", "SOURCE_INFERRED"),
        "admin_finance": ("PRIMARY_OPERATOR", "FINANCE_USAGE_CREDITS_*, FINANCE_DEPOSITS_* perms", "RUNTIME_VERIFIED"),
        "admin_security": ("DENIED", "confirmed via FINAL-L5-05AL live 5-role matrix", "RUNTIME_VERIFIED"),
        "admin_readonly": ("READ_ONLY", "FINANCE_READ granted, 0 mutation", "RUNTIME_VERIFIED"),
        "tenant_owner": ("PRIMARY_OPERATOR", "submits Security Deposit, purchases packages", "BUSINESS_DEFAULT"),
        "staff": ("DENIED", "no financial ownership", "BUSINESS_DEFAULT"),
        "technician": ("DENIED", "no financial ownership", "BUSINESS_DEFAULT"),
        "customer": ("SELF_SERVICE", "views own Usage Credit/wallet balance where applicable", "BUSINESS_DEFAULT"),
        "guest": ("NOT_APPLICABLE", "no account yet", "BUSINESS_DEFAULT"),
    },
    "booking_matching_scheduling": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("APPROVER", "operational oversight, override/reassignment", "SOURCE_INFERRED"),
        "admin_finance": ("DENIED", "outside Finance domain", "SOURCE_INFERRED"),
        "admin_security": ("DENIED", "outside Security domain", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("READ_ONLY", "visibility into own tenant's bookings", "BUSINESS_DEFAULT"),
        "staff": ("SECONDARY_OPERATOR", "views/accepts assigned bookings", "BUSINESS_DEFAULT"),
        "technician": ("SECONDARY_OPERATOR", "views/accepts assigned bookings", "BUSINESS_DEFAULT"),
        "customer": ("PRIMARY_OPERATOR", "creates/cancels/reschedules own bookings -- core self-service purpose", "BUSINESS_DEFAULT"),
        "guest": ("SYSTEM_TRIGGER_ONLY", "may initiate booking flow pre-registration in some verticals", "BUSINESS_DEFAULT"),
    },
    "job_lifecycle": {
        "super_admin": ("OWNER", "P.ALL wildcard, force-close/void proven FINAL-L5-05AD", "RUNTIME_VERIFIED"),
        "admin_operations": ("APPROVER", "admin:jobs:force_close/void per FINAL-L5-05AD", "RUNTIME_VERIFIED"),
        "admin_finance": ("DENIED", "outside Finance domain", "SOURCE_INFERRED"),
        "admin_security": ("DENIED", "outside Security domain", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("READ_ONLY", "visibility into own tenant's job execution", "BUSINESS_DEFAULT"),
        "technician": ("PRIMARY_OPERATOR", "executes job: accept/en-route/arrived/in-progress/completed (confirmed, staff-app JobDetailScreen)", "SOURCE_INFERRED"),
        "staff": ("SECONDARY_OPERATOR", "dispatch/oversight of technicians", "BUSINESS_DEFAULT"),
        "customer": ("SELF_SERVICE", "confirms completion, provides quote approval where required", "BUSINESS_DEFAULT"),
        "guest": ("NOT_APPLICABLE", "no account yet", "BUSINESS_DEFAULT"),
    },
    "finance_ledger_commission": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("DENIED", "confirmed via FINAL-L5-05AJ live direct-navigation denial test", "RUNTIME_VERIFIED"),
        "admin_finance": ("PRIMARY_OPERATOR", "FINANCE_* permission bundle", "RUNTIME_VERIFIED"),
        "admin_security": ("DENIED", "outside Security domain", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("READ_ONLY", "views own tenant's commission/invoice ledger", "BUSINESS_DEFAULT"),
        "staff": ("DENIED", "no financial ownership", "BUSINESS_DEFAULT"),
        "technician": ("SELF_SERVICE", "views own earnings (staff-app EarningsScreen confirmed)", "SOURCE_INFERRED"),
        "customer": ("SELF_SERVICE", "views own invoice/receipt", "BUSINESS_DEFAULT"),
        "guest": ("NOT_APPLICABLE", "no account yet", "BUSINESS_DEFAULT"),
    },
    "notifications_audit_workers": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("READ_ONLY", "operational notifications visibility", "SOURCE_INFERRED"),
        "admin_finance": ("READ_ONLY", "financial notifications visibility", "SOURCE_INFERRED"),
        "admin_security": ("PRIMARY_OPERATOR", "AUTH_AUDIT_READ, SECURITY_AUDIT_* perms", "RUNTIME_VERIFIED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("SELF_SERVICE", "receives own tenant's notifications", "BUSINESS_DEFAULT"),
        "staff": ("SELF_SERVICE", "receives own assignment notifications", "BUSINESS_DEFAULT"),
        "technician": ("SELF_SERVICE", "receives own assignment notifications", "BUSINESS_DEFAULT"),
        "customer": ("SELF_SERVICE", "receives own booking/job notifications", "BUSINESS_DEFAULT"),
        "guest": ("SYSTEM_TRIGGER_ONLY", "OTP delivery only", "BUSINESS_DEFAULT"),
    },
    "reviews_rewards_disputes": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("APPROVER", "dispute/complaint operational resolution", "SOURCE_INFERRED"),
        "admin_finance": ("APPROVER", "Service Credit / refund financial resolution", "SOURCE_INFERRED"),
        "admin_security": ("DENIED", "outside Security domain", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("SECONDARY_OPERATOR", "responds to disputes/reviews about own tenant", "BUSINESS_DEFAULT"),
        "staff": ("DENIED", "no dispute-resolution ownership", "BUSINESS_DEFAULT"),
        "technician": ("READ_ONLY", "views own reviews/ratings", "BUSINESS_DEFAULT"),
        "customer": ("PRIMARY_OPERATOR", "submits reviews, raises disputes -- core self-service purpose", "BUSINESS_DEFAULT"),
        "guest": ("NOT_APPLICABLE", "no account yet", "BUSINESS_DEFAULT"),
    },
    "compliance_security_ops": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("DENIED", "outside Operations domain", "SOURCE_INFERRED"),
        "admin_finance": ("DENIED", "outside Finance domain", "SOURCE_INFERRED"),
        "admin_security": ("PRIMARY_OPERATOR", "SECURITY_THREATS_*, SECURITY_IP_BLOCKLIST_*, SECURITY_API_KEYS_* -- proven FINAL-L5-05AL/AM", "RUNTIME_VERIFIED"),
        "admin_readonly": ("READ_ONLY", "SECURITY_READ/SESSIONS_READ/AUDIT_READ granted, 0 mutation", "RUNTIME_VERIFIED"),
        "tenant_owner": ("SELF_SERVICE", "DPDP/compliance requests for own tenant data", "BUSINESS_DEFAULT"),
        "staff": ("NOT_APPLICABLE", "no compliance-request ownership", "BUSINESS_DEFAULT"),
        "technician": ("NOT_APPLICABLE", "no compliance-request ownership", "BUSINESS_DEFAULT"),
        "customer": ("SELF_SERVICE", "DPDP/compliance requests for own personal data", "BUSINESS_DEFAULT"),
        "guest": ("NOT_APPLICABLE", "no account yet", "BUSINESS_DEFAULT"),
    },
    "media_storage_exports": {
        "super_admin": ("OWNER", "P.ALL wildcard, export permission matrix proven FINAL-L5-05AA/AB/AD", "RUNTIME_VERIFIED"),
        "admin_operations": ("PRIMARY_OPERATOR", "operational exports per RESOURCE_EXPORT_PERMISSIONS", "RUNTIME_VERIFIED"),
        "admin_finance": ("PRIMARY_OPERATOR", "financial exports per RESOURCE_EXPORT_PERMISSIONS", "RUNTIME_VERIFIED"),
        "admin_security": ("PRIMARY_OPERATOR", "SECURITY_AUDIT_EXPORT proven FINAL-L5-05O", "RUNTIME_VERIFIED"),
        "admin_readonly": ("DENIED", "0 export creation by default policy, proven FINAL-L5-05AJ", "RUNTIME_VERIFIED"),
        "tenant_owner": ("SELF_SERVICE", "uploads own documents/logo/photos", "BUSINESS_DEFAULT"),
        "staff": ("SELF_SERVICE", "uploads job-site evidence photos where required", "BUSINESS_DEFAULT"),
        "technician": ("SELF_SERVICE", "uploads job-site evidence photos where required", "BUSINESS_DEFAULT"),
        "customer": ("SELF_SERVICE", "uploads profile photo, views own invoices/receipts", "BUSINESS_DEFAULT"),
        "guest": ("NOT_APPLICABLE", "no account yet", "BUSINESS_DEFAULT"),
    },
    "system_configuration": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("DENIED", "outside Operations domain", "SOURCE_INFERRED"),
        "admin_finance": ("DENIED", "outside Finance domain", "SOURCE_INFERRED"),
        "admin_security": ("PARTIAL", "Security Policy read-only proven; update ownership UNRESOLVED per FINAL-L5-05AM", "RUNTIME_VERIFIED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("SELF_SERVICE", "own tenant operational settings only", "BUSINESS_DEFAULT"),
        "staff": ("NOT_APPLICABLE", "no system-config ownership", "BUSINESS_DEFAULT"),
        "technician": ("NOT_APPLICABLE", "no system-config ownership", "BUSINESS_DEFAULT"),
        "customer": ("NOT_APPLICABLE", "no system-config ownership", "BUSINESS_DEFAULT"),
        "guest": ("NOT_APPLICABLE", "no system-config ownership", "BUSINESS_DEFAULT"),
    },
    "marketing_leads": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("DENIED", "outside Operations domain per canonical role intent", "SOURCE_INFERRED"),
        "admin_finance": ("DENIED", "outside Finance domain", "SOURCE_INFERRED"),
        "admin_security": ("DENIED", "outside Security domain", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("PRIMARY_OPERATOR", "manages own campaigns/promotions per FINAL-L5-05 marketing sprints", "BUSINESS_DEFAULT"),
        "staff": ("NOT_APPLICABLE", "no marketing ownership", "BUSINESS_DEFAULT"),
        "technician": ("NOT_APPLICABLE", "no marketing ownership", "BUSINESS_DEFAULT"),
        "customer": ("SELF_SERVICE", "redeems promotions/coupons", "BUSINESS_DEFAULT"),
        "guest": ("READ_ONLY", "sees public promotions pre-registration", "BUSINESS_DEFAULT"),
    },
    "vertical_extensions": {
        "super_admin": ("OWNER", "P.ALL wildcard", "RUNTIME_VERIFIED"),
        "admin_operations": ("PRIMARY_OPERATOR", "operational scope for non-home-services verticals", "SOURCE_INFERRED"),
        "admin_finance": ("DENIED", "outside Finance domain", "SOURCE_INFERRED"),
        "admin_security": ("DENIED", "outside Security domain", "SOURCE_INFERRED"),
        "admin_readonly": ("READ_ONLY", "0 mutation invariant", "RUNTIME_VERIFIED"),
        "tenant_owner": ("PRIMARY_OPERATOR", "operates own vertical-specific business (real estate/food/etc)", "BUSINESS_DEFAULT"),
        "staff": ("SECONDARY_OPERATOR", "executes vertical-specific workflows", "BUSINESS_DEFAULT"),
        "technician": ("NOT_APPLICABLE", "vertical extensions are non-home-services by definition", "BUSINESS_DEFAULT"),
        "customer": ("SELF_SERVICE", "consumes vertical-specific offerings via AI chat flows", "BUSINESS_DEFAULT"),
        "guest": ("SYSTEM_TRIGGER_ONLY", "AI chat lead capture pre-registration", "BUSINESS_DEFAULT"),
    },
}


def main():
    matrix = []
    unknown_cells = 0
    for module in MODULES:
        for role in ROLES:
            cell = RULES.get(module, {}).get(role)
            if cell is None:
                matrix.append({"module": module, "role": role, "cell": "UNKNOWN", "reason": None, "cert_status": None})
                unknown_cells += 1
            else:
                matrix.append({"module": module, "role": role, "cell": cell[0], "reason": cell[1], "cert_status": cell[2]})

    runtime_verified = sum(1 for m in matrix if m["cert_status"] == "RUNTIME_VERIFIED")
    source_inferred = sum(1 for m in matrix if m["cert_status"] == "SOURCE_INFERRED")
    business_default = sum(1 for m in matrix if m["cert_status"] == "BUSINESS_DEFAULT")

    out = {
        "modules_total": len(MODULES),
        "roles_total": len(ROLES),
        "cells_total": len(matrix),
        "cells_unknown": unknown_cells,
        "cells_runtime_verified": runtime_verified,
        "cells_source_inferred": source_inferred,
        "cells_business_default": business_default,
        "matrix": matrix,
    }
    out_path = os.path.join(ROOT, "docs", "module-l5", "role-module-matrix.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "matrix"}, indent=2))
    return 0 if unknown_cells == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
