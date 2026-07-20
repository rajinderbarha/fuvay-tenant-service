# Deferred Items

Per this slice's OUT OF SCOPE list and the findings above, the following
remain deferred:

- Narrowing office (tenant_owner/staff) unclaimed-asset access —
  `product-decisions-required.md` item 1.
- A future migration giving `MediaAsset` a first-class claim column —
  `product-decisions-required.md` item 2.
- ServiceJob cancellation/completion access time-boxing —
  `product-decisions-required.md` item 3.
- Enforcement mechanism for future new `metadata_json` writers —
  `product-decisions-required.md` item 4.
- Aligning `_load`'s lifecycle filter with attach-time strictness
  (carried forward from 2F-18C).
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
