/**
 * DTOs matching the REAL backend response shapes (traced from
 * app/engines/auth/service.py -- login/verify_phone_otp_login/verify_mfa
 * all return this same shape; refresh_token returns just the token pair;
 * get_mobile_access_context returns the new Phase F projection).
 */
export interface LoginSuccessDTO {
  mfa_required: false;
  access_token: string;
  refresh_token: string | null;
  next_destination?: string;
  reason_code?: string;
  requires_password_change?: boolean;
  redirect_to?: string | null;
  user: Record<string, unknown>;
  tenant: Record<string, unknown> | null;
}

export interface MfaRequiredDTO {
  mfa_required: true;
  mfa_challenge_token: string;
}

export type LoginResultDTO = LoginSuccessDTO | MfaRequiredDTO;

export interface RefreshResultDTO {
  access_token: string;
  refresh_token: string;
}

/** Real shape from AuthService.get_mobile_access_context (Phase F backend addition). */
export interface AccessContextDTO {
  user_id: string;
  canonical_role: string;
  audience: string;
  tenant_id: string | null;
  tenant_status: string | null;
  technician_id: string | null;
  technician_status: string | null;
  enabled_verticals: string[];
  capabilities: string[];
}

export type SessionAllowedAction = "view" | "remove_trust" | "revoke";

export interface SessionListItemDTO {
  session_id: string;
  device_name: string | null;
  /** Phase W: safe display projection ("Unknown Android device" fallback,
   * never a fabricated hardware claim) -- prefer this over device_name. */
  device_display_name?: string;
  device_type?: string | null;
  ip_address?: string | null;
  /** No GeoIP integration exists (confirmed by audit) -- always null today;
   * kept optional so a real integration can populate it later without a
   * mobile change. */
  approximate_location?: string | null;
  is_trusted?: boolean;
  trusted_at?: string | null;
  trust_expires_at?: string | null;
  is_approved?: boolean;
  is_current?: boolean;
  allowed_actions?: SessionAllowedAction[];
  last_active_at?: string | null;
  created_at?: string | null;
}

export interface SessionListResponseDTO {
  sessions: SessionListItemDTO[];
  total: number;
  current_session_id: string | null;
  total_sessions: number;
  trusted_device_count: number;
}

/** Sensitive material persisted in SecureStore (Phase F spec section 5). */
export interface StoredSessionBundle {
  schemaVersion: 1;
  accessToken: string;
  refreshToken: string;
  sessionId: string | null;
}
