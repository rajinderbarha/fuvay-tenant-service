import { apiClient } from "../../../api/api-client";
import type { PriceTier } from "../domain/bargain-schema";

/**
 * Real path verified against
 * app/engines/home_service_booking/customer_router.py — see
 * CUSTOMER-L5-10-contract-matrix.md. Sends only a tier name, never a raw
 * amount — the backend resolves and stores the exact amount from its own
 * already-computed price_options.
 */
export const bargainApi = {
  confirmPriceChoice: (draftId: string, priceTier: PriceTier, options: { signal?: AbortSignal } = {}) =>
    apiClient.post<unknown>(
      `/v1/customer/home-services/booking-drafts/${encodeURIComponent(draftId)}/confirm-price-choice`,
      { price_tier: priceTier },
      { signal: options.signal }
    ),
};
