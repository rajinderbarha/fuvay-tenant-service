# CUSTOMER-L5-02 — Session Lifecycle

```
OTP request      POST /v1/auth/otp/send
  → challenge    (no explicit challenge_id in this backend's contract —
                   the phone number itself + a server-side OTPRecord row,
                   scoped by purpose="phone_login", is the challenge;
                   see CUSTOMER-L5-02-contract-matrix.md)
  → verification  POST /v1/auth/otp/verify {phone, otp, device_id, device_name}
  → session       {access_token, refresh_token, user, tenant}
  → access token use   Authorization: Bearer <access_token> (api-client.ts, CUSTOMER-L5-00)
  → refresh       POST /v1/auth/token/refresh {refresh_token} — on any 401
                   (auth-refresh-coordinator.ts, this sprint)
  → rotation      backend issues a NEW access_token + refresh_token pair on
                   every refresh call (not incremental — verified from
                   service.py#refresh_token, which calls _build_token_pair
                   again) — old tokens are overwritten atomically by
                   persistSession() (both secureStorage.setItem calls in
                   one Promise.all)
  → expiry        access token: 30 min (TokenPair.expires_in default,
                   schemas.py) — client never reads this value directly
                   (tokens are opaque, per CUSTOMER-L5-02 §18); expiry is
                   discovered only via a 401 response
  → revocation    DELETE /v1/auth/sessions/{id} (this device or another) —
                   revoking the CURRENT session does not locally invalidate
                   the in-memory access token immediately; the NEXT API
                   call will 401, and since a revoked session has no valid
                   refresh either, the coordinator's refresh attempt fails
                   and clears the local session (see failure matrix)
  → logout        POST /v1/auth/logout (best-effort) → secure storage
                   cleared locally regardless of server response
```

## Challenge Binding

No distinct `challenge_id` exists in this backend's real contract — the
`(phone, purpose)` pair plus the most recent unexpired `OTPRecord` row *is*
the server-side challenge (`service.py#verify_phone_otp_login`'s query:
`purpose == "phone_login" AND recipient_hash == hash(phone) AND is_used ==
False AND expires_at > now()`, ordered by `created_at desc`, `limit(1)`).
The client does not fabricate a challenge ID — `useOtpFlow` re-derives the
normalized phone number from its own state on every verify call, so
changing the phone number field between request and verify naturally
targets a different (or no) challenge server-side; there is no separate
local "invalidate the previous challenge" step needed because there is no
locally-held challenge object to invalidate.

## OTP Expiry / Attempts

From `service.py`: `OTP_EXPIRE_MINUTES` (constant, value not re-derived
here to avoid drifting out of sync with the backend — the client does not
hardcode or display a countdown against this value, matching "the backend
remains authoritative"). Max 3 attempts
(`otp_record.attempts > 3` → `is_used = True`, rejects with "Too many
incorrect OTP attempts"). The client surfaces whatever message the backend
returns via `ApiError` categories — `unauthorized` for both wrong-code and
too-many-attempts (the backend does not distinguish these with different
HTTP statuses in this contract), `not_found` for "OTP not found or
expired."

## Multi-Device

Each OTP verification creates a **new** `UserSession` row
(`service.py#verify_phone_otp_login` always does `self.db.add(session)`) —
there is no "reuse existing session for this device" logic server-side, so
signing in twice on the same physical device (e.g. after an app
reinstall) produces two session rows, both listed by `GET /v1/auth/sessions`
until one is revoked or expires. This is real backend behavior, not a
client assumption.
