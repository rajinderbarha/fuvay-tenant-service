import { request } from "../client/httpClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  loginOutcomeSchema, otpSendResponseSchema, refreshResponseSchema, logoutResponseSchema,
  accessContextResponseSchema, passwordResetRequestResponseSchema, passwordResetConfirmResponseSchema,
} from "./authContracts";

/**
 * Typed auth endpoint methods -- each maps to one confirmed-mounted route
 * (app/engines/auth/router.py, read directly this phase). No method
 * exists here for an endpoint this phase didn't verify against source:
 * `selectPrincipal` is NOT implemented (no `/auth/principal/select` route
 * exists in the current router -- that was an audit lead, not a real
 * endpoint); `listDevices`/`revokeDevice`/`getMfaStatus` are likewise
 * omitted (no dedicated device-list or MFA-status route was found --
 * `/auth/sessions` conflates session+device, and MFA state is only
 * observable indirectly via login's `mfa_required` flag or `/auth/me`).
 * None of these methods retries automatically -- see retryPolicy.ts,
 * which only ever wraps GET requests.
 */

export interface LoginWithPasswordInput {
  email: string; // accepts email OR E.164 mobile per LoginRequest._normalise_email
  password: string;
  deviceId?: string;
  deviceName?: string;
  rememberDevice?: boolean;
}

export async function loginWithPassword(input: LoginWithPasswordInput) {
  const res = await request({
    method: "POST",
    path: "/v1/auth/login",
    body: {
      email: input.email,
      password: input.password,
      device_id: input.deviceId ?? "mobile",
      device_name: input.deviceName,
      remember_device: input.rememberDevice ?? false,
    },
  });
  return parseApiSuccess(res.json, loginOutcomeSchema);
}

export interface RequestLoginOtpInput {
  phone: string;
}

export async function requestLoginOtp(input: RequestLoginOtpInput) {
  const res = await request({
    method: "POST",
    path: "/v1/auth/otp/send",
    body: { phone: input.phone, purpose: "phone_login" },
  });
  return parseApiSuccess(res.json, otpSendResponseSchema);
}

export interface VerifyLoginOtpInput {
  phone: string;
  otp: string;
  deviceId?: string;
  deviceName?: string;
}

export async function verifyLoginOtp(input: VerifyLoginOtpInput) {
  const res = await request({
    method: "POST",
    path: "/v1/auth/otp/verify",
    body: { phone: input.phone, otp: input.otp, device_id: input.deviceId ?? "mobile", device_name: input.deviceName },
  });
  return parseApiSuccess(res.json, loginOutcomeSchema);
}

export interface CompleteMfaChallengeInput {
  mfaChallengeToken: string;
  code: string;
  deviceId?: string;
  deviceName?: string;
  rememberDevice?: boolean;
}

export async function completeMfaChallenge(input: CompleteMfaChallengeInput) {
  const res = await request({
    method: "POST",
    path: "/v1/auth/mfa/verify",
    body: {
      mfa_challenge_token: input.mfaChallengeToken,
      code: input.code,
      device_id: input.deviceId ?? "mobile",
      device_name: input.deviceName,
      remember_device: input.rememberDevice ?? false,
    },
  });
  // verify_mfa never returns the mfa_required branch (source: always
  // returns a token bundle or raises) -- still parsed through the union
  // schema so a genuinely malformed response fails closed the same way.
  return parseApiSuccess(res.json, loginOutcomeSchema);
}

/** Never wrapped in the generic retry policy -- refreshCoordinator.ts is
 * the ONLY caller, and it owns single-flight + no-recursive-retry
 * guarantees itself (spec section 17). */
export async function refreshSession(refreshToken: string) {
  const res = await request({ method: "POST", path: "/v1/auth/token/refresh", body: { refresh_token: refreshToken } });
  return parseApiSuccess(res.json, refreshResponseSchema);
}

export async function logout(accessToken: string) {
  const res = await request({ method: "POST", path: "/v1/auth/logout", accessToken });
  return parseApiSuccess(res.json, logoutResponseSchema);
}

export async function getAccessContext(accessToken: string) {
  const res = await request({ method: "GET", path: "/v1/auth/access-context", accessToken });
  return parseApiSuccess(res.json, accessContextResponseSchema);
}

export interface RequestPasswordResetInput {
  email?: string;
  phone?: string;
}

/** Enumeration-safe by construction -- the backend returns the identical
 * message whether or not an account exists (verified in source). */
export async function requestPasswordReset(input: RequestPasswordResetInput) {
  const res = await request({ method: "POST", path: "/v1/auth/password/reset/request", body: input });
  return parseApiSuccess(res.json, passwordResetRequestResponseSchema);
}

export interface ConfirmPasswordResetInput {
  email?: string;
  phone?: string;
  resetToken: string;
  newPassword: string;
  confirmPassword: string;
}

/** Never returns a session (confirmed in source: a successful reset
 * revokes every existing session and returns only a message) -- the
 * caller must route back to a fresh sign-in, never auto-login. */
export async function confirmPasswordReset(input: ConfirmPasswordResetInput) {
  const res = await request({
    method: "POST",
    path: "/v1/auth/password/reset/confirm",
    body: {
      email: input.email, phone: input.phone,
      reset_token: input.resetToken, new_password: input.newPassword, confirm_password: input.confirmPassword,
    },
  });
  return parseApiSuccess(res.json, passwordResetConfirmResponseSchema);
}
