import { resolveActivityLabel, ASSISTANT_ACTIVITY_LABELS } from "../assistantActivity";

describe("assistantActivity stage labels", () => {
  it("has a real, distinct label for every booking-review/finalization stage (not a reused question-flow label)", () => {
    expect(ASSISTANT_ACTIVITY_LABELS.resolving_price).toBe("Preparing service details…");
    expect(ASSISTANT_ACTIVITY_LABELS.finding_provider).toBe("Looking for available professionals…");
    expect(ASSISTANT_ACTIVITY_LABELS.preparing_review).toBe("Preparing your booking summary…");
    expect(ASSISTANT_ACTIVITY_LABELS.confirming_booking).toBe("Confirming your booking…");
  });

  it("never shows technical/internal terminology in any registered label", () => {
    const allLabels = Object.values(ASSISTANT_ACTIVITY_LABELS).join(" ");
    expect(allLabels).not.toMatch(/api|deepseek|tool|json|route|endpoint/i);
  });

  it("resolveActivityLabel renders the new stages with and without a zipcode", () => {
    expect(resolveActivityLabel("confirming_booking", "140412")).toBe("Confirming your booking…");
    expect(resolveActivityLabel("finding_provider", null)).toBe("Looking for available professionals…");
  });
});
