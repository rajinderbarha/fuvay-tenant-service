/**
 * Deterministic session state machine (spec section 16). Every transition
 * is explicit and validated by `isValidTransition` -- an attempted
 * transition not in `ALLOWED_TRANSITIONS` is rejected rather than
 * silently applied, which is what makes the prohibited transitions listed
 * in the spec (mfa_required → authenticated without a challenge, etc.)
 * structurally impossible rather than merely "shouldn't happen."
 */
export type SessionState =
  | "uninitialized"
  | "restoring"
  | "unauthenticated"
  | "authenticating"
  | "mfa_required"
  | "authenticated"
  | "refreshing"
  | "session_expired"
  | "account_suspended"
  | "invalid_audience"
  | "network_degraded"
  | "fatal_error";

const ALLOWED_TRANSITIONS: Record<SessionState, readonly SessionState[]> = {
  uninitialized: ["restoring"],
  restoring: ["unauthenticated", "authenticated", "session_expired", "invalid_audience", "account_suspended", "fatal_error", "network_degraded"],
  unauthenticated: ["authenticating"],
  authenticating: ["authenticated", "mfa_required", "unauthenticated", "account_suspended", "invalid_audience", "network_degraded"],
  // Only a successfully-verified challenge may reach `authenticated` --
  // there is no `mfa_required -> authenticated` transition without first
  // passing through `authenticating` again (the MFA-verify call), which
  // is itself the only edge into `authenticated` from this state.
  mfa_required: ["authenticating", "unauthenticated"],
  authenticated: ["refreshing", "session_expired", "account_suspended", "invalid_audience", "unauthenticated", "network_degraded"],
  refreshing: ["authenticated", "session_expired", "invalid_audience", "network_degraded"],
  // Terminal-ish states: only reachable path back into the app is a fresh
  // login (unauthenticated), never a silent return to `authenticated`.
  session_expired: ["unauthenticated"],
  account_suspended: ["unauthenticated"],
  invalid_audience: ["unauthenticated"],
  network_degraded: ["restoring", "authenticating", "refreshing", "unauthenticated"],
  fatal_error: ["restoring"],
};

export function isValidTransition(from: SessionState, to: SessionState): boolean {
  return ALLOWED_TRANSITIONS[from].includes(to);
}

export class InvalidSessionTransitionError extends Error {
  constructor(public readonly from: SessionState, public readonly to: SessionState) {
    super(`Invalid session transition: ${from} -> ${to}`);
    this.name = "InvalidSessionTransitionError";
  }
}

/** Throws rather than silently no-op-ing on an invalid transition --
 * session bugs here are exactly the class of bug that must fail loudly
 * in development, not degrade into a confusing runtime state. */
export function assertValidTransition(from: SessionState, to: SessionState): void {
  if (!isValidTransition(from, to)) {
    throw new InvalidSessionTransitionError(from, to);
  }
}
