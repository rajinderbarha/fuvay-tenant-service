import { resolvePartsPresentationKind, resolvePartsPresentation } from "../partsApprovalPresentation";

describe("resolvePartsPresentationKind", () => {
  it("maps the real customer-visible statuses correctly", () => {
    expect(resolvePartsPresentationKind("customer_approval_pending")).toBe("actionable");
    expect(resolvePartsPresentationKind("business_approved")).toBe("informational");
    expect(resolvePartsPresentationKind("installed")).toBe("informational");
    expect(resolvePartsPresentationKind("customer_approved")).toBe("approved");
    expect(resolvePartsPresentationKind("customer_rejected")).toBe("declined");
  });

  it("fails safe to unavailable for internal-only or unrecognized statuses", () => {
    expect(resolvePartsPresentationKind("requested")).toBe("unavailable");
    expect(resolvePartsPresentationKind("business_rejected")).toBe("unavailable");
    expect(resolvePartsPresentationKind("some_future_status")).toBe("unavailable");
    expect(resolvePartsPresentationKind(null)).toBe("unavailable");
  });
});

describe("resolvePartsPresentation", () => {
  it("never labels tenant approval as customer consent for the informational kind", () => {
    const p = resolvePartsPresentation("informational");
    expect(p.explanation).not.toMatch(/you approved|your approval/i);
  });

  it("never implies action is still needed once declined", () => {
    const p = resolvePartsPresentation("declined");
    expect(p.explanation).not.toMatch(/review|approve/i);
  });
});
