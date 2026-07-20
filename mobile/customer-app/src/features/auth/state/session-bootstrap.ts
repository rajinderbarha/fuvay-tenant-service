import { authApi } from "../api/auth-api";
import { toCustomerSession } from "../domain/session";
import { hydrateSessionTokens, persistSession, getSessionState, bindSessionToApiClient } from "./session-store";
import { bindRefreshCoordinator } from "./auth-refresh-coordinator";
import { ApiError } from "../../../api/api-errors";
import { logger } from "../../../observability/logger";

let bound = false;

/**
 * Called once by the startup orchestrator's `loading-secure-session-placeholder`
 * phase. Reads persisted tokens, validates them against `/v1/auth/me`, and
 * falls back to "guest" on any failure — never throws, since an auth
 * problem must not fail the whole startup run (CUSTOMER-L5-01 §28: startup
 * accepts authentication state as a dependency, it does not depend on auth
 * succeeding).
 *
 * Refresh-on-expiry is no longer handled inline here — `authApi.me()` goes
 * through `api-client.ts`, which now transparently refreshes once via
 * `auth-refresh-coordinator.ts` on a 401 (CUSTOMER-L5-02 §21). If that
 * refresh also fails, the coordinator has already cleared the session by
 * the time this catch block runs.
 */
export async function bootstrapSession(): Promise<"authenticated" | "guest"> {
  if (!bound) {
    bindSessionToApiClient();
    bindRefreshCoordinator();
    bound = true;
  }

  const tokens = await hydrateSessionTokens();
  if (!tokens) return "guest";

  try {
    const profile = await authApi.me();
    await persistSession(toCustomerSession(tokens, profile));
    return "authenticated";
  } catch (err) {
    // Network/timeout/server error (not "unauthorized" — that path is
    // already handled by the refresh coordinator above): don't destroy a
    // possibly-still-valid session over a transient failure. Report
    // "guest" for this run only, so the customer isn't stuck if the
    // backend is briefly unreachable at cold start.
    logger.warn("auth.session_bootstrap_failed", { category: err instanceof ApiError ? err.category : "unknown_error" });
    return getSessionState().status === "authenticated" ? "authenticated" : "guest";
  }
}
