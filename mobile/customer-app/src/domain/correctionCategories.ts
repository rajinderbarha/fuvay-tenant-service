/**
 * Data Correction Request phase audit finding: `POST /v1/me/compliance/
 * requests` (request_type=data_correction) has no category field, no
 * separate current-value/requested-value fields and no attachment
 * support -- only a single `reason: Text` column
 * (`app/engines/compliance/models.py` `ComplianceRequest.reason`). The
 * category selector is therefore a CLIENT-SIDE routing/context concept
 * only: it decides whether a field can be corrected immediately through
 * an existing real screen (`DIRECTLY_EDITABLE`) or must go through this
 * formal request (`PRIVACY_CORRECTION_SUPPORTED`), and its label is
 * prefixed into the one real `reason` field for the reviewer's context --
 * it is never submitted as a separate structured field that doesn't
 * exist on the backend.
 */
export type CorrectionCategoryCode =
  | "account_details" | "contact_information" | "address_information"
  | "booking_information" | "other";

export type CorrectionCapability = "direct_edit" | "formal_request";

export interface CorrectionCategoryPresentation {
  code: CorrectionCategoryCode;
  label: string;
  description: string;
  capability: CorrectionCapability;
  /** Only set when capability is "direct_edit". */
  directEditRoute?: "EditProfile" | "SavedAddresses";
  directEditActionLabel?: string;
}

/**
 * Full name/display name are the ONLY fields the real profile endpoint
 * lets a customer edit directly (`EditProfileScreen` audit: phone/email
 * are deliberately read-only there too -- no verified change flow exists
 * for either, confirmed in `app/engines/auth/router.py`, only login OTP).
 * Address fields have a real, existing direct-edit surface
 * (SavedAddresses/AddAddress/EditAddress). Everything else -- including
 * contact info, since it has no verified change flow -- has no direct-
 * edit path and must go through this formal request.
 */
export const CORRECTION_CATEGORIES: CorrectionCategoryPresentation[] = [
  {
    code: "account_details", label: "Account details",
    description: "Your name as it appears on your account.",
    capability: "direct_edit", directEditRoute: "EditProfile", directEditActionLabel: "Edit personal details",
  },
  {
    code: "contact_information", label: "Contact information",
    description: "Your phone number or email address.",
    capability: "formal_request",
  },
  {
    code: "address_information", label: "Address information",
    description: "A saved address on your account.",
    capability: "direct_edit", directEditRoute: "SavedAddresses", directEditActionLabel: "Manage addresses",
  },
  {
    code: "booking_information", label: "Booking or service information",
    description: "Details recorded against a past or current booking.",
    capability: "formal_request",
  },
  {
    code: "other", label: "Other personal data",
    description: "Anything else linked to your account.",
    capability: "formal_request",
  },
];

export function resolveCorrectionCategory(code: string): CorrectionCategoryPresentation | null {
  return CORRECTION_CATEGORIES.find(c => c.code === code) ?? null;
}

/** Combines the category context + the two form fields the approved
 * design shows into the single real `reason` field the backend accepts.
 * Never fabricates a structured backend field that doesn't exist. */
export function buildCorrectionReason(params: {
  categoryLabel: string; whatIsIncorrect: string; whatItShouldSay: string;
}): string {
  return [
    `Category: ${params.categoryLabel}`,
    `What is incorrect: ${params.whatIsIncorrect.trim()}`,
    `What it should say: ${params.whatItShouldSay.trim()}`,
  ].join("\n\n");
}

export const CORRECTION_FIELD_MAX_LENGTH = 500;
