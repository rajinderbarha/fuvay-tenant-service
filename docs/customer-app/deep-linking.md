# Customer App — Deep Linking

## 1. Supported Schemes / Hosts

- Custom scheme: `serviceos://` (registered as `app.json`'s `expo.scheme`
  this sprint — it was previously unset).
- Universal link host: `app.serviceos.in` — **placeholder, not a verified
  real domain**. No `applinks`/`assetlinks` association files exist in this
  repository, and iOS Associated Domains / Android App Links were not
  configured natively this sprint (see known-gaps.md — this requires a real
  domain the org controls plus native entitlements/manifest changes this
  sprint didn't have grounds to invent).
- `expo.dev`-issued Expo Go development URL (`Linking.createURL("/")`) —
  automatically included by `linking-config.ts` for local development only.

## 2. Supported Path Structure

Only paths matching a compiled entry in
`deep-link-validator.ts#PATH_ROUTES` resolve to anything; every other path
is rejected as `unknown_path`.

| Path | Route id | Params |
|---|---|---|
| `` (root) | `baselineLanding` | — |
| `home` | `home` | — |
| `search` | `search` | — |
| `services/:serviceId` | `serviceDetails` | `serviceId` |
| `bookings` | `bookingsList` | — |
| `bookings/:bookingId` | `bookingDetail` | `bookingId` |
| `rewards` | `rewards` | — |
| `support` | `support` | — |
| `legal/terms` | `legalTerms` | — |
| `legal/privacy` | `legalPrivacy` | — |

A path only resolves if the matched route is also `deepLinkEnabled: true`
in `route-registry.ts` — the table above and the registry must agree, or
the link is rejected even if the path matches.

## 3. Parameter Validation

Every extracted param must match `^[A-Za-z0-9_-]{1,64}$` — no length
overrun, no punctuation beyond `-`/`_`, no script-like content. Params
become the branded ID types (`ServiceId`, `BookingId`, ...) only after this
runtime check; there is no path where an unvalidated string becomes a
typed param.

## 4. Security Filters

`deep-link-validator.ts` (see `docs/customer-app/CUSTOMER-L5-01` spec §31)
implements, in order: unknown scheme/host rejection, a query-key allowlist
(`campaign`, `ref`, `exp`, `src` only — everything else is
`unexpected_query_field`), a sensitive-key-pattern rejection
(`token|otp|password|secret|session|auth|access_key|api_key` — even if the
key were somehow allowlisted), a nested-redirect rejection (any query value
containing `http://`/`https://` is rejected, preventing open-redirect-style
abuse), expiry checking (`exp` query param, Unix seconds), and
cross-marketplace rejection when a `marketplaceId` is present and mismatched.
`deep-link-parser.ts` separately enforces a 2048-character URL length cap
and rejects unparseable strings.

## 5. Deferred Flow

`deep-link-resolver.ts#resolveDeepLink` runs the full pipeline (parse →
validate → `route-guards.ts#evaluateRouteAccess`). If the guard result is
`deny-auth` or `deny-not-ready`, the destination is stored in
`pending-deep-link-store.ts` (memory-only, consume-once, 5-minute TTL) via
`setPendingDestination`, and `startup-route-resolver.ts` picks it up on the
next `resolveInitialRoute` call once auth/onboarding are resolved. Any
other guard denial is a hard rejection — deep links do not get a second
chance to "become" a system-gate bypass.

## 6. Notification Intent Flow

Push registration/inbox are not implemented this sprint. The contract
(`notification-intent.ts#NotificationNavigationIntent` /
`resolveNotificationIntent`) exists for a future notification handler to
call: it never trusts `intent.route` as a literal navigable string — the
value must match a compiled `RouteId` **and** that route must have
`notificationEnabled: true`. Consume-once dedup by `notificationId`
prevents replay; `expiresAt` is honored.

## 7. Native Configuration

- `app.json`: `expo.scheme = "serviceos"` (added this sprint).
- No `ios.associatedDomains` or `android.intentFilters` entries exist —
  universal/app links are **not yet functional end-to-end**, only the
  custom-scheme path is real today. This is documented, not silently
  claimed as done.
- `linking-config.ts` deliberately does **not** use React Navigation's
  declarative `config.screens` path-to-route mapping (which would navigate
  straight from a raw URL with zero validation) — `getInitialURL`/
  `subscribe` only surface the raw URL for React Navigation's own internal
  bookkeeping; actual routing always goes through the validated resolver
  pipeline above.

## 8. Testing Instructions

```bash
# Simulator/emulator, dev client running:
npx uri-scheme open "serviceos://bookings/abc-123" --ios
npx uri-scheme open "serviceos://bookings/abc-123" --android
```

Automated coverage: `deep-link-parser.test.ts` (6 tests),
`deep-link-validator.test.ts` (10 tests), `pending-deep-link-store.test.ts`
(4 tests), `notification-intent.test.ts` (6 tests),
`startup-route-resolver.test.ts` (priority-ordering coverage including
"deep link cannot bypass maintenance/mandatory-update").
