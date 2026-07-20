import type { AnswerRecord } from "./assistant-session";
import type { StepId } from "./assistant-steps";

const MAX_TEXT_LENGTH = 500;
// eslint-disable-next-line no-control-regex -- deliberately stripping ASCII control characters, not matching a literal range.
const CONTROL_CHARACTERS = /[\x00-\x1F\x7F]/g;

/** Canonical value is always the stable backend option ID — never the translated display label (CUSTOMER-L5-05 §32). */
export function normalizeSingleSelectAnswer(stepId: StepId, optionId: string, displayLabel: string): AnswerRecord {
  return { stepId, questionType: "SINGLE_SELECT", canonicalAnswer: optionId, displaySummary: displayLabel, submittedAt: new Date().toISOString() };
}

/** Order is preserved from the backend-supplied option order, not re-sorted client-side (CUSTOMER-L5-05 §32). */
export function normalizeMultiSelectAnswer(stepId: StepId, optionIds: string[], displayLabels: string[]): AnswerRecord {
  return {
    stepId,
    questionType: "MULTI_SELECT",
    canonicalAnswer: optionIds,
    displaySummary: displayLabels.length > 0 ? displayLabels.join(", ") : "None selected",
    submittedAt: new Date().toISOString(),
  };
}

/** Trims, strips control characters, and caps length — never sent to logs/analytics raw (CUSTOMER-L5-05 §22/§53). */
export function normalizeShortTextAnswer(stepId: StepId, rawText: string): AnswerRecord {
  const normalized = rawText.replace(CONTROL_CHARACTERS, "").replace(/\s+/g, " ").trim().slice(0, MAX_TEXT_LENGTH);
  return { stepId, questionType: "SHORT_TEXT", canonicalAnswer: normalized, displaySummary: normalized, submittedAt: new Date().toISOString() };
}

/** Informational steps only record acknowledgement, never a customer-authored value. */
export function normalizeInformationAcknowledgement(stepId: StepId): AnswerRecord {
  return { stepId, questionType: "INFORMATION", canonicalAnswer: "acknowledged", displaySummary: "Acknowledged", submittedAt: new Date().toISOString() };
}
