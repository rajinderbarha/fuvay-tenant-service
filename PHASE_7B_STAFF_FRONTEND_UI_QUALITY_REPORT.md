# Phase 7B — Static UI Quality Check

## Consistency

All 13 pages use the shared `StaffLayout` (except the login page itself, which is
pre-authentication) and the shared component library (`Card`, `StatCard`, `Badge`, `Skeleton`,
`EmptyState`, `Btn`, `Input`) from `components/shared/ui.tsx` — the same library already used
throughout the existing tenant-owner pages in this app. No new/duplicate component primitives
were introduced.

## Loading / error / empty states

Every data-driven page follows the same three-state pattern:
- **Loading:** `<Skeleton>` placeholders sized to the eventual content.
- **Error:** red-toned message block showing `error.message` and, when present, `Request ID: {requestId}`.
- **Empty:** `<EmptyState>` with an icon, a title, and explanatory copy — never a blank table.

## Honest-gap pages (Documents, Sessions, Activity)

Use the same `EmptyState` component as a normal empty-data state, but with copy explicitly
stating the feature "is not yet available in this app" rather than implying the technician
simply has no data yet — an intentional distinction so staff aren't misled into thinking a
working feature returned zero results.

## Responsive / layout notes

All pages use CSS grid/flexbox with `auto-fit`/`minmax` for stat-card rows, consistent with the
existing app's pages. No fixed pixel-width assumptions beyond the 240px sidebar (also consistent
with existing layout conventions in this app).

## Accessibility notes

Disabled forbidden-action buttons in the Job Detail shell use `title="Not certified in this
phase"` (native tooltip) and are marked `disabled` (removes them from the tab order's active
interaction set while keeping them visible and readable by screen readers as disabled controls).

## Known limitation

No live browser was available in this environment — see
`PHASE_7B_BROWSER_ENVIRONMENT_LIMITATION_REPORT.md` for what was and wasn't verified visually.
