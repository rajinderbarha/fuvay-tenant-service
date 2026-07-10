"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
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

export default function CategoriesAnalyticsPage() {
  const [df, setDf] = useState(ago30);
  const [dt, setDt] = useState(today);
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await adminAnalyticsApi.getCategoryPerformance({ date_from: df, date_to: dt });
      setData(r?.data ?? null);
    } catch { setData(null); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [df, dt]);

  const summary   = data?.summary ?? {};
  const breakdown = data?.breakdown ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Category Performance</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Compare revenue and job volume across service categories</p>
        </div>
        <AnalyticsDateFilter dateFrom={df} dateTo={dt} onChange={(f, t) => { setDf(f); setDt(t); }} loading={loading} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 16 }}>
        <AnalyticsKpiCard label="Total Categories"  value={summary.total_categories}  loading={loading} />
        <AnalyticsKpiCard label="Active Categories" value={summary.active_categories} loading={loading} />
        <AnalyticsKpiCard label="Total Jobs"        value={summary.total_jobs}        loading={loading} />
      </div>

      <div style={card}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>Categories Breakdown</h2>
        <AnalyticsBreakdownTable
          rows={breakdown}
          loading={loading}
          emptyText="No category data for this period"
          columns={[
            { key: "category_name",     label: "Category" },
            { key: "total_jobs",        label: "Jobs",           numeric: true },
            { key: "total_revenue",     label: "Revenue (AED)",  numeric: true },
            { key: "avg_rating",        label: "Avg Rating",     numeric: true },
            { key: "active_providers",  label: "Providers",      numeric: true },
            { key: "complaint_rate",    label: "Complaints %",   numeric: true },
          ]}
        />
      </div>

      {breakdown.length > 0 && (
        <div style={card}>
          <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 12px" }}>Drill Into Category</h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {breakdown.map((row: any) => (
              <Link
                key={row.category_id}
                href={`/admin/analytics/categories/${row.category_id}`}
                style={{ padding: "6px 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius: 8,
                  color: "var(--text-secondary)", textDecoration: "none", display: "inline-block" }}
              >
                {row.category_name}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
