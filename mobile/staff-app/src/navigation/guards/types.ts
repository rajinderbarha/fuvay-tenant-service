/**
 * Phase E — shared guard/session types. This is the normalized mobile
 * access context (spec section 4): every field here is backend-authoritative
 * and arrives through an injectable session adapter (see ../session), never
 * chosen by the client. Canonical role/audience names mirror the real
 * backend registry (app/core/permissions.py ROLE_PERMISSIONS,
 * app/engines/auth/constants.py ROLES/AUDIENCE) -- not invented here.
 */

export type CanonicalRole =
  | "super_admin"
  | "admin_operations"
  | "admin_finance"
  | "admin_security"
  | "admin_readonly"
  | "tenant_owner"
  | "staff"
  | "technician"
  | "customer"
  | "guest";

/** Mirrors app/engines/auth/constants.py AUDIENCE values. */
export type Audience = "serviceos:admin" | "serviceos:tenant" | "serviceos:staff" | "serviceos:customer";

/** Canonical roles this mobile app is allowed to operate as (spec section 4).
 * `staff` is included only because the backend audience for `technician`
 * capabilities is shared with `staff` in some tenants (explicitly authorized
 * field staff) -- this app never grants tenant-admin capabilities to either. */
export const MOBILE_ALLOWED_ROLES: ReadonlySet<CanonicalRole> = new Set(["technician", "staff"]);
export const MOBILE_ALLOWED_AUDIENCE: Audience = "serviceos:staff";

export type TenantStatus = string; // backend-defined (e.g. "active", "suspended", "terminated")
export type TechnicianStatus = string; // backend-defined (e.g. "active", "inactive", "suspended", "pending")

export interface AccessContext {
  authenticated: boolean;
  userId?: string;
  canonicalRole?: CanonicalRole;
  audience?: Audience;
  tenantId?: string;
  tenantStatus?: TenantStatus;
  technicianId?: string;
  technicianStatus?: TechnicianStatus;
  enabledVerticals?: string[];
  capabilities?: string[];
  /** ISO 8601 timestamp. Session is treated as expired if this is in the past. */
  sessionExpiry?: string;
  minimumSupportedAppVersion?: string;
}

export const UNAUTHENTICATED_CONTEXT: AccessContext = { authenticated: false };

export type BootstrapState =
  | "initializing"
  | "unauthenticated"
  | "authenticated_loading_context"
  | "authenticated_ready"
  | "account_pending"
  | "account_suspended"
  | "tenant_suspended"
  | "technician_inactive"
  | "access_denied"
  | "update_required"
  | "service_unavailable";

/** Every blocked navigation decision must carry one of these (spec section 5). */
export type ReasonCode =
  | "SESSION_REQUIRED"
  | "SESSION_EXPIRED"
  | "WRONG_AUDIENCE"
  | "ROLE_NOT_ALLOWED"
  | "TENANT_CONTEXT_MISSING"
  | "TENANT_INACTIVE"
  | "TECHNICIAN_CONTEXT_MISSING"
  | "TECHNICIAN_INACTIVE"
  | "CAPABILITY_REQUIRED"
  | "ENTITY_NOT_FOUND"
  | "ENTITY_NOT_ASSIGNED"
  | "ACTION_NOT_ALLOWED"
  | "ROUTE_NOT_FOUND"
  | "APP_UPDATE_REQUIRED";

export type NavigationTree = "Bootstrap" | "AuthStack" | "AppTabs" | "JobExecutionStack" | "RestrictedStateStack";

export type AuthRouteName = "Login" | "OtpVerify" | "Mfa" | "ForgotPassword" | "ResetPassword" | "ResetSuccess";

export type RestrictedRouteName =
  | "AccountPending"
  | "AccountSuspended"
  | "TenantSuspended"
  | "TechnicianInactive"
  | "AccessDenied"
  | "AppUpdateRequired"
  | "ServiceUnavailable";

export interface JobExecutionParams {
  jobId: string;
  jobReference?: string;
  targetAction?: string;
  notificationId?: string;
}

/** One deterministic destination for every access state (spec section 5). */
export type RootDestination =
  | { tree: "Bootstrap" }
  | { tree: "AuthStack"; screen: AuthRouteName; reasonCode?: ReasonCode }
  | { tree: "AppTabs" }
  | { tree: "JobExecutionStack"; screen: string; params: JobExecutionParams }
  | { tree: "RestrictedStateStack"; screen: RestrictedRouteName; reasonCode: ReasonCode };

export interface GuardResult {
  allowed: boolean;
  reasonCode?: ReasonCode;
  destination?: RootDestination;
}
