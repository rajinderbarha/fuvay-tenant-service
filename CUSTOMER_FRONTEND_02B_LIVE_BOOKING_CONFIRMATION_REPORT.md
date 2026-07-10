# CUSTOMER-FRONTEND-02B — Part 4: Live Booking Confirmation Report

## Real curl flow, continued from Part 3

5. `POST .../confirm-price-choice` `{"price_tier":"mid"}` → `customer_offer: 850.0, selected_price_tier: mid`.
6. `POST .../summary` → full booking summary incl. price_estimate, selected_provider, serviceability, `ready_for_confirmation: true`.
7. `POST .../confirm` (with `Idempotency-Key` header) → REAL response:

```json
{
  "idempotent": false,
  "booking_number": "BK-20260710-000002",
  "booking_id": "29abc459-803a-4b37-83f9-6637ad074d8c",
  "job_number": "JOB-20260710-000002",
  "job_id": "b035159a-b19b-4500-8cb4-99a412e8ac34",
  "status": "pending_assignment",
  "booking_status": "confirmed",
  "confirmation_id": "47185a0f-4b71-4cde-9671-23db01dcefe8",
  "selected_provider_tenant_id": "34b427a7-b2be-496c-b826-6d51bb181248",
  "selected_price_option": "mid",
  "selected_price_amount": 850.0,
  "payment_mode": "customer_pays_provider_directly"
}
```

All required fields verified present and correct:
- `booking_id` present.
- `selected_provider_tenant_id` = the real Demo AC Services tenant.
- `selected_price_option` = "mid".
- `payment_mode` = "customer_pays_provider_directly".

STATUS: LIVE BOOKING CONFIRMATION SUCCESS.
