# Price Live Evidence — UX-06 Round 4

Real `POST /v1/customer/home-services/booking-drafts/{id}/price-estimate` call
(catalog-default pricing path, `HomeServiceChatbotBookingService.resolve_price_estimate`):

```json
{"price_snapshot": {
  "pricing_model": "fixed", "visit_fee": 0, "base_price": 75.0, "min_price": 75.0,
  "max_price": null, "currency": "INR", "city_tier": "tier_3",
  "note": "Fixed price service.", "platform_fee_pct": 10.0, "platform_fee": 7.5,
  "customer_total": 82.5, "customer_min_price": 82.5, "customer_max_price": null,
  "fee_included_note": "Includes ₹7 platform fee (10%)", "display_price": "₹82",
  "source": "backend_catalog"
}, "draft_status": "price_estimated"}
```

`source: "backend_catalog"` confirms this is a real, server-computed value —
`display_price` is what `DeepSeekChatScreen.tsx` shows verbatim (no
client-side recalculation), satisfying Workstream 6's "server-returned values
only" requirement.

**Important correction discovered this round**: this catalog-default price
(₹75 base + platform fee = ₹82 total) is a DIFFERENT real pricing source than
the `base_price: 775.0` entered on the tenant's `TenantServiceAreaService`
mapping this round's seed created. The tenant-specific price only takes effect
through the `match-and-price` → `confirm-price-choice` provider-selection
sequence (a separate, real, not-yet-wired step — see
round4-implementation-summary.md), which additionally requires a platform-wide
`BargainRule` record this round deliberately did not create (out of the safe,
isolated-tenant seed scope). The DeepSeekChatScreen flow currently shows and
confirms against the catalog-default price only, which is real and
server-authoritative, just not yet the full provider-priced flow.
