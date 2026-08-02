"use client";
import { useEffect, useState } from "react";
import { providerAnalyticsApi } from "../../../../lib/api";
import { KpiCard, DateFilter, SimpleTable } from "../../../../components/analytics";

const today = () => new Date().toISOString().slice(0, 10);
const ago30  = () => { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10); };

export default function ProviderQualityPage() {
  const [df, setDf] = useState(ago30);
  const [dt, setDt] = useState(today);
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await providerAnalyticsApi.getQualitySummary({ date_from: df, date_to: dt });
      setData(r?.data ?? null);
    } catch { setData(null); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [df, dt]);

  const s  = data?.summary ?? {};
  const bd = data?.breakdown ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Reviews & Quality</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Customer review scores and satisfaction trends</p>
        </div>
        <DateFilter dateFrom={df} dateTo={dt} onChange={(f, t) => { setDf(f); setDt(t); }} loading={loading} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 16 }}>
        <KpiCard label="Total Reviews"  value={s.total_reviews}   loading={loading} />
        <KpiCard label="Average Rating" value={s.avg_rating}      loading={loading} severity={Number(s.avg_rating) < 3.5 ? "warning" : "success"} />
        <KpiCard label="5-Star Reviews" value={s.five_star_count} loading={loading} />
        <KpiCard label="1-Star Reviews" value={s.one_star_count}  loading={loading} severity={Number(s.one_star_count) > 5 ? "warning" : "normal"} />
      </div>

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>Ratings by Staff</h2>
        <SimpleTable
          rows={bd}
          loading={loading}
          emptyText="No review data for this period"
          columns={[
            { key: "staff_name",    label: "Staff" },
            { key: "avg_rating",    label: "Avg Rating",  numeric: true },
            { key: "review_count",  label: "Reviews",     numeric: true },
            { key: "five_star_pct", label: "5-Star %",    numeric: true },
          ]}
        />
      </div>
    </div>
  );
}
