/**
 * `GET /v1/auth/sessions`, `DELETE /v1/auth/sessions/{id}`,
 * `PUT /v1/auth/password/change`, `POST /v1/auth/logout-all`,
 * `POST /v1/auth/mfa/{setup,confirm,disable}` -- all confirmed real,
 * role-generic routes in `app/engines/auth/router.py` (any authenticated
 * user, including customer).
 */
import { z } from "zod";

// CORRECTION (Account Security phase): the real `AuthService.list_sessions`
// response key is `session_id`, not `id` (confirmed via direct source
// read) -- the prior schema required a field the backend never sends, so
// every real fetch would fail zod validation with a ContractValidationError.
//
// Manage Sessions phase: added `channel` (derived server-side from
// `device_type`, never fabricated client-side) and `created_at`.
// `ip_address` deliberately absent -- the backend no longer returns it to
// this contract (full IP was never meant to reach the customer client).
export const sessionDtoSchema = z.object({
  session_id: z.string(),
  device_name: z.string().nullable().optional(),
  device_type: z.string().nullable().optional(),
  channel: z.string(),
  is_current: z.boolean(),
  is_trusted: z.boolean(),
  last_active_at: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
}).passthrough();

export const sessionsListResponseSchema = z.object({
  sessions: z.array(sessionDtoSchema),
  total: z.number(),
});
export type SessionDto = z.infer<typeof sessionDtoSchema>;

// `PasswordChangeRequest` requires all three fields, including
// `confirm_password` (confirmed in `app/engines/auth/schemas.py`) -- the
// prior frontend contract omitted it, meaning every real call would 422.
export const changePasswordRequestSchema = z.object({
  current_password: z.string().min(1),
  new_password: z.string().min(8),
  confirm_password: z.string().min(8),
});
export type ChangePasswordRequest = z.infer<typeof changePasswordRequestSchema>;

export const changePasswordResponseSchema = z.object({
  message: z.string(),
  other_sessions_revoked: z.number().optional(),
}).passthrough();

export const logoutAllResponseSchema = z.object({
  sessions_revoked: z.number(),
  message: z.string(),
});

export const revokeOtherSessionsResponseSchema = z.object({
  sessions_revoked: z.number(),
  active_session_count: z.number(),
  message: z.string(),
});

export const mfaSetupResponseSchema = z.object({
  secret: z.string(),
  qr_uri: z.string(),
  backup_codes: z.array(z.string()),
  backup_codes_remaining: z.number(),
});

export const mfaConfirmResponseSchema = z.object({
  mfa_enabled: z.boolean(),
  message: z.string(),
});

export const mfaDisableResponseSchema = z.object({
  mfa_enabled: z.boolean(),
  message: z.string(),
});

// Login Activity phase: `GET /v1/auth/me/login-activity` -- deliberately a
// SEPARATE, allowlisted contract from the admin/tenant-owner
// `/login-history` route. No ip_address/failure_reason/raw event_type.
export const loginActivityEventDtoSchema = z.object({
  event_id: z.string(),
  label: z.string(),
  outcome: z.enum(["successful", "verification_required", "blocked", "unknown"]),
  channel: z.string(),
  device_name: z.string().nullable(),
  is_current_device: z.boolean(),
  occurred_at: z.string(),
});
export type LoginActivityEventDto = z.infer<typeof loginActivityEventDtoSchema>;

export const loginActivityResponseSchema = z.object({
  events: z.array(loginActivityEventDtoSchema),
  next_cursor: z.string().nullable(),
});
