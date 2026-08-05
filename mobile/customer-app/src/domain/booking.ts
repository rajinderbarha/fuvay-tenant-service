import { ServiceBookingId, BookingDraftId, CustomerId, TenantId, CategoryId } from "./ids";
import { BookingStatus, AssignmentStatus } from "./status";
import { ServerDate, ServerTimestamp } from "./dates";
import { Money } from "./money";

/** Customer-safe provider info only -- never internal_score,
 * matching_score_snapshot or admin price range (see
 * home_service_assignment/customer_router.py `_customer_safe_provider`). */
export interface BookingProviderSummary {
  providerName: string | null;
  rating: number | null;
  publicBadges: string[];
}

export interface ServiceBooking {
  id: ServiceBookingId;
  bookingNumber: string;
  draftId: BookingDraftId;
  customerId: CustomerId | null;
  tenantId: TenantId | null;
  categoryId: CategoryId;
  customerName: string | null;
  city: string | null;
  zipcode: string | null;
  preferredDate: ServerDate | null;
  preferredTimeWindow: string | null;
  agreedPrice: Money | null;
  provider: BookingProviderSummary | null;
  status: BookingStatus;
  assignmentStatus: AssignmentStatus;
  failureReason: string | null;
  createdAt: ServerTimestamp | null;
  updatedAt: ServerTimestamp | null;
}
