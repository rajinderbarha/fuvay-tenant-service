/**
 * DESIGN PHASE UX-05 -- canonical role derivation + StaffPermission
 * presentation helpers for the staff/technician mobile app.
 *
 * Canonical roles for THIS app's users: "staff" | "technician" ONLY.
 * tenant_owner/customer/super_admin/admin_* may appear as referenced
 * entities in data (e.g. a booking's customer) but never as a role a user
 * of this app holds. Never invent dispatcher/field_agent/branch_manager/
 * etc. -- see docs/design/ux-05-staff-technician-app/canonical-role-
 * presentation.md.
 *
 * IMPORTANT: real StaffUser (src/lib/api.ts) has no `role` field today --
 * the backend returns `specialisations`/`status`/`working_hours` but not an
 * explicit staff-vs-technician role flag. This module's `deriveRole` is
 * therefore READINESS-TAGGED "product_decision_required": until a real
 * role/permission field is confirmed on StaffUser, this UI defaults every
 * authenticated user to the more restrictive "technician" presentation
 * (fail-closed, not fail-open) and never fabricates elevated staff
 * capability from the frontend alone. Frontend hiding is never itself an
 * authorization boundary -- the backend remains the real gate regardless
 * of what this module decides to show.
 */
import type { StaffUser } from "../api";
import type { CanonicalMobileRole, StaffPermissionView } from "../../types/ux05";

export const KNOWN_PERMISSION_KEYS = [
  "parts_request:approve",
  "parts_request:reject",
  "parts_request:mark_installed",
  "quote:review",
  "checklist:review",
  "assignment:manage",
  "customer_issue:manage",
  "finance:view_job_amount",
] as const;
export type PermissionKey = typeof KNOWN_PERMISSION_KEYS[number];

/**
 * Fail-closed role derivation. `staffUser` has no live role/permission
 * field yet (see file header) -- this reads an optional, defensively-typed
 * `role` property if the backend ever adds one, and otherwise defaults to
 * "technician" (the least-privileged canonical presentation).
 */
export function deriveRole(staffUser: StaffUser & { role?: string }): CanonicalMobileRole {
  if (staffUser.role === "staff") return "staff";
  return "technician";
}

/**
 * No live StaffPermission-fetch endpoint is wired into src/lib/api.ts yet
 * (API_CONTRACT_REQUIRED -- see docs/design/ux-05-staff-technician-app/
 * backend-contract-blockers.md). This returns an all-denied set for
 * "technician" and a design-fixture set for "staff" so screens can render
 * a real permission-gated UI shape now without granting anything for real.
 */
export function permissionsFor(role: CanonicalMobileRole, tenantId: string | null): StaffPermissionView[] {
  const scopeTenantId = tenantId ?? "";
  if (role === "technician") {
    return KNOWN_PERMISSION_KEYS.map(key => ({
      permissionKey: key, granted: false, explicitDeny: false,
      scopeTenantId, reason: "Technicians do not hold tenant staff permissions.",
    }));
  }
  // Staff: design fixture, not a live grant -- see backend-contract-blockers.md.
  return KNOWN_PERMISSION_KEYS.map(key => ({
    permissionKey: key, granted: false, explicitDeny: false,
    scopeTenantId, reason: "MOCK_DESIGN_ONLY -- no live StaffPermission endpoint wired yet.",
  }));
}

export function hasPermission(permissions: StaffPermissionView[], key: PermissionKey): boolean {
  const p = permissions.find(x => x.permissionKey === key);
  if (!p) return false;
  if (p.explicitDeny) return false; // explicit deny always overrides grant
  return p.granted;
}
