import { environment } from "../config/environment";
import { buildRequestHeaders } from "../api/request-context";
import { logger } from "../observability/logger";
import { remoteConfigEnvelopeSchema, SUPPORTED_SCHEMA_VERSION } from "./remote-config-schema";
import { RemoteConfigError, type RemoteConfigFetchResult } from "./remote-config-types";

const MAX_RESPONSE_BYTES = 256 * 1024; // remote config must stay small
const REMOTE_CONFIG_PATH = "/v1/customer-app/remote-config";

export interface FetchRemoteConfigOptions {
  etag?: string;
  timeoutMs?: number;
  marketplaceId?: string;
  signal?: AbortSignal;
}

/**
 * Dedicated fetch wrapper (not routed through api/api-client.ts) because
 * remote-config fetching needs direct access to response headers (ETag,
 * content-length, content-type) that the generic JSON-envelope client
 * intentionally does not expose.
 */
export async function fetchRemoteConfig(options: FetchRemoteConfigOptions = {}): Promise<RemoteConfigFetchResult> {
  const headers = await buildRequestHeaders({
    Accept: "application/json",
    ...(options.etag ? { "If-None-Match": options.etag } : {}),
    ...(options.marketplaceId ? { "X-Marketplace-Id": options.marketplaceId } : {}),
  });

  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? 8000;
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
  if (options.signal) options.signal.addEventListener("abort", () => controller.abort());

  try {
    const res = await fetch(`${environment.apiBaseUrl}${REMOTE_CONFIG_PATH}`, { method: "GET", headers, signal: controller.signal });

    if (res.status === 304) {
      return { status: "not-modified", etag: options.etag };
    }

    if (!res.ok) {
      const retryable = res.status >= 500 || res.status === 429;
      throw new RemoteConfigError("server_error", `Remote config request failed with status ${res.status}.`, retryable);
    }

    const contentType = res.headers.get("content-type") ?? "";
    if (!contentType.includes("application/json")) {
      throw new RemoteConfigError("content_type_invalid", `Unexpected content-type: ${contentType || "none"}.`);
    }

    const contentLength = Number(res.headers.get("content-length") ?? "0");
    if (contentLength > MAX_RESPONSE_BYTES) {
      throw new RemoteConfigError("response_too_large", `Response of ${contentLength} bytes exceeds the ${MAX_RESPONSE_BYTES}-byte limit.`);
    }

    const text = await res.text();
    if (text.length > MAX_RESPONSE_BYTES) {
      throw new RemoteConfigError("response_too_large", `Response of ${text.length} bytes exceeds the ${MAX_RESPONSE_BYTES}-byte limit.`);
    }

    let json: unknown;
    try {
      json = JSON.parse(text);
    } catch {
      throw new RemoteConfigError("invalid_schema", "Response was not valid JSON.");
    }

    if (
      typeof json === "object" &&
      json !== null &&
      "schemaVersion" in json &&
      (json as { schemaVersion: unknown }).schemaVersion !== SUPPORTED_SCHEMA_VERSION
    ) {
      throw new RemoteConfigError(
        "unsupported_schema_version",
        `Unsupported remote config schema version: ${(json as { schemaVersion: unknown }).schemaVersion}.`
      );
    }

    const parsed = remoteConfigEnvelopeSchema.safeParse(json);
    if (!parsed.success) {
      // Schema errors are never treated as transient/network — retrying
      // a malformed response cannot succeed.
      logger.warn("remote_config.invalid_schema", { issueCount: parsed.error.issues.length });
      throw new RemoteConfigError("invalid_schema", "Remote config failed schema validation.");
    }

    return { status: "fresh", envelope: parsed.data, etag: res.headers.get("etag") ?? undefined };
  } catch (err) {
    if (err instanceof RemoteConfigError) throw err;
    if (err instanceof Error && err.name === "AbortError") {
      throw new RemoteConfigError("timeout", "Remote config request timed out.", true);
    }
    if (err instanceof TypeError) {
      throw new RemoteConfigError("network_error", "Network request failed.", true);
    }
    throw new RemoteConfigError("unknown_error", "Unexpected error fetching remote config.");
  } finally {
    clearTimeout(timeoutHandle);
  }
}
