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
import { apiFetch, ServiceOSError } from "./api";

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
// These were `WsPayload` (= any), so nothing on the Complaints & Resolution
// Center was checked against the endpoint. Mirrors CustomerComplaint
// .to_provider_dict() plus the tenant router's own projections.

export interface ComplaintJobSnapshot {
  job_id: string;
  job_number: string;
  master_service_name: string | null;
  technician_name: string | null;
  status: string;
  assignment_status: string | null;
  scheduled_date: string | null;
}

export interface ComplaintQueueItem {
  id: string;
  complaint_number: string;
  customer_alias: string;
  complaint_type: string;
  requested_resolution: string | null;
  priority: string;
  status: string;
  title: string | null;
  description: string;
  severity: string;
  sla_status: string;
  tenant_first_response_due_at: string | null;
  settlement_status: string | null;
  created_at: string | null;
  updated_at: string | null;
  job_number: string | null;
  master_service_name: string | null;
  /** Real tenant capabilities: "SEND_MESSAGE" | "OFFER_RESOLUTION". */
  available_actions: string[];
}

export interface ComplaintDetail extends ComplaintQueueItem {
  job: ComplaintJobSnapshot | null;
  /** Why a resolution cannot be proposed yet, when it cannot. */
  action_blocked_reason?: string | null;
}

export interface ComplaintQueueSummary {
  total: number; open: number; at_risk: number;
  breached: number; escalated: number; critical: number;
  awaiting_response: number; resolved_this_month: number;
}

export interface ComplaintQueueResponse {
  summary: ComplaintQueueSummary;
  complaints: ComplaintQueueItem[];
  available_filters: {
    status: string[];
    severity: string[];
    sla_state: string[];
    complaint_type: string[];
    services: { id: string; name: string }[];
  };
  pagination: { cursor: number; limit: number; total: number; has_next: boolean };
  generated_at: string | null;
}

export interface ComplaintListParams {
  search?: string;
  status?: string;
  severity?: string;
  sla_state?: string;
  service_id?: string;
  complaint_type?: string;
  cursor?: number;
  limit?: number;
}

export const tenantComplaintsApi = {
  list: <T = ComplaintQueueResponse>(params?: ComplaintListParams) =>
    apiFetch<T>(`/v1/tenant/home-services/complaints${query(params as Record<string, string | number | boolean | undefined>)}`),
  detail: <T = ComplaintDetail>(complaintId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/complaints/${complaintId}`),
  activity: <T = WsPayload>(complaintId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/complaints/${complaintId}/activity`),
  jobContext: <T = WsPayload>(complaintId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/complaints/${complaintId}/job-context`),
  /** Case evidence (photos/documents). `ComplaintService.list_media` existed
   *  but no router exposed it, so the Evidence tab had nothing to call. */
  evidence: <T = { items: ComplaintMediaItem[] }>(complaintId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/complaints/${complaintId}/evidence`),

  // Conversation + resolution reuse the existing, already-secured provider
  // endpoints (same pattern the reviews workspace uses for its mutations)
  // rather than duplicating the state-machine logic on a second router.
  messages: <T = ComplaintMessageItem[]>(complaintId: string) =>
    apiFetch<T>(`/v1/provider/complaints/${complaintId}/messages`),
  respond: <T = WsPayload>(complaintId: string, messageText: string) =>
    apiFetch<T>(`/v1/provider/complaints/${complaintId}/respond`, post({ message_text: messageText })),
  resolutions: <T = ComplaintResolutionItem[]>(complaintId: string) =>
    apiFetch<T>(`/v1/provider/complaints/${complaintId}/resolutions`),
  offerResolution: <T = WsPayload>(
    complaintId: string,
    body: { resolution_type: string; description: string; customer_visible_notes?: string },
  ) => apiFetch<T>(`/v1/provider/complaints/${complaintId}/offer-resolution`, post(body)),
};

export interface ComplaintMessageItem {
  id: string;
  sender_type: string;
  message_text: string;
  created_at: string | null;
}
export interface ComplaintMediaItem {
  id: string;
  uploaded_by_type: string;
  media_type: string;
  file_url: string;
  file_name: string | null;
  mime_type: string | null;
  file_size: number | null;
  caption: string | null;
  created_at: string | null;
}
export interface ComplaintResolutionItem {
  id: string;
  status: string;
  resolution_type: string;
  description: string;
  customer_visible_notes: string | null;
  created_at: string | null;
}

// ── Customers ──────────────────────────────────────────────────────────────
export interface HsCustomerListItem {
  customer_id: string;
  alias: string;
  is_active: boolean;
  repeat_status: "repeat" | "one_time" | "none";
  completed_jobs: number;
  cancelled_jobs: number;
  services_used_count: number;
  open_complaints: number;
  first_booking_at: string | null;
  last_activity_at: string | null;
  payment_reliability: "reliable" | "needs_review" | "insufficient_data";
}
export interface HsCustomerSummary {
  total_customers: number;
  active_customers: number;
  inactive_customers: number;
  new_customers: number;
  repeat_customers: number;
  one_time_customers: number;
  returning_rate: number;
  multi_service_customers: number;
  completed_job_customers: number;
  average_completed_jobs: number;
  confirmed_job_value: string;
  open_complaints: number;
  payment_review: number;
  payment_review_available: boolean;
  active_window_days: number;
  new_customer_window_days: number;
}
export interface HsCustomerDetail {
  customer_id: string;
  alias: string;
  is_active: boolean;
  repeat_status: "repeat" | "one_time" | "none";
  completed_jobs: number;
  cancelled_jobs: number;
  first_booking_at: string | null;
  last_activity_at: string | null;
  confirmed_job_value: string;
  open_complaints: number;
  services_used_by_master_service: Array<{
    offering_id: string;
    master_service_name: string | null;
    completed_jobs: number;
  }>;
  payment_reliability: "reliable" | "needs_review" | "insufficient_data";
  payment_decisions: number;
  payment_records_needing_review: number;
}
export interface HsCustomerListResponse {
  items: HsCustomerListItem[];
  total: number;
  page: number;
  page_size: number;
}
export interface HsCustomerListParams {
  q?: string;
  activity?: "active" | "inactive";
  repeat_status?: "repeat" | "one_time" | "none";
  payment_reliability?: "reliable" | "needs_review" | "insufficient_data";
  complaint_state?: "open" | "clear";
  sort?: "last_activity_desc" | "last_activity_asc" | "completed_desc" | "complaints_desc" | "first_booking_desc";
  page?: number;
  page_size?: number;
}
export interface HsCustomerFeed<T = WsPayload> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  note?: string;
}

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
  list: <T = HsCustomerListResponse>(params?: HsCustomerListParams) =>
    apiFetch<T>(`/v1/tenant/home-services/customers${query(params as Record<string, string | number | boolean | undefined>)}`),
  detail: <T = HsCustomerDetail>(customerId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}`),
  jobs: <T = HsCustomerFeed>(customerId: string, params?: { page?: number; page_size?: number }) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}/jobs${query(params)}`),
  complaints: <T = HsCustomerFeed>(customerId: string, params?: { page?: number; page_size?: number }) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}/complaints${query(params)}`),
  payments: <T = HsCustomerFeed>(customerId: string, params?: { page?: number; page_size?: number }) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}/payments${query(params)}`),
  reviews: <T = HsCustomerFeed>(customerId: string, params?: { page?: number; page_size?: number }) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}/reviews${query(params)}`),
  activity: <T = HsCustomerFeed>(customerId: string, params?: { page?: number; page_size?: number }) =>
    apiFetch<T>(`/v1/tenant/home-services/customers/${customerId}/activity${query(params)}`),
};

// ── Reviews ────────────────────────────────────────────────────────────────
// These were `WsPayload` (= any), so nothing on the Reviews & Service Quality
// page was type-checked against the endpoint at all -- a renamed or missing
// field compiled cleanly and failed only in the browser. Mirrors
// hs_quality_service.py exactly.

export interface HsReviewListItem {
  review_id: string;
  review_number: string;
  customer_alias: string;
  rating: number;
  review_excerpt: string;
  job_id: string;
  job_number: string;
  service_name: string;
  technician_name: string | null;
  reply_status: "answered" | "unanswered";
  /** Publication state of the review itself: pending until approved. */
  review_status: string;
  complaint_linked: boolean;
  complaint_number: string | null;
  moderation_status: string | null;
  created_at: string | null;
}

export interface HsReviewSummary {
  reviews: number;
  average_rating: number | null;
  response_rate: number;
  low_ratings: number;
  unanswered: number;
  flagged: number;
}

export interface HsReviewFilterOptions {
  technicians: { id: string; name: string }[];
  services: { id: string; name: string }[];
  moderation_statuses: string[];
}

export interface HsReviewsListResponse {
  reviews: HsReviewListItem[];
  total: number;
  limit: number;
  offset: number;
  summary: HsReviewSummary | null;
  rating_trend: { date: string; average_rating: number; review_count: number }[];
  rating_distribution: { stars: number; count: number; percent: number }[];
  quality_signals: {
    sla_met_percent: number | null;
    rework_rate_percent: number | null;
    complaint_after_completion_percent: number | null;
    sample_size: number;
  } | null;
  available_filters: HsReviewFilterOptions;
  /** Modules whose query failed server-side; render those panels as unavailable. */
  failed_modules: string[];
  generated_at: string | null;
}

export interface HsReviewDetail {
  review_id: string;
  review_number: string;
  customer_alias: string;
  rating: number;
  title: string | null;
  review_text: string | null;
  review_status: string;
  created_at: string | null;
  job: {
    job_id: string; job_number: string; status: string | null;
    city: string | null; zipcode: string | null;
    completion_data: unknown; service_name: string;
  };
  technician: { id: string; name: string | null } | null;
  reply: { reply_id: string; reply_text: string; status: string; created_at: string | null } | null;
  complaint: {
    complaint_id: string; complaint_number: string; status: string;
    severity: string | null; sla_status: string | null;
  } | null;
  invoice: { invoice_number: string; payment_status: string | null } | null;
  moderation: {
    flag_id: string; status: string; reason_code: string | null;
    reason_text: string | null; created_at: string | null;
  } | null;
  activity: { event_type: string; actor_type: string | null; reason: string | null; occurred_at: string | null }[];
  /** Server-authoritative: drives which action controls are offered. */
  available_actions: string[];
}

export interface HsReviewListParams {
  rating?: number;
  rating_max?: number;
  reply_status?: string;
  technician_id?: string;
  offering_id?: string;
  complaint_linked?: boolean;
  moderation_status?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export const hsReviewsApi = {
  list: <T = HsReviewsListResponse>(params?: HsReviewListParams) =>
    apiFetch<T>(`/v1/tenant/home-services/reviews${query(params as Record<string, string | number | boolean | undefined>)}`),
  get: <T = HsReviewDetail>(reviewId: string) => apiFetch<T>(`/v1/tenant/home-services/reviews/${reviewId}`),
  /**
   * Publishing a provider reply NEVER worked from this portal. The field was
   * sent as `body`, but ProviderReplyRequest declares `reply_text` and sets
   * `extra="forbid"` -- so every attempt failed validation twice over
   * ("reply_text: Field required" plus "body: Extra inputs are not
   * permitted") and came back 422. Verified against the live endpoint.
   */
  reply: <T = WsPayload>(reviewId: string, replyText: string) =>
    apiFetch<T>(`/v1/provider/reviews/${reviewId}/reply`, post({ reply_text: replyText })),
  /** A provider cannot moderate a review directly -- they FLAG it and admin
   * moderates. Naming it "requestModeration" on the page is accurate.
   *
   * Same defect as `reply` above: ReviewFlagRequest takes
   * `reason_code`/`reason_text` and forbids extras, but this sent
   * `reason`/`explanation`, so requesting moderation always 422'd. */
  requestModeration: <T = WsPayload>(reviewId: string, reasonCode: string, reasonText?: string) =>
    apiFetch<T>(`/v1/provider/reviews/${reviewId}/flag`, post({ reason_code: reasonCode, reason_text: reasonText ?? null })),
};

// ── Team ───────────────────────────────────────────────────────────────────
export interface TeamDirectoryStaffRow {
  staff_id: string; user_id: string | null; name: string; photo: string | null;
  role: string; employment_status: string; verification_status: string;
  availability_status: string; on_leave: boolean; readiness: string;
  readiness_missing: string[]; jobs_today: number; capacity_used: number;
  capacity_limit: number; capacity_percentage: number;
  capacity_state: "ready" | "at_risk" | "incomplete"; conflict_count: number;
  available_actions: string[]; version: string | null;
}
export interface TeamDirectoryResponse {
  summary: { total_team: number; active: number; technicians: number; available_now: number; setup_incomplete: number; schedule_conflicts: number };
  staff: TeamDirectoryStaffRow[];
  pagination: { cursor: number; limit: number; next_cursor: number | null; previous_cursor: number | null; total: number };
  available_filters: { role: string[]; status: string[]; availability: string[]; readiness: string[] };
  generated_at: string;
}
export type StaffOverview = WsPayload;
export type StaffCapabilities = WsPayload;
export interface StaffAvailabilityWorkspace {
  staff_id: string; presence: string; presence_updated_at: string | null;
  can_receive_assignment: boolean; weekly_rules: WsPayload[]; time_off: WsPayload[]; overrides: WsPayload[];
}
export interface StaffJobsWorkspace {
  items: WsPayload[]; pagination: { total: number; cursor: number; limit: number; next_cursor: number | null; previous_cursor: number | null };
  available_statuses: string[];
}
export interface StaffPerformanceWorkspace {
  staff_id: string; total_jobs: number; completed_jobs: number; cancelled_jobs: number;
  completed_last_30_days: number; emergency_jobs: number; completion_rate: number;
  last_completed_at: string | null; ratings: WsPayload;
}
export interface StaffDocumentsWorkspace { items: WsPayload[]; pagination: WsPayload }
export interface StaffActivityWorkspace { items: WsPayload[]; pagination: WsPayload }
export type TeamReadinessSummary = WsPayload;

export const homeServicesTeamApi = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  list: <T = TeamDirectoryResponse>(params?: Record<string, any>) => apiFetch<T>(`/v1/tenant/home-services/team${query(params)}`),
  overview: <T = StaffOverview>(staffId: string) => apiFetch<T>(`/v1/tenant/home-services/team/${staffId}/overview`),
  /** Capability = which offerings this member is allowed to be dispatched
   * for; the backend models it as the member record's skills/offerings. */
  capabilities: <T = StaffCapabilities>(staffId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/team/${staffId}/capabilities`),
  availability: <T = StaffAvailabilityWorkspace>(staffId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/team/${staffId}/availability`),
  jobs: <T = StaffJobsWorkspace>(staffId: string, params?: Record<string, string | number | undefined>) =>
    apiFetch<T>(`/v1/tenant/home-services/team/${staffId}/jobs${query(params)}`),
  performance: <T = StaffPerformanceWorkspace>(staffId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/team/${staffId}/performance`),
  documents: <T = StaffDocumentsWorkspace>(staffId: string, params?: Record<string, string | number | undefined>) =>
    apiFetch<T>(`/v1/tenant/home-services/team/${staffId}/documents${query(params)}`),
  activity: <T = StaffActivityWorkspace>(staffId: string, params?: Record<string, string | number | undefined>) =>
    apiFetch<T>(`/v1/tenant/home-services/team/${staffId}/activity${query(params)}`),
};

// ── Services workspace ─────────────────────────────────────────────────────
export interface SWCatalogService {
  tenant_service_id: string;
  master_service_id: string;
  name: string;
  job_type_label: string | null;
  job_type?: string | null;
  setup_status: "draft" | "published";
  missing_pricing: boolean;
  readiness_ready: boolean;
  blocker_count: number;
  customer_visible: boolean;
  pricing_behavior: string | null;
  tenant_min_price: number | null;
  tenant_max_price: number | null;
  tenant_visit_fee: number | null;
}
export interface SWCatalogGroup {
  service_group_id: string;
  name: string;
  services: SWCatalogService[];
}
export interface SWResolvedPrice {
  resolved: boolean;
  minimum_price?: number;
  maximum_price?: number;
  source?: string;
  reason?: string;
}
export interface SWOfferingDetail {
  tenant_service: WsPayload;
  service_name: string;
  service_group_name: string | null;
  job_type_label: string | null;
  blueprint: {
    type_mode: "required" | "optional";
    brand_mode: "required" | "optional";
    pricing_behavior?: string;
    requires_issue_type: boolean;
    requires_checklist: boolean;
    requires_estimate_approval: boolean;
    requires_technician: boolean;
    requires_schedule: boolean;
    requires_service_area?: boolean;
    requires_availability?: boolean;
    workflow_version: number | null;
    source: "service_job_workflow" | "master_service_legacy";
  };
  readiness: { ready: boolean; status: string; blockers: Array<{
    code: string; message: string; step?: string; job_type_id?: string;
    dimension_path?: Record<string, string>;
  }> };
  types: Array<{ service_type_id: string; name: string }>;
  brands: Array<{ brand_id: string; name: string }>;
  effective_pricing: {
    default: SWResolvedPrice;
    by_type: Array<SWResolvedPrice & {
      service_type_id: string;
      name: string;
      brand_overrides: Array<SWResolvedPrice & { brand_id: string }>;
    }>;
  };
}
export interface SWWorkspace {
  summary: {
    enabled_services: number;
    published: number;
    draft: number;
    missing_pricing: number;
    type_overrides: number;
    brand_overrides: number;
  };
  catalog_tree: SWCatalogGroup[];
  generated_at: string;
}
export type HsSetupAvailableType = WsPayload;

export const servicesWorkspaceApi = {
  get: <T = SWWorkspace>(params?: Record<string, string | number | boolean | undefined>) =>
    apiFetch<T>(`/v1/tenant/home-services/services${query(params)}`),
  detail: <T = SWOfferingDetail>(tenantServiceId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/services/${tenantServiceId}`),
};

// ── Bookings & Jobs ────────────────────────────────────────────────────────
export interface BJSla {
  sla_status: "ON_TRACK" | "AT_RISK" | "BREACHED" | "NOT_APPLICABLE";
  next_deadline: string | null;
  minutes_remaining: number | null;
  minutes_overdue: number | null;
  breach_stage: string | null;
  source_policy: string | null;
}
export interface BJAction { action_key: string; label: string; endpoint?: string }
export interface BJItem {
  booking_id: string; booking_number: string;
  service_job_id: string; job_number: string;
  offering_id: string; service_name: string | null;
  job_type_id: string | null; job_type_label: string | null;
  customer_id: string | null; customer_alias: string | null;
  locality: string | null; city: string | null; zipcode: string | null;
  scheduled_date: string | null; scheduled_time_window: string | null;
  assigned_staff_id: string | null; assigned_staff_name: string | null;
  assignment_status: string; status: string; stage: string; stage_label: string;
  is_active: boolean; is_terminal: boolean; next_action: BJAction | null;
  available_actions: BJAction[]; sla: BJSla | null;
  open_complaint_count: number; created_at: string | null; updated_at: string | null;
}
export interface BJListResponse {
  items: BJItem[]; total: number; limit: number; offset: number;
  summary: {
    total_active: number; unassigned: number; in_progress: number;
    awaiting_approval: number; at_risk: number; completed_today: number;
  };
  available_filters: {
    services: Array<{ offering_id: string; name: string }>;
    technicians: Array<{ staff_member_id: string; name: string }>;
    job_types: Array<{ job_type_id: string; label: string }>;
  };
  generated_at: string;
}
export interface BJDetail {
  booking: Record<string, unknown> & { customer_alias?: string; locality?: string };
  job: Record<string, unknown> & {
    id: string; job_number: string; scheduled_date?: string | null;
    scheduled_time_window?: string | null;
  };
  service_name: string | null; job_type_label: string | null;
  stage: { stage: string; stage_label: string; is_terminal: boolean; next_action: BJAction | null };
  available_actions: BJAction[];
  invoice: (Record<string, unknown> & { customer_payable_amount?: number; payment_status?: string }) | null;
  quote: (Record<string, unknown> & { customer_payable_amount?: number; status?: string }) | null;
  visit_fee: string | null; open_complaint_count: number; sla: BJSla;
  workflow_stages: Array<{
    step_key: string; label: string; state: "completed" | "current" | "skipped" | "upcoming";
    requires_photo?: boolean; requires_note?: boolean;
  }>;
  direct_payment_notice: string;
}
export interface BJAddress {
  granted: boolean; reason_code: string; locality?: string;
  access_expiry?: string | null; address_snapshot?: Record<string, unknown> | string | null;
  city?: string | null; zipcode?: string | null;
}

export const bookingsJobsApi = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  list: <T = BJListResponse>(params?: Record<string, any>) =>
    apiFetch<T>(`/v1/tenant/home-services/bookings-jobs${query(params)}`),
  detail: <T = BJDetail>(jobId: string) => apiFetch<T>(`/v1/tenant/home-services/bookings-jobs/${jobId}`),
  address: <T = BJAddress>(jobId: string) => apiFetch<T>(`/v1/tenant/home-services/bookings-jobs/${jobId}/address`),
  /** Confirming payment on a job is a direct-payment declaration -- that is
   * the only money-in action a provider can take against a job. */
  confirmPayment: <T = WsPayload>(jobId: string, payload: Record<string, unknown>) =>
    apiFetch<T>(`/v1/tenant/home-services/bookings-jobs/${jobId}/confirm-payment`, post(payload)),
};

// ── Dispatch ───────────────────────────────────────────────────────────────
export interface HsDispatchJobSummary {
  job_id: string;
  job_number: string;
  booking_id: string;
  booking_number?: string | null;
  status: string;
  assignment_status: string;
  assigned_staff_id?: string | null;
  assigned_staff_name?: string | null;
  assignment_id?: string | null;
  requested_at?: string | null;
  scheduled_date?: string | null;
  scheduled_time_window?: string | null;
  requested_date?: string | null;
  requested_time_window?: string | null;
  customer_alias?: string | null;
  customer_address?: string | null;
  locality?: string | null;
  city?: string | null;
  zipcode?: string | null;
  issue_summary?: string | null;
  master_service_name?: string | null;
  service_icon_url?: string | null;
  is_emergency?: boolean;
  service_due_at?: string | null;
  minutes_until_due?: number | null;
  is_overdue?: boolean;
  has_conflict?: boolean;
}

export interface HsDispatchTechnician {
  staff_member_id: string;
  name: string;
  status: string;
  profile_photo_url?: string | null;
  capacity_used?: number;
  capacity_limit?: number;
  jobs_in_range: HsDispatchJobSummary[];
  jobs_today?: HsDispatchJobSummary[];
}

export interface HsDispatchProjection {
  summary: {
    unassigned_count: number;
    scheduled_count: number;
    on_the_way_count: number;
    capacity_used: number;
    capacity_total: number;
    conflict_count: number;
  };
  unassigned_jobs: HsDispatchJobSummary[];
  scheduled_jobs: HsDispatchJobSummary[];
  technician_schedule: HsDispatchTechnician[];
  conflicts: number;
  available_actions: string[];
  pagination: { total: number; limit: number; offset: number };
  filters: {
    services: Array<{ id: string; name: string }>;
    technicians: Array<{ staff_member_id: string; name: string; status: string }>;
  };
  view: "day" | "week";
  range_start: string;
  range_end: string;
  schedule_truncated: boolean;
  generated_at: string;
}

export interface HsAssignmentOptionTechnician {
  staff_member_id: string;
  name: string;
  role: string;
  status: string;
  profile_photo_url?: string | null;
  eligibility_status: "eligible" | "blocked";
  warnings?: string[];
  match_reasons?: string[];
  blocked_reasons?: string[];
  exclusion_reason_codes?: string[];
}

export interface HsAssignmentOptions {
  job_context: HsDispatchJobSummary;
  eligible_technicians: HsAssignmentOptionTechnician[];
  excluded_technicians: HsAssignmentOptionTechnician[];
  current_assignment: ({
    id: string;
    assigned_staff_member_id: string;
    assignment_status: string;
    staff_name?: string | null;
    profile_photo_url?: string | null;
  } & Record<string, unknown>) | null;
  available_actions: string[];
  version?: string | null;
}

interface HsDispatchMutationResponse {
  success: boolean;
  data?: Record<string, unknown>;
  error?: { code?: string; message?: string };
  error_code?: string;
  message?: string;
}

function requireDispatchMutationSuccess(response: HsDispatchMutationResponse) {
  if (!response.success) {
    throw new ServiceOSError(
      response.error?.code ?? response.error_code ?? "DISPATCH_ACTION_FAILED",
      response.error?.message ?? response.message ?? "The dispatch action could not be completed.",
    );
  }
  return response;
}

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
    apiFetch<HsDispatchMutationResponse>(`/v1/provider/service-jobs/${jobId}/assign`, post({
      staff_member_id: staffId, scheduled_date: scheduledDate, scheduled_time_window: timeWindow,
    })).then(requireDispatchMutationSuccess) as Promise<T>,
  reassign: <T = WsPayload>(jobId: string, staffId: string, reason?: string) =>
    apiFetch<HsDispatchMutationResponse>(`/v1/provider/service-jobs/${jobId}/reassign`, post({ staff_member_id: staffId, reason: reason ?? "" }))
      .then(requireDispatchMutationSuccess) as Promise<T>,
  unassign: <T = WsPayload>(jobId: string, reason?: string) =>
    apiFetch<HsDispatchMutationResponse>(`/v1/provider/service-jobs/${jobId}/cancel-assignment`, post({ reason: reason ?? "" }))
      .then(requireDispatchMutationSuccess) as Promise<T>,
};

// ── Onboarding: setup overview, application status, documents, finance ─────
export interface HomeServicesSetupSection {
  key: string;
  label: string;
  description: string;
  required: boolean;
  status: "not_started" | "complete" | "optional" | "blocked" | "locked" | "ready";
  locked?: boolean;
  percentage?: number;
  configured_count?: number;
  enabled_count?: number;
  prerequisite?: { key: string; label: string; route: string } | null;
  blocking_reasons: Array<{ code: string; message: string }>;
  warnings: Array<{ code: string; message: string }>;
  next_action: string;
  [key: string]: unknown;
}
export interface HomeServicesLifecycleStage {
  key: string;
  status: "COMPLETED" | "CURRENT" | "UPCOMING";
}
export interface HomeServicesSetupOverview {
  tenant: { id: string; name: string | null };
  vertical: { key: string; status: string; rejection_reason?: string | null; changes_requested_note?: string | null; suspend_reason?: string | null };
  lifecycle: { current_stage: string; stages: HomeServicesLifecycleStage[] };
  declarations: { all_accepted: boolean; items: DeclarationItem[] };
  blocker_count: number;
  warning_count: number;
  sections_ready: boolean;
  can_submit: boolean;
  progress: { percentage: number; completed_required: number; total_required: number; calculation_version: string };
  sections: HomeServicesSetupSection[];
  workspace_status: { owner_account_verified: boolean; business_profile_status: string; home_services_status: string; admin_review_status: string };
  next_action: { key: string };
}
export interface DeclarationItem {
  key: string;
  accepted: boolean;
}
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

/** Permanent post-activation verification workspace backed by the same
 * TenantDocument records used during onboarding. */
export const tenantVerificationDocumentsApi = {
  workspace: <T = WsPayload>() => apiFetch<T>("/v1/tenant/documents/workspace"),
  business: <T = WsPayload>() => apiFetch<T>("/v1/tenant/documents/business"),
  versions: <T = WsPayload>(docType: string) =>
    apiFetch<T>(`/v1/tenant/documents/versions/${encodeURIComponent(docType)}`),
  submit: <T = WsPayload>(payload: Record<string, unknown>) =>
    apiFetch<T>("/v1/tenant/documents", post(payload)),
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
