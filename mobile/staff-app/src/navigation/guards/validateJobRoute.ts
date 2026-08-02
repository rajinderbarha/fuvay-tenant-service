import { AccessContext, GuardResult } from "./types";
import { RouteKey, resolveRouteDefinition } from "../routeRegistry";
import { checkCapability } from "./resolveNavigationState";

/**
 * Steps 11-12 of the guard order: a valid jobId in a deep link or push
 * payload never authorizes access by itself (spec section 7). This module
 * defines the validation *contract* only -- Phase E does not call a real
 * job API. The adapter is injected so Phase F can swap in a real TanStack
 * Query-backed implementation without this guard logic changing, and so
 * tests can exercise every branch with fixtures.
 */
export interface JobSummary {
  jobId: string;
  tenantId: string;
  /** Technician currently assigned, if any -- compared against the
   * access context's technicianId, never against userId. */
  assignedTechnicianId: string | null;
  /** Backend-provided allow-list for the job's current stage (spec: entity/
   * workflow versions are handled by the feature mutation later; this
   * contract only checks whether the action is currently permitted at all). */
  allowedActions: string[];
  /** Screens permitted at the job's current stage, e.g. "Inspection" is not
   * reachable before the job has been accepted. Keyed by RouteKey. */
  allowedRouteKeys: RouteKey[];
}

export interface JobRouteAdapter {
  /** Resolves a job by ID, scoped to the caller's own tenant/session.
   * Returns null if the job doesn't exist or isn't visible to this caller
   * (the adapter itself must not leak cross-tenant existence). */
  fetchJobSummary(jobId: string): Promise<JobSummary | null>;
}

export interface ValidateJobRouteInput {
  routeKey: RouteKey;
  jobId: string;
  targetAction?: string;
  accessContext: AccessContext;
  adapter: JobRouteAdapter;
}

/**
 * Full job-route authorization: entity existence -> tenant match ->
 * assignment -> stage-permitted screen -> capability -> requested action
 * allowed. Denial never exposes customer information -- the only outputs
 * are a boolean, a reason code, and a safe redirect destination.
 */
export async function validateJobRoute({ routeKey, jobId, targetAction, accessContext, adapter }: ValidateJobRouteInput): Promise<GuardResult> {
  const route = resolveRouteDefinition(routeKey);
  if (!route || route.tree !== "JobExecutionStack") {
    return { allowed: false, reasonCode: "ROUTE_NOT_FOUND", destination: { tree: "AppTabs" } };
  }

  const capabilityCheck = checkCapability(accessContext, route.requiredCapability);
  if (!capabilityCheck.allowed) return capabilityCheck;

  const job = await adapter.fetchJobSummary(jobId);
  if (!job) {
    return { allowed: false, reasonCode: "ENTITY_NOT_FOUND", destination: { tree: "AppTabs" } };
  }

  if (job.tenantId !== accessContext.tenantId) {
    // Cross-tenant existence is never disclosed as "not found" vs "not
    // yours" -- both collapse to the same reason code and destination.
    return { allowed: false, reasonCode: "ENTITY_NOT_FOUND", destination: { tree: "AppTabs" } };
  }

  if (job.assignedTechnicianId !== accessContext.technicianId) {
    return { allowed: false, reasonCode: "ENTITY_NOT_ASSIGNED", destination: { tree: "AppTabs" } };
  }

  if (!job.allowedRouteKeys.includes(routeKey)) {
    return { allowed: false, reasonCode: "ACTION_NOT_ALLOWED", destination: { tree: "JobExecutionStack", screen: "JobDetail", params: { jobId } } };
  }

  if (targetAction && !job.allowedActions.includes(targetAction)) {
    return { allowed: false, reasonCode: "ACTION_NOT_ALLOWED", destination: { tree: "JobExecutionStack", screen: "JobDetail", params: { jobId } } };
  }

  return { allowed: true };
}
