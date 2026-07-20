# CUSTOMER-L5-14 — Notifications & Deep Links

## Real notification events found (independent background pass confirmed)

`platform_notifications/event_registry.py` (lines 108–123) defines real
quote lifecycle events: `EVT_QUOTE_SENT`, `EVT_QUOTE_APPROVED`,
`EVT_QUOTE_REJECTED`, `EVT_QUOTE_REVISION`. Whether these are actually
*emitted* by `quote_service.py`'s own methods (vs. only registered as
possible event types) was not exhaustively re-traced this sprint beyond
confirming the registry entries exist — if not wired to emission, a
customer would not receive a push notification when a quote is sent to
them, only discovering it by opening the app. This client does not
fabricate a notification-driven "you have a new request" banner as a
result; it relies entirely on the existing pull-based flow (booking
detail → "Additional approvals" button → this screen).

By contrast, `execution`'s `PartsRequest` system has **no** corresponding
`EVT_PARTS_*` events at all (grep across the notifications engine
confirmed zero matches) — another reason it could not have been this
sprint's real target even if its customer-decision dead-end were fixed.

## Deep link

`quoteDecision` route registered with `deepLinkEnabled: false`,
`notificationEnabled: true` (`route-registry.ts`) — consistent with
`tracking`'s own registration in CUSTOMER-L5-13: reachable if a push
notification payload names it (once/if real emission is confirmed and a
notification-tap handler is wired to it in a future sprint), but not
exposed as a public universal-link URL, since there's no product
requirement for a customer to share this screen externally.

## Route params

`{ bookingId: BookingId }` — identical shape to `Tracking`, resolving to
the real `job.id` internally via the same reused
`booking-confirmation`'s `useBookingDetail`, never taking a raw `quoteId`
or `jobId` directly from a deep link (avoids trusting an external,
unvalidated identifier — the booking-ownership check on
`useBookingDetail` remains the sole access gate, matching every previous
sprint's deep-link security posture).
