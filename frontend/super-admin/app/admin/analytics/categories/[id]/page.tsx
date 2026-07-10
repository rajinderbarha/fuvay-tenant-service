"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { adminAnalyticsApi } from "@/lib/api";
import {
  AnalyticsKpiCard,
  AnalyticsDateFilter,
  AnalyticsBreakdownTable,
} from "@/components/analytics";

const today = () => new Date().toISOString().slice(0, 10);
const ago30  = () => { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10); };

const card: React.CSSProperties = {
  background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 20,
};
const h2: React.CSSProperties = { fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 12px" };

export default function CategoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [df, setDf] = useState(ago30);
  const [dt, setDt] = useState(today);
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await adminAnalyticsApi.getCategoryDetail(id, { date_from: df, date_to: dt });
      setData(r?.data ?? null);
    } catch { setData(null); }
    finally { setLoading(false); }
  }

  useEffect(() => { if (id) load(); }, [id, df, dt]);

  const summary    = data?.summary ?? {};
  const topItems   = data?.top_items ?? [];
  const breakdown  = data?.breakdown ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>
            {summary.category_name ?? "Category Detail"}
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Detailed analytics for this category</p>
        </div>
        <AnalyticsDateFilter dateFrom={df} dateTo={dt} onChange={(f, t) => { setDf(f); setDt(t); }} loading={loading} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 16 }}>
        <AnalyticsKpiCard label="Total Jobs"       value={summary.total_jobs}       loading={loading} />
        <AnalyticsKpiCard label="Revenue (AED)"    value={summary.total_revenue}    loading={loading} />
        <AnalyticsKpiCard label="Avg Rating"       value={summary.avg_rating}       loading={loading} />
        <AnalyticsKpiCard label="Active Providers" value={summary.active_providers} loading={loading} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(320px,1fr))", gap: 24 }}>
        <div style={card}>
          <h2 style={h2}>Top Providers in Category</h2>
          <AnalyticsBreakdownTable
            rows={topItems}
            loading={loading}
            columns={[
              { key: "tenant_name",   label: "Provider" },
              { key: "job_count",     label: "Jobs",     numeric: true },
              { key: "total_revenue", label: "Revenue",  numeric: true },
              { key: "avg_rating",    label: "Rating",   numeric: true },
            ]}
          />
        </div>
        <div style={card}>
          <h2 style={h2}>Offering Breakdown</h2>
          <AnalyticsBreakdownTable
            rows={breakdown}
            loading={loading}
            columns={[
              { key: "offering_name", label: "Offering" },
              { key: "job_count",     label: "Jobs",    numeric: true },
              { key: "revenue",       label: "Revenue", numeric: true },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
