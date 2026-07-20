import { logger } from "../../../observability/logger";
import { isSupportedModuleType, type SupportedModuleType } from "./home-module-types";

/**
 * The centralized module-type → renderer map (CUSTOMER-L5-03 §7: "Create a
 * centralized typed module-renderer registry. Do not use an uncontrolled
 * screen-level switch with business logic scattered across Home."). React
 * components are registered by `HomeScreen` at render time (kept out of
 * this file to avoid a domain module importing React component code);
 * this module owns only the *decision* of which registered renderer key to
 * use for a given backend-reported module type, and the safe-skip behavior
 * for anything unrecognized.
 */
export interface UnknownModuleResult {
  recognized: false;
  moduleType: string;
}

export interface KnownModuleResult {
  recognized: true;
  moduleType: SupportedModuleType;
}

export function resolveModuleRenderer(moduleType: string): KnownModuleResult | UnknownModuleResult {
  if (isSupportedModuleType(moduleType)) {
    return { recognized: true, moduleType };
  }
  // Never crashes the page, never shows the raw type to the customer,
  // never attempts to dynamically resolve a component from the string
  // (CUSTOMER-L5-03 §8: "Do not execute arbitrary component names
  // received from backend.").
  logger.warn("home_module_skipped", { moduleType });
  return { recognized: false, moduleType };
}
