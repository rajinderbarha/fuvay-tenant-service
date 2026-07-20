# CUSTOMER-L5-12 — Notification Deep Links

## No Real Push Delivery Exists (Confirmed, Both Research Passes)

`app/engines/platform_notifications/channel_providers.py`'s push channel
(`PushNotificationProviderStub`) is a permanent stub — `deliver()` always
returns `success=False, failure_code="PROVIDER_NOT_CONFIGURED"`. No
device-token registration model exists anywhere in the backend. This
sprint therefore builds **no** "enable notifications"/device-token
registration UI — there is no real channel for such a registration to
matter to.

## Existing, Real, Already-Tested Client Infrastructure — Reused, Not Duplicated

`mobile/customer-app/src/navigation/notification-intent.ts`
(`resolveNotificationIntent`) already exists from CUSTOMER-L5-01, with its
own tests (`notification-intent.test.ts`), and already:

- Requires the target route to exist in `ROUTE_REGISTRY` **and** have
  `notificationEnabled: true`.
- Rejects expired intents (`expiresAt`).
- Deduplicates by `notificationId` (consume-once).
- Validates every param value against a safe character-class regex.

This sprint's only change is that `bookingDetail`'s route-registry entry
(already pre-configured `notificationEnabled: true` by an earlier sprint,
in anticipation of this one) is now backed by a real, production screen
(`BookingDetailScreen`) — no new deep-link infrastructure was built, per
§44's "Use existing infrastructure. Do not add duplicate real-time
systems."

## Consume-Once → Canonical Refetch (Real, Already Guaranteed)

Because `BookingDetailScreen` always fetches fresh on mount
(`staleTime: 0` on both its detail and tracking queries — `cache-policy.md`),
opening the screen via a resolved notification intent automatically
satisfies §44's "fetch canonical booking after open" requirement — there
is no separate "notification-triggered refresh" code path to build; the
screen's normal mount behavior already is that refresh.

## Never Renders Notification Text as Status

`resolveNotificationIntent`'s output is only ever a validated
`{routeId, params}` pair — this client never receives or renders
free-form notification body text as a status claim; the actual status
shown always comes from the real `GET /v1/customer/bookings/{id}`
response fetched after navigation, never from whatever a (currently
non-existent) push payload might have said.

## What Would Be Needed for Real Push Delivery (Not This Sprint's Scope)

A real backend push channel (replacing the stub), a device-token
registration endpoint, and a `PUSH_TOKEN_REGISTERED`-type mobile-side
registration call. None of this exists today; building the client-side
piece now would be dead code with no real channel to receive from —
documented as a real, disclosed gap in `known-gaps.md`.
