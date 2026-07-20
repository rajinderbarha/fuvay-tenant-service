/**
 * DESIGN PHASE UX-05 — Staff/Technician mobile app shared view-model types.
 *
 * These EXTEND the real API shapes in `src/lib/api.ts` (StaffUser, Job,
 * JobAssignment, BookingSummary, ChatThread, StaffNotification) rather than
 * redefining them — UX-05 adds mobile-workspace presentation concerns
 * (readiness, offline state, permission presentation, provenance) on top.
 *
 * REAL-EVIDENCE CORRECTION (found during Step 0 discovery, overrides the
 * UX-05 brief's illustrative example): this app's job surface is ALREADY
 * single-pipeline. MODULE-L5-36 (see src/lib/api.ts comments) confirmed
 * field_ops' `jobs` table has ZERO rows platform-wide and rewired the whole
 * mobile job surface to `service_jobs` (home_service_assignment + execution
 * engines). There is no live field_ops.Job data for this app to present, so
 * this file does NOT model a dual booking_field_ops / service_booking_
 * service_job pipeline split the way UX-04's web types.ts does for the
 * tenant-portal operations console. `Job` here is always the ServiceJob-
 * family job from `jobsApi`. `pipeline` is still carried on every job view
 * (fixed literal "service_booking_service_job") so a future field_ops
 * revival cannot silently get merged into this type without a compile
 * error at every call site — see docs/design/ux-05-staff-technician-app/
 * pipeline-aware-job-detail.md for the full writeup.
 *
 * Real status literals (verified against src/lib/transitions.ts, itself
 * sourced from app/engines/execution/constants.py per its own comment):
 *   pending_assignment, assigned, accepted, scheduled, on_the_way,
 *   reached_site, inspection_started, inspection_done, quote_required,
 *   service_started, work_done, customer_not_available, completed,
 *   cancelled, failed
 * These are the ONLY status values used anywhere below. No invented state
 * (no "paused"/"waiting_payment"/"closed"/"reopened"/"arrived").
 *
 * Canonical roles: "staff" | "technician" ONLY. Never invent aliases.
 */
import type {
  Job, JobAssignment, BookingSummary, JobDetail, StaffUser,
  ChatThread, StaffNotification, StaffPerformance, ExecutionEvent,
} from "../lib/api";
import type { JobAction } from "../lib/transitions";

// ---------------------------------------------------------------------------
// Shared vocabulary
// ---------------------------------------------------------------------------

export type ReadinessState =
  | "production_ready" | "read_only_ready" | "mock_design_only"
  | "api_contract_required" | "security_contract_pending"
  | "product_decision_required" | "deprecated" | "not_applicable";

/** Dev-only metadata attached to every actionable surface. Never rendered
 * to real users -- gated behind a __DEV__ / showcase-only presentation. */
export interface ActionReadinessView {
  actionKey: string;       // e.g. "service_job:accept", "parts_request:approve"
  readiness: ReadinessState;
  note: string;
}

export type CanonicalMobileRole = "staff" | "technician";

/** StaffPermission is authoritative on the backend; this is a PRESENTATION
 * of an already-decided grant, never itself an authorization boundary. */
export interface StaffPermissionView {
  permissionKey: string;   // e.g. "parts_request:approve", "finance:view_job_amount"
  granted: boolean;
  explicitDeny: boolean;   // explicit deny overrides any broader grant
  scopeTenantId: string;
  reason: string | null;
}

export interface MobilePrincipalView {
  meta: { readiness: ReadinessState; sourceAdapter: string };
  user: StaffUser;
  role: CanonicalMobileRole;   // derived from StaffUser + StaffPermission set, never hardcoded
  designation: string | null;  // descriptive display text only (e.g. "Senior AC Technician") -- NEVER authorization
  permissions: StaffPermissionView[];
  tenantId: string | null;
  crossTenantIsolated: boolean;
}

// ---------------------------------------------------------------------------
// Job provenance + pipeline identity
// ---------------------------------------------------------------------------

/** Every job view keeps this even though only one pipeline is live today --
 * see file header. `bookingId` / `jobId` are always distinct real fields,
 * never collapsed into one "id". */
export interface JobProvenanceView {
  pipeline: "service_booking_service_job";
  sourceBookingId: string;
  jobId: string;
  jobModel: "ServiceJob";
}

export interface SLAStateView {
  state: "on_track" | "approaching_deadline" | "at_risk" | "breached" | "unknown";
  label: string;
  scheduledFor: string | null;
}

export interface ActionPermissionView {
  action: JobAction;
  label: string;
  available: boolean;
  reason: string | null;
  offlineAllowed: false; // status transitions are always online-required -- see offline-operation-matrix.csv
}

// ---------------------------------------------------------------------------
// Home
// ---------------------------------------------------------------------------

export interface TechnicianHomeView {
  meta: { readiness: ReadinessState; sourceAdapter: string; lastRefreshedAt: string };
  greetingName: string;
  currentJob: MyWorkItemView | null;
  todayCount: number;
  completedTodayCount: number;
  rating: number | null;
  upcomingToday: MyWorkItemView[];
  jobsNeedingAction: MyWorkItemView[];
  pendingPartsCount: number;
  unreadNotificationCount: number;
  availability: AvailabilityView | null;
}

export interface StaffWorkQueueSummary {
  unassignedCount: number;
  assignmentConflictCount: number;
  quoteReviewCount: number;
  checklistReviewCount: number;
  partsApprovalCount: number;
  customerIssueCount: number;
  slaRiskCount: number;
}

export interface StaffHomeView {
  meta: { readiness: ReadinessState; sourceAdapter: string; lastRefreshedAt: string };
  greetingName: string;
  queueSummary: StaffWorkQueueSummary;
  actionQueue: WorkQueueItemView[];
  financeAlerts: FinanceAlertView[]; // empty unless a real finance StaffPermission is granted
  permissions: StaffPermissionView[];
}

export interface FinanceAlertView {
  meta: { readiness: ReadinessState };
  label: string;
  requiredPermission: string;
  visible: boolean; // false unless permission granted -- component must still not render the row when false
}

// ---------------------------------------------------------------------------
// My Work (technician) / Work Queue (staff)
// ---------------------------------------------------------------------------

export type MyWorkGroup = "current" | "today" | "upcoming" | "needs_action" | "completed";

export interface MyWorkItemView {
  meta: { readiness: ReadinessState; sourceAdapter: string };
  provenance: JobProvenanceView;
  job: Job;
  group: MyWorkGroup;
  sla: SLAStateView;
  primaryAction: ActionPermissionView | null;
  partsState: "none" | "requested" | "under_review" | "approved" | "rejected" | "installed";
  checklistState: "not_started" | "in_progress" | "complete" | "not_applicable";
  offlineCached: boolean;
}

export type WorkQueueGroup =
  | "unassigned" | "assignment_conflict" | "quote_review" | "checklist_review"
  | "parts_approval" | "customer_issue" | "sla_risk" | "work_done_awaiting_completion";

export interface WorkQueueItemView {
  meta: { readiness: ReadinessState; sourceAdapter: string };
  provenance: JobProvenanceView;
  group: WorkQueueGroup;
  priority: "low" | "medium" | "high" | "urgent";
  booking: BookingSummary | null;
  job: Job;
  technicianName: string | null;
  ageHours: number;
  sla: SLAStateView;
  requiredAction: string;
  permission: StaffPermissionView;
}

// ---------------------------------------------------------------------------
// Schedule
// ---------------------------------------------------------------------------

export interface ScheduleItemView {
  meta: { readiness: ReadinessState };
  provenance: JobProvenanceView;
  job: Job;
  timeWindow: string | null;
  status: string;
  hasConflict: boolean;
}

// ---------------------------------------------------------------------------
// Job Detail
// ---------------------------------------------------------------------------

export interface CustomerContactView {
  meta: { readiness: ReadinessState };
  // MODULE-L5-36 evidence: neither Job nor the safe BookingSummary view
  // expose a customer phone number to staff -- do not invent one.
  name: string | null;
  city: string | null;
  zipcode: string | null;
  issueSummary: string | null;
  preferredDate: string | null;
  preferredTimeWindow: string | null;
  callSupported: boolean;   // false until a real contact-relay endpoint exists
  messageSupported: boolean; // true -- real chat thread exists (chatApi)
}

export interface StatusTransitionView {
  currentStatus: string;
  currentLabel: string;
  availableActions: ActionPermissionView[];
  requiresNote: boolean;
  requiresEvidence: boolean;
  terminal: boolean;
  offlineRestricted: true; // always -- see offline-operation-matrix.csv
}

export interface JobNoteView {
  meta: { readiness: ReadinessState };
  id: string;
  authorRole: CanonicalMobileRole | "system";
  visibility: "internal" | "technician" | "customer_visible";
  text: string;
  createdAt: string;
}

export interface JobMediaView {
  meta: { readiness: ReadinessState };
  id: string;
  localUri: string | null;      // pre-upload, device-local only
  uploadState: "draft" | "uploading" | "confirmed" | "failed";
  visibility: "internal" | "customer_visible";
  // never storage keys / signed URLs / bucket names / credentials
  confirmedByBackend: boolean;
}

export interface InspectionDraftView {
  meta: { readiness: ReadinessState };
  jobId: string;
  customerIssue: string;
  observations: string;
  recommendedWork: string;
  requiredParts: string[];
  photos: JobMediaView[];
  customerVisibleSummary: string;
  internalNote: string;
  status: "draft" | "saved" | "completed" | "read_only";
}

export interface ChecklistExecutionView {
  meta: { readiness: ReadinessState };
  jobId: string;
  sections: ChecklistSectionView[];
  progressPercent: number;
  status: "not_started" | "in_progress" | "complete" | "read_only";
}

export interface ChecklistSectionView {
  title: string;
  items: ChecklistItemView[];
}

export interface ChecklistItemView {
  id: string;
  label: string;
  required: boolean;
  responseType: "pass_fail" | "text" | "numeric" | "photo";
  value: string | null;
  photoAttached: boolean;
}

export interface QuoteSummaryView {
  meta: { readiness: ReadinessState };
  jobId: string;
  status: "draft" | "submitted_for_review" | "sent_to_customer" | "approved" | "rejected";
  lineItemsSummary: string;
  technicianCanEdit: boolean;  // never includes "approve"/"finalize_price"
  staffCanReview: boolean;
}

export interface JobDetailView {
  meta: { readiness: ReadinessState; sourceAdapter: string; lastRefreshedAt: string };
  provenance: JobProvenanceView;
  job: Job;
  assignment: JobAssignment | null;
  booking: BookingSummary | null;
  sla: SLAStateView;
  statusTransition: StatusTransitionView;
  customer: CustomerContactView;
  notes: JobNoteView[];
  media: JobMediaView[];
  inspection: InspectionDraftView | null;
  checklist: ChecklistExecutionView | null;
  quote: QuoteSummaryView | null;
  partsRequests: PartsRequestStatusView[];
  timeline: ExecutionEvent[];
  offlineCached: boolean;
}

// ---------------------------------------------------------------------------
// Parts requests -- ServiceJob-only, technician never approves/rejects/installs
// ---------------------------------------------------------------------------

export type PartsRequestState = "requested" | "under_review" | "approved" | "rejected" | "installed";

export interface PartsRequestDraftView {
  meta: { readiness: ReadinessState };
  jobId: string; // ServiceJob only -- never attachable to a field_ops job
  partName: string;
  description: string;
  quantity: number;
  estimatedCost: number | null;
  reason: string;
  urgency: "normal" | "urgent" | null;
  photo: JobMediaView | null;
  note: string;
}

export interface PartsRequestStatusView {
  meta: { readiness: ReadinessState };
  id: string;
  jobId: string;
  partName: string;
  quantity: number;
  requestedAt: string;
  note: string | null;
  providerResponse: string | null;
  state: PartsRequestState;
  // Technician-visible actions only -- never approve/reject/mark_installed/
  // link_field_ops/create_supplier_order.
  technicianActions: Array<"add_note">;
}

/** Staff-only. Never surfaced to technician role. */
export interface PartsApprovalQueueItemView {
  meta: { readiness: ReadinessState };
  partsRequest: PartsRequestStatusView;
  permission: StaffPermissionView; // parts_request:approve
  requiredReason: boolean;
}

// ---------------------------------------------------------------------------
// Notifications / availability / offline
// ---------------------------------------------------------------------------

export interface NotificationView {
  meta: { readiness: ReadinessState };
  notification: StaffNotification;
  priority: "low" | "medium" | "high";
}

export interface AvailabilityView {
  meta: { readiness: ReadinessState };
  workStatus: "available" | "busy" | "on_job" | "off_duty" | "unknown";
  accountStatus: string;      // distinct from workStatus -- StaffUser.status
  currentJobStatus: string | null; // distinct again -- current Job.status
}

export type OfflineOperationCategory =
  | "view_cached" | "draft_only" | "online_required";

export interface OfflineSyncStateView {
  meta: { readiness: ReadinessState };
  networkState: "online" | "slow" | "offline";
  cacheState: "fresh" | "stale_cached" | "empty";
  pendingDrafts: number;
  syncState: "idle" | "sync_pending" | "sync_failed" | "conflict_detected";
}

// ---------------------------------------------------------------------------
// Perf / profile
// ---------------------------------------------------------------------------

export interface ProfileView {
  meta: { readiness: ReadinessState };
  user: StaffUser;
  role: CanonicalMobileRole;
  designation: string | null;
  performance: StaffPerformance | null; // null = "no score computed yet" (real 404 state, not an error)
  availability: AvailabilityView;
}
