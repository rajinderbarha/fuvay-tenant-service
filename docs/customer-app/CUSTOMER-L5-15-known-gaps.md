# CUSTOMER-L5-15 — Known Gaps

## P0

1. **No live runtime certification** — see `runtime-evidence.md`. Same
   constraint as every previous sprint, compounded this sprint by there
   being no real mutation to certify even in principle.
2. **No real, customer-facing cancellation or reschedule capability
   exists anywhere in this backend for the canonical `ServiceBooking`/
   `ServiceJob` pipeline.** This is the sprint's defining finding, not a
   deferred nice-to-have — see `baseline-verification.md`'s Central
   Finding and `contract-matrix.md`. A real, complete, permission-correct
   cancellation/reschedule engine exists (`app/engines/booking/`), but it
   operates on a wholly disconnected `bookings` table that the real
   booking-creation flow (`HomeServiceFinalCreationService.finalize()`)
   never populates — confirmed by direct data-flow tracing, cross-checked
   by an independent research pass. Closing this gap requires backend
   work: either build real cancel/reschedule endpoints against the
   canonical tables, or migrate the legacy engine onto them.

## P1

3. **Even the disconnected legacy `booking` engine would not satisfy this
   spec's fuller model if it were somehow wired up** — no per-cancellation
   fee amount field, no refund-eligibility field, no service-credit field
   beyond an internal credit-reservation release/forfeit, no
   Idempotency-Key support, no optimistic-concurrency/version field, and
   its reschedule-accept flow performs zero serviceability/pricing/
   bargain/provider revalidation (a bare date/slot overwrite). A backend
   fix would need to address all of these, not just the table mismatch.
4. **Cancelling a job (provider-only, today) does not cascade** — it
   never unassigns the technician (a real, correct `cancel_assignment`
   method exists but is never invoked), never cancels open
   `ServiceJobQuote`/`PartsRequest` rows (a real `cancel_quote` method
   exists but is likewise never invoked), and never publishes any
   notification event. Any future customer-facing cancel endpoint would
   need to orchestrate all of this explicitly — see
   `provider-assignment-impact.md`, `pricing-and-bargain-impact.md`.
5. **No cancellation/reschedule notification events exist in the active
   `platform_notifications` registry** — see
   `notification-deep-links.md`. An older, disused notification engine
   has seed-data strings for these events with no confirmed real emitter.
6. **`PARTS_STATUS_CANCELLED` is a dead constant** — defined once
   (`execution/constants.py`), referenced nowhere else, matching the
   same "aspirational status, zero service logic" pattern found in
   CUSTOMER-L5-10/12/13/14.

## P2

7. **No component/render tests added** for the (unchanged) informational
   row — consistent with the now-fifteen-sprints-running deprioritization
   of screen-render tests in favor of domain-logic tests, and there is no
   new interactive behavior to render-test regardless.
8. **This sprint's `ActionRow` `testID` addition is the only visible
   change to `BookingDetailScreen.tsx` beyond the new function call** —
   a minimal, backward-compatible change, not a rewrite, keeping this
   sprint's blast radius as small as its actual (near-zero) real scope.

## P3

9. **No localization changes were needed or made this sprint** — the
   existing `bookings.detail.actionCancelReschedule`/
   `actionCancelRescheduleNote` copy (English/Hindi/Punjabi, in place
   since CUSTOMER-L5-12) already correctly reflects the honest state;
   inventing new "cancellation policy"/"reschedule window" copy strings
   this sprint would have been translating text for a feature that does
   not exist.
10. **No analytics events were added** — every analytics event this
    sprint's spec requested (`cancellation_eligibility_checked`,
    `reschedule_submitted`, etc.) presupposes a real user-initiated flow
    that does not exist; adding them as dead event names would violate
    the same "no fake feature" principle applied throughout.
