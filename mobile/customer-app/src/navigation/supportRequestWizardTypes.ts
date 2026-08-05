/** Nested param list for the 3-step Create Support Request wizard --
 * separate from `CustomerAppStackParamList` since the draft now lives in
 * `SupportRequestWizardContext`, not navigation params (spec section 2:
 * `CreateSupportRequestDetails: undefined`). Only the entry screen
 * (`Topic`) receives real params, forwarded from the outer stack's
 * `CreateSupportRequest` route. */
export type SupportRequestWizardParamList = {
  Topic: { source?: "help_hub" | "support_requests" | "booking"; bookingId?: string } | undefined;
  Details: undefined;
  Review: undefined;
};
