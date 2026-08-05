import { CustomerProfileDto } from "../../api/contracts/customer";

export function makeCustomerProfileDto(overrides: Partial<CustomerProfileDto> = {}): CustomerProfileDto {
  return {
    id: "customer-33333333-3333-3333-3333-333333333333",
    user_id: "customer-33333333-3333-3333-3333-333333333333",
    full_name: "Asha Rao",
    display_name: "Asha",
    phone: "+919900000000",
    email: "asha@example.com",
    language: "en",
    timezone: "Asia/Kolkata",
    role: "customer",
    tenant_id: null,
    is_active: true,
    is_verified: true,
    is_mfa_enabled: false,
    avatar_url: null,
    profile_photo_media_id: null,
    last_login_at: null,
    created_at: "2025-01-15T08:00:00Z",
    ...overrides,
  };
}
