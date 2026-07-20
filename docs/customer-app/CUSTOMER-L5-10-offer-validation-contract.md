# CUSTOMER-L5-10 — Offer Validation Contract

## There Is No Free-Text/Custom-Amount Offer

The spec's aspirational model (§14-17) describes structured offer input
(quick presets, custom entry, client-side validation of a numeric amount).
**None of this applies to the real backend** — `confirm-price-choice`
accepts exactly one of three literal strings (`"low"|"mid"|"high"`), never
a raw amount (contract-matrix.md). This client's "offer input" is
therefore three fixed, backend-computed amounts presented as tappable
choices — there is no text field, no numeric keyboard, no decimal
precision handling, and no "amount too low/high" client-side validation to
build, because there is no amount for the customer to type.

## Amount Representation

The three real amounts (`low_price`/`mid_price`/`high_price`) come from
the same `ValidatedPriceOptions` schema CUSTOMER-L5-09 already validates
and renders — this sprint reuses that type and that schema verbatim (no
new money-parsing logic). `mid_price` is a real, backend-computed value
(never recomputed client-side, unchanged from L5-09). The amount actually
submitted is not a number at all — it is the tier name string; the
resulting numeric `customer_offer` in the response is always read back
from the backend's own already-computed `price_options`, never trusted
from anything this client sent.

## Hidden-Floor Protection

`allowed_offer_min`/`allowed_offer_max`/`platform_fee_amount` are present
in the real `confirm-price-choice` response (`booking_summary`) but are
parsed-and-never-rendered by this sprint's `bookingSummarySchema`/
`BargainScreen` — identical treatment to CUSTOMER-L5-09's handling of the
same fields in `match-and-price`'s response. Verified by grep: no
reference to `allowed_offer_min`, `allowed_offer_max`, or
`platform_fee_amount` exists anywhere in `BargainScreen.tsx` or any other
rendering code under `features/bargain/`, outside the schema definition
and test fixtures.

## Duplicate Submission Protection

`chooseTier()` sets `selectedTier` and calls the mutation; while
`confirming`, the UI disables all three "Choose" buttons (`disabled={isConfirming}`
on every `TierOption`) — a real, simple duplicate-tap guard. Since
`confirm-price-choice` is confirmed safely re-callable server-side
(overwrite semantics, no attempt/session state to corrupt), a genuine
double-submission (e.g., a race from a very fast double-tap that slips
past the UI disable) would at worst result in the same tier being
confirmed twice with an identical result — not a corrupted or duplicated
financial record, since there is no per-submission record at all, only
the current `booking_summary` state on the draft.

## Validation This Client Performs

None beyond "the tier the customer tapped is one of the three the backend
just returned a real amount for" — which is structurally guaranteed by
construction (`TierOption`'s `tier` prop is always one of `TIER_ORDER`,
itself a `const` array of the exact three real values). There is no
separate client-side range/decimal/currency validation to perform because
there is no free-form input to validate.

## Backend Validation (re-confirmed, not this sprint's code to enforce)

`price_tier` must be one of the three literal strings (422
`INVALID_PRICE_TIER` otherwise — unreachable from this client, since the
UI only ever sends one of the three); `draft.selected_tenant_id` and
`draft.price_snapshot.price_options` must already exist (422
`HOME_BOOKING_NO_PROVIDER_AVAILABLE` otherwise — prevented by this
sprint's own preflight check reaching this screen only after a real
`match-and-price` success).

## Idempotency and Concurrency

Not idempotent in the strict sense (each call appends a new audit event),
but safely repeatable (overwrite semantics) — see
`bargain-architecture.md`'s "Why Change Selection Doesn't Re-Fetch"
section. No idempotency key is sent or needed; the endpoint's own contract
has none.

## Test Coverage

`bargain-schema.test.ts` (5 tests): real success shape, all three real
tier values individually, an unrecognized tier value fails closed, null
optional fields accepted, malformed payload fails closed.
