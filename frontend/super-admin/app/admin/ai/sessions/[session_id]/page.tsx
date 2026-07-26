"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminAiApi, AISession } from "@/lib/api";

const ROLE_STYLE: Record<string, React.CSSProperties> = {
  user:      { background: "var(--info-bg)",        color: "var(--info-text)",    marginLeft: "auto" },
  assistant: { background: "var(--surface-sunken)", color: "var(--text-primary)" },
  system:    { background: "var(--warning-bg)",     color: "var(--warning-text)" },
  tool:      { background: "var(--surface)",        color: "var(--text-secondary)", border: "1px solid var(--border)" },
};

const btnStyle: React.CSSProperties = {
  padding: "6px 14px", fontSize: 13, borderRadius:"var(--radius-md)", cursor: "pointer",
  fontFamily: "inherit", border: "1px solid var(--border)",
  background: "var(--surface)", color: "var(--text-primary)",
};

export default function AISessionDetailPage() {
  const { session_id } = useParams<{ session_id: string }>();
  const [session, setSession] = useState<AISession | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await adminAiApi.getSession(session_id);
      setSession((r as any)?.data ?? null);
    } catch { setSession(null); }
    finally { setLoading(false); }
  }

  async function handoff() {
    await adminAiApi.handoffSession(session_id);
    load();
  }

  async function close() {
    await adminAiApi.closeSession(session_id);
    load();
  }

  useEffect(() => { if (session_id) load(); }, [session_id]);

  if (loading) return <div style={{ padding: 32, color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>;
  if (!session) return <div style={{ padding: 32, color: "var(--text-tertiary)", fontSize: 13 }}>Session not found</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>AI Session</h1>
          <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)", margin: 0 }}>
            {session.id}
          </p>
        </div>
        {session.is_active && (
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={handoff} style={{ ...btnStyle, borderColor: "var(--info-border)", color: "var(--info-text)" }}>
              Handoff to Human
            </button>
            <button onClick={close} style={btnStyle}>Close Session</button>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 16 }}>
        {[
          { label: "Status",   value: session.workflow_status },
          { label: "Intent",   value: session.current_intent },
          { label: "Turns",    value: String(session.turn_count) },
          { label: "Customer", value: session.customer_id?.slice(0, 12) ?? "anonymous" },
        ].map(({ label, value }) => (
          <div key={label} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
            <div style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 4 }}>
              {label}
            </div>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>{value}</div>
          </div>
        ))}
      </div>

      {Object.keys(session.collected_fields ?? {}).length > 0 && (
        <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
          <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 12px" }}>Collected Fields</h2>
          <pre style={{ fontSize: 11, background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: 12,
            overflowX: "auto", color: "var(--text-primary)", margin: 0 }}>
            {JSON.stringify(session.collected_fields, null, 2)}
          </pre>
        </div>
      )}

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>
          Conversation ({session.messages?.length ?? 0} messages)
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 600, overflowY: "auto" }}>
          {(session.messages ?? []).map(msg => (
            <div key={msg.id} style={{
              borderRadius: 10, padding: "10px 14px", maxWidth: "80%",
              ...(ROLE_STYLE[msg.role] ?? { background: "var(--surface-sunken)", color: "var(--text-primary)" }),
            }}>
              <div style={{ fontSize: 11, fontWeight: 500, color: "var(--text-tertiary)", marginBottom: 4, textTransform: "capitalize" }}>
                {msg.role}
              </div>
              <div style={{ fontSize: 13, whiteSpace: "pre-wrap" }}>{msg.content}</div>
              <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 4 }}>
                {new Date(msg.created_at).toLocaleTimeString()}
              </div>
            </div>
          ))}
          {(!session.messages || session.messages.length === 0) && (
            <div style={{ textAlign: "center", color: "var(--text-tertiary)", fontSize: 13, padding: "16px 0" }}>
              No messages
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
