import { ServerTimestamp } from "./dates";
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
