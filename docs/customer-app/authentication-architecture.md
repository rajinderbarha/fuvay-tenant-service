# Customer App — Authentication Architecture

## 1. Flow

OTP-only (phone + 6-digit code) against the real backend paths verified in
`CUSTOMER-L5-02-backend-contract-audit.md`:

```
OtpLoginScreen (single screen, two internal steps)
  enter-phone → authApi.sendOtp(phone, "phone_login")   POST /v1/auth/otp/send
  enter-otp   → authApi.verifyOtp(phone, otp, ...)      POST /v1/auth/otp/verify
                  → { access_token, refresh_token, user, tenant }
                  → persistSession() (secure-storage) → reevaluateStartup()
```

`useOtpFlow` (`features/auth/hooks/use-otp-flow.ts`) owns the two-step state
machine as component state — no navigation between the two steps, avoiding
passing non-serializable hook state through route params.

## 2. Session Model

`features/auth/domain/session.ts#CustomerSession` normalizes the backend's
`AuthUserProfile` (see contract audit) into the app's own shape. Screens
never see the raw backend fields.

## 3. Token Storage

Access + refresh tokens are written to `secure-storage.ts`
(`expo-secure-store`, CUSTOMER-L5-00) under
`SECURE_STORAGE_KEYS.accessToken`/`refreshToken` — **never** AsyncStorage.
This directly resolves CUSTOMER-L5-00 `known-gaps.md` item 1 ("auth token
still in AsyncStorage") for the new flow; the pre-existing `LegacyApp`
login flow is untouched and still uses AsyncStorage (documented, not
silently fixed — see `known-gaps.md`).

## 4. Session Store

`features/auth/state/session-store.ts` is a module-level store (same
pattern as CUSTOMER-L5-01's `remote-config-service.ts`/`startup-service.ts`)
with `getSessionState()`/`subscribeSession()`. It calls
`api/request-context.ts#setAuthTokenProvider` once
(`bindSessionToApiClient`) so `api-client.ts` (CUSTOMER-L5-00) resolves the
`Authorization` header from the session store without importing it
directly — the API client stays decoupled from how auth is implemented.

## 5. Startup Integration

`startup-service.ts`'s `loading-secure-session-placeholder` phase (declared
but a no-op in CUSTOMER-L5-01) now calls
`features/auth/state/session-bootstrap.ts#bootstrapSession()`:

1. Read persisted tokens (`hydrateSessionTokens`). None → `"guest"`.
2. Call `GET /v1/auth/me` to verify the access token is still valid and
   fetch a fresh profile.
3. On `401 unauthorized`: attempt one `POST /v1/auth/token/refresh`, retry
   `/me` once. Failure at either step → clear the session, `"guest"`.
4. On any other failure (network/timeout/server error): **do not** clear a
   possibly-still-valid local session — report the last-known status for
   this run only, so a briefly-unreachable backend doesn't force a logged-in
   customer back to guest.

The resulting status feeds `StartupRunInput.auth` (defaulting over the
previous hardcoded `"guest"`), which flows into
`route-guards.ts`/`startup-route-resolver.ts` exactly as CUSTOMER-L5-01
already wired it — no changes were needed to the guard/resolver logic
itself, only to what produces the `auth` value.

## 6. Re-evaluation on Session Change

`startup-service.ts#reevaluateStartup()` (new this sprint) re-runs the full
startup pipeline reusing the last known `connectivity`/`platform`. Called
from `useOtpFlow` after a successful login and from `useLogout` after
clearing the session — this is what makes the `authentication` system
route disappear/reappear correctly without every call site needing to know
startup's internal input shape.

## 7. Logout

`features/auth/hooks/use-logout.ts`: calls `POST /v1/auth/logout` (best
effort — a server-side failure does not block the local logout, since
clearing the local session is what actually protects the device), then
always clears the secure-stored tokens and re-evaluates startup.

## 8. Placeholder Compliance (CUSTOMER-L5-01 §28)

- No fake login success, no fake tokens, no mock customer accounts — every
  session comes from a real `/v1/auth/otp/verify` (or subsequent `/me`)
  response.
- `AuthPlaceholderState` values `"expired"`/`"locked"` are not yet produced
  by this sprint's code (only `"unknown"`/`"guest"`/`"authenticated"` are
  reachable) — the backend does return an `ACCOUNT_LOCKED` error category
  for the email+password path, but the OTP path this sprint uses doesn't
  hit that branch. Tracked in `known-gaps.md`.
- Deferred deep-link destinations requiring auth are handled entirely by
  CUSTOMER-L5-01's existing `pending-deep-link-store.ts` — no new code was
  needed; a destination deferred before login automatically becomes the
  route `resolveInitialRoute` picks once `reevaluateStartup()` runs
  post-login (subject to its 5-minute TTL).
