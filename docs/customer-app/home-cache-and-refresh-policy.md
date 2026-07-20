# Customer App — Home Cache and Refresh Policy

## Current Policy (this sprint)

Categories use TanStack Query's in-memory cache only (`staleTime: 5min`,
CUSTOMER-L5-00's default `gcTime: 5min`) — **no disk persistence**. Killing
the app clears the cache; the next Home mount refetches.

## Refresh Triggers Implemented

- First mount (query runs on mount, per TanStack Query defaults).
- Pull-to-refresh (`ScreenContainer`'s `onRefresh` → `categories.refetch()`).

## Refresh Triggers Not Implemented

- App resume after interval — TanStack Query's `refetchOnReconnect: true`
  (CUSTOMER-L5-00 default) covers network-reconnect, but there's no
  app-resume-after-N-minutes refresh specific to Home (only
  `startup-service.ts`'s own resume re-evaluation, which doesn't touch
  Home's query).
- Locale change invalidation — the query key includes `locale`, so a locale
  change would naturally produce a cache miss (a different query key) once
  locale is actually threaded through (see `known-gaps.md` — currently
  hardcoded to `"en"`).
- Region/marketplace change invalidation — not applicable; no such
  dimension exists in this backend's contract.
- Logout-time clearing — not implemented (see CUSTOMER-L5-02
  `known-gaps.md` item 25, which already flags this generally).

## Why No Disk Cache This Sprint

CUSTOMER-L5-01 established a disk-cache pattern for remote config
(`remote-config-cache.ts`) with environment/marketplace binding, corruption
recovery, and max-age rules. Home's category data does not yet warrant
that machinery — it's public-ish catalogue data (not customer-specific),
low-value to cache across app restarts compared to the complexity of
building and testing another cache-binding layer, and the category count is
small enough that a cold refetch is fast. If a later sprint's offline
requirements demand it, the same `preferenceStorage`-based pattern from
`remote-config-cache.ts` should be reused rather than inventing a new one.
