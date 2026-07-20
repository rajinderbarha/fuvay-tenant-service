# CUSTOMER-L5-12 — Cache Policy

## Query Keys

```
bookingsQueryKeys.list(locale, tenantId)
bookingsQueryKeys.detail(bookingId, locale, tenantId)
bookingsQueryKeys.tracking(bookingId, locale, tenantId)
bookingsQueryKeys.reviewStatus(bookingId, locale, tenantId)
```

All customer-scoped implicitly (the auth token scopes every real query
server-side — this client never passes a customer ID), and locale/tenant
-scoped following the exact convention every prior sprint's query keys
use (`draftQueryKeys`, `bookingQueryKeys` from CUSTOMER-L5-11, etc.).

## Staleness

`staleTime: 0` on every query in this feature — list, detail, tracking,
and review-status all refetch on every mount/focus rather than serving a
potentially-stale cached value silently as current. This matches §42's
"Refresh booking state when: screen opens" requirement without needing
any additional focus-listener code — React Query's own default refetch
-on-mount behavior with `staleTime: 0` already achieves it.

## Pull-to-Refresh

The list screen's `RefreshControl` calls the infinite query's own
`refetch()` (re-fetches all currently-loaded pages, preserving scroll
position). The detail screen does not have an explicit pull-to-refresh
control this sprint (not required by the spec for the detail screen
specifically) — its own `staleTime: 0` refetch-on-mount is the primary
freshness mechanism; the existing `ErrorState`'s retry action re-triggers
a fetch on demand.

## No Background Polling

Per §43's "Determine actual update architecture... Do not add duplicate
real-time systems": since no real-time push/WebSocket/SSE infrastructure
exists (`notification-deep-links.md`), and no bounded-polling requirement
was judged necessary for this sprint's real, currently-terminal-early
status sequence (`pending_assignment → assigned → accepted → scheduled`,
none of which change rapidly in practice), this sprint does not implement
a polling loop. The customer refreshes via pull-to-refresh, re-opening
the screen, or a (currently theoretical, since no push exists) resolved
notification intent.

## Cache Transition on Booking Creation (Cross-Reference)

CUSTOMER-L5-11's `useInvalidateDraftAfterBooking` already invalidates the
draft-detail cache after a successful confirmation — this sprint adds no
further invalidation there, since the newly-created booking is fetched
fresh (not from any stale cache) the first time this feature's own list
or detail screen is opened.

## Logout / Account Switch

No new persistence mechanism was added beyond standard React Query cache
entries — all four query types are discarded by the existing
unconditional `queryClient.clear()` (CUSTOMER-L5-02 pattern) on
logout/account-switch, with no additional clearing logic required.

## No Global Cache Clear

This sprint invalidates nothing beyond its own four query-key families —
no blanket `queryClient.clear()`/`invalidateQueries()` call with no key
filter was added.
