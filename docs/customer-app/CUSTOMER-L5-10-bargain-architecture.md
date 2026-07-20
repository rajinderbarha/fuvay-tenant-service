# CUSTOMER-L5-10 — Bargain Architecture

## Real Flow

```
valid estimate (fresh match-and-price call, re-derived on this screen's mount)
→ tier choice (low / mid / high) — a structured, backend-constrained choice, never free text
→ confirm-price-choice (backend resolves + persists the exact amount)
→ confirmed negotiated price (booking_summary.customer_offer)
→ booking-review boundary (dev-only placeholder this sprint, CUSTOMER-L5-11 owns the real screen)
```

There is no eligibility check, no session creation, no counteroffer, no
attempt tracking, and no rate limiting anywhere in this flow — all
confirmed absent from the real backend this sprint researched exhaustively
(contract-matrix.md). This is not an incomplete implementation of a richer
aspirational flow; it is the complete, honest implementation of the real
one.

## Why This Screen Re-Fetches the Estimate Rather Than Receiving It via Route Params

CUSTOMER-L5-09's `PricingEstimateScreen` holds its fetched `price_options`
only in its own local hook state — it was never cached onto the shared
draft object (`pricing-architecture.md`'s explicit design decision). This
sprint's spec (§47) also explicitly forbids passing "the full price
object" through route params. Given both constraints, `BargainScreen`
calls `useCalculatePriceEstimate` (reused directly from
`features/pricing/`) itself, on its own mount — the exact same real
`match-and-price` endpoint, re-derived fresh. This has a real, positive
side effect beyond just working around the two constraints: it guarantees
the tier the customer picks is always chosen against the **current** real
price, never a stale one carried over from the previous screen — a
genuine, if modest, form of the "estimate revision must be current"
requirement (§7), achieved for free by reusing the existing re-derivation
pattern rather than building a new revision-tracking mechanism.

## Why There Is No Separate "Eligibility Check" Step

The spec's aspirational model (§7-9) describes a distinct
eligibility-check stage before bargaining begins. This backend has no such
concept: any draft with a successful `price_snapshot.price_options` (i.e.,
any draft that has already passed through CUSTOMER-L5-09's real
`match-and-price` flow) can call `confirm-price-choice` for any of the
three tiers, unconditionally. This sprint's `evaluatePricingPreflight`
reuse (from `features/pricing/`) already captures every real precondition
that actually gates this flow — there is nothing further to check.

## Why "Choosing a Tier" *Is* the Entire Negotiation (Not a Precursor to One)

Per the decisive finding in `contract-matrix.md` (the `MANUAL_BARGAIN_RULES_ENABLED`
feature flag is off by product decision), there is no second, separate
"negotiation" step beyond the tier pick. Selecting `mid` (the "Expected"
tier) is not "declining to bargain" as distinct from "bargaining down to
`low`" — both are the identical real action (calling `confirm-price-choice`
with a different string), and both are equally real, backend-confirmed
outcomes. This sprint therefore does not offer a separate "skip bargaining"
action distinct from simply choosing a tier — there is no honest way to
distinguish those two product concepts given what this backend actually
implements.

## Why "Change Selection" Doesn't Re-Fetch

`confirm-price-choice` is confirmed safely re-callable with a different
tier (contract-matrix.md's point 4) — no session/attempt state exists to
corrupt by doing so. `changeSelection()` (in `use-bargain.ts`) simply
resets local UI state back to the `choosing` view using the
already-fetched `price_options` still held in the estimate mutation's
memory — no new network call is needed, since the numbers haven't gone
stale within the same screen visit (no TTL exists to expire them, per
CUSTOMER-L5-09's own findings). If the customer wants a genuinely fresh
number (e.g., after a long pause), the existing `refreshEstimate()` action
is available too.

## Draft Fields Written (server-side, this sprint never mutates these directly)

`confirm-price-choice` writes only into `draft.booking_summary` — merged,
not replaced (`selected_tenant_id`, `selected_provider_name`,
`selected_zipcode`, `selected_price_tier`, `customer_offer`,
`allowed_offer_min/max`, `platform_fee_amount`, `payment_mode`).
`draft.status` is confirmed unchanged by this call. This sprint's client
code never attempts to patch the shared draft cache with any of these
fields (unlike L5-08/L5-09's `selected_tenant_id`/`status` patches) —
`booking_summary` was never part of the draft schema `useDraft()` parses,
and no other screen in this app currently reads it, so there is nothing to
synchronize.

## The Real "Booking Review Boundary" Precondition

`build_booking_summary`'s (`/summary`, CUSTOMER-L5-11 scope)
`ready_for_confirmation` flag requires
`booking_summary.selected_price_tier` to already be one of
`"low"|"mid"|"high"`. This sprint's screen only shows its "Continue"
action after a successful `confirm-price-choice` response — the same real
precondition, enforced by UI flow rather than by calling `/summary`
itself (out of this sprint's scope).
