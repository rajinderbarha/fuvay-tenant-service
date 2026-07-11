# FINAL-L5-04B — Entitlement Cache Invalidation Report

## No query-cache library exists in this codebase
Re-confirmed (consistent with FINAL-L5-03's and FINAL-L5-04's findings): no React Query/SWR, no backend Redis-based entitlement cache. Every entitlement read is a live, uncached database query — there is no stale-cache class of bug possible for entitlement reads themselves.

## What "cache invalidation" actually means here: frontend React state refresh
| Requirement | Mechanism | Verified |
|---|---|---|
| 1. Admin Tenant Detail refreshes | `entApi.refetch()` called immediately after every mutation in `EntitlementsTab.tsx` | **Browser-verified** — disable/re-enable show live updated status without reload |
| 2. Tenant navigation refreshes | `EntitlementCtx`'s `loadEntitlements()` — currently only called on mount, not on a live push signal (see gap below) | **Verified via fresh page load**, not via live cross-tab push |
| 3. Tenant route guards refresh | Route guards (the one real one, `enable_service`) query the database live on every request — no caching layer to go stale | Structurally always fresh |
| 4. Customer availability refreshes | N/A — not implemented this sprint (see Customer Category Availability Report) | N/A |
| 5. Staff filters refresh | N/A — not implemented this sprint | N/A |
| 6. Matching uses current entitlement | N/A — not implemented this sprint (see Matching Entitlement Report) | N/A |
| 7. Logout/login does not restore stale access | **Confirmed** — entitlement is never embedded in the JWT; every check is a live DB query on each request, so a fresh login always reflects current state | Structurally true |

## Honest gap: no live push to an already-open tenant portal tab
If an admin disables a tenant's module entitlement while that tenant owner already has the portal open in a browser tab, the tenant's sidebar will **not** update until that tab is reloaded or the user navigates (triggering a fresh `TenantLayout` mount). This was proven in this sprint's E2E test by using a **fresh** browser context/login for the "after disable" check rather than reusing an already-open tab — the fresh-mount case was what got tested, not the already-open-tab case.

## Documentation of the required fields
| Field | Value |
|---|---|
| Query keys | N/A — no query-cache library; `useState`/`useEffect` per component |
| Stale time | N/A — every mount is a fresh fetch |
| Invalidation mechanism | Explicit `refetch()`/`loadEntitlements()` calls after known mutation points (admin UI only) |
| Cross-tab behavior | **Not implemented** — no `BroadcastChannel`/websocket/SSE push exists |
| Failure fallback | `getMyModules()` catch clause fails open (`entitlementsLoaded=true`, `entitledModuleKeys=[]` → `hasAnyModule` defaults to `true` while not-yet-loaded, but **empty and effectively hidden** if the fetch genuinely errors after loading) — verified via code read, not independently fault-injected this sprint |

## Result
No long-lived stale authorization cache exists (every read is live). The one real, honest gap is cross-tab/already-open-session live push, which does not exist — a session must remount (reload/navigate) to see an entitlement change made elsewhere. This is the same class of limitation the mission's own rule 7 ("Logout/login does not restore stale access") is worried about, and that specific case is proven safe; the narrower "live push to an open tab" case is not implemented.
