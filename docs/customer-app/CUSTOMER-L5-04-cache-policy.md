# CUSTOMER-L5-04 — Cache Policy

| Data | staleTime | Query type | Isolation dimensions | Invalidation |
|---|---|---|---|---|
| Category detail | 5 min | `useQuery` | categoryId, locale, tenant | Pull-to-refresh (`refetch()`); natural expiry |
| Category offering list | 5 min per page | `useInfiniteQuery` | categoryId, locale, tenant | Pull-to-refresh refetches page 1 only (React Query default); pagination resets on categoryId/locale/tenant change since those are key segments |
| Service detail | 5 min | `useQuery` | categoryId, serviceId, locale, tenant | Pull-to-refresh; natural expiry |
| Search results | 1 min | `useQuery` | normalizedQuery, categoryId scope, locale, tenant | Superseded automatically when the query text changes (new key); shorter `staleTime` than detail views since catalog search is cheaper to re-fetch and more likely to reflect recent admin edits |
| Recent searches | N/A — not a server-state cache | Local `AsyncStorage` | customerId | Explicit `clearRecentSearches()` call on logout/logout-all |

## Why No Marketplace/Region Dimension

Every real endpoint used this sprint (`/v1/customer/categories/*`,
`/v1/customer/search`) has no marketplace or region concept in its request
or response shape — confirmed by reading `customer_flow/router.py` and
`service.py` directly. Adding a marketplace/region segment to a query key
that never actually varies along that dimension would be a false signal of
isolation, not real isolation — CUSTOMER-L5-03 already established and
documented this same reasoning for Home's category list; this sprint's new
keys extend it consistently rather than reinventing it.

## Cross-Customer / Cross-Tenant Isolation

- **Category/service/search server-state caches** are scoped by
  `(locale, tenant)`, not by customer — these are public catalog reads (the
  backend endpoints in question have no auth dependency at all, confirmed by
  reading `router.py`: `get_current_user_optional` is imported but never
  used by any route function in this engine). A customer switch does not
  need to invalidate these — the data is genuinely marketplace-public, not
  personalized. `queryClient.clear()` on logout (CUSTOMER-L5-02) still wipes
  them anyway, as a blanket safety measure, which is strictly more
  conservative than required but not wrong.
- **Recent searches** are the one genuinely customer-specific cache this
  sprint adds, and are explicitly keyed by `customerId` and explicitly
  cleared on logout/logout-all — see search-architecture.md.

## Offline Behavior (Scoped to This Sprint's Data)

React Query's default behavior — serving cached data immediately while
revalidating in the background, and surfacing `isError` when a foreground
fetch fails with no usable cache — is relied on as-is. No custom offline
indicator was added to category/service/search screens beyond the existing,
already-shared `OfflineBanner` component (used identically to how Home uses
it). Full offline certification remains CUSTOMER-L5-22's scope.
