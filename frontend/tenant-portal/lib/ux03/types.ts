/**
 * DESIGN PHASE UX-03 — Tenant/Business Portal shared types.
 *
 * UI-layer types for the UX-03 foundation only. These are NOT a second
 * source of truth for backend contracts — anything shaped like a real
 * ServiceOS entity (job, booking, quote, etc.) here is a design fixture
 * until a real API contract is confirmed. See
 * docs/design/ux-03-tenant-portal/backend-contract-dependencies.md.
 *
 * Canonical tenant roles — NEVER invent additional role names. Job titles
 * (e.g. "Branch Manager", "Dispatcher") are descriptive labels a tenant may
 * assign to a staff member — they carry no authorization meaning. Real
 * capability comes from the role + StaffPermission overrides below.
 */
export type CanonicalTenantRole = "tenant_owner" | "staff" | "technician";

/** Referenced but not tenant-side roles (other portals / actors). */
export type ReferencedRole =
  | "customer"
  | "super_admin"
  | "admin_operations"
  | "admin_finance"
  | "admin_security"
  | "admin_readonly";

/** Dev-only metadata describing how real/ready a page or action is.
 * NEVER rendered to real users — dev-showcase and internal docs only. */
export type ReadinessState =
  | "PRODUCTION_READY"
  | "READ_ONLY_READY"
  | "MOCK_DESIGN_ONLY"
  | "API_CONTRACT_REQUIRED"
  | "SECURITY_CONTRACT_PENDING"
  | "PRODUCT_DECISION_REQUIRED"
  | "DEPRECATED"
  | "NOT_APPLICABLE";

/**
 * Real permission_key format observed in app/core/permissions.py:
 * "<namespace>:<resource>:<action>", e.g. "field_ops:jobs:assign".
 * StaffPermission (app/engines/auth/models.py::StaffPermission) rows store
 * { user_id, tenant_id, permission_key, is_granted }. A row with
 * is_granted=false is an EXPLICIT DENY that must render distinctly from
 * "not granted" (absence of a row) — deny never implies a role default
 * grant is upgraded, and grant never overrides an explicit deny.
 */
export interface StaffPermissionFixture {
  permissionKey: string; // e.g. "field_ops:jobs:assign"
  label: string; // human-readable, mapped 1:1 to permissionKey
  group: string; // e.g. "Jobs", "Finance", "Service Areas"
  description: string;
  roleDefaultForTechnician: boolean; // from ROLE_PERMISSIONS["technician"] in app/core/permissions.py
  state: "granted_by_role" | "granted_override" | "denied_override" | "not_granted";
}

/** Profile-completion / review lifecycle — one shared state machine used by
 * both the setup wizard and the dashboard, not duplicated per page. */
export type ProfileReviewState =
  | "not_started"
  | "in_progress"
  | "ready_to_submit"
  | "submitted"
  | "under_review"
  | "changes_requested"
  | "approved"
  | "rejected"
  | "suspended";

export interface TenantProfileFixture {
  tenantId: string;
  legalName: string;
  displayName: string;
  vertical: "home_services";
  reviewState: ProfileReviewState;
  completionPct: number; // 0-100, drives the setup wizard progress indicator
  ownerName: string;
  ownerEmail: string;
  registrationNumber: string | null;
  taxId: string | null;
  addresses: { id: string; label: string; line1: string; city: string; region: string; postalCode: string }[];
  categories: string[];
  serviceAreaCount: number;
  teamSize: number;
  packagePlan: string | null;
  securityDepositRequired: boolean;
  createdAt: string;
  submittedAt: string | null;
  lastReviewNoteAt: string | null;
  changesRequested: string[];
}

export interface TeamMemberFixture {
  id: string;
  name: string;
  email: string;
  role: CanonicalTenantRole; // tenant_owner | staff | technician — never invent variants
  jobTitle: string; // descriptive only, NOT an authorization boundary
  status: "active" | "invited" | "inactive" | "suspended";
  invitedAt: string;
  lastActiveAt: string | null;
  permissions: StaffPermissionFixture[];
  // technician-only extra sections
  technicianDetail?: {
    availability: "available" | "on_job" | "off_duty" | "on_leave";
    activeJobId: string | null;
    skills: string[];
    brands: string[];
    certifications: { id: string; label: string; expiresAt: string | null }[];
    completedJobsCount: number;
    rating: number | null;
    recentPartsActivityCount: number;
  };
}

/** Booking pipeline (Booking -> field_ops.Job) is a DISTINCT pipeline from
 * the Job pipeline (ServiceBooking -> ServiceJob). Never merge rows from
 * the two into one shared "job/booking" model without preserving which
 * pipeline it came from. */
export type PipelineKind = "booking_field_ops" | "service_booking_service_job";

export interface BookingFixture {
  id: string;
  pipeline: "booking_field_ops";
  canonicalId: string; // field_ops.Job id
  customerName: string;
  serviceName: string;
  status: "requested" | "confirmed" | "in_progress" | "completed" | "cancelled";
  scheduledAt: string;
  address: string;
  assignedStaffId: string | null;
  // Customer cancel/reschedule for this pipeline is UNRESOLVED product-side.
  cancelSupported: "unresolved_mock_only";
}

export interface ServiceJobFixture {
  id: string;
  pipeline: "service_booking_service_job";
  canonicalId: string; // ServiceJob id
  customerName: string;
  serviceName: string;
  status: "quoted" | "scheduled" | "in_progress" | "awaiting_parts" | "completed" | "cancelled";
  scheduledAt: string;
  address: string;
  assignedTechnicianId: string | null;
  quoteId: string | null;
  checklistId: string | null;
  partsRequestIds: string[];
  invoiceId: string | null;
  commissionBps: number;
  cancelSupported: "unresolved_mock_only";
}

export interface PartsRequestFixture {
  id: string;
  serviceJobId: string; // ServiceJob-only — field_ops.Job has no PartsRequest
  requestedByTechnicianId: string;
  items: { id: string; name: string; qty: number; unitCost: number }[];
  status: "requested" | "approved" | "rejected" | "installed";
  // Only provider-side staff (tenant_owner or staff w/ inventory:items:write-class
  // permission) may approve/reject/mark-installed. Technicians request/view only.
  decidedByStaffId: string | null;
  decidedAt: string | null;
}

/** Package credit / commission / security deposit are three SEPARATE
 * concepts — never collapse into one "balance" number, and never render
 * payout/withdrawal/settlement UI (the platform does not process ordinary
 * on-site customer-to-provider payments). */
export interface PackageCreditFixture {
  planName: string;
  creditBalance: number;
  creditIssuedThisCycle: number;
  creditConsumedThisCycle: number;
  commissionRateBps: number; // deducted from credit balance on job completion
  cycleEndsAt: string;
}

export interface SecurityDepositFixture {
  requiredAmount: number;
  heldAmount: number;
  status: "not_required" | "pending" | "held" | "partially_released" | "released" | "forfeited";
  lastChangeAt: string;
  history: { id: string; type: "hold" | "release" | "forfeit"; amount: number; at: string; note: string }[];
}

export interface FinanceTransactionFixture {
  id: string;
  kind: "credit_issue" | "credit_consume_commission" | "deposit_hold" | "deposit_release" | "invoice_settlement_record";
  amount: number;
  at: string;
  relatedJobId: string | null;
  note: string;
}

export interface PricingFixture {
  serviceId: string;
  serviceName: string;
  jobType: string;
  brand: string | null;
  zoneId: string | null;
  platformMinPrice: number;
  platformMaxPrice: number;
  tenantPrice: number;
  effectivePricePreview: number;
  belowPlatformMin: boolean;
}

export interface ServiceAreaFixture {
  id: string;
  city: string;
  district: string;
  postalCode: string;
  zoneId: string;
  coverageStatus: "covered" | "partial" | "not_covered" | "conflict";
  // geo authorization is only closed for a frozen slice — treat mutation as
  // read-only/mock unless proven otherwise for the specific action.
  mutationReadiness: ReadinessState;
}

export interface CustomerFixture {
  id: string;
  name: string;
  maskedPhone: string;
  maskedEmail: string;
  totalBookings: number;
  totalServiceJobs: number;
  lastServiceAt: string | null;
  openComplaintCount: number;
}

export interface ComplaintFixture {
  id: string;
  customerId: string;
  jobRef: string;
  category: string;
  status: "open" | "in_review" | "resolved" | "escalated_to_platform";
  submittedAt: string;
  // Provider-side has proposal/response authority only; final dispute
  // adjudication authority belongs to the platform — never imply otherwise.
  providerCanRespond: boolean;
}

export interface ComplianceItemFixture {
  id: string;
  requirement: string;
  status: "not_submitted" | "submitted" | "under_review" | "approved" | "rejected" | "expiring_soon" | "expired";
  documentId: string | null;
  submittedAt: string | null;
  reviewedAt: string | null;
  history: { id: string; at: string; actor: string; action: string }[];
}

export interface MediaAssetFixture {
  id: string;
  label: string;
  kind: "logo" | "gallery" | "job_photo" | "document";
  // Never surface storage keys, signed URLs, or credentials in fixtures/UI —
  // previewToken stands in for whatever safe reference the real API returns.
  previewToken: string;
  uploadedAt: string;
  sizeLabel: string;
}

export interface AuditEventFixture {
  id: string;
  at: string;
  actorName: string;
  actorRole: CanonicalTenantRole;
  action: string;
  resource: string;
  result: "success" | "failure" | "denied";
  // Tenant-scoped only — never platform-wide events, other tenants' events,
  // secrets, or tokens.
}

/** Typed adapter interface — every method is fixture-backed today
 * (MOCK_DESIGN_ONLY / READ_ONLY_READY per readiness-state-registry.csv)
 * until a real endpoint is confirmed and wired. */
export interface Ux03DataAdapter {
  getTenantProfile(): Promise<TenantProfileFixture>;
  listTeamMembers(): Promise<TeamMemberFixture[]>;
  getTeamMember(id: string): Promise<TeamMemberFixture | undefined>;
  listBookings(): Promise<BookingFixture[]>;
  listServiceJobs(): Promise<ServiceJobFixture[]>;
  listPartsRequests(serviceJobId: string): Promise<PartsRequestFixture[]>;
  getPackageCredit(): Promise<PackageCreditFixture>;
  getSecurityDeposit(): Promise<SecurityDepositFixture>;
  listFinanceTransactions(): Promise<FinanceTransactionFixture[]>;
  listPricing(): Promise<PricingFixture[]>;
  listServiceAreas(): Promise<ServiceAreaFixture[]>;
  listCustomers(): Promise<CustomerFixture[]>;
  listComplaints(): Promise<ComplaintFixture[]>;
  listComplianceItems(): Promise<ComplianceItemFixture[]>;
  listMediaAssets(): Promise<MediaAssetFixture[]>;
  listAuditEvents(): Promise<AuditEventFixture[]>;
}
