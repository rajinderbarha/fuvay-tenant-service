import {
  parseLoginOutcome, isMfaChallenge, adaptMfaChallenge, adaptSessionResult,
  parseAccessContext, adaptCustomerSessionContext, isValidCustomerSession,
} from "../authAdapters";
import { ContractValidationError } from "../../../domain/errors";

describe("authAdapters", () => {
  it("parses and identifies an MFA-challenge outcome", () => {
    const outcome = parseLoginOutcome({ mfa_required: true, mfa_challenge_token: "chal-1" });
    expect(isMfaChallenge(outcome)).toBe(true);
    if (isMfaChallenge(outcome)) {
      expect(adaptMfaChallenge(outcome)).toEqual({ status: "challenge_required", challengeToken: "chal-1" });
    }
  });

  it("parses and adapts a full session-result outcome", () => {
    const outcome = parseLoginOutcome({
      mfa_required: false,
      access_token: "acc-1",
      refresh_token: "ref-1",
      user: { id: "customer-1", role: "customer" },
    });
    expect(isMfaChallenge(outcome)).toBe(false);
    if (!isMfaChallenge(outcome)) {
      const session = adaptSessionResult(outcome);
      expect(session.accessToken).toBe("acc-1");
      expect(session.customerId).toBe("customer-1");
    }
  });

  it("rejects a session-result outcome with an empty access token", () => {
    const outcome = parseLoginOutcome({
      mfa_required: false, access_token: "acc", refresh_token: "ref", user: { id: "c1", role: "customer" },
    });
    if (!isMfaChallenge(outcome)) {
      const forcedEmpty = { ...outcome, access_token: "" };
      expect(() => adaptSessionResult(forcedEmpty)).toThrow(ContractValidationError);
    }
  });

  it("rejects a malformed login outcome (missing every recognized shape)", () => {
    expect(() => parseLoginOutcome({ unexpected: true })).toThrow(ContractValidationError);
  });

  it("accepts a valid customer access-context and marks the session valid", () => {
    const dto = parseAccessContext({
      user_id: "customer-1", canonical_role: "customer", audience: "serviceos:customer",
      tenant_id: null, tenant_status: null, technician_id: null, technician_status: null,
      enabled_verticals: [], capabilities: [],
    });
    const ctx = adaptCustomerSessionContext(dto);
    expect(isValidCustomerSession(ctx)).toBe(true);
    expect(ctx.customerId).toBe("customer-1");
  });

  it("rejects a staff-audience access-context as an invalid customer session", () => {
    const dto = parseAccessContext({
      user_id: "staff-1", canonical_role: "staff", audience: "serviceos:staff",
      tenant_id: "tenant-1", tenant_status: "active", technician_id: null, technician_status: null,
      enabled_verticals: ["home_services"], capabilities: [],
    });
    const ctx = adaptCustomerSessionContext(dto);
    expect(isValidCustomerSession(ctx)).toBe(false);
    expect(ctx.customerId).toBeNull();
  });

  it("rejects a technician-audience access-context even if role happens to be miscategorized", () => {
    const dto = parseAccessContext({
      user_id: "tech-1", canonical_role: "technician", audience: "serviceos:staff",
      tenant_id: "tenant-1", tenant_status: "active", technician_id: "tech-1", technician_status: "active",
      enabled_verticals: ["home_services"], capabilities: [],
    });
    expect(isValidCustomerSession(adaptCustomerSessionContext(dto))).toBe(false);
  });
});
