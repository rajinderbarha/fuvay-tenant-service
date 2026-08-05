import { BookingDraftId } from "./ids";

/** Real backend question types confirmed this task (question_flow_service
 * catalog resolution): choice types are `single_select`/`multi_select`;
 * `photo_capable` is a boolean flag on ANY question type, not a separate
 * type. Free-text is inferred from the absence of options (no dedicated
 * `question_type` string was confirmed for it in the envelope builder --
 * see adapter, which treats "no options" as free-text-capable rather
 * than guessing an enum value the backend never sends). */
export type QuestionType = "single_select" | "multi_select" | string;

export interface QuestionOption {
  id: string | null;
  label: string | null;
}

export interface CurrentQuestion {
  questionId: string;
  questionKey: string;
  questionType: QuestionType;
  text: string;
  helpText: string | null;
  required: boolean;
  options: QuestionOption[];
  photoCapable: boolean;
  /** True when there are no backend-defined options -- the only
   * client-safe signal for "this question accepts free text" (the
   * backend never sends a dedicated `question_type` for it). */
  acceptsFreeText: boolean;
}

export interface QuestionFlowProgress {
  answeredCount: number;
  remainingCount: number;
  complete: boolean;
}

export interface QuestionFlowScope {
  categoryId: string;
  offeringId: string;
  jobTypeId: string | null;
}

export interface AnsweredQuestion {
  questionId: string;
  questionKey: string;
  questionLabel: string;
  answerLabel: string;
}

export interface QuestionFlowEnvelope {
  envelopeVersion: number;
  sessionId: string | null;
  draftId: BookingDraftId;
  questionFlowVersion: number;
  scope: QuestionFlowScope;
  currentQuestion: CurrentQuestion | null;
  progress: QuestionFlowProgress;
  nextPermittedActions: string[];
  /** Already-answered questions, oldest first -- lets the UI show a
   * collapsed confirmed row (e.g. "Brand: LG") instead of only ever
   * showing the current unanswered question. */
  answeredQuestions: AnsweredQuestion[];
}
