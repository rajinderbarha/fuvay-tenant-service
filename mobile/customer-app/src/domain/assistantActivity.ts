/**
 * Claude-style processing activity labels (spec section 6). This is a
 * closed allowlist -- every label a customer can ever see is listed here
 * literally; nothing is assembled from raw backend text, a model name, a
 * tool name, or a percentage. Stages are driven by real observable
 * request-lifecycle events (see useAssistantController.ts), never a
 * timer rotating through impressive-sounding strings.
 */
export type AssistantActivityStage =
  | "opening_saved_booking"
  | "checking_serviceability"
  | "understanding_request"
  | "loading_requirements"
  | "validating_answer"
  | "preparing_next_question"
  | "saving_progress"
  | "switching_to_guided"
  // Booking-review/finalization stages -- previously the booking-review
  // screen reused question-flow stages here (e.g. "checking_pricing"
  // mapped to "validating_answer", showing "Validating your answer..."
  // while actually resolving a price -- semantically wrong text for a
  // real, different operation). Real, distinct stages instead, still
  // rendered by the same AssistantActivity component/visual language.
  | "resolving_price"
  | "finding_provider"
  | "preparing_review"
  | "confirming_booking";

export const ASSISTANT_ACTIVITY_LABELS: Record<AssistantActivityStage, string> = {
  opening_saved_booking: "Opening your saved booking…",
  checking_serviceability: "Checking services available in {zipcode}…",
  understanding_request: "Understanding your request…",
  loading_requirements: "Loading booking requirements…",
  validating_answer: "Validating your answer…",
  preparing_next_question: "Preparing the next question…",
  saving_progress: "Saving your progress…",
  switching_to_guided: "Switching to guided questions…",
  resolving_price: "Preparing service details…",
  finding_provider: "Looking for available professionals…",
  preparing_review: "Preparing your booking summary…",
  confirming_booking: "Confirming your booking…",
};

/** The only place `{zipcode}` interpolation happens -- callers must never
 * string-concatenate a raw label themselves. */
export function resolveActivityLabel(stage: AssistantActivityStage, zipcode: string | null): string {
  const template = ASSISTANT_ACTIVITY_LABELS[stage];
  return zipcode ? template.replace("{zipcode}", zipcode) : template.replace(" {zipcode}", "").replace("{zipcode}", "your area");
}
