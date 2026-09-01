"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { TenantLayout } from "../../../components/layout/TenantLayout";
import { providerAnalyticsApi } from "../../../lib/api";
import { AnalyticsMetric, DateFilter, AlertList } from "../../../components/analytics";

const today = () => new Date().toISOString().slice(0, 10);
const ago30  = () => { const d = new Date(); d.setDate(d.getDate() - 30); return d.toISOString().slice(0, 10); };

const card: React.CSSProperties = {
  background: "var(--surface)", border: "1px solid var(--border)", borderRadius:"var(--radius-lg)", padding: 20,
};

export default function ProviderAnalyticsDashboard() {
  const [df, setDf] = useState(ago30);
  const [dt, setDt] = useState(today);
  const [summary, setSummary]     = useState<any>(null);
  const [alerts, setAlerts]       = useState<any[]>([]);
  const [loading, setLoading]     = useState(true);
  const [alertLoad, setAlertLoad] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const r = await providerAnalyticsApi.getSummary({ date_from: df, date_to: dt });
      setSummary((r as any)?.summary ?? r ?? {});
    } catch { setSummary({}); }
    finally { setLoading(false); }
  }

  async function loadAlerts() {
    setAlertLoad(true);
    try {
      const r = await providerAnalyticsApi.getOperationalAlerts();
      setAlerts((r as any)?.breakdown ?? []);
    } catch { setAlerts([]); }
    finally { setAlertLoad(false); }
  }

  useEffect(() => { load(); loadAlerts(); }, [df, dt]);

  const s = summary ?? {};

  return (
    <TenantLayout activeNav="analytics">
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: "var(--text-primary)", margin: "0 0 4px" }}>Analytics Overview</h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>Your business performance summary</p>
        </div>
        <DateFilter dateFrom={df} dateTo={dt} onChange={(f, t) => { setDf(f); setDt(t); }} loading={loading} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(180px,1fr))", gap: 16 }}>
        <AnalyticsMetric label="Total Jobs"      value={s.total_jobs}      loading={loading} />
        <AnalyticsMetric label="Revenue (AED)"   value={s.total_revenue}   loading={loading} />
        <AnalyticsMetric label="Avg Rating"      value={s.avg_rating}      loading={loading} severity={Number(s.avg_rating) < 3.5 ? "warning" : "success"} />
        <AnalyticsMetric label="Open Complaints" value={s.open_complaints} loading={loading} severity={Number(s.open_complaints) > 0 ? "warning" : "normal"} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 16 }}>
        <AnalyticsMetric label="Active Staff"     value={s.active_staff}     loading={loading} />
        <AnalyticsMetric label="Usage Credit Balance"   value={s.wallet_balance}   unit="AED" loading={loading} />
        <AnalyticsMetric label="Pending Invoices" value={s.pending_invoices} loading={loading} />
      </div>

      <div style={card}>
        <h2 style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", margin: "0 0 12px" }}>Operational Alerts</h2>
        <AlertList alerts={alerts} loading={alertLoad} />
      </div>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <Link href="/analytics/financial"  style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>Financial →</Link>
        <Link href="/analytics/staff"      style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>Staff Performance →</Link>
        <Link href="/analytics/quality"    style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>Reviews & Quality →</Link>
        <Link href="/analytics/complaints" style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>Complaints →</Link>
        <Link href="/reports"              style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>Reports →</Link>
      </div>
    </div>
    </TenantLayout>
  );
}
