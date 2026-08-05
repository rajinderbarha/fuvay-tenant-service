import { createServiceCardEntryContext, createAssistantCardEntryContext } from "../assistantEntry";
import { asCategoryId } from "../ids";

describe("assistant entry context", () => {
  it("service-card entry preserves the selected category, never fabricating one", () => {
    const ctx = createServiceCardEntryContext({
      categoryId: asCategoryId("cat-1"),
      categoryName: "AC & Cooling",
      categorySlug: "ac-cooling",
      zipcode: "141001",
    });
    expect(ctx).toEqual({
      source: "service_card",
      categoryId: "cat-1",
      categoryName: "AC & Cooling",
      categorySlug: "ac-cooling",
      zipcode: "141001",
      existingDraftId: null,
    });
  });

  it("assistant-card (generic) entry never selects a category", () => {
    const ctx = createAssistantCardEntryContext({ zipcode: "141001" });
    expect(ctx).toEqual({
      source: "assistant_card",
      categoryId: null,
      categoryName: null,
      categorySlug: null,
      zipcode: "141001",
      existingDraftId: null,
    });
  });

  it("carries an existing draft id through when resuming", () => {
    const ctx = createServiceCardEntryContext({
      categoryId: asCategoryId("cat-1"), categoryName: "AC & Cooling", categorySlug: "ac-cooling",
      zipcode: "141001", existingDraftId: "draft-1",
    });
    expect(ctx.existingDraftId).toBe("draft-1");
  });

  it("never carries a customerId or serviceabilityChecked field (identity comes from the session, not navigation params)", () => {
    const ctx = createAssistantCardEntryContext({ zipcode: "141001" });
    expect(ctx).not.toHaveProperty("customerId");
    expect(ctx).not.toHaveProperty("serviceabilityChecked");
  });
});
