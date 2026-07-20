import type { AppEnvironmentName } from "../config/environment";
import type { RemoteConfigEnvelope } from "./remote-config-schema";

/**
 * The remote-config envelope only recognizes development/staging/production
 * (the backend has no concept of a client's "local" or "test" build). Local
 * and test client builds are treated as "development" for cache/integrity
 * binding purposes so they are not permanently unable to use cached config.
 */
export function bindableEnvironmentName(name: AppEnvironmentName): RemoteConfigEnvelope["environment"] {
  if (name === "production") return "production";
  if (name === "staging") return "staging";
  return "development";
}

export type ConfigSource = "compiled-defaults" | "cache-fresh" | "cache-stale-permitted" | "remote-fresh" | "remote-not-modified";

export interface ResolvedRemoteConfig {
  config: RemoteConfigEnvelope;
  source: ConfigSource;
  fetchedAt: string;
  etag?: string;
}

export interface ConfigCacheEntry {
  payload: RemoteConfigEnvelope;
  schemaVersion: number;
  configVersion: string;
  fetchedAt: string;
  expiresAt?: string;
  etag?: string;
  environment: RemoteConfigEnvelope["environment"];
  marketplaceId: string;
  validationStatus: "valid" | "invalid";
  integrityStatus: "trusted" | "unverified";
  appVersionFetched: string;
}

export type RemoteConfigErrorCategory =
  | "network_error"
  | "timeout"
  | "cancelled"
  | "invalid_schema"
  | "unsupported_schema_version"
  | "environment_mismatch"
  | "marketplace_mismatch"
  | "integrity_failure"
  | "content_type_invalid"
  | "response_too_large"
  | "server_error"
  | "unknown_error";

export class RemoteConfigError extends Error {
  readonly category: RemoteConfigErrorCategory;
  readonly retryable: boolean;

  constructor(category: RemoteConfigErrorCategory, message: string, retryable = false) {
    super(message);
    this.name = "RemoteConfigError";
    this.category = category;
    this.retryable = retryable;
  }
}

export interface RemoteConfigFetchResult {
  status: "fresh" | "not-modified";
  envelope?: RemoteConfigEnvelope;
  etag?: string;
}
