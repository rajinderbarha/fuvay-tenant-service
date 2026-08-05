import {
  isNotificationUnread, resolveNotificationVisual, groupNotificationsByDay, formatUnreadCount,
} from "../notificationPresentation";
import { CustomerNotification } from "../notification";
import { asNotificationId } from "../ids";
import { ServerTimestamp } from "../dates";

function notification(overrides: Partial<CustomerNotification> = {}): CustomerNotification {
  return {
    id: asNotificationId("n-1"),
    type: "booking.confirmed",
    title: "Your booking is confirmed",
    body: "Booking FUV-2841 is confirmed.",
    createdAt: "2026-08-01T09:42:00Z" as ServerTimestamp,
    readAt: null,
    readStatus: "unread",
    destination: { kind: "booking", bookingId: "b-1" },
    ...overrides,
  };
}

describe("isNotificationUnread / resolveNotificationVisual", () => {
  it("reads unread state from the real backend field, never local tap history", () => {
    expect(isNotificationUnread(notification({ readStatus: "unread" }))).toBe(true);
    expect(isNotificationUnread(notification({ readStatus: "read" }))).toBe(false);
  });

  it("gives unread notifications a strong title weight and an accessible label", () => {
    const visual = resolveNotificationVisual(notification({ readStatus: "unread" }));
    expect(visual.unread).toBe(true);
    expect(visual.titleWeight).toBe("strong");
    expect(visual.accessibilityStateLabel).toBe("Unread");
  });

  it("gives read notifications a regular weight and an accessible label", () => {
    const visual = resolveNotificationVisual(notification({ readStatus: "read" }));
    expect(visual.unread).toBe(false);
    expect(visual.titleWeight).toBe("regular");
    expect(visual.accessibilityStateLabel).toBe("Read");
  });
});

describe("groupNotificationsByDay", () => {
  const now = new Date("2026-08-02T12:00:00Z");

  it("groups into Today/Yesterday/Earlier using real timestamps", () => {
    const items = [
      notification({ id: asNotificationId("today"), createdAt: "2026-08-02T09:00:00Z" as ServerTimestamp }),
      notification({ id: asNotificationId("yesterday"), createdAt: "2026-08-01T09:00:00Z" as ServerTimestamp }),
      notification({ id: asNotificationId("earlier"), createdAt: "2026-07-20T09:00:00Z" as ServerTimestamp }),
    ];
    const groups = groupNotificationsByDay(items, now);
    expect(groups.map(g => g.label)).toEqual(["Today", "Yesterday", "Earlier"]);
    expect(groups[0].items[0].id).toBe("today");
    expect(groups[1].items[0].id).toBe("yesterday");
    expect(groups[2].items[0].id).toBe("earlier");
  });

  it("omits empty groups instead of rendering an empty section header", () => {
    const items = [notification({ createdAt: "2026-08-02T09:00:00Z" as ServerTimestamp })];
    const groups = groupNotificationsByDay(items, now);
    expect(groups).toHaveLength(1);
    expect(groups[0].label).toBe("Today");
  });

  it("never reorders within a group -- preserves authoritative backend ordering", () => {
    const items = [
      notification({ id: asNotificationId("first"), createdAt: "2026-08-02T10:00:00Z" as ServerTimestamp }),
      notification({ id: asNotificationId("second"), createdAt: "2026-08-02T09:00:00Z" as ServerTimestamp }),
    ];
    const groups = groupNotificationsByDay(items, now);
    expect(groups[0].items.map(i => i.id)).toEqual(["first", "second"]);
  });
});

describe("formatUnreadCount", () => {
  it("uses singular grammar for exactly 1", () => {
    expect(formatUnreadCount(1)).toBe("1 unread");
  });

  it("uses plural grammar for any other count", () => {
    expect(formatUnreadCount(3)).toBe("3 unread");
    expect(formatUnreadCount(0)).toBe("0 unread");
  });
});
