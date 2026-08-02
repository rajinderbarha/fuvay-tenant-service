import { AccessContext, GuardResult, BootstrapState, ReasonCode } from "./types";
import { resolveNavigationState, destinationForBootstrapState, checkCapability } from "./resolveNavigationState";
import { RouteKey, resolveRouteDefinition } from "../routeRegistry";
import { JobRouteAdapter, validateJobRoute } from "./validateJobRoute";

export interface ResolveAuthorizedRouteInput {
  routeKey: string;
  jobId?: string;
  targetAction?: string;
  accessContext: AccessContext;
  currentAppVersion: string;
  jobAdapter: JobRouteAdapter;
}

/**
 * Single entry point used by deep-linking and push-routing (spec sections
 * 8, 9) to decide whether a requested route may be opened right now. Runs
 * the full guard order (1-12): session/audience/role/tenant/technician
 * first (steps 1-9, via resolveNavigationState), then route existence,
 * capability, and -- for job routes -- entity/assignment/stage/action
 * (steps 10-12, via validateJobRoute). Unknown route keys fail closed.
 */
export async function resolveAuthorizedRoute({ routeKey, jobId, targetAction, accessContext, currentAppVersion, jobAdapter }: ResolveAuthorizedRouteInput): Promise<GuardResult> {
  const sessionState = resolveNavigationState({ bootstrapPhase: "restored", accessContext, currentAppVersion });
  if (sessionState.state !== "authenticated_ready") {
    return {
      allowed: false,
      reasonCode: sessionState.reasonCode,
      destination: destinationForBootstrapState(sessionState.state, sessionState.reasonCode),
    };
  }

  const route = resolveRouteDefinition(routeKey);
  if (!route) {
    return { allowed: false, reasonCode: "ROUTE_NOT_FOUND", destination: { tree: "AppTabs" } };
  }

  if (route.tree === "JobExecutionStack") {
    if (!jobId) {
      return { allowed: false, reasonCode: "ENTITY_NOT_FOUND", destination: { tree: "AppTabs" } };
    }
    return validateJobRoute({ routeKey: route.key as RouteKey, jobId, targetAction, accessContext, adapter: jobAdapter });
  }

  const capabilityResult = checkCapability(accessContext, route.requiredCapability);
  if (!capabilityResult.allowed) return capabilityResult;

  return { allowed: true };
}

export type { BootstrapState, ReasonCode };
