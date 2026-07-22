# Deferred Items

Per this slice's explicit OUT OF SCOPE list, the following remain deferred:

- Implementation of the selected next module (`app.engines.platform_notifications.provider_router`) — deferred to Slice 2F-18.
- All 10 non-selected modules — queued in `non-selected-module-queue.csv`, not implemented.
- Any new role, permission, or migration.
- Any pipeline merge (`Booking`/`ServiceBooking`, `field_ops.Job`/`ServiceJob`).
- Any `PartsRequest` or `quote_checklist` modification.
- `My Work` / `Next-Action` aggregation.
- Booking Exception Resolution.
- Frontend/UI work of any kind.
- Remediation of `readonly@demo-ac-services.local` (confirmed untouched).
- Application of Migration 144 (confirmed unapplied).
- A full-application (~960-route) missing-mutation discovery sweep (see `known-limitations.md`, `product-decisions-required.md`).
