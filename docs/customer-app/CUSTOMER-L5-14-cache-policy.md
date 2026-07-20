# CUSTOMER-L5-14 — Cache Policy

Consistent with every previous sprint: `staleTime: 0` + refetch-on-mount
everywhere, no polling loop.

## Query keys (`quote-queries.ts`)

- `["quoteDecision", "jobQuotes", jobId, locale, tenantId]` —
  `useJobQuotes`.
- `["quoteDecision", "detail", quoteId, locale, tenantId]` —
  `useQuoteDetail`.

## Invalidation on decision success (`useInvalidateAfterDecision`)

After approve/reject/request-revision succeeds:

1. `["quoteDecision", "jobQuotes", jobId]` — this job's quote list
   (prefix match, locale/tenant-agnostic).
2. `["quoteDecision", "detail"]` — every cached quote detail (broad,
   deliberately not scoped to one `quoteId`: cheap to over-invalidate a
   handful of quote-detail entries, and a customer could in principle
   have more than one job's quotes cached in the same session).
3. `["booking", "detail"]` — `booking-confirmation`'s cache (used by
   this screen's own `job.id` resolution and by `BookingReview`/
   `BookingSuccess`).
4. `["bookings", "detail"]` and `["bookings", "tracking"]` — the
   *separate* `features/bookings` cache used by
   `BookingDetailScreen`/`BookingsListScreen`, so the status label a
   customer sees immediately after navigating back is fresh, not stale.

## Why the mutation's own response is not cached/parsed as the new quote state

`useApproveQuote` deliberately does not parse or store the raw approve
response (see the doc comment in `quote-queries.ts`) — the invalidated
`useQuoteDetail` refetch is the single source of truth for the resulting
shape, avoiding two divergent parse paths (approve response vs. detail
response) for what should always be the same server record.

## What is NOT cached

`GET /customer/quotes/{quote_id}/events` (the audit trail) — not queried
at all this sprint; see `known-gaps.md`.
