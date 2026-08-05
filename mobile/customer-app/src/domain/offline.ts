/**
 * Offline-operation classification (Phase A-C foundation section 10,
 * completed here per Phase D section 18). Every customer mutation this
 * app will ever perform must be tagged with exactly one of these classes,
 * and `MUTATION_SAFETY` below is the single registry of that mapping so a
 * future mutation hook can look up the right behavior instead of a screen
 * author guessing.
 */
export type OfflineOperationClass =
  | "LOCAL_DRAFT"
  | "MEDIA_UPLOAD"
  | "IDEMPOTENT_MUTATION"
  | "ONLINE_ONLY_MUTATION";

export type CustomerMutationKey =
  | "bookingDraft.update"
  | "bookingDraft.attachPhoto"
  | "bookingDraft.serviceabilityCheck"
  | "bookingDraft.priceEstimate"
  | "bookingDraft.confirmPriceChoice"
  | "bookingDraft.confirm"
  | "booking.cancel"
  | "booking.reschedule"
  | "quote.approve"
  | "quote.reject"
  | "quote.requestRevision"
  | "review.submit"
  | "address.create"
  | "address.update"
  | "address.delete"
  | "address.setDefault"
  | "notification.markRead"
  | "notification.markAllRead"
  | "chat.sendMessage"
  | "profile.update";

/**
 * Evidence for each entry:
 *  - bookingDraft.* before confirm: the draft is server-created but still
 *    mutable pre-finalization (home_service_booking/customer_router.py PUT
 *    .../booking-drafts/{id}) -- safe to hold as a local draft between
 *    edits, but every write still round-trips the server; this app must
 *    never show a draft edit as saved before that PUT succeeds.
 *  - bookingDraft.confirm: creates ServiceBooking + ServiceJob
 *    (home_service_booking/customer_router.py, confirmed idempotent via
 *    draft-status guard) -- ONLINE_ONLY, must never appear to succeed
 *    without a live response.
 *  - booking.cancel / booking.reschedule: home_service_assignment/
 *    customer_router.py -- state-changing, guarded by cancellable-status
 *    checks server-side; must not be retried blindly (a retried cancel
 *    after a network blip could hit a job that has since moved past the
 *    cancellable window and receive a confusing 409) -- ONLINE_ONLY.
 *  - quote.approve: requires an `Idempotency-Key` header
 *    (quote_checklist/customer_router.py) -- the one mutation in this set
 *    with a verified idempotency mechanism, so it is safe to retry with
 *    the SAME key, never with a new one.
 *  - quote.reject / requestRevision: same router, no Idempotency-Key
 *    parameter observed -- treat as online-only until one is added.
 */
export const MUTATION_SAFETY: Record<CustomerMutationKey, OfflineOperationClass> = {
  "bookingDraft.update": "LOCAL_DRAFT",
  "bookingDraft.attachPhoto": "MEDIA_UPLOAD",
  "bookingDraft.serviceabilityCheck": "ONLINE_ONLY_MUTATION",
  "bookingDraft.priceEstimate": "ONLINE_ONLY_MUTATION",
  "bookingDraft.confirmPriceChoice": "ONLINE_ONLY_MUTATION",
  "bookingDraft.confirm": "ONLINE_ONLY_MUTATION",
  "booking.cancel": "ONLINE_ONLY_MUTATION",
  "booking.reschedule": "ONLINE_ONLY_MUTATION",
  "quote.approve": "IDEMPOTENT_MUTATION",
  "quote.reject": "ONLINE_ONLY_MUTATION",
  "quote.requestRevision": "ONLINE_ONLY_MUTATION",
  "review.submit": "ONLINE_ONLY_MUTATION",
  "address.create": "ONLINE_ONLY_MUTATION",
  "address.update": "ONLINE_ONLY_MUTATION",
  "address.delete": "ONLINE_ONLY_MUTATION",
  "address.setDefault": "ONLINE_ONLY_MUTATION",
  "notification.markRead": "IDEMPOTENT_MUTATION",
  "notification.markAllRead": "IDEMPOTENT_MUTATION",
  "chat.sendMessage": "ONLINE_ONLY_MUTATION",
  "profile.update": "ONLINE_ONLY_MUTATION",
};

export function offlinePolicyFor(key: CustomerMutationKey): OfflineOperationClass {
  return MUTATION_SAFETY[key];
}

/** True for the classes that must NEVER render an optimistic "success"
 * state before the backend responds. */
export function requiresLiveConfirmation(cls: OfflineOperationClass): boolean {
  return cls === "ONLINE_ONLY_MUTATION" || cls === "IDEMPOTENT_MUTATION";
}
