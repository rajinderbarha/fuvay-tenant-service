import type { ValidatedIssueType } from "./diagnostic-catalog-schema";

/**
 * The full set of steps this sprint can ever show. There is no backend
 * question-type taxonomy (see contract-matrix.md) — this list is the
 * client's own honest mapping from real, verified backend signals to a
 * renderable step, never an invented production diagnostic tree.
 */
export type StepId = "issue_type" | "issue_description" | "photo_boundary" | "service_type" | "service_option" | "brand" | "customer_note" | "completion";

export type QuestionType = "SINGLE_SELECT" | "MULTI_SELECT" | "SHORT_TEXT" | "INFORMATION";

export const STEP_QUESTION_TYPES: Record<Exclude<StepId, "completion">, QuestionType> = {
  issue_type: "SINGLE_SELECT",
  issue_description: "SHORT_TEXT",
  photo_boundary: "INFORMATION",
  service_type: "SINGLE_SELECT",
  service_option: "MULTI_SELECT",
  brand: "SINGLE_SELECT",
  customer_note: "SHORT_TEXT",
};

/**
 * Real, verified signals only. `hasIssueTypes`/`hasServiceOptions`/
 * `hasBrands`/`hasServiceTypes` come from actual catalog responses being
 * non-empty (data-presence, never assumed). `requiresBrand`/`requiresType`/
 * `requiresCustomerNotes`/`requiresPhotoUpload` come directly from
 * CUSTOMER-L5-04's already-fetched `ValidatedOfferingDetail.required_fields`
 * — the most precise, offering-scoped signal available (see known-gaps.md
 * for the documented `requiresType` → service-types-catalog assumption).
 */
export interface StepGates {
  hasIssueTypes: boolean;
  hasServiceOptions: boolean;
  hasBrands: boolean;
  hasServiceTypes: boolean;
  requiresBrand: boolean;
  requiresType: boolean;
  requiresCustomerNotes: boolean;
  requiresPhotoUpload: boolean;
}

/**
 * The static step order, computed once from real gates. `issue_description`
 * is deliberately excluded here — it can only be known after the customer
 * answers `issue_type`, which is why `applyIssueTypeBranch` exists as a
 * separate, dynamic step (CUSTOMER-L5-05 §28's one real branching point).
 */
export function buildBaseStepOrder(gates: StepGates): StepId[] {
  const steps: StepId[] = [];
  if (gates.hasIssueTypes) steps.push("issue_type");
  if (gates.requiresType && gates.hasServiceTypes) steps.push("service_type");
  if (gates.hasServiceOptions) steps.push("service_option");
  if (gates.requiresBrand && gates.hasBrands) steps.push("brand");
  if (gates.requiresCustomerNotes) steps.push("customer_note");
  if (gates.requiresPhotoUpload) steps.push("photo_boundary");
  steps.push("completion");
  return steps;
}

/**
 * Derives the effective step order from the immutable `baseSteps` (computed
 * once from real offering/category gates) plus the customer's current
 * `issue_type` answer, if any. Always recomputed from `baseSteps` rather
 * than mutated incrementally — this is what makes answer revision safe:
 * revising `issue_type` and calling this again automatically drops a
 * no-longer-applicable `issue_description`/dynamic `photo_boundary` without
 * a separate "undo" function that could drift out of sync
 * (CUSTOMER-L5-05 §29's "invalidated downstream answers removed").
 *
 * `photo_boundary` from the offering-level gate (already present in
 * `baseSteps`) is never removed by this function — only a *dynamically*
 * issue-type-triggered `photo_boundary` (one not already in `baseSteps`) is
 * added or dropped as the issue-type answer changes.
 */
export function deriveSteps(baseSteps: StepId[], selectedIssueType: ValidatedIssueType | null): StepId[] {
  if (!selectedIssueType) return baseSteps;

  const issueTypeIndex = baseSteps.indexOf("issue_type");
  if (issueTypeIndex === -1) return baseSteps;

  const insertions: StepId[] = [];
  if (selectedIssueType.requires_description) insertions.push("issue_description");
  if (selectedIssueType.requires_photo && !baseSteps.includes("photo_boundary")) insertions.push("photo_boundary");
  if (insertions.length === 0) return baseSteps;

  const result = [...baseSteps];
  result.splice(issueTypeIndex + 1, 0, ...insertions);
  return result;
}
