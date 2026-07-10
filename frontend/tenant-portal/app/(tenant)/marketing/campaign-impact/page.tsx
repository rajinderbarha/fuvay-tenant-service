"use client";
import { useEffect, useState } from "react";
import { providerMarketingApi, CampaignImpactItem, AttributedLead } from "../../../../lib/api";

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

const btnStyle: React.CSSProperties = {
  padding: "6px 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius: 8,
  background: "var(--surface)", color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit",
};
const th: React.CSSProperties = {
  padding: "8px 14px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

export default function CampaignImpactPage() {
  const [events, setEvents]     = useState<CampaignImpactItem[]>([]);
  const [leads, setLeads]       = useState<AttributedLead[]>([]);
  const [loading, setLoading]   = useState(true);
  const [tab, setTab]           = useState<"events" | "leads">("events");

  async function load() {
    setLoading(true);
    try {
      const [evtRes, leadRes] = await Promise.all([
        providerMarketingApi.getCampaignImpact({ limit: 50 }),
        providerMarketingApi.getLeadsAttributed({ limit: 50 }),
      ]);
      setEvents(((evtRes as any)?.data?.items ?? []) as CampaignImpactItem[]);
      setLeads(((leadRes as any)?.data?.items ?? []) as AttributedLead[]);
    } catch {
      setEvents([]); setLeads([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Campaign Impact</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Platform campaign events and converted leads for your profile</p>
        </div>
        <button onClick={load} disabled={loading} style={btnStyle}>
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Campaign Events</div>
          <div style={{ fontSize: 24, fontWeight: 600, color: "var(--text-primary)" }}>{events.length}</div>
        </div>
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>Attributed Leads</div>
          <div style={{ fontSize: 24, fontWeight: 600, color: "var(--success-text)" }}>{leads.length}</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--border)" }}>
        {(["events", "leads"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "8px 16px", fontSize: 13, fontWeight: 500, border: "none", background: "none",
            cursor: "pointer", fontFamily: "inherit", textTransform: "capitalize",
            borderBottom: tab === t ? "2px solid var(--brand)" : "2px solid transparent",
            color: tab === t ? "var(--text-primary)" : "var(--text-tertiary)",
            marginBottom: -1,
          }}>
            {t === "events" ? "All Events" : "Converted Leads"}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
      ) : tab === "events" ? (
        events.length === 0 ? (
          <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
            No campaign events found for your profile
          </div>
        ) : (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                  <th style={th}>Event</th>
                  <th style={th}>Campaign</th>
                  <th style={th}>Source</th>
                  <th style={th}>Date</th>
                </tr>
              </thead>
              <tbody>
                {events.map(e => (
                  <tr key={e.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 14px", fontSize: 11, fontWeight: 500, textTransform: "capitalize",
                      color: EVENT_COLOR[e.event_type] ?? "var(--text-secondary)" }}>
                      {e.event_type}
                    </td>
                    <td style={{ padding: "10px 14px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {e.campaign_id.slice(0, 8)}…
                    </td>
                    <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {e.source_record_type ?? "—"}
                      {e.source_record_id ? ` (${e.source_record_id.slice(0, 8)})` : ""}
                    </td>
                    <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {new Date(e.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : (
        leads.length === 0 ? (
          <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>
            No attributed leads yet — they appear when a campaign converts to a booking or lead
          </div>
        ) : (
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                  <th style={th}>Lead ID</th>
                  <th style={th}>Campaign</th>
                  <th style={th}>Record Type</th>
                  <th style={th}>Date</th>
                </tr>
              </thead>
              <tbody>
                {leads.map(l => (
                  <tr key={l.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 14px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-primary)" }}>
                      {l.id.slice(0, 12)}…
                    </td>
                    <td style={{ padding: "10px 14px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {l.campaign_id.slice(0, 8)}…
                    </td>
                    <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-secondary)", textTransform: "capitalize" }}>
                      {l.source_record_type ?? "—"}
                    </td>
                    <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {new Date(l.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
