import { remoteConfigEnvelopeSchema, SUPPORTED_SCHEMA_VERSION, type RemoteConfigEnvelope } from "../remote-config-schema";

function validEnvelope(overrides: Partial<RemoteConfigEnvelope> = {}): unknown {
  return {
    schemaVersion: SUPPORTED_SCHEMA_VERSION,
    configVersion: "2026-06-01.1",
    generatedAt: "2026-06-01T00:00:00.000Z",
    expiresAt: "2026-06-02T00:00:00.000Z",
    environment: "development",
    marketplace: {
      marketplaceId: "default",
      displayName: "ServiceOS",
      active: true,
      defaultLocale: "en",
      supportedLocales: ["en", "hi"],
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
      updateTitle: "Update",
      updateMessage: "Please update",
    },
    maintenance: { enabled: false, type: "none" },
    modules: [{ key: "home-services", displayNameKey: "modules.homeServices", enabled: true, visible: true, routeId: "home", order: 0 }],
    navigation: { allowedRouteIds: ["home", "baselineLanding"], fallbackRouteId: "baselineLanding" },
    ...overrides,
  };
}

describe("remoteConfigEnvelopeSchema", () => {
  it("accepts a valid envelope", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(validEnvelope());
    expect(result.success).toBe(true);
  });

  it("rejects an unsupported schema version", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(validEnvelope({ schemaVersion: 99 as never }));
    expect(result.success).toBe(false);
  });

  it("rejects a duplicate module key", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(
      validEnvelope({
        modules: [
          { key: "a", displayNameKey: "x", enabled: true, visible: true, order: 0 },
          { key: "a", displayNameKey: "y", enabled: true, visible: true, order: 1 },
        ] as never,
      })
    );
    expect(result.success).toBe(false);
  });

  it("rejects a module that depends on an unknown module", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(
      validEnvelope({ modules: [{ key: "a", displayNameKey: "x", enabled: true, visible: true, order: 0, dependsOn: ["missing"] }] as never })
    );
    expect(result.success).toBe(false);
  });

  it("rejects a cyclic module dependency graph", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(
      validEnvelope({
        modules: [
          { key: "a", displayNameKey: "x", enabled: true, visible: true, order: 0, dependsOn: ["b"] },
          { key: "b", displayNameKey: "y", enabled: true, visible: true, order: 1, dependsOn: ["a"] },
        ] as never,
      })
    );
    expect(result.success).toBe(false);
  });

  it("rejects a non-https store URL", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(
      validEnvelope({
        versionPolicy: {
          minSupportedVersion: "1.0.0",
          latestRecommendedVersion: "1.0.0",
          mandatoryUpdate: false,
          optionalUpdate: false,
          updateTitle: "x",
          updateMessage: "y",
          storeUrlAndroid: "http://insecure.example.com",
        } as never,
      })
    );
    expect(result.success).toBe(false);
  });

  it("rejects expiresAt before generatedAt", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(validEnvelope({ generatedAt: "2026-06-02T00:00:00.000Z", expiresAt: "2026-06-01T00:00:00.000Z" }));
    expect(result.success).toBe(false);
  });

  it("rejects maintenance enabled with type 'none'", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(validEnvelope({ maintenance: { enabled: true, type: "none" } as never }));
    expect(result.success).toBe(false);
  });

  it("rejects maintenance with estimatedEndAt before startAt", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(
      validEnvelope({
        maintenance: { enabled: true, type: "active-blocking", startAt: "2026-06-02T00:00:00.000Z", estimatedEndAt: "2026-06-01T00:00:00.000Z" } as never,
      })
    );
    expect(result.success).toBe(false);
  });

  it("rejects a fallbackRouteId not present in a non-empty allowedRouteIds", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(validEnvelope({ navigation: { allowedRouteIds: ["home"], fallbackRouteId: "profile" } as never }));
    expect(result.success).toBe(false);
  });

  it("rejects an unknown maintenance type enum value", () => {
    const result = remoteConfigEnvelopeSchema.safeParse(validEnvelope({ maintenance: { enabled: false, type: "half-broken" } as never }));
    expect(result.success).toBe(false);
  });
});
