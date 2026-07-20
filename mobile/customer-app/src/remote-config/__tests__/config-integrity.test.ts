describe("verifyConfigIntegrity", () => {
  const originalEnv = { ...process.env };

  afterEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
  });

  function envelope(overrides: Record<string, unknown> = {}) {
    return {
      environment: "production",
      marketplace: { marketplaceId: "default" },
      ...overrides,
    };
  }

  it("rejects a config whose declared environment doesn't match the build environment", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "production";
    process.env.EXPO_PUBLIC_API_URL = "https://api.serviceos.in";
    const { verifyConfigIntegrity } = require("../config-integrity");
    const result = verifyConfigIntegrity({
      envelope: envelope({ environment: "staging" }),
      sourceUrl: "https://api.serviceos.in/v1/x",
      marketplaceContextId: "default",
    });
    expect(result.status).toBe("rejected");
    expect(result.reason).toBe("environment_mismatch");
  });

  it("rejects a config for a different marketplace than requested", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "production";
    process.env.EXPO_PUBLIC_API_URL = "https://api.serviceos.in";
    const { verifyConfigIntegrity } = require("../config-integrity");
    const result = verifyConfigIntegrity({
      envelope: envelope({ marketplace: { marketplaceId: "other" } }),
      sourceUrl: "https://api.serviceos.in/v1/x",
      marketplaceContextId: "default",
    });
    expect(result.status).toBe("rejected");
    expect(result.reason).toBe("marketplace_mismatch");
  });

  it("rejects a production config served from an untrusted host", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "production";
    process.env.EXPO_PUBLIC_API_URL = "https://api.serviceos.in";
    const { verifyConfigIntegrity } = require("../config-integrity");
    const result = verifyConfigIntegrity({ envelope: envelope(), sourceUrl: "https://evil.example.com/v1/x", marketplaceContextId: "default" });
    expect(result.status).toBe("rejected");
    expect(result.reason).toBe("untrusted_origin");
  });

  it("marks a matching production config from the trusted host as unverified (no signature available)", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "production";
    process.env.EXPO_PUBLIC_API_URL = "https://api.serviceos.in";
    const { verifyConfigIntegrity } = require("../config-integrity");
    const result = verifyConfigIntegrity({ envelope: envelope(), sourceUrl: "https://api.serviceos.in/v1/x", marketplaceContextId: "default" });
    expect(result.status).toBe("unverified");
  });

  it("treats a local build's config environment as bindable to 'development'", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "local";
    process.env.EXPO_PUBLIC_API_URL = "http://localhost:8000";
    const { verifyConfigIntegrity } = require("../config-integrity");
    const result = verifyConfigIntegrity({
      envelope: envelope({ environment: "development" }),
      sourceUrl: "http://localhost:8000/v1/x",
      marketplaceContextId: "default",
    });
    expect(result.status).toBe("unverified");
  });
});
