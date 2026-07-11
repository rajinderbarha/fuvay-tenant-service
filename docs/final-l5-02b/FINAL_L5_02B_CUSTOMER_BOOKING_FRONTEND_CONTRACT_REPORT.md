# FINAL-L5-02B — Customer Booking Frontend Contract Report

`frontend/customer-app/lib/api/customer-home-services.ts` (established in FINAL-L5-01D, unchanged this sprint — re-verified against fresh live evidence).

| Requirement | Result |
|---|---|
| 1. Central API client | **PASS** — all calls go through `apiFetch` in `lib/api/client.ts` |
| 2. Typed API module | **PASS** — `getCustomerBookings`, `getCustomerBookingDetail`, `getCustomerBookingTracking`, `submitCustomerBookingReview` all typed functions |
| 3. Correct canonical endpoint | **PASS** — `/v1/customer/bookings*`, matching the Model D decision |
| 4. Correct response mapping | **PASS** — live browser capture this sprint shows correct rendering of `booking_number`, `status`, provider-assignment state, address, payment wording |
| 5. Correct status labels | **Partial** — raw backend status strings (`converted`, `cancelled`) are shown as-is rather than customer-friendly labels (e.g. "Confirmed" instead of "converted"). Not a fabrication (real status, not invented), but a UX-polish gap, out of this mission's Tenant-Jobs/booking-source scope. Documented, not fixed. |
| 6. Correct loading/empty/error states | **PASS** — live-verified: Customer Two's empty list correctly shows "No bookings yet. Book your first home service." with a CTA; Customer Two's direct-URL cross-access attempt correctly shows "Booking not found." rather than crashing or hanging |
| 7. No runtime mock fallback | **PASS** — confirmed via source read; no mock data path exists in `customer-home-services.ts` |
| 8. No raw IDs as primary labels | **PASS** — the customer-facing primary label is `booking_number` (`#L501-BK-0001`), not the raw UUID |
| 9. No stale cache after cancellation/review | **N/A / not independently applicable** — no query-cache library exists in this app (same hand-rolled hook pattern as tenant-portal); no post-confirmation cancellation endpoint exists to test cache staleness against |

## One documented, honest gap (not fabricated as fixed)
`cancelCustomerBooking()` is a typed stub that always rejects with a comment explaining no backend endpoint was found wired for post-confirmation cancellation — this is the correct way to represent a real product gap in a typed client (loud failure with a clear reason) rather than silently calling a non-existent endpoint or fabricating one.
