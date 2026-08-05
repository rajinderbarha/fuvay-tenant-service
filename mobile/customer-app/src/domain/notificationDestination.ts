import { SafeNotificationDestination } from "./notification";

/**
 * Explicit destination allowlist (spec section 11). Never opens
 * `action_url`, an internal backend web path, and never parses the
 * customer-visible title/body for a route. Only `source_record_type` +
 * `source_record_id` -- both real, ID-shaped backend fields -- decide the
 * destination, and only for the two types with a matching real screen.
 * Every other `source_record_type` (or a missing id) resolves to `null`,
 * which the screen renders as non-interactive.
 */
export function resolveSafeNotificationDestination(
  sourceRecordType: string | null,
  sourceRecordId: string | null,
): SafeNotificationDestination | null {
  if (!sourceRecordId) return null;
  switch (sourceRecordType) {
    case "service_bookings":
      return { kind: "booking", bookingId: sourceRecordId };
    case "customer_complaints":
      return { kind: "supportRequest", requestId: sourceRecordId };
    default:
      return null;
  }
}
