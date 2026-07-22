# Deferred Items

Per this slice's OUT OF SCOPE list and the findings above, the following
remain deferred:

- Attachment uploader-level authorization and message-level attachment
  binding — `product-decisions-required.md` items 1-2.
- Completed/cancelled Job technician access time-boxing —
  `product-decisions-required.md` item 3.
- `list_threads` live-assignment-aware technician listing —
  `product-decisions-required.md` item 4.
- Integrating `app/engines/media/access.py`'s own authorization semantics
  — `known-limitations.md` item 7.
- Any of the 26 remaining unprotected tenant/provider mutation routes
  across the other 10 non-selected modules — unchanged from 2F-18, queued
  in `remaining-module-queue-update.csv` (2F-18's copy, not modified here).
- Building new chat/notification/WebSocket/push/email/SMS/attachment-upload
  infrastructure (explicit OUT OF SCOPE).
- Any new role, permission, or migration.
- Any pipeline merge (`Booking`/`ServiceBooking`, `field_ops.Job`/`ServiceJob`).
- Any `PartsRequest` or `quote_checklist` modification.
- Frontend/UI redesign of any kind — no frontend file touched this slice.
- Remediation of `readonly@demo-ac-services.local` (confirmed untouched).
- Application of Migration 144 (confirmed unapplied).
- Live-database integration test runs (`*Live*` test classes) — no
  Postgres instance available in this environment.
- Beginning a second, unrelated module's authorization work.
