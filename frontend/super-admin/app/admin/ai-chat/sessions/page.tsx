"use client";
import { TableSurface } from "@serviceos/design-system";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Skeleton, Modal, Pagination } from "../../../../components/shared/ui";
import { MessageSquare, ChevronLeft } from "lucide-react";
import { adminAIChatApi, AIConversationSession, AIConversationMessage } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import Link from "next/link";

const STATUS_VARIANT: Record<string, "success" | "info" | "muted" | "warning"> = {
  active:    "success",
  completed: "info",
  abandoned: "muted",
  paused:    "warning",
};

function SessionDetail({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const session  = useApi(useCallback(() => adminAIChatApi.getSession(sessionId), [sessionId]));
  const messages = useApi(useCallback(() => adminAIChatApi.getSessionMessages(sessionId), [sessionId]));

  const s: AIConversationSession | null = session.data ?? null;
  const msgs: AIConversationMessage[]   = messages.data?.messages ?? [];

  return (
    <Modal open onClose={onClose} title={`Session ${sessionId.slice(0, 8)}…`} size="lg">
      <div style={{ display: "flex", flexDirection: "column", gap: 16, maxHeight: "70vh", overflowY: "auto" }}>
        {session.loading ? (
          <Skeleton height={80} />
        ) : s ? (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 13 }}>
            <div><span style={{ color: "var(--text-tertiary)" }}>Status:</span>{" "}
              <Badge variant={STATUS_VARIANT[s.workflow_status] ?? "default"}>{s.workflow_status}</Badge>
            </div>
            <div><span style={{ color: "var(--text-tertiary)" }}>Intent:</span>{" "}
              <strong>{s.current_intent}</strong>
            </div>
            <div><span style={{ color: "var(--text-tertiary)" }}>Turns:</span>{" "}{s.turn_count}</div>
            <div><span style={{ color: "var(--text-tertiary)" }}>Customer:</span>{" "}
              <span style={{ fontFamily: "monospace", fontSize: 11 }}>{s.customer_id?.slice(0, 8) ?? "Guest"}…</span>
            </div>
            <div style={{ gridColumn: "1/-1" }}>
              <span style={{ color: "var(--text-tertiary)" }}>Last active:</span>{" "}
              <span style={{ fontSize: 11 }}>{new Date(s.last_activity_at).toLocaleString()}</span>
            </div>
          </div>
        ) : null}

        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 16 }}>
          <h4 style={{ fontWeight: 600, fontSize: 13, marginBottom: 12 }}>Conversation</h4>
          {messages.loading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[...Array(4)].map((_, i) => <Skeleton key={i} height={48} />)}
            </div>
          ) : msgs.length === 0 ? (
            <p style={{ color: "var(--text-tertiary)", fontSize: 13, textAlign: "center", padding: "16px 0" }}>No messages yet.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {msgs.map(m => (
                <div
                  key={m.id}
                  style={{
                    display: "flex",
                    justifyContent: m.role === "user" ? "flex-end" : "flex-start",
                  }}
                >
                  <div style={{
                    maxWidth: "85%", borderRadius:"var(--radius-md)", padding: "8px 12px", fontSize: 13,
                    background: m.role === "user" ? "var(--brand)" : "var(--surface-sunken)",
                    color: m.role === "user" ? "#fff" : "var(--text-primary)",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                      <span style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", opacity: 0.6 }}>{m.role}</span>
                      {m.tool_calls_made?.length > 0 && (
                        <span style={{ fontSize: 10, background: "#fef9c3", color: "#854d0e", padding: "1px 6px", borderRadius: 4 }}>
                          Tools: {m.tool_calls_made.join(", ")}
                        </span>
                      )}
                      {m.latency_ms && (
                        <span style={{ fontSize: 10, opacity: 0.5 }}>{m.latency_ms}ms</span>
                      )}
                    </div>
                    <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{m.content}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

export default function AISessionsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page,         setPage]         = useState(1);
  const [selectedId,   setSelectedId]   = useState<string | null>(null);

  const sessions = useApi(useCallback(
    () => adminAIChatApi.listSessions({ workflow_status: statusFilter || undefined, page, page_size: 20 }),
    [statusFilter, page]
  ));

  const sessionList: AIConversationSession[] = sessions.data?.sessions ?? [];
  const total      = sessions.data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  const filterBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: "4px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
    border: active ? "1px solid var(--brand)" : "1px solid var(--border)",
    background: active ? "var(--brand)" : "var(--surface)",
    color: active ? "#fff" : "var(--text-secondary)",
    transition: "all 0.12s", fontFamily: "inherit",
  });

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/admin/ai-chat">
            <button style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-tertiary)", display: "flex" }}>
              <ChevronLeft size={20} />
            </button>
          </Link>
          <SectionHeader
            title="AI Chat Sessions"
            subtitle={`${total} total sessions`}
            icon={<MessageSquare size={20} />}
          />
        </div>

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {["", "active", "completed", "abandoned", "paused"].map(s => (
            <button key={s} onClick={() => { setStatusFilter(s); setPage(1); }} style={filterBtnStyle(statusFilter === s)}>
              {s || "All"}
            </button>
          ))}
        </div>

        <Card>
          <div style={{ overflowX: "auto" }}>
            <TableSurface style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                  {["Session ID", "Customer", "Intent", "Turns", "Status", "Last Active", ""].map(h => (
                    <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sessions.loading ? (
                  [...Array(8)].map((_, i) => (
                    <tr key={i}><td colSpan={7} style={{ padding: "10px 16px" }}><Skeleton height={24} /></td></tr>
                  ))
                ) : sessionList.length === 0 ? (
                  <tr><td colSpan={7} style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-tertiary)" }}>No sessions found.</td></tr>
                ) : sessionList.map(s => (
                  <tr key={s.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 11, color: "var(--text-secondary)" }}>{s.id.slice(0, 12)}…</td>
                    <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>{s.customer_id ? s.customer_id.slice(0, 8) + "…" : "Guest"}</td>
                    <td style={{ padding: "10px 16px" }}>
                      <span style={{ background: "var(--surface-sunken)", color: "var(--text-secondary)", fontSize: 11, padding: "2px 6px", borderRadius: 4 }}>
                        {s.current_intent}
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 13, color: "var(--text-primary)" }}>{s.turn_count}</td>
                    <td style={{ padding: "10px 16px" }}>
                      <Badge variant={STATUS_VARIANT[s.workflow_status] ?? "default"}>{s.workflow_status}</Badge>
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>
                      {new Date(s.last_activity_at).toLocaleString()}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <button onClick={() => setSelectedId(s.id)} style={{ color: "var(--brand)", background: "none", border: "none", cursor: "pointer", fontSize: 12, fontFamily: "inherit" }}>
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </TableSurface>
          </div>
          <Pagination page={page} pageSize={20} total={total} pageCount={totalPages} onPage={setPage} itemLabel="sessions" />
        </Card>

        {selectedId && <SessionDetail sessionId={selectedId} onClose={() => setSelectedId(null)} />}
      </div>
    </AdminLayout>
  );
}
