"use client";
import { TableSurface } from "@serviceos/design-system";
import { useEffect, useState } from "react";
import Link from "next/link";
import { adminAiApi, AISession } from "@/lib/api";
import { PageHeader } from "@serviceos/design-system";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  active:     { background: "var(--success-bg)",      color: "var(--success-text)" },
  completed:  { background: "var(--surface-sunken)",  color: "var(--text-secondary)" },
  abandoned:  { background: "var(--warning-bg)",      color: "var(--warning-text)" },
  handed_off: { background: "var(--info-bg)",         color: "var(--info-text)" },
  failed:     { background: "var(--danger-bg)",       color: "var(--danger-text)" },
};

const selStyle: React.CSSProperties = {
  height: 34, padding: "0 10px", fontSize: 13, border: "1px solid var(--border)",
  borderRadius:"var(--radius-md)", background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit",
};
const btnStyle: React.CSSProperties = {
  padding: "6px 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  background: "var(--surface)", color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit",
};
const th: React.CSSProperties = {
  padding: "8px 14px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

export default function AISessionsPage() {
  const [sessions, setSessions] = useState<AISession[]>([]);
  const [loading, setLoading]   = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [intentFilter, setIntentFilter] = useState("");

  async function load() {
    setLoading(true);
    try {
      const r = await adminAiApi.listSessions({
        status: statusFilter || undefined,
        intent: intentFilter || undefined,
        limit: 50,
      });
      setSessions((r as any)?.data ?? []);
    } catch { setSessions([]); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [statusFilter, intentFilter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <PageHeader eyebrow="Intelligence" context="AI" title="AI Sessions"
        description="All customer AI conversation sessions" actions={<>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={selStyle}>
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="abandoned">Abandoned</option>
            <option value="handed_off">Handed Off</option>
          </select>
          <select value={intentFilter} onChange={e => setIntentFilter(e.target.value)} style={selStyle}>
            <option value="">All Intents</option>
            <option value="booking_intent">Booking</option>
            <option value="service_inquiry">Service Inquiry</option>
            <option value="complaint">Complaint</option>
            <option value="unknown">Unknown</option>
          </select>
          <button onClick={load} disabled={loading} style={btnStyle}>
            {loading ? "Loading…" : "Refresh"}
          </button>
        </>} />

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <Link href="/admin/ai/failed-actions" style={{ fontSize: 13, color: "var(--danger-text)", textDecoration: "none" }}>Failed Actions →</Link>
        <Link href="/admin/ai/metrics"         style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>AI Metrics →</Link>
      </div>

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading sessions…</div>
        ) : sessions.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>No sessions found</div>
        ) : (
          <TableSurface style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                <th style={th}>Session</th>
                <th style={th}>Customer</th>
                <th style={th}>Intent</th>
                <th style={{ ...th, textAlign: "center" }}>Turns</th>
                <th style={th}>Status</th>
                <th style={th}>Created</th>
                <th style={th}></th>
              </tr>
            </thead>
            <tbody>
              {sessions.map(s => (
                <tr key={s.id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "10px 14px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {s.id.slice(0, 8)}…
                  </td>
                  <td style={{ padding: "10px 14px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
                    {s.customer_id?.slice(0, 8) ?? "—"}
                  </td>
                  <td style={{ padding: "10px 14px", color: "var(--text-primary)" }}>{s.current_intent}</td>
                  <td style={{ padding: "10px 14px", textAlign: "center" }}>{s.turn_count}</td>
                  <td style={{ padding: "10px 14px" }}>
                    <span style={{
                      fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                      ...(STATUS_STYLE[s.workflow_status] ?? { background: "var(--surface-sunken)", color: "var(--text-secondary)" }),
                    }}>
                      {s.workflow_status}
                    </span>
                  </td>
                  <td style={{ padding: "10px 14px", fontSize: 11, color: "var(--text-tertiary)" }}>
                    {new Date(s.created_at).toLocaleString()}
                  </td>
                  <td style={{ padding: "10px 14px" }}>
                    <Link href={`/admin/ai/sessions/${s.id}`} style={{ fontSize: 11, color: "var(--accent)", textDecoration: "none" }}>
                      Detail →
                    </Link>
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
