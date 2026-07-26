"use client";
import { useEffect, useState } from "react";
import { adminAnalyticsApi } from "@/lib/api";
import {
  AnalyticsKpiCard,
  AnalyticsDateFilter,
  AnalyticsBreakdownTable,
} from "@/components/analytics";

const today = () => new Date().toISOString().slice(0, 10);
const ago30  = () => { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10); };

const card: React.CSSProperties = {
  background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20,
};
const h2: React.CSSProperties = { fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 12px" };

export default function QualityAnalyticsPage() {
  const [df, setDf] = useState(ago30);
  const [dt, setDt] = useState(today);
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await adminAnalyticsApi.getQualitySummary({ date_from: df, date_to: dt });
      setData(r?.data ?? null);
    } catch { setData(null); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [df, dt]);

  const s  = data?.summary ?? {};
  const ti = data?.top_items ?? [];
  const bd = data?.breakdown ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Quality & Reviews</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Platform ratings, review volume and quality trends</p>
        </div>
        <AnalyticsDateFilter dateFrom={df} dateTo={dt} onChange={(f, t) => { setDf(f); setDt(t); }} loading={loading} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 16 }}>
        <AnalyticsKpiCard label="Total Reviews"  value={s.total_reviews}       loading={loading} />
        <AnalyticsKpiCard label="Platform Avg"   value={s.platform_avg_rating} loading={loading} severity={Number(s.platform_avg_rating) < 3.5 ? "warning" : "success"} />
        <AnalyticsKpiCard label="5-Star Reviews" value={s.five_star_count}     loading={loading} />
        <AnalyticsKpiCard label="1-Star Reviews" value={s.one_star_count}      loading={loading} severity={Number(s.one_star_count) > 20 ? "warning" : "normal"} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(320px,1fr))", gap: 24 }}>
        <div style={card}>
          <h2 style={h2}>Highest Rated Providers</h2>
          <AnalyticsBreakdownTable
            rows={ti}
            loading={loading}
            columns={[
              { key: "tenant_name",    label: "Provider" },
              { key: "avg_rating",     label: "Avg Rating",    numeric: true },
              { key: "review_count",   label: "Reviews",       numeric: true },
              { key: "five_star_pct",  label: "5-Star %",      numeric: true },
            ]}
          />
        </div>
        <div style={card}>
          <h2 style={h2}>Rating by Category</h2>
          <AnalyticsBreakdownTable
            rows={bd}
            loading={loading}
            columns={[
              { key: "category_name", label: "Category" },
              { key: "avg_rating",    label: "Avg Rating",  numeric: true },
              { key: "review_count",  label: "Reviews",     numeric: true },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
