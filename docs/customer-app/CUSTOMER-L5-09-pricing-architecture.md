# CUSTOMER-L5-09 — Pricing Architecture

## Client Architecture

`features/pricing/` follows the exact directory pattern established in
every prior sprint:

```
domain/   pricing-schema.ts        zod schema, fail-closed parse, reuses L5-08's matchedProviderSchema
          pricing-preflight.ts     pure client-side precondition check (no network call)
          pricing-state.ts         centralized state model (§38), pure derivation function
api/      pricing-api.ts           one function, reuses the real match-and-price endpoint
queries/  pricing-queries.ts       useCalculatePriceEstimate mutation
hooks/    use-pricing-estimate.ts  composes draft + preflight + mutation + revision tracking
screens/  PricingEstimateScreen.tsx        the real production screen
          BookingReviewBoundaryPlaceholderScreen.tsx   dev-only next boundary (CUSTOMER-L5-10)
```

## Why "Preflight" Has No Network Call

The spec's own vocabulary (§7, §38) distinguishes a "preflight" stage from
"calculating." This backend has no dedicated preflight endpoint — the real
preconditions (draft not terminal, provider matched, address selected,
serviceable) are all fields already present on the draft object this app's
earlier screens (L5-06/07/08) already fetch and cache. `evaluatePricingPreflight`
is therefore a pure, synchronous function over the already-loaded
`ValidatedBookingDraft` — no extra request, no extra latency, and no risk
of a preflight-says-yes/calculate-says-no race condition since there is no
separate network round trip between the two checks.

## Why Estimate Calculation Reuses `match-and-price` (Not a New Endpoint)

See CUSTOMER-L5-09-pricing-resolution.md for the full architectural
analysis. In short: this backend has no dedicated
`calculate-estimate`/`get-estimate`/`revalidate-estimate` endpoint — the
one real mechanism that produces a genuine Low/Mid/High trio is
`match-and-price`, which CUSTOMER-L5-08 already integrated for its
provider-selection side effect. This sprint calls the exact same endpoint
again, now also parsing the price-options fields L5-08's schema
deliberately excluded. This is not a workaround — it is the real,
intended re-derivation mechanism (confirmed: calling it repeatedly is safe
and is how the backend itself expects a fresh result to be obtained,
per CUSTOMER-L5-08's already-documented Idempotency section).

## Revalidation = Re-Calling the Same Mutation

Since there is no revalidate-specific endpoint and no price-specific TTL
(contract-matrix.md), "revalidation" in this sprint is implemented as:
calling `useCalculatePriceEstimate`'s `mutate(draftId)` again. This
happens in two ways:

1. **Automatically on screen mount** (`usePricingEstimate`'s
   auto-trigger-once effect, mirroring `ServiceabilityScreen`/
   `ProviderPreviewScreen`'s established pattern) — every fresh visit to
   this screen gets a fresh calculation, never a stale cached amount from
   a previous mount.
2. **Explicitly via the "Refresh estimate" action** — a real, visible
   control that re-runs the exact same real call, letting the customer
   force a revalidation at will (useful if they suspect their context has
   changed, e.g., after backgrounding the app for a while).

## Revision Detection Is a Client-Side Convenience, Not a Backend Guarantee

`usePricingEstimate` keeps the previously-successful `price_options` in a
`useRef` and compares it (via `priceOptionsEqual`, an exact field-by-field
comparison — no floating-point tolerance games, since these are the exact
numbers the backend returned) against each new result. When they differ,
the screen shows a "this estimate has changed" banner. This is entirely a
client-side inference — the backend itself has no revision counter and
performs no diffing (contract-matrix.md) — so this sprint is explicit
(in-code comment and this doc) that "revised" is derived, not
backend-asserted.

## Draft Cache Synchronization

`useCalculatePriceEstimate`'s `onSuccess` patches the existing
`draftQueryKeys.detail(...)` cache entry (`status`, `selected_tenant_id`,
`provider_match_status`) — the exact same fields L5-08's `useMatchProvider`
already patches, since both mutations call the same endpoint and get the
same `draft_status`/`selected_provider` shape back. This sprint does not
additionally cache `price_snapshot`/price fields onto the draft object
client-side — the pricing screen's own `usePricingEstimate` hook is the
single source of truth for displayed price data during the session; there
is no need to duplicate it into the shared draft cache since no other
screen in this app reads price fields from the draft yet.

## No Client-Side Median/Floor/Fee Calculation

`mid_price` is rendered exactly as returned — never recomputed via
`(low + high) / 2` client-side, even though that arithmetic would produce
the same visible number today (matching_engine.py's own formula does
exactly that, server-side, with a real rounding step this client does not
attempt to replicate). `allowed_offer_min`/`allowed_offer_max`/
`platform_fee_percent`/`platform_fee_amount` are parsed (so a real
response is not rejected) but never rendered or used in any arithmetic —
verified by grep: no file under `features/pricing/` performs `+`, `-`,
`*`, or `/` on any parsed money field.
