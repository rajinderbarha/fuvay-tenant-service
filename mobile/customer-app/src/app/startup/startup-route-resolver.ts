import { evaluateVersionPolicy } from "../../remote-config/version-policy";
import { evaluateMaintenancePolicy } from "../../remote-config/maintenance-policy";
import type { RemoteConfigEnvelope } from "../../remote-config/remote-config-schema";
import type { AuthPlaceholderState, OnboardingPlaceholderState } from "../../navigation/route-guards";
import type { PendingDestination } from "../../navigation/deep-links/pending-deep-link-store";
import type { InitialRouteDecision } from "./startup-types";

export interface StartupRouteResolverInput {
  environmentValid: boolean;
  buildSupported: boolean;
  config?: RemoteConfigEnvelope;
  configSource: "compiled-defaults" | "cache-fresh" | "cache-stale-permitted" | "remote-fresh" | "remote-not-modified" | "none";
  currentVersion: string;
  currentBuildNumber: string;
  platform: "ios" | "android";
  connectivity: "online" | "offline" | "unknown";
  auth: AuthPlaceholderState;
  onboarding: OnboardingPlaceholderState;
  pendingDeepLink?: PendingDestination | null;
  pendingNotification?: { routeId: string; params: Record<string, string> } | null;
  startupFailed: boolean;
  nowIso?: string;
}

/**
 * Pure and deterministic — performs no navigation, no I/O. Implements the
 * priority order documented in docs/customer-app/CUSTOMER-L5-01-startup-architecture.md:
 * mandatory system gates always outrank business/deep-link/notification
 * destinations, and a deep link can never bypass them.
 */
export function resolveInitialRoute(input: StartupRouteResolverInput): InitialRouteDecision {
  if (!input.environmentValid) {
    return { routeId: "unsupportedBuild", reason: "invalid-environment", shouldConsumeDeepLink: false, shouldConsumeNotification: false, degradedMode: true };
  }

  if (!input.buildSupported) {
    return { routeId: "unsupportedBuild", reason: "unsupported-build", shouldConsumeDeepLink: false, shouldConsumeNotification: false, degradedMode: true };
  }

  if (input.startupFailed || !input.config) {
    if (input.connectivity === "offline" && input.configSource === "none") {
      return { routeId: "offlineStartup", reason: "offline-no-cache", shouldConsumeDeepLink: false, shouldConsumeNotification: false, degradedMode: true };
    }
    return { routeId: "startupError", reason: "startup-failure", shouldConsumeDeepLink: false, shouldConsumeNotification: false, degradedMode: true };
  }

  const maintenance = evaluateMaintenancePolicy(input.config.maintenance, input.nowIso);
  if (maintenance.blocking) {
    return { routeId: "maintenance", reason: "mandatory-maintenance", shouldConsumeDeepLink: false, shouldConsumeNotification: false, degradedMode: false };
  }

  const version = evaluateVersionPolicy({
    currentVersion: input.currentVersion,
    currentBuildNumber: input.currentBuildNumber,
    platform: input.platform,
    policy: input.config.versionPolicy,
    nowIso: input.nowIso,
  });
  if (version.outcome === "mandatory-update" || version.outcome === "blocked-build") {
    return { routeId: "mandatoryUpdate", reason: "mandatory-update", shouldConsumeDeepLink: false, shouldConsumeNotification: false, degradedMode: false };
  }

  if (!input.config.marketplace.active || !input.config.marketplace.customerAppEnabled || !input.config.application.customerAppEnabled) {
    return {
      routeId: "appUnavailable",
      reason: "marketplace-unavailable",
      shouldConsumeDeepLink: false,
      shouldConsumeNotification: false,
      degradedMode: false,
    };
  }

  const degradedMode = input.configSource === "cache-stale-permitted" || input.configSource === "compiled-defaults";

  if (input.connectivity === "offline" && input.configSource === "none") {
    return { routeId: "offlineStartup", reason: "offline-no-cache", shouldConsumeDeepLink: false, shouldConsumeNotification: false, degradedMode: true };
  }

  if (input.auth === "unknown") {
    return { routeId: "startup", reason: "auth-required", shouldConsumeDeepLink: false, shouldConsumeNotification: false, degradedMode };
  }

  if (input.auth === "guest" && input.pendingDeepLink?.requiresAuth) {
    return { routeId: "authentication", reason: "auth-required", shouldConsumeDeepLink: false, shouldConsumeNotification: false, degradedMode };
  }

  if (input.onboarding === "required") {
    return { routeId: "baselineLanding", reason: "onboarding-required", shouldConsumeDeepLink: false, shouldConsumeNotification: false, degradedMode };
  }

  if (input.pendingDeepLink && !input.pendingDeepLink.consumed) {
    return {
      routeId: input.pendingDeepLink.routeId,
      params: input.pendingDeepLink.params,
      reason: "deep-link",
      shouldConsumeDeepLink: true,
      shouldConsumeNotification: false,
      degradedMode,
    };
  }

  if (input.pendingNotification) {
    return {
      routeId: input.pendingNotification.routeId as InitialRouteDecision["routeId"],
      params: input.pendingNotification.params,
      reason: "notification",
      shouldConsumeDeepLink: false,
      shouldConsumeNotification: true,
      degradedMode,
    };
  }

  // An explicit remote-config override always wins. Otherwise, an
  // authenticated customer lands on the real Home screen (CUSTOMER-L5-03);
  // a guest lands on the compiled-safe baseline (no production customer
  // screen should render for a signed-out visitor this sprint).
  const fallback = input.config.navigation.initialRouteOverride ?? (input.auth === "authenticated" ? "home" : input.config.navigation.fallbackRouteId);
  return {
    routeId: (fallback as InitialRouteDecision["routeId"]) || "baselineLanding",
    reason: "default-landing",
    shouldConsumeDeepLink: false,
    shouldConsumeNotification: false,
    degradedMode,
  };
}
