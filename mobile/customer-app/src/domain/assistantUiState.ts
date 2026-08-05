/**
 * Explicit assistant UI state machine (spec section 8) -- replaces
 * scattered booleans. Every transition is validated so an impossible
 * combination (e.g. showing "ready" while an answer submission is still
 * in flight) can never silently occur.
 */
export type AssistantUiState =
  | "bootstrapping"
  | "resolving_session"
  | "checking_serviceability"
  | "loading_question"
  | "ready"
  | "submitting_answer"
  | "assistant_processing"
  | "refreshing_question_flow"
  | "guided_fallback"
  | "offline"
  | "recoverable_error"
  | "blocked"
  | "complete";

const ALLOWED_TRANSITIONS: Record<AssistantUiState, readonly AssistantUiState[]> = {
  bootstrapping: ["resolving_session", "offline", "recoverable_error", "blocked"],
  resolving_session: ["checking_serviceability", "loading_question", "ready", "offline", "recoverable_error", "blocked", "guided_fallback"],
  checking_serviceability: ["loading_question", "ready", "blocked", "offline", "recoverable_error"],
  loading_question: ["ready", "complete", "offline", "recoverable_error", "guided_fallback"],
  ready: ["submitting_answer", "assistant_processing", "refreshing_question_flow", "offline", "recoverable_error", "guided_fallback", "complete"],
  submitting_answer: ["refreshing_question_flow", "recoverable_error", "offline", "guided_fallback"],
  assistant_processing: ["ready", "refreshing_question_flow", "recoverable_error", "offline", "guided_fallback"],
  refreshing_question_flow: ["ready", "complete", "recoverable_error", "offline", "guided_fallback"],
  guided_fallback: ["loading_question", "ready", "recoverable_error", "offline"],
  offline: ["resolving_session", "ready", "loading_question"],
  recoverable_error: ["resolving_session", "loading_question", "ready", "submitting_answer"],
  blocked: [],
  complete: [],
};

export function isValidAssistantTransition(from: AssistantUiState, to: AssistantUiState): boolean {
  return ALLOWED_TRANSITIONS[from].includes(to);
}

export class InvalidAssistantTransitionError extends Error {
  constructor(public readonly from: AssistantUiState, public readonly to: AssistantUiState) {
    super(`Invalid assistant UI transition: ${from} -> ${to}`);
    this.name = "InvalidAssistantTransitionError";
  }
}

export function assertValidAssistantTransition(from: AssistantUiState, to: AssistantUiState): void {
  if (!isValidAssistantTransition(from, to)) {
    throw new InvalidAssistantTransitionError(from, to);
  }
}

/** States where a slow-request "guided fallback" offer is meaningful --
 * used by the controller's timeout timer to decide whether to surface
 * `Continue with guided questions`. */
export const STALL_PRONE_STATES: readonly AssistantUiState[] = [
  "resolving_session", "checking_serviceability", "assistant_processing", "loading_question",
];
