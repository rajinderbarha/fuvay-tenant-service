# Customer App — Session Lifecycle

## States

`SessionStatus`: `"unknown"` (not yet hydrated) → `"guest"` (no valid
session) | `"authenticated"` (valid session + profile).

## Lifecycle Events

| Event | Trigger | Effect |
|---|---|---|
| Cold start | App launch | `startup-service.ts` runs `bootstrapSession()` once during `loading-secure-session-placeholder` |
| OTP verified | `useOtpFlow#verifyOtp` success | `persistSession()` (secure storage + in-memory state) → `reevaluateStartup()` |
| Logout | `useLogout#logout` | `POST /v1/auth/logout` (best effort) → `clearSession()` → `reevaluateStartup()` |
| Access token expired mid-session | `/v1/auth/me` returns 401 during bootstrap | One `POST /v1/auth/token/refresh` attempt; failure clears the session |
| Profile edited | `useUpdateProfile` mutation success | `updateSessionProfile()` patches the in-memory session from the `PUT /v1/auth/me` response — no re-fetch needed |
| App resume | `AppState` → `active`, ≥60s since last check (CUSTOMER-L5-01) | `retryStartup()` re-runs `bootstrapSession()`, re-verifying the session is still valid |

## What Is Persisted vs. In-Memory

- **Secure storage** (`expo-secure-store`): `accessToken`, `refreshToken`
  only. Nothing else — no profile fields, no PII, in secure storage.
- **In-memory only** (`session-store.ts` module state, lost on app kill):
  the full `CustomerSession` (name, phone, email, etc.) — re-derived from
  `/v1/auth/me` on every cold start rather than cached to disk, so a stale
  cached name/phone can never be shown after an out-of-band backend change.

## Concurrency / Race Protection

`bootstrapSession()` only runs inside `startup-service.ts`'s sequence-ID-
guarded phase machinery (CUSTOMER-L5-01), so a superseded run's session
result is discarded exactly like any other stale phase result — no separate
mutex was needed in the auth layer itself.

## Multi-Device / Multi-Session

`POST /v1/auth/logout` revokes only the current session
(`user.jti`/`session_id`); `POST /v1/auth/logout-all` (revoke every
session) exists on the backend but is not surfaced in the customer app this
sprint (no "sign out everywhere" UI) — tracked in `known-gaps.md`.

## Clearing Customer-Specific Data on Logout

This sprint's session store itself holds no cache beyond the in-memory
session object, so `clearSession()` is sufficient. Once a later sprint adds
customer-specific TanStack Query caches (bookings, recent activity, etc.),
`useLogout` must also call `queryClient.clear()` (or a scoped
`removeQueries`) — tracked in `known-gaps.md` since no such cached data
exists yet to clear.
