"use client";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../components/layout/AdminLayout";
import { Card, Badge, StatCard, SectionHeader, Skeleton } from "../../../components/shared/ui";
import { Bot, MessageSquare, BarChart2, AlertCircle, CheckCircle, Clock } from "lucide-react";
import { adminAIChatApi, AIConversationSession } from "../../../lib/api";
import { useApi } from "../../../hooks/useApi";
import Link from "next/link";

const STATUS_VARIANT: Record<string, "success" | "info" | "muted" | "warning"> = {
  active:    "success",
  completed: "info",
  abandoned: "muted",
  paused:    "warning",
};

export default function AIChatDashboard() {
  const [statusFilter, setStatusFilter] = useState("");

  const sessions = useApi(useCallback(
    () => adminAIChatApi.listSessions({ workflow_status: statusFilter || undefined, page_size: 20 }),
    [statusFilter]
  ));
  const logs = useApi(useCallback(
    () => adminAIChatApi.listLogs({ page_size: 5 }),
    []
  ));

  const sessionList: AIConversationSession[] = sessions.data?.sessions ?? [];
  const total = sessions.data?.total ?? 0;

  const active    = sessionList.filter(s => s.workflow_status === "active").length;
  const completed = sessionList.filter(s => s.workflow_status === "completed").length;
  const avgTurns  = sessionList.length
    ? Math.round(sessionList.reduce((a, s) => a + s.turn_count, 0) / sessionList.length)
    : 0;

  const recentLogs = logs.data?.logs ?? [];
  const avgLatency = recentLogs.length
    ? Math.round(recentLogs.reduce((a, l) => a + (l.latency_ms ?? 0), 0) / recentLogs.length)
    : 0;

  const navItems = [
    { label: "Sessions",         href: "/admin/ai-chat/sessions",         icon: <MessageSquare size={16} /> },
    { label: "LLM Logs",         href: "/admin/ai-chat/logs",             icon: <BarChart2 size={16} /> },
    { label: "Prompt Templates", href: "/admin/ai-chat/prompt-templates", icon: <Bot size={16} /> },
    { label: "Test Console",     href: "/admin/ai-chat/test-console",     icon: <AlertCircle size={16} /> },
  ];

  const filterBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: "4px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer",
    border: active ? "1px solid var(--brand)" : "1px solid var(--border)",
    background: active ? "var(--brand)" : "var(--surface)",
    color: active ? "#fff" : "var(--text-secondary)",
    transition: "all 0.12s", fontFamily: "inherit",
  });

  return (
    <AdminLayout>
      <div style={{ padding: "24px 32px", maxWidth: 1280, margin: "0 auto", display: "flex", flexDirection: "column", gap: 24 }}>
        <SectionHeader
          title="AI Conversation Engine"
          subtitle="Monitor DeepSeek sessions, LLM logs, and prompt templates"
          icon={<Bot size={22} />}
        />

        {/* Quick nav */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {navItems.map(nav => (
            <Link key={nav.href} href={nav.href} style={{ textDecoration: "none" }}>
              <Card hover style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--brand)" }}>{nav.icon}</span>
                <span style={{ fontWeight: 500, fontSize: 13, color: "var(--text-primary)" }}>{nav.label}</span>
              </Card>
            </Link>
          ))}
        </div>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          <StatCard label="Total Sessions" value={String(total)}     icon={<MessageSquare size={18} />} />
          <StatCard label="Active Now"     value={String(active)}    icon={<CheckCircle size={18} />} accent="var(--success)" />
          <StatCard label="Completed"      value={String(completed)} icon={<CheckCircle size={18} />} />
          <StatCard label="Avg Latency"    value={`${avgLatency}ms`} icon={<BarChart2 size={18} />} />
        </div>

        {/* Sessions table */}
        <Card>
          <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>Recent Sessions</span>
            <div style={{ display: "flex", gap: 6 }}>
              {["", "active", "completed", "abandoned"].map(s => (
                <button key={s} onClick={() => setStatusFilter(s)} style={filterBtnStyle(statusFilter === s)}>
                  {s || "All"}
                </button>
              ))}
            </div>
          </div>
          {sessions.loading ? (
            <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
              {[...Array(5)].map((_, i) => <Skeleton key={i} height={40} />)}
            </div>
          ) : (
            <div>
              {sessionList.length === 0 ? (
                <p style={{ padding: "24px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
                  No sessions found.
                </p>
              ) : sessionList.map(s => (
                <Link key={s.id} href={`/admin/ai-chat/sessions?id=${s.id}`} style={{ textDecoration: "none" }}>
                  <div style={{
                    padding: "12px 16px", borderBottom: "1px solid var(--border)",
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    cursor: "pointer",
                  }}>
                    <div>
                      <p style={{ fontSize: 12, fontFamily: "monospace", color: "var(--text-primary)" }}>{s.id.slice(0, 8)}…</p>
                      <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Intent: {s.current_intent} · Turns: {s.turn_count}</p>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <Badge variant={STATUS_VARIANT[s.workflow_status] ?? "default"}>{s.workflow_status}</Badge>
                      <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                        {new Date(s.last_activity_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>

        {/* Recent LLM calls */}
        <Card>
          <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>Recent LLM Calls</span>
          </div>
          <div>
            {recentLogs.map(log => (
              <div key={log.id} style={{
                padding: "12px 16px", borderBottom: "1px solid var(--border)",
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}>
                <div>
                  <p style={{ fontSize: 11, fontFamily: "monospace", color: "var(--text-secondary)" }}>{log.id.slice(0, 8)}…</p>
                  <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                    {log.model_used} · {log.prompt_tokens ?? 0}+{log.completion_tokens ?? 0} tokens
                    {log.had_tool_calls ? ` · Tools: ${log.tool_names.join(", ")}` : ""}
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <Badge variant={log.response_status === "success" ? "success" : "danger"}>
                    {log.response_status}
                  </Badge>
                  <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{log.latency_ms}ms</span>
                </div>
              </div>
            ))}
            {recentLogs.length === 0 && (
              <p style={{ padding: "16px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>
                No LLM calls yet.
              </p>
            )}
          </div>
        </Card>
      </div>
    </AdminLayout>
  );
}
