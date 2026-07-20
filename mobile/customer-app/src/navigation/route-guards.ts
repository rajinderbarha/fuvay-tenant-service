import { getRouteDefinition, type RouteId } from "./route-registry";
import { evaluateModule, type ModuleEvaluationContext } from "../remote-config/remote-config-evaluator";
import { evaluateMaintenancePolicy } from "../remote-config/maintenance-policy";
import type { RemoteConfigEnvelope } from "../remote-config/remote-config-schema";

/**
 * CUSTOMER-L5-02 implements real authentication. Until then, the app only
 * ever produces "guest" (no fake login success, no fake tokens — see
 * docs/customer-app/CUSTOMER-L5-01-startup-architecture.md §"Placeholders").
 */
export type AuthPlaceholderState = "unknown" | "guest" | "authenticated" | "expired" | "locked";

/** No onboarding screens exist yet (CUSTOMER-L5-00 built none) — "skipped-where-allowed" is the only reachable value this sprint. */
export type OnboardingPlaceholderState = "unknown" | "required" | "completed" | "skipped-where-allowed";

export type RouteGuardDecision =
  | "allow"
  | "deny-not-ready"
  | "deny-maintenance"
  | "deny-version"
  | "deny-marketplace"
  | "deny-auth"
  | "deny-onboarding"
  | "deny-production"
  | "deny-feature"
  | "deny-unknown-route"
  | "deny-development-only";

export interface RouteGuardContext {
  startupReady: boolean;
  config: RemoteConfigEnvelope;
  maintenanceBlocking: boolean;
  versionMandatoryUpdate: boolean;
  marketplaceAvailable: boolean;
  auth: AuthPlaceholderState;
  onboarding: OnboardingPlaceholderState;
  isProductionBuild: boolean;
  isDevBuild: boolean;
  appVersion: string;
  regionCode?: string;
  /** True when the route is being entered via a deep link (tightens deep-link-specific checks). */
  viaDeepLink?: boolean;
  /** True when the route is being entered via a push-notification intent. */
  viaNotification?: boolean;
}

export interface RouteGuardResult {
  decision: RouteGuardDecision;
  routeId: RouteId;
  fallbackRouteId?: RouteId;
}

/**
 * The single centralized access evaluator — screens must not implement
 * their own ad hoc guard logic. Mandatory system gates (maintenance,
 * version policy) are checked before anything route-specific, so a route's
 * own access policy can never override them.
 */
export function evaluateRouteAccess(routeId: string, context: RouteGuardContext): RouteGuardResult {
  const definition = getRouteDefinition(routeId);
  if (!definition) {
    return { decision: "deny-unknown-route", routeId: routeId as RouteId };
  }

  if (!context.startupReady) {
    return { decision: "deny-not-ready", routeId: definition.id, fallbackRouteId: "startup" };
  }

  if (context.maintenanceBlocking) {
    return { decision: "deny-maintenance", routeId: definition.id, fallbackRouteId: "maintenance" };
  }

  if (context.versionMandatoryUpdate) {
    return { decision: "deny-version", routeId: definition.id, fallbackRouteId: "mandatoryUpdate" };
  }

  if (!context.marketplaceAvailable) {
    return { decision: "deny-marketplace", routeId: definition.id, fallbackRouteId: "appUnavailable" };
  }

  if (definition.access === "development-only" && !context.isDevBuild) {
    return { decision: "deny-development-only", routeId: definition.id, fallbackRouteId: definition.fallbackRouteId };
  }

  if (context.isProductionBuild && !definition.productionEnabled) {
    return { decision: "deny-production", routeId: definition.id, fallbackRouteId: definition.fallbackRouteId };
  }

  if (
    (definition.access === "authenticated" || definition.access === "profile-required" || definition.access === "booking-owner-required") &&
    context.auth !== "authenticated"
  ) {
    return { decision: "deny-auth", routeId: definition.id, fallbackRouteId: "authentication" };
  }

  if (definition.access === "authenticated" && context.onboarding === "required") {
    return { decision: "deny-onboarding", routeId: definition.id, fallbackRouteId: definition.fallbackRouteId };
  }

  if (definition.access === "module-enabled" && definition.featureKey) {
    const evaluationContext: ModuleEvaluationContext = { config: context.config, appVersion: context.appVersion, regionCode: context.regionCode };
    if (evaluateModule(definition.featureKey, evaluationContext) !== "enabled") {
      return { decision: "deny-feature", routeId: definition.id, fallbackRouteId: definition.fallbackRouteId };
    }
  }

  if (context.viaDeepLink && !definition.deepLinkEnabled) {
    return { decision: "deny-unknown-route", routeId: definition.id, fallbackRouteId: definition.fallbackRouteId };
  }

  if (context.viaNotification && !definition.notificationEnabled) {
    return { decision: "deny-unknown-route", routeId: definition.id, fallbackRouteId: definition.fallbackRouteId };
  }

  return { decision: "allow", routeId: definition.id };
}

/** Convenience used by the startup route resolver — derives the guard's maintenance input from the raw config. */
export function isMaintenanceBlocking(config: RemoteConfigEnvelope, nowIso?: string): boolean {
  return evaluateMaintenancePolicy(config.maintenance, nowIso).blocking;
}
