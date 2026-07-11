# FINAL-L5-04 — Bug Fix Register

## Bug 1: Super-admin dynamic vertical sidebar was fetch-once-on-mount, not live
- **Symptom**: Enabling/disabling a vertical on `/admin/verticals` (or activating/deactivating a category on `/admin/categories`) did not update the sidebar until a hard page reload — the sidebar's `effectiveMenu` state was only ever fetched once, in a mount-only `useEffect`.
- **Root cause**: No mechanism existed for a page to signal `AdminLayout` (its parent shell) to re-fetch `effectiveMenu` after a mutation elsewhere in the tree.
- **Fix**: Added `AdminMenuRefreshCtx` (`createContext<() => void>`) to `AdminLayout.tsx`, exposing the existing `loadEffectiveMenu` callback via `useAdminMenuRefresh()`. Wired into `app/admin/verticals/page.tsx`'s `handleToggle` and `VerticalDetailModal`'s `onToggled`, and `app/admin/categories/page.tsx`'s `activateAction`/`deactivateAction`.
- **Verification**: Real Playwright test, real backend, real Chromium — `SIDEBAR_SHOWS_BEAUTY_AFTER_ENABLE_LIVE: true`, `SIDEBAR_HIDES_BEAUTY_AFTER_DISABLE_LIVE: true`. 0 TS errors, both apps' production builds pass.
- **Risk assessed**: Low — purely additive (new context, new callback invocations at 2 known mutation call sites), no existing behavior removed or altered when the context isn't consumed.

## Bug 2: `Breadcrumbs.tsx` component existed in both apps but was never rendered anywhere
- **Symptom**: No breadcrumb trail appeared on any page in either super-admin or tenant-portal, despite a complete, well-built `Breadcrumbs.tsx` component (real `aria-label="Breadcrumb"` nav, real label resolution via `page-registry.ts`) existing in both apps' `components/layout/` directories.
- **Root cause**: Zero import/render consumers of the component anywhere in either codebase — it was built but never wired into the shell layouts.
- **Fix**: Added `import { Breadcrumbs } from "./Breadcrumbs"` and `<Breadcrumbs/>` to `AdminLayout.tsx` and `TenantLayout.tsx`, placed inside the `<main>` wrapper immediately before `{children}`.
- **Verification**: Real browser checks — `/admin/categories` → "Catalog / Categories"; `/service-jobs` → "Jobs / Service Jobs"; `/jobs` correctly renders nothing (1-crumb registry entry, component's own suppression logic, confirmed by design not by accident). 0 TS errors, both apps' production builds pass.
- **Risk assessed**: Low — self-contained component with no required props, reads its own path via `usePathname()`, degrades to `null` gracefully when no registry match exists.

## Bugs found but NOT fixed this sprint (deliberately deferred — see Remaining Blockers for rationale)
1. `tenant.category_id` is always NULL for every seeded tenant → tenant-side `enabled_engines`/`modules` resolution is permanently empty → no real tenant-entitlement-based nav filtering exists anywhere (frontend or backend). **Deferred**: fixing this touches core tenant data resolution used across the whole tenant portal, not just navigation, and needs dedicated backend verification beyond this sprint's bounded scope to avoid regressing live navigation for every tenant.
2. Sidebar items have no `aria-current="page"` on the active item (accessibility gap, see Navigation Accessibility Report). **Deferred**: real, low-risk fix, just not reached within this sprint's time budget after the two higher-priority fixes above.
3. No responsive/mobile navigation exists at any breakpoint under ~1024px (see Responsive Navigation Report). **Deferred**: a real UI feature addition (off-canvas drawer / hamburger), not a bug fix, and out of scope for a bounded-safe-fix sprint.
4. `/admin/verticals` was wrongly classified as `DISCONNECTED_NO_MENU` in the FINAL-L5-00 inventory (it is actually linked). **Fixed in documentation only this sprint** (corrected in the Disconnected Page Resolution Report) — no code change was needed since the page was never actually disconnected, only mis-classified in an earlier report.

## Result
2 real bugs fixed and browser-verified this sprint. 3 additional real gaps found and honestly deferred with stated rationale, plus 1 stale-documentation error corrected.
