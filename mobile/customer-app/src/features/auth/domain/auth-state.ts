/**
 * The full state vocabulary from CUSTOMER-L5-02 §8. `session-store.ts`'s
 * `SessionStatus` (`"unknown" | "guest" | "authenticated"`) remains the
 * source of truth for routing (CUSTOMER-L5-01's `route-guards.ts` only
 * needs that three-way split) — this richer `AuthState` is a read-only
 * *view* over the session store plus the in-flight flags already tracked
 * by `useOtpFlow`/`auth-refresh-coordinator.ts`/`useLogout`, used for
 * diagnostics and UI messaging where the extra detail is useful (e.g.
 * distinguishing "refreshing" from "authenticated" in the dev inspector).
 * It is derived, never stored — there is exactly one source of truth
 * (`session-store.ts`), never two competing state machines.
 */
export type AuthState =
  "unknown" | "restoring" | "guest" | "otp-requesting" | "otp-requested" | "otp-verifying" | "authenticated" | "refreshing" | "logging-out" | "error";

export interface AuthStateInputs {
  sessionStatus: "unknown" | "guest" | "authenticated";
  restoring: boolean;
  otpFlowStep?: "enter-phone" | "sending" | "enter-otp" | "verifying";
  refreshing: boolean;
  loggingOut: boolean;
  lastErrorCategory?: string;
}

/**
 * Pure derivation, fully unit-testable. `restoring` always wins over
 * `sessionStatus === "unknown"` being read as a terminal state — "unknown"
 * only means "not yet determined", never a state the UI should branch on
 * directly (see route-guards.ts, which treats it as not-ready).
 */
export function deriveAuthState(inputs: AuthStateInputs): AuthState {
  if (inputs.restoring) return "restoring";
  if (inputs.loggingOut) return "logging-out";
  if (inputs.refreshing) return "refreshing";
  if (inputs.otpFlowStep === "sending") return "otp-requesting";
  if (inputs.otpFlowStep === "enter-otp") return "otp-requested";
  if (inputs.otpFlowStep === "verifying") return "otp-verifying";
  if (inputs.lastErrorCategory) return "error";
  if (inputs.sessionStatus === "authenticated") return "authenticated";
  if (inputs.sessionStatus === "guest") return "guest";
  return "unknown";
}
