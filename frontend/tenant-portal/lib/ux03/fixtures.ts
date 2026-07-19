/**
 * DESIGN PHASE UX-03 — typed fixtures backing the tenant-portal dev showcase.
 * Realistic ServiceOS data (home_services vertical), no lorem ipsum, no
 * fake production URLs, no real secrets. See typed-fixture-contract.md.
 */
import type {
  AuditEventFixture,
  BookingFixture,
  ComplaintFixture,
  ComplianceItemFixture,
  CustomerFixture,
  FinanceTransactionFixture,
  MediaAssetFixture,
  PackageCreditFixture,
  PartsRequestFixture,
  PricingFixture,
  SecurityDepositFixture,
  ServiceAreaFixture,
  ServiceJobFixture,
  StaffPermissionFixture,
  TeamMemberFixture,
  TenantProfileFixture,
  Ux03DataAdapter,
} from "./types";

export const FIXTURE_TENANT_PROFILE: TenantProfileFixture = {
  tenantId: "tn_8841",
  legalName: "Bright Home Services Pvt Ltd",
  displayName: "Bright Home Services",
  vertical: "home_services",
  reviewState: "under_review",
  completionPct: 82,
  ownerName: "Ananya Rao",
  ownerEmail: "ananya@brighthomeservices.example",
  registrationNumber: "U74999KA2023PTC178234",
  taxId: "29AACCB1234F1Z5",
  addresses: [
    { id: "addr_1", label: "Registered Office", line1: "12 MG Road", city: "Bengaluru", region: "Karnataka", postalCode: "560001" },
  ],
  categories: ["AC Repair", "Plumbing", "Electrical"],
  serviceAreaCount: 6,
  teamSize: 14,
  packagePlan: "Growth",
  securityDepositRequired: true,
  createdAt: "2026-06-02T09:12:00Z",
  submittedAt: "2026-07-10T14:00:00Z",
  lastReviewNoteAt: "2026-07-15T11:20:00Z",
  changesRequested: ["Upload GST certificate (current copy expired)", "Confirm 2 service areas overlap with an existing tenant"],
};

const PERM = (permissionKey: string, label: string, group: string, description: string, roleDefaultForTechnician: boolean, state: StaffPermissionFixture["state"]): StaffPermissionFixture => ({
  permissionKey, label, group, description, roleDefaultForTechnician, state,
});

// Real permission_key strings from app/core/permissions.py (P.* constants).
export const FIXTURE_PERMISSION_CATALOG: StaffPermissionFixture[] = [
  PERM("field_ops:jobs:read", "View assigned jobs", "Jobs", "See jobs assigned to this staff member.", true, "granted_by_role"),
  PERM("field_ops:jobs:update", "Update job status", "Jobs", "Transition status on own assigned jobs.", true, "granted_by_role"),
  PERM("field_ops:jobs:assign", "Assign/reassign jobs", "Jobs", "Dispatch jobs to technicians.", false, "not_granted"),
  PERM("field_ops:jobs:close", "Close jobs & record payment", "Jobs", "Record direct customer payment and close own jobs.", true, "granted_by_role"),
  PERM("field_ops:parts:add", "Request parts", "Parts", "Add a parts request on own jobs (technician-facing only).", true, "granted_by_role"),
  PERM("inventory:items:write", "Approve/reject parts requests", "Parts", "Provider-side approval authority — technicians never get this.", false, "not_granted"),
  PERM("field_ops:quotes:manage", "Create/update quotes", "Jobs", "Draft and edit quotes on own jobs.", true, "granted_by_role"),
  PERM("tenant_service_area:read", "View service areas", "Service Areas", "Read-only view of configured coverage.", true, "granted_by_role"),
  PERM("tenant_service_area:update", "Edit service areas", "Service Areas", "Mutate zones/coverage (frozen-slice authorization applies).", false, "denied_override"),
  PERM("booking:bookings:read", "View schedule", "Bookings", "See own booking schedule.", true, "granted_by_role"),
  PERM("chat:read", "Read chat", "Communication", "View customer chat threads.", true, "granted_by_role"),
  PERM("chat:write", "Send chat messages", "Communication", "Reply in customer chat threads.", true, "granted_by_role"),
];

export const FIXTURE_TEAM_MEMBERS: TeamMemberFixture[] = [
  {
    id: "staff_owner_1", name: "Ananya Rao", email: "ananya@brighthomeservices.example",
    role: "tenant_owner", jobTitle: "Founder", status: "active",
    invitedAt: "2026-06-02T09:12:00Z", lastActiveAt: "2026-07-19T08:30:00Z",
    permissions: [],
  },
  {
    id: "staff_2", name: "Kiran Shetty", email: "kiran@brighthomeservices.example",
    role: "staff", jobTitle: "Office Coordinator", status: "active",
    invitedAt: "2026-06-05T10:00:00Z", lastActiveAt: "2026-07-18T17:45:00Z",
    permissions: FIXTURE_PERMISSION_CATALOG.map((p) => ({ ...p, state: p.roleDefaultForTechnician ? "granted_by_role" : "not_granted" })),
  },
  {
    id: "tech_3", name: "Rahul Menon", email: "rahul@brighthomeservices.example",
    role: "technician", jobTitle: "Senior AC Technician", status: "active",
    invitedAt: "2026-06-08T09:00:00Z", lastActiveAt: "2026-07-19T07:10:00Z",
    permissions: FIXTURE_PERMISSION_CATALOG.map((p, i) =>
      i === 5 ? { ...p, state: "denied_override" } : { ...p, state: p.roleDefaultForTechnician ? "granted_by_role" : "not_granted" }
    ),
    technicianDetail: {
      availability: "on_job", activeJobId: "sj_2201", skills: ["Split AC", "Window AC", "Ducted AC"],
      brands: ["Daikin", "Voltas", "LG"], certifications: [{ id: "cert_1", label: "Refrigerant Handling", expiresAt: "2027-03-01T00:00:00Z" }],
      completedJobsCount: 312, rating: 4.7, recentPartsActivityCount: 3,
    },
  },
  {
    id: "tech_4", name: "Divya Prasad", email: "divya@brighthomeservices.example",
    role: "technician", jobTitle: "Plumbing Technician", status: "invited",
    invitedAt: "2026-07-17T12:00:00Z", lastActiveAt: null,
    permissions: FIXTURE_PERMISSION_CATALOG.map((p) => ({ ...p, state: p.roleDefaultForTechnician ? "granted_by_role" : "not_granted" })),
    technicianDetail: {
      availability: "off_duty", activeJobId: null, skills: ["Pipe Fitting", "Leak Repair"],
      brands: [], certifications: [], completedJobsCount: 0, rating: null, recentPartsActivityCount: 0,
    },
  },
];

export const FIXTURE_BOOKINGS: BookingFixture[] = [
  { id: "bk_1001", pipeline: "booking_field_ops", canonicalId: "fo_job_5510", customerName: "Meera Iyer", serviceName: "AC Repair", status: "confirmed", scheduledAt: "2026-07-20T10:00:00Z", address: "14 Indiranagar, Bengaluru", assignedStaffId: "tech_3", cancelSupported: "unresolved_mock_only" },
  { id: "bk_1002", pipeline: "booking_field_ops", canonicalId: "fo_job_5511", customerName: "Suresh Nair", serviceName: "Plumbing Inspection", status: "requested", scheduledAt: "2026-07-21T13:00:00Z", address: "22 Koramangala, Bengaluru", assignedStaffId: null, cancelSupported: "unresolved_mock_only" },
];

export const FIXTURE_SERVICE_JOBS: ServiceJobFixture[] = [
  { id: "sj_2201", pipeline: "service_booking_service_job", canonicalId: "sj_2201", customerName: "Arjun Kumar", serviceName: "Ducted AC Service", status: "in_progress", scheduledAt: "2026-07-19T09:00:00Z", address: "8 HSR Layout, Bengaluru", assignedTechnicianId: "tech_3", quoteId: "q_901", checklistId: "cl_401", partsRequestIds: ["pr_701"], invoiceId: null, commissionBps: 1200, cancelSupported: "unresolved_mock_only" },
  { id: "sj_2202", pipeline: "service_booking_service_job", canonicalId: "sj_2202", customerName: "Neha Gupta", serviceName: "Window AC Install", status: "quoted", scheduledAt: "2026-07-22T11:00:00Z", address: "3 Jayanagar, Bengaluru", assignedTechnicianId: null, quoteId: "q_902", checklistId: null, partsRequestIds: [], invoiceId: null, commissionBps: 1200, cancelSupported: "unresolved_mock_only" },
];

export const FIXTURE_PARTS_REQUESTS: PartsRequestFixture[] = [
  { id: "pr_701", serviceJobId: "sj_2201", requestedByTechnicianId: "tech_3", items: [{ id: "it_1", name: "Copper piping (3m)", qty: 1, unitCost: 850 }, { id: "it_2", name: "Gas refill (R32)", qty: 1, unitCost: 2200 }], status: "requested", decidedByStaffId: null, decidedAt: null },
];

export const FIXTURE_PACKAGE_CREDIT: PackageCreditFixture = {
  planName: "Growth", creditBalance: 18400, creditIssuedThisCycle: 25000, creditConsumedThisCycle: 6600, commissionRateBps: 1200, cycleEndsAt: "2026-08-01T00:00:00Z",
};

export const FIXTURE_SECURITY_DEPOSIT: SecurityDepositFixture = {
  requiredAmount: 25000, heldAmount: 25000, status: "held", lastChangeAt: "2026-06-10T09:00:00Z",
  history: [{ id: "dep_1", type: "hold", amount: 25000, at: "2026-06-10T09:00:00Z", note: "Initial deposit on activation." }],
};

export const FIXTURE_FINANCE_TRANSACTIONS: FinanceTransactionFixture[] = [
  { id: "txn_1", kind: "credit_issue", amount: 25000, at: "2026-07-01T00:00:00Z", relatedJobId: null, note: "Monthly package credit issued." },
  { id: "txn_2", kind: "credit_consume_commission", amount: -1080, at: "2026-07-19T09:40:00Z", relatedJobId: "sj_2201", note: "Commission on job completion (12%)." },
  { id: "txn_3", kind: "deposit_hold", amount: 25000, at: "2026-06-10T09:00:00Z", relatedJobId: null, note: "Security deposit held on activation." },
];

export const FIXTURE_PRICING: PricingFixture[] = [
  { serviceId: "svc_ac_repair", serviceName: "AC Repair", jobType: "Split AC — Gas Refill", brand: "Daikin", zoneId: "zone_blr_east", platformMinPrice: 900, platformMaxPrice: 3500, tenantPrice: 1500, effectivePricePreview: 1500, belowPlatformMin: false },
  { serviceId: "svc_plumbing", serviceName: "Plumbing Inspection", jobType: "Standard Inspection", brand: null, zoneId: "zone_blr_south", platformMinPrice: 400, platformMaxPrice: 1200, tenantPrice: 350, effectivePricePreview: 350, belowPlatformMin: true },
];

export const FIXTURE_SERVICE_AREAS: ServiceAreaFixture[] = [
  { id: "sa_1", city: "Bengaluru", district: "East", postalCode: "560038", zoneId: "zone_blr_east", coverageStatus: "covered", mutationReadiness: "READ_ONLY_READY" },
  { id: "sa_2", city: "Bengaluru", district: "South", postalCode: "560095", zoneId: "zone_blr_south", coverageStatus: "conflict", mutationReadiness: "PRODUCT_DECISION_REQUIRED" },
];

export const FIXTURE_CUSTOMERS: CustomerFixture[] = [
  { id: "cust_1", name: "Arjun Kumar", maskedPhone: "+91 98••••210", maskedEmail: "ar••••@example.com", totalBookings: 3, totalServiceJobs: 5, lastServiceAt: "2026-07-19T09:00:00Z", openComplaintCount: 0 },
  { id: "cust_2", name: "Neha Gupta", maskedPhone: "+91 90••••441", maskedEmail: "ne••••@example.com", totalBookings: 1, totalServiceJobs: 1, lastServiceAt: null, openComplaintCount: 1 },
];

export const FIXTURE_COMPLAINTS: ComplaintFixture[] = [
  { id: "cmp_1", customerId: "cust_2", jobRef: "sj_2202", category: "Quote dispute", status: "open", submittedAt: "2026-07-18T15:00:00Z", providerCanRespond: true },
];

export const FIXTURE_COMPLIANCE: ComplianceItemFixture[] = [
  { id: "comp_1", requirement: "GST Certificate", status: "expiring_soon", documentId: "doc_1", submittedAt: "2025-01-10T00:00:00Z", reviewedAt: "2025-01-14T00:00:00Z", history: [{ id: "h1", at: "2025-01-14T00:00:00Z", actor: "Admin Ops", action: "approved" }] },
  { id: "comp_2", requirement: "Trade License", status: "under_review", documentId: "doc_2", submittedAt: "2026-07-15T00:00:00Z", reviewedAt: null, history: [{ id: "h2", at: "2026-07-15T00:00:00Z", actor: "Ananya Rao", action: "submitted" }] },
];

export const FIXTURE_MEDIA_ASSETS: MediaAssetFixture[] = [
  { id: "media_1", label: "Business Logo", kind: "logo", previewToken: "preview_tok_logo_1", uploadedAt: "2026-06-03T00:00:00Z", sizeLabel: "84 KB" },
  { id: "media_2", label: "Storefront Photo", kind: "gallery", previewToken: "preview_tok_gallery_1", uploadedAt: "2026-06-04T00:00:00Z", sizeLabel: "1.2 MB" },
];

export const FIXTURE_AUDIT_EVENTS: AuditEventFixture[] = [
  { id: "aud_1", at: "2026-07-19T08:30:00Z", actorName: "Ananya Rao", actorRole: "tenant_owner", action: "updated business hours", resource: "settings", result: "success" },
  { id: "aud_2", at: "2026-07-18T17:45:00Z", actorName: "Kiran Shetty", actorRole: "staff", action: "attempted zone edit", resource: "tenant_service_area", result: "denied" },
];

/** Fixture-backed adapter — every method is MOCK_DESIGN_ONLY or
 * READ_ONLY_READY today (see readiness-state-registry.csv). Swap the
 * implementation, not the interface, once a real endpoint is confirmed. */
export const ux03FixtureAdapter: Ux03DataAdapter = {
  async getTenantProfile() { return FIXTURE_TENANT_PROFILE; },
  async listTeamMembers() { return FIXTURE_TEAM_MEMBERS; },
  async getTeamMember(id) { return FIXTURE_TEAM_MEMBERS.find((m) => m.id === id); },
  async listBookings() { return FIXTURE_BOOKINGS; },
  async listServiceJobs() { return FIXTURE_SERVICE_JOBS; },
  async listPartsRequests(serviceJobId) { return FIXTURE_PARTS_REQUESTS.filter((p) => p.serviceJobId === serviceJobId); },
  async getPackageCredit() { return FIXTURE_PACKAGE_CREDIT; },
  async getSecurityDeposit() { return FIXTURE_SECURITY_DEPOSIT; },
  async listFinanceTransactions() { return FIXTURE_FINANCE_TRANSACTIONS; },
  async listPricing() { return FIXTURE_PRICING; },
  async listServiceAreas() { return FIXTURE_SERVICE_AREAS; },
  async listCustomers() { return FIXTURE_CUSTOMERS; },
  async listComplaints() { return FIXTURE_COMPLAINTS; },
  async listComplianceItems() { return FIXTURE_COMPLIANCE; },
  async listMediaAssets() { return FIXTURE_MEDIA_ASSETS; },
  async listAuditEvents() { return FIXTURE_AUDIT_EVENTS; },
};
