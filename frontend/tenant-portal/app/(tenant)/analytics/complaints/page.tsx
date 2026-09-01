"use client";
import { useEffect, useState } from "react";
import { providerAnalyticsApi } from "../../../../lib/api";
import { AnalyticsMetric, DateFilter, SimpleTable } from "../../../../components/analytics";

const today = () => new Date().toISOString().slice(0, 10);
const ago30  = () => { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10); };

export default function ProviderComplaintsPage() {
  const [df, setDf] = useState(ago30);
  const [dt, setDt] = useState(today);
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await providerAnalyticsApi.getComplaintSummary({ date_from: df, date_to: dt });
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
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Complaints & Disputes</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Your complaint history and resolution performance</p>
        </div>
        <DateFilter dateFrom={df} dateTo={dt} onChange={(f, t) => { setDf(f); setDt(t); }} loading={loading} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 16 }}>
        <AnalyticsMetric label="Total Complaints"    value={s.total_complaints}    loading={loading} />
        <AnalyticsMetric label="Open Complaints"     value={s.open_complaints}     loading={loading} severity={Number(s.open_complaints) > 0 ? "warning" : "normal"} />
        <AnalyticsMetric label="Refunds Issued"      value={s.refunds_issued}      unit="AED" loading={loading} />
        <AnalyticsMetric label="Avg Resolution Days" value={s.avg_resolution_days} loading={loading} />
      </div>

      <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20 }}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 16px" }}>Recent Complaints</h2>
        <SimpleTable
          rows={bd}
          loading={loading}
          emptyText="No complaints for this period"
          columns={[
            { key: "complaint_type",     label: "Type" },
            { key: "status",             label: "Status" },
            { key: "count",              label: "Count",         numeric: true },
            { key: "refund_total",       label: "Refunds (AED)", numeric: true },
          ]}
        />
      </div>
    </div>
  );
}
