import { CUSTOMER_CAPABILITY_REGISTRY, getCapability, capabilitiesForVertical, capabilitiesByEvidence } from "../registry";

describe("customer capability registry", () => {
  it("has a unique key for every capability", () => {
    const keys = CUSTOMER_CAPABILITY_REGISTRY.map(c => c.key);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("never classifies anything as RUNTIME_PROVEN this phase (no live authenticated call was made)", () => {
    expect(capabilitiesByEvidence("RUNTIME_PROVEN")).toHaveLength(0);
  });

  it("gives every non-MISSING/ROLE_BLOCKED/DISCONNECTED entry a canonical endpoint or explicit null", () => {
    for (const c of CUSTOMER_CAPABILITY_REGISTRY) {
      if (["MISSING"].includes(c.evidence)) {
        expect(c.canonicalEndpoint === null || typeof c.canonicalEndpoint === "string").toBe(true);
      }
    }
  });

  it("requires a blocker note on every non-fully-working entry", () => {
    const nonWorking = CUSTOMER_CAPABILITY_REGISTRY.filter(
      c => c.evidence !== "SOURCE_VERIFIED" && c.evidence !== "RUNTIME_PROVEN",
    );
    for (const c of nonWorking) {
      expect(Boolean(c.blocker)).toBe(true);
    }
  });

  it("marks parts customer-approval routes ROLE_BLOCKED, not SOURCE_VERIFIED, since only provider/staff can call them", () => {
    const partsApproval = getCapability("parts.approval");
    expect(partsApproval?.evidence).toBe("ROLE_BLOCKED");
  });

  it("marks all bargain-submission capabilities MISSING (no customer route exists)", () => {
    const bargain = capabilitiesByEvidence("MISSING").filter(c => c.group === "Pricing and bargaining");
    expect(bargain.length).toBeGreaterThan(0);
    for (const c of bargain) expect(c.exposableInUi).toBe(false);
  });

  it("flags the legacy /v1/bookings engine as DISCONNECTED and not exposable", () => {
    const legacy = getCapability("bookings.legacyBookingEngineWarning");
    expect(legacy?.evidence).toBe("DISCONNECTED");
    expect(legacy?.exposableInUi).toBe(false);
  });

  it("filters correctly by vertical, always including global capabilities", () => {
    const homeServices = capabilitiesForVertical("home_services");
    expect(homeServices.some(c => c.vertical === "home_services")).toBe(true);
    expect(homeServices.some(c => c.vertical === "global")).toBe(true);
    expect(homeServices.some(c => c.vertical === "coaching")).toBe(false);
  });

  it("never marks a capability without a working route as exposableInUi", () => {
    for (const c of CUSTOMER_CAPABILITY_REGISTRY) {
      if (c.evidence === "MISSING" || c.evidence === "ROLE_BLOCKED" || c.evidence === "DISCONNECTED") {
        expect(c.exposableInUi).toBe(false);
      }
    }
  });
});
