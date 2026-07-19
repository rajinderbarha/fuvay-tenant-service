/**
 * DESIGN PHASE UX-02 — typed fixture data.
 *
 * Realistic ServiceOS-shaped data for design/dev-showcase purposes only.
 * No lorem ipsum, no real production URLs, no real secrets. Every value is
 * synthetic. See docs/design/ux-02-super-admin/typed-fixture-contract.md.
 */
import type {
  TenantFixture,
  VerificationSubmissionFixture,
  ComplianceCaseFixture,
  SecurityObservationFixture,
  AuditEntryFixture,
  PlatformNoticeFixture,
} from "./types";

export const FIXTURE_TENANTS: TenantFixture[] = [
  {
    id: "tn_2201", legalName: "Blue Ridge Home Services LLC", displayName: "Blue Ridge Home Services",
    ownerName: "Maria Novak", ownerEmail: "maria.novak@blueridge-example.test", vertical: "home_services",
    status: "active", planPackage: "Growth", packageCreditBalance: 4200, commissionRateBps: 1200,
    securityDepositAmount: 5000, storageQuotaGb: 50, storageUsedGb: 18.4, city: "Asheville", region: "NC",
    createdAt: "2025-11-02T10:00:00Z", lastActivityAt: "2026-07-18T14:22:00Z", riskScore: "low",
    openComplaints: 1, staffCount: 14,
  },
  {
    id: "tn_2202", legalName: "Summit Realty Partners", displayName: "Summit Realty",
    ownerName: "Dev Patel", ownerEmail: "dev.patel@summitrealty-example.test", vertical: "real_estate",
    status: "pending_verification", planPackage: "Starter", packageCreditBalance: 0, commissionRateBps: 800,
    securityDepositAmount: 2000, storageQuotaGb: 20, storageUsedGb: 0.6, city: "Denver", region: "CO",
    createdAt: "2026-07-10T09:00:00Z", lastActivityAt: "2026-07-17T08:00:00Z", riskScore: "medium",
    openComplaints: 0, staffCount: 3,
  },
  {
    id: "tn_2203", legalName: "Coastal Coaching Collective", displayName: "Coastal Coaching",
    ownerName: "Renee Ibarra", ownerEmail: "renee.ibarra@coastalcoaching-example.test", vertical: "coaching",
    status: "active", planPackage: "Pro", packageCreditBalance: 9100, commissionRateBps: 1000,
    securityDepositAmount: 3000, storageQuotaGb: 100, storageUsedGb: 61.2, city: "San Diego", region: "CA",
    createdAt: "2025-05-14T10:00:00Z", lastActivityAt: "2026-07-19T02:11:00Z", riskScore: "low",
    openComplaints: 3, staffCount: 22,
  },
  {
    id: "tn_2204", legalName: "Harborline Repairs Inc.", displayName: "Harborline Repairs",
    ownerName: "Chen Wu", ownerEmail: "chen.wu@harborline-example.test", vertical: "home_services",
    status: "suspended", planPackage: "Growth", packageCreditBalance: 120, commissionRateBps: 1200,
    securityDepositAmount: 5000, storageQuotaGb: 50, storageUsedGb: 41.9, city: "Portland", region: "OR",
    createdAt: "2024-09-22T10:00:00Z", lastActivityAt: "2026-06-30T11:40:00Z", riskScore: "high",
    openComplaints: 7, staffCount: 9,
  },
  {
    id: "tn_2205", legalName: "Prairie Field Ops LLC", displayName: "Prairie Field Ops",
    ownerName: "Sam Okafor", ownerEmail: "sam.okafor@prairiefieldops-example.test", vertical: "home_services",
    status: "onboarding", planPackage: "Starter", packageCreditBalance: 0, commissionRateBps: 900,
    securityDepositAmount: 2000, storageQuotaGb: 20, storageUsedGb: 0.1, city: "Omaha", region: "NE",
    createdAt: "2026-07-15T10:00:00Z", lastActivityAt: "2026-07-15T10:00:00Z", riskScore: "low",
    openComplaints: 0, staffCount: 1,
  },
];

export const FIXTURE_VERIFICATIONS: VerificationSubmissionFixture[] = [
  {
    id: "vf_9001", tenantId: "tn_2202", applicantName: "Dev Patel", submittedAt: "2026-07-10T09:20:00Z",
    documents: [
      { id: "doc_1", label: "Business License", kind: "license", previewToken: "preview_tok_9001a" },
      { id: "doc_2", label: "Proof of Insurance", kind: "insurance", previewToken: "preview_tok_9001b" },
    ],
    checklist: [
      { id: "ck_1", label: "Business license matches legal name", status: "pass" },
      { id: "ck_2", label: "Insurance coverage meets minimum", status: "pending" },
      { id: "ck_3", label: "Owner identity verified", status: "pending" },
    ],
    status: "pending",
  },
  {
    id: "vf_9002", tenantId: "tn_2205", applicantName: "Sam Okafor", submittedAt: "2026-07-15T10:05:00Z",
    documents: [{ id: "doc_3", label: "Business License", kind: "license", previewToken: "preview_tok_9002a" }],
    checklist: [
      { id: "ck_4", label: "Business license matches legal name", status: "pending" },
      { id: "ck_5", label: "Insurance coverage meets minimum", status: "fail" },
    ],
    status: "more_info_requested",
  },
];

export const FIXTURE_COMPLIANCE_CASES: ComplianceCaseFixture[] = [
  { id: "cc_501", tenantId: "tn_2204", title: "Repeated no-show complaints", category: "service_quality", severity: "high", status: "escalated", openedAt: "2026-06-20T00:00:00Z", assignedTo: "admin_operations:jane.k" },
  { id: "cc_502", tenantId: "tn_2203", title: "Customer data access request delay", category: "privacy", severity: "medium", status: "in_review", openedAt: "2026-07-05T00:00:00Z", assignedTo: "admin_security:leo.m" },
  { id: "cc_503", tenantId: "tn_2201", title: "Duplicate invoice reported by customer", category: "billing", severity: "low", status: "open", openedAt: "2026-07-16T00:00:00Z", assignedTo: "admin_finance:priya.s" },
];

export const FIXTURE_SECURITY_OBSERVATIONS: SecurityObservationFixture[] = [
  { id: "so_701", title: "Multiple failed admin logins from new device fingerprint", status: "needs_verification", detectedAt: "2026-07-19T03:12:00Z", actor: "admin_operations:jane.k", ipMasked: "203.0.113.x", correlationId: "corr_701a", riskLevel: "medium" },
  { id: "so_702", title: "Elevated permission grant outside change window", status: "confirmed_finding", detectedAt: "2026-07-18T22:40:00Z", actor: "super_admin:root", ipMasked: "198.51.100.x", correlationId: "corr_702a", riskLevel: "high" },
  { id: "so_703", title: "Static-analysis: unused export-permission key detected", status: "observation", detectedAt: "2026-07-17T09:00:00Z", actor: "system:ci", ipMasked: "n/a", correlationId: "corr_703a", riskLevel: "low" },
];

export const FIXTURE_AUDIT_ENTRIES: AuditEntryFixture[] = [
  { id: "ae_1001", timestamp: "2026-07-19T03:12:05Z", actor: "jane.k", role: "admin_operations", tenantId: "tn_2204", action: "tenant.suspend", resource: "tenant:tn_2204", result: "success", ipDevice: "203.0.113.x / Chrome-Win", correlationId: "corr_701a", risk: "medium", detailsRedacted: { reason: "[redacted]", previousStatus: "active" } },
  { id: "ae_1002", timestamp: "2026-07-18T22:41:10Z", actor: "root", role: "super_admin", tenantId: null, action: "permission.grant", resource: "role:admin_operations", result: "success", ipDevice: "198.51.100.x / API", correlationId: "corr_702a", risk: "high", detailsRedacted: { grantedPermission: "[redacted]" } },
  { id: "ae_1003", timestamp: "2026-07-16T14:02:00Z", actor: "priya.s", role: "admin_finance", tenantId: "tn_2201", action: "invoice.review", resource: "invoice:inv_88123", result: "success", ipDevice: "192.0.2.x / macOS-Safari", correlationId: "corr_601a", risk: "low", detailsRedacted: {} },
];

export const FIXTURE_PLATFORM_NOTICES: PlatformNoticeFixture[] = [
  { id: "pn_1", title: "Scheduled maintenance window", body: "Notification dispatch worker restart planned 2026-07-20 02:00 UTC.", severity: "info", createdAt: "2026-07-19T01:00:00Z" },
  { id: "pn_2", title: "3 tenants above 90% storage quota", body: "Review storage quota page for affected tenants.", severity: "warning", createdAt: "2026-07-19T06:00:00Z" },
];
