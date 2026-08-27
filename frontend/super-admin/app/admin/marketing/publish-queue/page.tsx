"use client";
import { TableSurface } from "@serviceos/design-system";
import { useCallback, useState } from "react";
import { adminMarketingApi, MarketingPublishQueueEntry } from "@/lib/api";
import { Card, Badge, Btn, Select, Skeleton, Pagination } from "@/components/shared/ui";
import { useApi } from "@/hooks/useApi";
import { RefreshCw } from "lucide-react";
import { PageHeader } from "@serviceos/design-system";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "queued", label: "Queued" },
  { value: "ready", label: "Ready" },
  { value: "published", label: "Published" },
  { value: "manually_published", label: "Manually Published" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
];

const CHANNEL_OPTIONS = [
  { value: "", label: "All channels" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "instagram", label: "Instagram" },
  { value: "facebook", label: "Facebook" },
  { value: "website", label: "Website" },
  { value: "sms", label: "SMS" },
  { value: "email", label: "Email" },
];

function statusVariant(s: string): "success" | "warning" | "danger" | "info" | "default" {
  if (s === "published" || s === "manually_published") return "success";
  if (s === "ready") return "info";
  if (s === "queued") return "warning";
  if (s === "failed" || s === "cancelled") return "danger";
  return "default";
}

const th: React.CSSProperties = {
  padding: "8px 14px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

export default function AdminPublishQueuePage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [channelFilter, setChannelFilter] = useState("");
  const [page, setPage] = useState(1);

  const { data, loading, refetch } = useApi(
    useCallback(
      () => adminMarketingApi.listPublishQueue({ status: statusFilter || undefined, channel: channelFilter || undefined, page, page_size: 20 }),
      [statusFilter, channelFilter, page]
    )
  );

  const entries: MarketingPublishQueueEntry[] = data?.queue ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <PageHeader
        title="Publish Queue"
        description="Marketing assets queued for publishing."
        eyebrow="Marketing"
        actions={<Btn onClick={() => refetch()}>
          <RefreshCw size={14} /> Refresh
        </Btn>}
      />

      <Card>
        <div style={{ padding: "12px 16px", display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Select value={statusFilter} onChange={setStatusFilter} options={STATUS_OPTIONS} />
          <Select value={channelFilter} onChange={setChannelFilter} options={CHANNEL_OPTIONS} />
        </div>
      </Card>

      <Card>
        {loading ? (
          <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 10 }}>
            {[...Array(5)].map((_, i) => <Skeleton key={i} height={40} />)}
          </div>
        ) : entries.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No publish queue entries found.</div>
        ) : (
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                {["Asset ID", "Channel", "Publish Mode", "Status", "Scheduled", "Published", "External URL"].map(h => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "10px 14px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {entry.asset_id.slice(0, 8)}…
                  </td>
                  <td style={{ padding: "10px 14px" }}><Badge variant="default">{entry.channel}</Badge></td>
                  <td style={{ padding: "10px 14px", color: "var(--text-tertiary)" }}>{entry.publish_mode}</td>
                  <td style={{ padding: "10px 14px" }}><Badge variant={statusVariant(entry.status)}>{entry.status}</Badge></td>
                  <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {entry.scheduled_at ? new Date(entry.scheduled_at).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {entry.published_at ? new Date(entry.published_at).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: "10px 14px", fontSize: 11 }}>
                    {entry.external_url ? (
                      <a href={entry.external_url} target="_blank" rel="noopener noreferrer"
                        style={{ color: "var(--accent)", overflow: "hidden", textOverflow: "ellipsis",
                          display: "block", maxWidth: 200, whiteSpace: "nowrap" }}>
                        {entry.external_url}
                      </a>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        )}
        {!loading && entries.length > 0 && <Pagination page={page} pageSize={20} pageCount={page + (entries.length === 20 ? 1 : 0)}
          hasPrevious={page > 1} hasNext={entries.length === 20} navigationMode="adjacent" onPage={setPage} alwaysShow />}
      </Card>
    </div>
  );
}
