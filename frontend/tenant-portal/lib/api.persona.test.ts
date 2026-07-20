// Slice 2F-6B — direct unit tests for the invoice/payment frontend
// authorization helpers added this slice. Uses Node's built-in test
// runner (node:test / node:assert) since this app has no jest/vitest
// configured (see docs/workflow-rearchitecture/phase-02a-slice-02f6b/
// known-limitations.md) -- no new test dependency was introduced.
//
// Run with: npx tsc lib/api.ts lib/api.persona.test.ts --module commonjs
//   --target es2020 --outDir <tmp> --skipLibCheck --esModuleInterop
//   && node --test <tmp>/api.persona.test.js
// (npx tsx's on-the-fly TS execution was unavailable in this environment
// due to an npm cache-cleanup permission issue on Windows -- unrelated to
// this change; tsc + node --test is the verified working alternative.)
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  isCanonicalStaffRole,
  canManageProviderInvoices,
  canIssueProviderInvoice,
  canOfferProviderComplaintResolution,
  PROVIDER_RESOLUTION_LEGAL_SOURCE_STATES,
} from "./api";

test("isCanonicalStaffRole matches only the canonical staff role", () => {
  assert.equal(isCanonicalStaffRole("staff"), true);
  assert.equal(isCanonicalStaffRole("technician"), false);
  assert.equal(isCanonicalStaffRole("tenant_owner"), false);
  assert.equal(isCanonicalStaffRole("customer"), false);
  assert.equal(isCanonicalStaffRole(undefined), false);
  assert.equal(isCanonicalStaffRole(null), false);
  assert.equal(isCanonicalStaffRole("office_staff"), false);
  assert.equal(isCanonicalStaffRole("manager"), false);
});

test("canManageProviderInvoices: tenant_owner allowed with mutation-capable scope", () => {
  assert.equal(canManageProviderInvoices("tenant_owner", "full_access"), true);
  assert.equal(canManageProviderInvoices("tenant_owner", null), true);
});

test("canManageProviderInvoices: canonical staff allowed with mutation-capable scope", () => {
  assert.equal(canManageProviderInvoices("staff", "full_access"), true);
  assert.equal(canManageProviderInvoices("staff", null), true);
});

test("canManageProviderInvoices: technician denied regardless of scope", () => {
  assert.equal(canManageProviderInvoices("technician", "full_access"), false);
  assert.equal(canManageProviderInvoices("technician", null), false);
});

test("canManageProviderInvoices: customer/guest denied", () => {
  assert.equal(canManageProviderInvoices("customer", "full_access"), false);
  assert.equal(canManageProviderInvoices("guest", "full_access"), false);
});

test("canManageProviderInvoices: read-only access scope denies tenant_owner and staff", () => {
  assert.equal(canManageProviderInvoices("tenant_owner", "customer_support_limited"), false);
  assert.equal(canManageProviderInvoices("staff", "customer_support_limited"), false);
});

test("canManageProviderInvoices: unknown role fails closed", () => {
  assert.equal(canManageProviderInvoices("totally_bogus_role", "full_access"), false);
});

test("canIssueProviderInvoice: tenant_owner allowed with mutation-capable scope", () => {
  assert.equal(canIssueProviderInvoice("tenant_owner", "full_access"), true);
});

test("canIssueProviderInvoice: staff denied (owner-only capability)", () => {
  assert.equal(canIssueProviderInvoice("staff", "full_access"), false);
});

test("canIssueProviderInvoice: technician denied", () => {
  assert.equal(canIssueProviderInvoice("technician", "full_access"), false);
});

test("canIssueProviderInvoice: customer/guest denied", () => {
  assert.equal(canIssueProviderInvoice("customer", "full_access"), false);
  assert.equal(canIssueProviderInvoice("guest", "full_access"), false);
});

test("canIssueProviderInvoice: read-only access scope denies tenant_owner", () => {
  assert.equal(canIssueProviderInvoice("tenant_owner", "customer_support_limited"), false);
});

test("canIssueProviderInvoice: unknown role fails closed", () => {
  assert.equal(canIssueProviderInvoice("some_unknown_role", "full_access"), false);
});

// ── Slice 2F-9B: canOfferProviderComplaintResolution ──────────────────────────
// Exact legal source states (from ALLOWED_TRANSITIONS_EXT, backend-authoritative):
const ALL_STATES = [
  "open", "awaiting_provider_response", "awaiting_customer_response",
  "under_admin_review", "resolution_proposed", "rework_approved",
  "refund_requested", "refund_approved", "refund_recorded",
  "resolved", "settled", "closed", "cancelled", "rejected",
];

test("PROVIDER_RESOLUTION_LEGAL_SOURCE_STATES is exactly the 2 backend-legal states", () => {
  assert.deepEqual(
    [...PROVIDER_RESOLUTION_LEGAL_SOURCE_STATES].sort(),
    ["awaiting_provider_response", "under_admin_review"].sort(),
  );
});

for (const status of ALL_STATES) {
  const legal = (["awaiting_provider_response", "under_admin_review"] as string[]).includes(status);
  test(`canOfferProviderComplaintResolution: tenant_owner + full_access + status=${status} -> ${legal}`, () => {
    assert.equal(canOfferProviderComplaintResolution("tenant_owner", status, "full_access"), legal);
  });
}

test("canOfferProviderComplaintResolution: read-only scope denies even in a legal state", () => {
  assert.equal(canOfferProviderComplaintResolution("tenant_owner", "awaiting_provider_response", "customer_support_limited"), false);
  assert.equal(canOfferProviderComplaintResolution("tenant_owner", "under_admin_review", "customer_support_limited"), false);
});

test("canOfferProviderComplaintResolution: staff denied even in a legal state", () => {
  assert.equal(canOfferProviderComplaintResolution("staff", "awaiting_provider_response", "full_access"), false);
});

test("canOfferProviderComplaintResolution: technician denied even in a legal state", () => {
  assert.equal(canOfferProviderComplaintResolution("technician", "awaiting_provider_response", "full_access"), false);
});

test("canOfferProviderComplaintResolution: customer/guest denied even in a legal state", () => {
  assert.equal(canOfferProviderComplaintResolution("customer", "awaiting_provider_response", "full_access"), false);
  assert.equal(canOfferProviderComplaintResolution("guest", "awaiting_provider_response", "full_access"), false);
});

test("canOfferProviderComplaintResolution: unknown role fails closed even in a legal state", () => {
  assert.equal(canOfferProviderComplaintResolution("totally_bogus_role", "awaiting_provider_response", "full_access"), false);
});

test("canOfferProviderComplaintResolution: unknown access scope value does not bypass -- only exact scope string denies, but role+state still gate correctly", () => {
  assert.equal(canOfferProviderComplaintResolution("tenant_owner", "awaiting_provider_response", "some_unrecognized_scope"), true);
  assert.equal(canOfferProviderComplaintResolution("staff", "awaiting_provider_response", "some_unrecognized_scope"), false);
});

test("canOfferProviderComplaintResolution: missing status fails closed", () => {
  assert.equal(canOfferProviderComplaintResolution("tenant_owner", null, "full_access"), false);
  assert.equal(canOfferProviderComplaintResolution("tenant_owner", undefined, "full_access"), false);
  assert.equal(canOfferProviderComplaintResolution("tenant_owner", "", "full_access"), false);
});

test("canOfferProviderComplaintResolution: unknown/unrecognized status fails closed", () => {
  assert.equal(canOfferProviderComplaintResolution("tenant_owner", "some_made_up_status", "full_access"), false);
});
