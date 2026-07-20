/** Mirrors app/engines/auth/service.py#_user_to_profile exactly — see CUSTOMER-L5-02-backend-contract-audit.md. */
export interface AuthUserProfile {
  user_id: string;
  id: string;
  email: string;
  phone: string | null;
  full_name: string;
  display_name: string | null;
  language: string;
  timezone: string;
  role: string;
  tenant_id: string | null;
  is_verified: boolean;
  is_mfa_enabled: boolean;
  is_active: boolean;
  onboarding_complete: boolean;
  force_password_change: boolean;
  password_reset_required: boolean;
  temporary_password_active: boolean;
  password_changed_at: string | null;
  avatar_url: string | null;
  profile_photo_media_id: string | null;
  last_login_at: string | null;
  created_at: string;
  permissions: string[];
}

export interface AuthTenantContext {
  tenant_id: string | null;
  [key: string]: unknown;
}

export interface OtpSendResponse {
  message: string;
  /** Dev-only fallback when Twilio Verify isn't configured — never rendered outside __DEV__. */
  otp_hint?: string;
  use_verify?: boolean;
}

export interface OtpVerifyResponse {
  access_token: string;
  refresh_token: string;
  user: AuthUserProfile;
  tenant: AuthTenantContext | null;
}

export interface RegisterCustomerResponse {
  user_id: string;
  message: string;
  otp_hint?: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  expires_in?: number;
}

/** Mirrors app/engines/auth/service.py#list_sessions exactly. */
export interface SessionSummaryDto {
  session_id: string;
  device_name: string | null;
  device_type: string | null;
  ip_address: string | null;
  last_active_at: string;
  is_current: boolean;
  is_trusted: boolean;
  is_approved: boolean;
  created_at: string;
}

export interface SessionListResponse {
  sessions: SessionSummaryDto[];
  total: number;
}

export interface RevokeSessionResponse {
  session_id: string;
  revoked: boolean;
}

export interface LogoutAllResponse {
  sessions_revoked: number;
  message: string;
}
