/**
 * DTO for the deterministic question-flow envelope, confirmed against
 * `QuestionFlowService._build_envelope` (app/engines/home_service_booking/
 * question_flow_service.py, read directly this task). This is the exact
 * authoritative shape -- backend selects every question and every
 * allowed answer; nothing here is inferred or guessed client-side.
 */
import { z } from "zod";

export const questionOptionDtoSchema = z.object({
  id: z.string().nullable(),
  label: z.string().nullable(),
});

export const currentQuestionDtoSchema = z.object({
  question_id: z.string(),
  question_key: z.string(),
  question_type: z.string(),
  text: z.string(),
  help_text: z.string().nullable().optional(),
  required: z.boolean(),
  options: z.array(questionOptionDtoSchema),
  validation_metadata: z.record(z.string(), z.unknown()).nullable().optional(),
  photo_capable: z.boolean(),
});

export const questionFlowProgressDtoSchema = z.object({
  answered_count: z.number(),
  remaining_count: z.number(),
  complete: z.boolean(),
});

export const questionFlowScopeDtoSchema = z.object({
  category_id: z.string(),
  offering_id: z.string(),
  job_type_id: z.string().nullable(),
});

export const answeredQuestionDtoSchema = z.object({
  question_id: z.string(),
  question_key: z.string(),
  question_label: z.string(),
  answer_label: z.string(),
});

export const questionFlowEnvelopeSchema = z.object({
  envelope_version: z.number(),
  session_id: z.string().nullable(),
  draft_id: z.string(),
  workflow_version: z.string().nullable(),
  question_flow_version: z.number(),
  scope: questionFlowScopeDtoSchema,
  current_question: currentQuestionDtoSchema.nullable(),
  progress: questionFlowProgressDtoSchema,
  next_permitted_actions: z.array(z.string()),
  // Confirmed-answer rows for already-answered questions (question_flow_
  // service._answered_summary) -- lets the UI collapse a past answer into
  // a one-line "Brand: LG" chip instead of only ever showing the current
  // unanswered question. `.optional()` / defaulted so an older cached
  // envelope shape (pre this addition) still parses.
  answered_questions: z.array(answeredQuestionDtoSchema).optional().default([]),
});
export type QuestionFlowEnvelopeDto = z.infer<typeof questionFlowEnvelopeSchema>;

/** Response shape for `POST /question-flow/interpret` -- confirmed against
 * `QuestionInterpretationService.interpret`. `envelope` is ALWAYS the
 * current canonical envelope (freshly re-fetched after a successful
 * match, unchanged otherwise) -- the frontend never has to infer what to
 * render next from `reply` text. */
export const interpretQuestionFlowResponseSchema = z.object({
  action: z.enum(["match_option", "ask_clarification", "answer_and_repeat_question", "out_of_scope", "cannot_answer"]),
  reply: z.string(),
  envelope: questionFlowEnvelopeSchema,
});
export type InterpretQuestionFlowResponseDto = z.infer<typeof interpretQuestionFlowResponseSchema>;
