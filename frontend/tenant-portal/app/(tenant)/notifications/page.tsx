"use client";
import React, { useState, useCallback } from "react";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { Card, Badge, Btn, Skeleton, SectionHeader } from "../../../components/shared/ui";
import { notificationsApi } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import type { NotificationRecord, NotificationChannel } from "../../../lib/api";
import { Bell, RefreshCw } from "lucide-react";

const CHANNEL_LABELS: Record<string, string> = {
  in_app: "In-App", push: "Push", sms: "SMS", email: "Email",
};
const STATUS_VARIANT: Record<string, "success"|"warning"|"danger"|"muted"> = {
  sent: "success", delivered: "success", pending: "warning",
  queued: "warning", failed: "danger", bounced: "danger",
};

export default function NotificationsPage() {
  const [tab, setTab] = useState<"history"|"channels">("history");

  const history  = useApi(useCallback(() => notificationsApi.list({ limit: "50" }), []));
  const channels = useApi(useCallback(() => notificationsApi.getChannels(), []));

  const toggleAction = useAction(useCallback(
    (channel: string, enabled: boolean) => notificationsApi.setChannel(channel, enabled),
    []
  ));

  async function handleToggle(ch: NotificationChannel) {
    const res = await toggleAction.execute(ch.channel, !ch.is_enabled);
    if (res) channels.refetch();
  }

  return (
    <TenantLayout activeNav="notifications">
      <SectionHeader
        title="Notifications"
        subtitle="Delivery history and channel settings"
        icon={<Bell/>}
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Btn variant={tab === "history"  ? "primary" : "ghost"} size="sm" onClick={() => setTab("history")}>History</Btn>
            <Btn variant={tab === "channels" ? "primary" : "ghost"} size="sm" onClick={() => setTab("channels")}>Channels</Btn>
            <Btn variant="ghost" size="sm" icon={<RefreshCw size={14}/>} onClick={() => { history.refetch(); channels.refetch(); }}/>
          </div>
        }
      />

      {tab === "history" && (
        history.loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {[...Array(5)].map((_, i) => <Skeleton key={i} height={60} style={{ borderRadius:"var(--radius-lg)" }} />)}
          </div>
        ) : (history.data?.notifications ?? []).length === 0 ? (
          <Card padding={48} style={{ textAlign: "center" }}>
            <div style={{ display: "flex", justifyContent: "center", color: "var(--text-tertiary)", marginBottom: 12 }}>
              <Bell size={32}/>
            </div>
            <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>No notifications yet</p>
          </Card>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {(history.data?.notifications ?? []).map((n: NotificationRecord) => (
              <Card key={n.notification_id} padding={14}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                        {n.title || n.notif_type}
                      </span>
                      <Badge variant={STATUS_VARIANT[n.status] ?? "muted"} size="sm">{n.status}</Badge>
                      <Badge variant="muted" size="sm">{CHANNEL_LABELS[n.channel] ?? n.channel}</Badge>
                    </div>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
                      {new Date(n.created_at).toLocaleString("en-IN")}
                      {n.reference_id && ` · ref: ${n.reference_id}`}
                    </p>
                  </div>
                  <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                    {n.attempt_count} attempt{n.attempt_count !== 1 ? "s" : ""}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        )
      )}

      {tab === "channels" && (
        channels.loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {[...Array(4)].map((_, i) => <Skeleton key={i} height={70} style={{ borderRadius:"var(--radius-lg)" }} />)}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {(channels.data?.channels ?? []).map((ch: NotificationChannel) => (
              <Card key={ch.channel} padding={16}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>
                      {CHANNEL_LABELS[ch.channel] ?? ch.channel}
                    </p>
                    <p style={{ fontSize: 12, color: "var(--text-tertiary)", margin: 0 }}>
                      {ch.verified_at ? `Verified ${new Date(ch.verified_at).toLocaleDateString("en-IN")}` : "Not yet verified"}
                    </p>
                  </div>
                  <Btn
                    variant={ch.is_enabled ? "danger" : "primary"}
                    size="sm"
                    loading={toggleAction.loading}
                    onClick={() => handleToggle(ch)}
                  >
                    {ch.is_enabled ? "Disable" : "Enable"}
                  </Btn>
                </div>
              </Card>
            ))}
            {(channels.data?.channels ?? []).length === 0 && (
              <Card padding={48} style={{ textAlign: "center" }}>
                <p style={{ fontSize: 14, color: "var(--text-secondary)", margin: 0 }}>
                  No channel config found. Channels are auto-created when you send a notification.
                </p>
              </Card>
            )}
          </div>
        )
      )}
    </TenantLayout>
  );
}
