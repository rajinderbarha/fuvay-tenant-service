import { queryClient } from "../queryClient";
import { discardBookingDraft } from "../../storage/draft/bookingDraftPersistence";
import { clearPersistedNavigationState } from "../../navigation/navigationPersistence";
import { CustomerId } from "../../domain/ids";

/**
 * Query-cache security (spec section 29). Called on logout, account
 * suspension, invalid audience, or terminal session failure -- cancels
 * every in-flight protected query and wipes the cache outright rather
 * than trying to selectively invalidate keys, since Phase D's query-key
 * factory scopes everything customer-owned and there is no per-key
 * allowlist of "safe to keep" data once identity is no longer trusted.
 */
export async function clearProtectedState(previousCustomerId?: CustomerId): Promise<void> {
  await queryClient.cancelQueries();
  queryClient.clear();
  await clearPersistedNavigationState();
  if (previousCustomerId) {
    await discardBookingDraft(previousCustomerId);
  }
}

/**
 * Called when a DIFFERENT customer signs in on the same device (spec
 * section 29's "reuse" prohibition). Identical to `clearProtectedState`
 * today because Phase D's query keys already scope by customer/entity
 * ID rather than relying on an ambient "current customer" -- there is
 * nothing safe to carry forward across identities, so this is a full
 * clear, not a selective one.
 */
export async function clearStateForCustomerSwitch(previousCustomerId?: CustomerId): Promise<void> {
  await clearProtectedState(previousCustomerId);
}
