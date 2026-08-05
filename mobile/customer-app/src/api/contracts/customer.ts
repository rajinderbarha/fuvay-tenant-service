/**
 * DTO for `GET`/`PUT /v1/customer/profile` (`app/engines/profile/router.py`
 * + `ProfileService._serialize_user`, read directly this task).
 *
 * CORRECTION (2026-08-01, Profile Root Tab phase): the prior schema here
 * required `account_status` and expected `photo_url` -- neither field
 * exists in the real serializer output (confirmed via direct source
 * read; the file this schema's old comment cited,
 * `profile_edit_router.py`, does not exist in this codebase). Every real
 * fetch against the actual backend would have failed zod validation with
 * a `ContractValidationError` since `account_status` is genuinely absent.
 * This is now verified against the real, single source of truth.
 */
import { z } from "zod";

export const customerProfileDtoSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  email: z.string().nullable(),
  phone: z.string().nullable(),
  full_name: z.string().nullable(),
  display_name: z.string().nullable(),
  language: z.string(),
  timezone: z.string(),
  role: z.string(),
  tenant_id: z.string().nullable(),
  is_active: z.boolean(),
  // Confirmed: a SINGLE combined verification flag -- there is no
  // separate mobile_verified/email_verified field in the real response.
  // Never split this into two badges the backend doesn't actually report.
  is_verified: z.boolean(),
  is_mfa_enabled: z.boolean(),
  avatar_url: z.string().nullable(),
  profile_photo_media_id: z.string().nullable().optional(),
  last_login_at: z.string().nullable(),
  created_at: z.string(),
}).passthrough();
export type CustomerProfileDto = z.infer<typeof customerProfileDtoSchema>;

/** `PUT /v1/customer/profile` accepts exactly these fields (confirmed via
 * `UpdateUserProfileRequest`); phone changes bypass OTP re-verification in
 * the current implementation despite the route's own docstring claiming
 * otherwise (confirmed via direct read of `ProfileService.
 * update_user_profile` -- disclosed as a real, if surprising, backend
 * behavior, not something this app can fix from the client). */
export const updateCustomerProfileRequestSchema = z.object({
  full_name: z.string().min(2).max(255).optional(),
  display_name: z.string().min(1).max(255).optional(),
  language: z.string().optional(),
  timezone: z.string().optional(),
});
export type UpdateCustomerProfileRequest = z.infer<typeof updateCustomerProfileRequestSchema>;
