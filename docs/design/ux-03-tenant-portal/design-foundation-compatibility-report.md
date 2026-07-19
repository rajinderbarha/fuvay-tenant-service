# Design Foundation Compatibility Report

Classification of UX-01 design-system components and UX-02 product-neutral
patterns for tenant-portal reuse.

| Component/Pattern | Classification | Notes |
|---|---|---|
| Button, Card, Field (Input/Textarea/Select), Modal, Drawer, Tooltip, Alert/Banner, Skeleton, StateViews (Empty/Error/PermissionDenied), PageShell/PageHeader/Section | REUSE_DIRECTLY | No tenant-specific change needed |
| StatusBadge + statusRegistry | REUSE_WITH_CONFIGURATION | Extended additively with tenant-specific status keys (see design-system change below); no removal, no rename |
| DataTable | REUSE_DIRECTLY | Generic columns/rows/mobileCard API fits tenant list pages as-is |
| UX-02 EnterpriseListPage / EnterpriseDetailPage / ReviewApprovalWorkspace | TENANT_SPECIFIC_WRAPPER_REQUIRED | Concepts generalized into new tenant-portal-local `TenantListPage`/`TenantDetailPage`/`OperationalWorkspace` rather than importing super-admin's copies (would create a cross-portal-app import) |
| UX-02 ReadinessTag | TENANT_SPECIFIC_WRAPPER_REQUIRED | Re-implemented locally in tenant-portal (same shape, `ReadinessState` type re-declared under `lib/ux03/types.ts` per the tenant role/permission model) rather than imported cross-app |
| UX-02 RoleDashboard | RUNTIME_VERIFICATION_REQUIRED | Role-branching concept is reusable but was not ported this phase; the pre-approval/approved dashboard split was built directly instead — see tenant-dashboard-specification.md |

## Design-system change made this phase

`frontend/packages/design-system/src/tokens/motion.ts`'s `statusRegistry`
gained ~24 new keys (e.g. `under_review`, `changes_requested`,
`denied_override`, `covered`, `held`) used by tenant-portal fixtures. This
is purely additive:
- No existing key's `tone`/`label` was changed.
- No existing key was removed or renamed.
- `StatusBadge` falls back to a humanized neutral badge for unknown keys
  regardless, so even a hypothetical omission would not throw.

Proof this cannot change Super Admin behavior: grepped every newly added
key across `frontend/super-admin/`. A handful of substring hits exist
(e.g. "partial coverage", "under review" inside free-text `description`
fields in `lib/ux02/nav-ia.ts`), but none are passed as a `StatusBadge`
`status=` prop — Super Admin's fixtures
(`frontend/super-admin/lib/ux02/fixtures.ts`) only ever use status values
that existed in `statusRegistry` before this change (`active`, `pending`,
`approved`, `in_review`, etc. — note `in_review`, not `under_review`).
No Super Admin `StatusBadge` rendering path is affected.
