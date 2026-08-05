/**
 * Authentication/session TYPE contracts only -- per Phase D section 7,
 * no login transport is implemented this phase. Shapes are derived from
 * the real mounted routes confirmed this phase: /v1/auth/otp/send,
 * /v1/auth/otp/verify, /v1/auth/login, /v1/auth/token/refresh,
 * /v1/auth/logout, /v1/auth/register/customer, /v1/auth/me,
 * /v1/auth/mfa/*. These are generic auth-engine routes (not
 * customer-exclusive) -- role/audience is established by the response,
 * not the URL, hence `CustomerSessionContext.audience` below.
 */
import { CustomerId, TenantId } from "./ids";

export interface OtpRequestInput {
  phone: string;
}

export interface OtpVerifyInput {
  phone: string;
  code: string;
}

export interface EmailPasswordLoginInput {
  email: string;
  password: string;
}

export type MfaChallengeType = "otp" | "backup_code";

export interface MfaChallenge {
  type: MfaChallengeType;
  sessionToken: string;
}

export type SessionExpiryReason = "expired" | "revoked" | "device_untrusted";

export type CustomerAudience = "serviceos:customer";

/** Result of resolving `/v1/auth/access-context` for a signed-in session.
 * A future navigation guard (Phase E) must check `audience` explicitly --
 * a staff/provider token reaching this app must never be treated as a
 * valid customer session. */
export interface CustomerSessionContext {
  authenticated: boolean;
  audience: CustomerAudience | string;
  customerId: CustomerId | null;
  tenantId: TenantId | null;
  accountStatus: "active" | "suspended" | "blocked" | "unknown";
}

// ─────────────────────────────────────────────────────────────────────────
// Phase F additions -- session result model (spec section 13) and MFA
// challenge states (spec section 12). Verified against app/engines/auth/
// service.py this phase: login/verify_phone_otp_login/verify_mfa all
// return `{mfa_required: true, mfa_challenge_token}` OR a token bundle
// with `access_token`, `refresh_token` (nullable when a forced password
// change blocks issuing one), `user`, optional `tenant`, and backend-
// authoritative `next_destination`/`reason_code`.
// ─────────────────────────────────────────────────────────────────────────

/** Verified backend MFA states this phase (source: AuthService.verify_mfa
 * / MFAVerifyRequest). The backend does not return a distinct
 * "challenge_pending"/"challenge_expired" status field -- expiry and
 * invalidity both surface as an INVALID_TOKEN error on verify, so this
 * union is intentionally narrower than the spec's suggested list; states
 * without direct evidence (`recovery_code_required`, `locked` as a
 * distinct MFA-specific state) are omitted rather than fabricated. A
 * backup code IS accepted by the same `/mfa/verify` endpoint (service.py
 * tries TOTP first, then backup code) -- there is no separate challenge
 * state for it, just a different `code` shape. */
export type MfaChallengeStatus =
  | "not_required"
  | "challenge_required"
  | "challenge_verified"
  | "failed";

export interface MfaChallengeState {
  status: MfaChallengeStatus;
  /** Opaque backend-issued token, NEVER a TOTP/recovery code -- kept
   * separate from access/refresh tokens in the token vault and cleared on
   * success, expiry, logout or cancellation (spec section 12). */
  challengeToken: string | null;
}

export type PostLoginDestination = string;

/** The one validated internal session result every successful auth flow
 * (password, OTP, MFA-completed) normalizes into. Never constructed from
 * a decoded JWT's claims -- always from a verified backend response body. */
export interface SessionResult {
  accessToken: string;
  /** Null only in the documented forced-password-change case (password
   * login where requiresPasswordChange is true) -- the backend
   * deliberately withholds a refresh token until the change completes. */
  refreshToken: string | null;
  customerId: CustomerId;
  requiresPasswordChange: boolean;
  postLoginDestination: PostLoginDestination | null;
}

export interface OtpSendResult {
  message: string;
  /** True when Twilio Verify (not the local DB-fallback OTP) is the
   * active delivery mechanism -- purely informational, never used to
   * change client validation behavior. */
  usesExternalVerifyProvider: boolean;
}
