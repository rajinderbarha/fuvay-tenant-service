/**
 * In-memory draft for the 3-step Create Support Request wizard. Nothing
 * here is persisted to AsyncStorage/secure storage (spec section 3) --
 * it lives only in navigation params and component state for the
 * lifetime of the wizard, and is discarded on cancel or submission.
 *
 * Only fields the real backend create route
 * (`POST /v1/customer/complaints`) actually accepts are modeled here:
 * `record_type`/`record_id` (the linked booking), `complaint_type`
 * (`categoryCode`), and `description`/`title`. There is no
 * `customerId` field -- identity always comes from the authenticated
 * session server-side, never the draft. No status/priority/assignee
 * field exists because the backend never accepts one from a customer.
 * `attachmentIds` stays permanently empty -- no customer-reachable
 * attachment route exists (confirmed during the Step 2 audit).
 */
export interface SupportRequestDraft {
  categoryCode: string | null;
  bookingId: string | null;
  subject: string;
  description: string;
  attachmentIds: string[];
}

export function createEmptySupportRequestDraft(): SupportRequestDraft {
  return { categoryCode: null, bookingId: null, subject: "", description: "", attachmentIds: [] };
}

/** Explicit submission allowlist (spec section 6) -- only the 4 real
 * fields the backend accepts (`app/engines/complaints/customer_router.py`
 * `CreateComplaintIn`) are ever built here. `customer_id`/`tenant_id`
 * are never in this object because there is no field for the frontend
 * to even populate; the backend derives both from the authenticated
 * session server-side. There is likewise no `status`/`priority`/
 * `assigned_to`/`sla`/`refund_status`/`resolution`/audit field on the
 * real create schema for a customer to send. `record_type` is always
 * `"service_booking"` since the booking picker is the only linkage UI
 * built (spec's other real `record_type` values -- job/invoice/
 * coaching/lead/review -- have no picker in this app). */
export function buildCreateSupportRequestPayload(
  draft: SupportRequestDraft, complaintType: string,
): { record_type: "service_booking"; record_id: string; complaint_type: string; description: string; title?: string } {
  const trimmedTitle = draft.subject.trim();
  return {
    record_type: "service_booking",
    record_id: draft.bookingId as string,
    complaint_type: complaintType,
    description: draft.description.trim(),
    ...(trimmedTitle ? { title: trimmedTitle } : {}),
  };
}

export function isSupportRequestDraftDirty(draft: SupportRequestDraft): boolean {
  return draft.categoryCode !== null || draft.bookingId !== null
    || draft.subject.trim().length > 0 || draft.description.trim().length > 0
    || draft.attachmentIds.length > 0;
}

/** The real DB column limit (`title = Column(String(300))` in
 * `app/engines/complaints/models.py`) -- title is optional server-side,
 * so an empty title is valid, but a non-empty one must not exceed this.
 * `description` (`Column(Text, nullable=False)`) has no real backend
 * length ceiling, so no authoritative max is asserted for it here. */
export const SUPPORT_REQUEST_TITLE_MAX_LENGTH = 300;

/** Rejects C0 control characters other than tab/newline/carriage-return,
 * plus DEL -- built from char codes rather than a literal regex range so
 * no invisible byte ends up in source. Legitimate Unicode text
 * (including Punjabi/Hindi script) never contains these. */
export function hasControlCharacters(value: string): boolean {
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i);
    const isC0Control = code <= 0x1f && code !== 0x09 && code !== 0x0a && code !== 0x0d;
    if (isC0Control || code === 0x7f) return true;
  }
  return false;
}

export interface SupportRequestDetailsValidation {
  titleError: string | null;
  descriptionError: string | null;
  isValid: boolean;
}

/** Shared validation for Step 2 -- title is optional (backend never
 * requires it) but must respect the real 300-char column limit and
 * reject control characters; description is required non-empty
 * (whitespace-only rejected) with no fabricated backend maximum. */
export function validateSupportRequestDetails(title: string, description: string): SupportRequestDetailsValidation {
  const trimmedTitle = title.trim();
  const trimmedDescription = description.trim();

  let titleError: string | null = null;
  if (trimmedTitle.length > SUPPORT_REQUEST_TITLE_MAX_LENGTH) {
    titleError = `Title must be ${SUPPORT_REQUEST_TITLE_MAX_LENGTH} characters or fewer.`;
  } else if (hasControlCharacters(title)) {
    titleError = "Title contains characters that aren't allowed.";
  }

  let descriptionError: string | null = null;
  if (!trimmedDescription) {
    descriptionError = "Tell us what happened.";
  } else if (hasControlCharacters(description)) {
    descriptionError = "Description contains characters that aren't allowed.";
  }

  return { titleError, descriptionError, isValid: !titleError && !descriptionError };
}
