# Seed Before/After Report — UX-06 Round 4

## Before (real `GET /v1/tenant/service-areas` + `.../services`, captured live)

| Area | Coverage | Service mappings |
|---|---|---|
| `c50daa54-3d07-46a4-b449-41761ab33fc0` | city=Ludhiana | **0** |
| `b50750e9-8e1f-4863-b1b7-f170c2859901` | zipcode=Ludhiana/147001 | 1 (`ac_installation`, unrelated) |

Real serviceability check (`POST .../serviceability-check`, city=Ludhiana,
`ac_repair`): `{"serviceable": false, "message": "This service is not available
in Ludhiana yet. We're expanding soon!"}` — matches Round 3's finding exactly.

## Action taken

`POST /v1/tenant/service-areas/c50daa54-.../services` with
`{service_id: a96e625a-... (ac_repair), job_type: "repair", is_available: true,
sla_minutes: 120, base_price: 775.0}`, then
`PUT .../services/d07529ff-...` adding `min_price: 650.0, max_price: 900.0`.

## After (real calls, same draft/serviceability-check/price-estimate endpoints)

| Area | Coverage | Service mappings |
|---|---|---|
| `c50daa54-...` | city=Ludhiana | **1** (`ac_repair`, `repair`, NEW) |
| `b50750e9-...` | zipcode=Ludhiana/147001 | 1 (unchanged) |

Real serviceability check (same category/offering, city=Ludhiana):
```json
{"serviceable": true, "available_provider_count": 1, "matched_by": "city",
 "message": "Service is available in Ludhiana.", "reason_code": null,
 "draft_status": "serviceability_checked"}
```

Real price estimate (same draft, immediately after):
```json
{"price_snapshot": {"pricing_model": "fixed", "visit_fee": 0, "base_price": 75.0,
 "min_price": 75.0, "currency": "INR", "city_tier": "tier_3",
 "platform_fee_pct": 10.0, "platform_fee": 7.5, "customer_total": 82.5,
 "display_price": "₹82", "source": "backend_catalog"}, "draft_status": "price_estimated"}
```

(Note: the displayed `base_price` of ₹75 here comes from the offering's
platform-catalog default pricing, not the ₹775 entered on the tenant service
area mapping — the catalog-default price-estimate path and the
provider-specific `match-and-price` path are two different real pricing
sources; see round4-implementation-summary.md.)

## Negative control (unaffected)

Re-ran the identical sequence with city=Mumbai (never touched by this seed):
`{"serviceable": false, "message": "This service is not available in Mumbai
yet. We're expanding soon!", "reason_code": "NO_PROVIDER_IN_CITY"}` — confirms
the seed did not broaden serviceability beyond the one intended city.

## Removal

To reverse: `DELETE /v1/tenant/service-areas/c50daa54-.../services/d07529ff-...`
(real endpoint, confirmed present in `app/engines/serviceability/router.py`).
Not executed at the end of this round because the seed is needed for
continued Round 5 work on the deeper booking-submission blocker (see
seed-removal-report.md for the exact command and its restore-prior-behavior
verification).
