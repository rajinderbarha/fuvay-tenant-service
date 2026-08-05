import { IconProps } from "../components/Icon";

export interface CustomerNotificationTypePresentation {
  icon: IconProps["name"];
}

/** Closed mapper over every real customer-facing `notification_type`
 * confirmed during the In-App Notification Center audit (every
 * `InAppNotification(...)` call site in the backend whose recipient is a
 * customer). Icon choice is purely presentational -- it never drives
 * navigation; `resolveSafeNotificationDestination` does that from
 * `source_record_type`/`source_record_id` alone. An unmapped type falls
 * back to a neutral bell rather than guessing. */
const TYPE_ICON: Record<string, IconProps["name"]> = {
  "booking.confirmed": "briefcase-outline",
  "complaint.filed": "shield-checkmark-outline",
  "complaint.resolution_offered": "shield-checkmark-outline",
  "complaint.resolution_proposed": "shield-checkmark-outline",
  "complaint.rejected": "shield-checkmark-outline",
  "complaint.resolved": "shield-checkmark-outline",
  "complaint.settlement_proposed": "shield-checkmark-outline",
  "complaint.ai_settlement_proposed": "shield-checkmark-outline",
  "complaint.settlement_paid": "shield-checkmark-outline",
  "invoice.issued": "document-text-outline",
  "quote.sent": "receipt-outline",
  "review.reply": "star-outline",
  "chat.message": "chatbubble-outline",
};

export function resolveCustomerNotificationType(rawType: string): CustomerNotificationTypePresentation {
  return { icon: TYPE_ICON[rawType] ?? "notifications-outline" };
}
