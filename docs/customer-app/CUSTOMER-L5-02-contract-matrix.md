# CUSTOMER-L5-02 — Contract Matrix

Verified directly against `app/engines/auth/router.py` and
`app/engines/auth/service.py` (no OpenAPI/Swagger generation exists in this
repository to cross-check against — verification is source-code-level).

| Capability | Backend contract | Client type | Runtime schema | API client method | Query/Mutation | UI behavior | Test coverage | Parity |
|---|---|---|---|---|---|---|---|---|
| OTP request | `POST /v1/auth/otp/send` | `OtpSendResponse` | none (trivial `{message, otp_hint?}`, not worth Zod) | `authApi.sendOtp` | `useOtpFlow#sendOtp` | `OtpLoginScreen` phone step | `phone-validation.test.ts` (input validation only) | MATCHED |
| OTP verify | `POST /v1/auth/otp/verify` | `OtpVerifyResponse` | none (mapped via `toCustomerSession`, which is itself tested) | `authApi.verifyOtp` | `useOtpFlow#verifyOtp` | `OtpLoginScreen` code step | `session.test.ts` (mapping) | MATCHED |
| OTP resend | Same endpoint as request (`/v1/auth/otp/send` — no distinct resend route) | n/a | n/a | `authApi.sendOtp` (called again) | `useOtpFlow#sendOtp` | "Use a different number" resets and re-sends | Not separately tested (same code path as request) | MATCHED |
| Signup | `POST /v1/auth/register/customer` | `RegisterCustomerResponse` | none | `authApi.registerCustomer` | none wired | **not built** — see known-gaps | Not tested | MISSING_CLIENT (UI) |
| Login (email+password) | `POST /v1/auth/login` | n/a | n/a | not implemented | none | **not built** — OTP is the only flow this sprint implements (product decision, not a backend gap) | n/a | NOT_APPLICABLE |
| Token refresh | `POST /v1/auth/token/refresh` | `RefreshTokenResponse` | none | `authApi.refreshToken` | `auth-refresh-coordinator.ts` | Transparent — no dedicated screen | `auth-refresh-coordinator.test.ts`, `api-client.test.ts` | MATCHED |
| Logout | `POST /v1/auth/logout` | `{message}` | none | `authApi.logout` | `useLogout` | Sign-out button on Profile/Baseline | manual (no dedicated unit test — thin wrapper) | MATCHED |
| Logout all | `POST /v1/auth/logout-all` | `LogoutAllResponse` | none | `authApi.logoutAll` | `useLogoutAll` | "Sign out of all devices" on Sessions screen | `use-logout-all.test.ts` | MATCHED |
| Current customer | `GET /v1/auth/me` | `AuthUserProfile` | none (mapped via `toCustomerSession`) | `authApi.me` | `bootstrapSession`, `session-bootstrap.ts` | Drives session state everywhere | `session-bootstrap.test.ts`, `session.test.ts` | MATCHED |
| Profile update | `PUT /v1/auth/me` | `AuthUserProfile` (request body is a subset: `full_name?/phone?/avatar_url?`) | none | `authApi.updateProfile` | `useUpdateProfile` | `ProfileScreen` save | manual (thin mutation wrapper — see known-gaps) | MATCHED |
| Session list | `GET /v1/auth/sessions` | `SessionListResponse` | `sessionSummarySchema` (Zod) | `authApi.listSessions` | `useSessions` | `SessionsScreen` list | `session-summary-schema.test.ts` | MATCHED |
| Session revoke | `DELETE /v1/auth/sessions/{id}` | `RevokeSessionResponse` | none | `authApi.revokeSession` | `useRevokeSession` | `SessionsScreen` per-row "Sign out" | manual (thin mutation wrapper) | MATCHED |
| Account deletion | **no endpoint found anywhere in this backend** | — | — | — | — | — | — | MISSING_BACKEND |
| Consent (terms/privacy/marketing) | **no field in `_user_to_profile`, no consent endpoint found** | — | — | — | — | — | — | MISSING_BACKEND |
| MFA | `POST /v1/auth/mfa/verify`, `/mfa/setup`, `/mfa/confirm`, `/mfa/disable` (real, but staff/admin-oriented — `is_mfa_enabled` gate) | — | — | not implemented | — | not built | — | UNVERIFIED (real endpoints exist; not exercised by any customer-facing flow this sprint) |
| Password reset | `POST /v1/auth/password/reset/request`, `/password/reset/confirm` | real | — | not implemented | — | not built (customer accounts registered via OTP have no password set) | — | NOT_APPLICABLE |

## Assumptions Removed From the Previous Pass

The earlier CUSTOMER-L5-02 implementation in this codebase (see
`CUSTOMER-L5-02-baseline-verification.md`) already used the correct
verified paths above — no assumption-based endpoint names were carried
forward. The one real backend-contract finding (documented since the
first pass) is that the **pre-existing, out-of-scope** `src/lib/api.ts`
legacy screen calls invented paths (`/v1/auth/customer/otp-request` etc.)
that do not exist.
