import { expect, it } from "vitest";
import { namedJobType, preferredJobType } from "./service-family";
it("opens Installation for AC Installation instead of the first Service tab", () => {
  const links = [{ job_type_id: "service", job_type: { key: "service" } }, { job_type_id: "install", job_type: { key: "installation" } }];
  expect(preferredJobType("AC Installation", links)).toBe("install");
  expect(preferredJobType("Air Conditioner", links)).toBe("service");
  expect(preferredJobType("New family", [])).toBeNull();
});
it("does not infer job types from family names or words within a name", () => {
  expect(namedJobType("AC Services")).toBeNull();
  expect(namedJobType("Installation Equipment")).toBeNull();
  expect(namedJobType("Geyser Repair")).toBe("repair");
  expect(namedJobType("AC Uninstallation")).toBe("uninstallation");
});
