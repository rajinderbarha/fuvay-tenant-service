import { authenticatedRequest } from "../client/authenticatedClient";
import { parseApiSuccess } from "../client/responseParser";
import { questionFlowEnvelopeSchema, interpretQuestionFlowResponseSchema } from "../contracts/questionFlow";

const base = (draftId: string) => `/v1/customer/home-services/booking-drafts/${draftId}/question-flow`;

/** `language` presents the SAME canonical question in the customer's
 * chosen conversation language (CUSTOMER-ASSISTANT-UX-04 Part 3). Only
 * the display text/labels differ -- question id, option ids, order, type
 * and progress are always the backend's own, so answers submitted from a
 * translated question are byte-identical to those from the English one. */
export async function getQuestionFlow(draftId: string, language?: string | null, sessionId?: string | null) {
  const params = new URLSearchParams();
  if (language) params.set("language", language);
  if (sessionId) params.set("session_id", sessionId);
  const query = params.toString();
  const res = await authenticatedRequest({ method: "GET", path: query ? `${base(draftId)}?${query}` : base(draftId) });
  return parseApiSuccess(res.json, questionFlowEnvelopeSchema);
}

/** Backend-first-with-DeepSeek-on-demand: called ONLY for the customer's
 * own free-text message while a canonical question is active -- never for
 * a tap (submitQuestionFlowAnswer below), and never to pick the next
 * question (the backend alone decides that; see
 * QuestionInterpretationService's module docstring). */
export async function interpretQuestionFlowText(draftId: string, text: string, sessionId?: string | null) {
  const res = await authenticatedRequest({
    method: "POST",
    path: `${base(draftId)}/interpret`,
    body: { text, session_id: sessionId ?? undefined },
  });
  return parseApiSuccess(res.json, interpretQuestionFlowResponseSchema);
}

export interface SubmitAnswerInput {
  questionId: string;
  optionId?: string | null;
  value?: string | null;
  expectedVersion?: number;
  /** Presents the NEXT question (returned in this same response) in the
   * conversation language, so the customer never sees one question
   * translated and the next one in English. */
  language?: string | null;
  sessionId?: string | null;
}

/** Fails closed on QF_QUESTION_NOT_APPLICABLE / QF_INVALID_OPTION /
 * QF_ANSWER_REQUIRED / QF_STALE_QUESTION_FLOW_VERSION (409) -- confirmed
 * in QuestionFlowService.submit_answer; the caller (assistant lifecycle
 * controller) must refresh the envelope and re-render on any of these
 * rather than retry the same stale submission. */
export async function submitQuestionFlowAnswer(draftId: string, input: SubmitAnswerInput) {
  const res = await authenticatedRequest({
    method: "POST",
    path: `${base(draftId)}/answer`,
    body: {
      question_id: input.questionId,
      option_id: input.optionId,
      value: input.value,
      expected_version: input.expectedVersion,
      language: input.language ?? undefined,
      session_id: input.sessionId ?? undefined,
    },
  });
  return parseApiSuccess(res.json, questionFlowEnvelopeSchema);
}
