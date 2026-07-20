# CUSTOMER-L5-09 — Pricing Resolution

## Two Independent Pricing Mechanisms (the sprint's central finding)

This backend contains **two architecturally separate, non-composed**
pricing computations inside the same `home_service_booking` engine:

### (a) `POST /{draftId}/price-estimate` → `resolve_price_estimate` → `_compute_price_snapshot`

```
MasterService.pricing_model / base_price / min_price / max_price / visit_fee
        ↓
max(offering_price, CityTierConfig.floor_price for this city+category)
        ↓
{ pricing_model, visit_fee, base_price, min_price, max_price,
  currency: "INR", city_tier, note, display_price, source: "backend_catalog" }
```

- Real city-tier engine: `CityTierConfig` (`app/engines/pricing/models.py`),
  columns include `city_name, tier, service_category, service_name,
  floor_price, min_price, max_price, default_estimate, visit_fee,
  bargain_floor, provider_override_allowed, currency, is_active`.
- No provider/tenant dependency at all — computable the moment a service
  and city are known, independent of provider matching.
- Sets `draft.status = "price_estimated"`, `draft.price_status = "estimated"`.
- Produces one `base_price` plus catalog `min_price`/`max_price` bounds —
  not a marketed Low/Mid/High trio.

### (b) `POST /{draftId}/match-and-price` → `match_provider_and_price` → `compute_price_tiers`

```
select_best_provider() → matched Tenant
        ↓
BargainRule (most specific match: service+type+brand > service+type > service-only)
        ↓
compute_symmetric_customer_price_tiers(customer_min_price, customer_max_price, fee%, fee_fixed)
        ↓
{ currency: "INR", low_price, mid_price, high_price,
  allowed_offer_min, allowed_offer_max,
  platform_fee_percent, platform_fee_amount, payment_mode }
```

- Zero city/zone/tier input of any kind.
- Fully dependent on the specific matched provider's own `BargainRule`.
- Sets `draft.status = "provider_matched"`. Does **not** touch
  `price_status` at all.
- Produces a real three-value Low/Mid/High trio.

### They merge in storage but never in logic

Both write into `draft.price_snapshot` via a shallow merge
(`{**(draft.price_snapshot or {}), ...}`), so if both endpoints were
called on the same draft, the resulting JSON blob would contain both sets
of keys side by side (`pricing_model`, `city_tier`, `base_price`, `note`,
`display_price`, `source` from (a); `price_options` from (b)) — but
neither computation ever reads the other's output. There is no code
anywhere that reconciles, cross-validates, or prefers one over the other.

## This Sprint's Resolution Decision

**Use (b) — `match-and-price` — as the sole, canonical Low/Mid/High
source.** Reasoning:

1. The product context (this sprint's own spec, §1) states the customer
   already has a provider match *before* this stage begins — (a) has no
   provider dependency and, by its own design, logically precedes
   matching rather than following it.
2. Only (b) produces a genuine three-value range; (a) produces a single
   `base_price`, which does not fulfill "real low-price / real mid-price /
   real high-price" as three distinct, real values.
3. CUSTOMER-L5-08 already built the real navigation path
   (`ServiceabilityScreen` → `ProviderPreviewScreen`) ending at a matched
   provider — (a) is not on that path today, and inserting a call to it
   at this late stage would set `draft.status = "price_estimated"`,
   **regressing** the draft's status backward past the already-reached
   `"provider_matched"` state with no code anywhere that depends on or
   expects that regression.

**Consequence, stated plainly and without workaround**: this sprint's
real, rendered Low/Mid/High has genuinely **no city-tier or zone
influence** — because the specific backend computation this sprint
correctly uses for the reasons above does not consult either input. A
future sprint could revisit this if product direction changes the real
backend to compose the two mechanisms (e.g., using the city-tier floor as
a lower bound on the provider's own range) — that composition does not
exist in the backend today, and this sprint does not simulate it
client-side.

## Precedence Within the Real Flow Used

For the one real mechanism this sprint uses, the actual resolution order
(verified in `service.py:582-616`) is:

```
1. Query all active, non-deleted BargainRule rows for this master_service_id
2. Join each to its linked ServicePricingRule (via pricing_rule_id), if any
3. Rank by specificity:
     3 = ServicePricingRule matches both offering_type_id AND brand_id
     2 = ServicePricingRule matches offering_type_id only
     1 = ServicePricingRule has neither type nor brand scope (a general rule)
    -1 = ServicePricingRule is type/brand-scoped but doesn't match this request (excluded)
4. Among remaining eligible rows, prefer higher specificity, then most recently created
5. If none found, or the winning row lacks customer_min_price/customer_max_price
   → 422 PRICE_OPTIONS_UNAVAILABLE
6. Compute Low/Mid/High from the winning BargainRule (+ its linked
   ServicePricingRule's admin range, used only for validation, not the
   final numbers)
```

This is a real, service-type/brand-aware precedence — this sprint's
`pricing-explanation` copy references it honestly ("this estimate is for
the specific service, type, and brand you selected") without exposing the
internal specificity-scoring mechanism itself.

## Missing-Rule Behavior

If no eligible `BargainRule` exists (or the winning one lacks a customer
range), the customer sees `PRICE_OPTIONS_UNAVAILABLE` — a real, expected,
non-fabricated outcome this sprint's UI treats as an honest "price
unavailable" state (see failure-matrix.md), not an error to hide or paper
over with an invented default range.

## Revision Behavior

No revision counter exists anywhere in the real data (contract-matrix.md).
"Revalidation" in this sprint means literally re-calling `match-and-price`
— which unconditionally overwrites `draft.price_snapshot.price_options`
and `draft.selected_provider_snapshot`/`selected_tenant_id` with a fresh
computation, with no diffing performed server-side. This sprint's own
client-side revision detection (comparing the previous in-memory result to
the new one after a manual refresh) is documented in
pricing-architecture.md — it is a client-side convenience for surfacing a
"price changed" banner, not a backend-guaranteed revision concept.
