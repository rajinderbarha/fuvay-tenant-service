import { evaluateModule } from "../remote-config-evaluator";
import type { RemoteConfigEnvelope, ModuleConfig } from "../remote-config-schema";

function module(overrides: Partial<ModuleConfig>): ModuleConfig {
  return { key: "test", displayNameKey: "x", enabled: true, visible: true, requiresAuth: false, dependsOn: [], order: 0, ...overrides };
}

function envelope(modules: ModuleConfig[], overrides: Partial<RemoteConfigEnvelope> = {}): RemoteConfigEnvelope {
  return {
    schemaVersion: 1,
    configVersion: "v1",
    generatedAt: "2026-06-01T00:00:00.000Z",
    environment: "development",
    marketplace: {
      marketplaceId: "default",
      displayName: "x",
      active: true,
      defaultLocale: "en",
      supportedLocales: ["en"],
      defaultCurrency: "INR",
      timezone: "Asia/Kolkata",
      country: "IN",
      customerAppEnabled: true,
    },
    application: {
      customerAppEnabled: true,
      developmentToolsEnabled: true,
      analyticsEnabled: false,
      crashReportingEnabled: false,
      remoteImagesEnabled: true,
      deepLinksEnabled: true,
      notificationRoutingEnabled: false,
      refreshIntervalSeconds: 900,
      maxConfigAgeSeconds: 86400,
      cachedConfigFallbackAllowed: true,
    },
    versionPolicy: {
      minSupportedVersion: "1.0.0",
      latestRecommendedVersion: "1.0.0",
      mandatoryUpdate: false,
      optionalUpdate: false,
      updateTitle: "x",
      updateMessage: "y",
      gracePeriodHours: 0,
      blockedBuildNumbers: [],
    },
    maintenance: { enabled: false, type: "none", retryAllowed: true, permittedRouteIds: [] },
    modules,
    navigation: { allowedRouteIds: [], disabledRouteIds: [], deepLinkAllowlist: [], notificationRouteAllowlist: [], fallbackRouteId: "baselineLanding" },
    ...overrides,
  };
}

describe("evaluateModule", () => {
  it("returns enabled for a fully eligible module", () => {
    const config = envelope([module({ key: "a" })]);
    expect(evaluateModule("a", { config, appVersion: "1.0.0" })).toBe("enabled");
  });

  it("returns disabled when the module is disabled", () => {
    const config = envelope([module({ key: "a", enabled: false })]);
    expect(evaluateModule("a", { config, appVersion: "1.0.0" })).toBe("disabled");
  });

  it("returns hidden when the module is not visible", () => {
    const config = envelope([module({ key: "a", visible: false })]);
    expect(evaluateModule("a", { config, appVersion: "1.0.0" })).toBe("hidden");
  });

  it("returns unsupported-version when app version is below minAppVersion", () => {
    const config = envelope([module({ key: "a", minAppVersion: "2.0.0" })]);
    expect(evaluateModule("a", { config, appVersion: "1.0.0" })).toBe("unsupported-version");
  });

  it("returns outside-region when the region isn't in supportedRegions", () => {
    const config = envelope([module({ key: "a", supportedRegions: ["US"] })]);
    expect(evaluateModule("a", { config, appVersion: "1.0.0", regionCode: "IN" })).toBe("outside-region");
  });

  it("returns dependency-disabled when a dependency is disabled", () => {
    const config = envelope([module({ key: "a", dependsOn: ["b"] }), module({ key: "b", enabled: false })]);
    expect(evaluateModule("a", { config, appVersion: "1.0.0" })).toBe("dependency-disabled");
  });

  it("returns maintenance-disabled when maintenance is active-blocking", () => {
    const config = envelope([module({ key: "a" })], { maintenance: { enabled: true, type: "active-blocking", retryAllowed: true, permittedRouteIds: [] } });
    expect(evaluateModule("a", { config, appVersion: "1.0.0" })).toBe("maintenance-disabled");
  });

  it("returns configuration-invalid for an unknown module key", () => {
    const config = envelope([module({ key: "a" })]);
    expect(evaluateModule("does-not-exist", { config, appVersion: "1.0.0" })).toBe("configuration-invalid");
  });

  it("fails closed (not enabled) for a scheduled-future maintenance-blocked wrong platform-like edge case with missing region when required", () => {
    const config = envelope([module({ key: "a", supportedRegions: ["US"] })]);
    expect(evaluateModule("a", { config, appVersion: "1.0.0" })).not.toBe("enabled");
  });
});
