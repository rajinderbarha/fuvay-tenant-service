import { NotificationId } from "./ids";
import { ServerTimestamp } from "./dates";

/** Only these two `source_record_type` values have a real, matching
 * customer-app route (In-App Notification Center audit of every real
 * notification-creation call site in the backend). Other real customer-
 * facing types exist (`service_invoices`, `service_job_quote`,
 * `customer_review`, `chat_thread`) but no Invoice/Quote/Review/Chat
 * screen exists in this app yet -- those notifications are rendered
 * safely but stay non-interactive rather than guessing a destination. */
export type SafeNotificationDestination =
  | { kind: "booking"; bookingId: string }
  | { kind: "supportRequest"; requestId: string };

export type CustomerNotificationReadStatus = "unread" | "read" | "archived";

export interface CustomerNotification {
  id: NotificationId;
  /** Raw backend type string (e.g. `booking.confirmed`) -- never rendered
   * directly to the customer; always passed through
   * `resolveCustomerNotificationType` first. */
  type: string;
  title: string;
  body: string;
  createdAt: ServerTimestamp;
  readAt: ServerTimestamp | null;
  readStatus: CustomerNotificationReadStatus;
  destination: SafeNotificationDestination | null;
}
