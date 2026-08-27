"use client";
import { TableSurface } from "@serviceos/design-system";
import { useEffect, useState } from "react";
import { adminMarketingApi } from "@/lib/api";
import { PageHeader } from "@serviceos/design-system";
import { Btn } from "@/components/shared/ui";

const EVENT_COLOR: Record<string, string> = {
  targeted:  "var(--text-secondary)",
  sent:      "var(--accent)",
  delivered: "var(--accent)",
  opened:    "var(--success-text)",
  clicked:   "var(--success-text)",
  converted: "var(--success-text)",
  failed:    "var(--danger-text)",
  skipped:   "var(--warning-text)",
};

const selStyle: React.CSSProperties = {
  height: 34, padding: "0 10px", fontSize: 13, border: "1px solid var(--border)",
  borderRadius:"var(--radius-md)", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit",
};
const th: React.CSSProperties = {
  padding: "8px 14px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

export default function MarketingEventsPage() {
  const [events, setEvents]   = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [eventFilter, setEventFilter] = useState("");

  async function load() {
    setLoading(true);
    try {
      const r = await adminMarketingApi.listEvents({
        event_type: eventFilter || undefined,
        limit: 100,
      });
      setEvents((r as any)?.data ?? []);
    } catch { setEvents([]); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [eventFilter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <PageHeader
        title="Campaign Events"
        description="Delivery and conversion event stream."
        eyebrow="Marketing"
        actions={<div style={{ display: "flex", gap: "var(--layout-control-gap)" }}>
          <select value={eventFilter} onChange={e => setEventFilter(e.target.value)} style={selStyle}>
            <option value="">All Events</option>
            {["targeted","sent","delivered","opened","clicked","converted","failed","skipped"].map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <Btn variant="secondary" size="sm" onClick={load} loading={loading}>Refresh</Btn>
        </div>}
      />

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading events…</div>
        ) : events.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No events found</div>
        ) : (
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                <th style={th}>Event</th>
                <th style={th}>Campaign</th>
                <th style={th}>Recipient</th>
                <th style={th}>Source</th>
                <th style={th}>Time</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e: any) => (
                <tr key={e.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "10px 14px" }}>
                    <span style={{ fontSize: 11, fontWeight: 500, textTransform: "capitalize",
                      color: EVENT_COLOR[e.event_type] ?? "var(--text-secondary)" }}>
                      {e.event_type}
                    </span>
                  </td>
                  <td style={{ padding: "10px 14px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {e.campaign_id?.slice(0, 8)}…
                  </td>
                  <td style={{ padding: "10px 14px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {e.recipient_user_id?.slice(0, 8) ?? "—"}
                  </td>
                  <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {e.source_record_type ?? "—"}
                    {e.source_record_id && ` (${e.source_record_id.slice(0, 8)})`}
                  </td>
                  <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {e.created_at ? new Date(e.created_at).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableSurface>
        )}
      </div>
    </div>
  );
}
