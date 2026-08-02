import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";

export interface SecurityStatusDTO {
  level: "protected" | "protection_recommended" | "action_required" | "unavailable";
  label: string;
  reasons: string[];
}

export interface SecuritySummaryDTO {
  security_status: SecurityStatusDTO;
  password: { configured: boolean; changed_at: string | null; change_allowed: boolean };
  mfa: { enabled: boolean; method: string | null; enabled_at: string | null; recovery_codes_remaining: number | null; required_by_policy: boolean };
  current_device: { session_id: string | null; trusted: boolean; device_name: string | null; last_active_at: string | null };
  verified_contacts: { masked_mobile: string | null; mobile_verified: boolean; masked_email: string | null; email_verified: boolean };
  active_session_count: number;
  recent_activity: SecurityActivityItemDTO[];
}

export interface SecurityActivityItemDTO {
  id: string;
  action_type: string;
  outcome: string;
  failure_reason: string | null;
  device_id: string | null;
  ip_masked: string | null;
  created_at: string;
}

/** Technician Security & MFA (Phase V). Reuses the EXISTING real
 * `/v1/auth/me/mobile-security-summary` (composed server-side over the
 * canonical get_security_overview/get_security_activity/list_sessions --
 * never a second security-status calculation on the client). */
export function getSecuritySummary(signal?: AbortSignal): Promise<ApiResult<SecuritySummaryDTO>> {
  return authenticatedRequest<SecuritySummaryDTO>(`/v1/auth/me/mobile-security-summary`, { method: "GET", signal });
}

export function getSecurityActivity(limit = 50, offset = 0, signal?: AbortSignal): Promise<ApiResult<{ items: SecurityActivityItemDTO[]; total: number; limit: number; offset: number }>> {
  return authenticatedRequest(`/v1/auth/me/security-activity?limit=${limit}&offset=${offset}`, { method: "GET", signal });
}

export function removeDeviceTrust(sessionId: string): Promise<ApiResult<{ session_id: string; is_trusted: boolean }>> {
  return authenticatedRequest(`/v1/auth/me/devices/${sessionId}/remove-trust`, { method: "POST" });
}
