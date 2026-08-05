import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import {
  sessionsListResponseSchema, changePasswordRequestSchema, ChangePasswordRequest,
  changePasswordResponseSchema, logoutAllResponseSchema, revokeOtherSessionsResponseSchema,
  mfaSetupResponseSchema, mfaConfirmResponseSchema, mfaDisableResponseSchema,
  loginActivityResponseSchema,
} from "../contracts/customerSecurity";
import { LoginActivityFilter } from "../../domain/customerSecurity";
import { z } from "zod";

export async function listMySessions() {
  const res = await authenticatedRequest({ method: "GET", path: "/v1/auth/sessions" });
  return parseApiSuccess(res.json, sessionsListResponseSchema);
}

export async function revokeSession(sessionId: string) {
  const res = await authenticatedRequest({ method: "DELETE", path: `/v1/auth/sessions/${sessionId}` });
  return parseApiSuccess(res.json, z.object({ session_id: z.string(), revoked: z.boolean() }));
}

export async function changePassword(body: ChangePasswordRequest) {
  const parsed = changePasswordRequestSchema.parse(body);
  const res = await authenticatedRequest({ method: "PUT", path: "/v1/auth/password/change", body: parsed });
  return parseApiSuccess(res.json, changePasswordResponseSchema);
}

export async function logoutAllSessions() {
  const res = await authenticatedRequest({ method: "POST", path: "/v1/auth/logout-all" });
  return parseApiSuccess(res.json, logoutAllResponseSchema);
}

/** `POST /v1/auth/sessions/revoke-all-other` -- fixed this phase to
 * genuinely exclude the caller's own session (previously revoked
 * everything despite its docstring's "except current" promise). */
export async function revokeOtherSessions() {
  const res = await authenticatedRequest({ method: "POST", path: "/v1/auth/sessions/revoke-all-other" });
  return parseApiSuccess(res.json, revokeOtherSessionsResponseSchema);
}

export async function setupMfa() {
  const res = await authenticatedRequest({ method: "POST", path: "/v1/auth/mfa/setup" });
  return parseApiSuccess(res.json, mfaSetupResponseSchema);
}

export async function confirmMfa(code: string) {
  const res = await authenticatedRequest({ method: "POST", path: "/v1/auth/mfa/confirm", body: { code } });
  return parseApiSuccess(res.json, mfaConfirmResponseSchema);
}

export async function disableMfa(password: string, code: string) {
  const res = await authenticatedRequest({ method: "POST", path: "/v1/auth/mfa/disable", body: { password, code } });
  return parseApiSuccess(res.json, mfaDisableResponseSchema);
}

/** `GET /v1/auth/me/login-activity` -- distinct, allowlisted route from
 * the admin/tenant-owner `/login-history` endpoint. */
export async function getMyLoginActivity(filter: LoginActivityFilter, cursor?: string) {
  const params = new URLSearchParams({ filter });
  if (cursor) params.set("cursor", cursor);
  const res = await authenticatedRequest({ method: "GET", path: `/v1/auth/me/login-activity?${params.toString()}` });
  return parseApiSuccess(res.json, loginActivityResponseSchema);
}
