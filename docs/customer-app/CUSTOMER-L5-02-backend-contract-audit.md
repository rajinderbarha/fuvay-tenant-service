# CUSTOMER-L5-02 — Backend Contract Audit

Read directly from `app/engines/auth/router.py`, `app/engines/auth/schemas.py`,
`app/engines/auth/service.py`. This is a shared multi-role auth engine (admin,
tenant staff, and customer all use it), not a customer-only API — the
customer app uses a subset of its 37 endpoints.

## Critical Finding

The **pre-existing** `mobile/customer-app/src/lib/api.ts` (`authApi`) calls
paths that **do not exist on the real backend**:
`/v1/auth/customer/otp-request`, `/v1/auth/customer/otp-verify`,
`/v1/auth/customer/login`. The real paths are `/v1/auth/otp/send`,
`/v1/auth/otp/verify`, `/v1/auth/login`. This means the existing
`LoginScreen`/`AuthContext` login flow has never successfully authenticated
against the real backend — it was built against an assumed contract that
was never verified. This sprint's new auth implementation uses the verified
real paths; the legacy `src/lib/api.ts#authApi` is left as-is (its screens
still exist and are still reachable via `LegacyApp`) but is now known-broken
and documented in `known-gaps.md` rather than silently trusted.

## Endpoints Used by CUSTOMER-L5-02

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/v1/auth/otp/send` | none | `{ phone, purpose: "phone_login" }` → `{ message, otp_hint? }` (dev-only hint) |
| POST | `/v1/auth/otp/verify` | none | `{ phone, otp, device_id, device_name }` → `{ access_token, refresh_token, user, tenant }` |
| POST | `/v1/auth/register/customer` | none | `{ full_name, phone, email? }` → `{ user_id, message, otp_hint? }` — creates an inactive customer, then OTP-verify (purpose `phone_login`) activates it |
| POST | `/v1/auth/token/refresh` | none (refresh token in body) | `{ refresh_token }` → new `{ access_token, refresh_token }` pair |
| POST | `/v1/auth/logout` | Bearer | revokes current session |
| GET | `/v1/auth/me` | Bearer | full profile + `permissions[]` |
| PUT | `/v1/auth/me` | Bearer | `{ full_name?, phone?, avatar_url? }` → updated profile |

## Response Shapes (verified from `service.py`)

`_user_to_profile()` (used by `/otp/verify`, `/login`, `/me`):
```
user_id, id, email, phone, full_name, display_name, language, timezone,
role, tenant_id, is_verified, is_mfa_enabled, is_active,
onboarding_complete, force_password_change, password_reset_required,
temporary_password_active, password_changed_at, avatar_url,
profile_photo_media_id, last_login_at, created_at, permissions[]
```

`role` for a customer-registered account is always `"customer"`
(`service.py#register_customer`). No separate "customer profile" model
exists beyond the shared `User` row — CUSTOMER-L5-02's "profile" screen
therefore maps directly onto this shape, not a customer-specific one.

## Not Implemented / Not Available

- **MFA** (`/mfa/verify`, `/mfa/setup`) exists on the backend but is a
  staff/admin-oriented flow (`is_mfa_enabled` gate) — not built into the
  customer OTP-login screen this sprint since customer accounts don't set
  up MFA through any existing customer-facing flow.
- **Password reset** (`/password/reset/request`, `/password/reset/confirm`)
  exists but customer accounts registered via `/register/customer` have no
  `hashed_password` set — password-based login/reset only applies to the
  email+password path, which the customer app does not use as its primary
  flow (OTP is). Not wired this sprint.
- **Twilio Verify** (`app/twilio_client.py`) is used for real SMS delivery
  in production when configured; in local/dev without Twilio credentials,
  `otp_hint` is returned directly in the response body (`send_phone_otp`'s
  DB-fallback path) — this is how OTP is testable without a real SMS
  provider in this environment. The client must never display `otp_hint`
  outside a `__DEV__` build (implemented as a guard in `useOtpFlow`).
- **Session list / revoke** (`GET /v1/auth/sessions`,
  `DELETE /v1/auth/sessions/{id}`) exist but are not surfaced in the
  customer app this sprint (no product requirement for a "manage devices"
  screen yet) — tracked in `known-gaps.md`.
- **Rate limiting** is enforced server-side
  (`rate_limiter.check_and_raise`, keyed by IP for send, by phone for
  verify) — the client-side OTP flow surfaces the resulting 429 through the
  existing `ApiError` category `rate_limited` (CUSTOMER-L5-00's
  `api-errors.ts`) rather than re-implementing throttling client-side.
