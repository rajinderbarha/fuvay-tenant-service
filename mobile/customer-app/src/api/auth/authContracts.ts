/**
 * DTO contracts for the auth engine, verified directly against
 * app/engines/auth/router.py + service.py this phase (not just OpenAPI
 * path existence -- every field below traces to a specific `return {...}`
 * in AuthService).
 */
import { z } from "zod";

// POST /v1/auth/login, /v1/auth/otp/verify, /v1/auth/mfa/verify all
// return one of two shapes: an MFA challenge, or a token bundle. Modeled
// as a discriminated union on `mfa_required` (present on all three per
// AuthService.login/verify_phone_otp_login/verify_mfa).
export const mfaChallengeResponseSchema = z.object({
  mfa_required: z.literal(true),
  mfa_challenge_token: z.string(),
});
export type MfaChallengeResponseDto = z.infer<typeof mfaChallengeResponseSchema>;

const userProfileDtoSchema = z.object({
  id: z.string(),
  email: z.string().nullable().optional(),
  phone: z.string().nullable().optional(),
  full_name: z.string().nullable().optional(),
  role: z.string(),
}).passthrough();

const tenantContextDtoSchema = z.object({
  id: z.string(),
  name: z.string().nullable().optional(),
  status: z.string().nullable().optional(),
}).nullable();

export const authSessionResponseSchema = z.object({
  mfa_required: z.literal(false).optional(),
  access_token: z.string(),
  refresh_token: z.string().nullable(),
  requires_password_change: z.boolean().optional(),
  next_destination: z.string().nullable().optional(),
  reason_code: z.string().nullable().optional(),
  user: userProfileDtoSchema,
  tenant: tenantContextDtoSchema.optional(),
});
export type AuthSessionResponseDto = z.infer<typeof authSessionResponseSchema>;

export const loginOutcomeSchema = z.union([mfaChallengeResponseSchema, authSessionResponseSchema]);
export type LoginOutcomeDto = z.infer<typeof loginOutcomeSchema>;

// POST /v1/auth/otp/send -- app/engines/auth/service.py send_phone_otp.
// `otp_hint` is a DEV-ONLY field (settings.DEBUG) the backend itself only
// includes outside production -- this client must never log or persist
// it even when present; see api/auth/authAdapters.ts.
export const otpSendResponseSchema = z.object({
  message: z.string(),
  use_verify: z.boolean().optional(),
  otp_hint: z.string().optional(),
});
export type OtpSendResponseDto = z.infer<typeof otpSendResponseSchema>;

// POST /v1/auth/token/refresh -- AuthService.refresh_token. Deliberately
// narrower than the login response: no user/tenant/destination fields are
// returned by this endpoint (confirmed in source), so the schema does not
// invent them.
export const refreshResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
});
export type RefreshResponseDto = z.infer<typeof refreshResponseSchema>;

export const logoutResponseSchema = z.object({ message: z.string() });
export type LogoutResponseDto = z.infer<typeof logoutResponseSchema>;

// GET /v1/auth/access-context -- AuthService.get_mobile_access_context.
// This is the single source of truth for customer role/audience/tenant/
// vertical-enablement guard decisions (Phase E consumes it via
// sessionManager, never a decoded JWT claim).
// POST /v1/auth/password/reset/request -- AuthService.request_password_reset.
// Deliberately enumeration-safe: identical response shape whether or not
// the account exists (source: "Always return success (don't reveal if
// account exists)"). `otp_hint` is DEV-ONLY, same rule as otpSendResponseSchema.
export const passwordResetRequestResponseSchema = z.object({
  message: z.string(),
  otp_hint: z.string().optional(),
});
export type PasswordResetRequestResponseDto = z.infer<typeof passwordResetRequestResponseSchema>;

// POST /v1/auth/password/reset/confirm -- AuthService.confirm_password_reset.
// Confirmed: never returns a session (no access_token/refresh_token field
// exists on this response) -- a reset revokes ALL existing sessions
// server-side and the customer must sign in again afterward.
export const passwordResetConfirmResponseSchema = z.object({
  message: z.string(),
});
export type PasswordResetConfirmResponseDto = z.infer<typeof passwordResetConfirmResponseSchema>;

export const accessContextResponseSchema = z.object({
  user_id: z.string(),
  canonical_role: z.string(),
  audience: z.string(),
  tenant_id: z.string().nullable(),
  tenant_status: z.string().nullable(),
  technician_id: z.string().nullable(),
  technician_status: z.string().nullable(),
  enabled_verticals: z.array(z.string()),
  capabilities: z.array(z.string()),
});
export type AccessContextResponseDto = z.infer<typeof accessContextResponseSchema>;
