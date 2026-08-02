import { ENV } from "../../config/environment";
import { buildPublicHeaders } from "./requestHeaders";

/**
 * The real platform health endpoint (app/engines/health_router.py) returns
 * a plain HealthResponse, NOT the standard ApiResponse envelope (no
 * `success`/`data` wrapper) -- confirmed by reading the router directly.
 * This is intentionally a separate, minimal client rather than routed
 * through publicClient/responseParser, which assume the standard envelope.
 */
export type PublicHealthStatus = "online" | "limited" | "unavailable";

export async function checkPublicHealth(signal?: AbortSignal): Promise<PublicHealthStatus> {
  try {
    const response = await fetch(new URL("/v1/health", ENV.apiBaseUrl).toString(), {
      method: "GET",
      headers: buildPublicHeaders(),
      signal,
    });
    if (!response.ok) return "unavailable";
    const body = await response.json().catch(() => null);
    const status = body?.status;
    if (status === "ok") return "online";
    if (status === "degraded") return "limited";
    return "unavailable";
  } catch {
    // Never exposes the underlying network/parse error to the UI --
    // any failure here is presentationally identical to "unavailable".
    return "unavailable";
  }
}
