import { describe, expect, it } from "vitest";
import { dispatchUrlForAvailabilityJob } from "./availabilityNavigation";

describe("Availability to Dispatch navigation", () => {
  it("opens the selected job on the selected day", () => {
    expect(dispatchUrlForAvailabilityJob("2026-09-14", "job-123"))
      .toBe("/home-services/dispatch?date=2026-09-14&job_id=job-123");
  });
});
