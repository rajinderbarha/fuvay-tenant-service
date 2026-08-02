import { SessionState } from "./types";

export const selectBootstrapStatus = (state: SessionState) => state.bootstrapStatus;
export const selectIsAuthenticated = (state: SessionState) => state.authenticated;
export const selectAccessContext = (state: SessionState) => state.accessContext;
export const selectNetworkStatus = (state: SessionState) => state.networkStatus;
export const selectSessionError = (state: SessionState) => state.sessionError;
export const selectPendingSafeDestination = (state: SessionState) => state.pendingSafeDestination;

/** True only once bootstrap has left "initializing" -- gates whether it's
 * safe to render anything other than the branded splash. */
export const selectBootstrapComplete = (state: SessionState) => state.bootstrapStatus !== "initializing";
