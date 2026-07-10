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

export default function StaffPerformancePage() {
  const [df, setDf] = useState(ago30);
  const [dt, setDt] = useState(today);
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await adminAnalyticsApi.getStaffPerformance({ date_from: df, date_to: dt });
      setData(r?.data ?? null);
    } catch { setData(null); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [df, dt]);

  const s  = data?.summary ?? {};
  const ti = data?.top_items ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Staff Performance</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Cross-tenant staff/technician performance overview</p>
        </div>
        <AnalyticsDateFilter dateFrom={df} dateTo={dt} onChange={(f, t) => { setDf(f); setDt(t); }} loading={loading} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 16 }}>
        <AnalyticsKpiCard label="Total Staff"        value={s.total_staff}        loading={loading} />
        <AnalyticsKpiCard label="Active This Period" value={s.active_staff}       loading={loading} />
        <AnalyticsKpiCard label="Avg Jobs/Staff"     value={s.avg_jobs_per_staff} loading={loading} />
      </div>

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, padding: 20 }}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>Top Performing Staff</h2>
        <AnalyticsBreakdownTable
          rows={ti}
          loading={loading}
          emptyText="No staff data for this period"
          columns={[
            { key: "staff_name",     label: "Name" },
            { key: "tenant_name",    label: "Provider" },
            { key: "job_count",      label: "Jobs",     numeric: true },
            { key: "avg_rating",     label: "Rating",   numeric: true },
            { key: "revenue",        label: "Revenue",  numeric: true },
          ]}
        />
      </div>
    </div>
  );
}
