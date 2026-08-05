import { resolvePrivacyRequestPresentation } from "../privacyRequestPresentation";
import { PrivacyRequest } from "../privacyData";
import { ServerTimestamp } from "../dates";

function request(overrides: Partial<PrivacyRequest> = {}): PrivacyRequest {
  return {
    id: "r-1", requestNumber: "COMP-1", requestType: "right_to_erasure",
    status: "submitted", statusLabel: "Submitted", slaStatus: "on_track", slaLabel: "On Track",
    verificationStatus: "not_required",
    submittedAt: "2026-01-01T00:00:00Z" as ServerTimestamp, dueAt: null, completedAt: null,
    reason: "test", rejectionReason: null,
    createdAt: "2026-01-01T00:00:00Z" as ServerTimestamp, updatedAt: null,
    ...overrides,
  };
}

describe("resolvePrivacyRequestPresentation", () => {
  it.each([
    ["submitted", "Submitted", "info", false, true],
    ["identity_verification_pending", "Additional verification required", "warning", false, true],
    ["under_review", "Under review", "warning", false, true],
    ["approved", "Approved", "success", false, true],
    ["partially_approved", "Partially approved", "success", false, true],
    ["processing", "Processing", "info", false, true],
    ["completed", "Completed", "success", true, false],
    ["rejected", "Rejected", "danger", true, false],
    ["failed", "Needs attention", "danger", false, true],
    ["cancelled", "Withdrawn", "neutral", true, false],
    ["sla_breached", "Delayed", "warning", false, true],
  ] as const)("maps status '%s' to title '%s'", (status, title, tone, isTerminal, isRefreshMeaningful) => {
    const p = resolvePrivacyRequestPresentation(request({ status }));
    expect(p.title).toBe(title);
    expect(p.tone).toBe(tone);
    expect(p.isTerminal).toBe(isTerminal);
    expect(p.isRefreshMeaningful).toBe(isRefreshMeaningful);
  });

  it("falls back to a safe neutral 'Status unavailable' for an unrecognized status", () => {
    const p = resolvePrivacyRequestPresentation(request({ status: "some_future_status_v2" }));
    expect(p.title).toBe("Status unavailable");
    expect(p.tone).toBe("neutral");
    expect(p.canWithdraw).toBe(false);
    expect(p.canDownloadExport).toBe(false);
  });

  it("maps every confirmed request type to a customer-safe label", () => {
    expect(resolvePrivacyRequestPresentation(request({ requestType: "right_to_erasure" })).typeLabel).toBe("Account deletion");
    expect(resolvePrivacyRequestPresentation(request({ requestType: "data_export" })).typeLabel).toBe("Data export");
    expect(resolvePrivacyRequestPresentation(request({ requestType: "consent_withdrawal" })).typeLabel).toBe("Consent withdrawal");
    expect(resolvePrivacyRequestPresentation(request({ requestType: "grievance" })).typeLabel).toBe("Grievance");
  });

  it("falls back to a generic type label for an unrecognized request type", () => {
    const p = resolvePrivacyRequestPresentation(request({ requestType: "future_type" as never }));
    expect(p.typeLabel).toBe("Privacy request");
  });

  it("allows withdrawal only while submitted or identity_verification_pending", () => {
    expect(resolvePrivacyRequestPresentation(request({ status: "submitted" })).canWithdraw).toBe(true);
    expect(resolvePrivacyRequestPresentation(request({ status: "identity_verification_pending" })).canWithdraw).toBe(true);
    expect(resolvePrivacyRequestPresentation(request({ status: "under_review" })).canWithdraw).toBe(false);
    expect(resolvePrivacyRequestPresentation(request({ status: "completed" })).canWithdraw).toBe(false);
  });

  it("allows export download only when the export is ready and not expired", () => {
    const ready = request({
      requestType: "data_export", status: "completed",
      export: { exportId: "e-1", status: "ready", expiresAt: null, isExpired: false },
    });
    expect(resolvePrivacyRequestPresentation(ready).canDownloadExport).toBe(true);

    const expired = request({
      requestType: "data_export", status: "completed",
      export: { exportId: "e-1", status: "expired", expiresAt: null, isExpired: true },
    });
    expect(resolvePrivacyRequestPresentation(expired).canDownloadExport).toBe(false);

    const noExport = request({ requestType: "data_export", status: "completed" });
    expect(resolvePrivacyRequestPresentation(noExport).canDownloadExport).toBe(false);

    const wrongType = request({
      requestType: "right_to_erasure", status: "completed",
      export: { exportId: "e-1", status: "ready", expiresAt: null, isExpired: false },
    });
    expect(resolvePrivacyRequestPresentation(wrongType).canDownloadExport).toBe(false);
  });
});
