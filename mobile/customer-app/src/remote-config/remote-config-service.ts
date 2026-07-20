import { environment } from "../config/environment";
import { logger } from "../observability/logger";
import { buildCompiledDefaults } from "./remote-config-defaults";
import { fetchRemoteConfig } from "./remote-config-client";
import { readConfigCache, writeConfigCache, evaluateCacheUsability } from "./remote-config-cache";
import { verifyConfigIntegrity } from "./config-integrity";
import { RemoteConfigError, bindableEnvironmentName, type ResolvedRemoteConfig, type ConfigSource } from "./remote-config-types";

export interface RemoteConfigRefreshOptions {
  marketplaceId?: string;
  force?: boolean;
  timeoutMs?: number;
  signal?: AbortSignal;
}

export interface RemoteConfigServiceState {
  current: ResolvedRemoteConfig;
  lastSuccessfulRefreshAt?: string;
  refreshError?: RemoteConfigError;
  refreshing: boolean;
}

const DEFAULT_MARKETPLACE_ID = "default";

let state: RemoteConfigServiceState = {
  current: { config: buildCompiledDefaults(), source: "compiled-defaults", fetchedAt: new Date().toISOString() },
  refreshing: false,
};

let inFlightRefresh: Promise<ResolvedRemoteConfig> | null = null;
const listeners = new Set<(state: RemoteConfigServiceState) => void>();

function setState(next: Partial<RemoteConfigServiceState>) {
  state = { ...state, ...next };
  listeners.forEach((listener) => listener(state));
}

export function getRemoteConfigState(): RemoteConfigServiceState {
  return state;
}

export function subscribeRemoteConfig(listener: (state: RemoteConfigServiceState) => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Resolves the config from cache without touching the network — used for fast, non-blocking startup. */
export async function loadCachedConfig(marketplaceId: string = DEFAULT_MARKETPLACE_ID): Promise<ResolvedRemoteConfig | null> {
  const cached = await readConfigCache();
  if (!cached) return null;

  const usability = evaluateCacheUsability(cached, {
    nowIso: new Date().toISOString(),
    environment: bindableEnvironmentName(environment.name),
    marketplaceId,
    maxAgeSeconds: cached.payload.application.maxConfigAgeSeconds,
    allowStale: cached.payload.application.cachedConfigFallbackAllowed,
  });

  if (!usability.usable) return null;

  const source: ConfigSource = usability.fresh ? "cache-fresh" : "cache-stale-permitted";
  return { config: cached.payload, source, fetchedAt: cached.fetchedAt, etag: cached.etag };
}

/**
 * Fetches fresh config, validates integrity, and updates the cache. Never
 * runs two fetches concurrently — a second caller awaits the same in-flight
 * promise instead of issuing a duplicate request (prevents refresh storms).
 */
export async function refreshRemoteConfig(options: RemoteConfigRefreshOptions = {}): Promise<ResolvedRemoteConfig> {
  if (inFlightRefresh && !options.force) return inFlightRefresh;

  const marketplaceId = options.marketplaceId ?? DEFAULT_MARKETPLACE_ID;
  setState({ refreshing: true });

  inFlightRefresh = (async () => {
    try {
      const cached = await readConfigCache();
      const fetchResult = await fetchRemoteConfig({ etag: cached?.etag, timeoutMs: options.timeoutMs, marketplaceId, signal: options.signal });

      if (fetchResult.status === "not-modified" && cached) {
        const resolved: ResolvedRemoteConfig = {
          config: cached.payload,
          source: "remote-not-modified",
          fetchedAt: new Date().toISOString(),
          etag: cached.etag,
        };
        setState({ current: resolved, lastSuccessfulRefreshAt: resolved.fetchedAt, refreshError: undefined, refreshing: false });
        logger.info("remote_config.not_modified", { configVersion: cached.configVersion });
        return resolved;
      }

      if (!fetchResult.envelope) {
        throw new RemoteConfigError("unknown_error", "Fetch reported fresh status with no envelope.");
      }

      const integrity = verifyConfigIntegrity({ envelope: fetchResult.envelope, sourceUrl: environment.apiBaseUrl, marketplaceContextId: marketplaceId });
      if (integrity.status === "rejected") {
        throw new RemoteConfigError("integrity_failure", `Config rejected: ${integrity.reason}.`);
      }

      const fetchedAt = new Date().toISOString();
      await writeConfigCache({
        payload: fetchResult.envelope,
        schemaVersion: fetchResult.envelope.schemaVersion,
        configVersion: fetchResult.envelope.configVersion,
        fetchedAt,
        expiresAt: fetchResult.envelope.expiresAt,
        etag: fetchResult.etag,
        environment: fetchResult.envelope.environment,
        marketplaceId: fetchResult.envelope.marketplace.marketplaceId,
        validationStatus: "valid",
        integrityStatus: integrity.status === "unverified" ? "unverified" : "trusted",
        appVersionFetched: environment.buildVersion,
      });

      const resolved: ResolvedRemoteConfig = { config: fetchResult.envelope, source: "remote-fresh", fetchedAt, etag: fetchResult.etag };
      setState({ current: resolved, lastSuccessfulRefreshAt: fetchedAt, refreshError: undefined, refreshing: false });
      logger.info("remote_config.fetch_succeeded", { configVersion: fetchResult.envelope.configVersion });
      return resolved;
    } catch (err) {
      const normalized = err instanceof RemoteConfigError ? err : new RemoteConfigError("unknown_error", "Unexpected remote config refresh failure.");
      setState({ refreshError: normalized, refreshing: false });
      logger.warn("remote_config.fetch_failed", { category: normalized.category });
      throw normalized;
    } finally {
      inFlightRefresh = null;
    }
  })();

  return inFlightRefresh;
}

/** Test-only reset — production code never needs to reset module-level state. */
export function __resetRemoteConfigStateForTests(): void {
  state = { current: { config: buildCompiledDefaults(), source: "compiled-defaults", fetchedAt: new Date().toISOString() }, refreshing: false };
  inFlightRefresh = null;
  listeners.clear();
}
