# Authorization Helper Review — Workstream 3

## Existing helpers (frontend/tenant-portal/lib/api.ts, re-verified)
- `getUserRole()` — reads `serviceos_user_role` from `localStorage`.
- `getAccessScope()` — reads the `access_scope` claim directly off the JWT
  (E2E-09B pattern; UX polish only, backend is the real boundary).
- `isTenantReadOnly()` — `getAccessScope() === "customer_support_limited"`.
- `isTenantOwnerRole(role)` — `role === "tenant_owner" || role === undefined`
  (the `undefined` case is an intentional loading-state convention from
  FINAL-L5-03, preserved unchanged).

None of these existing helpers group `staff` and `technician` together —
there was no pre-existing bug to fix in that sense. The actual gap was
narrower: **no helper existed at all** that represented "tenant owner OR
canonical staff, excluding technician" (the exact persona needed for 3 of
the 4 invoice/payment capabilities), and no helper existed for
"tenant owner only, with technician/staff both excluded" combined with
the access-scope check in one call (the 4th capability, issue-invoice,
previously only had the raw `isTenantOwnerRole` building block available,
without the access-scope check folded in).

## New helpers added
```ts
export function isCanonicalStaffRole(role): boolean {
  return role === "staff";
}

export function canManageProviderInvoices(role, accessScope = getAccessScope()): boolean {
  if (accessScope === "customer_support_limited") return false;
  return isTenantOwnerRole(role) || isCanonicalStaffRole(role);
}

export function canIssueProviderInvoice(role, accessScope = getAccessScope()): boolean {
  if (accessScope === "customer_support_limited") return false;
  return isTenantOwnerRole(role);
}
```

- `isCanonicalStaffRole` checks the literal canonical role string
  `"staff"` only — `technician` is a distinct string value and is never
  matched. No `office_staff`/`manager`/`tenant_manager` alias was
  introduced.
- Both composed functions fold in the access-scope check directly, so a
  future call site cannot forget it (mirrors the backend's own
  `require_owner_or_office_staff_mutation`/`require_tenant_mutation_permission`
  pattern of checking role AND access-scope in one guard).
- Reuses `isTenantOwnerRole` and `getAccessScope()` exactly as they exist
  today — no backend role/permission was touched, no parallel
  authorization system was created.

## Access-scope availability
Confirmed `access_scope` is already present in the tenant-portal's JWT
payload and already read by `getAccessScope()` — no new field needed to
be threaded through from the backend. No fake frontend-only read-only
flag was introduced.

## Super-admin behavior
No existing tenant-portal impersonation/override behavior was found or
touched — `getUserRole()` would return whatever role a super_admin's
session carries (this codebase's existing behavior, unmodified). This
slice does not alter that.

## Why no live call site update was needed
As documented in `frontend-caller-inventory.csv`, zero components
currently call any of the 4 backend endpoints — there is no existing
`if (isTenantOwnerRole(...))`-style visibility check on an Issue/Record-
Payment/Create/Add-Item control to correct, because no such control
exists yet. The 2 new helper functions are added as correct,
policy-matching infrastructure for whenever such a control is built,
without redesigning or adding any UI this slice (out of scope: "do not
redesign the invoice interface").
