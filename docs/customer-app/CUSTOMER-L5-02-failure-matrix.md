# CUSTOMER-L5-02 — Failure Matrix

| Failure | Detection point | Customer message | Field/screen | Retry | Session cleanup | Pending destination | Analytics | Log level | Severity |
|---|---|---|---|---|---|---|---|---|---|
| Invalid identifier (bad phone format) | Client-side (`phone-validation.ts`, before any request) | "Enter a valid phone number." | `OtpLoginScreen` phone field | User edits and resubmits | N/A | N/A | none (client-only validation) | N/A | P3 |
| OTP invalid (wrong code) | `ApiError.category === "unauthorized"` from `/otp/verify` | "Incorrect or expired code. Please try again." | `OtpLoginScreen` code field | User retries | N/A | N/A | none this sprint (see known-gaps) | warn (`api.error`, CUSTOMER-L5-00) | P3 |
| OTP expired | Same category as invalid (backend doesn't distinguish — see session-lifecycle doc) | Same message | Same | Same | N/A | N/A | none | warn | P3 |
| Rate limited (OTP send/verify) | `ApiError.category === "rate_limited"` | "Too many attempts. Please wait a moment and try again." | `OtpLoginScreen` | User waits, no auto-retry | N/A | N/A | none | warn | P2 |
| Account locked | Not reachable via the OTP path this sprint (`ACCOUNT_LOCKED` only thrown by `service.py#login`, the email+password path, which this app doesn't call) | N/A | N/A | N/A | N/A | N/A | N/A | N/A | NOT_APPLICABLE this sprint |
| Account disabled | `service.py#verify_phone_otp_login` raises `UNAUTHORIZED` ("Account is deactivated") — same category as wrong-code, **not separately distinguishable client-side** | Generic "Incorrect or expired code" shown even though the real cause is account deactivation | `OtpLoginScreen` | User retries indefinitely with no path forward | N/A | N/A | none | warn | P1 — real gap, not a false claim; documented in known-gaps rather than built around |
| Refresh token expired/revoked | `authApi.refreshToken` rejects inside `auth-refresh-coordinator.ts` | No direct message — session silently clears, customer is routed to guest/baseline on next `reevaluateStartup` (implicit, via the normal guest experience) | N/A (no dedicated "session expired" screen built) | Customer signs in again via the normal `OtpLoginScreen` entry point | `clearSession()` | Preserved by `pending-deep-link-store.ts`'s own TTL (unrelated to this failure) | none | warn (`auth_session_refresh_failed`) | P2 |
| Session revoked from another device | Same as above — next 401 triggers the same refresh-fails-and-clears path | Same | Same | Same | Same | Same | none | warn | P2 |
| Profile update conflict | Not distinguished — `PUT /v1/auth/me` has no optimistic-concurrency/ETag field in its contract, so a "stale write wins" (last write wins) rather than a detectable conflict | N/A | N/A | N/A | N/A | N/A | N/A | N/A | MISSING_BACKEND (no conflict signal exists to detect) |
| Secure storage failure (write) | `secureStorage.setItem` returns `false` on failure (CUSTOMER-L5-00's adapter swallows the native error and returns a boolean) — `persistSession` now checks both results | In-memory session still works for this run (no customer-facing interruption); nothing survives an app restart if the write failed | N/A | N/A | N/A | N/A | none | warn (`auth.session_persist_failed`) | P2 — detected and logged; no customer-facing recovery UI exists yet (would require prompting to re-authenticate proactively, not built this sprint) |
| Marketplace mismatch | Not exercised — single-marketplace test environment (see security review) | UNVERIFIED | — | — | — | — | — | — | UNVERIFIED |
| Offline before OTP request | `ApiError.category === "network_error"` | "Something went wrong. Please try again." (generic — see known-gaps for the missing offline-specific copy) | `OtpLoginScreen` | User retries once online | N/A | N/A | none | warn | P3 |
| Timeout (any auth call) | `ApiError.category === "timeout"` | Same generic message | Same | Retryable (`ApiError.retryable`) | N/A | N/A | none | warn | P3 |
| Backend 500 | `ApiError.category === "server_error"` | Same generic message | Same | Retryable | N/A | N/A | none | warn | P3 |

Every row's client message comes from `useOtpFlow.ts#safeErrorMessage` — a
small, fixed mapping from `ApiError.category` to copy. It does not yet
cover every category distinctly (see the "account disabled" and
"marketplace mismatch" rows above) — this is an honest gap, not a false
completeness claim.
