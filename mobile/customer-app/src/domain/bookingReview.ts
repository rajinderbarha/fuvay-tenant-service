import { BookingDraftId } from "./ids";
import { ServerDate } from "./dates";
import { ServicePriceState, InspectionPricing } from "./servicePricing";
import { Money } from "./money";

export interface ReviewProvider {
  tenantId: string;
  providerName: string;
  /** Backend-authored trust chips: `{name, icon?, color?}`. Never
   * fabricated client-side. */
  publicBadges: { name: string; icon?: string | null; color?: string | null }[];
  rating: number | null;
}

export interface ReviewAnswerField {
  key: string;
  label: string;
  value: string;
}

export interface ReviewAddress {
  city: string | null;
  zipcode: string | null;
  /** Passthrough display lines from `address_snapshot` -- whatever real
   * fields the backend stored (label/line1/line2/etc). Never fabricated
   * beyond what the snapshot actually carries. */
  lines: string[];
  serviceable: boolean;
  serviceabilityStatus: string | null;
}

/**
 * The Review domain model -- adapted from `build_booking_summary`'s
 * response (`HomeServiceChatbotBookingService.build_booking_summary`) plus
 * the enriched draft fields (`category_name`/`job_type_label` from
 * `_enrich_draft`, confirmed this task). No field here is invented; a
 * field the backend hasn't resolved yet is `null`, never guessed.
 */
export interface BookingReviewSummary {
  draftId: BookingDraftId;
  categoryName: string | null;
  offeringName: string;
  jobTypeLabel: string | null;
  issueSummary: string | null;
  answers: ReviewAnswerField[];
  address: ReviewAddress;
  priceState: ServicePriceState;
  inspection: InspectionPricing | null;
  bargainAvailable: boolean;
  provider: ReviewProvider | null;
  photoCount: number;
  /** The attached photo URLs themselves, so the review screen can show
   * thumbnails and let the customer remove one -- a count alone made the
   * attachments surface read-only. */
  photoUrls: string[];
  preferredDate: ServerDate | null;
  /** The real, capacity-checked slot the provider will honour, resolved
   * before confirmation. Null when the provider has no capacity in the
   * search horizon -- never a fabricated date. */
  promisedSlot: {
    date: string;
    timeWindow: string;
    startsAt: string;
    endsAt: string;
    slotMinutes: number;
    daysAhead: number;
  } | null;
  /** Minutes the provider is committing to, clock running from booking
   * creation -- provider-side allocation delay is never the customer's wait. */
  serviceSlaMinutes: number | null;
  serviceDueAt: string | null;
  /** True when the customer picked from the emergency (notice-waived) slot
   * list. `emergencySurcharge` is the provider's own configured rate, shown
   * before confirmation; null when they charge nothing extra. */
  isEmergency: boolean;
  emergencySurcharge: Money | null;
  readyForConfirmation: boolean;
  missing: string[];
}

/** One offer from GET /{draft_id}/available-slots -- the same shape
 * `promisedSlot` uses, minus the two informational-only capacity fields
 * (`capacity`/`already_booked`) that selecting a slot doesn't carry back
 * through `select-slot`'s response. */
export interface AvailableSlot {
  date: string;
  timeWindow: string;
  daysAhead: number;
}
