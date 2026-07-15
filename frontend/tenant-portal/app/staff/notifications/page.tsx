"use client";
import React, { useCallback, useState } from "react";
import { StaffLayout } from "../../../components/layout/StaffLayout";
import { Card, Btn, Badge, Skeleton, EmptyState } from "../../../components/shared/ui";
import { useApi, useAction } from "../../../hooks/useApi";
import { staffSelfApi } from "../../../lib/api";
import { Bell, CheckCheck } from "lucide-react";

export default function StaffNotificationsPage() {
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const notifs = useApi(useCallback(() => staffSelfApi.getNotifications(), []));

  const markReadAction = useAction((id: string) => staffSelfApi.markRead(id), { onSuccess: () => notifs.refetch() });
  const markAllAction = useAction(() => staffSelfApi.markAllRead(), { onSuccess: () => notifs.refetch() });

  // MODULE-L5-39: the real notification shape uses read_status ("read"/
  // "unread") + notification_type, not is_read/type. mark-read also hit a
  // 404 route (/mark-read vs /read) -- fixed in staffSelfApi.
  const isUnread = (n: { read_status: string }) => n.read_status !== "read";
  const items = (notifs.data?.items ?? []).filter(n => filter === "all" || isUnread(n));

  return (
    <StaffLayout activeNav="notifications">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0 }}>Notifications</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0 0" }}>
            Assignment, schedule, and system alerts relevant to you.
          </p>
        </div>
        <Btn size="sm" variant="secondary" onClick={() => markAllAction.execute()}>
          <CheckCheck size={14}/> {markAllAction.loading ? "Marking…" : "Mark all read"}
        </Btn>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {(["all", "unread"] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            style={{
              padding: "6px 14px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer",
              border: "1px solid var(--border)",
              background: filter === f ? "var(--accent, #2563eb)" : "var(--card-bg)",
              color: filter === f ? "#fff" : "var(--text)",
            }}>
            {f === "all" ? "All" : "Unread"}
          </button>
        ))}
      </div>

      {(markAllAction.error || markReadAction.error) && (
        <p style={{ fontSize: 12, color: "var(--danger-text)", marginBottom: 12 }}>
          {markAllAction.error || markReadAction.error}
          {(markAllAction.requestId || markReadAction.requestId) && ` — Request ID: ${markAllAction.requestId || markReadAction.requestId}`}
        </p>
      )}

      <Card padding={0}>
        {notifs.loading ? <Skeleton height={160}/> : notifs.error ? (
          <div style={{ padding: 20 }}>
            <p style={{ color: "var(--danger-text)", fontSize: 13 }}>{notifs.error}{notifs.requestId && ` — Request ID: ${notifs.requestId}`}</p>
          </div>
        ) : items.length === 0 ? (
          <EmptyState icon={<Bell/>} title="No notifications." description="You're all caught up."/>
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {items.map(n => (
              <div key={n.id} style={{
                display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12,
                padding: "12px 16px", borderBottom: "1px solid var(--border)",
                background: isUnread(n) ? "var(--accent-subtle, rgba(37,99,235,0.06))" : "transparent",
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{n.title || n.notification_type || "Notification"}</div>
                  {n.body && <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>{n.body}</div>}
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>{new Date(n.created_at).toLocaleString()}</div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {isUnread(n) && <Badge variant="info" size="sm">New</Badge>}
                  {isUnread(n) && (
                    <Btn size="sm" variant="secondary" onClick={() => markReadAction.execute(n.id)}>Mark read</Btn>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </StaffLayout>
  );
}
