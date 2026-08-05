import { request, RequestOptions, RawResponse } from "./httpClient";
import { getInMemoryAccessToken } from "../session/tokenVault";
import { getRefreshedAccessToken } from "../session/refreshCoordinator";
import { getCurrentCustomerId, logout } from "../session/sessionManager";
import { DomainError } from "../../domain/errors";

/**
 * Wraps the raw HTTP client with automatic 401 recovery for protected
 * endpoints (spec section 9/17): on an `AUTH_REQUIRED`/`SESSION_EXPIRED`
 * failure, attempts exactly ONE refresh-and-retry via the shared
 * refreshCoordinator (never a second attempt -- see the `retried` guard),
 * and never for the refresh/login/logout endpoints themselves (those call
 * `httpClient.request` directly, not this wrapper, so there is no
 * possibility of this recursing into `/token/refresh`).
 */
export async function authenticatedRequest(options: Omit<RequestOptions, "accessToken">): Promise<RawResponse> {
  const accessToken = getInMemoryAccessToken();
  try {
    return await request({ ...options, accessToken });
  } catch (err) {
    const isAuthFailure = err instanceof DomainError && (err.category === "AUTH_REQUIRED" || err.category === "SESSION_EXPIRED");
    if (!isAuthFailure) throw err;

    const customerId = getCurrentCustomerId();
    if (!customerId) throw err;

    let refreshedToken: string;
    try {
      refreshedToken = await getRefreshedAccessToken(customerId);
    } catch {
      await logout();
      throw err;
    }

    try {
      return await request({ ...options, accessToken: refreshedToken });
    } catch (retryErr) {
      const retryIsAuthFailure = retryErr instanceof DomainError && (retryErr.category === "AUTH_REQUIRED" || retryErr.category === "SESSION_EXPIRED");
      if (retryIsAuthFailure) {
        // The refreshed token was itself rejected -- do not attempt a
        // second refresh (no infinite loop); terminate the session.
        await logout();
      }
      throw retryErr;
    }
  }
}
