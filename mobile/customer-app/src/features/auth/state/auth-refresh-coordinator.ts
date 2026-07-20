import { authApi } from "../api/auth-api";
import { toCustomerSession } from "../domain/session";
import { getSessionState, persistSession, clearSession } from "./session-store";
import { setUnauthorizedHandler } from "../../../api/request-context";
import { logger } from "../../../observability/logger";

/**
 * Single-flight refresh coordinator (CUSTOMER-L5-02 §21). Any number of
 * concurrent API calls that hit a 401 within the same instant all await the
 * same in-flight refresh promise rather than each firing their own
 * `/v1/auth/token/refresh` request — the second+ caller never even reaches
 * the network. A failed refresh clears the session exactly once.
 */
let inFlightRefresh: Promise<boolean> | null = null;

async function performRefresh(): Promise<boolean> {
  const current = getSessionState().session;
  if (!current) return false;

  try {
    const refreshed = await authApi.refreshToken(current.refreshToken);
    const profile = await authApi.me();
    await persistSession(toCustomerSession({ accessToken: refreshed.access_token, refreshToken: refreshed.refresh_token }, profile));
    logger.info("auth_session_refresh_succeeded");
    return true;
  } catch {
    logger.warn("auth_session_refresh_failed");
    await clearSession();
    return false;
  }
}

async function handleUnauthorizedOnce(): Promise<boolean> {
  if (!getSessionState().session) return false; // nothing to refresh — a genuinely unauthenticated request, not an expired session
  if (!inFlightRefresh) {
    inFlightRefresh = performRefresh().finally(() => {
      inFlightRefresh = null;
    });
  }
  return inFlightRefresh;
}

let bound = false;

export function bindRefreshCoordinator(): void {
  if (bound) return;
  bound = true;
  setUnauthorizedHandler(handleUnauthorizedOnce);
}

export function __resetRefreshCoordinatorForTests(): void {
  inFlightRefresh = null;
  bound = false;
  setUnauthorizedHandler(null);
}
