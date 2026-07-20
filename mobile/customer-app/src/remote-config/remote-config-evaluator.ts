import { compareVersions, isValidVersion } from "./version-policy";
import { evaluateMaintenancePolicy } from "./maintenance-policy";
import type { ModuleConfig, RemoteConfigEnvelope } from "./remote-config-schema";

export type ModuleEvaluation =
  "enabled" | "disabled" | "hidden" | "unsupported-version" | "outside-region" | "dependency-disabled" | "maintenance-disabled" | "configuration-invalid";

export interface ModuleEvaluationContext {
  config: RemoteConfigEnvelope;
  appVersion: string;
  regionCode?: string;
  nowIso?: string;
}

/**
 * Centralized module/feature gate — the only place that should decide
 * whether a business module is reachable. Fails closed: any ambiguous or
 * invalid input resolves to a non-enabled outcome, never "enabled".
 */
export function evaluateModule(moduleKey: string, context: ModuleEvaluationContext): ModuleEvaluation {
  const module = context.config.modules.find((candidate) => candidate.key === moduleKey);
  if (!module) return "configuration-invalid";

  const maintenance = evaluateMaintenancePolicy(context.config.maintenance, context.nowIso);
  if (maintenance.blocking) return "maintenance-disabled";

  if (!module.enabled) return "disabled";
  if (!module.visible) return "hidden";

  if (module.minAppVersion) {
    if (!isValidVersion(context.appVersion) || !isValidVersion(module.minAppVersion)) return "configuration-invalid";
    if (compareVersions(context.appVersion, module.minAppVersion) < 0) return "unsupported-version";
  }

  if (module.supportedRegions && module.supportedRegions.length > 0) {
    if (!context.regionCode || !module.supportedRegions.includes(context.regionCode)) return "outside-region";
  }

  for (const dependencyKey of module.dependsOn) {
    const dependencyEvaluation = evaluateModule(dependencyKey, context);
    if (dependencyEvaluation !== "enabled") return "dependency-disabled";
  }

  return "enabled";
}

export function listEnabledModules(context: ModuleEvaluationContext): ModuleConfig[] {
  return context.config.modules.filter((module) => evaluateModule(module.key, context) === "enabled").sort((a, b) => a.order - b.order);
}
