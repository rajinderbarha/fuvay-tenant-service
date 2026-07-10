# CUSTOMER-FRONTEND-01 — Remaining Blockers / Known Gaps

1. **No real browser click-through performed.** No browser/DOM tool was
   available this session; only `curl.exe` (not even exercised against a
   running dev server — build issues consumed the remaining time) and static
   source review. See BROWSER_VERIFICATION report. This alone forces the
   final verdict to `PARTIAL_READY_WITH_CUSTOMER_FRONTEND_01_BLOCKERS`.

2. **Production build not cleanly reproduced.** `npx next build` reached
   "Compiled successfully" + "Finished TypeScript" on its best run but failed
   at "Collecting page data" with a filesystem race (`ENOENT
   .next\build-manifest.json`), reproducibly across bash and PowerShell. Root
   cause likely environment-specific (this session's `G:\` drive + Turbopack +
   a robocopy'd rather than `npm install`-ed `node_modules`, since the real
   `npm install` failed with `ERR_SSL_CIPHER_OPERATION_FAILED`). Needs
   re-verification in a clean environment.

3. **No live 200 from provider matching or booking confirmation.** The only
   serviceable zipcode in this dev DB (141001/141002 Ludhiana) returned
   `HOME_BOOKING_NO_PROVIDER_AVAILABLE` for AC Installation — meaning the
   Price/Review/Confirm/Tracking/Review-submission steps were verified by
   source reading only, not by an observed live success response. This is a
   backend seed-data/eligibility gap, out of this sprint's strict frontend-only
   scope to fix.

4. **Cancel-after-confirmation is not wired.** No
   `POST /v1/customer/bookings/{id}/cancel` route exists in
   `home_service_assignment/customer_router.py` (only the pre-confirmation
   booking-*draft* cancel exists). `cancelCustomerBooking()` in the API module
   throws a clear "not wired" error instead of faking success. A cancel action
   was intentionally NOT added to the booking-detail UI.

5. **No dedicated "service questions" endpoint.** Searched `admin_catalog`,
   `home_service_booking`, and the service-option customer router — none
   returns a structured single/multi/text/photo question list. The Details
   step instead uses `flow/config`'s `requires_*` flags plus service-options/
   issue-types lists as the closest real substitute.

6. **Photo upload disabled, honestly.** `POST .../booking-drafts/{id}/photos`
   exists but expects an already-hosted `photo_url`; no working multipart
   upload endpoint was verified in this session, so the Details step shows a
   disabled-with-explanation message rather than a fake upload control.

7. **"Popular services" and "recent booking" widgets not built.** No backend
   endpoint exists for either concept; building them client-side from the full
   bookings list was judged lower priority than the core 16-step flow given
   time constraints. See UI Report.

8. **Support action and cancel action on tracking page not built** — no real
   backend endpoints were found/verified for either within the time available.

9. **No registration/password-reset flow.** Only login + logout exist in
   customer-app; account provisioning is assumed to happen elsewhere (seed
   data / admin-side), matching the rest of this sprint's read-only-auth scope.

10. **Cross-customer-access and 403 paths not live-tested.** Only one seeded
    customer account exists in this dev DB, so "customer cannot access another
    customer's booking" was verified by reading the backend's own
    `customer_id` filter (returns a safe not-found shape), not by an actual
    two-account live test.

11. **Review submission never observed live.** No genuinely completed booking
    exists in this dev DB (the only draft created never reached `confirm`
    because matching failed). Fabricating a fake completed booking to force a
    review-submission test was explicitly against this sprint's honesty
    requirement, so this was left as a documented gap instead.

None of the above are believed to be data-integrity or security risks — the
backend enforces `customer_id` scoping, matching, and price integrity
server-side regardless of any frontend gap — but they must be closed out
before this app can be called production-ready, and none of them permit a
READY verdict this session per the sprint's own hard rule on browser
verification.
