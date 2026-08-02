import Constants from "expo-constants";
import * as sessionManager from "../../services/auth/sessionManager";
import { SessionSnapshot } from "../../services/auth/sessionManager";
import { resolveNavigationState } from "../../navigation/guards/resolveNavigationState";
import { BootstrapState, ReasonCode, UNAUTHENTICATED_CONTEXT } from "../../navigation/guards/types";
import { isOffline } from "../../services/api/networkState";
import { ENV } from "../../config/environment";

const CURRENT_APP_VERSION = Constants.expoConfig?.version ?? "0.0.0";

export interface BootstrapResult {
  bootstrapStatus: BootstrapState;
  reasonCode?: ReasonCode;
  snapshot: SessionSnapshot;
}

function unauthenticatedSnapshot(): SessionSnapshot {
  return {
    accessTokenPresent: false, sessionId: null, expiresAt: null,
    authenticated: false, accessContext: UNAUTHENTICATED_CONTEXT,
    lastValidatedAt: null, sessionGeneration: 0,
  };
}

/**
 * The full cold-start sequence (Phase F spec section 7), steps 2-9 (step 1,
 * loading ENV, already happened at import time via config/environment.ts).
 * Never trusts a locally-decoded token, never displays protected UI before
 * backend validation, and a network timeout resolves to a locked/offline
 * state rather than silently granting access.
 */
export async function runSessionBootstrap(): Promise<BootstrapResult> {
  if (isOffline()) {
    // Cold start while offline: never treat a stored-but-unverified token
    // as authorization. This is the deliberate locked/offline state (spec
    // section 7) -- Retry/Sign-out actions live in the restricted screen,
    // not here.
    return { bootstrapStatus: "service_unavailable", snapshot: unauthenticatedSnapshot() };
  }

  let timeoutHandle: ReturnType<typeof setTimeout>;
  const timeoutPromise = new Promise<"timeout">(resolve => {
    timeoutHandle = setTimeout(() => resolve("timeout"), ENV.bootstrapTimeoutMs);
  });
  const restorePromise = sessionManager.restoreSession();
  const raced = await Promise.race([restorePromise, timeoutPromise]);
  clearTimeout(timeoutHandle!);

  if (raced === "timeout") {
    // A bounded startup timeout must not silently convert into
    // authenticated access -- resolve to the same locked/offline-style
    // restricted state as being offline, with Retry available.
    return { bootstrapStatus: "service_unavailable", snapshot: unauthenticatedSnapshot() };
  }

  const snapshot = raced;
  const { state, reasonCode } = resolveNavigationState({
    bootstrapPhase: "restored",
    accessContext: snapshot.accessContext,
    currentAppVersion: CURRENT_APP_VERSION,
  });
  return { bootstrapStatus: state, reasonCode, snapshot };
}
