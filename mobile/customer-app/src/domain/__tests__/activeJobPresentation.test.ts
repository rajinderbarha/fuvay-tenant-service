import {
  resolveActiveJobStage, resolveActiveJobPresentation, resolveJobProgressStepState, formatScheduleWindow,
} from "../activeJobPresentation";

describe("resolveActiveJobStage", () => {
  it("recognizes the three stages this phase owns", () => {
    expect(resolveActiveJobStage("assignment")).toBe("assignment");
    expect(resolveActiveJobStage("scheduled")).toBe("scheduled");
    expect(resolveActiveJobStage("on_the_way")).toBe("on_the_way");
  });

  it("fails safe to null for every other stage, including future/unknown ones", () => {
    expect(resolveActiveJobStage("inspection")).toBeNull();
    expect(resolveActiveJobStage("completed")).toBeNull();
    expect(resolveActiveJobStage("some_future_stage")).toBeNull();
    expect(resolveActiveJobStage(null)).toBeNull();
    expect(resolveActiveJobStage(undefined)).toBeNull();
  });
});

describe("resolveActiveJobPresentation", () => {
  it("never marks a future step complete for the assignment stage", () => {
    const p = resolveActiveJobPresentation("assignment");
    expect(p.showSchedule).toBe(false);
    expect(p.showTechnicianCard).toBe(true);
  });

  it("does not imply travel for scheduled", () => {
    const p = resolveActiveJobPresentation("scheduled");
    expect(p.explanation).not.toMatch(/on the way|heading/i);
  });

  it("only claims travel for on_the_way", () => {
    const p = resolveActiveJobPresentation("on_the_way");
    expect(p.explanation).toMatch(/heading to your address/i);
  });
});

describe("resolveJobProgressStepState", () => {
  it("marks booked complete and arrived pending for every owned stage", () => {
    for (const stage of ["assignment", "scheduled", "on_the_way"] as const) {
      expect(resolveJobProgressStepState("booked", stage)).toBe("complete");
      expect(resolveJobProgressStepState("arrived", stage)).toBe("pending");
    }
  });

  it("marks the current stage active, never complete", () => {
    expect(resolveJobProgressStepState("on_the_way", "on_the_way")).toBe("active");
  });

  it("never marks a step ahead of the real stage as complete", () => {
    expect(resolveJobProgressStepState("on_the_way", "assignment")).toBe("pending");
    expect(resolveJobProgressStepState("scheduled", "assignment")).toBe("pending");
  });
});

describe("formatScheduleWindow", () => {
  it("returns null (never a placeholder) when no schedule is set", () => {
    expect(formatScheduleWindow(null, null)).toBeNull();
  });

  it("formats a real date with a real window, never a fabricated ETA", () => {
    expect(formatScheduleWindow("2026-08-05", "3:00 PM - 5:00 PM")).toMatch(/5 Aug 2026 · 3:00 PM - 5:00 PM/);
  });

  it("formats the date alone when no window is set", () => {
    expect(formatScheduleWindow("2026-08-05", null)).toMatch(/^5 Aug 2026$/);
  });

  it("distinguishes provider acceptance from technician assignment", () => {
    const p = resolveActiveJobPresentation("assignment", "accepted");
    expect(p.title).toBe("Provider accepted");
    expect(p.showTechnicianCard).toBe(false);
    expect(p.nextExpected).toContain("technician");
  });

  it("turns a 24-hour backend window into customer-friendly time", () => {
    expect(formatScheduleWindow("2026-08-24", "10:00-11:00")).toBe("24 Aug 2026 · 10:00 AM–11:00 AM");
  });
});
