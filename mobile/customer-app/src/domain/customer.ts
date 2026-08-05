import { CustomerId } from "./ids";
import { ServerTimestamp } from "./dates";

/** Derived from real endpoint/config existence, never an optimistic
 * frontend assumption (spec section 4). See
 * api/adapters/customer.ts::deriveProfileCapabilities for the exact
 * source-verified reasoning behind each flag. */
export interface CustomerProfileCapabilities {
  canEditProfile: boolean;
  canUpdateAvatar: boolean;
  canManageAddresses: boolean;
  canChangePassword: boolean;
  canManageSessions: boolean;
  canDeleteAccount: boolean;
}

export interface CustomerProfile {
  id: CustomerId;
  fullName: string | null;
  displayName: string | null;
  phone: string | null;
  email: string | null;
  avatarUrl: string | null;
  language: string;
  timezone: string;
  /** SINGLE combined flag -- the real backend has no separate mobile/
   * email verification state (see contracts/customer.ts). Never rendered
   * as two badges. */
  verified: boolean;
  /** Real backend flag (`User.is_mfa_enabled`) -- never inferred from
   * whether the customer encountered an MFA challenge during one login. */
  mfaEnabled: boolean;
  isActive: boolean;
  createdAt: ServerTimestamp;
  capabilities: CustomerProfileCapabilities;
}
