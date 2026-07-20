import type { StartupPhase, StartupPhaseRecord, StartupSnapshot, StartupErrorCategory, InitialRouteDecision } from "./startup-types";
import type { ResolvedRemoteConfig } from "../../remote-config/remote-config-types";
import type { AuthPlaceholderState, OnboardingPlaceholderState } from "../../navigation/route-guards";

export type StartupAction =
  | { type: "RESET" }
  | { type: "PHASE_STARTED"; phase: StartupPhase; at: string }
  | { type: "PHASE_COMPLETED"; phase: StartupPhase; at: string; result: "success" | "fallback"; fallbackUsed?: boolean }
  | { type: "PHASE_FAILED"; phase: StartupPhase; at: string; category: StartupErrorCategory; retryAllowed: boolean }
  | { type: "CONFIG_RESOLVED"; config: ResolvedRemoteConfig }
  | { type: "AUTH_RESOLVED"; auth: AuthPlaceholderState }
  | { type: "ONBOARDING_RESOLVED"; onboarding: OnboardingPlaceholderState }
  | { type: "CONNECTIVITY_RESOLVED"; connectivity: "online" | "offline" | "unknown" }
  | { type: "ROUTE_RESOLVED"; decision: InitialRouteDecision }
  | { type: "READY"; at: string }
  | { type: "DEGRADED"; at: string }
  | { type: "FAILED"; at: string; category: StartupErrorCategory; message: string; errorReferenceId: string };

export function createInitialStartupSnapshot(): StartupSnapshot {
  return {
    sequenceId: 0,
    status: "idle",
    currentPhase: "idle",
    phaseHistory: [],
    auth: "unknown",
    onboarding: "unknown",
    connectivity: "unknown",
  };
}

/**
 * Pure reducer — no I/O, no timers, no navigation. The startup service
 * (startup-service.ts) is the only thing that dispatches into this and
 * performs the actual async work; this function only ever computes the next
 * snapshot from the current one, which is what makes it unit-testable
 * without mounting the app.
 */
export function startupReducer(state: StartupSnapshot, action: StartupAction): StartupSnapshot {
  switch (action.type) {
    case "RESET":
      return { ...createInitialStartupSnapshot(), sequenceId: state.sequenceId + 1, status: "running" };

    case "PHASE_STARTED":
      return {
        ...state,
        currentPhase: action.phase,
        phaseHistory: [...state.phaseHistory, { phase: action.phase, startedAt: action.at }],
        startedAt: state.startedAt ?? (action.phase === "initializing" ? action.at : state.startedAt),
      };

    case "PHASE_COMPLETED":
      return {
        ...state,
        phaseHistory: updateLastPhase(state.phaseHistory, action.phase, { completedAt: action.at, result: action.result, fallbackUsed: action.fallbackUsed }),
      };

    case "PHASE_FAILED":
      return {
        ...state,
        phaseHistory: updateLastPhase(state.phaseHistory, action.phase, {
          completedAt: action.at,
          result: "error",
          errorCategory: action.category,
          retryAllowed: action.retryAllowed,
        }),
      };

    case "CONFIG_RESOLVED":
      return { ...state, resolvedConfig: action.config };

    case "AUTH_RESOLVED":
      return { ...state, auth: action.auth };

    case "ONBOARDING_RESOLVED":
      return { ...state, onboarding: action.onboarding };

    case "CONNECTIVITY_RESOLVED":
      return { ...state, connectivity: action.connectivity };

    case "ROUTE_RESOLVED":
      return { ...state, routeDecision: action.decision };

    case "READY":
      return { ...state, status: "ready", currentPhase: "ready", readyAt: action.at };

    case "DEGRADED":
      return { ...state, status: "degraded", currentPhase: "degraded", readyAt: action.at };

    case "FAILED":
      return {
        ...state,
        status: "failed",
        currentPhase: "failed",
        error: { category: action.category, message: action.message, errorReferenceId: action.errorReferenceId },
      };

    default:
      return state;
  }
}

function updateLastPhase(history: StartupPhaseRecord[], phase: StartupPhase, patch: Partial<StartupPhaseRecord>): StartupPhaseRecord[] {
  const index = [...history].reverse().findIndex((record) => record.phase === phase && !record.completedAt);
  if (index === -1) return history;
  const realIndex = history.length - 1 - index;
  const next = [...history];
  next[realIndex] = { ...next[realIndex], ...patch };
  return next;
}
