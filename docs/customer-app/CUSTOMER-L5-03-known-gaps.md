# CUSTOMER-L5-03 — Known Gaps (Deepened Pass)

Supplements `known-gaps.md` (cross-sprint) and the first pass's own
CUSTOMER-L5-03 gap items (already listed there: locale hardcoding — now
fixed, see below; no component tests; no analytics; icon mapping;
unused offerings API; disk cache). Only new findings from this pass are
listed here.

## P0

1. **No live runtime certification** — see
   `CUSTOMER-L5-03-runtime-evidence.md`. Identical constraint to
   CUSTOMER-L5-02's own P0 gap. The primary reason this pass's gate is
   PARTIAL.

## P1

2. **Tenant/marketplace binding is architecturally ready but functionally
   inert.** `getRequestTenantId()`/`setRequestTenantId()` are wired
   end-to-end into `home-queries.ts`'s cache key, but nothing in the app
   ever calls `setRequestTenantId()` with a real value — there is no
   tenant-selection or tenant-detection flow. Tenant isolation is
   therefore UNVERIFIED, not proven.
3. **Fixed this pass, but only for `home-queries.ts`'s call site**: the
   `Accept-Language` header defect (see baseline-verification) is fixed at
   the *source* (`i18n-setup.ts`), so it actually fixes every API call
   across the whole app, not just Home's — worth noting since it's a
   cross-cutting fix delivered inside a Home-focused sprint.
4. **`resolveModuleRenderer`/`evaluateModuleVisibility` are exercised only
   by unit tests, never by a rendered `HomeScreen` component test** — the
   wiring inside `HomeScreen.tsx` itself (the `if (recognized) ... else
   CONFIGURATION_INVALID` branch, the `useEffect` logging call) has no
   direct test coverage, only manual code review + TypeScript compilation.

## P2

5. **The critical-module-unavailable page-level error state
   (`criticalModuleUnavailable` in `HomeScreen.tsx`) is currently
   unreachable by real traffic** — Home is already auth-gated before it
   can mount (`route-guards.ts`), so `AUTH_REQUIRED` can never actually
   fire in practice; it exists for architectural completeness and to
   protect the *next* module addition, not because it's exercised today.
6. **No module-level analytics events** (`home_module_viewed`,
   `home_module_failed`, etc.) — same "no vendor authorized" gap as every
   previous sprint, now also applying to the new registry layer
   specifically.
7. **Orphaned locale-scoped cache entries are never proactively evicted**
   on a language change — TanStack Query's normal garbage collection
   (5-minute `gcTime`) handles it eventually, but there's no explicit
   `queryClient.removeQueries({queryKey: ["home","categories"]})` call
   when locale changes. Low impact (bounded memory, short GC window), not
   fixed this pass.
