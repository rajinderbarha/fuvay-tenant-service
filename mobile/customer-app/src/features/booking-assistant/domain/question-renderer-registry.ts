import { logger } from "../../../observability/logger";
import type { QuestionType } from "./assistant-steps";

const SUPPORTED_QUESTION_TYPES: readonly QuestionType[] = ["SINGLE_SELECT", "MULTI_SELECT", "SHORT_TEXT", "INFORMATION"];

export type ResolvedRenderer = { recognized: true; questionType: QuestionType } | { recognized: false; questionType: string };

/**
 * Centralized, typed lookup — mirrors CUSTOMER-L5-03's `module-registry.ts`
 * pattern. Never resolves a component from a backend-supplied string;
 * `QuestionType` values are entirely client-derived from real gates
 * (assistant-steps.ts), not backend enum values, but this still fails
 * closed for forward-compatibility if a future step type is added to the
 * domain model without a matching renderer wired in.
 */
export function resolveQuestionRenderer(questionType: string): ResolvedRenderer {
  if ((SUPPORTED_QUESTION_TYPES as readonly string[]).includes(questionType)) {
    return { recognized: true, questionType: questionType as QuestionType };
  }
  logger.warn("unsupported_question_received", { questionType });
  return { recognized: false, questionType };
}
