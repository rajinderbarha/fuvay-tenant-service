import { BookingDraftId } from "./ids";
import { ServerTimestamp } from "./dates";

export interface BookingDraftSummary {
  id: BookingDraftId;
  aiSessionId: string | null;
  status: string;
  city: string | null;
  zipcode: string | null;
  issueSummary: string | null;
  serviceabilityStatus: string | null;
  priceStatus: string | null;
  categoryName: string | null;
  offeringName: string | null;
  jobTypeLabel: string | null;
  createdAt: ServerTimestamp | null;
}
