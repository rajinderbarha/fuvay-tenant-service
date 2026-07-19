# UX-01 Source Baseline (verified by reading actual files, not docs)

Verified against `frontend/packages/design-system/src/` and `frontend/super-admin/`.

## Design-system package
- `package.json`: `@serviceos/design-system`, exports `.` -> `src/index.ts`, plus `./theme.css`.
- `src/index.ts` re-exports tokens, theme (ThemeProvider), and `components/` (Button, Badge/StatusBadge,
  Input/Textarea/Select, Card, Modal, Drawer, Tooltip, Toast/Alert/Banner, Skeleton/Spinner,
  EmptyState/ErrorState/PermissionDeniedState, PageShell/PageHeader/Section, DataTable).
- `src/__tests__` exists — UX-01 wrote tests for the package itself (never run, see build-report.md).

## Super Admin app (existing, pre-UX-02)
- `lib/nav-config.ts` — `ADMIN_NAV_GROUPS: NavGroup[]`, each `NavItem` has
  `{id,label,href,icon?,group,permission?}`. Single source of truth already wired into
  `components/layout/AdminLayout.tsx`.
- `lib/permission-catalog.ts` — UI-only metadata labeling backend permission keys
  (`app.core.permissions.ROLE_PERMISSIONS`). Explicitly documents itself as not a second
  authorization engine.
- `hooks/usePermissions.ts`, `components/shared/PermissionGate.tsx` — existing gating helpers.
- `app/admin/**` — ~150 existing routes (see `existing-super-admin-route-audit.csv`).
- `components/enterprise/*` — `EnterpriseDataGrid`, `EnterpriseFilterBar`, `EnterpriseColumnManager`,
  `EnterprisePagination` already exist as a pre-UX-02 enterprise list toolkit (separate from the
  new `components/ux02/patterns/EnterpriseListPage.tsx` built in this phase — see compatibility report
  for why a new, design-system-native pattern was added rather than replacing these in place).

## Conclusion
UX-01's package and the existing super-admin nav/permission scaffolding are real, importable source
and are the basis this phase extends. See `ux01-source-compatibility-report.md` for the
reusable/extend/broken classification.
