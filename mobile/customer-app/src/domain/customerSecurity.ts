import { ServerTimestamp } from "./dates";

export interface CustomerSession {
  sessionId: string;
  deviceName: string | null;
  /** Derived server-side from the real stored `device_type` -- "Mobile" or
   * "Web" (spec section 4/7). Never a raw browser/OS string. */
  channel: string;
  isCurrent: boolean;
  isTrusted: boolean;
  lastActiveAt: ServerTimestamp | null;
  createdAt: ServerTimestamp | null;
}

/**
 * Every action gated by a confirmed real backend route (`app/engines/auth/
 * router.py`, audited this phase) -- never a decorative row. `canSetupMfa`/
 * `canDisableMfa` reflect that the full enrollment contract (setup ->
 * confirm -> enabled, password+TOTP-gated disable) genuinely exists.
 */
export interface SecurityCapabilities {
  canChangePassword: boolean;
  canRequestPasswordReset: boolean;
  canSetupMfa: boolean;
  canDisableMfa: boolean;
  canListSessions: boolean;
  canRevokeSession: boolean;
  canManageSessions: boolean;
  canRevokeOtherSessions: boolean;
  canGlobalLogout: boolean;
}

export interface MfaEnrollment {
  secret: string;
  qrUri: string;
  backupCodes: string[];
}

export type LoginActivityOutcome = "successful" | "verification_required" | "blocked" | "unknown";

/** Every field here is an explicit allowlist match to
 * `AuthService.get_my_login_activity`'s response -- no raw IP, no
 * failure_reason, no raw backend event_type string (Login Activity
 * phase). No approximate-location field exists: this backend has no
 * geo-lookup capability, so none is fabricated here either. */
export interface LoginActivityEvent {
  eventId: string;
  label: string;
  outcome: LoginActivityOutcome;
  channel: string;
  deviceName: string | null;
  isCurrentDevice: boolean;
  occurredAt: ServerTimestamp;
}

export type LoginActivityFilter = "all" | "successful" | "needs_attention";
