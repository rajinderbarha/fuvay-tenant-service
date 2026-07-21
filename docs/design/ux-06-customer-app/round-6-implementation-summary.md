# UX-06 Round 6 Implementation Summary

**Status: `CUSTOMER_APP_SOURCE_COMPLETE_BACKEND_INTEGRATION_BLOCKED`**
(see final-status-rationale.md / round-6-final-status.md).

## Scope (narrow, bounded, as instructed — no broader design work added)

1. Re-confirmed backend health.
2. Read `match_provider_and_price()` directly: **no fallback path** exists to
   book at the plain server price without an active `BargainRule` — Outcome
   B for the literal question. Also found a real, unresolved backend
   inconsistency (`auto_price_options_enabled=True` by default, but never
   checked by this function) — flagged, not fixed (backend, out of scope).
3. Per the brief's Item 4, searched for an existing already-configured
   combination via a read-only `SELECT` against `bargain_rules` — found one
   (`ac_installation`, same DEMO tenant). Used it to run the **complete
   canonical booking pipeline live, end-to-end, for the first time this
   phase**: real draft → brand → serviceability → price → provider match →
   tier selection → idempotent confirm → **real booking reference**
   (`BK-20260721-000001`) → real list insertion → real detail retrieval.
   Zero new shared platform policy created.
4. Corrected a real Round-1 architectural mistake discovered while wiring
   this up: `/v1/customer/bookings*` is the SAME ServiceBooking/ServiceJob
   pipeline (`home_service_assignment` engine), not a distinct pipeline as
   originally assumed — fixed `Booking` type + `BookingCard`/
   `BookingsListScreen`/`BookingDetailScreen` to the real field shape.
5. Ran a real Playwright browser session: the real booking created in step 3
   is now visible in Home's "Recent Bookings", the Bookings tab, and Booking
   Detail — and survives a full page reload. Strongest runtime evidence of
   the entire phase.
6. 4-run test stability sweep (1 clean-install + 3 consecutive): 46/46
   passing every time, zero flakiness. The Round 2 transient timeout
   explicitly classified as an unreproduced, not-fully-root-caused risk —
   not claimed fixed, not claimed nonexistent.
7. Re-confirmed `tsc --noEmit` clean (0 errors) and zero backend/other-app
   diff.
8. Final status reconciled across known-limitations.md,
   final-status-rationale.md, approval-gate.md.

## What remains (backend-owned, out of UX-06's frontend scope)

Exactly one item: `ac_repair` (the sole customer-catalog-visible offering)
needs either its own `BargainRule` or the catalog needs to surface
`ac_installation` (which already works) as a selectable offering. Both are
backend data changes.

## Commits this round

1. `a163c98` — bargain-optionality proof + full booking created via existing
   config, Booking-type architecture correction.
2. `97760a9` — Playwright proof of the real booking through production UI +
   4-run test stability sweep.
3. `bbd67ff` — known-limitations/final-status-rationale/approval-gate
   reconciled to the new status.
4. This commit — implementation summary + artifact manifest refresh.
