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
}): AssistantEntryContext {
  return {
    source: "service_card",
    categoryId: input.categoryId,
    categoryName: input.categoryName,
    categorySlug: input.categorySlug,
    zipcode: input.zipcode,
    existingDraftId: input.existingDraftId ?? null,
  };
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
