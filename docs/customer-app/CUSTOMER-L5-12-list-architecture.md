# CUSTOMER-L5-12 — List Architecture

## Real Endpoint

`GET /v1/customer/bookings` (`home_service_assignment/customer_router.py`)
— chosen over the alternative `GET /v1/customer/my-activity/bookings`
(`final_records`, used by CUSTOMER-L5-11's own narrow post-confirmation
fetch) because it is already customer-safe server-side and is the sibling
of the real detail/tracking endpoints this sprint also uses (one coherent
router, not three disparate ones). See baseline-verification.md's Central
Findings and contract-matrix.md.

## Real, Disclosed Limitation: No Server-Side Status/Date/Search Filter

`list_bookings` accepts only `page`/`page_size` — confirmed by direct
reading and by an independent research pass, both reaching the same
conclusion. Per §14's explicit instruction ("Do not filter only the
currently loaded page") this is a genuine tension: the real backend gives
this client no way to request "just my active bookings" or "just my past
bookings" from the server. This sprint resolves the tension as follows:

1. **Real pagination is used as-is** (`useInfiniteQuery`, `page`/`page_size`,
   `mayHaveMore` inferred honestly from a full page — never a fabricated
   `total`).
2. **The Active/Past segmented control filters client-side** over
   whatever pages have been loaded so far via `groupForStatus()`
   (the same centralized status registry the detail screen uses — never
   a separate, duplicated grouping guess).
3. **This does not fetch the customer's entire booking history at once**
   (§59's "no full-history load if paginated" takes precedence over
   §14's filter-scope guidance when the two conflict, since unbounded
   fetching is the more universally harmful failure mode) — each tab
   continues to page forward through the same real, shared infinite list
   as the customer scrolls, rather than eagerly loading everything.
4. **Documented honestly as a known, disclosed backend limitation** in
   `known-gaps.md`, not silently presented as if server-side filtering
   were happening.

## Search / Sort — Not Implemented (Confirmed Absent)

No search or sort parameter exists on this endpoint (confirmed
exhaustively by both this sprint's own research and an independent
background pass). Per §16's explicit instruction ("If unsupported, do not
fake search"), no search UI was built.

## Pagination Details

- Query key: `bookingsQueryKeys.list(locale, tenantId)` — customer scope
  comes from the auth token server-side; locale/tenant scoping follows
  the same convention every prior sprint's query keys use.
- `getNextPageParam` returns `undefined` (stopping pagination) the moment
  a page returns fewer than `PAGE_SIZE` items — an honest inference from
  the real data, not a fabricated end-of-list signal.
- Pull-to-refresh (`RefreshControl`) calls the infinite query's own
  `refetch()`, which by React Query's default behavior re-fetches all
  currently-loaded pages (not just the first) — preserving scroll
  position and previously-loaded items rather than resetting to page 1
  only.

## No Duplicate Rows

`keyExtractor` uses the real, stable `booking_id` — React Query's
infinite-query page cache naturally prevents the same booking from being
requested twice across pages (real backend pagination via `offset`, which
that config indirectly derives from `page`/`page_size`, cannot itself
produce duplicate rows across sequential pages absent a data mutation
between requests).

## Test Coverage

`booking-list-schema.test.ts` (5 tests) and `booking-group.test.ts`
(3 tests) cover the real page shape, item-level resilience (dropping
invalid rows), the honest `mayHaveMore` inference, and the centralized
status-to-group mapping the Active/Past filter relies on.
