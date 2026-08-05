import { QuestionFlowEnvelopeDto, questionFlowEnvelopeSchema } from "../contracts/questionFlow";
import { QuestionFlowEnvelope, CurrentQuestion } from "../../domain/questionEnvelope";
import { asBookingDraftId } from "../../domain/ids";
import { ContractValidationError } from "../../domain/errors";

export function parseQuestionFlowEnvelope(raw: unknown): QuestionFlowEnvelopeDto {
  const result = questionFlowEnvelopeSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("QuestionFlowEnvelopeDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

function adaptCurrentQuestion(dto: QuestionFlowEnvelopeDto["current_question"]): CurrentQuestion | null {
  if (!dto) return null;
  return {
    questionId: dto.question_id,
    questionKey: dto.question_key,
    questionType: dto.question_type,
    text: dto.text,
    helpText: dto.help_text ?? null,
    required: dto.required,
    options: dto.options,
    photoCapable: dto.photo_capable,
    acceptsFreeText: dto.options.length === 0,
  };
}

export function adaptQuestionFlowEnvelope(dto: QuestionFlowEnvelopeDto): QuestionFlowEnvelope {
  return {
    envelopeVersion: dto.envelope_version,
    sessionId: dto.session_id,
    draftId: asBookingDraftId(dto.draft_id),
    questionFlowVersion: dto.question_flow_version,
    scope: {
      categoryId: dto.scope.category_id,
      offeringId: dto.scope.offering_id,
      jobTypeId: dto.scope.job_type_id,
    },
    currentQuestion: adaptCurrentQuestion(dto.current_question),
    progress: {
      answeredCount: dto.progress.answered_count,
      remainingCount: dto.progress.remaining_count,
      complete: dto.progress.complete,
    },
    nextPermittedActions: dto.next_permitted_actions,
    answeredQuestions: dto.answered_questions.map(a => ({
      questionId: a.question_id,
      questionKey: a.question_key,
      questionLabel: a.question_label,
      answerLabel: a.answer_label,
    })),
  };
}
