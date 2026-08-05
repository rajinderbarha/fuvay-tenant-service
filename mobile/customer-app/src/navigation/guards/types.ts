/**
 * Phase E — navigation/guard state types. These are inputs the (Phase F)
 * session/bootstrap layer will eventually populate from real backend
 * state (Phase D `CustomerSessionContext`, capability registry, etc.) --
 * Phase E owns only the pure decision logic that consumes them, never a
 * live data source. Mirrors the Staff App's guard/types.ts shape so both
 * apps share one mental model, but every union here is customer-specific
 * (no staff/tenant/admin concepts leak in).
 */
import { CustomerAudience } from "../../domain/auth";
import { VerticalKey } from "../../domain/catalog";

export type BootstrapStatus =
  | "initializing"
  | "resolving_config"
  | "resolving_session"
  | "resolving_deep_link"
  | "ready"
  | "failed";

export type AuthNavigationStatus =
  | "unknown"
  | "unauthenticated"
  | "authenticated_customer"
  | "session_expired"
  | "invalid_audience";

export type AccountAccessStatus = "active" | "suspended" | "rejected" | "disabled";

export type AppVersionStatus = "supported" | "update_available" | "update_required" | "unsupported";

export type PlatformAvailabilityStatus = "available" | "maintenance" | "api_unavailable";

export type StorageStatus = "available" | "unavailable" | "corrupted";

export type NetworkStatus = "online" | "offline" | "unknown";

/** Which verticals are currently enabled -- consumed by deep-link/vertical
 * guards (spec section 15). Never a hardcoded permanent set; Home
 * Services being first-launch priority is a product default, not a
 * navigation-layer assumption. */
export interface EnabledVerticalSummary {
  enabled: readonly VerticalKey[];
}

export type PendingDeepLinkRejectReason =
  | "unknown_route"
  | "malformed_params"
  | "requires_auth"
  | "wrong_audience"
  | "vertical_disabled"
  | "capability_unavailable"
  | "expired";

export interface PendingDeepLink {
  routeKey: string;
  params: Record<string, string>;
  /** Set once validated -- an unvalidated link must never be navigated to. */
  validated: boolean;
  rejectedReason?: PendingDeepLinkRejectReason;
}

/** Full input to the pure route resolver (spec section 10). Every field is
 * a snapshot value, never a live store reference -- the resolver must be
 * callable in a test with plain objects and no React context. */
export interface AppNavigationSnapshot {
  bootstrap: BootstrapStatus;
  auth: AuthNavigationStatus;
  audience: CustomerAudience | string | null;
  account: AccountAccessStatus;
  appVersion: AppVersionStatus;
  platform: PlatformAvailabilityStatus;
  storage: StorageStatus;
  network: NetworkStatus;
  enabledVerticals: EnabledVerticalSummary;
  pendingDeepLink?: PendingDeepLink;
}

export type NavigationTree =
  | "Bootstrap"
  | "PublicStack"
  | "CustomerAppStack"
  | "ExceptionalStateStack";

export type ExceptionalRouteName =
  | "PreparingExperience"
  | "SessionExpired"
  | "AccountSuspended"
  | "UpdateRequired"
  | "Maintenance"
  | "ApiUnavailable"
  | "StorageUnavailable"
  | "VerticalUnavailable"
  | "InvalidAccess";

export type PublicRouteName =
  | "LoginMethod"
  | "VerifyLoginOtp"
  | "PasswordLogin"
  | "MfaChallenge"
  | "RecoveryCodeChallenge"
  | "ForgotPasswordRequest"
  | "ResetPasswordConfirm";

/** One deterministic destination for every navigation snapshot (spec
 * section 10-11) -- resolveDestination() below is the only function
 * allowed to produce one of these. */
export type RootDestination =
  | { tree: "Bootstrap" }
  | { tree: "PublicStack"; screen: PublicRouteName }
  | { tree: "CustomerAppStack"; pendingDeepLink?: PendingDeepLink }
  | { tree: "ExceptionalStateStack"; screen: ExceptionalRouteName; reason: string };
