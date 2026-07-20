# Selected Next Module — Explicit Boundaries

## In scope for Slice 2F-18 (the future implementation slice)
- The 10 mutation routes listed in `selected-next-module-route-list.csv`.
- Adding an existing, already-proven dependency (`require_owner_or_office_staff_mutation`, `require_staff_or_above_mutation`, or an equivalent already-existing dependency — the exact choice is 2F-18's own decision, informed by caller-evidence investigation) to each.
- Any DIRECTLY CONNECTED object-ownership gap found in the underlying `ChatThreadService`/`ChatMessageService`/`NotificationService` methods these routes call (mirroring the "close directly connected bypasses only" pattern established throughout this initiative).

## Explicitly out of scope for Slice 2F-18 (unless its own mission states otherwise)
- `app/engines/platform_notifications/customer_router.py` (separate persona, separate file).
- `app/engines/platform_notifications/admin_router.py` (platform-admin persona, separate file).
- Read/GET routes in `provider_router.py` (list threads, get messages, audit log reads) — unless a read-privacy gap is directly connected to a mutation gap being fixed.
- Any new role, permission, or migration.
- Any pipeline merge.
- Frontend/mobile changes.
- Any other module in `remaining-tenant-mutation-routes.csv` — those remain queued (`non-selected-module-queue.csv`), not touched by 2F-18.

## Why this boundary is coherent
Mirrors every successful prior slice's boundary discipline in this initiative (Booking, field_ops, quote_checklist) — one file, one engine, one persona-pair (provider+staff), a clear "this is what's broken, this is what's not touched" line.
