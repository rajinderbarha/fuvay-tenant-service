import { ServerTimestamp } from "./dates";
import { BookingReceiptStage } from "./bookingStatus";
import { ReceiptAddress, FinalizedPricingPresentation } from "./bookingReceipt";
import { NotificationCapability } from "./notificationCapability";
import { CustomerBookingEvent } from "./bookingActivity";

/** Reuses `BookingReceiptStage` from the Confirmation Receipt phase as
 * `CustomerBookingStage` (spec section 3: "Reuse the Booking Confirmation
 * status adapter instead of creating another mapping") -- this phase adds
 * no new proven stages beyond what that adapter already resolves. */
export type CustomerBookingStage = BookingReceiptStage;

export interface CustomerBookingAnswer {
  id: string;
  label: string;
  value: string;
}

export interface CustomerAttachment {
  id: string;
  url: string;
}

/** ACTIVE-BOOKING-DETAILS phase -- customer-safe projection of the real
 * ServiceJob, sourced from `_customer_safe_job` (see contracts/
 * customerBookings.ts). `rawStage` is the backend's own `map_job_status`
 * key (e.g. "assignment", "inspection", "completed") -- never rendered
 * directly; always passed through `resolveActiveJobStage` first. */
export interface CustomerJobTechnician {
  displayName: string;
  designation: string | null;
  photoUrl: string | null;
}

/** Sourced from the SAME atomic `completion_data` `complete_job()` writes
 * -- only the three customer-facing fields (never photo/signature ids,
 * `completed_by_staff_id`, or `technician_note`). */
export interface CustomerJobCompletion {
  workSummary: string | null;
  collectedAmount: number | null;
  completedAt: string | null;
}

export interface CustomerActiveJob {
  jobId: string;
  rawStage: string;
  rawStatus: string;
  scheduledDate: string | null;
  scheduledTimeWindow: string | null;
  technician: CustomerJobTechnician | null;
  completion: CustomerJobCompletion | null;
}

export interface CustomerBookingDetails {
  bookingId: string;
  bookingNumber: string | null;
  stage: CustomerBookingStage;
  statusLabel: string;
  activityText: string | null;
  supportingText: string | null;
  createdAt: ServerTimestamp | null;
  updatedAt: ServerTimestamp | null;
  job: CustomerActiveJob | null;
  service: {
    name: string | null;
    jobType: string | null;
    inspectionRequired: boolean;
    issueSummary: string | null;
    answers: CustomerBookingAnswer[];
  };
  address: ReceiptAddress;
  pricing: FinalizedPricingPresentation;
  attachments: CustomerAttachment[];
  note: string | null;
  activity: CustomerBookingEvent[];
  notifications: NotificationCapability;
}
