import { resolveInitialRoute, type StartupRouteResolverInput } from "../startup-route-resolver";
import type { RemoteConfigEnvelope } from "../../../remote-config/remote-config-schema";

function config(overrides: Partial<RemoteConfigEnvelope> = {}): RemoteConfigEnvelope {
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
    modules: [],
    navigation: { allowedRouteIds: [], disabledRouteIds: [], deepLinkAllowlist: [], notificationRouteAllowlist: [], fallbackRouteId: "baselineLanding" },
    ...overrides,
  };
}

function baseInput(overrides: Partial<StartupRouteResolverInput> = {}): StartupRouteResolverInput {
  return {
    environmentValid: true,
    buildSupported: true,
    config: config(),
    configSource: "remote-fresh",
    currentVersion: "1.0.0",
    currentBuildNumber: "1",
    platform: "android",
    connectivity: "online",
    auth: "guest",
    onboarding: "skipped-where-allowed",
    startupFailed: false,
    ...overrides,
  };
}

describe("resolveInitialRoute priority", () => {
  it("routes to unsupportedBuild for an invalid environment, before anything else", () => {
    const decision = resolveInitialRoute(
      baseInput({
        environmentValid: false,
        config: config({ maintenance: { enabled: true, type: "active-blocking", retryAllowed: true, permittedRouteIds: [] } }),
      })
    );
    expect(decision.routeId).toBe("unsupportedBuild");
    expect(decision.reason).toBe("invalid-environment");
  });

  it("routes to unsupportedBuild when the build itself is unsupported", () => {
    const decision = resolveInitialRoute(baseInput({ buildSupported: false }));
    expect(decision.routeId).toBe("unsupportedBuild");
  });

  it("routes to maintenance when maintenance is blocking, even with a pending deep link", () => {
    const decision = resolveInitialRoute(
      baseInput({
        config: config({ maintenance: { enabled: true, type: "active-blocking", retryAllowed: true, permittedRouteIds: [] } }),
        pendingDeepLink: {
          routeId: "home",
          params: {},
          source: "custom-scheme",
          receivedAt: "x",
          expiresAt: "y",
          requiresAuth: false,
          requiresMarketplace: false,
          consumed: false,
        },
      })
    );
    expect(decision.routeId).toBe("maintenance");
  });

  it("routes to mandatoryUpdate when the version policy demands it, overriding maintenance-free state and deep links", () => {
    const decision = resolveInitialRoute(
      baseInput({
        config: config({
          versionPolicy: {
            minSupportedVersion: "2.0.0",
            latestRecommendedVersion: "2.0.0",
            mandatoryUpdate: false,
            optionalUpdate: false,
            updateTitle: "x",
            updateMessage: "y",
            gracePeriodHours: 0,
            blockedBuildNumbers: [],
          },
        }),
        pendingDeepLink: {
          routeId: "home",
          params: {},
          source: "custom-scheme",
          receivedAt: "x",
          expiresAt: "y",
          requiresAuth: false,
          requiresMarketplace: false,
          consumed: false,
        },
      })
    );
    expect(decision.routeId).toBe("mandatoryUpdate");
  });

  it("routes to appUnavailable when the marketplace is inactive", () => {
    const decision = resolveInitialRoute(
      baseInput({
        config: config({
          marketplace: {
            marketplaceId: "default",
            displayName: "x",
            active: false,
            defaultLocale: "en",
            supportedLocales: ["en"],
            defaultCurrency: "INR",
            timezone: "Asia/Kolkata",
            country: "IN",
            customerAppEnabled: true,
          },
        }),
      })
    );
    expect(decision.routeId).toBe("appUnavailable");
  });

  it("routes to offlineStartup when offline with no cache", () => {
    const decision = resolveInitialRoute(baseInput({ connectivity: "offline", configSource: "none", startupFailed: true }));
    expect(decision.routeId).toBe("offlineStartup");
  });

  it("routes to startupError on failure with a usable config source", () => {
    const decision = resolveInitialRoute(baseInput({ startupFailed: true, connectivity: "online" }));
    expect(decision.routeId).toBe("startupError");
  });

  it("defers to authentication when a deep link requires auth and the customer is a guest", () => {
    const decision = resolveInitialRoute(
      baseInput({
        pendingDeepLink: {
          routeId: "bookingDetail",
          params: {},
          source: "custom-scheme",
          receivedAt: "x",
          expiresAt: "y",
          requiresAuth: true,
          requiresMarketplace: false,
          consumed: false,
        },
      })
    );
    expect(decision.routeId).toBe("authentication");
  });

  it("consumes a valid pending deep link once no system gate applies", () => {
    const decision = resolveInitialRoute(
      baseInput({
        pendingDeepLink: {
          routeId: "home",
          params: { serviceId: "abc" },
          source: "custom-scheme",
          receivedAt: "x",
          expiresAt: "y",
          requiresAuth: false,
          requiresMarketplace: false,
          consumed: false,
        },
      })
    );
    expect(decision.routeId).toBe("home");
    expect(decision.shouldConsumeDeepLink).toBe(true);
    expect(decision.reason).toBe("deep-link");
  });

  it("falls back to the configured default landing route (baselineLanding) for a guest", () => {
    const decision = resolveInitialRoute(baseInput());
    expect(decision.routeId).toBe("baselineLanding");
    expect(decision.reason).toBe("default-landing");
  });

  it("falls back to the Home route for an authenticated customer with no pending destination", () => {
    const decision = resolveInitialRoute(baseInput({ auth: "authenticated" }));
    expect(decision.routeId).toBe("home");
    expect(decision.reason).toBe("default-landing");
  });

  it("an explicit remote-config initialRouteOverride wins over the auth-based default", () => {
    const decision = resolveInitialRoute(
      baseInput({
        auth: "authenticated",
        config: config({
          navigation: {
            allowedRouteIds: [],
            disabledRouteIds: [],
            deepLinkAllowlist: [],
            notificationRouteAllowlist: [],
            fallbackRouteId: "baselineLanding",
            initialRouteOverride: "support",
          },
        }),
      })
    );
    expect(decision.routeId).toBe("support");
  });

  it("marks degradedMode true when using a stale-permitted or compiled-default config source", () => {
    expect(resolveInitialRoute(baseInput({ configSource: "cache-stale-permitted" })).degradedMode).toBe(true);
    expect(resolveInitialRoute(baseInput({ configSource: "compiled-defaults" })).degradedMode).toBe(true);
    expect(resolveInitialRoute(baseInput({ configSource: "remote-fresh" })).degradedMode).toBe(false);
  });
});
