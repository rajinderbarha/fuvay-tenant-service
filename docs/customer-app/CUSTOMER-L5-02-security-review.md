# CUSTOMER-L5-02 — Security Review

Static/code-level review. No penetration testing or live-backend fuzzing
was performed (no running backend instance available in this environment
— see `CUSTOMER-L5-02-runtime-evidence.md`).

## Account Enumeration

`POST /v1/auth/otp/send` returns a generic `{message, otp_hint?}` — reading
`service.py#send_phone_otp`, the response shape is identical whether or not
the phone number belongs to an existing account (an OTP is generated and
returned/sent either way; the "no account found" error only surfaces later,
at **verify** time, if `_get_user_by_phone` finds nothing after OTP
success). This is a **backend behavior**, not a client mitigation — the
client's `useOtpFlow` does not add any extra message-neutralization since
none is needed for the request step. At verify time, an account-not-found
error IS distinguishable (`NOT_FOUND` vs `UNAUTHORIZED` for wrong-code) —
this is a real, minor enumeration surface in the backend's own contract,
outside this sprint's ability to fix (would require a backend change).
Documented, not silently accepted as fine.

## OTP Security

- Never logged: grep confirms no `logger.*otp` call anywhere in
  `features/auth/` passes the OTP value itself — only counts/categories.
- Never persisted: `useOtpFlow`'s `otp` state is plain React `useState`,
  cleared by `reset()` and naturally cleared on unmount; never touches
  `preferenceStorage`/`secureStorage`.
- `devOtpHint` (the backend's non-Twilio dev fallback) is gated by
  `__DEV__` at the point it's read from the response (`useOtpFlow.ts`) — it
  is `null` in any production build regardless of what the backend returns,
  so even a misconfigured production backend echoing a hint could not reach
  the UI.
- Client never verifies OTP locally — every code goes to
  `POST /v1/auth/otp/verify`; there is no local digit-comparison anywhere.

## Token Storage

`secureStorage` (`expo-secure-store`, CUSTOMER-L5-00) — access + refresh
tokens only, never `AsyncStorage`/`preferenceStorage`. Verified by
`session-store.test.ts` reading back through the real (mocked-native)
`secure-storage.ts` adapter, not a bypassed test double.

## Refresh Safety

- Single-flight: `auth-refresh-coordinator.test.ts` proves two concurrent
  `handleUnauthorized()` calls trigger exactly one
  `authApi.refreshToken` call.
- No infinite loop: `api-client.ts`'s `requestWithRetry` passes
  `allowUnauthorizedRetry=false` on the retried call — a second 401 after
  the retry propagates immediately rather than triggering another refresh
  attempt (`api-client.test.ts` "does not retry a second time").
- `skipAuth` requests (OTP send/verify, register, refresh itself) never
  invoke the unauthorized handler — verified by `api-client.test.ts`.

## Route Guarding / Deep-Link Bypass

Unchanged from CUSTOMER-L5-01 (`route-guards.ts`, `deep-link-resolver.ts`)
— this pass did not modify guard logic. A deep link to an
`access: "authenticated"` route while guest still defers to
`pending-deep-link-store.ts` rather than bypassing the check (existing
CUSTOMER-L5-01 test coverage, re-confirmed passing this pass: 290/290).

## Cross-Customer Isolation

Enforced **server-side**: `service.py#revoke_session` explicitly checks
`session.user_id != requesting_user_id` and raises `PERMISSION_DENIED`.
The client does not re-implement this check (correctly — frontend checks
cannot substitute for backend enforcement per CUSTOMER-L5-02 §41).

Client-side cache isolation on account switch: `useSessions`'s and
`profile-queries.ts`'s TanStack Query cache keys have no per-customer
dimension, so a stale cached result from Customer A could theoretically
render before a refetch completes if Customer B logs in on the same device
without a full app restart. **Closed this pass**: `useLogout` and
`useLogoutAll` both call `queryClient.clear()` (CUSTOMER-L5-00's shared
query client) immediately after clearing the session — every server-state
query cache (profile, sessions, and any future customer-specific data) is
wiped on logout, so no next-login's screen can render leftover data from
the previous customer. Not covered by an automated test this pass (the
existing `use-logout-all.test.ts` verifies session clearing, not cache
clearing specifically — see known-gaps).

## Marketplace Mismatch

`request-context.ts#setRequestTenantId` (CUSTOMER-L5-00) exists but is
never called by anything in `features/auth/` this sprint — there is no
multi-marketplace concept exercised by the current single-marketplace
backend deployment this environment has access to, so this could not be
verified end-to-end. Documented as UNVERIFIED, not claimed as tested.

## Logging Redaction

`observability/logger.ts`'s redaction (CUSTOMER-L5-00,
`redaction.test.ts`) already matches `token|otp|password|secret|session`
key-name patterns — `auth_session_refresh_succeeded`/`_failed` log calls in
`auth-refresh-coordinator.ts` pass no metadata object at all (not even a
redacted one), so there is nothing to leak by construction.

## Production Debug / Mock Login

Grep confirms no hardcoded OTP, no hardcoded customer, no mock-login code
path anywhere in `features/auth/` — every session originates from a real
`/v1/auth/otp/verify` (or subsequent `/me`/`/token/refresh`) response.

## Known Open Risks (not closed this pass)

1. Query-cache customer isolation on account switch (see "Cross-Customer
   Isolation" above) — `useLogout`/`useLogoutAll` do not call
   `queryClient.clear()`.
2. No `X-Tenant-Id` binding exercised (single-marketplace environment).
3. Backend allows direct phone-number change with no re-verification —
   mitigated client-side by rendering the field read-only, but the backend
   endpoint itself remains reachable to any client that chooses to call it
   directly (out of this app's control).
