/**
 * DESIGN PHASE UX-02 — Super Admin shared types.
 *
 * These are UI-layer types for the UX-02 foundation work only. They are NOT
 * a second source of truth for backend contracts. Anything shaped like a
 * real ServiceOS entity here (tenant, verification submission, compliance
 * case, etc.) is a design fixture until a real API contract is confirmed —
 * see docs/design/ux-02-super-admin/backend-contract-dependencies.md.
 *
 * Canonical admin roles — never invent additional role names:
 */
export type CanonicalAdminRole =
  | "super_admin"
  | "admin_operations"
  | "admin_finance"
  | "admin_security"
  | "admin_readonly";

/**
 * Dev-only metadata describing how real/ready a page or action is.
 * NEVER rendered to real users — dev-showcase and internal docs only.
 */
export type ReadinessState =
  | "PRODUCTION_READY"
  | "READ_ONLY_READY"
  | "MOCK_DESIGN_ONLY"
  | "API_CONTRACT_REQUIRED"
  | "SECURITY_CONTRACT_PENDING"
  | "PRODUCT_DECISION_REQUIRED"
  | "DEPRECATED"
  | "NOT_APPLICABLE";

/** Security-observation status language — never overstate a static
 * observation as a confirmed live incident. */
export type SecurityObservationStatus =
  | "observation"
  | "needs_verification"
  | "confirmed_finding"
  | "investigating"
  | "action_required"
  | "remediated"
  | "false_positive"
  | "product_policy_blocked";

export interface TenantFixture {
  id: string;
  legalName: string;
  displayName: string;
  ownerName: string;
  ownerEmail: string;
  vertical: "home_services" | "real_estate" | "coaching";
  status: "active" | "suspended" | "pending_verification" | "onboarding" | "deactivated";
  planPackage: string;
  packageCreditBalance: number; // platform package credit, NOT job payments
  commissionRateBps: number;
  securityDepositAmount: number;
  storageQuotaGb: number;
  storageUsedGb: number;
  city: string;
  region: string;
  createdAt: string;
  lastActivityAt: string;
  riskScore: "low" | "medium" | "high";
  openComplaints: number;
  staffCount: number;
}

export interface VerificationSubmissionFixture {
  id: string;
  tenantId: string;
  applicantName: string;
  submittedAt: string;
  documents: { id: string; label: string; kind: string; previewToken: string }[];
  checklist: { id: string; label: string; status: "pending" | "pass" | "fail" }[];
  status: "pending" | "approved" | "rejected" | "more_info_requested";
}

export interface ComplianceCaseFixture {
  id: string;
  tenantId: string;
  title: string;
  category: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "open" | "in_review" | "resolved" | "escalated";
  openedAt: string;
  assignedTo: string;
}

export interface SecurityObservationFixture {
  id: string;
  title: string;
  status: SecurityObservationStatus;
  detectedAt: string;
  actor: string;
  ipMasked: string;
  correlationId: string;
  riskLevel: "low" | "medium" | "high";
}

export interface AuditEntryFixture {
  id: string;
  timestamp: string;
  actor: string;
  role: CanonicalAdminRole;
  tenantId: string | null;
  action: string;
  resource: string;
  result: "success" | "failure" | "denied";
  ipDevice: string;
  correlationId: string;
  risk: "low" | "medium" | "high";
  detailsRedacted: Record<string, unknown>;
}

export interface PlatformNoticeFixture {
  id: string;
  title: string;
  body: string;
  severity: "info" | "warning" | "critical";
  createdAt: string;
}

/** Typed adapter interface — no real search API wired yet (MOCK_DESIGN_ONLY). */
export interface CommandPaletteAdapter {
  search(query: string): Promise<{ id: string; label: string; group: string; href: string }[]>;
}

/** Typed adapter interface for future production data — every current
 * implementation is fixture-backed until a real endpoint is confirmed. */
export interface Ux02DataAdapter {
  listTenants(): Promise<TenantFixture[]>;
  getTenant(id: string): Promise<TenantFixture | undefined>;
  listVerificationSubmissions(): Promise<VerificationSubmissionFixture[]>;
  listComplianceCases(): Promise<ComplianceCaseFixture[]>;
  listSecurityObservations(): Promise<SecurityObservationFixture[]>;
  listAuditEntries(): Promise<AuditEntryFixture[]>;
}
