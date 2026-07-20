# CUSTOMER-L5-15 — Tracking Cleanup Contract

## Finding

No cancellation or reschedule action exists that this client can
trigger, so there is no client-side moment requiring tracking-session
cleanup (ending an active `ServiceTrackingScreen` session, clearing
coordinates/route/ETA/contact) as a *consequence of this sprint's own
work*. CUSTOMER-L5-13's `ServiceTrackingScreen` already has no live
session/websocket to clean up in the first place — it is a stateless,
always-refetchable, non-map, milestone-based screen with `staleTime: 0`
(see `CUSTOMER-L5-13-tracking-architecture.md`), not a persistent
connection that could leak state across a cancellation.

## What the backend does NOT do

Confirmed (background research pass): `execution/home_service_service.py`
's `cancel_job` never touches `ServiceJobExecutionEvent`,
`ServiceJobMediaUpload`, `PartsRequest`, or `ServiceJobQuote` rows beyond
writing its own single cancellation event. If a customer were somehow
viewing `ServiceTrackingScreen` for a job a provider cancels mid-session,
this client's existing `staleTime: 0` + refetch-on-mount/focus pattern
would show the new `cancelled` status on the next natural refetch — no
special-cased cleanup code is needed or added, since the screen was
never a stateful, cleanup-requiring resource to begin with.

## Conclusion

No code changes were needed or made for tracking cleanup this sprint —
the architecture established in CUSTOMER-L5-13 already satisfies this
requirement by construction (no persistent client-held tracking state
exists to leak).
