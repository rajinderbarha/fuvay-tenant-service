/**
 * Validated, immutable environment configuration (Phase F spec section 3).
 * This is the ONLY place `process.env.EXPO_PUBLIC_*` is read for networking
 * concerns -- feature code imports `ENV` from here, never `process.env`
 * directly. Expo only exposes variables prefixed `EXPO_PUBLIC_` to client
 * bundles (documented below); anything without that prefix stays server/
 * build-time only and is never available here by design -- do not add a
 * secret without that prefix and expect it to work, and never add one WITH
 * that prefix expecting it to stay secret.
 *
 * Public (bundled into the client, safe to be public):
 *   EXPO_PUBLIC_ENV                    - local | test | staging | production
 *   EXPO_PUBLIC_API_BASE_URL           - required outside "local"
 *   EXPO_PUBLIC_UNIVERSAL_LINK_HOST    - optional (Phase E deep linking)
 *   EXPO_PUBLIC_API_TIMEOUT_MS         - optional, defaults below
 */
export type AppEnvironment = "local" | "test" | "staging" | "production";

export interface Environment {
  readonly appEnv: AppEnvironment;
  readonly apiBaseUrl: string;
  readonly apiTimeoutMs: number;
  readonly bootstrapTimeoutMs: number;
}

const DEFAULT_LOCAL_BASE_URL = "http://localhost:8000";
const DEFAULT_API_TIMEOUT_MS = 15_000;
const DEFAULT_BOOTSTRAP_TIMEOUT_MS = 10_000;

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
    // No hardcoded localhost in production: this branch is unreachable
    // once appEnv is staging/production, and DEFAULT_LOCAL_BASE_URL is
    // only ever used for local dev when the developer hasn't set one.
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

  // Real bug found while testing on a physical device over LAN: this only
  // ever matched simulator-loopback hostnames, never the private LAN IP a
  // physical device actually uses to reach the dev machine -- even though
  // the .env file's own documented workflow ("Physical device: replace
  // with your computer's local IP address") assumes exactly that works.
  // RFC1918 private ranges only, still appEnv==="local"-gated below.
  const isPrivateLanIp = /^(10\.|127\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(parsed.hostname);
  const isLocalHost = parsed.hostname === "localhost" || parsed.hostname === "10.0.2.2" || isPrivateLanIp;
  if (parsed.protocol !== "https:" && !(appEnv === "local" && isLocalHost)) {
    throw new Error(
      `EXPO_PUBLIC_API_BASE_URL must use HTTPS outside local development (got "${parsed.protocol}" for appEnv="${appEnv}").`,
    );
  }

  const apiTimeoutMs = Number(env.EXPO_PUBLIC_API_TIMEOUT_MS) || DEFAULT_API_TIMEOUT_MS;

  return Object.freeze({
    appEnv,
    apiBaseUrl,
    apiTimeoutMs,
    bootstrapTimeoutMs: DEFAULT_BOOTSTRAP_TIMEOUT_MS,
  });
}

export const ENV: Environment = buildEnvironment();
