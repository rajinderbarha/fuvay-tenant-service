"use client";
import React, { useCallback } from "react";
import { Card, Badge, Btn } from "../../../components/shared/ui";
import { sprint27AdminApi } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import { RefreshCw, Info } from "lucide-react";

const STATE_VARIANT: Record<string, "success" | "warning" | "danger" | "muted"> = {
  "Available": "success",
  "Not Configured": "muted",
  "Verification Required": "warning",
  "Degraded": "warning",
  "Disabled": "muted",
  "Failed": "danger",
};

const CHANNEL_LABEL: Record<string, string> = {
  in_app: "In-App", email: "Email", sms: "SMS", whatsapp: "WhatsApp", push: "Push",
};

export function DeliveryProvidersPanel() {
  const statusApi = useApi(useCallback(() => sprint27AdminApi.getChannelStatus(), []), []);
  const items = statusApi.data?.items ?? [];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0, maxWidth: 640 }}>
          Only channels with a real, working delivery provider can be required or made primary on an
          Event Policy. A channel shown as &ldquo;Not Configured&rdquo; here will be rejected if a policy
          tries to require it &mdash; it can still be added as a fallback.
        </p>
        <Btn size="sm" variant="ghost" onClick={() => statusApi.refetch()}><RefreshCw size={14}/></Btn>
      </div>

      {statusApi.loading ? (
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading channel status…</p>
      ) : (
        <Card style={{ padding: 0 }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--surface-sunken)", borderBottom: "1px solid var(--border)" }}>
                  {["Channel", "Provider", "State", "Last Successful Delivery", "Failure Rate", "Webhook", ""].map(h => (
                    <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-tertiary)", textTransform: "uppercase" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map(row => (
                  <tr key={row.channel} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 14px", fontWeight: 600 }}>{CHANNEL_LABEL[row.channel] ?? row.channel}</td>
                    <td style={{ padding: "10px 14px", color: "var(--text-secondary)" }}>{row.provider ?? "—"}</td>
                    <td style={{ padding: "10px 14px" }}>
                      <Badge variant={STATE_VARIANT[row.state] ?? "muted"} size="sm">{row.state}</Badge>
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--text-tertiary)", fontSize: 12 }}>
                      {row.last_successful_delivery ? new Date(row.last_successful_delivery).toLocaleString() : "Never"}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      {row.failure_rate_pct !== null ? `${row.failure_rate_pct}%` : "No attempts yet"}
                    </td>
                    <td style={{ padding: "10px 14px", color: "var(--text-tertiary)" }}>{row.webhook_status ?? "Not implemented"}</td>
                    <td style={{ padding: "10px 14px" }}>
                      {row.note && (
                        <span title={row.note} style={{ display: "inline-flex", color: "var(--text-tertiary)", cursor: "help" }}>
                          <Info size={14}/>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
