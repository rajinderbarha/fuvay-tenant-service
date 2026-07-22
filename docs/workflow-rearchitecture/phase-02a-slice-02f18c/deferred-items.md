# Deferred Items

Per this slice's OUT OF SCOPE list and the findings above, the following
remain deferred:

- A schema change (migration) to give `MediaAsset` a first-class
  thread/Job lineage column instead of the `metadata_json` convention —
  `product-decisions-required.md` item 3.
- Narrowing unclaimed `chat_attachment` asset visibility further —
  `product-decisions-required.md` item 1.
- Aligning `_load`'s lifecycle filter with attach-time strictness —
  `product-decisions-required.md` item 2.
- Extending retrieval-privacy unification to every media context —
  `product-decisions-required.md` item 4.
- Any of the 26 remaining unprotected tenant/provider mutation routes
  across the other 10 non-selected modules — unchanged, queued in
  `remaining-module-queue-update.csv` (copied from prior slices, not
  modified).
- Building new media upload/versioning/storage/signed-URL infrastructure,
  a new message-attachment table, or any migration (explicit OUT OF
  SCOPE).
- Any new role, permission, or alias.
- Any pipeline merge (`Booking`/`ServiceBooking`, `field_ops.Job`/`ServiceJob`).
- Any `PartsRequest` or `quote_checklist` modification.
- Frontend/UI redesign of any kind — no frontend file touched this slice.
- `My Work` / `Next-Action` aggregation; Booking Exception Resolution.
- Remediation of `readonly@demo-ac-services.local` (confirmed untouched).
- Application of Migration 144 (confirmed unapplied).
- Live-database integration test runs (`*Live*` test classes).
- Beginning a second, unrelated module's authorization work.
