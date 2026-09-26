import type { InAppNotificationItem } from "./api";

/**
 * Resolve an in-app notification to a same-origin route only.
 *
 * `destination` is projected from a backend allow-list. The fallback keeps
 * historical notifications usable while explicitly repairing the retired
 * provider job-list URL and rejecting protocol-relative/external targets.
 */
export function notificationDestination(
  notification: Pick<InAppNotificationItem, "destination" | "action_url">,
): string | null {
  const candidate = notification.destination || notification.action_url;
  if (!candidate || !candidate.startsWith("/") || candidate.startsWith("//")) return null;
  if (candidate === "/service-jobs" || candidate === "/service-jobs/") {
    return "/home-services/bookings-jobs";
  }
  return candidate;
}
