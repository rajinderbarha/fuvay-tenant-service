import * as authApi from "./authApi";
import { fetchMappedAccessContext } from "./accessContextApi";
import { readSessionBundle, writeSessionBundle, clearSessionBundle } from "./sessionStorage";
import {
  getAccessToken, getSessionGeneration, isTokenPresent,
  establishTokens, setTokens, clearTokens,
} from "./tokenCoordinator";
import { refresh as coordinatedRefresh } from "./refreshCoordinator";
import { emitSessionEvent } from "./sessionEvents";
import { AccessContext, UNAUTHENTICATED_CONTEXT } from "../../navigation/guards/types";
import { decodeAccessTokenExpiry } from "./tokenInspect";
import { registerPushDevice, revokePushDevice } from "../notifications/pushRegistration";

/**
 * The in-memory session model + orchestrating methods (Phase F spec
 * section 6). This is framework-agnostic (no React) so it's directly unit
 * testable; state/session/SessionProvider.tsx is the thin React binding
 * on top of it.
 */
export interface SessionSnapshot {
  accessTokenPresent: boolean;
  sessionId: string | null;
  expiresAt: string | null;
  authenticated: boolean;
  accessContext: AccessContext;
  lastValidatedAt: string | null;
  sessionGeneration: number;
}

let pendingSafeDestination: string | null = null;

function snapshot(accessContext: AccessContext, lastValidatedAt: string | null): SessionSnapshot {
  return {
    accessTokenPresent: isTokenPresent(),
    sessionId: null,
    expiresAt: decodeAccessTokenExpiry(getAccessToken()),
    authenticated: accessContext.authenticated,
    accessContext,
    lastValidatedAt,
    sessionGeneration: getSessionGeneration(),
  };
}

/**
 * Cold-start restoration (steps 2-7 of spec section 7; step 1/env-load and
 * step 8/9 route-guard-resolution live in sessionBootstrap.ts +
 * navigation). Never trusts a locally-decoded token as proof of session
 * validity -- always calls the backend (directly, or via one coordinated
 * refresh) before returning `authenticated: true`.
 */
export async function restoreSession(): Promise<SessionSnapshot> {
  const bundle = await readSessionBundle();
  if (!bundle) {
    return snapshot(UNAUTHENTICATED_CONTEXT, null);
  }

  establishTokens({ accessToken: bundle.accessToken, refreshToken: bundle.refreshToken, sessionId: bundle.sessionId });

  const expiresAt = decodeAccessTokenExpiry(bundle.accessToken);
  const isExpired = expiresAt !== null && Date.parse(expiresAt) <= Date.now();

  if (isExpired) {
    const refreshed = await coordinatedRefresh();
    if (!refreshed.ok) {
      // refreshCoordinator already cleared storage/tokens and emitted the
      // right terminal event on a real expiry/reuse; a transient network
      // failure here just means "still not verified" -- resolve unauthenticated,
      // never optimistically authenticated.
      return snapshot(UNAUTHENTICATED_CONTEXT, null);
    }
  }

  return validateSession();
}

/** Calls the backend to fetch the authoritative access context -- this IS
 * the "validation" (there is no separate token-introspection call needed
 * for a normal technician session; a failed authenticated request here
 * means the token is not actually valid regardless of its local expiry). */
export async function validateSession(): Promise<SessionSnapshot> {
  const result = await fetchMappedAccessContext(decodeAccessTokenExpiry(getAccessToken()) ?? undefined);
  const now = new Date().toISOString();

  if (!result.ok) {
    if (result.error.category === "auth") {
      await clearSession(`validate_failed:${result.error.code}`);
    }
    return snapshot(UNAUTHENTICATED_CONTEXT, now);
  }

  emitAccessContextEvents(result.data);
  return snapshot(result.data, now);
}

function emitAccessContextEvents(accessContext: AccessContext): void {
  emitSessionEvent({ type: "ACCESS_CONTEXT_CHANGED", accessContext });
  if (accessContext.tenantStatus && accessContext.tenantStatus !== "active") {
    emitSessionEvent({ type: "TENANT_RESTRICTED", accessContext });
  }
  if (accessContext.technicianStatus && accessContext.technicianStatus !== "active") {
    emitSessionEvent({ type: "TECHNICIAN_RESTRICTED", accessContext });
  }
}

/** Called after a successful login/OTP/MFA verification (Phase F does not
 * call this itself -- Phase (Login) will). `authResult` is the real
 * LoginSuccessDTO-shaped payload. */
export async function establishSession(authResult: { access_token: string; refresh_token: string | null }): Promise<SessionSnapshot> {
  if (!authResult.refresh_token) {
    throw new Error("establishSession requires a refresh_token (force-password-change flows must complete that step first).");
  }
  establishTokens({ accessToken: authResult.access_token, refreshToken: authResult.refresh_token, sessionId: null });
  await writeSessionBundle({ schemaVersion: 1, accessToken: authResult.access_token, refreshToken: authResult.refresh_token, sessionId: null });
  const result = await validateSession();
  emitSessionEvent({ type: "SESSION_ESTABLISHED", accessContext: result.accessContext });
  // Best-effort push-device registration (spec section 6) -- never blocks
  // or fails login; permission prompt only fires if not yet determined.
  registerPushDevice().catch(() => {});
  return result;
}

export async function refreshSession(): Promise<SessionSnapshot> {
  const outcome = await coordinatedRefresh();
  if (!outcome.ok) return snapshot(UNAUTHENTICATED_CONTEXT, null);
  return validateSession();
}

export async function refreshAccessContext(): Promise<SessionSnapshot> {
  return validateSession();
}

/** Local-only cleanup -- always succeeds regardless of network state. */
export async function clearSession(reason: string): Promise<void> {
  await clearSessionBundle();
  clearTokens();
  emitSessionEvent({ type: "SESSION_CLEARED", reason });
}

/** Current-device logout (spec section 19): best-effort backend
 * revocation, but local session is ALWAYS cleared even if the network
 * call fails or the device is offline. */
export async function revokeCurrentSession(): Promise<void> {
  await revokePushDevice();
  try {
    await authApi.logoutCurrentSession();
  } catch {
    // Network failure during logout must not leave the user "stuck" logged in.
  }
  await clearSession("logout_current_device");
}

/** Logout-all (spec section 19): requires the canonical backend endpoint;
 * if it can't be confirmed, the CURRENT device still ends up locally
 * signed out (never left in protected navigation), but the caller should
 * surface that remote revocation of OTHER sessions was not confirmed. */
export async function revokeAllSessions(): Promise<{ remoteConfirmed: boolean; sessionsRevoked?: number }> {
  await revokePushDevice();
  try {
    const result = await authApi.logoutAllSessions();
    await clearSession("logout_all_sessions");
    if (!result.ok) return { remoteConfirmed: false };
    return { remoteConfirmed: true, sessionsRevoked: result.data.sessions_revoked };
  } catch {
    await clearSession("logout_all_sessions_network_failure");
    return { remoteConfirmed: false };
  }
}

/**
 * The backend records device trust against UserSession.is_trusted, set
 * ONLY at login time via LoginRequest.remember_device (see
 * app/engines/auth/service.py AuthService.login). There is no endpoint to
 * mark an *existing* session trusted after the fact -- inventing a
 * mobile-only trust credential here would create a second, competing trust
 * mechanism, which the spec explicitly forbids. This is intentionally
 * unimplemented until/unless the backend adds that endpoint.
 */
export function markSessionTrusted(): never {
  throw new Error("markSessionTrusted is not supported: the backend only sets device trust at login (remember_device), with no endpoint to mark an existing session trusted afterward.");
}

export function setPendingDestination(destination: string | null): void {
  pendingSafeDestination = destination;
}

/** Consumes (returns + clears) the pending post-login destination so it
 * can never be replayed into a second, unintended navigation. */
export function consumePendingDestination(): string | null {
  const destination = pendingSafeDestination;
  pendingSafeDestination = null;
  return destination;
}
