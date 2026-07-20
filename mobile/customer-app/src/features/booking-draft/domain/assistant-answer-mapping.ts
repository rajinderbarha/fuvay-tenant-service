import type { AnswerRecord } from "../../booking-assistant/domain/assistant-session";

export interface DraftUpdatePayload {
  brand_id?: string;
  offering_type_id?: string;
  issue_summary?: string;
}

/**
 * Maps CUSTOMER-L5-05's collected assistant answers onto the real,
 * verified subset of draft fields the backend's `PUT` endpoint actually
 * accepts — see CUSTOMER-L5-06-contract-matrix.md. `issue_type_id` and
 * `service_option_ids_json` are deliberately never included here: both are
 * real columns on `HomeServiceBookingDraft` but neither is in the `PUT`
 * endpoint's accepted-field list (`service.py#update_draft_fields`'s
 * `uuid_fields`), so sending them would silently do nothing — omitting them
 * is honest, not an oversight. `service_type` → `offering_type_id` carries
 * forward CUSTOMER-L5-05's own documented naming assumption (no confirmed
 * FK between the two catalogs).
 */
export function mapAssistantAnswersToDraftUpdate(answers: AnswerRecord[]): DraftUpdatePayload {
  const payload: DraftUpdatePayload = {};

  const brand = answers.find((a) => a.stepId === "brand");
  if (brand && typeof brand.canonicalAnswer === "string") payload.brand_id = brand.canonicalAnswer;

  const serviceType = answers.find((a) => a.stepId === "service_type");
  if (serviceType && typeof serviceType.canonicalAnswer === "string") payload.offering_type_id = serviceType.canonicalAnswer;

  const issueDescription = answers.find((a) => a.stepId === "issue_description");
  const customerNote = answers.find((a) => a.stepId === "customer_note");
  const summaryParts = [issueDescription, customerNote]
    .filter((a): a is AnswerRecord => Boolean(a) && typeof a?.canonicalAnswer === "string" && (a.canonicalAnswer as string).length > 0)
    .map((a) => a.canonicalAnswer as string);
  if (summaryParts.length > 0) payload.issue_summary = summaryParts.join(" — ");

  return payload;
}
