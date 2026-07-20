# CUSTOMER-L5-13 — Cache Policy

## Query Keys

```
serviceTrackingQueryKeys.timeline(jobId, locale, tenantId)
```

Plus the reused `bookingQueryKeys.detail(bookingId, locale, tenantId)`
from CUSTOMER-L5-11 (job-ID resolution). Both customer-scoped implicitly
(auth token) and locale/tenant-scoped following the established
convention.

## Staleness

`staleTime: 0` — refetches on every mount, matching every real-data
screen since CUSTOMER-L5-09. Since there is no live session/location
stream to manage (`tracking-architecture.md`), this is the entire
freshness strategy — no additional background-refresh or reconnect logic
was needed.

## No Location-Specific Retention Policy Needed

Per §40's requested "precise location" cache policy: not applicable —
this sprint never receives or caches any coordinate data
(`location-event-contract.md`).

## Logout / Account Switch

No new persistence mechanism was added beyond standard React Query cache
entries — discarded by the existing unconditional `queryClient.clear()`
(CUSTOMER-L5-02 pattern) on logout/account-switch, with no additional
clearing logic required.

## No Global Cache Clear

This sprint invalidates nothing beyond its own one query-key family — no
blanket `queryClient.clear()`/`invalidateQueries()` call with no key
filter was added.
