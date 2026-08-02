import {
  AccessContext, BootstrapState, GuardResult, ReasonCode, RootDestination,
  MOBILE_ALLOWED_ROLES, MOBILE_ALLOWED_AUDIENCE,
} from "./types";

/** Confirmed live against the real backend's ROLE_PERMISSIONS
 * (app/core/permissions.py) -- the technician role's field-work
 * permission, also grantable to `staff` via StaffPermission overrides. */
const STAFF_FIELD_WORK_CAPABILITY = "field_ops:jobs:read";

/**
 * Guard order steps 1-9 (spec section 5): bootstrap complete -> version ->
 * session validity -> audience -> role -> tenant existence/status ->
 * technician existence/status -> authenticated_ready. Steps 10-12
 * (capability/entity/action) are route- and job-scoped and live in
 * resolveAuthorizedRoute / validateJobRoute -- they run only once this
 * function has already returned authenticated_ready.
 *
 * This function is pure and deterministic: same inputs always produce the
 * same BootstrapState + reason code, so it can't produce a redirect loop by
 * itself (RootNavigator renders directly from its output, it never re-calls
 * it in response to its own output).
 */
export interface ResolveNavigationStateInput {
  bootstrapPhase: "initializing" | "restored";
  accessContext: AccessContext;
  currentAppVersion: string;
}

export interface ResolveNavigationStateResult {
  state: BootstrapState;
  reasonCode?: ReasonCode;
}

function isVersionBelow(current: string, minimum: string): boolean {
  const c = current.split(".").map(n => parseInt(n, 10) || 0);
  const m = minimum.split(".").map(n => parseInt(n, 10) || 0);
  for (let i = 0; i < Math.max(c.length, m.length); i++) {
    const cv = c[i] ?? 0;
    const mv = m[i] ?? 0;
    if (cv !== mv) return cv < mv;
  }
  return false;
}

function isSessionExpired(sessionExpiry: string | undefined): boolean {
  if (!sessionExpiry) return false;
  const expiry = Date.parse(sessionExpiry);
  if (Number.isNaN(expiry)) return false;
  return expiry <= Date.now();
}

/** Steps 1-9 of the guard order, collapsed into one bootstrap-state result. */
export function resolveNavigationState({ bootstrapPhase, accessContext, currentAppVersion }: ResolveNavigationStateInput): ResolveNavigationStateResult {
  // 1. Bootstrap complete
  if (bootstrapPhase === "initializing") return { state: "initializing" };

  // 2. Minimum app version supported
  if (accessContext.minimumSupportedAppVersion && isVersionBelow(currentAppVersion, accessContext.minimumSupportedAppVersion)) {
    return { state: "update_required", reasonCode: "APP_UPDATE_REQUIRED" };
  }

  // 3. Valid authenticated session (existence AND non-expiry -- a stored
  // token is never treated as valid merely because it exists).
  if (!accessContext.authenticated) return { state: "unauthenticated", reasonCode: "SESSION_REQUIRED" };
  if (isSessionExpired(accessContext.sessionExpiry)) return { state: "unauthenticated", reasonCode: "SESSION_EXPIRED" };

  // 4. Correct mobile audience
  if (accessContext.audience !== MOBILE_ALLOWED_AUDIENCE) {
    return { state: "access_denied", reasonCode: "WRONG_AUDIENCE" };
  }

  // 5. Allowed canonical role -- never expanded to make navigation "work".
  if (!accessContext.canonicalRole || !MOBILE_ALLOWED_ROLES.has(accessContext.canonicalRole)) {
    return { state: "access_denied", reasonCode: "ROLE_NOT_ALLOWED" };
  }

  // 5b. Office staff are NOT admitted merely for belonging to the tenant
  // (Phase G spec section 9): a `staff` role additionally needs the real,
  // backend-issued field-work capability confirmed live against
  // ROLE_PERMISSIONS (app/core/permissions.py) -- "field_ops:jobs:read".
  // `technician` never needs this extra check; it's already a field role.
  if (accessContext.canonicalRole === "staff" && !(accessContext.capabilities ?? []).includes(STAFF_FIELD_WORK_CAPABILITY)) {
    return { state: "access_denied", reasonCode: "CAPABILITY_REQUIRED" };
  }

  // 6/7. Tenant exists and is active
  if (!accessContext.tenantId) return { state: "access_denied", reasonCode: "TENANT_CONTEXT_MISSING" };
  if (accessContext.tenantStatus !== "active") return { state: "tenant_suspended", reasonCode: "TENANT_INACTIVE" };

  // 8/9. Technician/field identity exists and is active -- required for
  // BOTH technician and (capability-gated) staff, proving a real
  // ProviderTeamMember link rather than bare tenant membership.
  if (!accessContext.technicianId) return { state: "access_denied", reasonCode: "TECHNICIAN_CONTEXT_MISSING" };
  if (accessContext.technicianStatus === "pending") return { state: "account_pending" };
  if (accessContext.technicianStatus === "suspended") return { state: "account_suspended" };
  if (accessContext.technicianStatus !== "active") return { state: "technician_inactive", reasonCode: "TECHNICIAN_INACTIVE" };

  return { state: "authenticated_ready" };
}

/** Maps a BootstrapState to its single deterministic RootNavigator destination. */
export function destinationForBootstrapState(state: BootstrapState, reasonCode?: ReasonCode): RootDestination {
  switch (state) {
    case "initializing":
      return { tree: "Bootstrap" };
    case "unauthenticated":
      return { tree: "AuthStack", screen: "Login", reasonCode };
    case "authenticated_loading_context":
      return { tree: "Bootstrap" };
    case "authenticated_ready":
      return { tree: "AppTabs" };
    case "account_pending":
      return { tree: "RestrictedStateStack", screen: "AccountPending", reasonCode: reasonCode ?? "TECHNICIAN_INACTIVE" };
    case "account_suspended":
      return { tree: "RestrictedStateStack", screen: "AccountSuspended", reasonCode: reasonCode ?? "TECHNICIAN_INACTIVE" };
    case "tenant_suspended":
      return { tree: "RestrictedStateStack", screen: "TenantSuspended", reasonCode: reasonCode ?? "TENANT_INACTIVE" };
    case "technician_inactive":
      return { tree: "RestrictedStateStack", screen: "TechnicianInactive", reasonCode: reasonCode ?? "TECHNICIAN_INACTIVE" };
    case "access_denied":
      return { tree: "RestrictedStateStack", screen: "AccessDenied", reasonCode: reasonCode ?? "ROLE_NOT_ALLOWED" };
    case "update_required":
      return { tree: "RestrictedStateStack", screen: "AppUpdateRequired", reasonCode: reasonCode ?? "APP_UPDATE_REQUIRED" };
    case "service_unavailable":
      return { tree: "RestrictedStateStack", screen: "ServiceUnavailable", reasonCode: reasonCode ?? "ROLE_NOT_ALLOWED" };
    default: {
      // Unknown backend state fails closed rather than guessing a route.
      const _exhaustive: never = state;
      return { tree: "RestrictedStateStack", screen: "ServiceUnavailable", reasonCode: "ROLE_NOT_ALLOWED" };
    }
  }
}

export function resolveRootDestination(input: ResolveNavigationStateInput): { destination: RootDestination; state: BootstrapState; reasonCode?: ReasonCode } {
  const { state, reasonCode } = resolveNavigationState(input);
  return { destination: destinationForBootstrapState(state, reasonCode), state, reasonCode };
}

/** Step 10: does the access context carry the capability a route requires. */
export function checkCapability(accessContext: AccessContext, requiredCapability: string | undefined): GuardResult {
  if (!requiredCapability) return { allowed: true };
  if ((accessContext.capabilities ?? []).includes(requiredCapability)) return { allowed: true };
  return { allowed: false, reasonCode: "CAPABILITY_REQUIRED", destination: { tree: "AppTabs" } };
}
