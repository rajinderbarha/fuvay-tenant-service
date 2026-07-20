import type { AuthUserProfile } from "../api/auth-api-types";

export interface CustomerSession {
  accessToken: string;
  refreshToken: string;
  userId: string;
  fullName: string;
  displayName: string | null;
  phone: string | null;
  email: string;
  language: string;
  role: string;
  tenantId: string | null;
  isVerified: boolean;
  onboardingComplete: boolean;
  avatarUrl: string | null;
}

/**
 * Normalizes the raw backend profile shape into the app's own session
 * model. Screens/hooks consume `CustomerSession`, never the raw
 * `AuthUserProfile` directly, so a future backend field rename doesn't
 * ripple through every screen.
 */
export function toCustomerSession(tokens: { accessToken: string; refreshToken: string }, profile: AuthUserProfile): CustomerSession {
  return {
    accessToken: tokens.accessToken,
    refreshToken: tokens.refreshToken,
    userId: profile.user_id,
    fullName: normalizeDisplayText(profile.full_name),
    displayName: profile.display_name ? normalizeDisplayText(profile.display_name) : null,
    phone: profile.phone,
    email: profile.email,
    language: profile.language,
    role: profile.role,
    tenantId: profile.tenant_id,
    isVerified: profile.is_verified,
    onboardingComplete: profile.onboarding_complete,
    avatarUrl: profile.avatar_url,
  };
}

/** Strips control characters and collapses whitespace so a malformed backend name never breaks layout or accessibility. */
function normalizeDisplayText(value: string): string {
  // eslint-disable-next-line no-control-regex
  return value
    .replace(/[\x00-\x1F\x7F]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function customerInitials(session: Pick<CustomerSession, "fullName">): string {
  const parts = session.fullName.split(" ").filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase();
}
