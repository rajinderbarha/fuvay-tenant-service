# Enterprise List Page Pattern

Component: `frontend/super-admin/components/ux02/patterns/EnterpriseListPage.tsx`.

## Used by
Tenant List (`/dev/ux-02/tenants`), Compliance Cases (`/dev/ux-02/compliance`),
Security Observations (`/dev/ux-02/security`) — 3 usages, satisfying "used by Tenant List + at
least 2 more".

## Props contract
`title`, `description`, `readiness`, `rows: T[]`, `columns: DataTableColumn<T>[]`, `rowKey`,
`searchFields`, optional `filters: ListFilterOption[]` + `getFilterValue`, optional
`bulkActions: {key,label}[]`, optional `mobileCard` render prop for the responsive fallback.

## Behavior
- Search box filters rows client-side via `searchFields`.
- Filter chips: each `ListFilterOption` renders as a set of togglable values; applied filters show
  as removable chips (see `filter-saved-view-system.md`).
- Selection + bulk actions render an impact-preview/confirmation step, never an immediate mutation
  (see `bulk-action-pattern.md`) — all `MOCK_DESIGN_ONLY` regardless of the page's overall readiness.
- Below the mobile breakpoint, `mobileCard(row)` replaces the `DataTable` entirely.

## Design-system usage
Built entirely from `@serviceos/design-system` primitives (`PageHeader`, `Section`, `DataTable`,
`Button`) plus the local `ReadinessTag` widget — no raw hex colors, no second status-color system.
