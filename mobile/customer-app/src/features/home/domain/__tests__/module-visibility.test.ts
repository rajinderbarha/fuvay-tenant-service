import { evaluateModuleVisibility, filterVisibleModules } from "../module-visibility";
import type { HomeModuleEnvelope } from "../home-module-types";

function module(overrides: Partial<HomeModuleEnvelope> = {}): HomeModuleEnvelope {
  return { id: "m1", type: "category-grid", order: 0, critical: true, requiresAuth: true, ...overrides };
}

describe("evaluateModuleVisibility", () => {
  it("is VISIBLE for a valid, authenticated, in-version module", () => {
    expect(evaluateModuleVisibility(module(), { authenticated: true, appVersion: "1.0.0" })).toBe("VISIBLE");
  });

  it("is CONFIGURATION_INVALID for an unrecognized module type", () => {
    expect(evaluateModuleVisibility(module({ type: "totally-unknown-type" }), { authenticated: true, appVersion: "1.0.0" })).toBe("CONFIGURATION_INVALID");
  });

  it("is DISABLED when explicitly disabled by context", () => {
    expect(evaluateModuleVisibility(module(), { authenticated: true, appVersion: "1.0.0", enabled: false })).toBe("DISABLED");
  });

  it("is AUTH_REQUIRED when the module requires auth and the customer is a guest", () => {
    expect(evaluateModuleVisibility(module({ requiresAuth: true }), { authenticated: false, appVersion: "1.0.0" })).toBe("AUTH_REQUIRED");
  });

  it("does not require auth for a module that doesn't need it", () => {
    expect(evaluateModuleVisibility(module({ requiresAuth: false }), { authenticated: false, appVersion: "1.0.0" })).toBe("VISIBLE");
  });

  it("is UNSUPPORTED_VERSION when the app version is below the module's minimum", () => {
    expect(evaluateModuleVisibility(module({ minAppVersion: "2.0.0" }), { authenticated: true, appVersion: "1.0.0" })).toBe("UNSUPPORTED_VERSION");
  });

  it("is OUTSIDE_REGION when the region isn't in the module's allowlist", () => {
    expect(evaluateModuleVisibility(module({ regions: ["US"] }), { authenticated: true, appVersion: "1.0.0", regionCode: "IN" })).toBe("OUTSIDE_REGION");
  });

  it("is CONFIGURATION_INVALID for a malformed minAppVersion rather than crashing", () => {
    expect(evaluateModuleVisibility(module({ minAppVersion: "not-a-version" }), { authenticated: true, appVersion: "1.0.0" })).toBe("CONFIGURATION_INVALID");
  });
});

describe("filterVisibleModules", () => {
  it("keeps only visible modules and sorts by order", () => {
    const modules = [
      module({ id: "b", order: 2, requiresAuth: false }),
      module({ id: "a", order: 1, requiresAuth: false }),
      module({ id: "c", order: 0, requiresAuth: true }), // hidden: no auth
    ];
    const result = filterVisibleModules(modules, { authenticated: false, appVersion: "1.0.0" });
    expect(result.map((m) => m.id)).toEqual(["a", "b"]);
  });
});
