# UX-06 Round 4 Implementation Summary

**Status: CUSTOMER_APP_DESIGN_PARTIAL.** (See final-status-rationale.md for why
COMPLETE was not reached, and what specifically remains.)

## What this round did

1. Verified branch/lineage before starting (`d5eb7d4`, working tree clean).
2. **Safely, reversibly seeded real serviceability data** using only real
   tenant-portal API endpoints (no raw SQL), scoped to the pre-existing DEMO
   tenant already used by `scripts/seed_demo_users.py`: added one
   `TenantServiceAreaService` mapping (`ac_repair`/`repair`) to an existing
   Ludhiana city-coverage area. Full before/after/idempotency/removal evidence
   in test-data-environment-safety.md / tenant-service-area-seed-contract.md /
   seed-before-after-report.md / seed-idempotency-report.md /
   seed-removal-report.md.
3. **Proved the seed's real effect live**: serviceability check for
   `ac_repair`/Ludhiana now returns `serviceable: true` (was `false` in Round
   3); price-estimate now returns a real `₹82` value (was untested in Round 3).
   Both re-confirmed in a real browser session (not just curl).
4. **Discovered the real, deeper next blocker**: the canonical
   `match-and-price` → `confirm-price-choice` → `mark_ready_for_confirmation`
   → `confirm` sequence requires a platform-wide `BargainRule` record (for
   `ac_repair`) that does not exist in this dev DB — and correctly, per the
   safety rules, was NOT created this round (it would be a shared canonical
   record, not isolated test-tenant data). Documented precisely in
   canonical-booking-contract.md / booking-submission-live-evidence.md.
5. Ran a real Playwright browser certification of the improved flow (login →
   home → bookings/profile tabs → chat → language select → categories →
   offerings → issue/address → **real positive serviceability + real price**
   → confirm attempt correctly rejected with a real backend error). Zero
   uncaught console errors this round (Round 3's 2 runtime-crash bugs did not
   recur).
6. Ran the first production-design route audit across 18 screens
   (production-design-route-audit.csv) — the user's specific concern. Found:
   every screen actually visited this round IS the new design (no old mock
   scaffold detected), but 3 screens (Notifications, Booking Detail, standalone
   Service Detail) were not visited/verified — marked honestly as
   "unverified," not silently assumed clean.
7. Generated a full typecheck-error-inventory.csv (all 123 errors, file/line/
   code/message/owned-by-UX-06 flag) — confirms zero UX-06-owned files have
   any errors (already satisfied from Round 3; this round formalized it into
   the required CSV format).
8. Added 4 new tests (23 total, up from 19) covering the real booking-contract
   request shape (no client-controlled tenant/price, real idempotency-key
   reuse on retry).
9. Re-confirmed zero backend/other-frontend-app changes.

## What remains

The `BargainRule` gap (booking submission itself), Notifications/Booking
Detail/Service Detail design verification, dark theme (doesn't exist yet),
saved-address integration in the booking flow, the 123 pre-existing typecheck
errors in non-UX-06-owned screens. Full, prioritized list in
known-limitations.md.
