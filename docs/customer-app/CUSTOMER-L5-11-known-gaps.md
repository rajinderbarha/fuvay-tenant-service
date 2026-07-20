# CUSTOMER-L5-11 — Known Gaps

## P0

1. **No live runtime certification** — see `CUSTOMER-L5-11-runtime-evidence.md`.
   Identical constraint to every previous sprint's own P0 gap.

## P1

2. **`ServiceBooking.provider_snapshot` is not server-side stripped** —
   confirmed to include `internal_score`/`matching_score_snapshot`
   (unlike `booking_summary.selected_provider`, which is). This client
   mitigates it via schema-level stripping (`security-review.md`), but
   the underlying backend inconsistency remains a real, disclosed data-
   hygiene gap the backend team should address directly (a customer with
   raw database or future-API access to the full `ServiceBooking` record
   would see internal scoring data other equivalent fields correctly
   hide).
3. **`finalize()`'s own guard exceptions
   (`FINAL_DRAFT_NOT_FOUND`/`FINAL_DRAFT_NOT_READY`/`FINAL_ACCESS_DENIED`)
   are not cleanly mapped** — they fall through to a generic
   `INTERNAL_ERROR` 500 handler rather than a specific 4xx response
   (baseline-verification.md finding #5). In practice rarely triggered,
   since `mark_ready_for_confirmation` (called first, with clean 422s)
   already screens out most of the same conditions — but a real,
   disclosed backend robustness gap for the narrow race-condition window
   between the two calls. Not fixable from this sprint's frontend code.
4. **`GET /bookings/{id}` returns HTTP 200 for not-found/access-denied**
   rather than 404/403 — a real, disclosed API design quirk this client
   works around via response-body-shape parsing
   (`parseBookingDetailResponse`'s union type), documented in
   contract-matrix.md.
5. **No cancellation-policy or consent/terms field exists anywhere in
   this backend** — this sprint displays static, deliberately generic
   app copy for cancellation policy (rather than a fabricated specific
   policy) and renders no consent checkbox at all (rather than an
   unpersisted one). See `review-contract.md`.
6. **No component/render tests** for either new screen — same,
   now-consistent-across-eleven-sprints deprioritization pattern.

## P2

7. **No genuine live duplicate-submission or timeout-reconciliation test
   was performed** — the safety of "Check status" reusing the same
   idempotency key rests on source-code reading of the real DB-unique
   constraints, not an observed live race. See `idempotency-contract.md`/
   `runtime-evidence.md`.
8. **`bookingsList`/`bookingDetail` remain unbuilt this sprint** (still
   `productionEnabled: false`) — a future "My Bookings" sprint must build
   fresh against `/v1/customer/my-activity/bookings*`, and must **not**
   reuse or extend the pre-existing, unrelated
   `BookingsListScreen.tsx`/`BookingDetailScreen.tsx` (which call a
   completely different, legacy `/v1/bookings` engine — see
   baseline-verification.md finding #5's cross-check section). Flagged
   prominently here since the naming similarity is a real risk of
   accidental conflation in a future sprint.
9. **No notification-registration UI was built** — the real backend has
   zero notification side effects on booking creation today (confirmed:
   `creation_service.py`'s own docstring states "Does NOT push
   notifications... Sprint 20+"), so there is nothing real to register
   against. Will need building once that backend capability exists.
10. **No analytics events actually wired to a vendor** — same
    now-eleven-sprints-running gap: no analytics SDK is integrated in
    this app at all; `logger.*` calls are structured logs only.
11. **`booking-confirmation-api.ts`/hook composition files have no
    dedicated unit tests** — consistent with the established, repo-wide
    pattern for thin API wrappers and hook-composition layers.

## P3

12. **Punjabi/Hindi translations of the new `bookingReview.*`/
    `bookingConfirmation.*` keys were written by this sprint and have not
    been reviewed by a native-speaking product reviewer** — same
    disclosed caveat pattern as every previous sprint's localization
    additions.
13. **Rollback-on-exception behavior is a source-level inference**, not a
    live-observed guarantee — see `conversion-contract.md`.
14. **Two unused localization keys remain** (`bookingReview.editService`/
    `bookingReview.editSchedule`) — added defensively but ultimately not
    used once it became clear no real edit-service/edit-schedule route
    exists to navigate to (`review-contract.md`); harmless (unused
    translation keys are not a lint error) but worth removing in a future
    cleanup pass.
