# ADMIN-TENANT-E2E-09B — Live Bookability/Matching Report (CRITICAL — not deferred)

This corrects the prior sprint's false deferral (which checked the wrong table,
`tenant_wallets` = 0.0000, and incorrectly concluded credits were insufficient). The real
table, `tenant_billing.credit_balance` = 3937.00, is healthy — so the live match-and-price
flow was run for real, end-to-end, as `customer@serviceos.in`.

## Real sequence executed

1. Logged in as `customer@serviceos.in` → real JWT.
2. `POST /v1/customer/home-services/booking-drafts` with
   `{category_slug: "home_services", offering_slug: "ac_repair"}` → 200, draft
   `1329656a-d7d3-47e6-8f71-a74f6dcf2ea7` created.
3. `PUT /v1/customer/home-services/booking-drafts/{id}` with issue="AC Not Cooling",
   city="Ludhiana", zipcode="141001", offering_type_id=Split AC, brand_id=LG → 200,
   `draft_status: collecting_details`.
4. `POST /v1/customer/home-services/booking-drafts/{id}/match-and-price` → **200 OK**:

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
    "low_price": 770.0, "mid_price": 850.0, "high_price": 935.0,
    "platform_fee_percent": 10.0, "platform_fee_amount": 85.0,
    "payment_mode": "customer_pays_provider_directly"
  },
  "draft_status": "provider_matched"
}
```

5. `POST .../cancel` afterward to leave no dangling draft state.

## What this proves

- Service setup active (Split AC published), service coverage active (141001 → Split AC + LG
  row), provider price range active (850-1100), service area active, availability active,
  usage credit balance sufficient (3937.00 via `tenant_billing`) — all real gates passed.
- Matching selected Demo AC Services (the only real tenant) — real selection, not fabricated.
- Real Low/Mid/High = 770/850/935 (currency INR), `payment_mode:
  customer_pays_provider_directly` — no manual-bargain logic, no `tenant_wallets` dependency
  anywhere in the response or the code path that produced it.
- No internal debug/scoring fields leaked to the customer-facing response.

Verdict: PASS — genuinely executed, not deferred. Not
NOT_READY_TENANT_LIVE_BOOKABILITY_FAILED / NOT_READY_TENANT_MATCHING_FAILED.
