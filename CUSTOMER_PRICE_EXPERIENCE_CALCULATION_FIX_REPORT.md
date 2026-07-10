# Customer Price Experience Calculation Fix Report

## The bug

`POST /v1/admin/home-services/price-experience/preview` called
`app.engines.home_service_booking.matching_engine.compute_price_tiers`,
which implements **asymmetric** fee application — fee only added to the
low end (`bargain_floor = customer_min * (1+fee%)`), while `high =
customer_max_price` was passed through completely unmodified. For the
ticket's own example (Selected Range ₹350–₹420 @ 10%), this produced
`High = ₹420` — the pre-fee selected maximum — instead of the correct
`₹462`.

That asymmetric formula is *correct* for its actual purpose elsewhere
(the certified Provider-First Matching flow, where "customer_min/max" is
the tenant's own negotiation range and the fee models a bargain floor,
not a full markup) — it was simply the wrong function for this admin
testing/preview tool, which needs fee applied to the entire selected
range, both ends.

## The fix

Switched the endpoint to
`app.engines.admin_catalog.bargain_engine.compute_symmetric_customer_price_tiers`
— the same pure function already used (and already certified) by the
Admin Home Services Catalog Console and Tenant Setup Wizard sprints,
which applies the platform fee to both `min` and `max`:

```
Low  = selected_min * (1 + fee%/100)
High = selected_max * (1 + fee%/100)
Mid  = round_to_nearest_5((Low + High) / 2)
```

Added a new `rounding_increment` parameter (default `10`, unchanged for
existing callers) so this endpoint alone can request nearest-5 rounding,
matching this ticket's exact expected `₹425` for the `₹350–₹420 @ 10%`
example (nearest-10 would have produced `₹420` instead).

## Live-verified against every ticket example

| Selected Range | Fee | Low | Mid | High |
|---|---|---|---|---|
| ₹350–₹420 | 10% | **₹385** | **₹425** | **₹462** |
| ₹350–₹450 | 10% | **₹385** | **₹440** | **₹495** |
| ₹300–₹500 | 10% | **₹330** | ₹440 | **₹550** |

All match the ticket's expected values exactly. Validation cases also
verified live: Selected Range below Admin Min → `422
SELECTED_RANGE_BELOW_ADMIN_MIN`; above Admin Max → `422
SELECTED_RANGE_ABOVE_ADMIN_MAX`; min > max → `422 INVALID_PRICE_RANGE`.

## No regression to existing certified callers

`compute_symmetric_customer_price_tiers`'s default `rounding_increment=10`
is unchanged, so the Admin Home Services Catalog Console (Window AC
550–700 → 605/690/770) and Tenant Setup Wizard (Split AC 850–1100 →
935/1070/1210) examples were re-verified to produce identical output
after this change — confirmed both via direct function calls and the
full pytest regression suite (193/193 passing across every Home Services
test file this session).
