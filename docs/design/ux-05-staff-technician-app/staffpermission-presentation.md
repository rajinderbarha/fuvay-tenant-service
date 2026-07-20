# StaffPermission Presentation

## Real-evidence gap
No StaffPermission-fetch endpoint is wired into `src/lib/api.ts` today. `permissionsFor()`
(`src/lib/ux05/permissions.ts`) returns an **all-denied** set for `technician`, and a **MOCK_DESIGN_ONLY,
still-all-denied** fixture set for `staff` — this phase does not fabricate a granted permission for any real
user. Every `StaffPermissionView.reason` for the staff fixture set explicitly says
`"MOCK_DESIGN_ONLY -- no live StaffPermission endpoint wired yet."` so no showcase screen can be mistaken for a
live-permission demo.

## Contract enforced regardless of data source
- `explicitDeny` always overrides `granted` (`hasPermission()`, unit-tested in
  `src/lib/ux05/__tests__/permissions.test.ts`).
- Every permission is `scopeTenantId`-bound; nothing cross-tenant is ever assumed granted.
- `PermissionRestrictedState` component renders whenever a check fails — presentation-only, never itself the
  security boundary (documented in its own file header).

## Known permission keys used by this design phase
`parts_request:approve`, `parts_request:reject`, `parts_request:mark_installed`, `quote:review`,
`checklist:review`, `assignment:manage`, `customer_issue:manage`, `finance:view_job_amount` — chosen to mirror
UX-04's tenant-portal permission surface conceptually (same operational concerns), not copied from any confirmed
backend enum. Confirming the real key names against the backend permission model is listed in
`backend-contract-blockers.md`.
