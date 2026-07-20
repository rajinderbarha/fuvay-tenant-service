# CUSTOMER-L5-02 — Authentication Architecture (Deepened Pass)

Supersedes/extends `authentication-architecture.md` (first pass) with the
hardening added in this pass: a single-flight refresh coordinator wired
into the canonical API client, session/device management, and a formal
(derived, not stored) `AuthState` vocabulary.

## State Machine

`session-store.ts`'s `SessionStatus` (`"unknown" | "guest" |
"authenticated"`) remains the single source of truth used for routing
(`route-guards.ts` only needs the three-way split). `domain/auth-state.ts`
adds a **derived, read-only** `AuthState` covering the fuller vocabulary
(`restoring`, `otp-requesting`, `otp-requested`, `otp-verifying`,
`refreshing`, `logging-out`, `error`, plus the three base states) via a
pure function (`deriveAuthState`) over the session status and the
already-tracked in-flight flags from `useOtpFlow`/the refresh
coordinator/`useLogout`. This avoids the two-competing-state-machines
anti-pattern the sprint brief explicitly warns against (§8: "do not manage
authentication with scattered booleans" / do not create a second source of
truth) — there is exactly one stored state (`session-store.ts`) and one
pure derivation over it, fully unit tested (`auth-state.test.ts`).

## API Flow

```
useOtpFlow.sendOtp()   → POST /v1/auth/otp/send    (skipAuth)
useOtpFlow.verifyOtp() → POST /v1/auth/otp/verify   (skipAuth)
                        → persistSession() → reevaluateStartup()
```

## Token Refresh Coordination (new this pass)

Previously (first pass), refresh only happened once, manually, inside
`bootstrapSession()` at cold start. This pass generalizes it:

```
api-client.ts (requestWithRetry)
  → 401 response, request did not skipAuth, not already a retry
  → request-context.ts#handleUnauthorized()
      → auth-refresh-coordinator.ts#handleUnauthorizedOnce()
          → no session? return false immediately (no network call)
          → in-flight refresh exists? await the same promise (single-flight)
          → else: POST /v1/auth/token/refresh → GET /v1/auth/me → persistSession()
  → true  → requestWithRetry() retried exactly once (allowUnauthorizedRetry=false this time)
  → false → original 401 ApiError propagates
```

This means **any** authenticated API call anywhere in the app — not just
the ones `bootstrapSession` happens to call — now transparently survives
one expired-access-token 401 without the customer noticing, and
concurrent 401s (e.g. two screens fetching at once) share exactly one
refresh request (`api-client.test.ts`, `auth-refresh-coordinator.test.ts`
prove both the single retry and the single-flight behavior). `bootstrapSession()`
was simplified accordingly — it no longer duplicates refresh logic.

## Session Restoration

Unchanged from the first pass (`session-bootstrap.ts#bootstrapSession`),
now simpler since 401 handling moved to the coordinator. See
`CUSTOMER-L5-02-session-lifecycle.md`.

## Navigation Integration

Unchanged from the first pass — `startup-route-resolver.ts`'s
auth-based default-landing logic (CUSTOMER-L5-03) and
`route-guards.ts`'s `access: "authenticated"` checks (CUSTOMER-L5-01) are
untouched by this hardening pass.

## Pending Destination

Unchanged — `reevaluateStartup()` (CUSTOMER-L5-01) already re-runs the full
resolver after login/logout, which already re-checks
`pending-deep-link-store.ts`.

## Logout / Logout-All

- `useLogout` — `POST /v1/auth/logout` (best-effort — local clear always
  happens), then `reevaluateStartup()`.
- `useLogoutAll` (new this pass) — `POST /v1/auth/logout-all`, same
  best-effort-local-clear pattern, explicit confirmation required at the
  call site (`SessionsScreen`'s `ConfirmationModal`, not a bare button
  press — CUSTOMER-L5-02 §36).

## Sessions and Devices (new this pass)

`GET /v1/auth/sessions` → Zod-validated
(`session-summary-schema.ts#parseSessionList`, drops malformed entries
rather than crashing) → `SessionsScreen`. Revocation
(`DELETE /v1/auth/sessions/{id}`) is ownership-checked **server-side**
(`service.py#revoke_session` rejects a session that doesn't belong to the
requesting user — verified by reading the service code, not assumed) — the
client does not re-implement that check, it only surfaces the resulting
error if the backend ever did reject it.

## Customer Cache Clearing

`clearSession()` (session-store.ts) removes the in-memory
`CustomerSession` and the two secure-storage tokens. `useSessions`'s
TanStack Query cache is invalidated on revoke but is **not** proactively
cleared on logout (see `CUSTOMER-L5-02-known-gaps.md` — same class of gap
already flagged for Home's category cache in CUSTOMER-L5-03).
