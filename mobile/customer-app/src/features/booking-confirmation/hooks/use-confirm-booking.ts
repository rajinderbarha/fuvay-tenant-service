import { useRef, useState } from "react";
import { useConfirmBooking } from "../queries/booking-confirmation-queries";
import { categorizeConfirmFailure, type ConfirmState } from "../domain/booking-state";
import { logger } from "../../../observability/logger";

function newIdempotencyKey(): string {
  return `bkconf_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 12)}`;
}

/**
 * Owns the confirm-booking submission and its stable idempotency key.
 * The key is generated once (on first submit) and held for the lifetime
 * of this hook instance — a retry after an uncertain outcome reuses the
 * exact same key, never a fresh one (CUSTOMER-L5-11 §26's hard
 * requirement: "same key reused after uncertain timeout... new key not
 * generated on every retry"). The key is never logged (see
 * CUSTOMER-L5-11-security-review.md).
 */
export function useConfirmBookingFlow(draftId: string) {
  const confirmMutation = useConfirmBooking();
  const idempotencyKeyRef = useRef<string | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);

  function confirm() {
    if (!idempotencyKeyRef.current) idempotencyKeyRef.current = newIdempotencyKey();
    setHasSubmitted(true);
    confirmMutation.mutate({ draftId, idempotencyKey: idempotencyKeyRef.current });
  }

  const state: ConfirmState = (() => {
    if (!hasSubmitted) return { kind: "idle" };
    if (confirmMutation.isPending) return { kind: "confirming" };
    if (confirmMutation.isSuccess && confirmMutation.data) return { kind: "confirmed", result: confirmMutation.data };
    if (confirmMutation.isError) {
      const outcome = categorizeConfirmFailure(confirmMutation.error.category);
      if (outcome === "uncertain") logger.warn("booking_create_timeout", {});
      return { kind: outcome };
    }
    return { kind: "idle" };
  })();

  return { state, confirm };
}
