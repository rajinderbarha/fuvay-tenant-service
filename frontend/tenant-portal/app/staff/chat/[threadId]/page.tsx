"use client";
/**
 * MODULE-L5-19 — Staff chat conversation view.
 *
 * The technician reads a thread's messages and replies to the customer. Wired to
 * staff_chat_router; marks the thread read on open.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { StaffLayout } from "../../../../components/layout/StaffLayout";
import { Skeleton } from "../../../../components/shared/ui";
import { useApi } from "../../../../hooks/useApi";
import { staffChatApi } from "../../../../lib/api";

export default function StaffChatThreadPage() {
  const params = useParams();
  const router = useRouter();
  const threadId = params.threadId as string;

  const messages = useApi(useCallback(() => staffChatApi.listMessages(threadId), [threadId]));
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { staffChatApi.markRead(threadId).catch(() => {}); }, [threadId]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.data]);

  async function send() {
    const t = text.trim();
    if (!t) return;
    setSending(true); setErr(null);
    try {
      await staffChatApi.sendMessage(threadId, t);
      setText("");
      messages.refetch();
    } catch (e) { setErr(e instanceof Error ? e.message : "Failed to send."); }
    finally { setSending(false); }
  }

  return (
    <StaffLayout activeNav="chat">
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <button onClick={() => router.push("/staff/chat")}
          style={{ background: "none", border: "none", fontSize: 22, cursor: "pointer" }}>‹</button>
        <h1 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>Conversation</h1>
      </div>
      {err && <div style={{ color: "var(--danger-text)", fontSize: 13, marginBottom: 10 }}>{err}</div>}

      <div style={{ display: "flex", flexDirection: "column", gap: 8, minHeight: 300,
        maxHeight: "60vh", overflowY: "auto", padding: "8px 0" }}>
        {messages.loading ? <Skeleton /> : (messages.data ?? []).length === 0 ? (
          <p style={{ fontSize: 13, color: "var(--text-tertiary)", textAlign: "center", padding: 24 }}>
            No messages yet.
          </p>
        ) : (
          (messages.data ?? []).map(m => {
            const mine = m.sender_type === "staff" || m.sender_type === "provider";
            return (
              <div key={m.id} style={{ alignSelf: mine ? "flex-end" : "flex-start", maxWidth: "70%",
                background: mine ? "var(--brand)" : "var(--surface-sunken, #f4f4f5)",
                color: mine ? "#fff" : "var(--text-primary)", padding: "9px 13px", borderRadius: 14,
                border: mine ? "none" : "1px solid var(--border)" }}>
                <div style={{ fontSize: 14, whiteSpace: "pre-wrap" }}>{m.message_text}</div>
                <div style={{ fontSize: 10, opacity: 0.7, marginTop: 3, textAlign: "right" }}>
                  {m.sender_type} · {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            );
          })
        )}
        <div ref={endRef} />
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 12, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
        <input value={text} onChange={e => setText(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") send(); }}
          placeholder="Reply to the customer…"
          style={{ flex: 1, padding: 11, borderRadius: 10, border: "1px solid var(--border)", fontSize: 14 }} />
        <button onClick={send} disabled={sending || !text.trim()}
          style={{ padding: "0 18px", borderRadius: 10, border: "none", background: "var(--brand)",
            color: "#fff", fontWeight: 600, cursor: "pointer" }}>
          {sending ? "…" : "Send"}
        </button>
      </div>
    </StaffLayout>
  );
}
