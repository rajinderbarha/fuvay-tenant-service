import { buildBaseStepOrder, deriveSteps, type StepGates, type StepId } from "../assistant-steps";
import type { ValidatedIssueType } from "../diagnostic-catalog-schema";

const noGates: StepGates = {
  hasIssueTypes: false,
  hasServiceOptions: false,
  hasBrands: false,
  hasServiceTypes: false,
  requiresBrand: false,
  requiresType: false,
  requiresCustomerNotes: false,
  requiresPhotoUpload: false,
};

function issueType(overrides: Partial<ValidatedIssueType> = {}): ValidatedIssueType {
  return {
    issue_type_id: "it-1",
    name: "Not cooling",
    code: "NOT_COOLING",
    severity: "high",
    is_common: true,
    requires_photo: false,
    requires_description: false,
    display_order: 1,
    ...overrides,
  };
}

describe("buildBaseStepOrder", () => {
  it("always includes completion, even with no gates satisfied", () => {
    expect(buildBaseStepOrder(noGates)).toEqual(["completion"]);
  });

  it("includes issue_type only when the catalog has issue types", () => {
    expect(buildBaseStepOrder({ ...noGates, hasIssueTypes: true })).toEqual(["issue_type", "completion"]);
  });

  it("includes service_type only when both requiresType and hasServiceTypes are true", () => {
    expect(buildBaseStepOrder({ ...noGates, requiresType: true })).toEqual(["completion"]);
    expect(buildBaseStepOrder({ ...noGates, hasServiceTypes: true })).toEqual(["completion"]);
    expect(buildBaseStepOrder({ ...noGates, requiresType: true, hasServiceTypes: true })).toEqual(["service_type", "completion"]);
  });

  it("includes brand only when both requiresBrand and hasBrands are true", () => {
    expect(buildBaseStepOrder({ ...noGates, requiresBrand: true, hasBrands: true })).toEqual(["brand", "completion"]);
  });

  it("includes service_option purely from data presence, independent of requiresType", () => {
    expect(buildBaseStepOrder({ ...noGates, hasServiceOptions: true })).toEqual(["service_option", "completion"]);
  });

  it("orders a fully-gated plan deterministically", () => {
    expect(
      buildBaseStepOrder({
        hasIssueTypes: true,
        hasServiceOptions: true,
        hasBrands: true,
        hasServiceTypes: true,
        requiresBrand: true,
        requiresType: true,
        requiresCustomerNotes: true,
        requiresPhotoUpload: true,
      })
    ).toEqual(["issue_type", "service_type", "service_option", "brand", "customer_note", "photo_boundary", "completion"]);
  });
});

describe("deriveSteps", () => {
  const baseSteps = ["issue_type", "service_option", "completion"] as const;

  it("returns baseSteps unchanged when no issue type is selected", () => {
    expect(deriveSteps([...baseSteps], null)).toEqual([...baseSteps]);
  });

  it("inserts issue_description right after issue_type when required", () => {
    const result = deriveSteps([...baseSteps], issueType({ requires_description: true }));
    expect(result).toEqual(["issue_type", "issue_description", "service_option", "completion"]);
  });

  it("inserts photo_boundary right after issue_type when required and not already present", () => {
    const result = deriveSteps([...baseSteps], issueType({ requires_photo: true }));
    expect(result).toEqual(["issue_type", "photo_boundary", "service_option", "completion"]);
  });

  it("inserts both issue_description and photo_boundary in order when both are required", () => {
    const result = deriveSteps([...baseSteps], issueType({ requires_description: true, requires_photo: true }));
    expect(result).toEqual(["issue_type", "issue_description", "photo_boundary", "service_option", "completion"]);
  });

  it("does not duplicate photo_boundary if the offering-level gate already placed it in baseSteps", () => {
    const withPhotoBoundary: StepId[] = ["issue_type", "service_option", "photo_boundary", "completion"];
    const result = deriveSteps(withPhotoBoundary, issueType({ requires_photo: true }));
    expect(result).toEqual(withPhotoBoundary);
  });

  it("returns baseSteps unchanged when issue_type is not in the plan at all", () => {
    const noIssueStep: StepId[] = ["service_option", "completion"];
    expect(deriveSteps(noIssueStep, issueType({ requires_description: true }))).toEqual(noIssueStep);
  });
});
