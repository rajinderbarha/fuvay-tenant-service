/**
 * FINAL-L5-05M — Central frontend permission metadata catalog.
 *
 * This is metadata only, NOT a second authorization engine. Permission
 * truth is always the server-provided array from GET /v1/auth/me
 * (app.core.permissions.ROLE_PERMISSIONS on the backend — see
 * app/core/permissions.py). Every key referenced here must exist in that
 * backend registry; this file only labels/groups them for UI use
 * (human-readable labels, domain grouping, read-vs-mutation shape) and
 * exists so navigation/route/action gates share one source instead of
 * repeating string literals across components.
 *
 * Keys intentionally mirror the backend's exact permission-key strings —
 * no aliasing, no frontend-invented keys.
 */

export type PermissionDomain =
  | "dashboard" | "tenants" | "operations" | "catalog" | "pricing"
  | "home_services" | "finance" | "security" | "platform" | "marketing";

export type PermissionShape = "read" | "mutation" | "export" | "admin";

export interface PermissionMeta {
  key: string;
  label: string;
  domain: PermissionDomain;
  shape: PermissionShape;
}

/** Every permission key this frontend references, matching
 * app/core/permissions.py exactly. Extend here first if a new nav item,
 * route or action needs a real backend permission. */
export const PERMISSION_CATALOG: Record<string, PermissionMeta> = {
  "tenant:read":                          { key: "tenant:read", label: "Read Tenants", domain: "tenants", shape: "read" },
  "field_ops:jobs:read":                  { key: "field_ops:jobs:read", label: "Read Jobs (tenant-portal)", domain: "operations", shape: "read" },
  "admin:jobs:read":                      { key: "admin:jobs:read", label: "Read Jobs (admin)", domain: "operations", shape: "read" },
  "admin:jobs:reassign":                  { key: "admin:jobs:reassign", label: "Reassign Job", domain: "operations", shape: "mutation" },
  "admin:jobs:status_override":           { key: "admin:jobs:status_override", label: "Override Job Status", domain: "operations", shape: "mutation" },
  "admin:jobs:force_close":               { key: "admin:jobs:force_close", label: "Force-close Job", domain: "operations", shape: "mutation" },
  "admin:jobs:void":                      { key: "admin:jobs:void", label: "Void Job", domain: "operations", shape: "mutation" },
  "staff:read":                           { key: "staff:read", label: "Read Staff", domain: "operations", shape: "read" },
  "analytics:dashboard:read":             { key: "analytics:dashboard:read", label: "Read Analytics/Reports", domain: "marketing", shape: "read" },
  "finance:hub:read":                     { key: "finance:hub:read", label: "Read Finance Hub", domain: "finance", shape: "read" },
  "finance.usage_credits.read":           { key: "finance.usage_credits.read", label: "Read Usage Credit Balance", domain: "finance", shape: "read" },
  "finance.usage_credits.ledger.read":    { key: "finance.usage_credits.ledger.read", label: "Read Usage Credit Ledger", domain: "finance", shape: "read" },
  "finance.usage_credits.adjust":         { key: "finance.usage_credits.adjust", label: "Adjust Usage Credit", domain: "finance", shape: "mutation" },
  "finance.usage_credits.top_up":         { key: "finance.usage_credits.top_up", label: "Top-up Usage Credit", domain: "finance", shape: "mutation" },
  "finance:topups:read":                  { key: "finance:topups:read", label: "Read Credit Top-ups", domain: "finance", shape: "read" },
  "finance:topups:update":                { key: "finance:topups:update", label: "Approve/Retry Credit Top-up", domain: "finance", shape: "mutation" },
  "finance:topups:refund":                { key: "finance:topups:refund", label: "Refund Credit Top-up", domain: "finance", shape: "mutation" },
  "finance.security_deposits.read":       { key: "finance.security_deposits.read", label: "Read Security Deposits", domain: "finance", shape: "read" },
  "finance.security_deposits.adjust":     { key: "finance.security_deposits.adjust", label: "Adjust Security Deposit", domain: "finance", shape: "mutation" },
  "finance.security_deposits.mark_received": { key: "finance.security_deposits.mark_received", label: "Mark Security Deposit Paid", domain: "finance", shape: "mutation" },
  "finance.security_deposits.release":    { key: "finance.security_deposits.release", label: "Release Security Deposit", domain: "finance", shape: "mutation" },
  "finance.completed_job_deduction_rules.read": { key: "finance.completed_job_deduction_rules.read", label: "Read Completed Job Deduction Rules", domain: "finance", shape: "read" },
  "security:read":                        { key: "security:read", label: "Read Security Overview", domain: "security", shape: "read" },
  "security:sessions:read":               { key: "security:sessions:read", label: "Read Sessions", domain: "security", shape: "read" },
  "security:sessions:revoke":             { key: "security:sessions:revoke", label: "Revoke Session", domain: "security", shape: "mutation" },
  "security:audit:read":                  { key: "security:audit:read", label: "Read Security Audit Log", domain: "security", shape: "read" },
  "security:audit:export":                { key: "security:audit:export", label: "Export Security Audit Log", domain: "security", shape: "export" },
  "auth:users:read":                      { key: "auth:users:read", label: "Read Users", domain: "platform", shape: "read" },
  "auth:audit:read":                      { key: "auth:audit:read", label: "Read Auth Audit", domain: "platform", shape: "read" },
  "platform:roles:read":                  { key: "platform:roles:read", label: "Read Roles Catalog", domain: "platform", shape: "read" },
  "platform:permissions:read":            { key: "platform:permissions:read", label: "Read Permissions Catalog", domain: "platform", shape: "read" },
};

/** Sentinel used for nav items/routes/actions whose backing backend
 * endpoint has not yet been converted off the coarse require_super_admin
 * role check (FINAL-L5-05L found only a bounded subset of endpoints were
 * converted to require_permission — see FINAL_L5_05L_ADMIN_ROLE_RUNTIME.md).
 * This is NOT a hardcoded role check standing in for real permission
 * metadata — it IS the real, honest metadata: it mirrors backend truth
 * exactly (only super_admin can reach these routes today) rather than
 * inventing a permission key the backend doesn't actually enforce. */
export const SUPER_ADMIN_ONLY = "__requires_super_admin__" as const;

export function isValidPermissionKey(key: string): boolean {
  return key === SUPER_ADMIN_ONLY || key in PERMISSION_CATALOG;
}
