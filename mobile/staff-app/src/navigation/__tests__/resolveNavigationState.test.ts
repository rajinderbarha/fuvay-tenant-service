import { resolveNavigationState, destinationForBootstrapState, resolveRootDestination, checkCapability } from "../guards/resolveNavigationState";
import { AccessContext, BootstrapState } from "../guards/types";

const BASE: AccessContext = {
  authenticated: true,
  userId: "u1",
  canonicalRole: "technician",
  audience: "serviceos:staff",
  tenantId: "t1",
  tenantStatus: "active",
  technicianId: "tech1",
  technicianStatus: "active",
};

describe("resolveNavigationState — bootstrap states", () => {
  it("initializing while bootstrap phase is initializing, regardless of access context", () => {
    expect(resolveNavigationState({ bootstrapPhase: "initializing", accessContext: BASE, currentAppVersion: "1.0.0" }).state).toBe("initializing");
  });

  it("unauthenticated with SESSION_REQUIRED when not authenticated", () => {
    const result = resolveNavigationState({ bootstrapPhase: "restored", accessContext: { authenticated: false }, currentAppVersion: "1.0.0" });
    expect(result).toEqual({ state: "unauthenticated", reasonCode: "SESSION_REQUIRED" });
  });

  it("unauthenticated with SESSION_EXPIRED when session expiry is in the past (stored token is not trusted merely for existing)", () => {
    const result = resolveNavigationState({
      bootstrapPhase: "restored",
      accessContext: { ...BASE, sessionExpiry: new Date(Date.now() - 60_000).toISOString() },
      currentAppVersion: "1.0.0",
    });
    expect(result).toEqual({ state: "unauthenticated", reasonCode: "SESSION_EXPIRED" });
  });

  it("update_required when current app version is below minimumSupportedAppVersion", () => {
    const result = resolveNavigationState({
      bootstrapPhase: "restored",
      accessContext: { ...BASE, minimumSupportedAppVersion: "2.0.0" },
      currentAppVersion: "1.0.0",
    });
    expect(result).toEqual({ state: "update_required", reasonCode: "APP_UPDATE_REQUIRED" });
  });

  it("access_denied with WRONG_AUDIENCE for a non-staff audience token", () => {
    const result = resolveNavigationState({ bootstrapPhase: "restored", accessContext: { ...BASE, audience: "serviceos:customer" }, currentAppVersion: "1.0.0" });
    expect(result).toEqual({ state: "access_denied", reasonCode: "WRONG_AUDIENCE" });
  });

  it.each(["super_admin", "admin_operations", "admin_finance", "admin_security", "admin_readonly", "tenant_owner", "customer", "guest"] as const)(
    "access_denied with ROLE_NOT_ALLOWED for role %s",
    (role) => {
      const result = resolveNavigationState({ bootstrapPhase: "restored", accessContext: { ...BASE, canonicalRole: role }, currentAppVersion: "1.0.0" });
      expect(result).toEqual({ state: "access_denied", reasonCode: "ROLE_NOT_ALLOWED" });
    },
  );

  it("staff role WITH the field-work capability (explicitly authorized field staff) is allowed", () => {
    const result = resolveNavigationState({
      bootstrapPhase: "restored",
      accessContext: { ...BASE, canonicalRole: "staff", capabilities: ["field_ops:jobs:read"] },
      currentAppVersion: "1.0.0",
    });
    expect(result.state).toBe("authenticated_ready");
  });

  it("staff role WITHOUT the field-work capability is denied (office staff belonging to the tenant is not enough)", () => {
    const result = resolveNavigationState({
      bootstrapPhase: "restored",
      accessContext: { ...BASE, canonicalRole: "staff", capabilities: [] },
      currentAppVersion: "1.0.0",
    });
    expect(result).toEqual({ state: "access_denied", reasonCode: "CAPABILITY_REQUIRED" });
  });

  it("staff role with unrelated capabilities (no field_ops:jobs:read) is still denied", () => {
    const result = resolveNavigationState({
      bootstrapPhase: "restored",
      accessContext: { ...BASE, canonicalRole: "staff", capabilities: ["settings:read", "chat:messages:read"] },
      currentAppVersion: "1.0.0",
    });
    expect(result.reasonCode).toBe("CAPABILITY_REQUIRED");
  });

  it("access_denied with TENANT_CONTEXT_MISSING when tenantId is absent", () => {
    const result = resolveNavigationState({ bootstrapPhase: "restored", accessContext: { ...BASE, tenantId: undefined }, currentAppVersion: "1.0.0" });
    expect(result).toEqual({ state: "access_denied", reasonCode: "TENANT_CONTEXT_MISSING" });
  });

  it("tenant_suspended with TENANT_INACTIVE when tenant status isn't active", () => {
    const result = resolveNavigationState({ bootstrapPhase: "restored", accessContext: { ...BASE, tenantStatus: "suspended" }, currentAppVersion: "1.0.0" });
    expect(result).toEqual({ state: "tenant_suspended", reasonCode: "TENANT_INACTIVE" });
  });

  it("access_denied with TECHNICIAN_CONTEXT_MISSING when technicianId is absent", () => {
    const result = resolveNavigationState({ bootstrapPhase: "restored", accessContext: { ...BASE, technicianId: undefined }, currentAppVersion: "1.0.0" });
    expect(result).toEqual({ state: "access_denied", reasonCode: "TECHNICIAN_CONTEXT_MISSING" });
  });

  it("account_pending when technician status is pending", () => {
    const result = resolveNavigationState({ bootstrapPhase: "restored", accessContext: { ...BASE, technicianStatus: "pending" }, currentAppVersion: "1.0.0" });
    expect(result.state).toBe("account_pending");
  });

  it("account_suspended when technician status is suspended", () => {
    const result = resolveNavigationState({ bootstrapPhase: "restored", accessContext: { ...BASE, technicianStatus: "suspended" }, currentAppVersion: "1.0.0" });
    expect(result.state).toBe("account_suspended");
  });

  it("technician_inactive with TECHNICIAN_INACTIVE for any other non-active technician status", () => {
    const result = resolveNavigationState({ bootstrapPhase: "restored", accessContext: { ...BASE, technicianStatus: "on_leave" }, currentAppVersion: "1.0.0" });
    expect(result).toEqual({ state: "technician_inactive", reasonCode: "TECHNICIAN_INACTIVE" });
  });

  it("authenticated_ready when every guard passes", () => {
    const result = resolveNavigationState({ bootstrapPhase: "restored", accessContext: BASE, currentAppVersion: "1.0.0" });
    expect(result).toEqual({ state: "authenticated_ready" });
  });
});

describe("destinationForBootstrapState — one deterministic destination per state", () => {
  const cases: [BootstrapState, string][] = [
    ["initializing", "Bootstrap"],
    ["unauthenticated", "AuthStack"],
    ["authenticated_loading_context", "Bootstrap"],
    ["authenticated_ready", "AppTabs"],
    ["account_pending", "RestrictedStateStack"],
    ["account_suspended", "RestrictedStateStack"],
    ["tenant_suspended", "RestrictedStateStack"],
    ["technician_inactive", "RestrictedStateStack"],
    ["access_denied", "RestrictedStateStack"],
    ["update_required", "RestrictedStateStack"],
    ["service_unavailable", "RestrictedStateStack"],
  ];

  it.each(cases)("%s -> %s", (state, tree) => {
    expect(destinationForBootstrapState(state).tree).toBe(tree);
  });

  it("is deterministic: calling twice with the same state yields the same destination", () => {
    const a = destinationForBootstrapState("tenant_suspended", "TENANT_INACTIVE");
    const b = destinationForBootstrapState("tenant_suspended", "TENANT_INACTIVE");
    expect(a).toEqual(b);
  });
});

describe("resolveRootDestination", () => {
  it("combines state + reasonCode + destination for a wrong-audience rejection", () => {
    const result = resolveRootDestination({ bootstrapPhase: "restored", accessContext: { ...BASE, audience: "serviceos:customer" }, currentAppVersion: "1.0.0" });
    expect(result.state).toBe("access_denied");
    expect(result.reasonCode).toBe("WRONG_AUDIENCE");
    expect(result.destination).toEqual({ tree: "RestrictedStateStack", screen: "AccessDenied", reasonCode: "WRONG_AUDIENCE" });
  });
});

describe("checkCapability", () => {
  it("allows a route with no required capability", () => {
    expect(checkCapability(BASE, undefined)).toEqual({ allowed: true });
  });

  it("denies with CAPABILITY_REQUIRED when the capability is missing", () => {
    const result = checkCapability(BASE, "job:estimate:update");
    expect(result.allowed).toBe(false);
    expect(result.reasonCode).toBe("CAPABILITY_REQUIRED");
  });

  it("allows when the capability is present", () => {
    const result = checkCapability({ ...BASE, capabilities: ["job:estimate:update"] }, "job:estimate:update");
    expect(result.allowed).toBe(true);
  });
});
