/**
 * Validated, immutable environment configuration. This is the ONLY place
 * `process.env.EXPO_PUBLIC_*` is read -- feature code imports `ENV` from
 * here, never `process.env` directly. Expo only exposes variables prefixed
 * `EXPO_PUBLIC_` to client bundles; a secret without that prefix is never
 * available here by design, and a value WITH that prefix must never be
 * treated as secret (it ships in the client bundle).
 *
 * Public (bundled into the client, safe to be public):
 *   EXPO_PUBLIC_ENV              - local | test | staging | production
 *   EXPO_PUBLIC_API_BASE_URL     - required outside "local"
 *   EXPO_PUBLIC_API_TIMEOUT_MS   - optional, defaults below
 *
 * There is no DeepSeek key here and never will be -- the backend owns all
 * DeepSeek communication; this app only ever calls the ServiceOS API.
 */
export type AppEnvironment = "local" | "test" | "staging" | "production";

export interface Environment {
  readonly appEnv: AppEnvironment;
  readonly apiBaseUrl: string;
  readonly apiTimeoutMs: number;
}

const DEFAULT_LOCAL_BASE_URL = "http://localhost:8000";
const DEFAULT_API_TIMEOUT_MS = 15_000;

function normalizeBaseUrl(raw: string): string {
  return raw.trim().replace(/\/+$/, "");
}

function parseAppEnv(raw: string | undefined): AppEnvironment {
  if (raw === "local" || raw === "test" || raw === "staging" || raw === "production") return raw;
  return "local";
}

/**
 * Builds and validates the environment config. Throws with a clear message
 * rather than silently falling back to a wrong/insecure default -- a
 * missing/invalid base URL outside local dev must fail loudly at startup,
 * not surface later as a mysterious network error.
 */
export function buildEnvironment(env: Partial<NodeJS.ProcessEnv> = process.env): Environment {
  const appEnv = parseAppEnv(env.EXPO_PUBLIC_ENV);
  const rawBaseUrl = env.EXPO_PUBLIC_API_BASE_URL?.trim();

  let apiBaseUrl: string;
  if (appEnv === "local") {
    apiBaseUrl = normalizeBaseUrl(rawBaseUrl || DEFAULT_LOCAL_BASE_URL);
  } else {
    if (!rawBaseUrl) {
      throw new Error(
        `EXPO_PUBLIC_API_BASE_URL is required when EXPO_PUBLIC_ENV="${appEnv}". ` +
        "Refusing to fall back to a fabricated or local default outside local dev.",
      );
    }
    apiBaseUrl = normalizeBaseUrl(rawBaseUrl);
  }

  let parsed: URL;
  try {
    parsed = new URL(apiBaseUrl);
  } catch {
    throw new Error(`EXPO_PUBLIC_API_BASE_URL is not a valid URL: "${apiBaseUrl}"`);
  }

  // A physical device on the same Wi-Fi reaches the dev machine by its LAN
  // IP (e.g. 192.168.x.x), not "localhost" -- that's still local development
  // trust-wise (developer's own network), so the HTTPS requirement is
  // exempted for the whole "local" environment, not just loopback/emulator
  // aliases. Only "local" gets this exemption; staging/production still
  // require HTTPS unconditionally.
  if (parsed.protocol !== "https:" && appEnv !== "local") {
    throw new Error(
      `EXPO_PUBLIC_API_BASE_URL must use HTTPS outside local development (got "${parsed.protocol}" for appEnv="${appEnv}").`,
    );
  }

  const apiTimeoutMs = Number(env.EXPO_PUBLIC_API_TIMEOUT_MS) || DEFAULT_API_TIMEOUT_MS;

  return Object.freeze({ appEnv, apiBaseUrl, apiTimeoutMs });
}

export const ENV: Environment = buildEnvironment();
