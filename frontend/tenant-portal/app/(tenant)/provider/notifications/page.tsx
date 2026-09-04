"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Bell, BriefcaseBusiness, CheckCircle2, ChevronRight, CreditCard, UserRound } from "lucide-react";
import { Alert, Button, PageHeader, PageShell } from "@serviceos/design-system";
import { providerNotifApi, type InAppNotificationItem } from "../../../../lib/api";
import { useAction, useApi } from "../../../../hooks/useApi";
import styles from "./notifications.module.css";

type Category = "All" | "Unread" | "Jobs" | "Payments" | "Staff";
type DateRange = "All types" | "Today" | "This week";

const CATEGORIES: Category[] = ["All", "Unread", "Jobs", "Payments", "Staff"];
const DATE_RANGES: DateRange[] = ["All types", "Today", "This week"];

function categoryFor(notification: InAppNotificationItem): Exclude<Category, "All" | "Unread"> | "Other" {
  const value = `${notification.notification_type} ${notification.title}`.toLowerCase();
  if (/(payment|credit|invoice|refund|payout|finance|wallet)/.test(value)) return "Payments";
  if (/(staff|technician|team|availability|roster|assignment)/.test(value)) return "Staff";
  if (/(job|booking|service|dispatch|complaint|warranty|quote)/.test(value)) return "Jobs";
  return "Other";
}

function timeAgo(value: string): string {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "Time unavailable";
  const minutes = Math.max(0, Math.floor((Date.now() - timestamp) / 60_000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return days < 7 ? `${days}d ago` : new Date(value).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

function isInDateRange(value: string, range: DateRange): boolean {
  if (range === "All types") return true;
  const created = new Date(value);
  if (!Number.isFinite(created.getTime())) return false;
  const now = new Date();
  if (range === "Today") {
    return created.getFullYear() === now.getFullYear()
      && created.getMonth() === now.getMonth()
      && created.getDate() === now.getDate();
  }
  return now.getTime() - created.getTime() <= 7 * 24 * 60 * 60 * 1000;
}

function notificationVisual(notification: InAppNotificationItem) {
  const category = categoryFor(notification);
  const severity = notification.severity.toLowerCase();
  if (severity === "critical" || severity === "warning") return { Icon: AlertTriangle, tone: styles.warningIcon };
  if (category === "Payments") return { Icon: CreditCard, tone: styles.accentIcon };
  if (category === "Staff") return { Icon: UserRound, tone: styles.staffIcon };
  if (severity === "success") return { Icon: CheckCircle2, tone: styles.accentIcon };
  if (category === "Jobs") return { Icon: BriefcaseBusiness, tone: styles.neutralIcon };
  return { Icon: Bell, tone: styles.neutralIcon };
}

function NotificationRow({ notification, onRead }: { notification: InAppNotificationItem; onRead: (id: string) => void }) {
  const unread = notification.read_status === "unread";
  const { Icon, tone } = notificationVisual(notification);
  const content = <>
    <span className={`${styles.notificationIcon} ${tone}`} aria-hidden="true"><Icon size={16} /></span>
    <span className={styles.notificationCopy}>
      <span className={styles.notificationTitle}>{notification.title}{unread && <span className={styles.unreadDot} aria-label="Unread" />}</span>
      <span className={styles.notificationBody}>{notification.body}</span>
      {notification.action_label && <span className={styles.actionLabel}>{notification.action_label} <ChevronRight size={12} /></span>}
    </span>
    <time className={styles.notificationTime} dateTime={notification.created_at} title={new Date(notification.created_at).toLocaleString()}>
      {timeAgo(notification.created_at)}
    </time>
  </>;

  const className = `${styles.notificationRow} ${unread ? styles.unreadRow : ""}`;
  if (notification.action_url) {
    return <Link href={notification.action_url} className={className} onClick={() => unread && onRead(notification.id)}>{content}</Link>;
  }
  if (unread) {
    return <button type="button" className={className} onClick={() => onRead(notification.id)} aria-label={`Mark ${notification.title} as read`}>{content}</button>;
  }
  return <div className={className}>{content}</div>;
}

export default function ProviderNotificationsPage() {
  const [category, setCategory] = useState<Category>("All");
  const [dateRange, setDateRange] = useState<DateRange>("All types");
  const notifications = useApi(useCallback(() => providerNotifApi.list({ limit: 50 }), []));
  const unreadCount = useApi(useCallback(() => providerNotifApi.unreadCount(), []));
  const markRead = useAction(useCallback((id: string) => providerNotifApi.markRead(id), []));
  const markAll = useAction(useCallback(() => providerNotifApi.markAllRead(), []));

  const items = notifications.data?.items ?? [];
  const total = notifications.data?.total ?? 0;
  const unread = unreadCount.data?.unread_count ?? 0;

  const counts = useMemo<Record<Category, number>>(() => ({
    All: total,
    Unread: unread,
    Jobs: items.filter((item) => categoryFor(item) === "Jobs").length,
    Payments: items.filter((item) => categoryFor(item) === "Payments").length,
    Staff: items.filter((item) => categoryFor(item) === "Staff").length,
  }), [items, total, unread]);

  const visibleItems = useMemo(() => items.filter((item) => {
    if (category === "Unread" && item.read_status !== "unread") return false;
    if (!["All", "Unread"].includes(category) && categoryFor(item) !== category) return false;
    return isInDateRange(item.created_at, dateRange);
  }), [items, category, dateRange]);

  const refresh = useCallback(() => {
    notifications.refetch();
    unreadCount.refetch();
  }, [notifications, unreadCount]);

  const handleRead = useCallback((id: string) => {
    void markRead.execute(id).then(refresh);
  }, [markRead, refresh]);

  const handleMarkAll = useCallback(() => {
    void markAll.execute().then(refresh);
  }, [markAll, refresh]);

  return <PageShell>
    <PageHeader
      title="Notifications"
      description="Everything that needs your attention, in one feed."
      actions={<Button variant="secondary" onClick={handleMarkAll} loading={markAll.loading} disabled={unread === 0 || markAll.loading}>Mark all as read</Button>}
    />

    <div className={styles.page}>
      {(notifications.error || unreadCount.error || markRead.error || markAll.error) &&
        <Alert tone="danger" title="Notifications could not be updated">
          {notifications.error ?? unreadCount.error ?? markRead.error ?? markAll.error}
        </Alert>}

      <div className={styles.toolbar}>
        <div className={styles.categoryTabs} role="tablist" aria-label="Notification categories">
          {CATEGORIES.map((item) => <button key={item} type="button" role="tab" aria-selected={category === item}
            className={category === item ? styles.activeCategory : ""} onClick={() => setCategory(item)}>
            {item}<span>{counts[item]}</span>
          </button>)}
        </div>
        <div className={styles.dateFilters} aria-label="Notification date range">
          {DATE_RANGES.map((item) => <button key={item} type="button" aria-pressed={dateRange === item}
            className={dateRange === item ? styles.activeDate : ""} onClick={() => setDateRange(item)}>{item}</button>)}
        </div>
      </div>

      {notifications.loading && !notifications.data ? <div className={styles.feed} aria-label="Loading notifications">
        {[1, 2, 3, 4].map((key) => <div className={styles.skeletonRow} key={key} />)}
      </div> : visibleItems.length === 0 ? <div className={styles.emptyState}>
        <span><Bell size={22} /></span><strong>No notifications found</strong>
        <p>{category === "Unread" ? "You’re all caught up." : "Try another category or date range."}</p>
      </div> : <div className={styles.feed}>
        {visibleItems.map((notification) => <NotificationRow key={notification.id} notification={notification} onRead={handleRead} />)}
      </div>}
    </div>
  </PageShell>;
}
