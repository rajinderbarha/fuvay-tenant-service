import { createServiceCardEntryContext, createAssistantCardEntryContext, createQuickIssueEntryContext } from "../assistantEntry";
import { asCategoryId } from "../ids";

describe("assistant entry context", () => {
  it("service-card entry preserves the selected category, never fabricating one", () => {
    const ctx = createServiceCardEntryContext({
      categoryId: asCategoryId("cat-1"),
      categoryName: "AC & Cooling",
      categorySlug: "ac-cooling",
      serviceGroupSlug: null,
      masterServiceId: null,
      zipcode: "141001",
    });
    expect(ctx).toEqual({
      source: "service_card",
      categoryId: "cat-1",
      categoryName: "AC & Cooling",
      categorySlug: "ac-cooling",
      serviceGroupSlug: null,
      masterServiceId: null,
      zipcode: "141001",
      existingDraftId: null,
      // A plain category tap names no specific problem -- the Assistant
      // must still show its issue picker.
      preselectedIssueId: null,
    });
  });

  it("quick-issue entry carries the chosen problem alongside the category", () => {
    const ctx = createQuickIssueEntryContext({
      categoryId: asCategoryId("cat-1"),
      categoryName: "AC & Cooling",
      categorySlug: "ac-cooling",
      serviceGroupSlug: null,
      zipcode: "141001",
      issueId: "issue-7",
    });
    expect(ctx).toEqual({
      source: "service_card",
      categoryId: "cat-1",
      categoryName: "AC & Cooling",
      categorySlug: "ac-cooling",
      serviceGroupSlug: null,
      masterServiceId: null,
      zipcode: "141001",
      existingDraftId: null,
      preselectedIssueId: "issue-7",
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
