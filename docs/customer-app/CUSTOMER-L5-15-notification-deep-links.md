# CUSTOMER-L5-15 — Notification Deep Links

## Finding

The active `platform_notifications` `EVT_*` registry
(`app/engines/platform_notifications/event_registry.py`) defines **zero**
cancellation/reschedule events — confirmed by an independent background
grep pass finding no `EVT_*CANCEL*`/`EVT_*RESCHEDULE*` imports anywhere
in that file. An older, apparently-unused `app/engines/notification/`
engine has `"booking_cancelled"`/`"booking_rescheduled"` seed-data
strings, but no confirmed real emitter anywhere in the codebase calls
them.

The only place any cancellation/reschedule event is actually published
is the legacy, disconnected `booking` engine's raw event-bus calls
(`"booking.cancelled"`, `"booking.reschedule_requested"`,
`"booking.rescheduled"`) — irrelevant to the real customer app, since
that engine never processes a real customer's booking (see
`baseline-verification.md`).

## This client's implementation

No new notification deep link is added this sprint. No route reservation
(`route-registry.ts`) is created for a cancellation/reschedule
result/pending screen, since no such screen exists to deep-link into.

## What a correct backend fix would need

Real `EVT_JOB_CANCELLED`/`EVT_BOOKING_CANCELLED`/`EVT_RESCHEDULE_*`
events registered in `platform_notifications`, actually emitted from
`execution/home_service_service.py`'s `cancel_job` (once a real
customer-facing cancel exists), before any client-side deep link work
would have anything real to point to.
