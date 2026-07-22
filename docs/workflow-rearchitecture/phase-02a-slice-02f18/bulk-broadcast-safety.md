# Bulk/Broadcast Safety

## Finding: not applicable — no bulk or broadcast capability exists

`provider_router.py` (and `staff_notif_router`/`staff_chat_router` in the
same file) expose no route that accepts a list of recipients, a
tenant-wide/broadcast flag, or any multi-recipient targeting mechanism.
`mark_all_read` is the only "all X" operation on this router, and it is
scoped entirely to the caller's own notifications (`user_id == caller`) —
not a broadcast to other users, a bulk operation against other people's
data.

Classified `FALSE_POSITIVE_NON_MUTATION` for this workstream: there is
nothing here to test against the bulk/broadcast test matrix (mixed-tenant
recipient list, foreign staff recipient, etc.) because no such input
surface exists. This was confirmed by direct route enumeration (all 20
routes reviewed, see `provider-router-final-route-inventory.csv`), not
assumed from the router's name.

Broadcast/campaign notification sending exists conceptually in
`NotificationEventRegistry`/`fire_event`, but that is invoked internally by
other engines (booking, quote, invoice, etc.) — never as an HTTP mutation
reachable from this router, and out of this slice's scope (per mission:
"Do not build a new notification channel").
