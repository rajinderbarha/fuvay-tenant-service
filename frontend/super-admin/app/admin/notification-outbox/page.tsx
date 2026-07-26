"use client";
import { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Btn, Modal, SectionHeader } from "../../../components/shared/ui";
import { sprint27AdminApi, type NotificationOutboxRecord } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  pending:                { background: "var(--warning-bg)",      color: "var(--warning-text)" },
  sent:                   { background: "var(--info-bg)",         color: "var(--info-text)" },
  delivered:              { background: "var(--success-bg)",      color: "var(--success-text)" },
  failed:                 { background: "var(--danger-bg)",       color: "var(--danger-text)" },
  provider_not_configured:{ background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  preference_disabled:    { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  skipped:                { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
};

const CHANNEL_ICONS: Record<string, string> = {
  in_app: "🔔", email: "📧", sms: "📱", whatsapp: "💬", push: "📲",
};

const th: React.CSSProperties = {
  padding: "10px 16px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

const selStyle: React.CSSProperties = {
  height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit",
};

export default function NotificationOutboxPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [detail, setDetail] = useState<NotificationOutboxRecord | null>(null);
  const [page, setPage] = useState(0);
  const LIMIT = 50;

  const outbox = useApi(
    useCallback(
      () => sprint27AdminApi.listOutbox({
        ...(statusFilter ? { delivery_status: statusFilter } : {}),
        ...(channelFilter ? { channel: channelFilter } : {}),
        limit: LIMIT, offset: page * LIMIT,
      }),
      [statusFilter, channelFilter, page]
    )
  );

  const retryAction = useAction(
    useCallback((id: string) => sprint27AdminApi.retryOutbox(id), [])
  );

  const items: NotificationOutboxRecord[] = outbox.data?.items ?? [];
  const total: number = outbox.data?.total ?? 0;

  return (
    <AdminLayout>
      <SectionHeader title="Notification Outbox" subtitle={`${total} records`} />

      <Card>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", padding: 12 }}>
          <select style={selStyle} value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(0); }}>
            <option value="">All Statuses</option>
            {["pending","sent","delivered","failed","provider_not_configured","preference_disabled","skipped"].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select style={selStyle} value={channelFilter}
            onChange={e => { setChannelFilter(e.target.value); setPage(0); }}>
            <option value="">All Channels</option>
            {["in_app","email","sms","whatsapp","push"].map(c => (
              <option key={c} value={c}>{CHANNEL_ICONS[c]} {c}</option>
            ))}
          </select>
          <Btn size="sm" variant="ghost" onClick={() => { setStatusFilter(""); setChannelFilter(""); setPage(0); }}>
            Clear
          </Btn>
        </div>
      </Card>

      <Card>
        {outbox.loading ? (
          <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                  {["Recipient", "Channel", "Template", "Status", "Provider", "Retries", "Created", "Actions"].map(h => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
                      <span style={{ color: "var(--text-tertiary)" }}>{item.recipient_type}</span>
                      <br />{item.recipient_user_id?.slice(0, 8)}…
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>
                      {CHANNEL_ICONS[item.channel] || ""} {item.channel}
                    </td>
                    <td style={{ padding: "10px 16px", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis",
                      whiteSpace: "nowrap", fontSize: 11, color: "var(--text-secondary)" }}>
                      {item.template_key}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                        ...(STATUS_STYLE[item.delivery_status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
                        {item.delivery_status}
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>{item.provider_name ?? "—"}</td>
                    <td style={{ padding: "10px 16px", fontSize: 12, textAlign: "center", color: "var(--text-secondary)" }}>
                      {item.retry_count}/{item.max_retries}
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {item.created_at.replace("T", " ").slice(0, 16)}
                    </td>
                    <td style={{ padding: "10px 16px", display: "flex", gap: 8 }}>
                      <Btn size="xs" variant="ghost" onClick={() => setDetail(item)}>View</Btn>
                      {item.delivery_status === "failed" && item.retry_count < item.max_retries && (
                        <Btn size="xs"
                          onClick={() => retryAction.execute(item.id).then(() => outbox.refetch())}
                          loading={retryAction.loading}>
                          Retry
                        </Btn>
                      )}
                    </td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
                      No outbox records found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", borderTop: "1px solid var(--border)" }}>
          <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
            {page * LIMIT + 1}–{Math.min((page + 1) * LIMIT, total)} of {total}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <Btn size="sm" variant="ghost" disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Prev</Btn>
            <Btn size="sm" variant="ghost" disabled={(page + 1) * LIMIT >= total} onClick={() => setPage(p => p + 1)}>Next →</Btn>
          </div>
        </div>
      </Card>

      {detail && (
        <Modal open={!!detail} title="Outbox Record" onClose={() => setDetail(null)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 12, fontSize: 13 }}>
            <div><span style={{ fontWeight: 500 }}>ID:</span>{" "}
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{detail.id}</span>
            </div>
            <div><span style={{ fontWeight: 500 }}>Template:</span> {detail.template_key}</div>
            <div><span style={{ fontWeight: 500 }}>Title:</span> {detail.title}</div>
            <div>
              <span style={{ fontWeight: 500 }}>Body:</span>
              <pre style={{ marginTop: 4, background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: 10,
                fontSize: 11, whiteSpace: "pre-wrap", color: "var(--text-primary)" }}>{detail.body}</pre>
            </div>
            <div>
              <span style={{ fontWeight: 500 }}>Status:</span>{" "}
              <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                ...(STATUS_STYLE[detail.delivery_status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
                {detail.delivery_status}
              </span>
            </div>
            {detail.failure_code && (
              <div><span style={{ fontWeight: 500 }}>Failure:</span> {detail.failure_code}</div>
            )}
            <div><span style={{ fontWeight: 500 }}>Retries:</span> {detail.retry_count}/{detail.max_retries}</div>
          </div>
        </Modal>
      )}
    </AdminLayout>
  );
}
