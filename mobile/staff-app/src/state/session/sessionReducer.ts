import { SessionState } from "./types";
import { SessionSnapshot } from "../../services/auth/sessionManager";
import { BootstrapState, ReasonCode, NetworkState } from "./types";

export type SessionAction =
  | { kind: "BOOTSTRAP_STATE_CHANGED"; bootstrapStatus: BootstrapState; reasonCode?: ReasonCode }
  | { kind: "SNAPSHOT_UPDATED"; snapshot: SessionSnapshot }
  | { kind: "NETWORK_STATE_CHANGED"; networkStatus: NetworkState }
  | { kind: "PENDING_DESTINATION_CHANGED"; destination: string | null };

/** Pure reducer -- every session-state transition is expressed here so it
 * can be unit tested without React or any network call. */
export function sessionReducer(state: SessionState, action: SessionAction): SessionState {
  switch (action.kind) {
    case "BOOTSTRAP_STATE_CHANGED":
      return { ...state, bootstrapStatus: action.bootstrapStatus, sessionError: action.reasonCode ?? null };
    case "SNAPSHOT_UPDATED":
      return {
        ...state,
        accessTokenPresent: action.snapshot.accessTokenPresent,
        sessionId: action.snapshot.sessionId,
        expiresAt: action.snapshot.expiresAt,
        authenticated: action.snapshot.authenticated,
        accessContext: action.snapshot.accessContext,
        lastValidatedAt: action.snapshot.lastValidatedAt,
        sessionGeneration: action.snapshot.sessionGeneration,
      };
    case "NETWORK_STATE_CHANGED":
      return { ...state, networkStatus: action.networkStatus };
    case "PENDING_DESTINATION_CHANGED":
      return { ...state, pendingSafeDestination: action.destination };
    default:
      return state;
  }
}
