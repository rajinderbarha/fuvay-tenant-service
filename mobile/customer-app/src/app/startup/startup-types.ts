import type { RouteId } from "../../navigation/route-registry";
import type { AuthPlaceholderState, OnboardingPlaceholderState } from "../../navigation/route-guards";
import type { ResolvedRemoteConfig } from "../../remote-config/remote-config-types";

export const STARTUP_PHASES = [
  "idle",
  "initializing",
  "validating-environment",
  "loading-local-preferences",
  "loading-secure-session-placeholder",
  "resolving-locale",
  "resolving-theme",
  "checking-connectivity",
  "loading-cached-config",
  "fetching-remote-config",
  "evaluating-version-policy",
  "evaluating-maintenance-policy",
  "resolving-marketplace-context",
  "resolving-auth-placeholder",
  "resolving-onboarding-placeholder",
  "resolving-deep-link",
  "resolving-initial-route",
  "ready",
  "degraded",
  "failed",
] as const;

export type StartupPhase = (typeof STARTUP_PHASES)[number];

export type StartupErrorCategory = "environment_invalid" | "build_unsupported" | "config_unreachable" | "config_invalid" | "timeout" | "cancelled" | "unknown";

export interface StartupPhaseRecord {
  phase: StartupPhase;
  startedAt: string;
  completedAt?: string;
  result?: "success" | "fallback" | "error";
  errorCategory?: StartupErrorCategory;
  fallbackUsed?: boolean;
  retryAllowed?: boolean;
}

export type StartupRouteReason =
  | "invalid-environment"
  | "unsupported-build"
  | "mandatory-maintenance"
  | "mandatory-update"
  | "marketplace-unavailable"
  | "startup-failure"
  | "offline-no-cache"
  | "auth-required"
  | "onboarding-required"
  | "deep-link"
  | "notification"
  | "default-landing";

export interface InitialRouteDecision {
  routeId: RouteId;
  params?: Record<string, string>;
  reason: StartupRouteReason;
  shouldConsumeDeepLink: boolean;
  shouldConsumeNotification: boolean;
  degradedMode: boolean;
}

export interface StartupSnapshot {
  sequenceId: number;
  status: "idle" | "running" | "ready" | "degraded" | "failed";
  currentPhase: StartupPhase;
  phaseHistory: StartupPhaseRecord[];
  resolvedConfig?: ResolvedRemoteConfig;
  auth: AuthPlaceholderState;
  onboarding: OnboardingPlaceholderState;
  connectivity: "online" | "offline" | "unknown";
  routeDecision?: InitialRouteDecision;
  error?: { category: StartupErrorCategory; message: string; errorReferenceId: string };
  startedAt?: string;
  readyAt?: string;
  splashHiddenAt?: string;
}
