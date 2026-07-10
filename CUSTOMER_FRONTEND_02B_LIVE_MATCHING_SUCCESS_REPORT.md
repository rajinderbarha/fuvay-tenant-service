# CUSTOMER-FRONTEND-02B — Part 3: Live Matching Success Report

## Real curl flow (Customer One, real JWT, real DB)

1. `POST /v1/customer/home-services/booking-drafts` `{category_slug: home_services, offering_slug: ac_repair}` → draft created.
2. `PUT /v1/customer/home-services/booking-drafts/{id}` with `issue_summary, city=Ludhiana, zipcode=141001, brand_id=LG, offering_type_id=Split AC`.
3. `POST .../serviceability-check` → `{"serviceable": true, "available_provider_count": 1, "matched_by": "zipcode"}`.
4. `POST .../match-and-price` → REAL response:

```json
{
  "selected_provider": {
    "tenant_id": "34b427a7-b2be-496c-b826-6d51bb181248",
    "provider_name": "Demo AC Services",
    "public_badges": ["Verified", "High Completion"],
    "customer_visible_reason": "Best matched provider based on service coverage, availability, quality, and completion history."
  },
  "selected_provider_price_options": {
    "currency": "INR",
    "allowed_offer_min": 770.0,
    "allowed_offer_max": 935.0,
    "low_price": 770.0,
    "mid_price": 850.0,
    "high_price": 935.0,
    "platform_fee_percent": 10.0,
    "platform_fee_amount": 85.0,
    "payment_mode": "customer_pays_provider_directly"
  },
  "draft_status": "provider_matched"
}
```

## Verification against spec baseline
- Expected Low ₹770 / Mid ~₹850 / High ₹935 → **exact match** (no adjustment needed once seed gap was fixed).
- Platform fee 10% → confirmed (`platform_fee_percent: 10.0`).
- Payment mode `customer_pays_provider_directly` → confirmed.
- `selected_provider.business_name` real ("Demo AC Services"), `request_id` present in the response envelope (`meta.request_id`).
- No `internal_score` or admin/provider min/max range leaked to the customer response (confirmed by field-by-field inspection).

STATUS: LIVE MATCHING SUCCESS — no blockers.
