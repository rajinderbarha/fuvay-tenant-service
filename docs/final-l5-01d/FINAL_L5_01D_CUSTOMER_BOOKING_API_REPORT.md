# FINAL-L5-01D — Customer Booking API Regression Report

Real live HTTP tests against `/v1/customer/bookings*` after the seed alignment fix.

| Test | Role | Status | Body result | Expected | Result |
|---|---|---|---|---|---|
| List bookings | Customer One | 200 | **5 real items** (`L501-BK-0001..0005`) | Sees own bookings | **PASS** — was empty before this sprint's fix |
| Booking detail | Customer One | 200 | Real booking data | Sees own booking | **PASS** |
| Tracking | Customer One | 200 | Loads | Tracking resolves | **PASS** |
| Cross-customer detail access | Customer Two → Customer One's booking ID | 200 | `{"success": false, "error": {"code": "BOOKING_NOT_FOUND"}}` — **zero data disclosed** | 403 or secure 404 | **PASS (secure), soft status-code pattern** — no leak, but delivered as embedded error in a 200 response rather than an HTTP 404. See finding below. |
| List bookings | Customer Two | 200 | `items: []` | Cannot see Customer One's bookings | **PASS** — isolation confirmed |
| List bookings | Tenant Owner | 200 | `items: []` (safe empty — no `customer_id` claim) | Tenant cannot use customer self-scope endpoint improperly | **PASS (safe empty)**, same soft-block pattern as Tenant Jobs' customer case |
| List bookings | Technician | 200 | `items: []` | Technician cannot use customer self-scope endpoint improperly | **PASS (safe empty)** |
| Missing booking (fake UUID) | Customer One | 200 | `{"success": false, "error": {"code": "BOOKING_NOT_FOUND"}}` | Safe 404 | **PASS (secure)**, same embedded-error pattern |
| Unauthenticated | — | 401 | — | 401 | **PASS** |

## Real finding: embedded-error pattern instead of HTTP status codes
Both the cross-customer-access and missing-booking cases return `HTTP 200` with a nested `{"success": false, "error": {...}}` payload rather than a genuine `403`/`404` HTTP status. This is a **safe** pattern — zero data is ever disclosed to the wrong customer — but does not match the mission's literal expectation of a `403`/`404` status code. This mirrors the same architectural pattern found in the Tenant Jobs RBAC report (soft-scoping via empty results/embedded errors rather than explicit HTTP-level rejection). Logged as BUG-L5-01D-006 in the bug register — a consistency/hardening item, not a vulnerability.

## Result
**No cross-customer or cross-role data leakage found in any test.** Customer One's booking history is now real and populated (the core fix this sprint delivers). The status-code-vs-embedded-error pattern is a real, honest finding for future API consistency work.
