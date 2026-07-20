# CUSTOMER-L5-09 — Baseline Verification

## Previous Sprint Verification

| Sprint | Claimed status | Verified status | Notes |
|---|---|---|---|
| CUSTOMER-L5-00 through L5-08 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | No regressions; 526 tests passing at sprint start. |

1. Authentication: confirmed working, unmodified since L5-02.
2. Current customer loads: confirmed.
3. Real booking draft exists: confirmed (`HomeServiceBookingDraft`).
4. Draft restoration: confirmed working.
5. Draft versioning: **confirmed absent** — unchanged finding since L5-06; there is still no `version`/`revision` counter on the draft row itself. Price-specific staleness must therefore be detected by comparing field values (see pricing-resolution.md), not a version number.
6. Selected service canonical: confirmed (`MasterService`-space IDs).
7. Service type canonical: confirmed (`offering_type_id`).
8. Brand and option answers canonical: brand confirmed (`brand_id`); option IDs still **not** synced to the draft (unchanged L5-06/L5-08 finding).
9. Quantity/unit answers: **confirmed not part of this flow at all** — no quantity/unit field exists anywhere on `HomeServiceBookingDraft`, `MasterService`, or `BargainRule`. Per-unit/per-item pricing models are not used by this vertical's real data (see pricing-semantics.md).
10. Address valid: confirmed (L5-07, real `CustomerAddress`).
11. Serviceability confirmed: confirmed (L5-07, real `HomeServiceServiceabilityService`).
12. Zone and city tier canonical: **re-verified, now with a major new finding** — a real, working city-tier engine exists (`app.engines.pricing.models.CityTierConfig`) and is used by a real endpoint (`POST /{draftId}/price-estimate` → `resolve_price_estimate`), but this endpoint is **architecturally separate from and never called by** the provider-matched Low/Mid/High flow (`match-and-price`/`confirm-price-choice`) this sprint builds on. See contract-matrix.md and pricing-resolution.md for the full analysis — this is this sprint's most consequential finding, in the same category as L5-07's "no real SLA engine" and L5-08's "no candidate list."
13. Selected SLA valid: **still not applicable** — unchanged from L5-07, only a free-text `preferred_time_window` exists; no SLA pricing modifier exists anywhere in the code this sprint verified.
14. Provider match valid where pricing requires it: confirmed — `match_provider_and_price` requires a resolved match (raises `HOME_BOOKING_NO_PROVIDER_AVAILABLE` otherwise) before it will compute any price.
15. Selected Tenant/provider canonical: confirmed (`draft.selected_tenant_id`, written by L5-08's flow).
16. Matching result not expired: confirmed no expiry field exists — re-running `match-and-price` always re-derives fresh (unchanged L5-08 finding); "staleness" for this sprint means "has the customer's context changed since the last call," not a TTL.
17. Pricing engine endpoints identified: **two real, independent endpoints found** — `POST /{draftId}/price-estimate` (catalog + city-tier, NOT used by this sprint's real flow) and `POST /{draftId}/match-and-price` (provider-matched Low/Mid/High, the flow this sprint uses — already partially wired by L5-08, which deliberately never parsed the price fields).
18. Pricing rule models identified: `BargainRule` (customer-facing range + fee) and `ServicePricingRule` (admin range, linked via `pricing_rule_id`) — both real, read in full this sprint.
19. Catalogue pricing models identified: `MasterService.pricing_model/base_price/min_price/max_price/visit_fee` — real, but only consumed by the separate `/price-estimate` flow, not by `match-and-price`.
20. Tenant pricing models identified: `BargainRule.customer_min_price/customer_max_price` (per `master_service_id`, optionally scoped further by `service_type_id`/`brand_id` via the linked `ServicePricingRule`) is the real Tenant/provider-facing pricing input to `match-and-price`.
21. Zone overrides identified: **confirmed not used anywhere in the real Low/Mid/High computation** — `compute_price_tiers` reads only `BargainRule`/`ServicePricingRule` fields, never a zone table.
22. City-tier minimum/maximum rules identified: real (`CityTierConfig.floor_price`/`tier`), but — per finding #12 — only reachable via the separate `/price-estimate` endpoint this sprint's real flow does not call.
23. Currency and tax behavior identified: currency is **hardcoded to `"INR"`** in both real pricing code paths (`compute_price_tiers`'s default parameter, never overridden by its only real caller; `_compute_price_snapshot`'s literal `"currency": "INR"`) — no live multi-currency support exists despite the response schema carrying a `currency` field. No tax field exists anywhere in either response.
24. Bargain configuration identified (without implementing bargaining): `BargainRule.bargain_enabled` is a real column, but **confirmed never read anywhere in `match_provider_and_price`/`compute_price_tiers`/`confirm_price_choice`** — a real, disclosable inconsistency (a rule with `bargain_enabled=False` still produces a full price range through this flow). No `bargain_enabled`-equivalent field is ever returned to the customer. See known-gaps.md.
25. No fake prices in production paths: confirmed — `features/provider-matching/` (L5-08) never rendered any price field; this sprint is the first to touch pricing display.
26. No client-side pricing calculation controls behavior: confirmed — this sprint's design renders `low_price`/`mid_price`/`high_price` exactly as returned; `mid_price` is a real, backend-computed value (`compute_symmetric_customer_price_tiers`'s `round_to_nearest(10, (Low+High)/2)`), never recomputed client-side.
27. Existing tests pass: confirmed — 526/526 at sprint start.
28. Working tree: understood — unrelated parallel work in other engines/frontends, none touched.
29. No unrelated changes overwritten: confirmed.

## Existing Pricing Implementation Found

- **Low/Mid/High display**: none in the mobile app before this sprint. `features/provider-matching/domain/provider-match-schema.ts`'s `providerMatchResultSchema` structurally strips `selected_provider_price_options`/`area_market_comparison` via `z.object()`'s default unknown-key stripping (an explicit, documented L5-08 scope boundary — this sprint is where that boundary opens).
- **Currency formatting utility**: confirmed exists and already used elsewhere in the app for `category.startingFrom`/service pricing display (`formatCurrency`, used by `ServiceDetailScreen`) — this sprint reuses it rather than building a new one.
- **Price explanation, revalidation, revision handling**: none exist anywhere in the mobile app.
- **Bargain-eligibility display**: none exists; see finding #24 above for why this sprint cannot safely display one.
- **Placeholder/fake behavior found**: none — `PricingBoundaryPlaceholderScreen.tsx` is an honest, clearly-labeled dev-only boundary screen (not fake production data), which this sprint replaces with the real screen.

## Real Backend Contract — Central Findings

1. **Two independent, non-composed pricing mechanisms exist in this backend.** `/price-estimate` (catalog + real city-tier floor, single `base_price`/`min_price`/`max_price`, no provider dependency, sets `draft.status = "price_estimated"`) and `/match-and-price` (provider-matched real Low/Mid/High from `BargainRule`, no city-tier/zone input at all, sets `draft.status = "provider_matched"`). Both write into the same `draft.price_snapshot` JSON column via a shallow merge (`{**(price_snapshot or {}), ...}`), so calling both would leave both sets of fields coexisting in the same object — but neither endpoint reads the other's output.
2. **This sprint uses `/match-and-price` as the canonical Low/Mid/High source**, for three concrete reasons: (a) the product context (§1 of the spec) states the customer already has a provider match before this stage — `/price-estimate` has no provider dependency and architecturally precedes matching, not follows it; (b) only `/match-and-price` produces a genuine three-value Low/Mid/High trio — `/price-estimate` produces one `base_price` plus catalog min/max bounds, not a marketed range; (c) L5-08 already integrated `/match-and-price` into the real navigation flow (`ServiceabilityScreen` → `ProviderPreview` → this sprint's screen) — `/price-estimate` is not on that path today.
3. **Consequence, stated plainly**: this sprint's real Low/Mid/High has **no real city-tier or zone influence**, because the endpoint it correctly uses for the reasons above does not use either input. §22's "real city-tier influence" requirement is fulfilled by documenting the real, separate `/price-estimate` endpoint's genuine city-tier usage (pricing-resolution.md), not by fabricating city-tier involvement in a flow that verifiably has none.
4. **`mid_price` is real and backend-computed** — `compute_symmetric_customer_price_tiers`: `Low = provider_min*(1+fee%) + fee_fixed`, `High = provider_max*(1+fee%) + fee_fixed`, `Mid = round_to_nearest(10, (Low+High)/2)`. This client renders it verbatim; it is never recomputed client-side.
5. **`confirm_price_choice` (the tier-pick — low/mid/high) is the platform's only real "negotiation" mechanism** — it accepts a tier name only, never a raw customer-submitted amount. A separate, more general `evaluate_customer_bargain(customer_offer=...)` function exists in `bargain_engine.py` but is confirmed dead code in this flow (never called with a real `customer_offer` anywhere in `home_service_booking/`). This sprint does not call `confirm_price_choice` at all — that belongs to CUSTOMER-L5-10 per this sprint's explicit exclusion of "bargain offer submission... bargain acceptance."
6. **No estimate-specific expiry/TTL field exists.** The general draft `expires_at` is the only expiry concept; there is no separate price validity window. Re-calling `match-and-price` always re-derives fresh — "revalidation" in this sprint means "call it again," not "check a TTL."
7. **Currency is hardcoded to INR** in both real pricing code paths — documented as a real, disclosed limitation, not fabricated multi-currency support.

## Blockers

None preventing implementation of an honestly-scoped sprint.

## Corrections Completed

None to prior sprints' code (L5-08's `ProviderPreviewScreen`'s "Continue" target is updated this sprint from the dev-only `Pricing` placeholder to the real pricing screen — an expected, planned boundary promotion, not a correction of a defect).

## Deferred Issues

See `CUSTOMER-L5-09-known-gaps.md`.
