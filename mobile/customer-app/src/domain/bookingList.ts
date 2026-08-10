import { ServerTimestamp } from "./dates";

/** How soon a booking needs attention. The SERVER decides this (see
 * `home_service_assignment/urgency.py`) so the customer's list and the provider's
 * dashboard can never disagree about which visits are late. */
export type BookingUrgency = "late" | "today" | "upcoming" | "unscheduled";
import { BookingReceiptStage } from "./bookingStatus";
import { FinalizedPricingPresentation, ReceiptAddress } from "./bookingReceipt";

export interface BookingSummaryField {
  key: string;
  label: string;
  value: string;
  /** The question's real `input_type` from the catalog (see
   * admin_catalog/question_service.py's INPUT_TYPES). Used to tell a
   * free-text answer -- rendered as its own "Additional Detail" note --
   * apart from a chosen-option answer, rendered as a chip. Never used to
   * decide anything backend-authoritative, only display grouping. */
  questionType: string;
}

/** One card's worth of real, adapted data -- never raw DTO interpretation
 * in JSX (spec section 3). Deliberately does NOT duplicate the status/
 * pricing adapters -- both are imported from Booking Details' modules. */
export interface CustomerBookingListItem {
  bookingId: string;
  bookingNumber: string | null;
  rawStatus: string;
  stage: BookingReceiptStage;
  statusLabel: string;
  activityText: string | null;
  supportingText: string | null;
  createdAt: ServerTimestamp | null;
  serviceName: string | null;
  jobType: string | null;
  summaryFields: BookingSummaryField[];
  address: ReceiptAddress;
  pricing: FinalizedPricingPresentation;
  /** Null for finished work, and on an older backend that does not send it -- the list
   * then simply renders ungrouped rather than guessing. */
  urgency: BookingUrgency | null;
  /** The COMMITTED slot, not what the customer asked for. */
  scheduledDate: string | null;
  scheduledTimeWindow: string | null;
  /** "2 days late", worded by the server. */
  latenessLabel: string | null;
}

export interface BookingListCounts {
  active: number;
  completed: number;
  all: number;
}

export interface BookingListPage {
  items: CustomerBookingListItem[];
  total: number;
  /** Authoritative for ALL three buckets, every response -- never derive
   * a tab count from a partial/paginated fetch (spec closure item 1). */
  counts: BookingListCounts;
}
