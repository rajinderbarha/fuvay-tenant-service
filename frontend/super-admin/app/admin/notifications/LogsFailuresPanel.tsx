"use client";
import React, { useCallback, useState } from "react";
import { Card, Badge, Btn, Select, Input, Modal } from "../../../components/shared/ui";
import { sprint27AdminApi } from "../../../lib/api";
import type { NotificationOutboxRecord } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";
import { RefreshCw, Download, RotateCw, XCircle, Eye } from "lucide-react";

const STATUS_VARIANT: Record<string, "success" | "warning" | "danger" | "muted"> = {
  delivered: "success", pending: "warning", failed: "danger",
  skipped: "muted", provider_not_configured: "muted", preference_disabled: "muted",
};

export function LogsFailuresPanel() {
  const [statusFilter, setStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [selected, setSelected] = useState<NotificationOutboxRecord | null>(null);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const notify = (msg: string, ok = true) => { setToast({ msg, ok }); setTimeout(() => setToast(null), 3500); };

  const outboxApi = useApi(useCallback(() => sprint27AdminApi.listOutbox({
    delivery_status: statusFilter || undefined, channel: channelFilter || undefined, limit: 100,
  } as Record<string, string | number>), [statusFilter, channelFilter]));

  const retryAction = useAction((id: string) => sprint27AdminApi.retryOutbox(id));
  const cancelAction = useAction((id: string) => sprint27AdminApi.cancelOutbox(id));

  async function handleRetry(id: string) {
    try {
      await retryAction.execute(id);
      outboxApi.refetch();
      notify("Retry queued — idempotent, will not create a duplicate delivery.");
    } catch (e) {
      notify(e instanceof Error ? e.message : "Retry not allowed.", false);
    }
  }

  async function handleCancel(id: string) {
    try {
      await cancelAction.execute(id);
      outboxApi.refetch();
      notify("Pending delivery cancelled.");
    } catch (e) {
      notify(e instanceof Error ? e.message : "Cancel not allowed — only pending deliveries can be cancelled.", false);
    }
  }

  async function handleExport() {
    const data = await sprint27AdminApi.exportOutbox({
      delivery_status: statusFilter || undefined, channel: channelFilter || undefined,
    } as Record<string, string | number>);
    const blob = new Blob([JSON.stringify(data.items, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `notification-delivery-logs-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const items = outboxApi.data?.items ?? [];

  return (
    <div>
      {toast && (
        <div style={{ padding: "10px 16px", marginBottom: 16, borderRadius: 10,
          background: toast.ok ? "var(--success-bg)" : "var(--danger-bg)",
          border: `1px solid ${toast.ok ? "var(--success-border)" : "var(--danger-border)"}`,
          color: toast.ok ? "var(--success-text)" : "var(--danger-text)", fontSize: 13 }}>
          {toast.msg}
        </div>
      )}

      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
        <Select value={statusFilter} onChange={setStatusFilter} placeholder="Status" options={[
          { value: "", label: "All Statuses" },
          { value: "delivered", label: "Delivered" },
          { value: "pending", label: "Pending" },
          { value: "failed", label: "Failed" },
          { value: "skipped", label: "Skipped / Cancelled" },
          { value: "provider_not_configured", label: "Provider Not Configured" },
          { value: "preference_disabled", label: "Preference Disabled" },
        ]}/>
        <Select value={channelFilter} onChange={setChannelFilter} placeholder="Channel" options={[
          { value: "", label: "All Channels" },
          { value: "in_app", label: "In-App" }, { value: "email", label: "Email" },
          { value: "sms", label: "SMS" }, { value: "whatsapp", label: "WhatsApp" }, { value: "push", label: "Push" },
        ]}/>
        <div style={{ flex: 1 }}/>
        <Btn size="sm" variant="ghost" onClick={() => outboxApi.refetch()}><RefreshCw size={14}/></Btn>
        <Btn size="sm" variant="secondary" onClick={handleExport}><Download size={14} style={{ marginRight: 4 }}/>Export</Btn>
      </div>

      <Card style={{ padding: 0 }}>
        {outboxApi.loading ? (
          <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading delivery logs…</div>
        ) : items.length === 0 ? (
          <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No delivery attempts match this filter.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                  {["Delivery ID", "Vertical", "Recipient Type", "Channel", "Provider", "Status", "Attempts", "Created", "Actions"].map(h => (
                    <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map(row => (
                  <tr key={row.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "9px 14px", fontFamily: "monospace", fontSize: 11 }}>{row.id.slice(0, 8)}…</td>
                    <td style={{ padding: "9px 14px" }}>{row.vertical_key ?? "Global"}</td>
                    <td style={{ padding: "9px 14px" }}>{row.recipient_type}</td>
                    <td style={{ padding: "9px 14px" }}>{row.channel}</td>
                    <td style={{ padding: "9px 14px", color: "var(--text-secondary)" }}>{row.provider_name ?? "—"}</td>
                    <td style={{ padding: "9px 14px" }}>
                      <Badge variant={STATUS_VARIANT[row.delivery_status] ?? "muted"} size="sm">{row.delivery_status.replace(/_/g, " ")}</Badge>
                    </td>
                    <td style={{ padding: "9px 14px" }}>{row.retry_count} / {row.max_retries}</td>
                    <td style={{ padding: "9px 14px", color: "var(--text-tertiary)", fontSize: 12 }}>{new Date(row.created_at).toLocaleString()}</td>
                    <td style={{ padding: "9px 14px", display: "flex", gap: 4 }}>
                      <Btn size="xs" variant="ghost" onClick={() => setSelected(row)}><Eye size={12}/></Btn>
                      {row.delivery_status === "failed" && row.retry_count < row.max_retries && (
                        <Btn size="xs" variant="secondary" onClick={() => handleRetry(row.id)} loading={retryAction.loading}><RotateCw size={12}/></Btn>
                      )}
                      {row.delivery_status === "pending" && (
                        <Btn size="xs" variant="ghost" onClick={() => handleCancel(row.id)} loading={cancelAction.loading}><XCircle size={12}/></Btn>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div style={{ padding: "8px 14px", fontSize: 12, color: "var(--text-tertiary)" }}>Showing 1 to {items.length} of {outboxApi.data?.total ?? items.length} delivery attempts</div>
      </Card>

      {selected && (
        <Modal open onClose={() => setSelected(null)} title="Delivery trace" size="md">
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <Field label="Delivery ID" value={selected.id}/>
            <Field label="Event" value={selected.notification_event_id ?? "—"}/>
            <Field label="Template key" value={selected.template_key}/>
            <Field label="Title" value={selected.title}/>
            <Field label="Body" value={selected.body}/>
            <Field label="Channel" value={selected.channel}/>
            <Field label="Provider" value={selected.provider_name ?? "—"}/>
            <Field label="Vertical" value={selected.vertical_key ?? "Global"}/>
            <Field label="Status" value={selected.delivery_status}/>
            <Field label="Failure code" value={selected.failure_code ?? "—"}/>
            <Field label="Attempts" value={`${selected.retry_count} / ${selected.max_retries}`}/>
            <Field label="Sent at" value={selected.sent_at ? new Date(selected.sent_at).toLocaleString() : "Not yet sent"}/>
            <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: 8 }}>
              <Btn size="sm" variant="ghost" onClick={() => setSelected(null)}>Close</Btn>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", textTransform: "uppercase", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 13, color: "var(--text-primary)", wordBreak: "break-word" }}>{value}</div>
    </div>
  );
}
