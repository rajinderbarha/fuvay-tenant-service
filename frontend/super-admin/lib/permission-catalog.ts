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
  // FINAL-L5-05O — dashboard widget/quick-action permissions. These are
  // distinct from the underlying domain read permissions (e.g. finance:hub:read)
  // by design (Part 3/4's separation of concerns): a role can read a domain's
  // detail pages without necessarily seeing that domain's dashboard widget,
  // and vice versa.
  "dashboard.read":                       { key: "dashboard.read", label: "Read Dashboard (base KPIs)", domain: "dashboard", shape: "read" },
  "dashboard.finance.read":               { key: "dashboard.finance.read", label: "Read Finance Dashboard Widget", domain: "dashboard", shape: "read" },
  "dashboard.operations.read":            { key: "dashboard.operations.read", label: "Read Operations Dashboard Widget", domain: "dashboard", shape: "read" },
  "dashboard.security.read":              { key: "dashboard.security.read", label: "Read Security Dashboard Widget", domain: "dashboard", shape: "read" },
  "dashboard.export":                     { key: "dashboard.export", label: "Export Dashboard Snapshot", domain: "dashboard", shape: "export" },
  "dashboard.action_queue.manage":        { key: "dashboard.action_queue.manage", label: "Manage Dashboard Action Queue", domain: "dashboard", shape: "mutation" },
  "dashboard.engine_health.read":         { key: "dashboard.engine_health.read", label: "Read Engine Health Widget", domain: "dashboard", shape: "read" },
  "dashboard.activity.read":              { key: "dashboard.activity.read", label: "Read Activity Feed Widget", domain: "dashboard", shape: "read" },
  "finance:hub:export":                   { key: "finance:hub:export", label: "Export Finance Hub Data", domain: "finance", shape: "export" },
  "field_ops:jobs:export":                { key: "field_ops:jobs:export", label: "Export Jobs Data", domain: "operations", shape: "export" },
  // FINAL-L5-05AB — Enterprise Export ("/v1/enterprise/exports") canonical
  // permission for operational resources (Service Bookings, Refund
  // Requests, etc.) per app/engines/enterprise_grid/filter_registry.py's
  // RESOURCE_EXPORT_PERMISSIONS. Distinct from field_ops:jobs:export
  // (legacy Jobs domain export, different resource/endpoint).
  "operations:export":                    { key: "operations:export", label: "Export Operational Records", domain: "operations", shape: "export" },
  // FINAL-L5-05P — Tenant/Provider onboarding lifecycle permissions.
  "tenant:read":                          { key: "tenant:read", label: "Read Tenants", domain: "tenants", shape: "read" },
  "tenants.onboarding.read":              { key: "tenants.onboarding.read", label: "Read Provider Onboarding", domain: "tenants", shape: "read" },
  "tenants.approve":                      { key: "tenants.approve", label: "Approve Provider Onboarding", domain: "tenants", shape: "mutation" },
  "tenants.reject":                       { key: "tenants.reject", label: "Reject Provider Onboarding", domain: "tenants", shape: "mutation" },
  "tenants.request_more_info":            { key: "tenants.request_more_info", label: "Request More Info (Onboarding)", domain: "tenants", shape: "mutation" },
  "field_ops:jobs:read":                  { key: "field_ops:jobs:read", label: "Read Jobs (tenant-portal)", domain: "operations", shape: "read" },
  "admin:jobs:read":                      { key: "admin:jobs:read", label: "Read Jobs (admin)", domain: "operations", shape: "read" },
  "admin:jobs:reassign":                  { key: "admin:jobs:reassign", label: "Reassign Job", domain: "operations", shape: "mutation" },
  "admin:jobs:status_override":           { key: "admin:jobs:status_override", label: "Override Job Status", domain: "operations", shape: "mutation" },
  "admin:jobs:force_close":               { key: "admin:jobs:force_close", label: "Force-close Job", domain: "operations", shape: "mutation" },
  "admin:jobs:void":                      { key: "admin:jobs:void", label: "Void Job", domain: "operations", shape: "mutation" },
  "staff:read":                           { key: "staff:read", label: "Read Staff", domain: "operations", shape: "read" },
  "home_services:staff:view":             { key: "home_services:staff:view", label: "Read Home Services Staff", domain: "home_services", shape: "read" },
  "home_services:staff:export":           { key: "home_services:staff:export", label: "Export Home Services Staff", domain: "home_services", shape: "export" },
  "home_services:staff:audit":            { key: "home_services:staff:audit", label: "Read Home Services Staff Audit", domain: "home_services", shape: "read" },
  "home_services:staff:request_changes":  { key: "home_services:staff:request_changes", label: "Request Home Services Staff Changes", domain: "home_services", shape: "mutation" },
  "home_services:staff:verify":           { key: "home_services:staff:verify", label: "Verify Home Services Staff", domain: "home_services", shape: "mutation" },
  "home_services:staff:restrict":         { key: "home_services:staff:restrict", label: "Restrict Home Services Staff", domain: "home_services", shape: "mutation" },
  "home_services:staff:suspend":          { key: "home_services:staff:suspend", label: "Suspend Home Services Staff", domain: "home_services", shape: "mutation" },
  "home_services:staff:reactivate":       { key: "home_services:staff:reactivate", label: "Reactivate Home Services Staff", domain: "home_services", shape: "mutation" },
  "analytics:dashboard:read":             { key: "analytics:dashboard:read", label: "Read Analytics/Reports", domain: "marketing", shape: "read" },
  "finance:hub:read":                     { key: "finance:hub:read", label: "Read Finance Hub", domain: "finance", shape: "read" },
  "finance.usage_credits.read":           { key: "finance.usage_credits.read", label: "Read Usage Credit Balance", domain: "finance", shape: "read" },
  "finance.usage_credits.ledger.read":    { key: "finance.usage_credits.ledger.read", label: "Read Usage Credit Ledger", domain: "finance", shape: "read" },
  "finance.usage_credits.adjust":         { key: "finance.usage_credits.adjust", label: "Adjust Usage Credit", domain: "finance", shape: "mutation" },
  "finance.usage_credits.top_up":         { key: "finance.usage_credits.top_up", label: "Top-up Usage Credit", domain: "finance", shape: "mutation" },
  "finance:topups:read":                  { key: "finance:topups:read", label: "Read Credit Top-ups", domain: "finance", shape: "read" },
  "finance:topups:update":                { key: "finance:topups:update", label: "Approve/Retry Credit Top-up", domain: "finance", shape: "mutation" },
  "finance:topups:refund":                { key: "finance:topups:refund", label: "Refund Credit Top-up", domain: "finance", shape: "mutation" },
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
