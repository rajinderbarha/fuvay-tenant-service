/**
 * DESIGN PHASE UX-04 — Tenant Operations shared view-model types.
 *
 * These types EXTEND the UX-03 fixture layer (lib/ux03/types.ts) — they do
 * NOT redefine BookingFixture/ServiceJobFixture/PartsRequestFixture/etc.
 * UX-04 adds operations-workspace concerns (SLA/risk state, action
 * availability, permission presentation, source adapter provenance) on top
 * of the UX-03 domain fixtures. Still design-phase: anything here is a UI
 * fixture/contract, not a live API response, until confirmed otherwise —
 * see docs/design/ux-04-tenant-operations/backend-contract-dependencies.csv.
 *
 * Hard rules preserved from UX-03 (do not violate in any view model below):
 * - Booking (-> field_ops.Job) and ServiceBooking (-> ServiceJob) are
 *   separate pipelines; every view model that wraps either keeps `pipeline`
 *   and `canonicalId` from the underlying fixture, never collapsed.
 * - PartsRequest is ServiceJob-only.
 * - Credit / commission / security deposit / on-site payment are four
 *   separate concepts, never combined into one balance or payout UI.
 * - Cancel/reschedule stays `"unresolved_mock_only"`.
 * - Only canonical roles: tenant_owner, staff, technician.
 */
import type {
  PipelineKind,
  BookingFixture,
  ServiceJobFixture,
  PartsRequestFixture,
  PackageCreditFixture,
  ComplaintFixture,
  ComplianceItemFixture,
  MediaAssetFixture,
  AuditEventFixture,
  CanonicalTenantRole,
  ReadinessState,
} from "../ux03/types";

/** Shared SLA/risk vocabulary — used by badges, timeline markers, list
 * filters, and dashboard alerts. Values are backend-provided or typed
 * fixture values only; no invented calculation rule is implied here. */
export type SLAState =
  | "on_track"
  | "approaching_deadline"
  | "at_risk"
  | "breached"
  | "blocked"
  | "waiting_on_customer"
  | "waiting_on_provider"
  | "waiting_on_platform"
  | "product_decision_blocked";

export interface SLAStateView {
  state: SLAState;
  label: string;
  deadlineAt: string | null;
  explanation: string;
}

/** Permission presentation for one action on one entity — drives whether an
 * action renders as available, disabled-with-reason, or hidden. Frontend
 * nav/action visibility is never itself an authorization boundary; this
 * only *presents* what the (fixture) permission model already decided. */
export interface ActionPermissionView {
  actionKey: string; // e.g. "field_ops:jobs:assign"
  available: boolean;
  reason: string | null; // shown when available=false
}

export interface EntityLinkView {
  kind: "booking" | "service_job" | "quote" | "checklist" | "parts_request" | "invoice" | "complaint" | "compliance_item" | "customer" | "technician";
  id: string;
  label: string;
  href: string;
}

/** Common envelope every operational view model carries so a screen never
 * has to guess provenance, readiness, or which adapter produced it. */
export interface OperationalViewMeta {
  readiness: ReadinessState;
  sourceAdapter: string; // e.g. "ux04BookingAdapter.getBookingDetail"
  lastRefreshedAt: string;
}

// ---------------------------------------------------------------------------
// Booking / Job list + detail views
// ---------------------------------------------------------------------------

export interface BookingListItemView {
  meta: OperationalViewMeta;
  booking: BookingFixture; // pipeline: "booking_field_ops"
  sla: SLAStateView;
  nextAction: string | null;
  actions: ActionPermissionView[];
}

export interface BookingDetailView {
  meta: OperationalViewMeta;
  booking: BookingFixture;
  sla: SLAStateView;
  timeline: AuditEventFixture[];
  jobTransition: BookingToJobTransitionView | null;
  actions: ActionPermissionView[];
}

/** Booking -> field_ops.Job (or ServiceBooking -> ServiceJob) transition
 * presentation. Read-only presentation of an already-decided transition —
 * this is not an active resolution engine. */
export interface BookingToJobTransitionView {
  sourcePipeline: PipelineKind;
  sourceBookingId: string;
  condition: "not_yet_transitioned" | "transitioned" | "duplicate_prevented" | "validation_failed";
  resultingModel: "field_ops.Job" | "ServiceJob" | null;
  resultingJobId: string | null;
  existingJobLink: EntityLinkView | null;
  validationNotes: string[];
}

export interface JobListItemView {
  meta: OperationalViewMeta;
  job: ServiceJobFixture; // pipeline: "service_booking_service_job"
  sla: SLAStateView;
  nextAction: string | null;
  actions: ActionPermissionView[];
}

export interface JobDetailView {
  meta: OperationalViewMeta;
  job: ServiceJobFixture;
  sla: SLAStateView;
  statusTransition: StatusTransitionView;
  assignment: AssignmentCandidateView[];
  quote: QuoteView | null;
  checklist: ChecklistView | null;
  partsRequests: PartsRequestView[];
  invoice: InvoiceView | null;
  creditCommission: CreditCommissionView;
  communication: CommunicationEventView[];
  media: MediaAssetFixture[];
  activity: AuditEventFixture[];
  actions: ActionPermissionView[];
}

// ---------------------------------------------------------------------------
// UX-04B: field_ops.Job detail (distinct from ServiceJob's JobDetailView —
// field_ops.Job has NO quote/checklist/parts/invoice/credit concept, so
// this view model deliberately does not carry those fields at all, rather
// than carrying them as always-null).
// ---------------------------------------------------------------------------

export interface FieldOpsJobDetailView {
  meta: OperationalViewMeta;
  job: BookingFixture; // pipeline: "booking_field_ops"; field_ops.Job canonicalId
  sla: SLAStateView;
  timeline: AuditEventFixture[];
  activity: AuditEventFixture[];
  notes: string[];
  actions: ActionPermissionView[];
}

// ---------------------------------------------------------------------------
// UX-04B: ServiceBooking provenance contract. Every ServiceJob-pipeline view
// that presents "where this job came from" must use this explicit type
// rather than re-using ServiceJobFixture fields to stand in for the source
// booking — ServiceBooking id and ServiceJob id must never be substituted
// for each other or silently merged into one id.
// ---------------------------------------------------------------------------

export interface SourceBookingReference {
  /** Always "service_booking" for this pipeline's source entity — distinct
   * from the resulting "service_job" model. Never "booking_field_ops". */
  sourceModel: "service_booking";
  /** The ServiceBooking's own id. NEVER equal to, derived from, or
   * substituted with the resulting ServiceJob's id, even though UX-03's
   * fixture layer currently has no distinct ServiceBooking record to draw
   * this from — see servicebooking-provenance-contract.md for how this
   * pass derives a provisional, clearly-labeled id instead of reusing the
   * ServiceJob id. */
  sourceBookingId: string;
  resultingModel: "service_job";
  resultingServiceJobId: string;
}

export interface JobProvenance {
  source: SourceBookingReference;
  sourceAdapter: string;
  /** Sections that are ServiceJob-only and must never appear on a
   * field_ops.Job / Booking view. */
  serviceJobOnlySections: string[];
}

// ---------------------------------------------------------------------------
// Status transition
// ---------------------------------------------------------------------------

export interface StatusTransitionOptionView {
  toStatus: string;
  requiredFieldsOrEvidence: string[];
  customerVisibleEffect: string;
  financeEffect: string | null;
}

export interface StatusTransitionView {
  currentStatus: string;
  allowedNext: StatusTransitionOptionView[];
  // repository-backed states only — an empty allowedNext list is a valid,
  // honest terminal/blocked state, never papered over with invented options.
}

// ---------------------------------------------------------------------------
// Assignment / dispatch
// ---------------------------------------------------------------------------

export interface AssignmentCandidateView {
  technicianId: string;
  name: string;
  availability: "available" | "busy" | "off_shift" | "unknown";
  currentWorkload: number;
  skillMatch: "match" | "partial" | "unknown";
  brandMatch: "match" | "partial" | "unknown" | "not_applicable";
  coversZone: boolean;
  distanceLabel: string | null; // null when no real distance source exists
  existingAssignmentCount: number;
  ratingLabel: string | null; // null when no real rating source exists
  warnings: string[];
  isCurrentAssignee: boolean;
}

export interface AssignmentActionView {
  action: "assign" | "reassign" | "unassign";
  reasonRequired: boolean;
  confirmationCopy: string;
}

// ---------------------------------------------------------------------------
// Inspection
// ---------------------------------------------------------------------------

export interface InspectionView {
  serviceJobId: string;
  findings: string;
  customerReportedIssue: string;
  observations: string[];
  photos: MediaAssetFixture[];
  recommendedWork: string[];
  requiredParts: { name: string; qty: number }[];
  quoteRequired: boolean;
  checklistStatus: "not_started" | "in_progress" | "complete";
}

// ---------------------------------------------------------------------------
// Quote
// ---------------------------------------------------------------------------

export type QuoteStatus = "draft" | "submitted" | "awaiting_customer" | "approved" | "rejected" | "revised";

export interface QuoteLineItemView {
  kind: "labor" | "parts" | "addon" | "fee" | "discount";
  label: string;
  amount: number;
}

export interface QuoteView {
  id: string;
  serviceJobId: string;
  status: QuoteStatus;
  lineItems: QuoteLineItemView[];
  subtotal: number;
  total: number;
  notes: string;
  revisionNumber: number;
  createdByStaffId: string;
  customerResponseAt: string | null;
  customerResponseNote: string | null;
  timeline: { at: string; event: string }[];
}

// ---------------------------------------------------------------------------
// Checklist
// ---------------------------------------------------------------------------

export interface ChecklistItemView {
  id: string;
  label: string;
  required: boolean;
  completed: boolean;
  passFail: "pass" | "fail" | "not_applicable" | null;
  technicianNote: string | null;
  technicianMedia: MediaAssetFixture[];
  reviewerNote: string | null;
  customerVisible: boolean;
}

export interface ChecklistSectionView {
  id: string;
  label: string;
  items: ChecklistItemView[];
}

export interface ChecklistView {
  id: string;
  serviceJobId: string;
  sections: ChecklistSectionView[];
  progressPct: number;
  completionLocked: boolean;
  reviewState: "not_reviewed" | "in_review" | "reviewed";
}

// ---------------------------------------------------------------------------
// Parts request
// ---------------------------------------------------------------------------

export interface PartsRequestView {
  meta: OperationalViewMeta;
  request: PartsRequestFixture; // serviceJobId-scoped only — never field_ops.Job
  actions: ActionPermissionView[]; // approve/reject/mark-installed = provider-side only
}

/** UX-04B: one row in the Parts Request list. Adds list-only presentation
 * fields (technician/part/last-activity labels, installation state) on top
 * of the shared PartsRequestView — never a separate PartsRequest model. */
export interface PartsRequestListItemView {
  meta: OperationalViewMeta;
  request: PartsRequestFixture;
  technicianName: string;
  serviceJobLabel: string;
  installationState: "not_installed" | "installed" | "not_applicable";
  lastActivityAt: string;
  actions: ActionPermissionView[];
}

// ---------------------------------------------------------------------------
// Invoice / on-site payment
// ---------------------------------------------------------------------------

export type InvoiceState =
  | "not_generated"
  | "draft"
  | "issued"
  | "payment_expected_on_site"
  | "payment_recorded"
  | "partial"
  | "disputed"
  | "voided";

export interface InvoiceView {
  id: string | null;
  serviceJobId: string;
  quoteTotal: number | null;
  invoiceTotal: number;
  state: InvoiceState;
  paymentMethodRecord: string | null; // record of what happened on-site, not a platform-processed payment
  creditDeductionAmount: number;
  commissionDeductionAmount: number;
  // No capture/refund/payout action ever presented — platform does not
  // process ordinary on-site customer-to-provider payments.
}

// ---------------------------------------------------------------------------
// Credit / commission
// ---------------------------------------------------------------------------

export interface CreditCommissionView {
  packageCredit: PackageCreditFixture;
  estimatedCommissionForJob: number;
  creditAfterDeduction: number;
  lowCreditWarning: boolean;
  insufficientCreditBlocker: boolean;
  transactionRef: string | null;
  duplicateDeductionPrevented: boolean;
}

// ---------------------------------------------------------------------------
// Customer communication
// ---------------------------------------------------------------------------

export type CommunicationEventKind =
  | "booking_confirmation"
  | "assignment"
  | "on_the_way"
  | "inspection_update"
  | "quote_submitted"
  | "quote_response"
  | "parts_update"
  | "work_started"
  | "work_completed"
  | "invoice_issued"
  | "support_message";

export interface CommunicationEventView {
  id: string;
  kind: CommunicationEventKind;
  at: string;
  actorName: string;
  channel: "in_app" | "sms" | "email" | "push";
  deliveryState: "sent" | "delivered" | "failed" | "pending";
  customerVisible: boolean; // internal notes must never appear here as customer-visible
  failureCanRetry: boolean;
}

// ---------------------------------------------------------------------------
// Complaint / dispute
// ---------------------------------------------------------------------------

export interface ComplaintDetailView {
  meta: OperationalViewMeta;
  complaint: ComplaintFixture;
  customerStatement: string;
  relatedEntity: EntityLinkView;
  evidence: MediaAssetFixture[];
  timeline: { at: string; actor: string; note: string; customerVisible: boolean }[];
  internalNotes: string[];
  // No tenant dispute-resolution authority and no tenant-issued service
  // credit action — platform decides; tenant only proposes/responds.
  assignedStaffId: string | null;
}

export interface DisputeView {
  id: string;
  customerId: string;
  relatedEntity: EntityLinkView;
  amountContextLabel: string;
  reason: string;
  evidence: MediaAssetFixture[];
  status: "open" | "under_platform_review" | "decided";
  tenantResponse: string | null;
  timeline: { at: string; event: string }[];
  decision: string | null;
  // Platform issues a Customer Service Credit, never a cash refund; tenant
  // credit is deducted per policy — never presented as a tenant payout.
}

// ---------------------------------------------------------------------------
// Compliance
// ---------------------------------------------------------------------------

export interface ComplianceSubmissionView {
  item: ComplianceItemFixture;
  affectedFields: string[]; // populated only when status === "rejected" or a changes-requested-equivalent state
  reviewerExplanation: string | null;
  priorSubmissionPreserved: boolean;
  resubmissionSupported: boolean;
}

// ---------------------------------------------------------------------------
// Operational exception
// ---------------------------------------------------------------------------

export type OperationalExceptionKind =
  | "no_technician_available"
  | "outside_service_area"
  | "invalid_price_config"
  | "missing_quote"
  | "parts_unavailable"
  | "low_credit"
  | "incomplete_checklist"
  | "invalid_transition"
  | "missing_customer_confirmation"
  | "compliance_restriction"
  | "security_contract_blocked";

export interface OperationalExceptionView {
  kind: OperationalExceptionKind;
  affectedWorkflow: string;
  explanation: string;
  safeActions: string[];
  escalationPath: string | null;
  productDecisionState: ReadinessState;
}

// ---------------------------------------------------------------------------
// Action queue / command center
// ---------------------------------------------------------------------------

export interface OperationalActionItemView {
  id: string;
  entity: EntityLinkView;
  summary: string;
  sla: SLAStateView;
  requiredAction: string;
  actions: ActionPermissionView[];
}

export interface OperationalSearchResultGroup {
  pipelineLabel: string;
  results: EntityLinkView[];
}

// ---------------------------------------------------------------------------
// Adapter contract — typed interfaces only, no live calls (see
// docs/design/ux-04-tenant-operations/frontend-adapter-contract.md).
// ---------------------------------------------------------------------------

export interface Ux04OperationsAdapter {
  getCommandCenterQueue(role: CanonicalTenantRole): Promise<OperationalActionItemView[]>;
  search(query: string): Promise<OperationalSearchResultGroup[]>;
  listBookings(): Promise<BookingListItemView[]>;
  getBookingDetail(id: string): Promise<BookingDetailView>;
  listJobs(): Promise<JobListItemView[]>;
  getJobDetail(id: string): Promise<JobDetailView>;
  getAssignmentCandidates(jobId: string): Promise<AssignmentCandidateView[]>;
  getStatusTransition(jobId: string): Promise<StatusTransitionView>;
  getInspection(jobId: string): Promise<InspectionView>;
  getQuote(quoteId: string): Promise<QuoteView>;
  getChecklist(checklistId: string): Promise<ChecklistView>;
  listPartsRequests(jobId: string): Promise<PartsRequestView[]>;
  getInvoice(jobId: string): Promise<InvoiceView>;
  getCreditCommission(jobId: string): Promise<CreditCommissionView>;
  listCommunication(jobId: string): Promise<CommunicationEventView[]>;
  getComplaint(id: string): Promise<ComplaintDetailView>;
  listComplianceSubmissions(): Promise<ComplianceSubmissionView[]>;
}
