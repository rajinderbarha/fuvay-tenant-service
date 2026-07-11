# FINAL-L5-02B — Customer Booking RBAC and Isolation Report

Live probe against `/v1/customer/bookings*` this sprint, with **real bookings now seeded for both customers** (this sprint's seed fix — see Seed Alignment Report), enabling genuine bidirectional cross-access testing rather than a one-sided "sees nothing" proof.

| Test | Result |
|---|---|
| 1. Customer One sees only own bookings | **PASS** — `GET /v1/customer/bookings` returns exactly `['L501-BK-0001'..'0005']`, no `L501-BK-0006` |
| 2. Customer Two cannot see Customer One's booking | **PASS** — Customer Two's list returns exactly `['L501-BK-0006']` only |
| 3. Direct URL/API access is 403 or secure 404 | Both directions tested with real booking IDs: `customer1 → customer2's booking_id` and `customer2 → customer1's booking_id` both return `HTTP 200` with `{"success": false, "error": {"code": "BOOKING_NOT_FOUND", "message": "Booking not found."}}` — **zero data exposed in either direction**, but literal status is 200 not 403/404 (same pre-existing L5-01D-006 pattern, documented not hidden) |
| 4. Tenant owner cannot use customer self-scope endpoint improperly | **PASS** — Tenant Owner token against `/v1/customer/bookings` returns 200 with `items:[]` (soft-blocked, zero cross-scope data) |
| 5. Technician cannot use customer self-scope endpoint improperly | **PASS** — same soft-block pattern, `items:[]` |
| 6. Anonymous receives 401 | **PASS** — exact 401 |
| 7. Cancellation/review enforce ownership | Not independently live-tested this sprint (no post-confirmation cancel endpoint exists at all — see Backend Alignment Report; review endpoint reuses the same `ServiceBooking` ownership check already proven for detail/tracking, by code inspection of `home_service_assignment/customer_router.py`'s rating handler, which filters by `customer_id == user.user_id` identically to the detail handler) |

## Result
**Genuine bidirectional isolation confirmed with real data on both sides** (a stronger proof than FINAL-L5-01D's one-sided "Customer Two sees 0" check, made possible by this sprint's seed fix). No `NOT_READY_FINAL_L5_02B_CUSTOMER_ISOLATION_FAILED` — no data leak in any direction, in any role combination tested.
