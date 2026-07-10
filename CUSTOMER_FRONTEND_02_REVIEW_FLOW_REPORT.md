# CUSTOMER-FRONTEND-02 — Review Flow Report

File: `app/customer/bookings/[bookingId]/rate/page.tsx`

## Gating logic (verified in code)
```
if (booking && booking.status !== "completed" && !submitted && !existingReview) {
  return <div className="co-card">You can review this service after it is completed.</div>;
}
if (existingReview || submitted) {
  return <...>"Thanks for your feedback! A review has already been submitted for this booking."</...>;
}
```
- Form (star rating 1-5 + optional comment) only renders once neither of the above early-returns fires, i.e. only for a `completed` booking with no existing review. Confirmed correct gating.
- Rating validated client-side before submit: `if (rating < 1 || rating > 5) { setError(...) }`.
- Comment is optional: `comment: comment || undefined`.
- Submit calls the real API function `submitCustomerBookingReview(bookingId, {...})` — no direct fetch, no mock.
- Duplicate-review state reuses the same "already submitted" card via `existingReview` (fetched from `getCustomerBookingReview`).
- Errors render through `ErrorBanner`, which surfaces `CustomerApiError.requestId`.

## Live test — NOT REACHED (same root cause as Sprint 01)
No genuinely completed booking exists in this dev DB (bookings list for the seeded customer returns `{"items":[]}` — see Live API report). Provider matching for AC service in the only seeded zipcode still fails with `HOME_BOOKING_NO_PROVIDER_AVAILABLE`, so no booking has ever reached `confirmed`, let alone `completed`.

Per the spec's explicit instruction, a fake/synthetic completed booking was **not** fabricated. What WOULD be needed backend-side to create one safely: either (a) fix the seed data so a provider/tenant is eligible for AC service in a seeded zipcode, allowing a real booking through match->confirm, then a legitimate admin/staff action to mark the resulting job `completed`, or (b) if one exists, a dev-only "force complete" endpoint — none was found in `home_service_assignment` router in this session's scope of review, and building one is backend work outside this sprint's strict frontend-only scope.

## Verdict: Code-level gating is correct and safe. Live submission untestable due to a pre-existing, out-of-scope backend data gap — documented honestly, not fabricated around.
