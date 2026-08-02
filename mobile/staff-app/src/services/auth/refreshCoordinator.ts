import { refreshToken as callRefreshEndpoint } from "./authApi";
import { registerRefreshHandler, RefreshOutcome } from "../api/authenticatedClient";
import { getRefreshToken, getSessionId, setTokens, clearTokens } from "./tokenCoordinator";
import { writeSessionBundle, clearSessionBundle } from "./sessionStorage";
import { emitSessionEvent } from "./sessionEvents";

/**
 * Concurrency-safe refresh coordinator (Phase F spec section 9). Exactly
 * one refresh request runs at a time; every concurrent caller (e.g. three
 * screens whose queries all got a 401 at once) awaits the SAME in-flight
 * promise rather than each firing their own refresh.
 */
let inFlight: Promise<RefreshOutcome> | null = null;

export async function refresh(): Promise<RefreshOutcome> {
  if (inFlight) return inFlight;
  inFlight = doRefresh();
  try {
    return await inFlight;
  } finally {
    inFlight = null;
  }
}

async function terminalFailure(kind: "expired" | "reused" | "persist_failed"): Promise<void> {
  await clearSessionBundle();
  clearTokens();
  if (kind === "reused") {
    emitSessionEvent({ type: "SESSION_REVOKED", reasonCode: "REFRESH_TOKEN_REUSED" });
  } else {
    emitSessionEvent({ type: "SESSION_EXPIRED", reasonCode: kind === "persist_failed" ? "PERSIST_FAILED" : "REFRESH_TOKEN_EXPIRED" });
  }
}

async function doRefresh(): Promise<RefreshOutcome> {
  const raw = getRefreshToken();
  if (!raw) {
    await terminalFailure("expired");
    return { ok: false };
  }

  const result = await callRefreshEndpoint(raw);
  if (!result.ok) {
    // Reuse detection and genuine expiry both terminate the session --
    // any other failure (network/server) is transient and left alone so
    // the caller can retry later without destroying a still-valid session.
    if (result.error.code === "REFRESH_TOKEN_REUSED") {
      await terminalFailure("reused");
    } else if (result.error.code === "REFRESH_TOKEN_EXPIRED") {
      await terminalFailure("expired");
    }
    return { ok: false };
  }

  try {
    await writeSessionBundle({
      schemaVersion: 1,
      accessToken: result.data.access_token,
      refreshToken: result.data.refresh_token,
      sessionId: getSessionId(),
    });
  } catch {
    // Persistence failed after a successful rotation -- fail closed rather
    // than run with tokens that exist in memory but not on disk (spec
    // section 9: a later cold start would restore a stale/absent bundle).
    await terminalFailure("persist_failed");
    return { ok: false };
  }

  setTokens({ accessToken: result.data.access_token, refreshToken: result.data.refresh_token });
  emitSessionEvent({ type: "SESSION_REFRESHED" });
  return { ok: true, accessToken: result.data.access_token };
}

registerRefreshHandler(refresh);

/** Test-only: lets tests re-register after resetting authenticatedClient's handler slot. */
export function __registerRefreshHandlerForTests(): void {
  registerRefreshHandler(refresh);
}
