import {
  resolveArrivalInspectionStage, resolveArrivalInspectionPresentation,
  resolveQuoteDecisionStage, resolveQuoteDecisionPresentation,
} from "../inspectionQuotePresentation";

describe("resolveArrivalInspectionStage", () => {
  it("recognizes the three real job statuses this phase owns", () => {
    expect(resolveArrivalInspectionStage("reached_site")).toBe("arrived");
    expect(resolveArrivalInspectionStage("inspection_started")).toBe("inspecting");
    expect(resolveArrivalInspectionStage("inspection_done")).toBe("inspection_done");
    expect(resolveArrivalInspectionStage("quote_required")).toBe("inspection_done");
  });

  it("recognizes the real in-progress and work-done statuses", () => {
    expect(resolveArrivalInspectionStage("service_started")).toBe("in_progress");
    expect(resolveArrivalInspectionStage("work_done")).toBe("work_done");
  });

  it("fails safe to null for statuses this phase does not own", () => {
    expect(resolveArrivalInspectionStage("assigned")).toBeNull();
    expect(resolveArrivalInspectionStage("on_the_way")).toBeNull();
    expect(resolveArrivalInspectionStage("completed")).toBeNull();
    expect(resolveArrivalInspectionStage("some_future_status")).toBeNull();
    expect(resolveArrivalInspectionStage(null)).toBeNull();
  });
});

describe("resolveArrivalInspectionPresentation", () => {
  it("never implies inspection is done while only arrived", () => {
    const p = resolveArrivalInspectionPresentation("arrived");
    expect(p.explanation).not.toMatch(/inspect/i);
  });

  it("never implies a quote exists while still inspecting", () => {
    const p = resolveArrivalInspectionPresentation("inspecting");
    expect(p.explanation).not.toMatch(/quote|estimate/i);
  });
});

describe("resolveQuoteDecisionStage", () => {
  it("maps sent_to_customer to the actionable ready stage", () => {
    expect(resolveQuoteDecisionStage("sent_to_customer")).toBe("ready");
  });

  it("maps decided statuses correctly", () => {
    expect(resolveQuoteDecisionStage("customer_approved")).toBe("approved");
    expect(resolveQuoteDecisionStage("customer_rejected")).toBe("declined");
  });

  it("never treats an unrecognized future status as actionable", () => {
    expect(resolveQuoteDecisionStage("some_future_status")).toBe("unavailable");
    expect(resolveQuoteDecisionStage(null)).toBe("unavailable");
  });

  it("treats expired/withdrawn/superseded quotes as non-actionable", () => {
    expect(resolveQuoteDecisionStage("expired")).toBe("unavailable");
    expect(resolveQuoteDecisionStage("cancelled")).toBe("unavailable");
    expect(resolveQuoteDecisionStage("revision_requested")).toBe("unavailable");
  });
});

describe("resolveQuoteDecisionPresentation", () => {
  it("never claims completion for the approved state beyond authorizing repair", () => {
    const p = resolveQuoteDecisionPresentation("approved");
    expect(p.explanation).not.toMatch(/paid|payment received|complete/i);
  });
});
