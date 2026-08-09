/**
 * DTOs for the backend-first Booking Assistant bootstrap surface,
 * confirmed against `HomeServiceChatbotBookingService.{get_assistant_
 * bootstrap,select_issue}` / `OfferingInterpretationService.interpret`
 * (app/engines/home_service_booking/{service,offering_interpretation_
 * service}.py, read directly this task). Backend selects every issue
 * option and the resumable draft; nothing here is inferred client-side.
 * ISSUE-first (real customer intent -- "what's wrong with your AC"),
 * never Brand or any other follow-up attribute (root-cause fix for
 * "Brand appears before any real issue selection").
 */
import { z } from "zod";
import { bookingDraftResponseSchema } from "./bookingDraft";
import { questionFlowEnvelopeSchema } from "./questionFlow";

export const assistantIssueDtoSchema = z.object({
  id: z.string(),
  label: z.string(),
});

export const assistantBootstrapResponseSchema = z.object({
  schema_version: z.number(),
  category: z.object({
    id: z.string().nullable(),
    slug: z.string().nullable(),
    name: z.string().nullable(),
  }),
  zipcode: z.string().nullable(),
  serviceable: z.boolean(),
  issues: z.array(assistantIssueDtoSchema),
  resumable_draft: bookingDraftResponseSchema.nullable(),
  current_stage: z.enum(["issue_selection", "questions"]),
}).passthrough();
export type AssistantBootstrapResponseDto = z.infer<typeof assistantBootstrapResponseSchema>;

export const interpretOfferingSelectionResponseSchema = z.object({
  action: z.enum(["match_option", "ask_clarification", "answer_and_repeat_options", "out_of_scope", "cannot_answer"]),
  reply: z.string(),
  /** The matched problem, plus the CATEGORY it belongs to. Present when the
   * backend interpreted across every category bookable at the ZIP (no
   * `category_slug` sent) -- a match can then legitimately land outside the
   * category the conversation started in, so the caller has to know which one to
   * start the draft in. */
  matched_offering: z.object({
    id: z.string(),
    name: z.string(),
    category_slug: z.string().nullable().optional(),
    category_name: z.string().nullable().optional(),
    category_id: z.string().nullable().optional(),
  }).nullable(),
  offerings: z.array(z.object({ id: z.string(), name: z.string() })),
}).passthrough();
export type InterpretOfferingSelectionResponseDto = z.infer<typeof interpretOfferingSelectionResponseSchema>;

export const selectIssueResponseSchema = z.object({
  draft_id: z.string(),
  envelope: questionFlowEnvelopeSchema,
  selected_issue_ids: z.array(z.string()),
}).passthrough();
export type SelectIssueResponseDto = z.infer<typeof selectIssueResponseSchema>;
