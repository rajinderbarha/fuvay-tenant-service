import { compareVersions, isValidVersion } from "../../../remote-config/version-policy";
import { isSupportedModuleType, type HomeModuleEnvelope } from "./home-module-types";

export type ModuleVisibilityOutcome = "VISIBLE" | "HIDDEN" | "DISABLED" | "UNSUPPORTED_VERSION" | "OUTSIDE_REGION" | "AUTH_REQUIRED" | "CONFIGURATION_INVALID";

export interface ModuleVisibilityContext {
  authenticated: boolean;
  appVersion: string;
  regionCode?: string;
  enabled?: boolean;
}

/**
 * Centralized, deterministic evaluator (CUSTOMER-L5-03 §9) — module
 * components must never re-implement these checks themselves. Fails
 * closed: any ambiguous, invalid, or unknown-type module resolves to a
 * non-visible outcome, never VISIBLE.
 */
export function evaluateModuleVisibility(module: HomeModuleEnvelope, context: ModuleVisibilityContext): ModuleVisibilityOutcome {
  if (!isSupportedModuleType(module.type)) return "CONFIGURATION_INVALID";
  if (context.enabled === false) return "DISABLED";
  if (module.requiresAuth && !context.authenticated) return "AUTH_REQUIRED";

  if (module.minAppVersion) {
    if (!isValidVersion(context.appVersion) || !isValidVersion(module.minAppVersion)) return "CONFIGURATION_INVALID";
    if (compareVersions(context.appVersion, module.minAppVersion) < 0) return "UNSUPPORTED_VERSION";
  }

  if (module.regions && module.regions.length > 0) {
    if (!context.regionCode || !module.regions.includes(context.regionCode)) return "OUTSIDE_REGION";
  }

  return "VISIBLE";
}

export function filterVisibleModules<T extends HomeModuleEnvelope>(modules: T[], context: ModuleVisibilityContext): T[] {
  return modules.filter((module) => evaluateModuleVisibility(module, context) === "VISIBLE").sort((a, b) => a.order - b.order);
}
