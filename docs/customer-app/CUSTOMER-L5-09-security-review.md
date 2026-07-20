# CUSTOMER-L5-09 — Security Review

## Ownership Enforcement

`match_provider_and_price`'s draft lookup (`self._require_draft(draft_id,
customer_id)`, `service.py:648`) enforces draft ownership before any price
computation runs — unchanged pattern from every prior sprint. This client
sends only the path's `draftId` (no provider ID, no price-rule ID, no
tenant ID, no raw amount) — there is no client-constructible input this
sprint adds that could probe another customer's or tenant's pricing data.

## No Internal Fee/Margin/Floor Data Ever Reaches the Client's Rendered UI

`priceOptionsSchema` accepts `allowed_offer_min`/`allowed_offer_max`/
`platform_fee_percent`/`platform_fee_amount` (they arrive in the same flat
object as the customer-visible amounts — unlike L5-08's schema, which
excluded the whole price-options object entirely) but this sprint's UI
code never reads or renders any of these four fields — verified by grep:
no reference to `allowed_offer_min`, `allowed_offer_max`,
`platform_fee_percent`, or `platform_fee_amount` exists anywhere in
`PricingEstimateScreen.tsx` or any other file under `features/pricing/`
outside the schema definition itself. `internal_score`/
`internal_score_breakdown`/`selected_provider_admin`/`bargain_floor`
remain structurally impossible to receive at all (never returned to the
customer router, unchanged from L5-08).

## No Sensitive Logging

`pricing_calculation_started`/`pricing_calculation_succeeded`/
`pricing_calculation_failed`/`pricing_calculation_error`/
`pricing_continue_selected` log calls pass only booleans, currency codes,
and reason-key strings — never the actual low/mid/high amounts, never the
platform fee, never the provider name. Verified by direct review of every
`logger.*` call site added this sprint.

## No Production Mocks

Grepped `features/pricing/` for `mock`, `fake`, `TODO`, `FIXME` — none
found. Every rendered amount traces to a real, schema-validated
`match-and-price` response; `mid_price` is never recomputed client-side
(pricing-architecture.md).

## No Client-Submitted Price Values

This sprint never sends a price, a price tier, or any pricing-rule
identifier to the backend — the only outbound call
(`pricingApi.getEstimate`) is a bare `POST` with no body beyond the path's
`draftId`, identical to L5-08's `match-and-price` call. `confirm-price-choice`
(the one real endpoint that accepts a customer-chosen tier) is not called
by this sprint at all — enforced by the fact that no code path in
`features/pricing/` references that route.

## Cross-Tenant/Cross-Customer Isolation

Relies entirely on the backend's own draft-ownership check (above). This
sprint adds no new client-side authorization logic to bypass or get
wrong, and no new local persistence surface (cache-policy.md) requiring
its own clearing logic beyond the existing unconditional
`queryClient.clear()` on logout/account-switch.

## Bargain-Eligibility Non-Claim (a security-adjacent honesty finding)

Per pricing-semantics.md's Bargain Eligibility section, this sprint
deliberately displays no "bargaining allowed"/"fixed price" claim, because
no backend-authoritative signal exists to make that claim safely. Asserting
an unverified eligibility state would itself be a category of
information-integrity risk (misleading the customer about a real product
capability) — the safe choice here was to say nothing rather than guess.

## Currency Trust

`currency` is rendered exactly as the backend returns it (currently always
`"INR"`, see contract-matrix.md) via the existing, already-audited
`formatCurrency` utility — this sprint does not add any new currency
parsing, symbol concatenation, or locale-detection logic of its own.
