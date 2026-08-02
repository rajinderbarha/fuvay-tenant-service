/**
 * Centralized route registry (spec sections 2, 8, 9). Every internal
 * navigable destination -- reachable from a tab press, a deep link, or a
 * push notification -- is declared here exactly once. Deep-linking and
 * push-routing both resolve through this same table, so a link can never
 * reach a screen that isn't already a normal in-app route.
 */
export type RouteKey =
  | "HOME"
  | "JOBS"
  | "SCHEDULE"
  | "NOTIFICATIONS"
  | "PROFILE"
  | "JOB_DETAIL"
  | "JOB_INSPECTION"
  | "JOB_ESTIMATE"
  | "JOB_ESTIMATE_REVISION"
  | "JOB_PARTS"
  | "JOB_CHECKLIST"
  | "JOB_COMPLETION"
  | "JOB_DIRECT_PAYMENT";

export interface RouteDefinition {
  key: RouteKey;
  tree: "AppTabs" | "JobExecutionStack";
  screen: string;
  requiresJobId: boolean;
  /** Capability the access context must carry to open this route (step 10). */
  requiredCapability?: string;
}

export const ROUTE_REGISTRY: Record<RouteKey, RouteDefinition> = {
  HOME:                   { key: "HOME",                   tree: "AppTabs",           screen: "Home",          requiresJobId: false },
  JOBS:                   { key: "JOBS",                   tree: "AppTabs",           screen: "Jobs",          requiresJobId: false },
  SCHEDULE:               { key: "SCHEDULE",               tree: "AppTabs",           screen: "Schedule",      requiresJobId: false },
  NOTIFICATIONS:          { key: "NOTIFICATIONS",           tree: "AppTabs",           screen: "Notifications", requiresJobId: false },
  PROFILE:                { key: "PROFILE",                tree: "AppTabs",           screen: "Profile",       requiresJobId: false },
  JOB_DETAIL:             { key: "JOB_DETAIL",             tree: "JobExecutionStack", screen: "JobDetail",              requiresJobId: true },
  JOB_INSPECTION:         { key: "JOB_INSPECTION",         tree: "JobExecutionStack", screen: "Inspection",             requiresJobId: true, requiredCapability: "job:inspection:update" },
  JOB_ESTIMATE:           { key: "JOB_ESTIMATE",           tree: "JobExecutionStack", screen: "Estimate",               requiresJobId: true, requiredCapability: "job:estimate:read" },
  JOB_ESTIMATE_REVISION:  { key: "JOB_ESTIMATE_REVISION",  tree: "JobExecutionStack", screen: "EstimateRevision",       requiresJobId: true, requiredCapability: "job:estimate:update" },
  JOB_PARTS:              { key: "JOB_PARTS",              tree: "JobExecutionStack", screen: "PartsRequest",           requiresJobId: true, requiredCapability: "job:parts:request" },
  JOB_CHECKLIST:          { key: "JOB_CHECKLIST",          tree: "JobExecutionStack", screen: "Checklist",              requiresJobId: true, requiredCapability: "job:checklist:update" },
  JOB_COMPLETION:         { key: "JOB_COMPLETION",         tree: "JobExecutionStack", screen: "CompletionProof",        requiresJobId: true, requiredCapability: "job:completion:submit" },
  JOB_DIRECT_PAYMENT:     { key: "JOB_DIRECT_PAYMENT",     tree: "JobExecutionStack", screen: "DirectPaymentConfirmation", requiresJobId: true, requiredCapability: "job:payment:report" },
};

export function resolveRouteDefinition(key: string): RouteDefinition | undefined {
  return (ROUTE_REGISTRY as Record<string, RouteDefinition>)[key];
}
