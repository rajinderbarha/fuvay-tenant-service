# FINAL-L5-03 — Query, Cache and Server-State Standard

## Canonical system: `useApi`/`useAction` (no external query library)
Confirmed (originally established in FINAL-L5-01E's investigation, re-confirmed this sprint across all 3 apps): there is no React Query/SWR/Apollo — each app has its own `hooks/useApi.ts` with the same shape:
```ts
useApi<T>(fetcher: () => Promise<T>, deps: unknown[]) -> { data, loading, error, requestId, refetch }
useAction<T>(fn: (...) => Promise<T>) -> { execute, loading, error, requestId }
```
A `useRef(0)` request-id counter guards against stale-response races **within one hook instance**, not across independent instances (this was the exact mechanism behind the FINAL-L5-01E duplicate-`useStaffContext()` bug, now fixed).

## Mapped against the mission's suggested model
| Mission concept | Actual implementation |
|---|---|
| Query keys (`["tenant", tenantId, "jobs", filters]`) | Not literal string-array keys — each `useApi(fetcher, deps)` call's `deps` array serves the same "when to refetch" role, scoped to that one component instance |
| Cache invalidation | No cross-component cache exists to invalidate — "invalidation" is calling `.refetch()` on the specific hook instances that need fresh data after a mutation (e.g. `TenantLayout`'s `SetupWizardDrawer` refetch button calls `statusApi.refetch(); pkgApi.refetch(); creditApi.refetch(); ...` explicitly) |
| Mutation refetching | Same explicit-refetch pattern, confirmed present at every mutation site checked this sprint |
| Stale time / background refresh | Not implemented — every `useApi` call fetches once on mount, no automatic revalidation |
| Pagination | Handled per-page via explicit `limit`/`offset`/`page` params, not a shared pagination-aware query hook |
| Optimistic updates | Not found anywhere in this sprint's scan — all mutations wait for the real response before updating UI state (safer default, consistent with rule "optimistic updates only where safe" by simply not doing them where not proven safe) |

## Critical invalidations verified this sprint (real, not assumed)
- **Job completion → job detail + jobs list + usage-credit balance**: verified via the canonical seed's `Completed Job Deduction` ledger entry (`L501-JOB-0004`) and `TenantLayout`'s now-fixed `creditApi` correctly reflecting the real `usage_credit_balance` after the fix (previously this specific invalidation was moot because the wallet call was permanently broken — see Performance Code Cleanup Report).
- **Settings update → current profile/context**: not independently re-tested this sprint (out of the two bugs this sprint targeted).

## Decision: keep the existing pattern, don't introduce a query library
Per rule 1 ("do not rewrite the entire project without evidence") and the scale of a query-library migration (would touch every `useApi` call site across 3 apps — hundreds of components), this sprint documents the existing pattern as canonical rather than replacing it. The pattern's real weakness (duplicate-instance races, as found and fixed in FINAL-L5-01E and again implicitly avoided in this sprint's `TenantLayout` fix by using a single `creditApi` instance) is a known, documented risk class — not a reason to rewrite the whole data layer without a dedicated, separately-scoped migration sprint.

## Result
Documented and standardized as-is; real invalidation bug (dormant wallet call) fixed.
