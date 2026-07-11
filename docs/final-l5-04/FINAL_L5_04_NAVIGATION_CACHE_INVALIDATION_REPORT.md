# FINAL-L5-04 — Navigation Cache Invalidation Report

## Real architecture
No query-cache library (React Query, SWR, etc.) exists anywhere in this codebase (re-confirmed, consistent with FINAL-L5-03's finding). All navigation-relevant data (`effectiveMenu` for verticals, `permissions` for admin gating) is plain component-local state (`useState`) fetched via `useEffect`/callback on mount, with no shared cache layer to invalidate.

## What this sprint fixed
Before this sprint, `effectiveMenu` in `AdminLayout.tsx` was fetched exactly once, on mount — any change to vertical/category enablement made elsewhere in the same session (e.g., toggling a vertical on `/admin/verticals`) was invisible in the sidebar until a hard page reload. This is a real cache-invalidation-shaped bug (stale client state, no invalidation signal).

**Fix**: introduced `AdminMenuRefreshCtx`, a plain `createContext<() => void>` exposing the same `loadEffectiveMenu` callback used on mount, consumed via `useAdminMenuRefresh()` in `/admin/verticals` and `/admin/categories` pages, called immediately after any mutating action (enable/disable vertical, activate/deactivate category) succeeds. This is a manual, explicit "refetch on known mutation" pattern — not a general cache-invalidation system, but a correct, verified fix for the two real mutation points that affect the sidebar.

**Browser-verified**: toggling a vertical's enabled state on `/admin/verticals` updates the sidebar's vertical sections live, in the same session, with zero page reload (`SIDEBAR_SHOWS_BEAUTY_AFTER_ENABLE_LIVE: true`, `SIDEBAR_HIDES_BEAUTY_AFTER_DISABLE_LIVE: true` — from this sprint's Playwright run).

## Real remaining gap
This fix only covers the two pages that directly mutate vertical/category state. If any *other* code path mutates the same backend state (e.g., a future bulk-import tool, or a different admin page), the sidebar will go stale again unless that path is also wired to call `useAdminMenuRefresh()`. There is no automatic, registry-driven invalidation (e.g., an event bus or a shared cache key) that would make this systemic rather than per-call-site. This is an intentional, honestly-scoped fix — not a general solution — appropriate to the bounded-safe-fix approach used this sprint.

## No stale-permission-cache risk found
`usePermissions()` fetches from `authApi.me()` fresh per-mount per page (no cross-page cache), so permission changes take effect on next navigation without any stale-cache risk — this was already correct before this sprint.

## Result
One real stale-cache bug found and fixed for the two mutation points that affect it, browser-verified live; the fix is call-site-scoped rather than systemic, which is documented honestly as a real limit rather than a general "cache invalidation is solved" claim.
