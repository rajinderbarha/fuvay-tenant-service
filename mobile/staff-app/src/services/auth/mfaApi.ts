import { authenticatedRequest } from "../api/authenticatedClient";
import { ApiResult } from "../api/types";

/** MFA setup/confirm/disable (Phase R) -- calls the EXISTING canonical
 * /v1/auth/mfa/* endpoints directly; no separate MFA system. Request body
 * field names verified against app/engines/auth/schemas.py
 * (MFASetupConfirmRequest.code, MFADisableRequest.password/.code). */
export function setupMfa(): Promise<ApiResult<{ secret: string; otpauth_url: string; qr_code_url?: string }>> {
  return authenticatedRequest(`/v1/auth/mfa/setup`, { method: "POST" });
}

export function confirmMfa(code: string): Promise<ApiResult<{ backup_codes?: string[] }>> {
  return authenticatedRequest(`/v1/auth/mfa/confirm`, { method: "POST", body: { code } });
}

export function disableMfa(password: string, code: string): Promise<ApiResult<Record<string, unknown>>> {
  return authenticatedRequest(`/v1/auth/mfa/disable`, { method: "POST", body: { password, code } });
}

/** Regenerating backup codes invalidates all previous ones (real backend
 * behavior, confirmed by audit) -- requires a current TOTP code, not the
 * password, to prevent abuse if the phone is briefly unlocked. */
export function regenerateBackupCodes(code: string): Promise<ApiResult<{ backup_codes: string[]; message: string }>> {
  return authenticatedRequest(`/v1/auth/mfa/backup-codes/regenerate`, { method: "POST", body: { code } });
}
