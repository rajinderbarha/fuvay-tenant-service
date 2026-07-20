# CUSTOMER-L5-04 — Search Architecture

## Structure

```
features/search/
  api/search-api.ts              — GET /v1/customer/search client
  domain/search-schema.ts        — zod validation + per-item resilience (drops invalid rows)
  domain/query-normalization.ts  — trim/collapse/strip-control-chars/max-length, safe analytics buckets
  hooks/use-debounced-value.ts   — generic debounce
  hooks/use-recent-searches.ts   — customer-scoped local history
  state/recent-search-storage.ts — AsyncStorage, keyed per customerId
  queries/search-queries.ts      — single-shot (not infinite) React Query hook
  components/SearchCategoryResult.tsx, SearchServiceResult.tsx
  screens/SearchScreen.tsx
```

## Input Lifecycle

1. Raw keystrokes update `rawQuery` state immediately (input stays responsive).
2. `useDebouncedValue(rawQuery, 350ms)` delays the value used for search.
3. `normalizeSearchQuery()` trims, collapses whitespace, strips control
   characters, caps length at 100 chars, and preserves all other Unicode
   (Hindi/Punjabi search terms work exactly like English ones).
4. `isSearchableQuery()` requires at least 2 characters before any request
   fires — below that, the screen shows a hint instead of querying.
5. React Query's `enabled` flag (driven by `searchable`) is the cancellation
   mechanism: changing `normalized` before a request settles changes the
   query key, and React Query aborts the superseded `queryFn` via the
   `signal` it passes in — `search-api.ts` forwards that signal straight
   into `apiClient.get`'s own `AbortController` wiring. No hand-rolled
   cancellation logic was needed.

## Why There Is No Pagination

The real endpoint accepts `page`/`page_size` but does not use them
meaningfully: categories are hard-capped at 5 regardless of page
(`.limit(5)`, no offset), and offerings use `.limit(page_size)` with **no**
`.offset()` — a second page would return the exact same rows as the first.
Implementing "load more" here would either silently duplicate results or
require inventing client-side pagination logic the backend cannot actually
serve. `useSearchResults` is therefore a plain `useQuery`, not
`useInfiniteQuery` — this is a deliberate, documented scope decision, not an
oversight (see contract-matrix.md).

## Result Types

Only `CATEGORY` and `SERVICE` exist in the real response — no
`SERVICE_GROUP`/`PROMOTION` types are returned by this endpoint, so none are
implemented. Category results are always fully navigable
(`SearchCategoryResult` → `CategoryDetailScreen`). Service results from an
unscoped (global) search cannot be safely deep-linked to detail — see
known-gaps.md — and `SearchServiceResult` renders them as informational,
non-interactive cards with an explanatory hint rather than a broken or
guessed navigation target.

## Recent Searches (Local Only)

No backend search-history endpoint exists. `recent-search-storage.ts` keeps
up to 10 terms per `customerId` in `AsyncStorage`
(`serviceos.pref.recentSearches.v1:<customerId>`), most-recent-first,
de-duplicated case-insensitively. Cleared on both `logout` and `logoutAll`
(alongside the existing `queryClient.clear()` from CUSTOMER-L5-02) so no
customer's search history survives an account switch on a shared device.

## Privacy

- Raw query text is never logged — `logger.warn`/`info` calls around search
  only ever pass `queryLengthBucket`/`resultCountBucket`, never the string
  itself.
- Recent searches are stored in plain (non-secure) `AsyncStorage`, matching
  the app's existing "non-sensitive preference" tier — search terms are not
  credentials — but are still customer-scoped and cleared on logout, unlike
  a true shared preference.
- No suggestion/popular-search fabrication — an absent feature is shown as
  absent (no recent searches → section hidden; no popular searches → not
  rendered at all), never backfilled with static or invented data.

## Cache Policy

`staleTime: 60_000` for search results — shorter than category/service
detail's `5 * 60_000`, since search results are more likely to reflect
fast-changing catalog edits and are cheaper to re-fetch than a full detail
page. Recent searches are not a React Query cache at all (they are local
device state, not server state) and are therefore unaffected by
`queryClient.clear()` directly — they are cleared by an explicit call to
`clearRecentSearches()` alongside it.
