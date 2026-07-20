import { buildBaseStepOrder, deriveSteps, STEP_QUESTION_TYPES, type StepGates, type StepId, type QuestionType } from "./assistant-steps";
import type { ValidatedIssueType } from "./diagnostic-catalog-schema";

export type AssistantStatus = "IDLE" | "READY" | "COMPLETED" | "ERROR";

export interface AnswerRecord {
  stepId: StepId;
  questionType: QuestionType;
  /** Canonical value(s) — always a stable backend ID (or trimmed text for SHORT_TEXT), never a translated label. */
  canonicalAnswer: string | string[];
  /** Locale-aware label shown in the answer-history summary — display only, never submitted anywhere. */
  displaySummary: string;
  submittedAt: string;
}

export interface AssistantSessionState {
  status: AssistantStatus;
  serviceId: string;
  categoryId: string;
  baseSteps: StepId[];
  selectedIssueType: ValidatedIssueType | null;
  currentStepIndex: number;
  answers: Partial<Record<StepId, AnswerRecord>>;
  error?: { message: string };
}

export function createAssistantSession(serviceId: string, categoryId: string, gates: StepGates): AssistantSessionState {
  return {
    status: "READY",
    serviceId,
    categoryId,
    baseSteps: buildBaseStepOrder(gates),
    selectedIssueType: null,
    currentStepIndex: 0,
    answers: {},
  };
}

export function effectiveSteps(state: AssistantSessionState): StepId[] {
  return deriveSteps(state.baseSteps, state.selectedIssueType);
}

export function currentStepId(state: AssistantSessionState): StepId | null {
  return effectiveSteps(state)[state.currentStepIndex] ?? null;
}

export function currentQuestionType(state: AssistantSessionState): QuestionType | null {
  const id = currentStepId(state);
  return id && id !== "completion" ? STEP_QUESTION_TYPES[id] : null;
}

export function isAtCompletion(state: AssistantSessionState): boolean {
  return currentStepId(state) === "completion";
}

export function canGoBack(state: AssistantSessionState): boolean {
  return state.currentStepIndex > 0;
}

/** Honest, never fabricated: total reflects the real effective step count at this moment, which can grow by at most 2 once `issue_type` is answered (CUSTOMER-L5-05 §17). */
export function assistantProgress(state: AssistantSessionState): { current: number; total: number } {
  const steps = effectiveSteps(state);
  return { current: Math.min(state.currentStepIndex + 1, steps.length), total: steps.length };
}

/**
 * Submits an answer for the current step only — fails closed (returns an
 * ERROR state) if the caller's `record.stepId` does not match the actual
 * current step, guarding against a stale/tampered submission
 * (CUSTOMER-L5-05 §33/§61's "QUESTION_NOT_CURRENT" concept, enforced
 * client-side since no backend equivalent exists to enforce it for us).
 * `issueTypeForBranching` must be passed when `record.stepId === "issue_type"`
 * — its `requires_description`/`requires_photo` flags are what
 * `effectiveSteps` uses to grow the plan.
 */
export function submitAnswer(state: AssistantSessionState, record: AnswerRecord, issueTypeForBranching?: ValidatedIssueType): AssistantSessionState {
  if (state.status !== "READY") return state;

  const steps = effectiveSteps(state);
  const current = steps[state.currentStepIndex];
  if (!current || record.stepId !== current) {
    return { ...state, status: "ERROR", error: { message: "question_not_current" } };
  }

  return {
    ...state,
    answers: { ...state.answers, [record.stepId]: record },
    selectedIssueType: record.stepId === "issue_type" ? (issueTypeForBranching ?? null) : state.selectedIssueType,
    currentStepIndex: state.currentStepIndex + 1,
    status: "READY",
    error: undefined,
  };
}

export function goToPreviousStep(state: AssistantSessionState): AssistantSessionState {
  if (state.currentStepIndex === 0) return state;
  return { ...state, currentStepIndex: state.currentStepIndex - 1, status: "READY", error: undefined };
}

/**
 * Jumps back to `stepId` and discards every answer from that step onward —
 * downstream answers are not "preserved but marked invalid," they are
 * cleared, since re-answering an earlier step may change the effective
 * step list itself (revising `issue_type` clears `selectedIssueType`,
 * which `effectiveSteps` then recomputes from scratch — CUSTOMER-L5-05 §29).
 */
export function reviseAnswer(state: AssistantSessionState, stepId: StepId): AssistantSessionState {
  const steps = effectiveSteps(state);
  const targetIndex = steps.indexOf(stepId);
  if (targetIndex === -1) return state;

  const remainingAnswers: Partial<Record<StepId, AnswerRecord>> = {};
  for (const step of steps.slice(0, targetIndex)) {
    const existing = state.answers[step];
    if (existing) remainingAnswers[step] = existing;
  }

  return {
    ...state,
    answers: remainingAnswers,
    selectedIssueType: stepId === "issue_type" ? null : state.selectedIssueType,
    currentStepIndex: targetIndex,
    status: "READY",
    error: undefined,
  };
}

export function completeSession(state: AssistantSessionState): AssistantSessionState {
  if (!isAtCompletion(state)) return state;
  return { ...state, status: "COMPLETED" };
}

/** Ordered answer history for the conversation-summary view — CUSTOMER-L5-05 §16/§31. */
export function orderedAnswerHistory(state: AssistantSessionState): AnswerRecord[] {
  return effectiveSteps(state)
    .map((step) => state.answers[step])
    .filter((record): record is AnswerRecord => Boolean(record));
}
