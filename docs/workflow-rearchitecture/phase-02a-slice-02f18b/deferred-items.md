# Deferred Items

Per this slice's OUT OF SCOPE list and the findings above, the following
remain deferred:

- A schema change (migration) to give `MediaAsset` explicit Job/thread/
  message lineage columns — `product-decisions-required.md` item 1.
- Narrowing `MediaAccessService`'s technician tenant-wide view policy —
  `product-decisions-required.md` item 2 (would require modifying
  `app/engines/media/access.py`, app-wide blast radius).
- Unifying the media engine's own retrieval-path error privacy —
  `product-decisions-required.md` item 3.
- Sharing revocation state between chat-thread participation and generic
  media access — `product-decisions-required.md` item 4.
- Wiring up `staff_send_message`'s dropped `media_ids` field —
  `product-decisions-required.md` item 5.
- Adding a media field to `customer_router.py`'s `SendMessageIn`.
- Any of the 26 remaining unprotected tenant/provider mutation routes
  across the other 10 non-selected modules — unchanged, queued in
  `remaining-module-queue-update.csv` (copied from 2F-18, not modified).
- Building new media upload/versioning infrastructure, a new
  message-attachment model, or any migration (explicit OUT OF SCOPE).
- Any new role, permission, or alias.
- Any pipeline merge (`Booking`/`ServiceBooking`, `field_ops.Job`/`ServiceJob`).
- Any `PartsRequest` or `quote_checklist` modification.
- Frontend/UI redesign of any kind — no frontend file touched this slice.
- `My Work` / `Next-Action` aggregation; Booking Exception Resolution.
- Remediation of `readonly@demo-ac-services.local` (confirmed untouched).
- Application of Migration 144 (confirmed unapplied).
- Live-database integration test runs (`*Live*` test classes).
- Beginning a second, unrelated module's authorization work.
