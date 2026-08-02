import { buildEnvironment } from "../environment";

describe("buildEnvironment", () => {
  it("defaults to local with a local base URL when nothing is set", () => {
    const env = buildEnvironment({});
    expect(env.appEnv).toBe("local");
    expect(env.apiBaseUrl).toBe("http://localhost:8000");
  });

  it("normalizes a trailing slash", () => {
    const env = buildEnvironment({ EXPO_PUBLIC_ENV: "local", EXPO_PUBLIC_API_BASE_URL: "http://localhost:9000/" });
    expect(env.apiBaseUrl).toBe("http://localhost:9000");
  });

  it("throws when staging has no base URL configured (no fabricated production domain)", () => {
    expect(() => buildEnvironment({ EXPO_PUBLIC_ENV: "staging" })).toThrow(/EXPO_PUBLIC_API_BASE_URL is required/);
  });

  it("throws when production has no base URL configured", () => {
    expect(() => buildEnvironment({ EXPO_PUBLIC_ENV: "production" })).toThrow(/EXPO_PUBLIC_API_BASE_URL is required/);
  });

  it("requires HTTPS outside local dev", () => {
    expect(() => buildEnvironment({ EXPO_PUBLIC_ENV: "staging", EXPO_PUBLIC_API_BASE_URL: "http://staging.example.com" })).toThrow(/HTTPS/);
  });

  it("accepts HTTPS in staging", () => {
    const env = buildEnvironment({ EXPO_PUBLIC_ENV: "staging", EXPO_PUBLIC_API_BASE_URL: "https://staging.example.com" });
    expect(env.apiBaseUrl).toBe("https://staging.example.com");
  });

  it("rejects an invalid URL", () => {
    expect(() => buildEnvironment({ EXPO_PUBLIC_ENV: "local", EXPO_PUBLIC_API_BASE_URL: "not a url" })).toThrow(/not a valid URL/);
  });

  it("allows plain HTTP against localhost even when appEnv is local with an explicit base URL", () => {
    const env = buildEnvironment({ EXPO_PUBLIC_ENV: "local", EXPO_PUBLIC_API_BASE_URL: "http://10.0.2.2:8000" });
    expect(env.apiBaseUrl).toBe("http://10.0.2.2:8000");
  });

  it("applies a custom API timeout when provided", () => {
    const env = buildEnvironment({ EXPO_PUBLIC_ENV: "local", EXPO_PUBLIC_API_TIMEOUT_MS: "5000" });
    expect(env.apiTimeoutMs).toBe(5000);
  });
});
