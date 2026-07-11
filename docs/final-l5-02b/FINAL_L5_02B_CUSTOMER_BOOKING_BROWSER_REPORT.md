# FINAL-L5-02B — Real Chromium Customer Booking Browser Report

Spec: `e2e/tenant-portal/final-l5-02b-customer-booking-browser.spec.ts` (targets `localhost:3002`, the customer-app). Real Chromium, zero mocking.

## Customer One
| Step | Result |
|---|---|
| 1. Login | PASS |
| 2. Open booking list | PASS |
| 3. Verify seeded bookings appear | **PASS** — all 5 (`L501-BK-0001..0005`) visible with real status (`converted`/`cancelled`) |
| 4. Open detail | **PASS** — `#L501-BK-0001` detail opens |
| 5. Open tracking | Detail page itself embeds a "Status Timeline" section (tracking is not a separate route in this app — confirmed via live capture: "Status Timeline / Booking confirmed") |
| 6. Verify related service_job status | Status shown ("Provider is assigning a technician") reflects the joined `service_jobs` state |
| 7. Verify correct tenant/provider | Not independently asserted by name this sprint (provider fields were `null` for the un-assigned seeded jobs shown, consistent with real assignment state, not a bug) |
| 8. Verify correct payment wording | **PASS** — "Payment: Customer Pays Provider Directly" — exact allowed wording, live-captured |
| 9. Verify cancellation/review availability | Cancellation control not tested (no backend endpoint exists — documented gap, not a UI bug); review UI not independently probed this sprint |

## Customer Two
| Step | Result |
|---|---|
| 1. Login | PASS |
| 2. Verify Customer One booking absent | **PASS** — Customer Two's own seeded booking (`L501-BK-0006`) shown instead; `L501-BK-0001..0005` never appear |
| 3. Attempt direct URL | **PASS** — navigated directly to Customer One's booking URL |
| 4. Attempt direct API request | Covered by the Live API Smoke Report (bidirectional cross-access probe) |
| 5. Verify 403 or secure 404 | Body shows "Booking not found." — safe, no data exposure (HTTP 200 status caveat, same as documented elsewhere) |

## Result
Both Playwright tests passed: `2 passed (23.6s)`. Minor observation (not a blocker): the booking detail address line shows a leading comma (", Ludhiana") — the seeded `address_snapshot.line1` field renders empty for this record; a cosmetic seed-data completeness gap, not a source-of-truth or isolation issue.
