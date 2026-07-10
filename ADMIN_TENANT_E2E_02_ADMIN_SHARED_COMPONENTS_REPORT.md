# Shared Admin UI Components Report (Part 8)

Real mapping of spec's expected component list to what already exists (`components/shared/ui.tsx`,
`components/shared/ApiStates.tsx`, `components/layout/*`):

| Spec-expected | Real equivalent | Notes |
|---|---|---|
| AdminShell | `AdminLayout` (`components/layout/AdminLayout.tsx`) | full shell: sidebar+topbar+main |
| AdminSidebar | inline `<aside>` inside `AdminLayout` | not extracted as standalone component; fine as-is |
| AdminTopbar | `TopNav` (private fn inside `AdminLayout.tsx`) | not exported separately; internal detail |
| AdminBreadcrumbs | `components/layout/Breadcrumbs.tsx` | exists but **unused** by any admin page (Part 4 finding) |
| AdminPageHeader | `SectionHeader` (`ui.tsx`) | title+subtitle+actions+icon — direct equivalent, used widely |
| AdminPageContainer | `<main>` wrapper in `AdminLayout` (maxWidth 1440, centered) | shell-level, automatic for every page |
| AdminKpiCard | `StatCard` (`ui.tsx`) | label/value/change/trend/icon/alert — direct equivalent |
| AdminDataTableShell | `DataTable<T>` (`ui.tsx`) | generic columns/rows/loading/empty — direct equivalent |
| AdminStatusBadge | `Badge` (`ui.tsx`) + `JobStatusBadge` (`ui.tsx`) | variant-based pill; direct equivalent |
| AdminEmptyState | `EmptyState` (`ui.tsx`) AND `ApiEmptyState` (`ApiStates.tsx`) | two near-duplicates — see below |
| AdminLoadingState | `Skeleton`/`Spinner` (`ui.tsx`) AND `ApiLoadingState` (`ApiStates.tsx`) | overlapping |
| AdminErrorState | `ApiErrorState` (`ApiStates.tsx`) | direct equivalent, has retry + request_id |
| AdminPermissionDeniedState | `ApiPermissionDeniedState` (`ApiStates.tsx`) | direct equivalent |
| RequestIdBadge | `RequestIdBadge` + `CopyRequestIdButton` (`ApiStates.tsx`) | exact name match already |

## Real gap found: EmptyState duplication
`ui.tsx`'s generic `EmptyState` and `ApiStates.tsx`'s `ApiEmptyState` are genuinely two separate
components with overlapping purpose (one is a bare presentational empty-state, the other is
API-response-aware with title/description/action). Not unified in this sprint — unifying them
touches every page that imports either, which is broader than the "shell/nav only" scope; flagged
as a real, low-risk follow-up (rename/alias, not a rewrite).

## Conclusion
No new component was created. Every spec-named component already has a real, working equivalent
under a different name except `AdminBreadcrumbs`, which exists but is dead code (unused) — the
gap is adoption, not absence, and adopting it across 157 page files is out of this sprint's scope.
