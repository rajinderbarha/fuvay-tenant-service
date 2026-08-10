// ═══════════════════════════════════════════════════════════════════════════
// Tenant Home Services workspaces: coverage, complaints, customers, reviews,
// team, services, bookings/jobs, dispatch, documents, settings, onboarding.
//
// Real bug fixed here: fourteen tenant-portal pages and components have
// always imported these API objects and their types from lib/api, but none
// were ever implemented -- so those pages could not compile and the
// tenant-portal production build failed (242 TypeScript errors, 81 of them
// missing exports).
//
// Every path below is matched against a real route in the live OpenAPI
// schema. Where a surface has NO backend route at all, that is stated
// explicitly rather than papered over with an invented endpoint.
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

/** See the tradeoff note in api-tenant-support.ts. These are large,
 * backend-shaped workspace payloads whose exact shape the calling page
 * already asserts; the durable fix is schema tests over captured payloads. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type WsPayload = any;

function post(body?: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(body ?? {}) };
}
function patch(body?: unknown): RequestInit {
  return { method: "PATCH", body: JSON.stringify(body ?? {}) };
}
function del(): RequestInit {
  return { method: "DELETE" };
}
function query(params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(Object.fromEntries(entries.map(([k, v]) => [k, String(v)])))}`;
}

// ── Coverage ───────────────────────────────────────────────────────────────
export type CoverageKpis = WsPayload;
export type CoverageAreaListItem = WsPayload;
export type ServiceCoverageRow = WsPayload;
export type ServiceabilityCheckResult = WsPayload;

export const tenantCoverageApi = {
  /** The coverage workspace is assembled from the tenant's service areas --
   * there is no single "workspace" route, so this is the areas list the
   * page then derives its KPIs from. */
  workspace: <T = WsPayload>() => apiFetch<T>("/v1/tenant/home-services/coverage"),
  areaDetail: <T = WsPayload>(areaKey: string) => apiFetch<T>(`/v1/tenant/home-services/coverage/${areaKey}`),
  checkServiceability: <T = ServiceabilityCheckResult>(payload: Record<string, unknown>) =>
    apiFetch<T>("/v1/serviceability/check", post(payload)),
};

// ── Complaints ─────────────────────────────────────────────────────────────
export type ComplaintQueueItem = WsPayload;
export type ComplaintQueueSummary = WsPayload;
export type ComplaintDetail = WsPayload;

export const tenantComplaintsApi = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  list: <T = WsPayload>(params?: Record<string, any>) =>
    apiFetch<T>(`/v1/tenant/home-services/complaints${query(params)}`),
  detail: <T = ComplaintDetail>(complaintId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/complaints/${complaintId}`),
  activity: <T = WsPayload>(complaintId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/complaints/${complaintId}/activity`),
  jobContext: <T = WsPayload>(complaintId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/complaints/${complaintId}/job-context`),
};

// ── Customers ──────────────────────────────────────────────────────────────
export type HsCustomerListItem = WsPayload;
export type HsCustomerSummary = WsPayload;
export type HsCustomerDetail = WsPayload;

/**
 * Correction to an earlier note here: a real tenant customer directory DOES
 * exist. `/v1/tenant/home-services/customers/*` (9 routes) was written but
 * its router was never mounted, so everything 404'd and the capability
 * looked absent. These previously fell back to the tenant's own
 * booking/job records; they now call the real directory.
 */
export const hsCustomersApi = {
  /** Same aggregation the list rows are built from (backend note: summary
   * and list share one `_customer_aggregates` call so they can never
   * disagree) -- the real source for a KPI strip, not a client-side
   * re-derivation from a single page of `list()` rows. */
  summary: <T = HsCustomerSummary>() => apiFetch<T>("/v1/tenant/home-services/customers/summary"),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  list: <T = WsPayload>(params?: Record<string, any>) =>
    apiFetch<T>(`/v1/tenant/home-services/customers${query(params)}`),
  detail: <T = HsCustomerDetail>(customerId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}`),
  jobs: <T = WsPayload>(customerId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}/jobs`),
  complaints: <T = WsPayload>(customerId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}/complaints`),
  payments: <T = WsPayload>(customerId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}/payments`),
  reviews: <T = WsPayload>(customerId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}/reviews`),
  activity: <T = WsPayload>(customerId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}/activity`),
};

// ── Reviews ────────────────────────────────────────────────────────────────
export type HsReviewListItem = WsPayload;
export type HsReviewDetail = WsPayload;

export const hsReviewsApi = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  list: <T = WsPayload>(params?: Record<string, any>) =>
    apiFetch<T>(`/v1/tenant/home-services/reviews${query(params)}`),
  get: <T = HsReviewDetail>(reviewId: string) => apiFetch<T>(`/v1/tenant/home-services/reviews/${reviewId}`),
  reply: <T = WsPayload>(reviewId: string, body: string) =>
    apiFetch<T>(`/v1/provider/reviews/${reviewId}/reply`, post({ body })),
  /** A provider cannot moderate a review directly -- they FLAG it and admin
   * moderates. Naming it "requestModeration" on the page is accurate. */
  requestModeration: <T = WsPayload>(reviewId: string, reason: string, explanation?: string) =>
    apiFetch<T>(`/v1/provider/reviews/${reviewId}/flag`, post({ reason, explanation })),
};

// ── Team ───────────────────────────────────────────────────────────────────
export type TeamDirectoryStaffRow = WsPayload;
export type StaffOverview = WsPayload;
export type StaffCapabilities = WsPayload;
export type TeamReadinessSummary = WsPayload;

export const homeServicesTeamApi = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  list: <T = WsPayload>(params?: Record<string, any>) => apiFetch<T>(`/v1/tenant/home-services/team${query(params)}`),
  overview: <T = StaffOverview>(staffId: string) => apiFetch<T>(`/v1/tenant/home-services/team/${staffId}/overview`),
  /** Capability = which offerings this member is allowed to be dispatched
   * for; the backend models it as the member record's skills/offerings. */
  capabilities: <T = StaffCapabilities>(staffId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/team/${staffId}/capabilities`),
};

// ── Services workspace ─────────────────────────────────────────────────────
export type SWCatalogService = WsPayload;
export type SWResolvedPrice = WsPayload;
export type SWOfferingDetail = WsPayload;
export type HsSetupAvailableType = WsPayload;

export const servicesWorkspaceApi = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  get: <T = WsPayload>(params?: Record<string, any>) =>
    apiFetch<T>(`/v1/tenant/home-services/services${query(params)}`),
  detail: <T = SWOfferingDetail>(tenantServiceId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/services/${tenantServiceId}`),
};

// ── Bookings & Jobs ────────────────────────────────────────────────────────
export type BJItem = WsPayload;
export type BJDetail = WsPayload;

export const bookingsJobsApi = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  list: <T = WsPayload>(params?: Record<string, any>) =>
    apiFetch<T>(`/v1/tenant/home-services/bookings-jobs${query(params)}`),
  detail: <T = BJDetail>(jobId: string) => apiFetch<T>(`/v1/tenant/home-services/bookings-jobs/${jobId}`),
  /** Confirming payment on a job is a direct-payment declaration -- that is
   * the only money-in action a provider can take against a job. */
  confirmPayment: <T = WsPayload>(jobId: string, payload: Record<string, unknown>) =>
    apiFetch<T>(`/v1/tenant/home-services/bookings-jobs/${jobId}/confirm-payment`, post(payload)),
};

// ── Dispatch ───────────────────────────────────────────────────────────────
export type HsDispatchProjection = WsPayload;
export type HsDispatchJobSummary = WsPayload;
export type HsAssignmentOptions = WsPayload;
export type HsAssignmentOptionTechnician = WsPayload;

/**
 * Deliberately built on `/v1/provider/service-jobs/*`, NOT `/v1/dispatch/*`.
 *
 * The `/v1/dispatch/*` engine reads a `field_ops.Job` table that holds no
 * home-services rows, so those routes silently no-op for exactly the jobs
 * this page shows. `/v1/provider/service-jobs/*` is the live pipeline.
 */
export const homeServicesDispatchApi = {
  /**
   * Real bug fixed here: this pointed at `/v1/provider/service-jobs/
   * assignable`, a flat `{jobs, count}` list -- nothing like the
   * `{unassigned_jobs, scheduled_today, technicians, summary, ...}` shape
   * the Dispatch Board page actually renders, so the board crashed reading
   * `.length` off a field that endpoint never returned. The real, matching
   * projection (`HomeServiceDispatchProjectionService`, reading the SAME
   * live ServiceJob/ServiceBooking tables, not the dead field_ops.Job
   * table) was fully built at `GET /v1/tenant/home-services/dispatch` but
   * had no router mounted at all until this pass
   * (home_service_assignment/dispatch_router.py).
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getDispatchBoard: <T = HsDispatchProjection>(dateOrParams?: string | Record<string, any>) =>
    apiFetch<T>(`/v1/tenant/home-services/dispatch${query(
      typeof dateOrParams === "string" ? { date: dateOrParams } : dateOrParams,
    )}`),
  getAssignmentOptions: <T = HsAssignmentOptions>(jobId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/jobs/${jobId}/assignment-options`),
  /**
   * Assigning may also (re)schedule the visit in the same call, which is why the board
   * passes the chosen date and window through.
   *
   * Real bug fixed here: this sent `staff_id`, and both endpoints require
   * `staff_member_id` (AssignRequest / ReassignRequest). Every assign and reassign from
   * the Dispatch board answered 422 "One or more request fields failed validation" --
   * reproduced live against a real unassigned job before the change. The endpoint was
   * right; only the field name was wrong, which is why it looked like the board's assign
   * button did nothing.
   */
  assign: <T = WsPayload>(jobId: string, staffId: string, scheduledDate?: string, timeWindow?: string) =>
    apiFetch<T>(`/v1/provider/service-jobs/${jobId}/assign`, post({
      staff_member_id: staffId, scheduled_date: scheduledDate, scheduled_time_window: timeWindow,
    })),
  reassign: <T = WsPayload>(jobId: string, staffId: string, reason?: string) =>
    apiFetch<T>(`/v1/provider/service-jobs/${jobId}/reassign`, post({ staff_member_id: staffId, reason: reason ?? "" })),
  unassign: <T = WsPayload>(jobId: string, reason?: string) =>
    apiFetch<T>(`/v1/provider/service-jobs/${jobId}/cancel-assignment`, post({ reason: reason ?? "" })),
};

// ── Onboarding: setup overview, application status, documents, finance ─────
export type HomeServicesSetupOverview = WsPayload;
export type HomeServicesSetupSection = WsPayload;
export type HomeServicesLifecycleStage = WsPayload;
export type ApplicationStatus = WsPayload;
export type ApplicationStatusLifecycleStage = WsPayload;
export type ActivationGate = WsPayload;
export type BusinessProfileOverview = WsPayload;
export type BusinessProfileOptions = WsPayload;
export type VerificationDocumentsManifest = WsPayload;
export type VerificationRequirement = WsPayload;
export type FinanceReadinessManifest = WsPayload;
export type FinanceReadinessDirectPayment = WsPayload;

export const homeServicesSetupOverviewApi = {
  getOverview: <T = HomeServicesSetupOverview>() => apiFetch<T>("/v1/tenant/home-services/setup/overview"),
  /** Which setup step to send the tenant to next; the backend models this as
   * the ordered checklist items rather than a separate routing resource. */
  getRouting: <T = WsPayload>() => apiFetch<T>("/v1/tenant/home-services/setup/routing"),
  /** "Submit for review" re-runs the server-side readiness evaluation, which
   * is what advances the application when every gate passes. */
  submitForReview: <T = WsPayload>() => apiFetch<T>("/v1/tenant/home-services/setup/submit", post()),
};

export const tenantApplicationStatusApi = {
  get: <T = ApplicationStatus>() => apiFetch<T>("/v1/tenant/home-services/setup/application-status"),
};

/**
 * Correction to an earlier note here: real onboarding-document routes DO
 * exist under `/v1/tenant/home-services/setup/documents`. That router could
 * not even be imported (it referenced a `require_vertical_not_active` guard
 * that had never been written), so it was never mounted and its routes
 * 404'd. The guard now exists and these call the real endpoints.
 */
export const tenantDocumentsApi = {
  getRequirements: <T = VerificationDocumentsManifest>() => apiFetch<T>("/v1/tenant/home-services/setup/documents/requirements"),
  submitDocument: <T = WsPayload>(payload: Record<string, unknown>) =>
    apiFetch<T>("/v1/tenant/home-services/setup/documents", post(payload)),
  removeDocument: <T = WsPayload>(documentId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/setup/documents/${documentId}`, del()),
};

export const financeReadinessApi = {
  get: <T = FinanceReadinessManifest>() => apiFetch<T>("/v1/tenant/home-services/setup/finance"),
  /** Finance readiness is configuration on the tenant settings record. */
  save: <T = WsPayload>(payload: Record<string, unknown>) =>
    apiFetch<T>("/v1/tenant/home-services/setup/finance", { method: "PUT", body: JSON.stringify(payload) }),
};

// ── Booking window & availability exceptions ───────────────────────────────
export type BookingWindowSettings = WsPayload;
export type AvailabilityException = WsPayload;

export const bookingWindowApi = {
  get: <T = BookingWindowSettings>() => apiFetch<T>("/v1/provider/booking-window"),
  update: <T = BookingWindowSettings>(payload: Record<string, unknown>) =>
    apiFetch<T>("/v1/provider/booking-window", { method: "PUT", body: JSON.stringify(payload) }),
};

export const availabilityExceptionsApi = {
  /** Returns an `{ exceptions: [...] }` envelope, not a bare array. */
  list: <T = WsPayload>() => apiFetch<T>("/v1/provider/availability/exceptions"),
  create: <T = AvailabilityException>(payload: Record<string, unknown>) =>
    apiFetch<T>("/v1/provider/availability/exceptions", post(payload)),
  delete: <T = WsPayload>(exceptionId: string) =>
    apiFetch<T>(`/v1/provider/availability/exceptions/${exceptionId}`, del()),
};

// ── Workspace settings ─────────────────────────────────────────────────────
export type WorkspaceGeneralSettings = WsPayload;
export type WorkspaceSettingField = WsPayload;
export type WorkspaceTeamAccess = WsPayload;
export type WorkspaceActivity = WsPayload;

/**
 * Real bug fixed here: this previously pointed at `/v1/tenant/settings`,
 * `/v1/tenant/users` and `/v1/settings/audit-log` -- none of which exist.
 * The real backend is `WorkspaceSettingsService`
 * (app/engines/tenant_engine/workspace_settings_service.py):
 * get_general/update_general/get_team_access/get_activity, reading real
 * Tenant/TenantSettings/provider_availability_rules/platform_audit_logs
 * data with each field tagged TENANT_CONTROLLED/SERVICEOS_CONTROLLED/
 * ADMIN_POLICY -- it was fully written but had no router until this pass
 * (workspace_settings_router.py, mounted in app/main.py). Business hours
 * are read-only here on purpose -- editing them is the existing
 * /v1/provider/availability surface, not duplicated here.
 */
export const workspaceSettingsApi = {
  getGeneral: <T = WorkspaceGeneralSettings>() => apiFetch<T>("/v1/tenant/home-services/workspace-settings/general"),
  updateGeneral: <T = WorkspaceGeneralSettings>(payload: Record<string, unknown>, expectedVersion?: string | null) =>
    apiFetch<T>("/v1/tenant/home-services/workspace-settings/general",
      { method: "PUT", body: JSON.stringify({ payload, expected_version: expectedVersion ?? null }) }),
  getTeamAccess: <T = WorkspaceTeamAccess>() => apiFetch<T>("/v1/tenant/home-services/workspace-settings/team-access"),
  getActivity: <T = WorkspaceActivity>(limit = 30) => apiFetch<T>(`/v1/tenant/home-services/workspace-settings/activity?limit=${limit}`),
};

/** The job a complaint was raised against. The backend embeds it in the
 * complaint detail payload rather than exposing a separate resource, so
 * `available` is false when the complaint has no linked job. */
export type ComplaintJobContext = WsPayload;
