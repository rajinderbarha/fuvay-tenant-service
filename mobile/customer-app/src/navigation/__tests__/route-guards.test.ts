import { evaluateRouteAccess, type RouteGuardContext } from "../route-guards";
import type { RemoteConfigEnvelope } from "../../remote-config/remote-config-schema";

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

function context(overrides: Partial<RouteGuardContext> = {}): RouteGuardContext {
  return {
    startupReady: true,
    config: config(),
    maintenanceBlocking: false,
    versionMandatoryUpdate: false,
    marketplaceAvailable: true,
    auth: "guest",
    onboarding: "skipped-where-allowed",
    isProductionBuild: false,
    isDevBuild: true,
    appVersion: "1.0.0",
    ...overrides,
  };
}

describe("evaluateRouteAccess", () => {
  it("allows a public-system route", () => {
    expect(evaluateRouteAccess("baselineLanding", context()).decision).toBe("allow");
  });

  it("rejects an unknown route id", () => {
    expect(evaluateRouteAccess("not-a-real-route", context()).decision).toBe("deny-unknown-route");
  });

  it("denies everything when startup isn't ready, before any other check", () => {
    expect(evaluateRouteAccess("baselineLanding", context({ startupReady: false })).decision).toBe("deny-not-ready");
  });

  it("denies when maintenance is blocking, even for an otherwise-public route", () => {
    expect(evaluateRouteAccess("baselineLanding", context({ maintenanceBlocking: true })).decision).toBe("deny-maintenance");
  });

  it("denies when a mandatory version update is pending", () => {
    expect(evaluateRouteAccess("baselineLanding", context({ versionMandatoryUpdate: true })).decision).toBe("deny-version");
  });

  it("denies when the marketplace is unavailable", () => {
    expect(evaluateRouteAccess("baselineLanding", context({ marketplaceAvailable: false })).decision).toBe("deny-marketplace");
  });

  it("denies a development-only route in a non-dev build", () => {
    expect(evaluateRouteAccess("designSystemShowcase", context({ isDevBuild: false })).decision).toBe("deny-development-only");
  });

  it("allows a development-only route in a dev build", () => {
    expect(evaluateRouteAccess("designSystemShowcase", context({ isDevBuild: true })).decision).toBe("allow");
  });

  it("denies a production-disabled route in a production build", () => {
    expect(evaluateRouteAccess("notifications", context({ isProductionBuild: true })).decision).toBe("deny-production");
  });

  it("denies an authenticated route for a guest", () => {
    expect(evaluateRouteAccess("profile", context({ isProductionBuild: false, auth: "guest" })).decision).toBe("deny-auth");
  });

  it("allows an authenticated route for an authenticated customer", () => {
    expect(evaluateRouteAccess("profile", context({ isProductionBuild: false, auth: "authenticated" })).decision).toBe("allow");
  });

  it("denies a route reached via deep link when the route is not deep-link eligible", () => {
    expect(evaluateRouteAccess("profile", context({ isProductionBuild: false, auth: "authenticated", viaDeepLink: true })).decision).toBe("deny-unknown-route");
  });

  it("denies a route reached via notification when the route is not notification eligible", () => {
    expect(evaluateRouteAccess("home", context({ isProductionBuild: false, auth: "authenticated", viaNotification: true })).decision).toBe(
      "deny-unknown-route"
    );
  });
});
