import { validateJobRoute, JobRouteAdapter, JobSummary } from "../guards/validateJobRoute";
import { resolveAuthorizedRoute } from "../guards/resolveAuthorizedRoute";
import { AccessContext } from "../guards/types";

const ACCESS_CONTEXT: AccessContext = {
  authenticated: true, canonicalRole: "technician", audience: "serviceos:staff",
  tenantId: "t1", tenantStatus: "active", technicianId: "tech1", technicianStatus: "active",
  capabilities: ["job:inspection:update", "job:completion:submit"],
};

function adapterReturning(job: JobSummary | null): JobRouteAdapter {
  return { async fetchJobSummary() { return job; } };
}

describe("validateJobRoute — steps 10-12", () => {
  it("denies with ENTITY_NOT_FOUND when the job doesn't exist", async () => {
    const result = await validateJobRoute({ routeKey: "JOB_DETAIL", jobId: "missing", accessContext: ACCESS_CONTEXT, adapter: adapterReturning(null) });
    expect(result).toEqual({ allowed: false, reasonCode: "ENTITY_NOT_FOUND", destination: { tree: "AppTabs" } });
  });

  it("denies with ENTITY_NOT_FOUND (not a tenant-existence leak) when the job belongs to another tenant", async () => {
    const job: JobSummary = { jobId: "j1", tenantId: "other-tenant", assignedTechnicianId: "tech1", allowedActions: [], allowedRouteKeys: ["JOB_DETAIL"] };
    const result = await validateJobRoute({ routeKey: "JOB_DETAIL", jobId: "j1", accessContext: ACCESS_CONTEXT, adapter: adapterReturning(job) });
    expect(result).toEqual({ allowed: false, reasonCode: "ENTITY_NOT_FOUND", destination: { tree: "AppTabs" } });
  });

  it("denies with ENTITY_NOT_ASSIGNED when the job is assigned to a different technician", async () => {
    const job: JobSummary = { jobId: "j1", tenantId: "t1", assignedTechnicianId: "someone-else", allowedActions: [], allowedRouteKeys: ["JOB_DETAIL"] };
    const result = await validateJobRoute({ routeKey: "JOB_DETAIL", jobId: "j1", accessContext: ACCESS_CONTEXT, adapter: adapterReturning(job) });
    expect(result).toEqual({ allowed: false, reasonCode: "ENTITY_NOT_ASSIGNED", destination: { tree: "AppTabs" } });
  });

  it("denies with ACTION_NOT_ALLOWED and redirects to JobDetail when the screen isn't permitted at the job's current stage", async () => {
    const job: JobSummary = { jobId: "j1", tenantId: "t1", assignedTechnicianId: "tech1", allowedActions: [], allowedRouteKeys: ["JOB_DETAIL"] };
    const result = await validateJobRoute({ routeKey: "JOB_COMPLETION", jobId: "j1", accessContext: ACCESS_CONTEXT, adapter: adapterReturning(job) });
    expect(result).toEqual({ allowed: false, reasonCode: "ACTION_NOT_ALLOWED", destination: { tree: "JobExecutionStack", screen: "JobDetail", params: { jobId: "j1" } } });
  });

  it("denies with ACTION_NOT_ALLOWED when the requested targetAction isn't in the backend's allowed_actions", async () => {
    const job: JobSummary = { jobId: "j1", tenantId: "t1", assignedTechnicianId: "tech1", allowedActions: ["START_INSPECTION"], allowedRouteKeys: ["JOB_INSPECTION"] };
    const result = await validateJobRoute({ routeKey: "JOB_INSPECTION", jobId: "j1", targetAction: "COMPLETE_INSPECTION", accessContext: ACCESS_CONTEXT, adapter: adapterReturning(job) });
    expect(result.allowed).toBe(false);
    expect(result.reasonCode).toBe("ACTION_NOT_ALLOWED");
  });

  it("denies with CAPABILITY_REQUIRED before even calling the job adapter, when the access context lacks the route's capability", async () => {
    const fetchSpy = jest.fn(async () => null);
    const result = await validateJobRoute({
      routeKey: "JOB_ESTIMATE_REVISION", jobId: "j1",
      accessContext: { ...ACCESS_CONTEXT, capabilities: [] },
      adapter: { fetchJobSummary: fetchSpy },
    });
    expect(result.reasonCode).toBe("CAPABILITY_REQUIRED");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("allows a valid, currently-permitted job/action route", async () => {
    const job: JobSummary = { jobId: "j1", tenantId: "t1", assignedTechnicianId: "tech1", allowedActions: ["START_INSPECTION"], allowedRouteKeys: ["JOB_INSPECTION"] };
    const result = await validateJobRoute({ routeKey: "JOB_INSPECTION", jobId: "j1", targetAction: "START_INSPECTION", accessContext: ACCESS_CONTEXT, adapter: adapterReturning(job) });
    expect(result).toEqual({ allowed: true });
  });
});

describe("resolveAuthorizedRoute — full guard chain including root-level session guards", () => {
  it("redirects to AuthStack (SESSION_REQUIRED) before ever consulting the job adapter", async () => {
    const fetchSpy = jest.fn(async () => null);
    const result = await resolveAuthorizedRoute({
      routeKey: "JOB_DETAIL", jobId: "j1", accessContext: { authenticated: false },
      currentAppVersion: "1.0.0", jobAdapter: { fetchJobSummary: fetchSpy },
    });
    expect(result.allowed).toBe(false);
    expect(result.reasonCode).toBe("SESSION_REQUIRED");
    expect(result.destination).toEqual({ tree: "AuthStack", screen: "Login", reasonCode: "SESSION_REQUIRED" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("fails closed with ROUTE_NOT_FOUND for an unknown route key", async () => {
    const result = await resolveAuthorizedRoute({
      routeKey: "NOT_A_REAL_ROUTE", accessContext: ACCESS_CONTEXT,
      currentAppVersion: "1.0.0", jobAdapter: adapterReturning(null),
    });
    expect(result).toEqual({ allowed: false, reasonCode: "ROUTE_NOT_FOUND", destination: { tree: "AppTabs" } });
  });

  it("fails closed with ENTITY_NOT_FOUND when a job route is requested without a jobId", async () => {
    const result = await resolveAuthorizedRoute({
      routeKey: "JOB_DETAIL", accessContext: ACCESS_CONTEXT,
      currentAppVersion: "1.0.0", jobAdapter: adapterReturning(null),
    });
    expect(result).toEqual({ allowed: false, reasonCode: "ENTITY_NOT_FOUND", destination: { tree: "AppTabs" } });
  });

  it("allows a non-job route (e.g. JOBS tab) once every session guard passes", async () => {
    const result = await resolveAuthorizedRoute({
      routeKey: "JOBS", accessContext: ACCESS_CONTEXT,
      currentAppVersion: "1.0.0", jobAdapter: adapterReturning(null),
    });
    expect(result).toEqual({ allowed: true });
  });
});
