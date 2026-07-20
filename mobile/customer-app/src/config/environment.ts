/**
 * The only place in the app allowed to read `process.env` directly.
 * Screens and features must import `environment` from here, never touch
 * `process.env` themselves (enforced by convention + code review; see
 * docs/customer-app/environment-configuration.md).
 */

export type AppEnvironmentName = "local" | "development" | "test" | "staging" | "production";

export interface Environment {
  name: AppEnvironmentName;
  apiBaseUrl: string;
  apiTimeoutMs: number;
  buildVersion: string;
  buildNumber: string;
  analyticsEnabled: boolean;
  crashReportingEnabled: boolean;
  logLevel: "debug" | "info" | "warn" | "error";
  mockModeEnabled: boolean;
  deepLinkScheme: string;
}

function readEnvName(): AppEnvironmentName {
  const raw = (process.env.EXPO_PUBLIC_APP_ENV ?? "").toLowerCase();
  if (raw === "local" || raw === "development" || raw === "test" || raw === "staging" || raw === "production") {
    return raw;
  }
  return __DEV__ ? "development" : "production";
}

function isLocalhost(url: string): boolean {
  return /^https?:\/\/(localhost|127\.0\.0\.1|0\.0\.0\.0)/i.test(url);
}

class EnvironmentValidationError extends Error {
  constructor(issues: string[]) {
    super(`Invalid environment configuration:\n- ${issues.join("\n- ")}`);
    this.name = "EnvironmentValidationError";
  }
}

function buildEnvironment(): Environment {
  const name = readEnvName();
  const apiBaseUrl = process.env.EXPO_PUBLIC_API_URL ?? "";
  const issues: string[] = [];

  if (!apiBaseUrl) {
    issues.push("EXPO_PUBLIC_API_URL is not set.");
  }

  if (name === "production" && apiBaseUrl && isLocalhost(apiBaseUrl)) {
    issues.push("EXPO_PUBLIC_API_URL points at localhost in a production build.");
  }

  const mockModeEnabled = process.env.EXPO_PUBLIC_MOCK_MODE === "true";
  if (name === "production" && mockModeEnabled) {
    issues.push("EXPO_PUBLIC_MOCK_MODE must not be enabled in a production build.");
  }

  // Fail loudly on production/staging misconfiguration rather than silently
  // shipping a broken build; fall back safely (localhost) only in local/dev/test
  // so `expo start` still boots for a fresh clone without a .env file.
  if (issues.length > 0) {
    if (name === "production" || name === "staging") {
      throw new EnvironmentValidationError(issues);
    }
  }

  return {
    name,
    apiBaseUrl: apiBaseUrl || "http://localhost:8000",
    apiTimeoutMs: Number(process.env.EXPO_PUBLIC_API_TIMEOUT_MS ?? 15000),
    buildVersion: process.env.EXPO_PUBLIC_BUILD_VERSION ?? "0.0.0-dev",
    buildNumber: process.env.EXPO_PUBLIC_BUILD_NUMBER ?? "0",
    analyticsEnabled: process.env.EXPO_PUBLIC_ANALYTICS_ENABLED === "true" && name !== "local",
    crashReportingEnabled: process.env.EXPO_PUBLIC_CRASH_REPORTING_ENABLED === "true" && name !== "local",
    logLevel: (process.env.EXPO_PUBLIC_LOG_LEVEL as Environment["logLevel"]) ?? (name === "production" ? "warn" : "debug"),
    mockModeEnabled: mockModeEnabled && name !== "production",
    deepLinkScheme: process.env.EXPO_PUBLIC_DEEP_LINK_SCHEME ?? "serviceos",
  };
}

export const environment: Environment = buildEnvironment();
