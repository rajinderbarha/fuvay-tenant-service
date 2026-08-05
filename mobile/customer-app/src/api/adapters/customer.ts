import { CustomerProfileDto, customerProfileDtoSchema } from "../contracts/customer";
import { CustomerProfile, CustomerProfileCapabilities } from "../../domain/customer";
import { asCustomerId } from "../../domain/ids";
import { parseServerTimestamp } from "../../domain/dates";
import { ContractValidationError } from "../../domain/errors";

export function parseCustomerProfileDto(raw: unknown): CustomerProfileDto {
  const result = customerProfileDtoSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("CustomerProfileDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

/**
 * Capabilities are derived from confirmed real routes/config, not
 * optimistic assumptions (spec section 4):
 * - canEditProfile: `PUT /v1/customer/profile` exists (full_name/
 *   display_name/language/timezone) -- confirmed.
 * - canUpdateAvatar: false. `avatar_url` is a real field, but no
 *   confirmed pick-image -> upload -> URL pipeline exists for customer
 *   profile photos this task -- showing a picker without one would write
 *   a local-only image or a raw string, never a real upload.
 * - canManageAddresses: false. No customer address CRUD engine was found
 *   (only Home's ZIP-level serviceability check) -- Profile shows a
 *   read-only default-address preview instead.
 * - canChangePassword: true. `PUT /v1/auth/password/change` is real and
 *   role-generic (any authenticated user, confirmed in auth/router.py).
 * - canManageSessions: true. `GET /v1/auth/sessions` +
 *   `DELETE /v1/auth/sessions/{id}` are real and role-generic.
 * - canDeleteAccount: false. No DPDP-compliant deletion workflow exists.
 */
function deriveProfileCapabilities(): CustomerProfileCapabilities {
  return {
    canEditProfile: true,
    canUpdateAvatar: false,
    canManageAddresses: false,
    canChangePassword: true,
    canManageSessions: true,
    canDeleteAccount: false,
  };
}

export function adaptCustomerProfile(dto: CustomerProfileDto): CustomerProfile {
  return {
    id: asCustomerId(dto.id),
    fullName: dto.full_name,
    displayName: dto.display_name,
    phone: dto.phone,
    email: dto.email,
    avatarUrl: dto.avatar_url,
    language: dto.language,
    timezone: dto.timezone,
    verified: dto.is_verified,
    mfaEnabled: dto.is_mfa_enabled,
    isActive: dto.is_active,
    createdAt: parseServerTimestamp(dto.created_at, "created_at"),
    capabilities: deriveProfileCapabilities(),
  };
}
