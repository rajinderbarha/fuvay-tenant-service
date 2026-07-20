# Deferred Items

Per this slice's explicit OUT OF SCOPE list and the findings above, the
following remain deferred:

- Restricting technician chat visibility to assigned jobs only — see
  `product-decisions-required.md` item 1 (PRODUCT_DECISION_REQUIRED).
- Unifying thread-access error codes into a single privacy-safe 404 — see
  `product-decisions-required.md` item 2.
- Media attachment ownership validation — see
  `product-decisions-required.md` item 3.
- Adding `ForeignKey()` constraints to the 8 models in this module (would
  require a migration; migrations are forbidden this slice).
- Any of the 26 remaining unprotected tenant/provider mutation routes
  across the other 10 non-selected modules — queued in
  `remaining-module-queue-update.csv`, not implemented.
- Building a new notification channel, chat engine, WebSocket
  infrastructure, or attachment infrastructure (explicit OUT OF SCOPE).
- Any new role, permission, or migration.
- Any pipeline merge (`Booking`/`ServiceBooking`, `field_ops.Job`/`ServiceJob`).
- Any `PartsRequest` or `quote_checklist` modification.
- `My Work` / `Next-Action` aggregation; Booking Exception Resolution.
- Frontend/UI redesign of any kind (only backend dependency changes made;
  no frontend file touched — see `frontend-mobile-exposure-audit.md`).
- Remediation of `readonly@demo-ac-services.local` (confirmed untouched).
- Application of Migration 144 (confirmed unapplied).
- Live-database integration test runs (`*Live*` test classes) — no
  Postgres instance available in this environment; see
  `known-limitations.md` item 8 and `regression-report.md`.
