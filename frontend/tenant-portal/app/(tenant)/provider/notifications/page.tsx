"use client";
import { useCallback, useState } from "react";
import Link from "next/link";
import { providerNotifApi, type InAppNotificationItem } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";

const SEV_ICON: Record<string, string> = {
  info: "ℹ️", success: "✅", warning: "⚠️", critical: "🚨",
};

const btnBase: React.CSSProperties = {
  padding: "6px 12px", fontSize: 13, borderRadius:"var(--radius-md)", cursor: "pointer",
  fontFamily: "inherit", border: "1px solid var(--border)",
};

export default function ProviderNotificationsPage() {
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const notifs = useApi(
    useCallback(() => providerNotifApi.list({
      ...(filter === "unread" ? { read_status: "unread" } : {}),
      limit: 50,
    }), [filter])
  );

  const unreadCount = useApi(useCallback(() => providerNotifApi.unreadCount(), []));

  const markReadAction = useAction(
    useCallback((id: string) => providerNotifApi.markRead(id), [])
  );

  const markAllAction = useAction(
    useCallback(() => providerNotifApi.markAllRead(), [])
  );

  const items: InAppNotificationItem[] = notifs.data?.items ?? [];
  const total: number = notifs.data?.total ?? 0;
  const unread: number = unreadCount.data?.unread_count ?? 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 720, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>Notifications</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>{total} total · {unread} unread</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button style={{ ...btnBase, background: filter === "all" ? "var(--brand)" : "var(--surface)",
            color: filter === "all" ? "white" : "var(--text-primary)", borderColor: filter === "all" ? "var(--brand)" : "var(--border)" }}
            onClick={() => setFilter("all")}>All</button>
          <button style={{ ...btnBase, background: filter === "unread" ? "var(--brand)" : "var(--surface)",
            color: filter === "unread" ? "white" : "var(--text-primary)", borderColor: filter === "unread" ? "var(--brand)" : "var(--border)" }}
            onClick={() => setFilter("unread")}>
            Unread {unread > 0 && <span style={{ marginLeft: 4, background: "var(--danger)", color: "white", fontSize: 11, borderRadius: 999, padding: "1px 6px" }}>{unread}</span>}
          </button>
          {unread > 0 && (
            <button style={{ ...btnBase, background: "var(--surface)", color: "var(--text-secondary)" }}
              onClick={() => markAllAction.execute().then(() => { notifs.refetch(); unreadCount.refetch(); })}
              disabled={markAllAction.loading}>Mark All Read</button>
          )}
        </div>
      </div>

      {notifs.loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[1,2,3].map(i => <div key={i} style={{ height: 80, borderRadius:"var(--radius-md)", background: "var(--surface-sunken)" }}/>)}
        </div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: "center", padding: "64px 0", color: "var(--text-tertiary)" }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🔔</div>
          <p style={{ fontSize: 13 }}>No notifications yet</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {items.map(n => (
            <div key={n.id} style={{
              borderRadius: 10, border: `1px solid ${n.read_status === "unread" ? "var(--info-border)" : "var(--border)"}`,
              background: n.read_status === "unread" ? "var(--info-bg)" : "var(--surface)", padding: 16,
            }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12, flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: 20, flexShrink: 0 }}>{SEV_ICON[n.severity] ?? "🔔"}</span>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{n.title}</div>
                    <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>{n.body}</div>
                    {n.action_url && n.action_label && (
                      <Link href={n.action_url} style={{ fontSize: 11, color: "var(--accent)", marginTop: 4, display: "inline-block", textDecoration: "none" }}>
                        {n.action_label} →
                      </Link>
                    )}
                    <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>
                      {n.created_at.replace("T", " ").slice(0, 16)}
                    </div>
                  </div>
                </div>
                {n.read_status === "unread" && (
                  <button style={{ fontSize: 11, color: "var(--accent)", flexShrink: 0, background: "none", border: "none", cursor: "pointer", padding: 0 }}
                    onClick={() => markReadAction.execute(n.id).then(() => { notifs.refetch(); unreadCount.refetch(); })}
                    disabled={markReadAction.loading}>
                    Mark Read
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
