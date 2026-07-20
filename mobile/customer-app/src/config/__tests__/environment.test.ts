describe("environment", () => {
  const originalEnv = { ...process.env };

  afterEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
  });

  it("defaults to a safe localhost URL in local/dev without throwing", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "local";
    delete process.env.EXPO_PUBLIC_API_URL;
    const { environment } = require("../environment");
    expect(environment.apiBaseUrl).toContain("localhost");
    expect(environment.name).toBe("local");
  });

  it("throws when a production build points at localhost", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "production";
    process.env.EXPO_PUBLIC_API_URL = "http://localhost:8000";
    expect(() => require("../environment")).toThrow(/localhost/i);
  });

  it("throws when a production build has no API URL configured", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "production";
    delete process.env.EXPO_PUBLIC_API_URL;
    expect(() => require("../environment")).toThrow(/EXPO_PUBLIC_API_URL/);
  });

  it("throws when mock mode is enabled in a production build", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "production";
    process.env.EXPO_PUBLIC_API_URL = "https://api.serviceos.in";
    process.env.EXPO_PUBLIC_MOCK_MODE = "true";
    expect(() => require("../environment")).toThrow(/mock_mode/i);
  });

  it("accepts a valid production configuration", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "production";
    process.env.EXPO_PUBLIC_API_URL = "https://api.serviceos.in";
    process.env.EXPO_PUBLIC_MOCK_MODE = "false";
    const { environment } = require("../environment");
    expect(environment.apiBaseUrl).toBe("https://api.serviceos.in");
    expect(environment.mockModeEnabled).toBe(false);
  });

  it("disables analytics/crash reporting for the local environment even if flags are set", () => {
    process.env.EXPO_PUBLIC_APP_ENV = "local";
    process.env.EXPO_PUBLIC_ANALYTICS_ENABLED = "true";
    process.env.EXPO_PUBLIC_CRASH_REPORTING_ENABLED = "true";
    const { environment } = require("../environment");
    expect(environment.analyticsEnabled).toBe(false);
    expect(environment.crashReportingEnabled).toBe(false);
  });
});
