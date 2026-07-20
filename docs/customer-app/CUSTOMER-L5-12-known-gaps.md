# CUSTOMER-L5-12 — Known Gaps

## P0

1. **No live runtime certification** — see `CUSTOMER-L5-12-runtime-evidence.md`.
   Identical constraint to every previous sprint's own P0 gap.

## P1

2. **No real code path advances a booking/job past `scheduled`** —
   `dispatched`/`in_progress`/`completed`/`cancelled` are real, defined
   constants that are never assigned anywhere in the repository (verified
   exhaustively, two independent research passes). This means the review
   boundary (gated on `status === "completed"`) and the "past bookings"
   tab can currently never show any real data — both are correctly
   implemented, forward-compatible logic, but untestable against any real
   booking today. See `status-projection.md`.
3. **No server-side status/date/search filter exists on the real bookings
   list endpoint** — Active/Past filtering is applied client-side over
   whatever pages have been loaded via real pagination, a real, disclosed
   tension with §14's own "do not filter only the currently loaded page"
   instruction, resolved in favor of §59's "no full-history load"
   principle. See `list-architecture.md`.
4. **Timeline event labels are English-only** — `_safe_event_label`'s
   backend dictionary has no locale awareness; Hindi/Punjabi customers see
   these specific strings in English regardless of app locale. Same
   category of gap as prior sprints' `customer_visible_reason`/
   `assignment_message` findings.
5. **No component/render tests** for either new screen — same,
   now-consistent-across-twelve-sprints deprioritization pattern.
6. **No real push-notification channel exists** — the backend's push
   provider is a permanent stub. This client's notification-deep-link
   wiring is real and tested but cannot be exercised end to end against
   an actual push payload today. See `notification-deep-links.md`.

## P2

7. **No real cancellation or reschedule endpoint exists for a confirmed
   `ServiceBooking`** — only a pre-confirmation draft-level cancel exists.
   This sprint shows an honest informational note rather than a dead
   button; a future sprint (unowned per available spec context) would
   need to build the real backend endpoint first.
8. **No real technician-profile, parts-approval, or invoice capability
   exists** — same treatment (informational rows, no fabricated data).
   See `action-contract.md`.
9. **Legacy `BookingsListScreen.tsx`/`BookingDetailScreen.tsx` still exist,
   calling an entirely different, unrelated `/v1/bookings` engine** — this
   sprint does not touch, remove, or migrate them (out of scope), but
   flags again (as CUSTOMER-L5-11's known-gaps.md already did) that any
   future consolidation effort must not conflate the two systems.
10. **No analytics events actually wired to a vendor** — same
    now-twelve-sprints-running gap: no analytics SDK is integrated in
    this app at all; `logger.*` calls are structured logs only.
11. **`bookings-api.ts`/hook composition files have no dedicated unit
    tests** — consistent with the established, repo-wide pattern for thin
    API wrappers and hook-composition layers.
12. **No bounded background-polling was implemented** — judged
    unnecessary this sprint given the real status sequence's slow,
    infrequent transition cadence and the absence of any real-time push
    channel to react to; pull-to-refresh and refetch-on-mount are the
    real freshness mechanisms. Documented as a deliberate scope decision,
    not an oversight.

## P3

13. **Punjabi/Hindi translations of the new `bookings.*` keys were
    written by this sprint and have not been reviewed by a
    native-speaking product reviewer** — same disclosed caveat pattern as
    every previous sprint's localization additions.
14. **The `tracking` route remains reserved but unbuilt** — deliberately
    left to CUSTOMER-L5-13, since it most naturally maps to live
    GPS/map tracking (the separate `execution` engine's real but
    deliberately-deferred capability), not this sprint's assignment-event
    timeline (embedded directly in the booking-detail screen instead).
