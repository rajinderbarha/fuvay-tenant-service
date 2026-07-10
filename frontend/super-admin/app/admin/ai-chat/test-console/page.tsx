"use client";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Btn, SectionHeader, Skeleton } from "../../../../components/shared/ui";
import { Bot, ChevronLeft, Send, Zap } from "lucide-react";
import { adminAIChatApi, AIPromptTemplate } from "../../../../lib/api";
import { useApi, useAction } from "../../../../hooks/useApi";
import Link from "next/link";

interface ConsoleTurn {
  role: "user" | "assistant";
  content: string;
  latency_ms?: number;
  tokens?: Record<string, number>;
}

export default function TestConsolePage() {
  const [message,     setMessage]     = useState("");
  const [templateKey, setTemplateKey] = useState("");
  const [turns,       setTurns]       = useState<ConsoleTurn[]>([]);
  const [lastUsage,   setLastUsage]   = useState<Record<string, number> | null>(null);

  const templates = useApi(useCallback(
    () => adminAIChatApi.listTemplates({ active_only: true }),
    []
  ));
  const tmpls: AIPromptTemplate[] = templates.data?.templates ?? [];

  const sendAction = useAction(useCallback(
    (msg: string, key: string) =>
      adminAIChatApi.testConsole(msg, key || undefined),
    []
  ));

  async function handleSend() {
    const msg = message.trim();
    if (!msg) return;

    setTurns(prev => [...prev, { role: "user", content: msg }]);
    setMessage("");

    const t0 = Date.now();
    const result = await sendAction.execute(msg, templateKey);
    if (result) {
      const latency = Date.now() - t0;
      setTurns(prev => [
        ...prev,
        { role: "assistant", content: result.reply, latency_ms: latency, tokens: result.usage },
      ]);
      setLastUsage(result.usage ?? null);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const selectStyle: React.CSSProperties = {
    width: "100%", border: "1px solid var(--border)", borderRadius: 8,
    padding: "8px 12px", fontSize: 13, background: "var(--surface-sunken)",
    color: "var(--text-primary)", fontFamily: "inherit", outline: "none",
  };

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
            title="DeepSeek Test Console"
            subtitle="Test prompts directly against the AI without creating a session"
            icon={<Zap size={20} />}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
          {/* Chat panel */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Template selector */}
            <Card>
              <div style={{ padding: "12px 16px" }}>
                <label style={{ display: "block", fontSize: 11, color: "var(--text-tertiary)", marginBottom: 6 }}>
                  System Prompt Template (optional)
                </label>
                {templates.loading ? (
                  <Skeleton height={36} />
                ) : (
                  <select value={templateKey} onChange={e => setTemplateKey(e.target.value)} style={selectStyle}>
                    <option value="">Default (BASE_SYSTEM_PROMPT)</option>
                    {tmpls
                      .filter(t => t.category === "system" || t.category === "safety")
                      .map(t => (
                        <option key={t.template_key} value={t.template_key}>
                          {t.name} ({t.template_key})
                        </option>
                      ))}
                  </select>
                )}
              </div>
            </Card>

            {/* Conversation area */}
            <Card style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ height: 420, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
                {turns.length === 0 && (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-tertiary)" }}>
                    <Bot size={40} style={{ marginBottom: 12, opacity: 0.3 }} />
                    <p style={{ fontSize: 13 }}>Type a message to test DeepSeek</p>
                    <p style={{ fontSize: 11, marginTop: 4, opacity: 0.7 }}>Each call is independent — no session state</p>
                  </div>
                )}
                {turns.map((t, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: t.role === "user" ? "flex-end" : "flex-start" }}>
                    <div style={{
                      maxWidth: "80%", borderRadius: 8, padding: "8px 14px", fontSize: 13,
                      background: t.role === "user" ? "var(--brand)" : "var(--surface-sunken)",
                      color: t.role === "user" ? "#fff" : "var(--text-primary)",
                    }}>
                      <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{t.content}</p>
                      {t.role === "assistant" && (t.latency_ms || t.tokens) && (
                        <p style={{ fontSize: 10, opacity: 0.6, marginTop: 4 }}>
                          {t.latency_ms}ms
                          {t.tokens && ` · ${(t.tokens.prompt_tokens ?? 0) + (t.tokens.completion_tokens ?? 0)} tokens`}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
                {sendAction.loading && (
                  <div style={{ display: "flex", justifyContent: "flex-start" }}>
                    <div style={{ background: "var(--surface-sunken)", borderRadius: 8, padding: "10px 16px", display: "flex", gap: 4 }}>
                      {[0, 1, 2].map(i => (
                        <div key={i} style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--text-tertiary)",
                          animation: "bounce 0.8s infinite", animationDelay: `${i * 0.15}s` }} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div style={{ borderTop: "1px solid var(--border)", padding: 12, display: "flex", gap: 10 }}>
                <textarea
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type your test message… (Enter to send)"
                  rows={2}
                  style={{
                    flex: 1, border: "1px solid var(--border)", borderRadius: 8,
                    padding: "8px 12px", fontSize: 13, resize: "none",
                    fontFamily: "inherit", outline: "none", background: "var(--surface-sunken)",
                    color: "var(--text-primary)",
                  }}
                />
                <Btn
                  onClick={handleSend}
                  loading={sendAction.loading}
                  disabled={!message.trim()}
                  icon={<Send size={14} />}
                  style={{ alignSelf: "flex-end" }}
                >
                  Send
                </Btn>
              </div>
            </Card>

            {sendAction.error && (
              <div style={{ background: "var(--danger-bg)", border: "1px solid var(--danger-border)", borderRadius: 8, padding: 12, color: "var(--danger-text)", fontSize: 13 }}>
                {sendAction.error}
              </div>
            )}
          </div>

          {/* Info panel */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Card>
              <div style={{ padding: "14px 16px" }}>
                <h3 style={{ fontWeight: 600, fontSize: 13, marginBottom: 12 }}>Session Info</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12, color: "var(--text-secondary)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Turns sent</span>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                      {turns.filter(t => t.role === "user").length}
                    </span>
                  </div>
                  {lastUsage && (
                    <>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Last prompt tokens</span>
                        <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{lastUsage.prompt_tokens ?? 0}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>Last completion tokens</span>
                        <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{lastUsage.completion_tokens ?? 0}</span>
                      </div>
                    </>
                  )}
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span>Active template</span>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)", fontFamily: "monospace", fontSize: 11 }}>
                      {templateKey || "default"}
                    </span>
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div style={{ padding: "14px 16px" }}>
                <h3 style={{ fontWeight: 600, fontSize: 13, marginBottom: 12 }}>Safety Rules</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 11 }}>
                  <p style={{ color: "var(--danger-text)", fontWeight: 500, margin: 0 }}>Forbidden output fields:</p>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {[
                      "price", "final_price", "provider_id", "tenant_id",
                      "credit_balance", "subscription_status", "commission",
                      "booking_id", "appointment_id", "lead_id", "payment_status",
                    ].map(f => (
                      <span key={f} style={{ background: "var(--danger-bg)", color: "var(--danger-text)", padding: "1px 6px", borderRadius: 4 }}>
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </Card>

            <Btn variant="secondary" onClick={() => { setTurns([]); setLastUsage(null); }} style={{ width: "100%" }}>
              Clear Console
            </Btn>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
