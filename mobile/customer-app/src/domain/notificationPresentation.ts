import { CustomerNotification } from "./notification";
import { ServerTimestamp, toDisplayDate } from "./dates";

/** Never inferred from local tap history -- `read_status` is the real
 * backend field (spec section 9). */
export function isNotificationUnread(notification: CustomerNotification): boolean {
  return notification.readStatus === "unread";
}

export interface NotificationVisual {
  unread: boolean;
  titleWeight: "strong" | "regular";
  /** Accessible label announcing read state -- unread is never conveyed
   * by color alone. */
  accessibilityStateLabel: string;
}

export function resolveNotificationVisual(notification: CustomerNotification): NotificationVisual {
  const unread = isNotificationUnread(notification);
  return {
    unread,
    titleWeight: unread ? "strong" : "regular",
    accessibilityStateLabel: unread ? "Unread" : "Read",
  };
}

export type NotificationGroupLabel = "Today" | "Yesterday" | "Earlier";

function isSameCalendarDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** Groups by the device's local calendar day (spec section 8) -- real
 * `created_at` timestamps only, never a client-side arrival guess. Stable
 * for equal timestamps because it never reorders `notifications`; it only
 * partitions the already-ordered list the backend returned. */
export function groupNotificationsByDay(
  notifications: CustomerNotification[],
  now: Date = new Date(),
): Array<{ label: NotificationGroupLabel; items: CustomerNotification[] }> {
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);

  const today: CustomerNotification[] = [];
  const yesterdayItems: CustomerNotification[] = [];
  const earlier: CustomerNotification[] = [];

  for (const n of notifications) {
    const created = toDisplayDate(n.createdAt as ServerTimestamp);
    if (isSameCalendarDay(created, now)) today.push(n);
    else if (isSameCalendarDay(created, yesterday)) yesterdayItems.push(n);
    else earlier.push(n);
  }

  const groups: Array<{ label: NotificationGroupLabel; items: CustomerNotification[] }> = [];
  if (today.length) groups.push({ label: "Today", items: today });
  if (yesterdayItems.length) groups.push({ label: "Yesterday", items: yesterdayItems });
  if (earlier.length) groups.push({ label: "Earlier", items: earlier });
  return groups;
}

/** `1 unread` / `{N} unread` grammar (spec section 5). Zero is handled by
 * the caller hiding the badge entirely, never by rendering "0 unread". */
export function formatUnreadCount(count: number): string {
  return count === 1 ? "1 unread" : `${count} unread`;
}
