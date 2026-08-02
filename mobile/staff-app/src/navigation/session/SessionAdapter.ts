import { AccessContext } from "../guards/types";
import { runSessionBootstrap } from "../../state/session/sessionBootstrap";
import * as sessionManager from "../../services/auth/sessionManager";

/**
 * Injectable session/context adapter (spec section 3). Phase F wires the
 * real auth/session engine (services/auth/sessionManager +
 * state/session/sessionBootstrap) behind this SAME interface, exactly as
 * this file's Phase E comment anticipated -- SessionProvider.tsx itself
 * needed no changes for this. Tests still inject a FixtureSessionAdapter to
 * bypass the network entirely.
 */
export interface SessionAdapter {
  /** Restores session metadata only -- never assumes a stored value is a
   * still-valid session; the caller re-validates via resolveNavigationState. */
  restoreSession(): Promise<AccessContext>;
  clearSession(): Promise<void>;
}

export const secureStoreSessionAdapter: SessionAdapter = {
  async restoreSession(): Promise<AccessContext> {
    const result = await runSessionBootstrap();
    return result.snapshot.accessContext;
  },
  async clearSession(): Promise<void> {
    await sessionManager.clearSession("session_adapter_clear");
  },
};

/** Deterministic adapter for tests/dev fixtures -- never used in a real build. */
export function createFixtureSessionAdapter(context: AccessContext): SessionAdapter {
  return {
    async restoreSession() {
      return context;
    },
    async clearSession() {
      /* no-op */
    },
  };
}
