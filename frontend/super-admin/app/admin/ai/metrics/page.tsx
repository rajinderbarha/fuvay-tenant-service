"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { adminAiApi, AIMetrics } from "@/lib/api";
import { AnalyticsKpiCard } from "@/components/analytics";

const btnStyle: React.CSSProperties = {
  padding: "6px 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
  background: "var(--surface)", color: "var(--text-secondary)", cursor: "pointer", fontFamily: "inherit",
};

export default function AIMetricsPage() {
  const [metrics, setMetrics] = useState<AIMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await adminAiApi.getMetrics();
      setMetrics((r as any)?.data ?? null);
    } catch { setMetrics(null); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  const m = metrics ?? {} as AIMetrics;
  const rl = m.rate_limiter ?? { active_customers_in_msg_window: 0, customers_in_cooldown: 0 };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>AI Metrics</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>AI action execution statistics and rate limiter status</p>
        </div>
        <button onClick={load} disabled={loading} style={btnStyle}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 16 }}>
        <AnalyticsKpiCard label="Executed Actions"  value={m.executed_count}   loading={loading} severity="success" />
        <AnalyticsKpiCard label="Blocked Actions"   value={m.blocked_count}    loading={loading} severity={Number(m.blocked_count) > 10 ? "warning" : "normal"} />
        <AnalyticsKpiCard label="Failed Actions"    value={m.failed_count}     loading={loading} severity={Number(m.failed_count) > 5 ? "critical" : "normal"} />
        <AnalyticsKpiCard label="Validated"         value={m.validated_count}  loading={loading} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 16 }}>
        <AnalyticsKpiCard label="Unique Sessions"   value={m.unique_sessions}  loading={loading} />
        <AnalyticsKpiCard label="Unique Customers"  value={m.unique_customers} loading={loading} />
        <AnalyticsKpiCard label="Last Hour Actions" value={m.last_hour_count}  loading={loading} />
        <AnalyticsKpiCard label="In Cooldown Now"   value={rl.customers_in_cooldown}
          loading={loading} severity={Number(rl.customers_in_cooldown) > 0 ? "warning" : "normal"} />
      </div>

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 12px" }}>Rate Limiter Status</h2>
        <div style={{ fontSize: 13, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 4 }}>
          <div>Active customers sending messages (last 60s): <strong style={{ color: "var(--text-primary)" }}>{rl.active_customers_in_msg_window}</strong></div>
          <div>Customers in failure cooldown: <strong style={{ color: "var(--text-primary)" }}>{rl.customers_in_cooldown}</strong></div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Link href="/admin/ai/sessions"       style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>All Sessions →</Link>
        <Link href="/admin/ai/failed-actions" style={{ fontSize: 13, color: "var(--danger-text)", textDecoration: "none" }}>Failed Actions →</Link>
      </div>
    </div>
  );
}
