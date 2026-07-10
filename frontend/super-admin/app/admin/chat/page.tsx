"use client";
import { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Btn, Modal, SectionHeader } from "../../../components/shared/ui";
import { sprint27AdminApi, type ChatThreadRecord, type ChatMessageRecord } from "../../../lib/api";
import { useApi, useAction } from "../../../hooks/useApi";

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  open:     { background: "var(--success-bg)",     color: "var(--success-text)" },
  closed:   { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  archived: { background: "var(--surface-sunken)", color: "var(--text-tertiary)" },
  blocked:  { background: "var(--danger-bg)",      color: "var(--danger-text)" },
};

const th: React.CSSProperties = {
  padding: "10px 16px", fontSize: 11, fontWeight: 700, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--text-tertiary)", textAlign: "left",
};

const selStyle: React.CSSProperties = {
  height: 36, padding: "0 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius: 8,
  background: "var(--surface)", color: "var(--text-primary)", fontFamily: "inherit",
};

export default function AdminChatPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [viewThread, setViewThread] = useState<ChatThreadRecord | null>(null);
  const [messages, setMessages] = useState<ChatMessageRecord[]>([]);
  const [hideReason, setHideReason] = useState("");
  const [hideTarget, setHideTarget] = useState<string | null>(null);

  const threads = useApi(
    useCallback(() => sprint27AdminApi.listChatThreads({
      ...(statusFilter ? { status: statusFilter } : {}),
      limit: 50,
    }), [statusFilter])
  );

  const closeAction = useAction(
    useCallback((id: string) => sprint27AdminApi.closeThread(id), [])
  );

  const hideAction = useAction(
    useCallback((id: string, reason: string) => sprint27AdminApi.hideMessage(id, reason), [])
  );

  async function openThread(thread: ChatThreadRecord) {
    setViewThread(thread);
    loadMessages(thread.id);
  }

  async function loadMessages(threadId: string) {
    const res = await sprint27AdminApi.listChatMessages(threadId, { limit: 100 });
    setMessages(res.items ?? []);
  }

  const items: ChatThreadRecord[] = threads.data?.items ?? [];

  return (
    <AdminLayout>
      <SectionHeader title="Chat Threads" subtitle="All platform chat threads" />

      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <select style={selStyle} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">All Statuses</option>
          {["open", "closed", "archived", "blocked"].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <Btn size="sm" variant="ghost" onClick={() => setStatusFilter("")}>Clear</Btn>
      </div>

      <Card>
        {threads.loading ? (
          <div style={{ padding: 24, textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                  {["Thread #", "Record Type", "Record ID", "Status", "Last Message", "Created", "Actions"].map(h => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map(t => (
                  <tr key={t.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 600, color: "var(--text-primary)" }}>
                      {t.thread_number}
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 12, color: "var(--text-secondary)" }}>{t.record_type}</td>
                    <td style={{ padding: "10px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {t.record_id.slice(0, 8)}…
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
                        ...(STATUS_STYLE[t.status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
                        {t.status}
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {t.last_message_at ? t.last_message_at.replace("T", " ").slice(0, 16) : "—"}
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)" }}>
                      {t.created_at.replace("T", " ").slice(0, 16)}
                    </td>
                    <td style={{ padding: "10px 16px", display: "flex", gap: 8 }}>
                      <Btn size="xs" variant="ghost" onClick={() => openThread(t)}>View</Btn>
                      {t.status === "open" && (
                        <Btn size="xs" variant="danger"
                          onClick={() => closeAction.execute(t.id).then(() => threads.refetch())}
                          loading={closeAction.loading}>
                          Close
                        </Btn>
                      )}
                    </td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
                      No threads found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {viewThread && (
        <Modal open={!!viewThread} title={`Thread: ${viewThread.thread_number}`} onClose={() => setViewThread(null)}>
          <div style={{ marginBottom: 12, fontSize: 13 }}>
            <span style={{ color: "var(--text-tertiary)" }}>Record:</span>{" "}
            {viewThread.record_type} / {viewThread.record_id}
            <span style={{ marginLeft: 8, fontSize: 11, padding: "2px 8px", borderRadius: 999, fontWeight: 600,
              ...(STATUS_STYLE[viewThread.status] ?? { background: "var(--surface-sunken)", color: "var(--text-tertiary)" }) }}>
              {viewThread.status}
            </span>
          </div>
          <div style={{ border: "1px solid var(--border)", borderRadius: 10, background: "var(--surface-sunken)",
            padding: 12, maxHeight: 288, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
            {messages.length === 0 && (
              <div style={{ color: "var(--text-tertiary)", fontSize: 13, textAlign: "center", padding: "16px 0" }}>No messages</div>
            )}
            {messages.map(msg => (
              <div key={msg.id} style={{ display: "flex", gap: 8, justifyContent: msg.sender_type === "customer" ? "flex-start" : "flex-end" }}>
                <div style={{
                  borderRadius: 10, padding: "8px 12px", fontSize: 13, maxWidth: 280,
                  background: msg.sender_type === "customer" ? "var(--surface)" :
                              msg.sender_type === "system"   ? "var(--surface-sunken)" : "var(--info-bg)",
                  border: msg.sender_type === "customer" ? "1px solid var(--border)" :
                          msg.sender_type === "system"   ? "none" : "1px solid var(--info-border)",
                  color: msg.sender_type === "system" ? "var(--text-tertiary)" : "var(--text-primary)",
                }}>
                  <div style={{ fontSize: 10, color: "var(--text-tertiary)", marginBottom: 4 }}>{msg.sender_type}</div>
                  {msg.message_text}
                  <div style={{ marginTop: 6 }}>
                    <Btn size="xs" variant="ghost" onClick={() => setHideTarget(msg.id)}>Hide</Btn>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
            {viewThread.status === "open" && (
              <Btn variant="danger" size="sm"
                onClick={() => closeAction.execute(viewThread.id).then(() => { setViewThread(null); threads.refetch(); })}
                loading={closeAction.loading}>
                Close Thread
              </Btn>
            )}
            <Btn variant="ghost" size="sm" onClick={() => setViewThread(null)}>Close</Btn>
          </div>
        </Modal>
      )}

      {hideTarget && (
        <Modal open={!!hideTarget} title="Hide Message" onClose={() => setHideTarget(null)}>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>Reason for hiding:</label>
            <textarea style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px",
              fontSize: 13, background: "var(--bg)", color: "var(--text-primary)", fontFamily: "inherit",
              boxSizing: "border-box" }} rows={3}
              value={hideReason}
              onChange={e => setHideReason(e.target.value)}
              placeholder="Explain why this message is being hidden…" />
            <div style={{ display: "flex", gap: 8 }}>
              <Btn variant="danger"
                onClick={() => hideAction.execute(hideTarget, hideReason).then(() => {
                  setHideTarget(null); setHideReason("");
                  if (viewThread) loadMessages(viewThread.id);
                })}
                loading={hideAction.loading}
                disabled={!hideReason.trim()}>
                Hide Message
              </Btn>
              <Btn variant="ghost" onClick={() => setHideTarget(null)}>Cancel</Btn>
            </div>
          </div>
        </Modal>
      )}
    </AdminLayout>
  );
}
