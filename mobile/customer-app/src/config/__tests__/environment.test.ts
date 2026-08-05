import { buildEnvironment } from "../environment";

describe("buildEnvironment", () => {
  it("defaults to localhost in local dev when no base URL is set", () => {
    const env = buildEnvironment({ EXPO_PUBLIC_ENV: "local" });
    expect(env.appEnv).toBe("local");
    expect(env.apiBaseUrl).toBe("http://localhost:8000");
  });

  it("fails safely (throws) when the base URL is missing outside local", () => {
    expect(() => buildEnvironment({ EXPO_PUBLIC_ENV: "staging" })).toThrow(
      /EXPO_PUBLIC_API_BASE_URL is required/,
    );
  });

  it("fails safely (throws) when a non-local base URL is not HTTPS", () => {
    expect(() =>
      buildEnvironment({ EXPO_PUBLIC_ENV: "production", EXPO_PUBLIC_API_BASE_URL: "http://api.example.com" }),
    ).toThrow(/must use HTTPS/);
  });

  it("accepts a valid HTTPS base URL outside local", () => {
    const env = buildEnvironment({ EXPO_PUBLIC_ENV: "production", EXPO_PUBLIC_API_BASE_URL: "https://api.example.com/" });
    expect(env.apiBaseUrl).toBe("https://api.example.com");
  });

  it("accepts a non-HTTPS LAN IP in local dev (physical device on the same Wi-Fi)", () => {
    const env = buildEnvironment({ EXPO_PUBLIC_ENV: "local", EXPO_PUBLIC_API_BASE_URL: "http://192.168.18.13:8000" });
    expect(env.apiBaseUrl).toBe("http://192.168.18.13:8000");
  });

  it("rejects a malformed base URL", () => {
    expect(() =>
      buildEnvironment({ EXPO_PUBLIC_ENV: "production", EXPO_PUBLIC_API_BASE_URL: "not-a-url" }),
    ).toThrow(/not a valid URL/);
  });
});
