import { describe, it, expect } from "vitest";
import { FIXTURE_TENANTS, FIXTURE_COMPLIANCE_CASES } from "../../lib/ux02/fixtures";

describe("UX-02 fixtures", () => {
  it("every compliance case references a real fixture tenant id", () => {
    const tenantIds = new Set(FIXTURE_TENANTS.map((t) => t.id));
    for (const c of FIXTURE_COMPLIANCE_CASES) {
      expect(tenantIds.has(c.tenantId)).toBe(true);
    }
  });

  it("tenant package credit and security deposit are tracked as distinct fields", () => {
    for (const t of FIXTURE_TENANTS) {
      expect(typeof t.packageCreditBalance).toBe("number");
      expect(typeof t.securityDepositAmount).toBe("number");
    }
  });
});
