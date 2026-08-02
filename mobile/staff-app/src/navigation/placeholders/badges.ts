import { useState, useEffect } from "react";

/**
 * Navigation-safe badge data source (spec section 6). Badge counts are
 * intentionally decoupled from screen content -- a badge fetch failure
 * must never break tab navigation, so this hook always resolves to a
 * count (0 on failure) and never throws or suspends.
 */
export interface BadgeAdapter {
  fetchUnreadNotificationCount(): Promise<number>;
  fetchActionableJobCount(): Promise<number>;
}

export const defaultBadgeAdapter: BadgeAdapter = {
  // Phase Q: real endpoint now exists (GET /v1/staff/notifications/unread-count).
  async fetchUnreadNotificationCount() {
    const { getUnreadCount } = await import("../../services/notifications/notificationsApi");
    const result = await getUnreadCount();
    return result.ok ? result.data.unread_count : 0;
  },
  async fetchActionableJobCount() { return 0; },
};

export function useTabBadge(fetcher: () => Promise<number>): string | undefined {
  const [count, setCount] = useState<number | undefined>(undefined);
  useEffect(() => {
    let mounted = true;
    fetcher().then(value => { if (mounted) setCount(value > 0 ? value : undefined); }).catch(() => { if (mounted) setCount(undefined); });
    return () => { mounted = false; };
  }, [fetcher]);
  if (count === undefined) return undefined;
  return count > 99 ? "99+" : String(count);
}
