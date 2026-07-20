# CUSTOMER-L5-10 — Known Gaps

## P0

1. **No live runtime certification** — see `CUSTOMER-L5-10-runtime-evidence.md`.
   Identical constraint to every previous sprint's own P0 gap.

## P1

2. **This backend has no bargain-specific rate limiting or attempt
   capping anywhere** — a real, disclosed backend-side gap (not this
   sprint's frontend code to fix). A customer could, in principle, call
   `match-and-price`/`confirm-price-choice` repeatedly with no
   server-side throttling. See `attempt-and-rate-limit-policy.md`.
3. **No counteroffer, bargain-session, or multi-round negotiation exists
   anywhere in this backend** — the entire real "bargaining" capability is
   a single tier pick (`low`/`mid`/`high`), confirmed via exhaustive
   research including the decisive `MANUAL_BARGAIN_RULES_ENABLED = False`
   feature-flag finding. See `counteroffer-contract.md`. This is the
   sprint's most consequential finding, continuing the exact pattern of
   L5-07's "no real SLA engine," L5-08's "no candidate list," and
   L5-09's "no real city-tier influence in the used flow."
4. **`confirm-price-choice`'s request body is unvalidated raw JSON** — a
   missing `price_tier` key raises an unhandled `KeyError` server-side
   rather than a clean 422 (flagged again this sprint, unchanged from
   L5-09's known-gaps.md, now actually reachable by this sprint's code —
   though this client always sends a well-formed body, so the gap is
   never triggered by any real user action).
5. **No component/render tests** for `BargainScreen` — same,
   now-consistent-across-ten-sprints deprioritization pattern.
6. **No negotiated-price-specific expiry exists** — only the generic
   24-hour draft `expires_at`. A customer could theoretically confirm a
   tier choice, wait an extended period, and proceed to booking review
   with a "stale" (but never actually invalidated) negotiated price — the
   backend has no mechanism to detect or prevent this within this flow.

## P2

7. **`booking_summary` is not synchronized to the shared draft cache** —
   a deliberate scope decision (`cache-policy.md`), since no other screen
   currently reads it. A future sprint building a screen that needs this
   data (e.g., a booking-summary card elsewhere) will need to either add
   it to `bookingDraftSchema` or fetch it via `/summary` directly.
8. **No analytics events actually wired to a vendor** — same
   now-ten-sprints-running gap: no analytics SDK is integrated in this
   app at all; `logger.*` calls are structured logs only.
9. **`bargain-api.ts`/`use-bargain.ts` have no dedicated unit tests** —
   consistent with the established, repo-wide pattern that thin API
   wrappers and hook-composition layers over already-tested pure
   functions are not independently tested.
10. **No genuine "change selection then re-confirm with a different
    tier" round trip was tested against a live backend** — the
    `changeSelection` real-repeatability claim rests on source-code
    reading (`contract-matrix.md`'s point 4), not an observed live
    re-confirmation. See `runtime-evidence.md`.

## P3

11. **Punjabi/Hindi translations of the new `bargain.*` keys were written
    by this sprint and have not been reviewed by a native-speaking
    product reviewer** — same disclosed caveat pattern as every previous
    sprint's localization additions.
12. **If `MANUAL_BARGAIN_RULES_ENABLED` is ever turned on**, this sprint's
    `BargainState`/schema would need real, additive extension to support
    counteroffers/attempts/rate limits — documented in
    `counteroffer-contract.md`'s "If a Future Sprint Re-Enables Manual
    Bargaining" section as a forward-looking note, not a current defect.
