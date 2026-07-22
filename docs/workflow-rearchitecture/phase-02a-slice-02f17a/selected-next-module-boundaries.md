# Selected Next Module — Explicit Boundaries (carried forward from Slice 2F-17, re-confirmed)

Unchanged from Slice 2F-17's `selected-next-module-boundaries.md`. The full-application sweep performed this slice confirmed (rather than altered) these boundaries:

## In scope for Slice 2F-18
- The 10 mutation routes in `selected-next-module-route-list.csv`.
- Adding an already-proven dependency to each.
- Any DIRECTLY CONNECTED object-ownership gap in the underlying `ChatThreadService`/`ChatMessageService`/`NotificationService` methods.

## Explicitly out of scope for Slice 2F-18
- `customer_router.py`/`admin_router.py` in the same engine (separate personas, separate files) — this slice's duplicate/alternate-mount audit confirmed no same-record overlap exists between them and the 10 selected routes.
- Read/GET routes in `provider_router.py`.
- Any new role, permission, or migration.
- Any pipeline merge.
- Frontend/mobile changes.
- Every other module in `application-wide-module-queue.csv`.
