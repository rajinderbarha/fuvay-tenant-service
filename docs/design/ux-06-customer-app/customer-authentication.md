# Customer Authentication — UX-06

## Real, verified contract

`POST /v1/auth/login` — the same unified login endpoint used by every Fuvay role
(confirmed via live `openapi.json`: `requestBody` schema `LoginRequest { email,
password, device_id, device_name?, user_agent? }`, response `ApiResponse[dict]`).
This mirrors UX-05's finding for the staff/technician app: there is no
role-specific or phone/OTP-specific login endpoint anywhere in the schema.

`GET /v1/customer/profile` is used as the session-restore / "who am I" call.
`POST /v1/auth/logout` clears the server-side session.

## What was removed

The prior scaffold's `LoginScreen` offered a phone+OTP flow
(`/v1/auth/customer/otp-request` → `/v1/auth/customer/otp-verify`) as the *default*
mode, with email/password as a fallback. Neither OTP endpoint exists in the live
backend. Per the UX-06 brief's guidance to prefer removing a misleading control over
shipping one that silently fails, the OTP mode was deleted; the app now offers a
single, real email/password sign-in form (`src/screens/LoginScreen.tsx`).

## Session handling

Unchanged from the existing scaffold's pattern (kept because it's sound):
AsyncStorage holds the bearer token + minimal customer identity fields; `apiFetch`
in `lib/api.ts` injects `Authorization: Bearer <token>` on every authenticated call;
`AuthProvider` restores the session on cold start by calling `/v1/customer/profile`
with the stored token and treating a failure as "logged out" (no dangling stale
session).

## Verification status this round

Static/contract-level verification only (matched against `openapi.json`). A live
Playwright login→session-restore→logout pass (the rigor UX-05C applied) is deferred
to the next round — see known-limitations.md. No fabricated pass/fail claim is made
here.
