import { resolveWorkflowStatus, workflowToneColor, WORKFLOW_STATUS_MAP } from "../workflowStatus";
import { buildTheme } from "../themes/buildTheme";

describe("workflow status mapping", () => {
  it("resolves every real backend job status from app.engines.execution.constants", () => {
    const realStatuses = [
      "pending_assignment", "assigned", "accepted", "scheduled", "on_the_way", "reached_site",
      "inspection_started", "inspection_done", "quote_required", "service_started", "work_done",
      "completed", "customer_not_available", "cancelled", "failed", "closed_estimate_declined",
    ];
    for (const status of realStatuses) {
      expect(WORKFLOW_STATUS_MAP[status]).toBeDefined();
    }
  });

  it("never guesses a transition for an unknown status -- returns a safe neutral fallback", () => {
    const result = resolveWorkflowStatus("some_future_status_not_yet_known");
    expect(result.tone).toBe("neutral");
    expect(result.label).toBe("Unknown Status");
  });

  it("handles null/undefined status without throwing", () => {
    expect(() => resolveWorkflowStatus(null)).not.toThrow();
    expect(() => resolveWorkflowStatus(undefined)).not.toThrow();
  });

  it("maps every tone to a real theme color in both light and dark", () => {
    const light = buildTheme("light");
    const dark = buildTheme("dark");
    const tones = ["completed", "current", "upcoming", "blocked", "cancelled", "neutral"] as const;
    for (const tone of tones) {
      expect(workflowToneColor(light, tone)).toBeTruthy();
      expect(workflowToneColor(dark, tone)).toBeTruthy();
    }
  });
});
