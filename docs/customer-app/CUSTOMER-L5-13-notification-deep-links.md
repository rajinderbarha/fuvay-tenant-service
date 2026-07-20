# CUSTOMER-L5-13 — Notification Deep Links

## No Real Push Delivery Exists (Unchanged Finding From CUSTOMER-L5-12)

Re-confirmed this sprint: the backend's push channel remains a permanent
stub. No new push infrastructure was built or needed.

## Existing, Real, Already-Tested Infrastructure — Reused

Identical to CUSTOMER-L5-12's approach: `resolveNotificationIntent()`
(`navigation/notification-intent.ts`, unchanged since CUSTOMER-L5-01)
already validates any route with `notificationEnabled: true`. The
`tracking` route was already pre-configured `notificationEnabled: true`
by an earlier sprint (in anticipation of this one) — this sprint's only
change is promoting it to `productionEnabled: true` and backing it with a
real screen (`ServiceTrackingScreen`). No new deep-link validation code
was written.

## Consume-Once → Canonical Refetch

`ServiceTrackingScreen` always fetches fresh on mount (`staleTime: 0` on
both its underlying queries) — opening it via a resolved notification
intent automatically satisfies "fetch canonical state after open," exactly
as CUSTOMER-L5-12 already established for `BookingDetailScreen`.

## Never Renders Notification Payload as Canonical State

Same discipline as L5-12: this client never trusts free-form notification
body text as a status claim — the actual status shown always comes from
the real `GET /v1/customer/service-jobs/{jobId}/tracking` response
fetched after navigation.
