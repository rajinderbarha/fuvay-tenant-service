"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { adminAnalyticsApi } from "@/lib/api";
import { PageHeader } from "@serviceos/design-system";
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

export default function ProvidersAnalyticsPage() {
  const [df, setDf] = useState(ago30);
  const [dt, setDt] = useState(today);
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await adminAnalyticsApi.getProviderPerformance({ date_from: df, date_to: dt });
      setData(r?.data ?? null);
    } catch { setData(null); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [df, dt]);

  const summary  = data?.summary ?? {};
  const topItems = data?.top_items ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <PageHeader
        title="Provider Performance"
        description="Revenue, ratings, and job volume by provider."
        eyebrow="Analytics"
        actions={<AnalyticsDateFilter dateFrom={df} dateTo={dt} onChange={(f, t) => { setDf(f); setDt(t); }} loading={loading} />}
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 16 }}>
        <AnalyticsKpiCard label="Total Providers"      value={summary.total_providers}            loading={loading} />
        <AnalyticsKpiCard label="Active Providers"     value={summary.active_providers}           loading={loading} />
        <AnalyticsKpiCard label="Avg Revenue/Provider" value={summary.avg_revenue_per_provider}   unit="AED" loading={loading} />
        <AnalyticsKpiCard label="Avg Rating"           value={summary.avg_rating}                 loading={loading} />
      </div>

      <div style={card}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>Top Providers</h2>
        <AnalyticsBreakdownTable
          rows={topItems}
          loading={loading}
          emptyText="No provider data for this period"
          columns={[
            { key: "tenant_name",       label: "Provider" },
            { key: "total_revenue",     label: "Revenue (AED)",  numeric: true },
            { key: "job_count",         label: "Jobs",           numeric: true },
            { key: "avg_rating",        label: "Rating",         numeric: true },
            { key: "complaint_count",   label: "Complaints",     numeric: true },
            { key: "category_name",     label: "Primary Category" },
          ]}
        />
      </div>

      {topItems.length > 0 && (
        <div style={card}>
          <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 12px" }}>Drill Into Provider</h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {topItems.slice(0, 12).map((row: any) => (
              <Link
                key={row.tenant_id}
                href={`/admin/analytics/providers/${row.tenant_id}`}
                style={{ padding: "6px 12px", fontSize: 13, border: "1px solid var(--border)", borderRadius:"var(--radius-md)",
                  color: "var(--text-secondary)", textDecoration: "none", display: "inline-block" }}
              >
                {row.tenant_name}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
