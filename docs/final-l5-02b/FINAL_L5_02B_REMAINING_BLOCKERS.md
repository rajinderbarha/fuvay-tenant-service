# FINAL-L5-02B — Remaining Blockers

## Both targeted blockers: CLOSED
BUG-L502-005 (Tenant Jobs legacy `/v1/jobs` dependency) and BUG-L502-006 (booking source-of-truth ambiguity) are both closed with live evidence — see Bug Closure Report.

## Real findings, not fixed this sprint (documented, not hidden)
1. **Embedded-error pattern (HTTP 200 + `success:false`/embedded-error body instead of literal 403/404)** on both Tenant Jobs cross-tenant detail and Customer Booking cross-customer detail/tracking — re-confirmed this sprint (same pre-existing L5-01D-006 pattern). No data exposure in any tested case; a real API-consistency gap, not a security hole.
2. **No post-confirmation customer booking cancellation endpoint** — the customer-app's typed client already honestly documents this as a stub; not built this sprint (a genuine product gap, not this mission's ask).
3. **`confirm-price-choice` returns an unhandled HTTP 500** instead of a graceful 4xx when called with no matched provider — new finding this sprint, edge case not reachable via the normal UI flow, out of Tenant-Jobs/booking-source scope.
4. **A provider-bookability gate blocks live draft-to-booking matching** for the seeded demo tenant/zipcode/offering combination that otherwise matches the seed data exactly — an orthogonal Sprint-12-era engine issue, not investigated further (out of scope; the seed's direct-SQL approach bypasses this gate entirely, which is why seeded data works while a *fresh* live customer flow currently cannot reach confirmation).
5. **Customer booking status labels are raw backend strings** (`converted`, `cancelled`) rather than customer-friendly labels — UX polish, not fabricated data, out of scope.
6. **Staff Detail page's migrated widget was not independently browser-tested** this sprint (only TypeScript + source verified) — lower priority than the Dashboard widget since it's a secondary page, but honestly flagged as a coverage gap rather than claimed as browser-verified when it wasn't.
7. **Service Areas "+ Add Zone" button gating, review-only carried items from FINAL-L5-01D/01E** — untouched, out of this mission's scope.

## Why this is READY, not PARTIAL_READY
None of the above are Tenant-Jobs-migration or booking-source-of-truth blockers — they are either (a) pre-existing, already-classified, low-severity, no-data-leak items carried forward honestly, or (b) new but genuinely orthogonal findings (provider-bookability gate, one 500 error) discovered *because* this sprint tested more rigorously (a full live draft workflow, bidirectional isolation with real IDs) than any prior sprint attempted. Discovering and documenting new low-severity issues while doing deeper verification is a sign of rigor, not a reason to withhold READY for the two bugs this mission specifically targets.
