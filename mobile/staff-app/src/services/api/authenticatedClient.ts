import { performRequest } from "./apiClient";
import { buildAuthenticatedHeaders, withConcurrencyFields } from "./requestHeaders";
import { ApiRequestOptions, ApiResult } from "./types";
import { getAccessToken, getSessionGeneration } from "../auth/tokenCoordinator";
import { emitSessionEvent } from "../auth/sessionEvents";

/**
 * Authenticated request path (Phase F spec section 4). This file must NOT
 * import refreshCoordinator/authApi directly -- that would create
 * api<->auth circular imports (authApi needs this client for /me,
 * /access-context, /logout, /sessions). Instead the refresh trigger is
 * registered at runtime by refreshCoordinator via `registerRefreshHandler`
 * (a small DI seam, same pattern Phase E uses to keep navigation/session/api
 * acyclic). Feature code never constructs an Authorization header itself --
 * this is the only place that happens for authenticated calls.
 */
export type RefreshOutcome = { ok: true; accessToken: string } | { ok: false };
type RefreshHandler = () => Promise<RefreshOutcome>;

let refreshHandler: RefreshHandler | null = null;
export function registerRefreshHandler(fn: RefreshHandler): void {
  refreshHandler = fn;
}

/** Test-only reset. */
export function __resetRefreshHandlerForTests(): void {
  refreshHandler = null;
}

export async function authenticatedRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<ApiResult<T>> {
  const startGeneration = getSessionGeneration();
  const accessToken = getAccessToken();

  if (!accessToken) {
    return { ok: false, error: { code: "AUTH_REQUIRED", category: "auth", safeMessage: "Please sign in to continue.", retryable: false } };
  }

  const body = options.body && typeof options.body === "object"
    ? withConcurrencyFields(options.body as Record<string, unknown>, options.concurrency)
    : options.body;

  const headers = buildAuthenticatedHeaders(accessToken, options.idempotencyKey);
  const first = await performRequest<T>({ path, headers, options: { ...options, body }, context: "authenticated" });

  if (first.ok) return first;

  // 403 (permission/capability/tenant/technician-state) never triggers a
  // refresh -- only a genuinely expired access token does.
  if (first.error.code !== "ACCESS_TOKEN_EXPIRED") {
    if (first.error.category === "auth") {
      emitSessionEvent({ type: "SESSION_EXPIRED", reasonCode: first.error.code });
    }
    return first;
  }

  if (!refreshHandler) return first;
  const refreshed = await refreshHandler();
  if (!refreshed.ok) return first;

  // A logout/account-switch that happened while the refresh was in flight
  // bumps the session generation -- this response belongs to a session
  // generation that no longer exists, so it must never be replayed into
  // whatever is now the active session.
  if (getSessionGeneration() !== startGeneration) {
    return { ok: false, error: { code: "REQUEST_CANCELLED", category: "cancelled", safeMessage: "Request cancelled.", retryable: false } };
  }

  // Replay the ORIGINAL request exactly once with the rotated token.
  const retryHeaders = buildAuthenticatedHeaders(refreshed.accessToken, options.idempotencyKey);
  return performRequest<T>({ path, headers: retryHeaders, options: { ...options, body }, context: "authenticated" });
}
