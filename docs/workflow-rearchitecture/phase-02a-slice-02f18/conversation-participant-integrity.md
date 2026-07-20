# Conversation Participant Integrity

## Creator authority
`ChatThreadService.create_thread` seeds participants server-side only:
the caller (`actor_user_id`/`actor_type`) plus, when `tenant_id` is known,
the tenant owner and the record's assigned staff (`_provider_participants`)
— never from a client-supplied participant list (`provider_router.py` and
`staff_router.py` expose no `participants` field on any request schema).

## Tenant mixing
Fixed this slice: a provider/staff caller can no longer attach a thread to
a record belonging to a different tenant (see
`implementation-summary.md` finding 3), which is the only way this module
could previously have produced a thread mixing two tenants' participants.

## Internal vs. customer exposure
`visibility` (now validated, see `message-mutation-integrity.md`) is the
only mechanism separating provider-internal content from customer-facing
content within a shared thread — there is no separate "internal-only
thread" concept; visibility is per-message, not per-thread.

## Participant addition/removal
No route in `provider_router.py`/`staff_router` (or `customer_router.py`)
exposes participant add/remove — `ChatThreadService.add_participant` exists
but is only called internally during thread creation. Nothing in this slice's
scope needed to change here; documented as `TECHNICIAN_NOT_SUPPORTED`-style
absent capability rather than assumed.

## Duplicate participants
`_add_participant` already dedupes on `(thread_id, user_id)` via an
existence check before insert (pre-existing, unchanged) — confirmed by
direct code read, not modified this slice.

## Removed-participant access
No removal capability exists (see above), so this is not reachable in the
current codebase — not a gap introduced or left open by this slice, simply
absent functionality.
