"use client";
import { useEffect, useState } from "react";
import { adminAiApi, AIActionLog } from "@/lib/api";
import { PageHeader } from "@serviceos/design-system";
import { Btn } from "@/components/shared/ui";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  blocked: { background: "var(--danger-bg)",  color: "var(--danger-text)" },
  failed:  { background: "var(--warning-bg)", color: "var(--warning-text)" },
};

export default function AIFailedActionsPage() {
  const [logs, setLogs]       = useState<AIActionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const r = await adminAiApi.listFailedActions({ limit: 100 });
      setLogs((r as any)?.data ?? []);
    } catch { setLogs([]); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <PageHeader
        title="Failed AI Actions"
        description="Blocked and failed backend action requests from AI."
        eyebrow="Intelligence"
        actions={<Btn variant="secondary" size="sm" onClick={load} loading={loading}>Refresh</Btn>}
      />

      {loading ? (
        <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
      ) : logs.length === 0 ? (
        <div style={{ textAlign: "center", padding: "32px 0", color: "var(--success-text)", fontSize: 13 }}>
          No failed or blocked actions — AI is behaving safely.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {logs.map(log => (
            <div key={log.id} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <span style={{
                      fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 700,
                      textTransform: "uppercase", letterSpacing: "0.06em",
                      ...(STATUS_STYLE[log.status] ?? { background: "var(--surface-sunken)", color: "var(--text-secondary)" }),
                    }}>
                      {log.status}
                    </span>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{log.action}</span>
                    {log.failure_code && (
                      <span style={{ fontSize: 11, color: "var(--danger-text)", fontFamily: "'JetBrains Mono', monospace" }}>{log.failure_code}</span>
                    )}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 4, fontSize: 11, color: "var(--text-tertiary)" }}>
                    <span>Session: {log.session_id.slice(0, 12)}…</span>
                    {log.flow_type && <span>Flow: {log.flow_type}</span>}
                    {log.intent && <span>Intent: {log.intent}</span>}
                    <span>{new Date(log.created_at).toLocaleString()}</span>
                  </div>
                  {log.failure_message && (
                    <div style={{ marginTop: 8, fontSize: 11, color: "var(--danger-text)", background: "var(--danger-bg)", borderRadius: 6, padding: "6px 10px" }}>
                      {log.failure_message}
                    </div>
                  )}
                </div>
                <Btn variant="secondary" size="sm" onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                  style={{ flexShrink: 0 }}>
                  {expanded === log.id ? "Hide" : "Payload"}
                </Btn>
              </div>
              {expanded === log.id && log.request_payload && (
                <pre style={{
                  marginTop: 12, fontSize: 11, background: "var(--surface-sunken)", borderRadius:"var(--radius-md)",
                  padding: 12, overflow: "auto", maxHeight: 160, color: "var(--text-secondary)",
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {JSON.stringify(log.request_payload, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
