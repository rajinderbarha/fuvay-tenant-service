import { publicRequest } from "../api/publicClient";
import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";
import {
  LoginResultDTO, RefreshResultDTO, AccessContextDTO, SessionListItemDTO, SessionListResponseDTO,
} from "./types";
import { getOrCreateDeviceId } from "./deviceId";

/**
 * Thin wrappers over the real Fuvay auth endpoints (traced verbatim
 * from app/engines/auth/router.py + schemas.py -- field names below match
 * LoginRequest/OTPSendRequest/OTPVerifyRequest/MFAVerifyRequest/
 * RefreshTokenRequest/PasswordResetRequest/PasswordResetConfirmRequest
 * exactly). This is NOT the Login UI -- these are called by sessionManager
 * and, later, the Phase (Login) screens.
 */
export async function login(input: {
  email: string; password: string; deviceId?: string; deviceName?: string; rememberDevice?: boolean;
}): Promise<ApiResult<LoginResultDTO>> {
  const deviceId = input.deviceId ?? await getOrCreateDeviceId();
  return publicRequest<LoginResultDTO>("/v1/auth/login", {
    method: "POST",
    body: {
      email: input.email, password: input.password,
      device_id: deviceId, device_name: input.deviceName,
      remember_device: input.rememberDevice ?? false,
    },
  });
}

export async function sendOtp(input: { phone: string; purpose?: "phone_login" | "phone_verification" | "password_reset" | "job_approval" }): Promise<ApiResult<{ message: string; use_verify?: boolean; otp_hint?: string }>> {
  const deviceId = await getOrCreateDeviceId();
  return publicRequest("/v1/auth/otp/send", { method: "POST", body: { phone: input.phone, purpose: input.purpose ?? "phone_login", device_id: deviceId } });
}

export async function verifyOtp(input: { phone: string; otp: string; deviceId?: string; deviceName?: string }): Promise<ApiResult<LoginResultDTO>> {
  const deviceId = input.deviceId ?? await getOrCreateDeviceId();
  return publicRequest<LoginResultDTO>("/v1/auth/otp/verify", {
    method: "POST",
    body: { phone: input.phone, otp: input.otp, device_id: deviceId, device_name: input.deviceName },
  });
}

export function verifyMfa(input: {
  mfaChallengeToken: string; code: string; deviceId?: string; deviceName?: string; rememberDevice?: boolean;
}): Promise<ApiResult<LoginResultDTO>> {
  return publicRequest<LoginResultDTO>("/v1/auth/mfa/verify", {
    method: "POST",
    body: {
      mfa_challenge_token: input.mfaChallengeToken, code: input.code,
      device_id: input.deviceId ?? "mobile", device_name: input.deviceName,
      remember_device: input.rememberDevice ?? false,
    },
  });
}

/** Refresh is a PUBLIC endpoint -- the backend authenticates via the
 * refresh token itself, not a Bearer access token (confirmed: no
 * get_current_user dependency on POST /v1/auth/token/refresh). */
export function refreshToken(rawRefreshToken: string): Promise<ApiResult<RefreshResultDTO>> {
  return publicRequest<RefreshResultDTO>("/v1/auth/token/refresh", {
    method: "POST",
    body: { refresh_token: rawRefreshToken },
    unsafeToRetry: true, // refresh must never be silently auto-retried by the generic retry policy
  });
}

export function requestPasswordReset(input: { email?: string; phone?: string }): Promise<ApiResult<{ message: string }>> {
  return publicRequest("/v1/auth/password/reset/request", { method: "POST", body: input });
}

export function confirmPasswordReset(input: {
  email?: string; phone?: string; resetToken: string; newPassword: string; confirmPassword: string;
}): Promise<ApiResult<{ message: string }>> {
  return publicRequest("/v1/auth/password/reset/confirm", {
    method: "POST",
    body: {
      email: input.email, phone: input.phone, reset_token: input.resetToken,
      new_password: input.newPassword, confirm_password: input.confirmPassword,
    },
  });
}

/** Phase R addition -- PUT /v1/auth/password/change (requires current
 * password, distinct from the unauthenticated reset-by-code flow above). */
export function changePassword(input: {
  currentPassword: string; newPassword: string; confirmPassword: string;
}): Promise<ApiResult<{ message: string; other_sessions_revoked: number }>> {
  return authenticatedRequest("/v1/auth/password/change", {
    method: "PUT",
    body: {
      current_password: input.currentPassword,
      new_password: input.newPassword,
      confirm_password: input.confirmPassword,
    },
  });
}

export function getMe(): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest("/v1/auth/me", { method: "GET" });
}

/** Phase R addition -- PUT /v1/auth/me (UpdateProfileRequest: full_name/
 * phone/avatar_url only -- matches the technician-editable field list in
 * the Phase R ownership matrix; business/role/designation etc are
 * tenant-controlled and never sent from here). */
export function updateMyProfile(input: { fullName?: string; avatarUrl?: string }): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest("/v1/auth/me", {
    method: "PUT",
    body: { full_name: input.fullName, avatar_url: input.avatarUrl },
  });
}

/** Phase F backend addition -- GET /v1/auth/access-context (see
 * app/engines/auth/router.py + AuthService.get_mobile_access_context). */
export function getAccessContext(): Promise<ApiResult<AccessContextDTO>> {
  return authenticatedRequest<AccessContextDTO>("/v1/auth/access-context", { method: "GET" });
}

export function listSessions(): Promise<ApiResult<SessionListResponseDTO>> {
  return authenticatedRequest("/v1/auth/sessions", { method: "GET" });
}

export function revokeSession(sessionId: string): Promise<ApiResult<{ session_id: string; revoked: boolean }>> {
  return authenticatedRequest(`/v1/auth/sessions/${sessionId}`, { method: "DELETE" });
}

export function logoutCurrentSession(): Promise<ApiResult<{ message: string }>> {
  return authenticatedRequest("/v1/auth/logout", { method: "POST" });
}

export function logoutAllSessions(): Promise<ApiResult<{ sessions_revoked: number; message: string }>> {
  return authenticatedRequest("/v1/auth/logout-all", { method: "POST" });
}

/** Revokes every OTHER session, leaving the current one signed in --
 * distinct from logoutAllSessions above, which also ends this session. */
export function revokeAllOtherSessions(): Promise<ApiResult<{ sessions_revoked: number; message: string }>> {
  return authenticatedRequest("/v1/auth/sessions/revoke-all-other", { method: "POST" });
}
