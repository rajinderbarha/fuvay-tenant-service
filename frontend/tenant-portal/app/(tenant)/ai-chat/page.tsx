"use client";
import React, { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { useAction } from "../../../hooks/useApi";
import { aiChatApi, type AIChatMessage } from "../../../lib/api";

interface BookingPayload {
  service_type?: string;
  scheduled_at?: string;
  notes?: string;
  [key: string]: unknown;
}

interface MessageBubble {
  role: "user" | "assistant";
  content: string;
  tools_called?: string[];
  booking?: BookingPayload;
}

function parseBookingTag(text: string): { clean: string; booking: BookingPayload | null } {
  const open = "<BOOK>";
  const close = "</BOOK>";
  const start = text.indexOf(open);
  const end = text.indexOf(close);
  if (start === -1 || end === -1) return { clean: text, booking: null };
  const json = text.slice(start + open.length, end).trim();
  const before = text.slice(0, start).trim();
  const after = text.slice(end + close.length).trim();
  try {
    return { clean: [before, after].filter(Boolean).join("\n\n"), booking: JSON.parse(json) };
  } catch {
    return { clean: text, booking: null };
  }
}

export default function AiChatPage() {
  const [messages, setMessages] = useState<MessageBubble[]>([]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { execute: send, loading, error } = useAction(
    useCallback(async (text: string) => {
      const history: AIChatMessage[] = messages.map(m => ({ role: m.role, content: m.content }));
      setMessages(p => [...p, { role: "user", content: text }]);
      const res = await aiChatApi.chat(text, history);
      if (res) {
        const { clean, booking } = parseBookingTag(res.reply);
        setMessages(p => [...p, {
          role: "assistant",
          content: clean,
          tools_called: res.tools_called,
          booking: booking ?? undefined,
        }]);
      }
      return res;
    }, [messages])
  );

  const handleSend = () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    send(text);
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <TenantLayout activeNav="ai-assistant">
      <div style={{ maxWidth:780, display:"flex", flexDirection:"column",
        height:"calc(100vh - 120px)", minHeight:400 }}>

        <h1 style={{ fontSize:22, fontWeight:700, margin:"0 0 4px", color:"var(--text-primary)" }}>
          AI Assistant
        </h1>
        <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:"0 0 16px" }}>
          Powered by DeepSeek · Ask about services, bookings, jobs, or availability
        </p>

        {/* Chat area */}
        <div style={{ flex:1, overflowY:"auto", display:"flex", flexDirection:"column",
          gap:14, padding:"4px 0", marginBottom:16 }}>

          {messages.length === 0 && (
            <div style={{ textAlign:"center", padding:"48px 0" }}>
              <p style={{ fontSize:36, margin:"0 0 10px" }}>🤖</p>
              <p style={{ fontSize:15, color:"var(--text-secondary)", margin:"0 0 6px", fontWeight:600 }}>
                How can I help you today?
              </p>
              <p style={{ fontSize:13, color:"var(--text-tertiary)", margin:0 }}>
                Ask about available slots, your bookings, service catalog, or current jobs.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} style={{ display:"flex", flexDirection:"column",
              alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}>

              <div style={{
                maxWidth:"82%",
                background: msg.role === "user" ? "var(--accent)" : "var(--surface)",
                color: msg.role === "user" ? "white" : "var(--text-primary)",
                border: msg.role === "assistant" ? "1px solid var(--border)" : "none",
                borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                padding:"12px 16px",
                fontSize:14, lineHeight:1.55,
                whiteSpace:"pre-wrap",
              }}>
                {msg.content}
              </div>

              {/* Tool badges */}
              {msg.tools_called && msg.tools_called.length > 0 && (
                <div style={{ display:"flex", gap:4, marginTop:5, flexWrap:"wrap" }}>
                  {msg.tools_called.map(t => (
                    <span key={t} style={{ fontSize:10, padding:"2px 7px", borderRadius:999,
                      background:"var(--surface)", border:"1px solid var(--border)",
                      color:"var(--text-tertiary)", fontWeight:500 }}>
                      🔧 {t}
                    </span>
                  ))}
                </div>
              )}

              {/* BOOK CTA card */}
              {msg.booking && (
                <div style={{ marginTop:8, maxWidth:"82%", background:"var(--surface)",
                  border:"1px solid var(--accent)", borderRadius:"var(--radius-lg)",
                  padding:"14px 16px" }}>
                  <p style={{ margin:"0 0 8px", fontWeight:700, fontSize:13, color:"var(--accent)" }}>
                    📅 Booking Request Detected
                  </p>
                  {Object.entries(msg.booking).map(([k, v]) => (
                    v != null && (
                      <p key={k} style={{ margin:"0 0 3px", fontSize:12, color:"var(--text-secondary)" }}>
                        <strong style={{ textTransform:"capitalize" }}>{k.replace(/_/g," ")}:</strong>{" "}
                        {String(v)}
                      </p>
                    )
                  ))}
                  <Link href="/jobs"
                    style={{ display:"inline-block", marginTop:10, padding:"7px 16px", borderRadius:"var(--radius-md)",
                      background:"var(--accent)", color:"white", fontWeight:600, fontSize:12,
                      textDecoration:"none" }}>
                    Book Now →
                  </Link>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={{ display:"flex", alignItems:"flex-start" }}>
              <div style={{ background:"var(--surface)", border:"1px solid var(--border)",
                borderRadius:"14px 14px 14px 4px", padding:"12px 16px" }}>
                <span style={{ display:"inline-flex", gap:4 }}>
                  {[0,1,2].map(i => (
                    <span key={i} style={{
                      width:6, height:6, borderRadius:"50%", background:"var(--text-tertiary)",
                      display:"inline-block",
                      animation:`pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                    }}/>
                  ))}
                </span>
              </div>
            </div>
          )}

          {error && (
            <p style={{ fontSize:12, color:"var(--danger)", textAlign:"center" }}>{error}</p>
          )}

          <div ref={bottomRef}/>
        </div>

        {/* Input area */}
        <div style={{ borderTop:"1px solid var(--border)", paddingTop:14, flexShrink:0 }}>
          <div style={{ display:"flex", gap:10, alignItems:"flex-end" }}>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask anything… (Shift+Enter for newline)"
              rows={2}
              style={{ flex:1, padding:"10px 14px", borderRadius:"var(--radius-lg)",
                border:"1px solid var(--border)", background:"var(--surface)",
                color:"var(--text-primary)", fontSize:14, fontFamily:"inherit",
                resize:"none", outline:"none", lineHeight:1.5 }}
            />
            <button onClick={handleSend} disabled={loading || !input.trim()}
              style={{ height:44, width:44, borderRadius:"var(--radius-lg)", border:"none",
                background: (loading || !input.trim()) ? "var(--border)" : "var(--accent)",
                color:"white", fontSize:20, cursor:(loading || !input.trim()) ? "not-allowed" : "pointer",
                flexShrink:0, display:"flex", alignItems:"center", justifyContent:"center" }}>
              ↑
            </button>
          </div>
          <p style={{ margin:"6px 0 0", fontSize:11, color:"var(--text-tertiary)", textAlign:"center" }}>
            AI responses are for guidance only. Always verify bookings and availability directly.
          </p>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </TenantLayout>
  );
}
