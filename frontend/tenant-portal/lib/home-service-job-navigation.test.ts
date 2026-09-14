import { describe, expect, it } from "vitest";
import { canManageJobInDispatch, completedJobReviewUrl, providerJobWorkspaceUrl } from "./home-service-job-navigation";

describe("provider job navigation", () => {
  it.each(["completed", "cancelled", "failed", "closed_estimate_declined"])(
    "never sends a %s job to Dispatch, even with a stale stage flag",
    status => expect(canManageJobInDispatch(status, false)).toBe(false),
  );

  it("uses the backend terminal flag and keeps active jobs actionable", () => {
    expect(canManageJobInDispatch("scheduled", true)).toBe(false);
    expect(canManageJobInDispatch("scheduled", false)).toBe(true);
  });

  it("links only completed jobs to their review lookup", () => {
    expect(completedJobReviewUrl("completed", "JOB-20260912-000006"))
      .toBe("/home-services/reviews?search=JOB-20260912-000006");
    expect(completedJobReviewUrl("scheduled", "JOB-20260912-000006")).toBeNull();
  });

  it("opens a provider job in the supported bookings workspace", () => {
    expect(providerJobWorkspaceUrl("f5b9d779-d915-4e3d-9764-65547a89fdc6"))
      .toBe("/home-services/bookings-jobs?job_id=f5b9d779-d915-4e3d-9764-65547a89fdc6");
  });
});
