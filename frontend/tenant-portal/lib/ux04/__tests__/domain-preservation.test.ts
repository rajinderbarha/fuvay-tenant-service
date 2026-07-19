import { describe, it, expect } from "vitest";
import { bookingListFixture, jobListFixture, partsRequestFixture } from "../fixtures";

describe("UX-04A domain identity preservation", () => {
  it("every booking row is pipeline booking_field_ops with a field_ops.Job canonicalId format", () => {
    for (const row of bookingListFixture) {
      expect(row.booking.pipeline).toBe("booking_field_ops");
      expect(row.booking.canonicalId).toMatch(/^fo_job_/);
      expect(row.booking.cancelSupported).toBe("unresolved_mock_only");
    }
  });

  it("every job row is pipeline service_booking_service_job with a ServiceJob canonicalId format", () => {
    for (const row of jobListFixture) {
      expect(row.job.pipeline).toBe("service_booking_service_job");
      expect(row.job.canonicalId).toMatch(/^service_job_/);
      expect(row.job.cancelSupported).toBe("unresolved_mock_only");
    }
  });

  it("PartsRequest is ServiceJob-scoped only — never carries a field_ops.Job id", () => {
    expect(partsRequestFixture.request.serviceJobId).toMatch(/^sj_/);
    expect(Object.keys(partsRequestFixture.request)).not.toContain("fieldOpsJobId");
  });

  it("no fixture or type references the legacy /v1/reviews endpoint", () => {
    const serialized = JSON.stringify({ bookingListFixture, jobListFixture, partsRequestFixture });
    expect(serialized).not.toMatch(/\/v1\/reviews/);
  });
});
