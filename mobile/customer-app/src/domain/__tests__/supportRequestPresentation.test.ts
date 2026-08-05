import { resolveSupportRequestPresentation, canCancelSupportRequest } from "../supportRequestPresentation";
import { SupportRequest } from "../supportRequests";
import { ServerTimestamp } from "../dates";

function request(overrides: Partial<SupportRequest> = {}): SupportRequest {
  return {
    id: "c-1", complaintNumber: "CMP-1", recordType: "service_booking", recordId: "b-1",
    bookingId: "b-1", complaintType: "service_quality", status: "open",
    title: null, description: "test", requestedResolution: null, customerVisibleSummary: null,
    createdAt: "2026-01-01T00:00:00Z" as ServerTimestamp, updatedAt: null, resolvedAt: null, closedAt: null,
    ...overrides,
  };
}

describe("resolveSupportRequestPresentation", () => {
  it.each([
    ["open", "Open", "info", false],
    ["awaiting_provider_response", "Waiting on provider", "warning", false],
    ["awaiting_customer_response", "Waiting on you", "warning", false],
    ["under_admin_review", "Under review", "warning", false],
    ["resolution_proposed", "Resolution proposed", "info", false],
    ["rework_approved", "Rework approved", "success", false],
    ["refund_requested", "Refund requested", "info", false],
    ["refund_approved", "Refund approved", "success", false],
    ["refund_recorded", "Refund recorded", "success", false],
    ["rejected", "Rejected", "danger", true],
    ["resolved", "Resolved", "success", false],
    ["closed", "Closed", "neutral", true],
    ["cancelled", "Cancelled", "neutral", true],
  ] as const)("maps status '%s' to label '%s'", (status, label, tone, isTerminal) => {
    const p = resolveSupportRequestPresentation(request({ status }));
    expect(p.statusLabel).toBe(label);
    expect(p.tone).toBe(tone);
    expect(p.isTerminal).toBe(isTerminal);
  });

  it("falls back to a safe neutral label for an unrecognized status, never the raw value", () => {
    const p = resolveSupportRequestPresentation(request({ status: "some_future_status" }));
    expect(p.statusLabel).toBe("Status unavailable");
    expect(p.tone).toBe("neutral");
  });

  it("maps confirmed complaint types to customer-safe labels", () => {
    expect(resolveSupportRequestPresentation(request({ complaintType: "late_arrival" })).typeLabel).toBe("Late arrival");
    expect(resolveSupportRequestPresentation(request({ complaintType: "safety_concern" })).typeLabel).toBe("Safety concern");
  });

  it("falls back to a generic type label for an unrecognized complaint type", () => {
    expect(resolveSupportRequestPresentation(request({ complaintType: "invented_type" })).typeLabel).toBe("Support request");
  });
});

describe("canCancelSupportRequest", () => {
  it("allows cancellation only from 'open', matching the real backend state machine", () => {
    expect(canCancelSupportRequest("open")).toBe(true);
    expect(canCancelSupportRequest("awaiting_provider_response")).toBe(false);
    expect(canCancelSupportRequest("under_admin_review")).toBe(false);
    expect(canCancelSupportRequest("resolved")).toBe(false);
    expect(canCancelSupportRequest("closed")).toBe(false);
  });
});
