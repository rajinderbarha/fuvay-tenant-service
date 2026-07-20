import type { ValidatedBookingDraft } from "../../booking-draft/domain/draft-schema";
import { isPastExpiry } from "../../booking-draft/domain/draft-schema";

export type PricingPreflightResult = { ready: true } | { ready: false; reasonKey: string };

/**
 * Pure, client-side precondition check against the already-fetched draft —
 * there is no separate backend "preflight" endpoint (see
 * CUSTOMER-L5-09-pricing-architecture.md for why). Mirrors the exact real
 * preconditions `match-and-price` itself enforces server-side
 * (draft not terminal, a resolved provider match) plus the ones earlier
 * screens in this app's real flow already guarantee by the time this
 * screen is reachable (address selected, serviceable). Fails closed: any
 * unmet precondition blocks the request rather than sending it and hoping
 * for the best.
 */
export function evaluatePricingPreflight(draft: ValidatedBookingDraft | null | undefined, nowMs: number = Date.now()): PricingPreflightResult {
  if (!draft) return { ready: false, reasonKey: "pricing.preflight.draftMissing" };
  if (isPastExpiry(draft, nowMs)) return { ready: false, reasonKey: "pricing.preflight.draftExpired" };
  if (!draft.address_id) return { ready: false, reasonKey: "pricing.preflight.addressMissing" };
  if (draft.serviceability_status !== "serviceable") return { ready: false, reasonKey: "pricing.preflight.notServiceable" };
  if (draft.provider_match_status !== "matched" || !draft.selected_tenant_id) {
    return { ready: false, reasonKey: "pricing.preflight.providerNotMatched" };
  }
  return { ready: true };
}
