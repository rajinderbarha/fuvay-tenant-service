import { describe, it, expect } from "vitest";
import { jobProvenanceFixture, fieldOpsJobDetailFixture, jobDetailFixture, bookingListFixture } from "../fixtures";

describe("UX-04B ServiceBooking provenance contract", () => {
  it("ServiceBooking id and ServiceJob id are both present and never equal", () => {
    const { sourceBookingId, resultingServiceJobId } = jobProvenanceFixture.source;
    expect(sourceBookingId).toBeTruthy();
    expect(resultingServiceJobId).toBeTruthy();
    expect(sourceBookingId).not.toBe(resultingServiceJobId);
  });

  it("source model is always service_booking and resulting model is always service_job — never substituted", () => {
    expect(jobProvenanceFixture.source.sourceModel).toBe("service_booking");
    expect(jobProvenanceFixture.source.resultingModel).toBe("service_job");
  });

  it("pipeline labels stay distinct between field_ops.Job and ServiceJob fixtures", () => {
    expect(fieldOpsJobDetailFixture.job.pipeline).toBe("booking_field_ops");
    expect(jobDetailFixture.job.pipeline).toBe("service_booking_service_job");
    expect(fieldOpsJobDetailFixture.job.pipeline).not.toBe(jobDetailFixture.job.pipeline);
  });

  it("ServiceJob-only sections are declared explicitly and never attached to a field_ops.Job/Booking view", () => {
    expect(jobProvenanceFixture.serviceJobOnlySections).toEqual(
      expect.arrayContaining(["quote", "checklist", "partsRequests", "invoice", "creditCommission"])
    );
    // field_ops.Job detail view type has no such fields at all — structural
    // proof, not just a runtime check: these keys must not exist on the object.
    for (const key of jobProvenanceFixture.serviceJobOnlySections) {
      expect(Object.keys(fieldOpsJobDetailFixture)).not.toContain(key);
    }
  });

  it("Booking (field_ops.Job pipeline) fixtures never carry ServiceBooking metadata", () => {
    for (const row of bookingListFixture) {
      expect(Object.keys(row.booking)).not.toContain("sourceBookingId");
      expect(Object.keys(row.booking)).not.toContain("resultingServiceJobId");
    }
  });
});
