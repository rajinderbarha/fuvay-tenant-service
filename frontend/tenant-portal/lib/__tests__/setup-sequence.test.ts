import { expect, it } from "vitest";
import type { HomeServicesSetupOverview } from "../api";
import { SETUP_STEPS, setupPrerequisite } from "../setup-sequence";

function overview(completed: number, status = "draft_setup") {
  return { vertical: { status }, sections: SETUP_STEPS.map(([key], index) => ({ key, status: index < completed ? "complete" : "not_started" })) } as HomeServicesSetupOverview;
}

it("allows each next step only after all preceding steps are complete", () => {
  for (let done = 0; done < SETUP_STEPS.length; done++) {
    for (let target = 0; target < SETUP_STEPS.length; target++) {
      const blocker = setupPrerequisite(overview(done), SETUP_STEPS[target][1]);
      if (target <= done) expect(blocker).toBeNull();
      else expect(blocker?.key).toBe(SETUP_STEPS[done][0]);
    }
  }
});
it("fails closed for later direct URLs without an overview, while allowing profile and overview", () => {
  expect(setupPrerequisite(null, "review")?.key).toBe("BUSINESS_PROFILE");
  expect(setupPrerequisite(null, "business-profile")).toBeNull();
  expect(setupPrerequisite(null, "overview")).toBeNull();
});
it("does not gate operational editing for active tenants", () => {
  expect(setupPrerequisite(overview(0, "active"), "staff")).toBeNull();
});
