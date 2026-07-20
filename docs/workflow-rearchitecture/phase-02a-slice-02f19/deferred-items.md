# Deferred Items

Per this slice's OUT OF SCOPE list, the following remain deferred:

- Implementation of `app.engines.compliance.provider_router`'s
  authorization/ownership fixes — deferred to Slice 2F-20.
- All 9 non-selected modules — queued in `non-selected-module-queue.csv`,
  not implemented.
- Location and audit of the compliance export-generation worker —
  `product-decisions-required.md` item 3.
- Frontend/mobile caller investigation for the selected module —
  deferred to the implementation slice.
- Any new role, permission, or migration.
- Any pipeline merge.
- `PartsRequest`, `quote_checklist`, `Booking`/`ServiceBooking`,
  `field_ops.Job`/`ServiceJob` modification of any kind.
- `platform_notifications` and chat-media authorization modification of
  any kind (fully closed, not reopened).
- `My Work` / `Next-Action` aggregation; Booking Exception Resolution.
- Frontend/UI work of any kind.
- Remediation of `readonly@demo-ac-services.local` (confirmed untouched).
- Application of Migration 144 (confirmed unapplied).
- Live-database integration test runs.
