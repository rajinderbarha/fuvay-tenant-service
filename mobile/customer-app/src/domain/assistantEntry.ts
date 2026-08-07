import { CategoryId } from "./ids";

/**
 * Backend-authoritative entry hint for the Booking Assistant -- NOT
 * authorization and NOT serviceability proof (spec: "Navigation state is
 * an entry hint, never authorization or serviceability proof. The
 * backend must revalidate category availability and ZIP serviceability.").
 *
 * `customerId` is deliberately ABSENT -- identity comes from the
 * authenticated session (Phase F sessionManager), never a navigation
 * param. `serviceabilityChecked` is also absent as an authority signal --
 * the Assistant screen re-checks serviceability itself via the real
 * backend on entry, it never trusts a stale flag carried from Home.
 */
export type AssistantEntryContext =
  | {
      source: "service_card";
      categoryId: CategoryId;
      categoryName: string;
      categorySlug: string;
      zipcode: string;
      existingDraftId: string | null;
      /**
       * Set when the customer tapped a named problem on Home ("AC Not
       * Cooling") rather than the category itself, so the Assistant can
       * skip the issue picker and go straight to the detail questions.
       *
       * Still only a HINT, like everything else here: the Assistant
       * fetches the real backend issue list on entry and auto-selects
       * this id ONLY if it appears there. An id that is stale, no longer
       * active, or not serviceable at this ZIP simply falls back to the
       * normal picker -- it can never force a selection the backend
       * would not otherwise offer.
       */
      preselectedIssueId: string | null;
    }
  | {
      source: "assistant_card";
      categoryId: null;
      categoryName: null;
      categorySlug: null;
      zipcode: string;
      existingDraftId: string | null;
    };

export function createServiceCardEntryContext(input: {
  categoryId: CategoryId;
  categoryName: string;
  categorySlug: string;
  zipcode: string;
  existingDraftId?: string | null;
  preselectedIssueId?: string | null;
}): AssistantEntryContext {
  return {
    source: "service_card",
    categoryId: input.categoryId,
    categoryName: input.categoryName,
    categorySlug: input.categorySlug,
    zipcode: input.zipcode,
    existingDraftId: input.existingDraftId ?? null,
    preselectedIssueId: input.preselectedIssueId ?? null,
  };
}

/** Entry from a quick-issue chip on Home: same service-card entry, plus
 * the specific problem the customer named. */
export function createQuickIssueEntryContext(input: {
  categoryId: CategoryId;
  categoryName: string;
  categorySlug: string;
  zipcode: string;
  issueId: string;
}): AssistantEntryContext {
  return createServiceCardEntryContext({ ...input, preselectedIssueId: input.issueId });
}

export function createAssistantCardEntryContext(input: {
  zipcode: string;
  existingDraftId?: string | null;
}): AssistantEntryContext {
  return {
    source: "assistant_card",
    categoryId: null,
    categoryName: null,
    categorySlug: null,
    zipcode: input.zipcode,
    existingDraftId: input.existingDraftId ?? null,
  };
}
