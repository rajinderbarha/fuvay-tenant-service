import { refreshSession as refreshSessionApi } from "../auth/authApi";
import { rotateTokens, loadSession, clearSession } from "./tokenVault";
import { CustomerId } from "../../domain/ids";
import { DomainError } from "../../domain/errors";

/**
 * Single refresh coordinator for the whole app (spec section 17). Every
 * caller that hits an expired access token calls `getRefreshedAccessToken()`
 * -- if a refresh is already in flight, callers await the SAME promise
 * (`inFlightRefresh`) instead of firing a second network call. A session
 * `epoch` guards against a late-arriving refresh response resurrecting a
 * session the user has since logged out of (spec section 17/26): every
 * `logout()`/fatal session failure increments the epoch, and a refresh
 * that resolves against a stale epoch is discarded rather than applied.
 */
let epoch = 0;
let inFlightRefresh: Promise<string> | null = null;

export function getSessionEpoch(): number {
  return epoch;
}

/** Called by sessionManager on logout / terminal session failure. Any
 * refresh promise already in flight will still resolve, but its result is
 * discarded once it notices the epoch moved (see the check inside
 * `performRefresh`). */
export function bumpSessionEpoch(): number {
  epoch += 1;
  inFlightRefresh = null;
  return epoch;
}

async function performRefresh(customerId: CustomerId): Promise<string> {
  const epochAtStart = epoch;
  const stored = await loadSession();
  if (!stored?.refreshToken) {
    throw new DomainError({ category: "SESSION_EXPIRED", diagnostic: "No refresh token available" });
  }

  let response;
  try {
    response = await refreshSessionApi(stored.refreshToken);
  } catch (err) {
    // A network failure during refresh must not clear tokens -- only a
    // definitive backend rejection (expired/reused/revoked) does that;
    // see the catch-free path below where mapApiError already produced a
    // SESSION_EXPIRED-category DomainError for those cases specifically.
    if (err instanceof DomainError && err.category === "SESSION_EXPIRED") {
      if (epoch === epochAtStart) await clearSession();
      throw err;
    }
    throw err;
  }

  // Epoch changed while the network call was in flight (e.g. the user
  // logged out mid-refresh) -- this response must never restore a
  // cleared session (spec section 17/26).
  if (epoch !== epochAtStart) {
    throw new DomainError({ category: "SESSION_EXPIRED", diagnostic: "Session was invalidated during refresh" });
  }

  await rotateTokens(response.data.access_token, response.data.refresh_token, customerId);
  return response.data.access_token;
}

/**
 * Returns a fresh access token, coordinating so only one HTTP refresh
 * call is ever in flight regardless of how many callers ask concurrently
 * (spec section 17 test: "multiple concurrent expired requests → one
 * refresh for all waiters").
 */
export async function getRefreshedAccessToken(customerId: CustomerId): Promise<string> {
  if (!inFlightRefresh) {
    inFlightRefresh = performRefresh(customerId).finally(() => {
      inFlightRefresh = null;
    });
  }
  return inFlightRefresh;
}

/** Test-only reset. */
export function __resetRefreshCoordinatorForTests(): void {
  epoch = 0;
  inFlightRefresh = null;
}
