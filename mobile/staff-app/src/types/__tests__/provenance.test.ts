import type { JobProvenanceView, PartsRequestStatusView } from "../ux05";

describe("JobProvenanceView", () => {
  it("carries distinct sourceBookingId and jobId (never collapsed)", () => {
    const p: JobProvenanceView = {
      pipeline: "service_booking_service_job",
      sourceBookingId: "bk_123",
      jobId: "sj_456",
      jobModel: "ServiceJob",
    };
    expect(p.sourceBookingId).not.toBe(p.jobId);
    expect(p.jobModel).toBe("ServiceJob");
  });

  it("only ever types the pipeline literal that has real live data", () => {
    const p: JobProvenanceView = {
      pipeline: "service_booking_service_job", sourceBookingId: "bk_1", jobId: "sj_1", jobModel: "ServiceJob",
    };
    // @ts-expect-error -- "booking_field_ops" must not compile here; field_ops has 0 rows platform-wide (MODULE-L5-36)
    p.pipeline = "booking_field_ops";
  });
});

describe("PartsRequestStatusView technician-action restriction", () => {
  it("only allows add_note in the type -- approve/reject/mark_installed are not assignable", () => {
    const view: PartsRequestStatusView = {
      meta: { readiness: "production_ready" }, id: "pr_1", jobId: "sj_1", partName: "Capacitor",
      quantity: 1, requestedAt: "2026-07-18", note: null, providerResponse: null,
      state: "requested", technicianActions: ["add_note"],
    };
    expect(view.technicianActions).toEqual(["add_note"]);
    // @ts-expect-error -- "approve" is not a valid technicianActions member
    view.technicianActions = ["approve"];
  });
});
