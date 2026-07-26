"use client";
import React, { useCallback, useState } from "react";
import { AdminLayout } from "../../../../components/layout/AdminLayout";
import { Card, Badge, Btn, SectionHeader, Skeleton, Modal } from "../../../../components/shared/ui";
import { BarChart2, ChevronLeft, Zap } from "lucide-react";
import { adminAIChatApi, AILLMCallLog } from "../../../../lib/api";
import { useApi } from "../../../../hooks/useApi";
import Link from "next/link";

function LogDetail({ logId, onClose }: { logId: string; onClose: () => void }) {
  const log = useApi(useCallback(() => adminAIChatApi.getLog(logId), [logId]));
  const l: AILLMCallLog | null = log.data ?? null;

  return (
    <Modal open onClose={onClose} title={`LLM Call ${logId.slice(0, 8)}…`}>
      {log.loading ? <Skeleton height={160} /> : l ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, fontSize: 13 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div><span style={{ color: "var(--text-tertiary)" }}>Model:</span> <strong>{l.model_used}</strong></div>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <span style={{ color: "var(--text-tertiary)" }}>Status:</span>
              <Badge variant={l.response_status === "success" ? "success" : "danger"}>{l.response_status}</Badge>
            </div>
            <div><span style={{ color: "var(--text-tertiary)" }}>Prompt tokens:</span> {l.prompt_tokens ?? "—"}</div>
            <div><span style={{ color: "var(--text-tertiary)" }}>Completion tokens:</span> {l.completion_tokens ?? "—"}</div>
            <div><span style={{ color: "var(--text-tertiary)" }}>Latency:</span> {l.latency_ms}ms</div>
            <div><span style={{ color: "var(--text-tertiary)" }}>Tool calls:</span> {l.had_tool_calls ? l.tool_names.join(", ") : "None"}</div>
          </div>
          {l.error_message && (
            <div style={{
              background: "var(--danger-bg)", border: "1px solid var(--danger-border)",
              borderRadius:"var(--radius-md)", padding: 12, color: "var(--danger-text)", fontSize: 12,
            }}>
              {l.error_message}
            </div>
          )}
          {l.tool_calls && l.tool_calls.length > 0 && (
            <div>
              <h4 style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>Tool Calls</h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {l.tool_calls.map(tc => (
                  <div key={tc.id} style={{ background: "var(--surface-sunken)", borderRadius:"var(--radius-md)", padding: 12 }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                      <span style={{ fontWeight: 500, fontSize: 12 }}>{tc.tool_name}</span>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <Badge variant={tc.success ? "success" : "danger"}>{tc.success ? "OK" : "Error"}</Badge>
                        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{tc.latency_ms}ms</span>
                      </div>
                    </div>
                    <pre style={{ fontSize: 11, color: "var(--text-secondary)", overflow: "auto", maxHeight: 96, margin: 0 }}>
                      {JSON.stringify(tc.input_params, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : null}
    </Modal>
  );
}

export default function AILogsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page,         setPage]         = useState(1);
  const [selectedId,   setSelectedId]   = useState<string | null>(null);

  const logs = useApi(useCallback(
    () => adminAIChatApi.listLogs({ response_status: statusFilter || undefined, page, page_size: 20 }),
    [statusFilter, page]
  ));

  const logList: AILLMCallLog[] = logs.data?.logs ?? [];
  const total      = logs.data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  const totalTokens = logList.reduce(
    (a, l) => a + (l.prompt_tokens ?? 0) + (l.completion_tokens ?? 0), 0
  );
  const avgLatency = logList.length
    ? Math.round(logList.reduce((a, l) => a + (l.latency_ms ?? 0), 0) / logList.length)
    : 0;
  const toolCallCount = logList.filter(l => l.had_tool_calls).length;

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
            title="LLM Call Logs"
            subtitle={`${total} DeepSeek API calls recorded`}
            icon={<BarChart2 size={20} />}
          />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          <Card>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Total tokens (this page)</p>
            <p style={{ fontSize: 26, fontWeight: 700, color: "var(--brand)", marginTop: 4 }}>{totalTokens.toLocaleString()}</p>
          </Card>
          <Card>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Avg latency (this page)</p>
            <p style={{ fontSize: 26, fontWeight: 700, color: "var(--brand)", marginTop: 4 }}>{avgLatency}ms</p>
          </Card>
          <Card>
            <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Calls with tool use</p>
            <p style={{ fontSize: 26, fontWeight: 700, color: "var(--brand)", marginTop: 4 }}>{toolCallCount}</p>
          </Card>
        </div>

        <div style={{ display: "flex", gap: 6 }}>
          {["", "success", "error", "timeout"].map(s => (
            <button key={s} onClick={() => { setStatusFilter(s); setPage(1); }} style={filterBtnStyle(statusFilter === s)}>
              {s || "All"}
            </button>
          ))}
        </div>

        <Card>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-sunken)" }}>
                  {["Call ID", "Model", "Tokens", "Latency", "Tools", "Status", "Time", ""].map(h => (
                    <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.loading ? (
                  [...Array(8)].map((_, i) => (
                    <tr key={i}><td colSpan={8} style={{ padding: "10px 16px" }}><Skeleton height={24} /></td></tr>
                  ))
                ) : logList.length === 0 ? (
                  <tr><td colSpan={8} style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-tertiary)" }}>No logs found.</td></tr>
                ) : logList.map(l => (
                  <tr key={l.id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "10px 16px", fontFamily: "monospace", fontSize: 11 }}>{l.id.slice(0, 10)}…</td>
                    <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-secondary)" }}>{l.model_used}</td>
                    <td style={{ padding: "10px 16px", fontSize: 11 }}>{(l.prompt_tokens ?? 0) + (l.completion_tokens ?? 0)}</td>
                    <td style={{ padding: "10px 16px", fontSize: 11 }}>{l.latency_ms}ms</td>
                    <td style={{ padding: "10px 16px" }}>
                      {l.had_tool_calls ? (
                        <span style={{ fontSize: 11, background: "#fef9c3", color: "#854d0e", padding: "2px 6px", borderRadius: 4, display: "inline-flex", alignItems: "center", gap: 3 }}>
                          <Zap size={10} />{l.tool_names.length}
                        </span>
                      ) : <span style={{ color: "var(--text-tertiary)", fontSize: 11 }}>—</span>}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <Badge variant={l.response_status === "success" ? "success" : "danger"}>{l.response_status}</Badge>
                    </td>
                    <td style={{ padding: "10px 16px", fontSize: 11, color: "var(--text-tertiary)", whiteSpace: "nowrap" }}>{new Date(l.created_at).toLocaleString()}</td>
                    <td style={{ padding: "10px 16px" }}>
                      <button onClick={() => setSelectedId(l.id)} style={{ color: "var(--brand)", background: "none", border: "none", cursor: "pointer", fontSize: 12, fontFamily: "inherit" }}>
                        Detail
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div style={{ padding: "10px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", borderTop: "1px solid var(--border)" }}>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Page {page} of {totalPages}</span>
              <div style={{ display: "flex", gap: 8 }}>
                <Btn size="sm" variant="secondary" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Prev</Btn>
                <Btn size="sm" variant="secondary" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Next</Btn>
              </div>
            </div>
          )}
        </Card>

        {selectedId && <LogDetail logId={selectedId} onClose={() => setSelectedId(null)} />}
      </div>
    </AdminLayout>
  );
}
