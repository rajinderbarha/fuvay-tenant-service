# Deferred Items

Per this slice's OUT OF SCOPE list and the findings above, the following
remain deferred:

- Awareness monitoring for the static `thread.customer_id` gate —
  `product-decisions-required.md` item 1.
- A dedicated, granular `replace`-specific media permission —
  `product-decisions-required.md` item 2.
- Narrowing same-tenant unrelated staff replacement authority further —
  `product-decisions-required.md` item 3.
- A live-environment two-session concurrent-claim integration test —
  `product-decisions-required.md` item 4.
- Any of the 26 remaining unprotected tenant/provider mutation routes
  across the other 10 non-selected modules — unchanged, queued in
  `remaining-module-queue-update.csv`.
- Building new media upload/storage/signed-URL infrastructure, a new
  message-attachment table, or any migration (explicit OUT OF SCOPE).
- Any new role, permission, or alias.
- Any pipeline merge (`Booking`/`ServiceBooking`, `field_ops.Job`/`ServiceJob`).
- Any `PartsRequest` or `quote_checklist` modification.
- Frontend/UI redesign of any kind — no frontend file touched this slice.
- `My Work` / `Next-Action` aggregation; Booking Exception Resolution.
- Remediation of `readonly@demo-ac-services.local` (confirmed untouched).
- Application of Migration 144 (confirmed unapplied).
- Live-database integration test runs (`*Live*` test classes) and true
  concurrent-transaction testing (no live Postgres instance available).
- Beginning a second, unrelated module's authorization work.
