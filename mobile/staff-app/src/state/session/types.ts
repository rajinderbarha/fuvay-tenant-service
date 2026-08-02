import { BootstrapState, AccessContext, ReasonCode } from "../../navigation/guards/types";
import { NetworkState } from "../../services/api/types";

export type { BootstrapState, AccessContext, ReasonCode, NetworkState };

/**
 * React-facing session state (Phase F spec section 6). Composes
 * services/auth/sessionManager's framework-agnostic snapshot with the
 * fields that are specifically about presenting/driving the UI
 * (bootstrapStatus feeds Phase E's navigation guards directly; raw tokens
 * are never included here).
 */
export interface SessionState {
  bootstrapStatus: BootstrapState;
  accessTokenPresent: boolean;
  sessionId: string | null;
  expiresAt: string | null;
  authenticated: boolean;
  accessContext: AccessContext;
  lastValidatedAt: string | null;
  networkStatus: NetworkState;
  sessionError: ReasonCode | null;
  pendingSafeDestination: string | null;
  sessionGeneration: number;
}

export const INITIAL_SESSION_STATE: SessionState = {
  bootstrapStatus: "initializing",
  accessTokenPresent: false,
  sessionId: null,
  expiresAt: null,
  authenticated: false,
  accessContext: { authenticated: false },
  lastValidatedAt: null,
  networkStatus: "unknown",
  sessionError: null,
  pendingSafeDestination: null,
  sessionGeneration: 0,
};
