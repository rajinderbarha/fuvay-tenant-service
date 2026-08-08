/**
 * Service price-display state machine (Level 5 Home spec "SERVICE PRICE
 * PRESENTATION"). FORWARD-LOOKING INFRASTRUCTURE: confirmed this task
 * that `GET /v1/customer/home`'s `bookable_categories` carries NO price
 * field at all (category_id/name/code/icon_url only -- see
 * api/contracts/customerHome.ts header comment), so nothing in the Home
 * screen currently feeds this function with real data. It is built and
 * fully tested now so the day a category/service listing endpoint adds a
 * price projection, only an adapter needs to map that field onto
 * `ServicePriceState` -- no UI/display-rule code needs to change.
 *
 * `standard_price` (the field name confirmed elsewhere in the backend --
 * app/engines/home_service_booking/service.py, only reachable through an
 * in-progress booking draft, not a Home listing) is a Decimal that CAN be
 * exactly `0.0` for a real tenant/service combination -- this function
 * treats zero as "no valid price" the same as null, never as "free"
 * (spec: "Never display ₹0" / "Never display Free unless the backend
 * explicitly classifies the service as free" -- there is no such explicit
 * free-classification field anywhere in the backend today, so `isFree`
 * defaults to false and is never inferred from a zero amount).
 */
import { Money, formatMoney } from "./money";

export type ServicePriceState =
  | { kind: "valid"; amount: Money }
  | { kind: "inspection_based" }
  | { kind: "detail_dependent" }
  | { kind: "quote_required" }
  | { kind: "free" }
  | { kind: "unavailable" };

export interface ServicePriceDisplay {
  label: string;
  /** True only for `kind: "valid"` -- screen readers should not be told
   * "starting at" for a non-numeric state. */
  isNumericPrice: boolean;
}

/**
 * Never infers a price state from a raw number alone -- the CALLER is
 * responsible for classifying a raw backend value into one of these
 * `kind`s first (e.g. `amount > 0 ? {kind:"valid", amount} : {kind:
 * "unavailable"}` is an acceptable classification a future adapter would
 * do, but doing it silently inside a display function would hide the
 * classification decision from review).
 */
export function resolveServicePriceDisplay(state: ServicePriceState): ServicePriceDisplay {
  switch (state.kind) {
    case "valid":
      return { label: `From ${formatMoney(state.amount)}`, isNumericPrice: true };
    case "inspection_based":
      return { label: "Inspection-based", isNumericPrice: false };
    case "detail_dependent":
      return { label: "Price after details", isNumericPrice: false };
    case "quote_required":
      return { label: "Quote after inspection", isNumericPrice: false };
    case "free":
      return { label: "Free", isNumericPrice: false };
    case "unavailable":
      return { label: "Price unavailable", isNumericPrice: false };
  }
}

/** Classifies a raw, possibly-absent backend amount defensively -- zero,
 * null, undefined and negative all become `unavailable`, never `valid`
 * and never `free` (spec: "Never display ₹0"). */
export function classifyRawAmount(rawMinorUnits: number | null | undefined, currency: string = "INR"): ServicePriceState {
  if (rawMinorUnits == null || rawMinorUnits <= 0) {
    return { kind: "unavailable" };
  }
  return { kind: "valid", amount: { minorUnits: rawMinorUnits, currency } };
}

export interface InspectionPricing {
  visitFee: Money;
  /** True only when the backend's own snapshot carries fee-adjustment
   * policy wording -- never rendered unless the backend actually said so. */
  feeAdjustmentNote: string | null;
  /**
   * The platform's structured guarantee that this visit fee is credited
   * against the work if the customer goes ahead. Backend-authored (it lives
   * beside the billing code that honours it), so the app states it as a
   * promise the system actually keeps rather than as marketing copy. Null
   * when the backend did not assert it -- the app must then say nothing.
   */
  visitFeePolicy: {
    creditedAgainstWork: boolean;
    creditedWhen: string;
    condition: string;
    ifDeclined: string;
  } | null;
}

/**
 * Booking-Review classification (Service Match/Review/Confirmation phase).
 * Confirmed via direct source read of `HomeServiceChatbotBookingService`:
 * `resolve_price_estimate` (draft.price_snapshot.requires_inspection_estimate
 * / visit_fee / customer_message) and `match_provider_and_price`
 * (bargain_available / standard_price / price_options) both merge INTO the
 * same `draft.price_snapshot` (match-and-price spreads the existing
 * snapshot rather than replacing it), so `build_booking_summary`'s
 * `price_estimate` field carries every one of these keys together by the
 * time Review loads. Bargain/Low-Mid-High tier selection is explicitly out
 * of scope for this phase (mission statement: "Do not build ... bargaining
 * ... in this phase") -- a bargain-available draft is surfaced as
 * `quote_required` here rather than a fabricated single price.
 */
export function classifyReviewPricing(input: {
  requiresInspectionEstimate: boolean;
  visitFeeRaw: number | null;
  feeAdjustmentNote: string | null;
  visitFeePolicy?: InspectionPricing["visitFeePolicy"];
  bargainAvailable: boolean;
  standardPriceRaw: number | null;
  currency?: string;
}): { state: ServicePriceState; inspection: InspectionPricing | null } {
  const currency = input.currency ?? "INR";
  if (input.requiresInspectionEstimate) {
    if (input.visitFeeRaw != null && input.visitFeeRaw > 0) {
      return {
        state: { kind: "inspection_based" },
        inspection: {
          visitFee: { minorUnits: Math.round(input.visitFeeRaw * 100), currency },
          feeAdjustmentNote: input.feeAdjustmentNote,
          visitFeePolicy: input.visitFeePolicy ?? null,
        },
      };
    }
    return { state: { kind: "unavailable" }, inspection: null };
  }
  if (input.bargainAvailable) {
    return { state: { kind: "quote_required" }, inspection: null };
  }
  if (input.standardPriceRaw != null && input.standardPriceRaw > 0) {
    return {
      state: { kind: "valid", amount: { minorUnits: Math.round(input.standardPriceRaw * 100), currency } },
      inspection: null,
    };
  }
  return { state: { kind: "unavailable" }, inspection: null };
}
