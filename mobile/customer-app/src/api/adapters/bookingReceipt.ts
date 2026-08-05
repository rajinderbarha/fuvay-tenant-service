import { ServiceBookingDto } from "../contracts/customerBookings";
import { BookingReceipt } from "../../domain/bookingReceipt";
import { interpretBookingStatus } from "../../domain/bookingStatus";
import { classifyReviewPricing } from "../../domain/servicePricing";
import { resolveNotificationCapability } from "../../domain/notificationCapability";

function formatAddress(snapshot: Record<string, unknown> | null, city: string | null, zipcode: string | null) {
  const lines = ["line1", "line2", "label", "landmark"]
    .map(key => snapshot?.[key])
    .filter((v): v is string => typeof v === "string" && v.trim().length > 0);
  const cityZip = [city, zipcode].filter(Boolean).join(", ");
  const formatted = [...lines, cityZip].filter(Boolean).join(", ");
  return {
    label: typeof snapshot?.label === "string" ? snapshot.label : null,
    formatted: formatted || "Address not available",
    zipcode,
  };
}

/**
 * Adapts the finalized `ServiceBooking.to_dict()` into the Receipt domain
 * model. `provider_snapshot` is read from the DTO but NEVER surfaced here
 * (staff-dependent safety boundary, spec section 5) -- that omission is
 * enforced structurally: this function has no code path that reads it.
 */
export function adaptBookingReceipt(dto: ServiceBookingDto): BookingReceipt {
  const interpretation = interpretBookingStatus(dto.status, dto.assignment_status);
  const priceSnapshot = (dto.price_snapshot ?? {}) as Record<string, unknown>;
  const { state, inspection } = classifyReviewPricing({
    requiresInspectionEstimate: !!priceSnapshot.requires_inspection_estimate,
    visitFeeRaw: typeof priceSnapshot.visit_fee === "number" ? priceSnapshot.visit_fee : null,
    feeAdjustmentNote: typeof priceSnapshot.customer_message === "string" ? priceSnapshot.customer_message : null,
    bargainAvailable: !!priceSnapshot.bargain_available,
    standardPriceRaw: typeof priceSnapshot.standard_price === "number" ? priceSnapshot.standard_price : null,
  });

  return {
    bookingId: dto.id,
    bookingNumber: dto.booking_number,
    currentStage: interpretation.stage,
    statusLabel: interpretation.statusLabel,
    activityText: interpretation.activityText,
    supportingText: interpretation.supportingText,
    service: {
      name: dto.offering_name ?? dto.category_name ?? null,
      jobType: dto.job_type_label ?? null,
      issueSummary: dto.issue_summary,
      answers: [],
    },
    address: formatAddress(dto.address_snapshot, dto.city, dto.zipcode),
    pricing: { state, inspection },
    notificationCapability: resolveNotificationCapability(),
    preferredDate: null,
  };
}
