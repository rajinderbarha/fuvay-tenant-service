import { apiClient } from "../../../api/api-client";
import type {
  AuthUserProfile,
  OtpSendResponse,
  OtpVerifyResponse,
  RegisterCustomerResponse,
  RefreshTokenResponse,
  SessionListResponse,
  RevokeSessionResponse,
  LogoutAllResponse,
} from "./auth-api-types";

/**
 * Real backend paths verified against app/engines/auth/router.py — see
 * CUSTOMER-L5-02-contract-matrix.md. The pre-existing
 * src/lib/api.ts#authApi calls different, non-existent paths; this module
 * is deliberately separate rather than "fixing" that file in place, since
 * the legacy screens that call it are out of this sprint's scope.
 */
export const authApi = {
  sendOtp: (phone: string, purpose: "phone_login" | "phone_verification" = "phone_login") =>
    apiClient.post<OtpSendResponse>("/v1/auth/otp/send", { phone, purpose }, { skipAuth: true }),

  verifyOtp: (phone: string, otp: string, deviceId: string, deviceName?: string) =>
    apiClient.post<OtpVerifyResponse>("/v1/auth/otp/verify", { phone, otp, device_id: deviceId, device_name: deviceName }, { skipAuth: true }),

  registerCustomer: (fullName: string, phone: string, email?: string) =>
    apiClient.post<RegisterCustomerResponse>("/v1/auth/register/customer", { full_name: fullName, phone, email }, { skipAuth: true }),

  refreshToken: (refreshToken: string) => apiClient.post<RefreshTokenResponse>("/v1/auth/token/refresh", { refresh_token: refreshToken }, { skipAuth: true }),

  me: () => apiClient.get<AuthUserProfile>("/v1/auth/me"),

  updateProfile: (patch: { full_name?: string; phone?: string; avatar_url?: string }) => apiClient.put<AuthUserProfile>("/v1/auth/me", patch),

  logout: () => apiClient.post<{ message: string }>("/v1/auth/logout"),

  logoutAll: () => apiClient.post<LogoutAllResponse>("/v1/auth/logout-all"),

  listSessions: () => apiClient.get<SessionListResponse>("/v1/auth/sessions"),

  revokeSession: (sessionId: string) => apiClient.delete<RevokeSessionResponse>(`/v1/auth/sessions/${encodeURIComponent(sessionId)}`),
};
