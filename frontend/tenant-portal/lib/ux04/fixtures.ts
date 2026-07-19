/**
 * DESIGN PHASE UX-04 — realistic fixtures for the operations view models in
 * ./types.ts. MOCK_DESIGN_ONLY / READ_ONLY_READY per readiness-state-registry.csv
 * until wired to a real endpoint. No lorem ipsum — values mirror the shapes
 * described in UX-03's booking/job/quote/checklist/parts/finance docs.
 */
import type {
  BookingListItemView,
  JobListItemView,
  JobDetailView,
  OperationalActionItemView,
  AssignmentCandidateView,
  QuoteView,
  ChecklistView,
  PartsRequestView,
  InvoiceView,
  CreditCommissionView,
  CommunicationEventView,
  ComplaintDetailView,
  DisputeView,
  OperationalExceptionView,
  SLAStateView,
  InspectionView,
  FieldOpsJobDetailView,
  PartsRequestListItemView,
  JobProvenance,
} from "./types";
import { FIXTURE_COMPLAINTS, FIXTURE_MEDIA_ASSETS } from "../ux03/fixtures";

const now = "2026-07-19T09:00:00Z";

export const bookingListFixture: BookingListItemView[] = [
  {
    meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04BookingAdapter.listBookings", lastRefreshedAt: now },
    booking: {
      id: "bk_1001",
      pipeline: "booking_field_ops",
      canonicalId: "fo_job_4471",
      customerName: "Priya Nair",
      serviceName: "AC Deep Clean",
      status: "confirmed",
      scheduledAt: "2026-07-19T13:00:00Z",
      address: "12 Palm Grove, Kochi",
      assignedStaffId: "staff_22",
      cancelSupported: "unresolved_mock_only",
    },
    sla: { state: "approaching_deadline", label: "Approaching deadline", deadlineAt: "2026-07-19T13:00:00Z", explanation: "Scheduled slot begins in under 4 hours." },
    nextAction: "Confirm technician dispatch",
    actions: [{ actionKey: "field_ops:jobs:assign", available: true, reason: null }],
  },
  {
    meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04BookingAdapter.listBookings", lastRefreshedAt: now },
    booking: {
      id: "bk_1002",
      pipeline: "booking_field_ops",
      canonicalId: "fo_job_4472",
      customerName: "Arjun Menon",
      serviceName: "Plumbing Repair",
      status: "requested",
      scheduledAt: "2026-07-20T10:00:00Z",
      address: "44 Marine Drive, Kochi",
      assignedStaffId: null,
      cancelSupported: "unresolved_mock_only",
    },
    sla: { state: "at_risk", label: "Unassigned, at risk", deadlineAt: "2026-07-20T10:00:00Z", explanation: "No staff assigned within 24h of scheduled slot." },
    nextAction: "Assign staff",
    actions: [{ actionKey: "field_ops:jobs:assign", available: true, reason: null }],
  },
];

export const jobListFixture: JobListItemView[] = [
  {
    meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04JobAdapter.listJobs", lastRefreshedAt: now },
    job: {
      id: "sj_7001",
      pipeline: "service_booking_service_job",
      canonicalId: "service_job_7001",
      customerName: "Fatima Sheikh",
      serviceName: "Washing Machine Repair",
      status: "in_progress",
      scheduledAt: "2026-07-19T11:00:00Z",
      address: "8 Lotus Enclave, Kochi",
      assignedTechnicianId: "tech_9",
      quoteId: "q_501",
      checklistId: "cl_501",
      partsRequestIds: ["pr_301"],
      invoiceId: null,
      commissionBps: 800,
      cancelSupported: "unresolved_mock_only",
    },
    sla: { state: "on_track", label: "On track", deadlineAt: null, explanation: "Technician on-site, checklist in progress." },
    nextAction: "Review parts request",
    actions: [{ actionKey: "field_ops:jobs:transition", available: true, reason: null }],
  },
  {
    meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04JobAdapter.listJobs", lastRefreshedAt: now },
    job: {
      id: "sj_7002",
      pipeline: "service_booking_service_job",
      canonicalId: "service_job_7002",
      customerName: "Rohit Verma",
      serviceName: "Geyser Installation",
      status: "awaiting_parts",
      scheduledAt: "2026-07-18T15:00:00Z",
      address: "21 Hill View, Kochi",
      assignedTechnicianId: "tech_4",
      quoteId: "q_502",
      checklistId: null,
      partsRequestIds: ["pr_302"],
      invoiceId: null,
      commissionBps: 800,
      cancelSupported: "unresolved_mock_only",
    },
    sla: { state: "breached", label: "SLA breached", deadlineAt: "2026-07-19T00:00:00Z", explanation: "Awaiting parts approval past the 24h SLA window." },
    nextAction: "Approve or reject parts request",
    actions: [{ actionKey: "inventory:items:approve", available: false, reason: "Requires tenant_owner or a staff member with the parts-approval permission." }],
  },
];

export const assignmentCandidatesFixture: AssignmentCandidateView[] = [
  {
    technicianId: "tech_9",
    name: "Deepak R.",
    availability: "available",
    currentWorkload: 2,
    skillMatch: "match",
    brandMatch: "match",
    coversZone: true,
    distanceLabel: null,
    existingAssignmentCount: 2,
    ratingLabel: null,
    warnings: [],
    isCurrentAssignee: true,
  },
  {
    technicianId: "tech_14",
    name: "Sana K.",
    availability: "busy",
    currentWorkload: 4,
    skillMatch: "partial",
    brandMatch: "not_applicable",
    coversZone: true,
    distanceLabel: null,
    existingAssignmentCount: 4,
    ratingLabel: null,
    warnings: ["Currently assigned to 4 open jobs — reassigning may cause a scheduling conflict."],
    isCurrentAssignee: false,
  },
];

export const quoteFixture: QuoteView = {
  id: "q_501",
  serviceJobId: "sj_7001",
  status: "awaiting_customer",
  lineItems: [
    { kind: "labor", label: "Diagnostic + repair labor", amount: 600 },
    { kind: "parts", label: "Drain pump", amount: 950 },
    { kind: "fee", label: "Visit fee", amount: 150 },
  ],
  subtotal: 1700,
  total: 1700,
  notes: "Customer approved drain pump replacement over phone; awaiting in-app confirmation.",
  revisionNumber: 1,
  createdByStaffId: "staff_22",
  customerResponseAt: null,
  customerResponseNote: null,
  timeline: [{ at: "2026-07-19T09:30:00Z", event: "Quote submitted to customer" }],
};

export const checklistFixture: ChecklistView = {
  id: "cl_501",
  serviceJobId: "sj_7001",
  progressPct: 60,
  completionLocked: false,
  reviewState: "in_review",
  sections: [
    {
      id: "sec_1",
      label: "Safety checks",
      items: [
        { id: "it_1", label: "Power isolated before service", required: true, completed: true, passFail: "pass", technicianNote: null, technicianMedia: [], reviewerNote: null, customerVisible: true },
        { id: "it_2", label: "Water supply shut off", required: true, completed: true, passFail: "pass", technicianNote: null, technicianMedia: [], reviewerNote: null, customerVisible: true },
      ],
    },
    {
      id: "sec_2",
      label: "Repair steps",
      items: [
        { id: "it_3", label: "Drain pump replaced", required: true, completed: true, passFail: "pass", technicianNote: "Old pump seized; replaced with OEM part.", technicianMedia: [], reviewerNote: null, customerVisible: true },
        { id: "it_4", label: "Leak test after reassembly", required: true, completed: false, passFail: null, technicianNote: null, technicianMedia: [], reviewerNote: null, customerVisible: true },
      ],
    },
  ],
};

export const partsRequestFixture: PartsRequestView = {
  meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04PartsAdapter.listPartsRequests", lastRefreshedAt: now },
  request: {
    id: "pr_301",
    serviceJobId: "sj_7001",
    requestedByTechnicianId: "tech_9",
    items: [{ id: "part_1", name: "Drain pump (OEM)", qty: 1, unitCost: 950 }],
    status: "approved",
    decidedByStaffId: "staff_22",
    decidedAt: "2026-07-19T08:45:00Z",
  },
  actions: [
    { actionKey: "inventory:items:approve", available: false, reason: "Already decided — approve/reject is a one-time action." },
    { actionKey: "field_ops:jobs:read", available: true, reason: null },
  ],
};

export const invoiceFixture: InvoiceView = {
  id: null,
  serviceJobId: "sj_7001",
  quoteTotal: 1700,
  invoiceTotal: 1700,
  state: "payment_expected_on_site",
  paymentMethodRecord: null,
  creditDeductionAmount: 0,
  commissionDeductionAmount: 136,
};

export const creditCommissionFixture: CreditCommissionView = {
  packageCredit: {
    planName: "Growth Plan",
    creditBalance: 24500,
    creditIssuedThisCycle: 30000,
    creditConsumedThisCycle: 5500,
    commissionRateBps: 800,
    cycleEndsAt: "2026-07-31T23:59:59Z",
  },
  estimatedCommissionForJob: 136,
  creditAfterDeduction: 24364,
  lowCreditWarning: false,
  insufficientCreditBlocker: false,
  transactionRef: null,
  duplicateDeductionPrevented: true,
};

export const communicationFixture: CommunicationEventView[] = [
  { id: "ce_1", kind: "booking_confirmation", at: "2026-07-18T09:00:00Z", actorName: "System", channel: "sms", deliveryState: "delivered", customerVisible: true, failureCanRetry: false },
  { id: "ce_2", kind: "assignment", at: "2026-07-19T07:50:00Z", actorName: "Deepak R.", channel: "push", deliveryState: "delivered", customerVisible: true, failureCanRetry: false },
  { id: "ce_3", kind: "quote_submitted", at: "2026-07-19T09:30:00Z", actorName: "Deepak R.", channel: "in_app", deliveryState: "sent", customerVisible: true, failureCanRetry: false },
  { id: "ce_4", kind: "support_message", at: "2026-07-19T09:35:00Z", actorName: "Fatima Sheikh", channel: "in_app", deliveryState: "failed", customerVisible: false, failureCanRetry: true },
];

export const actionQueueFixture: OperationalActionItemView[] = [
  {
    id: "aq_1",
    entity: { kind: "service_job", id: "sj_7002", label: "Geyser Installation — Rohit Verma", href: "/dev/ux-04/job-detail" },
    summary: "Parts request awaiting approval, SLA breached",
    sla: { state: "breached", label: "SLA breached", deadlineAt: "2026-07-19T00:00:00Z", explanation: "24h approval window passed." },
    requiredAction: "Approve or reject parts request",
    actions: [{ actionKey: "inventory:items:approve", available: true, reason: null }],
  },
  {
    id: "aq_2",
    entity: { kind: "booking", id: "bk_1002", label: "Plumbing Repair — Arjun Menon", href: "/dev/ux-04/booking-detail" },
    summary: "Booking unassigned, scheduled in under 24h",
    sla: { state: "at_risk", label: "At risk", deadlineAt: "2026-07-20T10:00:00Z", explanation: "No staff assigned." },
    requiredAction: "Assign staff",
    actions: [{ actionKey: "field_ops:jobs:assign", available: true, reason: null }],
  },
];

/** Aggregated for the Job Detail workspace showcase page. */
export const jobDetailFixture: JobDetailView = {
  meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04JobAdapter.getJobDetail", lastRefreshedAt: now },
  job: jobListFixture[0].job,
  sla: jobListFixture[0].sla,
  statusTransition: {
    currentStatus: "in_progress",
    allowedNext: [
      { toStatus: "work_done", requiredFieldsOrEvidence: ["Checklist required items complete"], customerVisibleEffect: "Customer sees 'Work completed, awaiting review'.", financeEffect: null },
    ],
  },
  assignment: assignmentCandidatesFixture,
  quote: quoteFixture,
  checklist: checklistFixture,
  partsRequests: [partsRequestFixture],
  invoice: invoiceFixture,
  creditCommission: creditCommissionFixture,
  communication: communicationFixture,
  media: [],
  activity: [
    { id: "ae_1", at: "2026-07-19T07:50:00Z", actorName: "Staff Owner", actorRole: "tenant_owner", action: "assign", resource: "service_job:sj_7001", result: "success" },
  ],
  actions: [{ actionKey: "field_ops:jobs:transition", available: true, reason: null }],
};

/** UX-04A additions. */

export const complaintDetailFixture: ComplaintDetailView = {
  meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04ComplaintAdapter.getComplaint", lastRefreshedAt: now },
  complaint: FIXTURE_COMPLAINTS[0],
  customerStatement: "The technician quoted ₹1700 but I was charged extra for a part I never approved.",
  relatedEntity: { kind: "service_job", id: "sj_2202", label: "Service Job sj_2202", href: "/dev/ux-04/job-detail" },
  evidence: FIXTURE_MEDIA_ASSETS.slice(0, 1),
  timeline: [
    { at: "2026-07-18T15:00:00Z", actor: "Customer", note: "Filed complaint about unapproved parts charge.", customerVisible: true },
    { at: "2026-07-18T16:10:00Z", actor: "Ananya Rao", note: "Reviewing invoice line items internally before responding.", customerVisible: false },
  ],
  internalNotes: ["Check parts-request approval timestamp against quote revision 1."],
  assignedStaffId: "staff_22",
};

export const disputeFixture: DisputeView = {
  id: "dsp_1",
  customerId: "cust_2",
  relatedEntity: { kind: "invoice", id: "sj_2202", label: "Invoice — Service Job sj_2202", href: "/dev/ux-04/job-detail" },
  amountContextLabel: "₹950 parts charge in dispute",
  reason: "Customer states the drain-pump replacement was never verbally approved.",
  evidence: FIXTURE_MEDIA_ASSETS.slice(0, 1),
  status: "under_platform_review",
  tenantResponse: "Technician recorded verbal approval in the job notes at 09:12; no written confirmation exists.",
  timeline: [
    { at: "2026-07-18T15:00:00Z", event: "Dispute opened by customer" },
    { at: "2026-07-19T09:00:00Z", event: "Tenant response submitted" },
  ],
  decision: null,
};

export const operationalExceptionsFixture: OperationalExceptionView[] = [
  {
    kind: "no_technician_available",
    affectedWorkflow: "Assignment — Plumbing Repair (bk_1002)",
    explanation: "No technician with a plumbing skill tag is available in the covered zone for the requested slot.",
    safeActions: ["Widen the requested time window", "Escalate to a neighboring zone's staff pool"],
    escalationPath: "Contact platform operations if no staff becomes available within 24h.",
    productDecisionState: "PRODUCT_DECISION_REQUIRED",
  },
  {
    kind: "low_credit",
    affectedWorkflow: "Credit & Commission — package credit balance",
    explanation: "Package credit balance is projected to fall below the commission owed on open jobs this cycle.",
    safeActions: ["Review open job commission estimates", "Top up package credit before cycle end"],
    escalationPath: null,
    productDecisionState: "NOT_APPLICABLE",
  },
  {
    kind: "invalid_transition",
    affectedWorkflow: "Status transition — Service Job sj_7002",
    explanation: "An out-of-sequence transition was requested and rejected by the repository-backed state machine.",
    safeActions: ["Retry the correct next-step transition"],
    escalationPath: null,
    productDecisionState: "NOT_APPLICABLE",
  },
];

export const slaGalleryFixture: SLAStateView[] = [
  { state: "on_track", label: "On track", deadlineAt: null, explanation: "No deadline risk currently detected." },
  { state: "approaching_deadline", label: "Approaching deadline", deadlineAt: "2026-07-19T13:00:00Z", explanation: "Scheduled slot begins in under 4 hours." },
  { state: "at_risk", label: "At risk", deadlineAt: "2026-07-20T10:00:00Z", explanation: "No staff assigned within 24h of scheduled slot." },
  { state: "breached", label: "Breached", deadlineAt: "2026-07-19T00:00:00Z", explanation: "24h approval window passed." },
  { state: "blocked", label: "Blocked", deadlineAt: null, explanation: "Blocked pending an operational exception being cleared." },
  { state: "waiting_on_customer", label: "Waiting on customer", deadlineAt: null, explanation: "Quote awaiting customer approval." },
  { state: "waiting_on_provider", label: "Waiting on provider", deadlineAt: null, explanation: "Parts request awaiting provider-side approval." },
  { state: "waiting_on_platform", label: "Waiting on platform", deadlineAt: null, explanation: "Dispute under platform review." },
  { state: "product_decision_blocked", label: "Product decision blocked", deadlineAt: null, explanation: "No confirmed SLA rule exists for this workflow yet." },
];

export const inspectionFixture: InspectionView = {
  serviceJobId: "sj_7001",
  customerReportedIssue: "Washing machine drains slowly and makes a grinding noise on spin cycle.",
  findings: "Drain pump bearing worn; debris lodged in impeller housing.",
  observations: ["Grinding noise confirmed on spin cycle", "Drain time approx. 3x longer than expected"],
  photos: [],
  recommendedWork: ["Replace drain pump", "Clear impeller housing debris"],
  requiredParts: [{ name: "Drain pump (OEM)", qty: 1 }],
  quoteRequired: true,
  checklistStatus: "in_progress",
};

/** UX-04B additions. */

export const fieldOpsJobDetailFixture: FieldOpsJobDetailView = {
  meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04FieldOpsJobAdapter.getFieldOpsJobDetail", lastRefreshedAt: now },
  job: bookingListFixture[0].booking,
  sla: bookingListFixture[0].sla,
  timeline: [
    { id: "aefo_1", at: "2026-07-18T09:00:00Z", actorName: "System", actorRole: "tenant_owner", action: "booking confirmed", resource: "field_ops.Job:fo_job_4471", result: "success" },
    { id: "aefo_2", at: "2026-07-19T07:50:00Z", actorName: "Ananya Rao", actorRole: "tenant_owner", action: "assigned staff", resource: "field_ops.Job:fo_job_4471", result: "success" },
  ],
  activity: [
    { id: "aefo_3", at: "2026-07-19T07:50:00Z", actorName: "Ananya Rao", actorRole: "tenant_owner", action: "assign", resource: "field_ops.Job:fo_job_4471", result: "success" },
  ],
  notes: ["Customer requested a morning slot; confirmed for 13:00 IST window."],
  actions: [{ actionKey: "field_ops:jobs:assign", available: true, reason: null }],
};

export const partsRequestListFixture: PartsRequestListItemView[] = [
  {
    meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04PartsAdapter.listPartsRequestsList", lastRefreshedAt: now },
    request: partsRequestFixture.request,
    technicianName: "Deepak R.",
    serviceJobLabel: "Washing Machine Repair — sj_7001",
    installationState: "installed",
    lastActivityAt: "2026-07-19T08:45:00Z",
    actions: [{ actionKey: "field_ops:jobs:read", available: true, reason: null }],
  },
  {
    meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04PartsAdapter.listPartsRequestsList", lastRefreshedAt: now },
    request: {
      id: "pr_302",
      serviceJobId: "sj_7002",
      requestedByTechnicianId: "tech_4",
      items: [{ id: "part_2", name: "Geyser thermostat", qty: 1, unitCost: 420 }],
      status: "requested",
      decidedByStaffId: null,
      decidedAt: null,
    },
    technicianName: "Sana K.",
    serviceJobLabel: "Geyser Installation — sj_7002",
    installationState: "not_applicable",
    lastActivityAt: "2026-07-18T15:00:00Z",
    actions: [{ actionKey: "inventory:items:approve", available: true, reason: null }],
  },
  {
    meta: { readiness: "MOCK_DESIGN_ONLY", sourceAdapter: "ux04PartsAdapter.listPartsRequestsList", lastRefreshedAt: now },
    request: {
      id: "pr_303",
      serviceJobId: "sj_7003",
      requestedByTechnicianId: "tech_14",
      items: [{ id: "part_3", name: "Fridge compressor relay", qty: 1, unitCost: 260 }],
      status: "rejected",
      decidedByStaffId: "staff_22",
      decidedAt: "2026-07-17T12:00:00Z",
    },
    technicianName: "Sana K.",
    serviceJobLabel: "Fridge Repair — sj_7003",
    installationState: "not_applicable",
    lastActivityAt: "2026-07-17T12:00:00Z",
    actions: [{ actionKey: "inventory:items:approve", available: false, reason: "Already decided — approve/reject is a one-time action." }],
  },
];

export const partsRequestListEmptyFixture: PartsRequestListItemView[] = [];

export const jobProvenanceFixture: JobProvenance = {
  source: {
    sourceModel: "service_booking",
    // Provisional id: UX-03's fixture layer has no distinct ServiceBooking
    // record. Rather than reuse the ServiceJob id (which would silently
    // conflate the two), this pass derives a clearly-labeled, distinctly
    // prefixed provisional id so the two are never presented as the same
    // value. See servicebooking-provenance-contract.md.
    sourceBookingId: "svcbk_provisional_7001",
    resultingModel: "service_job",
    resultingServiceJobId: "sj_7001",
  },
  sourceAdapter: "ux04ProvenanceAdapter.getJobProvenance",
  serviceJobOnlySections: ["quote", "checklist", "partsRequests", "invoice", "creditCommission"],
};
