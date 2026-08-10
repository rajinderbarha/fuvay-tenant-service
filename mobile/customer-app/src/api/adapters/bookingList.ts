import { ServiceBookingDto, BookingListResponseDto } from "../contracts/customerBookings";
import { CustomerBookingListItem, BookingListPage, BookingSummaryField } from "../../domain/bookingList";
import { interpretBookingStatus } from "../../domain/bookingStatus";
import { classifyReviewPricing } from "../../domain/servicePricing";
import { parseServerTimestamp } from "../../domain/dates";

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

/** Same versioned `answer_snapshot` source as Booking Details -- never
 * re-derived, never re-humanized from a raw key (see that adapter's
 * comment for the full audit trail). */
function adaptSummaryFields(dto: ServiceBookingDto): BookingSummaryField[] {
  if (!dto.answer_snapshot) return [];
  return [...dto.answer_snapshot.answers]
    .sort((a, b) => a.sequence - b.sequence)
    .map(a => ({ key: a.question_id, label: a.question_label, value: a.answer_label, questionType: a.question_type }));
}

export function adaptBookingListItem(dto: ServiceBookingDto): CustomerBookingListItem {
  const interpretation = interpretBookingStatus(dto.status, dto.assignment_status);
  const priceSnapshot = (dto.price_snapshot ?? {}) as Record<string, unknown>;
  const { state, inspection } = classifyReviewPricing({
    requiresInspectionEstimate: !!priceSnapshot.requires_inspection_estimate,
    visitFeeRaw: typeof priceSnapshot.visit_fee === "number" ? priceSnapshot.visit_fee : null,
    feeAdjustmentNote: typeof priceSnapshot.customer_message === "string" ? priceSnapshot.customer_message : null,
    // Historical snapshots predate `visit_fee_policy`; asserting the
    // guarantee here would be claiming something this record never carried.
    visitFeePolicy: null,
    bargainAvailable: !!priceSnapshot.bargain_available,
    standardPriceRaw: typeof priceSnapshot.standard_price === "number" ? priceSnapshot.standard_price : null,
  });

  return {
    bookingId: dto.id,
    bookingNumber: dto.booking_number,
    rawStatus: dto.status,
    stage: interpretation.stage,
    statusLabel: interpretation.statusLabel,
    activityText: interpretation.activityText,
    supportingText: interpretation.supportingText,
    createdAt: dto.created_at ? parseServerTimestamp(dto.created_at, "created_at") : null,
    serviceName: dto.offering_name ?? dto.category_name ?? null,
    jobType: dto.job_type_label ?? null,
    summaryFields: adaptSummaryFields(dto),
    address: formatAddress(dto.address_snapshot, dto.city, dto.zipcode),
    pricing: { state, inspection },
    // Straight through from the server, never re-derived here. The provider's dashboard
    // reads the same field from the same rule, so the two cannot disagree about which
    // visits are late.
    urgency: dto.urgency ?? null,
    scheduledDate: dto.scheduled_date ?? null,
    scheduledTimeWindow: dto.scheduled_time_window ?? null,
    latenessLabel: dto.lateness_label ?? null,
  };
}

export function adaptBookingListPage(dto: BookingListResponseDto): BookingListPage {
  return { items: dto.items.map(adaptBookingListItem), total: dto.total, counts: dto.counts };
}
