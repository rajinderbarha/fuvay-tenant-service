"use client";
/**
 * MODULE-L5-14 — Customer chat conversation view.
 *
 * Reads a thread's messages and lets the customer reply, marking the thread read
 * on open. Wired to customer_chat_router.
 */
import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import ErrorBanner from "../../../../components/ErrorBanner";
import {
  listChatMessages, sendChatMessage, markThreadRead, ChatMessage,
} from "../../../../lib/api/customer-chat";

export default function CustomerChatThreadPage() {
  const params = useParams();
  const router = useRouter();
  const threadId = params.threadId as string;

  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const load = useCallback(() => {
    listChatMessages(threadId)
      .then((m) => { setMessages(m); markThreadRead(threadId).catch(() => {}); })
      .catch(setError);
  }, [threadId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function handleSend() {
    const t = text.trim();
    if (!t) return;
    setSending(true); setError(null);
    try {
      const msg = await sendChatMessage(threadId, t);
      setText("");
      setMessages((prev) => [...(prev ?? []), msg]);
    } catch (e) { setError(e); } finally { setSending(false); }
  }

  return (
    <div className="co-container" style={{ display: "flex", flexDirection: "column",
      height: "100dvh", paddingBottom: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 0" }}>
        <button onClick={() => router.push("/customer/chat")}
          style={{ background: "none", border: "none", fontSize: 22, cursor: "pointer" }}>‹</button>
        <h1 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Conversation</h1>
      </div>
      <ErrorBanner error={error} />

      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column",
        gap: 8, padding: "8px 0" }}>
        {messages === null ? (
          <div className="co-card">Loading…</div>
        ) : messages.length === 0 ? (
          <div style={{ textAlign: "center", color: "var(--text-tertiary)", padding: 24 }}>
            No messages yet. Say hello to your provider.
          </div>
        ) : (
          messages.map((m) => {
            const mine = m.sender_type === "customer";
            return (
              <div key={m.id} style={{ alignSelf: mine ? "flex-end" : "flex-start",
                maxWidth: "78%", background: mine ? "var(--accent)" : "var(--surface-elevated, #fff)",
                color: mine ? "#fff" : "var(--text-primary)", padding: "9px 13px",
                borderRadius: 16, border: mine ? "none" : "1px solid var(--border)" }}>
                <div style={{ fontSize: 14, whiteSpace: "pre-wrap" }}>{m.message_text}</div>
                <div style={{ fontSize: 10, opacity: 0.7, marginTop: 3, textAlign: "right" }}>
                  {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            );
          })
        )}
        <div ref={endRef} />
      </div>

      <div style={{ display: "flex", gap: 8, padding: "10px 0", borderTop: "1px solid var(--border)" }}>
        <input value={text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleSend(); }}
          placeholder="Type a message…"
          style={{ flex: 1, padding: 12, borderRadius: 24, border: "1px solid var(--border-strong)", fontSize: 15 }} />
        <button className="co-btn-primary" disabled={sending || !text.trim()}
          onClick={handleSend} style={{ borderRadius: 24, minWidth: 72 }}>
          {sending ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
